# Route is lifecycle plumbing only — auth, accept, dispatch loop, disconnect.
# Per-turn orchestration lives in app.services.agent_session.AgentSession.
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import CurrentUserWS
from app.core.config import settings
from app.schemas.base import AgentModelsResponse
from app.services.agent import AgentConnectionManager
from app.services.agent_session import AgentSession
from app.services.model_registry import chat_model_options, default_chat_model_ref

logger = logging.getLogger(__name__)

router = APIRouter()

manager = AgentConnectionManager()


@router.get("/agent/models", response_model=AgentModelsResponse)
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    default_ref = default_chat_model_ref(settings)
    return {
        "default": default_ref.id,
        "models": chat_model_options(settings),
    }


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: CurrentUserWS,
) -> None:
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket)
    session = AgentSession(
        websocket,
        user,
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            await session.handle_frame(data)
    finally:
        await session.shutdown()
        manager.disconnect(websocket)
