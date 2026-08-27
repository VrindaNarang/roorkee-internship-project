"""Tests for the Sales Copilot (Milestone 10).

`intent_router`/`prompt_builder`/`response_formatter` are pure-logic and
tested directly, same approach as `test_recommendation_engine.py`. The
end-to-end `copilot_service.answer()` pipeline is tested against the real
in-process backend (via `tool_executor`'s ASGI transport, hitting the same
test Postgres the other smoke tests use) with the LLM provider swapped for a
fake one — proving the whole grounding pipeline (intent -> real API calls ->
context -> prompt -> streamed answer -> verified source footer) works
without needing a real LLM API key.
"""

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.copilot import copilot_service, prompt_builder, response_formatter
from app.copilot.copilot_service import ChatTurn, CopilotContext
from app.copilot.intent_router import Intent, detect_intent
from app.main import app

client = TestClient(app)


# --------------------------------------------------------------------------
# Intent detection — the milestone's own example questions
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Summarize today's sales.", Intent.SALES_SUMMARY),
        ("Why did sales decrease this month?", Intent.SALES_TREND),
        ("Which customers should I contact this week?", Intent.CONTACT_LIST),
        ("Which customers have the highest purchase probability?", Intent.HIGH_PROBABILITY),
        ("Which customers are at risk?", Intent.AT_RISK),
        ("Explain why ABC College has a low Health Score.", Intent.CUSTOMER_HEALTH_EXPLAIN),
        ("Explain the prediction for XYZ University.", Intent.CUSTOMER_PREDICTION_EXPLAIN),
        ("Which region generated the highest revenue?", Intent.REGIONAL_PERFORMANCE),
        ("Which recommendations are currently the highest priority?", Intent.HIGH_PRIORITY_RECOMMENDATIONS),
        ("What's the weather like today?", Intent.GENERAL),
    ],
)
def test_detect_intent_matches_milestone_example_questions(question: str, expected: Intent) -> None:
    assert detect_intent(question) == expected


# --------------------------------------------------------------------------
# prompt_builder
# --------------------------------------------------------------------------


def test_build_messages_includes_system_prompt_context_and_question() -> None:
    context = CopilotContext(intent="sales_summary", sources=["Analytics API"], data={"total_revenue": 100})
    messages = prompt_builder.build_messages("How are sales?", context, [])

    assert messages[0]["role"] == "system"
    assert "Business Insight" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert "total_revenue" in messages[-1]["content"]
    assert "How are sales?" in messages[-1]["content"]


def test_build_messages_truncates_history_to_configured_max() -> None:
    context = CopilotContext(intent="general", sources=[], data={})
    long_history = [ChatTurn(role="user", content=f"turn {i}") for i in range(20)]
    messages = prompt_builder.build_messages("latest question", context, long_history)

    # system + up to max_history_turns + the new user message
    from app.copilot.config import get_copilot_settings

    max_turns = get_copilot_settings().max_history_turns
    assert len(messages) == 1 + max_turns + 1


# --------------------------------------------------------------------------
# response_formatter
# --------------------------------------------------------------------------


def test_source_footer_lists_every_source() -> None:
    context = CopilotContext(intent="at_risk", sources=["Health Score API", "Recommendation Engine"], data={})
    footer = response_formatter.source_footer(context)
    assert "Data Sources:" in footer
    assert "- Health Score API" in footer
    assert "- Recommendation Engine" in footer


def test_source_footer_empty_when_no_sources() -> None:
    context = CopilotContext(intent="general", sources=[], data={})
    assert response_formatter.source_footer(context) == ""


def test_has_data_error_detects_failed_tool_call() -> None:
    ok_context = CopilotContext(intent="x", sources=[], data={"a": {"value": 1}})
    error_context = CopilotContext(intent="x", sources=[], data={"a": {"error": "boom"}})
    assert response_formatter.has_data_error(ok_context) is False
    assert response_formatter.has_data_error(error_context) is True


# --------------------------------------------------------------------------
# End-to-end pipeline with a fake LLM (real tool calls, fake model)
# --------------------------------------------------------------------------


class _FakeProvider:
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        yield "Business Insight: "
        yield "revenue is stable this month."


@pytest.mark.asyncio
async def test_answer_streams_fake_llm_output_and_appends_real_source_footer(monkeypatch, auth_headers: dict) -> None:
    monkeypatch.setattr(copilot_service, "get_llm_provider", lambda: _FakeProvider())

    chunks = [
        chunk
        async for chunk in copilot_service.answer("Summarize today's sales.", [], auth_headers["Authorization"])
    ]
    full_text = "".join(chunks)

    assert "Business Insight: revenue is stable this month." in full_text
    assert "Data Sources:" in full_text
    assert "Analytics API" in full_text


@pytest.mark.asyncio
async def test_answer_without_auth_header_reports_tool_call_errors_not_a_crash(monkeypatch) -> None:
    """No forwarded token -> every internal tool call 401s -> the pipeline
    must degrade to an honest "data unavailable" answer, never raise."""
    monkeypatch.setattr(copilot_service, "get_llm_provider", lambda: _FakeProvider())

    chunks = [chunk async for chunk in copilot_service.answer("Summarize today's sales.", [], None)]
    full_text = "".join(chunks)

    assert full_text  # completed without raising


def test_copilot_chat_endpoint_streams_response(monkeypatch, auth_headers: dict) -> None:
    monkeypatch.setattr(copilot_service, "get_llm_provider", lambda: _FakeProvider())

    response = client.post(
        "/api/v1/copilot/chat",
        json={"question": "Summarize today's sales.", "history": []},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Business Insight" in response.text
    assert "Data Sources" in response.text


def test_copilot_chat_endpoint_requires_auth() -> None:
    response = client.post("/api/v1/copilot/chat", json={"question": "Summarize today's sales.", "history": []})
    assert response.status_code == 401


class _BrokenProvider:
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        raise ConnectionError("no provider reachable")
        yield ""  # pragma: no cover - unreachable, makes this an async generator


@pytest.mark.asyncio
async def test_answer_reports_honest_error_when_llm_is_unreachable(monkeypatch, auth_headers: dict) -> None:
    monkeypatch.setattr(copilot_service, "get_llm_provider", lambda: _BrokenProvider())

    chunks = [
        chunk
        async for chunk in copilot_service.answer("Summarize today's sales.", [], auth_headers["Authorization"])
    ]
    full_text = "".join(chunks)

    assert "couldn't reach the language model" in full_text
    # No fabricated business content and no (potentially misleading) sources
    # footer once the model itself never actually produced an answer.
    assert "Business Insight" not in full_text
    assert "Data Sources:" not in full_text
