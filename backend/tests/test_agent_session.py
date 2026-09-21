from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

from app.services.agent_session import _needs_parent_clarification, _tool_result_event_payload


def test_tool_result_event_payload_reads_current_pydantic_ai_shape() -> None:
    event = FunctionToolResultEvent(
        part=ToolReturnPart(
            tool_name="search_documents",
            content="Search result text",
            tool_call_id="tool-123",
        )
    )

    assert _tool_result_event_payload(event) == ("tool-123", "Search result text")


def test_parent_clarification_preflight_asks_for_missing_source() -> None:
    payload = _needs_parent_clarification(
        "Summarise this",
        has_files=False,
        has_history=False,
        deep_research=False,
    )

    assert payload is not None
    assert payload.question == "What should I use as the source material?"
    assert 2 <= len(payload.options) <= 5
    assert payload.allow_free_text is True
    assert payload.as_event_data()["allow_multiple"] is False


def test_parent_clarification_preflight_skips_when_file_attached() -> None:
    payload = _needs_parent_clarification(
        "Summarise this",
        has_files=True,
        has_history=False,
        deep_research=False,
    )

    assert payload is None


def test_parent_clarification_preflight_caps_at_two_rounds() -> None:
    payload = _needs_parent_clarification(
        "Summarise this",
        has_files=False,
        has_history=False,
        deep_research=False,
        clarification_round=2,
    )

    assert payload is None


def test_parent_clarification_second_round_is_narrower() -> None:
    first = _needs_parent_clarification(
        "Summarise this",
        has_files=False,
        has_history=False,
        deep_research=False,
        clarification_round=0,
    )
    second = _needs_parent_clarification(
        "Summarise this",
        has_files=False,
        has_history=False,
        deep_research=False,
        clarification_round=1,
    )

    assert first is not None
    assert second is not None
    assert len(second.options) < len(first.options)
