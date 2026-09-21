# Thin session wrapper — the route is lifecycle plumbing only; orchestration lives here.
import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from fastapi import WebSocket, WebSocketDisconnect
from pydantic_ai import (
    Agent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.messages import (
    BinaryContent,
    TextPart,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
)

from app.agents.assistant import Deps, get_agent
from app.api.deps import get_conversation_service
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db_context
from app.services.agent import (
    build_message_history,
    persist_assistant_turn,
    persist_user_turn,
    send_event,
)
from app.services.file_storage import get_file_storage
from app.services.research import RESEARCH_TOOL_NAMES, ResearchToolkit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClarificationPayload:
    """Structured clarification request emitted before an underspecified turn."""

    question: str
    options: list[str]
    allow_free_text: bool = True
    allow_multiple: bool = False

    def as_event_data(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "options": self.options[:5],
            "allow_free_text": self.allow_free_text,
            "allow_multiple": self.allow_multiple,
        }


@dataclass
class PendingClarification:
    """Tracks one parent-agent clarification loop across user replies."""

    original_message: str
    rounds: int = 0


def _tool_result_event_payload(tool_event: FunctionToolResultEvent) -> tuple[str, str]:
    """Extract result payload across pydantic-ai event shape changes."""
    result = getattr(tool_event, "result", None)
    part = getattr(tool_event, "part", None)
    tool_call_id = (
        getattr(tool_event, "tool_call_id", None)
        or getattr(part, "tool_call_id", None)
        or ""
    )
    content = (
        getattr(result, "content", None)
        if result is not None
        else getattr(part, "content", getattr(tool_event, "content", None))
    )
    return str(tool_call_id), "" if content is None else str(content)


def _needs_parent_clarification(
    user_message: str,
    *,
    has_files: bool,
    has_history: bool,
    deep_research: bool,
    clarification_round: int = 0,
) -> ClarificationPayload | None:
    """Return a structured preflight clarification request when intent is too vague.

    This runs before model execution and before deep-research delegation. It is
    deliberately conservative: the normal agent can handle ordinary ambiguity,
    but short deictic requests ("summarise this", "fix it") without any visible
    referent and broad research prompts need a selectable user choice first.
    """

    text = " ".join(user_message.lower().split())
    if not text:
        return None

    word_count = len(text.split())
    has_context = has_files or has_history
    deictic_terms = ("this", "that", "it", "these", "those", "the above", "the attached")

    if clarification_round >= 2:
        return None

    if not has_context and any(term in text for term in deictic_terms):
        if any(term in text for term in ("summarise", "summarize", "explain", "review", "analyse", "analyze")):
            if clarification_round == 1:
                return ClarificationPayload(
                    question="I still need the source. Which one should I use now?",
                    options=[
                        "I will attach the source file",
                        "I will paste the source text",
                        "Answer generally without source material",
                    ],
                )
            return ClarificationPayload(
                question="What should I use as the source material?",
                options=[
                    "I will attach the file",
                    "I will paste the text",
                    "Use the current conversation",
                    "Give a general answer instead",
                ],
            )
        if any(term in text for term in ("fix", "change", "update", "make", "do")):
            if clarification_round == 1:
                return ClarificationPayload(
                    question="I still need the target. What should I work on?",
                    options=[
                        "The current chat content",
                        "A file I will attach",
                        "A specific app page or component",
                    ],
                )
            return ClarificationPayload(
                question="What should I work on?",
                options=[
                    "The current chat content",
                    "An attached file",
                    "A page or feature in the app",
                    "I will describe it in more detail",
                ],
            )

    vague_starters = (
        "do it",
        "fix it",
        "make it better",
        "change it",
        "update it",
        "summarise this",
        "summarize this",
        "explain this",
        "review this",
    )
    if not has_files and word_count <= 5 and any(text.startswith(s) for s in vague_starters):
        if clarification_round == 1:
            return ClarificationPayload(
                question="Which target should I assume?",
                options=[
                    "The latest message in this chat",
                    "A file I will attach",
                    "A specific app page or component",
                ],
            )
        return ClarificationPayload(
            question="Which target should I use for this request?",
            options=[
                "The latest message in this chat",
                "A file I will attach",
                "A specific app page or component",
                "I will paste the relevant text",
            ],
        )

    if deep_research and word_count <= 6:
        if clarification_round == 1:
            return ClarificationPayload(
                question="Which research scope should I assume?",
                options=[
                    "Broad overview",
                    "Comparison and recommendation",
                    "Risks and trade-offs",
                ],
            )
        return ClarificationPayload(
            question="What scope should I research?",
            options=[
                "Give me a broad overview",
                "Compare options and recommend one",
                "Focus on risks and trade-offs",
                "Find current facts and sources",
            ],
        )

    return None


class AgentSession:
    """One WebSocket session with the AI agent."""

    # Control frames this session implements, beyond `stop`. Anything else with
    # a `type` is ignored rather than treated as a prompt.
    _HANDLED_FRAME_TYPES: ClassVar[frozenset[str]] = frozenset({"message", "ask_user_response"})

    def __init__(
        self,
        websocket: WebSocket,
        user: User,
    ) -> None:
        self.websocket = websocket
        self.user = user
        self.conversation_history: list[dict[str, str]] = []
        self.deps = Deps()
        self.deps.ask_user = self._ask_user
        self.current_conversation_id: str | None = None
        self._turn_task: asyncio.Task[None] | None = None
        self._ask_user_future: asyncio.Future[list[dict[str, Any]]] | None = None
        self._research: ResearchToolkit | None = None
        self._subagent_task_manager: Any | None = None
        self._pending_parent_clarification: PendingClarification | None = None

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; an ``ask_user_response`` unblocks a
        paused run; any other control frame is ignored; a bare message starts a
        new turn as a cancellable background task.
        """
        msg_type = data.get("type")

        if msg_type == "stop":
            await self._cancel_turn()
            return

        if msg_type == "ask_user_response":
            fut = self._ask_user_future
            if fut is not None and not fut.done():
                answers = data.get("answers")
                fut.set_result(answers if isinstance(answers, list) else [])
            return

        # A frame carrying a `type` this session does not implement is a control
        # frame, not a prompt — the shared frontend hook emits `resume`
        # regardless of which framework is generated. Falling through would
        # start a turn with an empty message and answer with "Empty message".
        if msg_type is not None and msg_type not in self._HANDLED_FRAME_TYPES:
            logger.debug("Ignoring unsupported control frame: %s", msg_type)
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
                    "conversation_id": self.current_conversation_id,
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if len(file_ids) > settings.MAX_CHAT_ATTACHMENTS:
            await send_event(
                self.websocket,
                "error",
                {
                    "message": (
                        f"Too many files. Maximum {settings.MAX_CHAT_ATTACHMENTS} files "
                        "per chat message."
                    )
                },
            )
            return

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
            self.user,
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            deep_research = settings.ENABLE_DEEP_RESEARCH and bool(data.get("deep_research", False))
            pending_clarification = self._pending_parent_clarification
            effective_user_message = user_message
            forced_assumption_note: str | None = None
            clarification_round = 0

            if pending_clarification is not None:
                clarification_round = pending_clarification.rounds
                effective_user_message = (
                    f"Original request:\n{pending_clarification.original_message}\n\n"
                    f"User clarification:\n{user_message or '(skipped)'}"
                )
                if clarification_round >= 2:
                    forced_assumption_note = (
                        "The user has already had two clarification rounds. Do not ask another "
                        "clarifying question. Proceed with your best reasonable assumption and "
                        "state that assumption briefly at the start of your response."
                    )

            clarification = None
            if pending_clarification is not None:
                answer = user_message.lower().strip()
                needs_second_round = (
                    not answer
                    or "skip" in answer
                    or answer in {"not sure", "unsure", "i don't know", "dont know"}
                    or ("attach" in answer and not file_ids)
                    or ("paste" in answer and len(answer.split()) <= 6)
                )
                if needs_second_round:
                    clarification = self._parent_clarification_for_turn(
                        pending_clarification.original_message,
                        has_files=bool(file_ids),
                        deep_research=deep_research,
                        round_number=clarification_round,
                    )
            else:
                clarification = self._parent_clarification_for_turn(
                    effective_user_message,
                    has_files=bool(file_ids),
                    deep_research=deep_research,
                    round_number=clarification_round,
                )
            if clarification is not None:
                if pending_clarification is None:
                    self._pending_parent_clarification = PendingClarification(
                        original_message=user_message,
                        rounds=1,
                    )
                else:
                    pending_clarification.rounds += 1
                await send_event(self.websocket, "clarification_request", clarification.as_event_data())
                await send_event(
                    self.websocket,
                    "complete",
                    {
                        "conversation_id": self.current_conversation_id,
                        "clarification_requested": True,
                    },
                )
                return

            if pending_clarification is not None and clarification is None:
                self._pending_parent_clarification = None

            self._research = None
            todo_cap = None
            subagent_cap = None
            ctx_manager_cap = None
            if deep_research and self.current_conversation_id:
                self._research = ResearchToolkit(self._send, model_name=data.get("model"))
                caps = await self._research.build(self.current_conversation_id)
                todo_cap = caps.todo
                subagent_cap = caps.subagents
                ctx_manager_cap = caps.context_manager
            else:
                deep_research = False
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
                deep_research=deep_research,
                todo_capability=todo_cap,
                subagent_capability=subagent_cap,
                context_manager_capability=ctx_manager_cap,
            )
            model_history = build_message_history(self.conversation_history)
            if forced_assumption_note:
                effective_user_message = f"{forced_assumption_note}\n\n{effective_user_message}"
            user_input = await self._build_multimodal_input(effective_user_message, file_ids)

            collected_tool_calls: list[dict[str, Any]] = []
            collected_thinking: list[str] = []
            self._subagent_task_manager = (
                self._research.subagent_capability.task_manager
                if self._research and self._research.subagent_capability
                else None
            )
            if self._subagent_task_manager is not None:
                self._subagent_task_manager.message_bus.add_handler(self._on_subagent_message)
            poller = (
                asyncio.create_task(self._poll_subagent_status())
                if self._research is not None
                else None
            )
            try:
                async with assistant.agent.iter(
                    user_input, deps=self.deps, message_history=model_history
                ) as agent_run:
                    await self._stream_agent_run(
                        agent_run, user_message, collected_tool_calls, collected_thinking
                    )
            finally:
                if poller is not None:
                    poller.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await poller
                if self._subagent_task_manager is not None:
                    self._subagent_task_manager.message_bus.remove_handler(
                        self._on_subagent_message
                    )
                    self._subagent_task_manager = None
                if self._research is not None:
                    await self._research.flush()

            # Update in-memory history only after a complete agent run
            if agent_run.result is not None:
                self.conversation_history.append({"role": "user", "content": effective_user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": agent_run.result.output}
                )
            assistant_msg_id: str | None = None
            if self.current_conversation_id and agent_run.result is not None:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    agent_run.result.output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                    thinking="".join(collected_thinking) or None,
                )

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

    def _parent_clarification_for_turn(
        self,
        user_message: str,
        *,
        has_files: bool,
        deep_research: bool,
        round_number: int,
    ) -> ClarificationPayload | None:
        """Preflight the parent-agent turn before model/delegation work starts."""

        if round_number >= 2:
            return None
        return _needs_parent_clarification(
            user_message,
            has_files=has_files,
            has_history=bool(self.conversation_history),
            deep_research=deep_research,
            clarification_round=round_number,
        )

    async def _ask_user(self, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pause the run: ask the client questions and block until they answer.

        Emits an ``ask_user`` event with the whole batch, then awaits a future the
        frame dispatcher completes when the matching ``ask_user_response`` arrives.
        The client returns a list of answers parallel to the questions.
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[list[dict[str, Any]]] = loop.create_future()
        self._ask_user_future = fut
        try:
            await send_event(self.websocket, "ask_user", {"questions": questions})
            return await fut
        finally:
            self._ask_user_future = None

    async def _send(self, event_type: str, data: Any) -> bool:
        """Emit a WebSocket event on this session's socket (bound for callbacks)."""
        return await send_event(self.websocket, event_type, data)

    async def _poll_subagent_status(self) -> None:
        """Emit ``subagent_status`` frames for changing async subagent tasks.

        Polls the subagent capability's task manager ~1/s and forwards a frame
        whenever a task's status changes (or is first seen). Cancelled in the
        run's ``finally``.
        """
        seen: dict[str, str] = {}
        cap = self._research.subagent_capability if self._research else None
        if cap is None:
            return
        try:
            while True:
                task_manager = cap.task_manager
                if task_manager is not None:
                    for handle in task_manager.list_handles():
                        status = getattr(handle.status, "value", str(handle.status))
                        task_id = handle.task_id
                        if seen.get(task_id) == status:
                            continue
                        seen[task_id] = status
                        await self._send(
                            "subagent_status",
                            {
                                "task_id": task_id,
                                "subagent_name": handle.subagent_name,
                                "description": handle.description,
                                "status": status,
                                "error": handle.error,
                            },
                        )
                        ts = datetime.utcnow().isoformat()
                        if status == "running":
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "info",
                                    "text": "Task started — running in background",
                                    "timestamp": ts,
                                },
                            )
                        elif status == "waiting_for_answer" and handle.pending_question:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "question",
                                    "text": handle.pending_question,
                                    "timestamp": ts,
                                },
                            )
                        elif status == "completed" and handle.result:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "result",
                                    "text": handle.result[:1500],
                                    "timestamp": ts,
                                },
                            )
                        elif status == "failed" and handle.error:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "error",
                                    "text": handle.error,
                                    "timestamp": ts,
                                },
                            )
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            task_manager = cap.task_manager
            if task_manager is not None:
                for handle in task_manager.list_handles():
                    status = getattr(handle.status, "value", str(handle.status))
                    if seen.get(handle.task_id) == status:
                        continue
                    await self._send(
                        "subagent_status",
                        {
                            "task_id": handle.task_id,
                            "subagent_name": handle.subagent_name,
                            "description": handle.description,
                            "status": status,
                            "error": handle.error,
                        },
                    )
                    ts = datetime.utcnow().isoformat()
                    if status == "completed" and handle.result:
                        await self._send(
                            "subagent_message",
                            {
                                "task_id": handle.task_id,
                                "type": "result",
                                "text": handle.result[:1500],
                                "timestamp": ts,
                            },
                        )
                    elif status == "failed" and handle.error:
                        await self._send(
                            "subagent_message",
                            {
                                "task_id": handle.task_id,
                                "type": "error",
                                "text": handle.error,
                                "timestamp": ts,
                            },
                        )
            raise

    async def _on_subagent_message(self, msg: Any) -> None:
        """Forward TASK_UPDATE (steering) messages from the message bus as SSE events."""
        try:
            from subagents_pydantic_ai.types import MessageType

            if msg.type != MessageType.TASK_UPDATE:
                return
            payload = msg.payload
            text = payload.get("message") if isinstance(payload, dict) else str(payload)
            if not text:
                return
            await self._send(
                "subagent_message",
                {
                    "task_id": msg.task_id,
                    "type": "steering",
                    "text": text,
                    "timestamp": msg.timestamp.isoformat(),
                },
            )
        except Exception:
            pass

    async def _build_multimodal_input(
        self, user_message: str, file_ids: list[Any]
    ) -> str | list[Any]:
        """Fold attached images and parsed file text into the user message."""
        if not file_ids:
            return user_message

        storage = get_file_storage()
        image_parts: list[BinaryContent] = []
        file_context_parts: list[str] = []
        async with get_db_context() as file_db:
            attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
            for chat_file in attached_files:
                try:
                    if chat_file.file_type == "image":
                        file_data = await storage.load(chat_file.storage_path)
                        image_parts.append(
                            BinaryContent(data=file_data, media_type=chat_file.mime_type)
                        )
                    elif chat_file.parsed_content:
                        file_context_parts.append(
                            f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```"
                        )
                except Exception:
                    logger.warning("Failed to load file %s", chat_file.id, exc_info=True)

        full_text = user_message + "".join(file_context_parts)
        if image_parts:
            return [full_text, *image_parts]
        return full_text

    async def _stream_agent_run(
        self,
        agent_run: Any,
        user_message: str,
        collected_tool_calls: list[dict[str, Any]],
        collected_thinking: list[str],
    ) -> None:
        """Drive the agent_run iterator, dispatching each node to its streaming helper."""
        async for node in agent_run:
            if Agent.is_user_prompt_node(node):
                prompt_text = (
                    node.user_prompt if isinstance(node.user_prompt, str) else user_message
                )
                await send_event(self.websocket, "user_prompt_processed", {"prompt": prompt_text})
            elif Agent.is_model_request_node(node):
                await send_event(self.websocket, "model_request_start", {})
                async with node.stream(agent_run.ctx) as request_stream:
                    await self._stream_request_events(request_stream, collected_thinking)
            elif Agent.is_call_tools_node(node):
                await send_event(self.websocket, "call_tools_start", {})
                async with node.stream(agent_run.ctx) as handle_stream:
                    await self._stream_tool_events(handle_stream, collected_tool_calls)
            elif Agent.is_end_node(node) and agent_run.result is not None:
                await send_event(
                    self.websocket, "final_result", {"output": agent_run.result.output}
                )

    async def _stream_request_events(
        self, request_stream: Any, collected_thinking: list[str]
    ) -> None:
        """Forward model-request events (text/thinking/tool deltas + final-result start).

        During a deep research turn the model narrates every delegation step.
        A plain-text response ends a PydanticAI run, so a step that issues a
        planning/delegation tool call (``RESEARCH_TOOL_NAMES``) is interstitial:
        its text is buffered and dropped. A step with only content tools (charts,
        RAG) or no tool calls is the final answer and its text is released.
        Reasoning and tool events are always forwarded.
        """
        deep_research = self._research is not None
        buffered_text: list[tuple[int, str]] = []
        tool_names: dict[int, str] = {}

        async def emit_text(index: int, content: str) -> None:
            if not content:
                return
            if deep_research:
                buffered_text.append((index, content))
            else:
                await send_event(self.websocket, "text_delta", {"index": index, "content": content})

        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                await send_event(
                    self.websocket,
                    "part_start",
                    {"index": event.index, "part_type": type(event.part).__name__},
                )
                if isinstance(event.part, ToolCallPart):
                    if event.part.tool_name:
                        tool_names[event.index] = event.part.tool_name
                elif isinstance(event.part, TextPart) and event.part.content:
                    await emit_text(event.index, event.part.content)
                elif isinstance(event.part, ThinkingPart) and event.part.content:
                    if collected_thinking:
                        collected_thinking.append(" ")
                    collected_thinking.append(event.part.content)
                    await send_event(
                        self.websocket,
                        "thinking_delta",
                        {"index": event.index, "content": event.part.content},
                    )
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    await emit_text(event.index, event.delta.content_delta)
                elif isinstance(event.delta, ThinkingPartDelta):
                    if event.delta.content_delta:
                        collected_thinking.append(event.delta.content_delta)
                        await send_event(
                            self.websocket,
                            "thinking_delta",
                            {"index": event.index, "content": event.delta.content_delta},
                        )
                elif isinstance(event.delta, ToolCallPartDelta):
                    if event.delta.tool_name_delta:
                        tool_names[event.index] = (
                            tool_names.get(event.index, "") + event.delta.tool_name_delta
                        )
                    await send_event(
                        self.websocket,
                        "tool_call_delta",
                        {"index": event.index, "args_delta": event.delta.args_delta},
                    )
            elif isinstance(event, FinalResultEvent):
                await send_event(
                    self.websocket,
                    "final_result_start",
                    {"tool_name": event.tool_name},
                )

        made_research_call = any(name in RESEARCH_TOOL_NAMES for name in tool_names.values())
        if deep_research and buffered_text and not made_research_call:
            for index, content in buffered_text:
                await send_event(self.websocket, "text_delta", {"index": index, "content": content})

    async def _stream_tool_events(
        self,
        handle_stream: Any,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Forward tool-call/result events; collect tool calls (with results) for persistence."""
        pending: dict[str, dict[str, Any]] = {}
        async for tool_event in handle_stream:
            if isinstance(tool_event, FunctionToolCallEvent):
                tc = {
                    "tool_call_id": tool_event.part.tool_call_id,
                    "tool_name": tool_event.part.tool_name,
                    "args": tool_event.part.args_as_dict(raise_if_invalid=False),
                }
                collected_tool_calls.append(tc)
                pending[tool_event.part.tool_call_id] = tc
                await send_event(self.websocket, "tool_call", tc)
            elif isinstance(tool_event, FunctionToolResultEvent):
                tool_call_id, content = _tool_result_event_payload(tool_event)
                tc = pending.get(tool_call_id)
                if tc is not None:
                    tc["result"] = content
                await send_event(
                    self.websocket,
                    "tool_result",
                    {
                        "tool_call_id": tool_call_id,
                        "content": content,
                    },
                )
