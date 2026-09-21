from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

from app.services.agent_session import _tool_result_event_payload


def test_tool_result_event_payload_reads_current_pydantic_ai_shape() -> None:
    event = FunctionToolResultEvent(
        part=ToolReturnPart(
            tool_name="search_documents",
            content="Search result text",
            tool_call_id="tool-123",
        )
    )

    assert _tool_result_event_payload(event) == ("tool-123", "Search result text")
