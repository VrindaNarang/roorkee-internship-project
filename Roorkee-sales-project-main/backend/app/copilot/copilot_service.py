"""Orchestrates one Copilot turn end-to-end: detect intent -> call exactly
the backend tools that intent needs -> assemble a structured, grounded
context -> hand that context (never raw DB rows) to the LLM -> stream back a
formatted answer. Mirrors `explainability_service.py` / `recommendation_
service.py`'s role as a pure orchestrator over already-built services — the
only new capability here is talking to an LLM, and even that never sees
anything beyond what `tool_executor.call_api` (a REST call into this same
backend) returned.

This is the only module other code should import from — the FastAPI router
calls `answer()` and nothing else in this package.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.copilot import intent_router, prompt_builder, response_formatter, tool_executor
from app.copilot.intent_router import Intent
from app.copilot.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class CopilotContext:
    intent: str
    sources: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


async def _resolve_entity(question: str, auth_header: str | None) -> dict | None:
    """Matches a college name mentioned in the question against the live
    customer list — never guesses or invents a name. Tries a full-name
    substring match first (e.g. the question literally contains "Sacred
    Heart College, Pune"), then falls back to matching on distinctive words
    from each name (skips short/common words) so "explain ABC's health
    score" style partial references still resolve.
    """
    customers = await tool_executor.call_api("/customers", params={"page_size": 100}, auth_header=auth_header)
    items = customers.get("items", []) if isinstance(customers, dict) else []
    if not items:
        return None

    q_lower = question.lower()

    exact_matches = [c for c in items if c["name"].lower() in q_lower]
    if exact_matches:
        return max(exact_matches, key=lambda c: len(c["name"]))

    def _distinctive_words(name: str) -> list[str]:
        first_segment = name.split(",")[0]
        return [w for w in first_segment.split() if len(w) > 3]

    partial_matches = [c for c in items if any(w.lower() in q_lower for w in _distinctive_words(c["name"]))]
    if not partial_matches:
        return None
    return max(partial_matches, key=lambda c: len(c["name"]))


async def _gather_context(intent: Intent, question: str, auth_header: str | None) -> CopilotContext:
    sources: list[str] = []
    data: dict = {}

    async def _call(path: str, params: dict | None = None) -> object:
        return await tool_executor.call_api(path, params=params, auth_header=auth_header)

    if intent == Intent.SALES_SUMMARY:
        data["dashboard_summary"] = await _call("/dashboard/summary")
        data["recent_sales_trend"] = await _call("/dashboard/sales-trend", params={"months": 2})
        sources.append("Analytics API")

    elif intent == Intent.CUSTOMER_HEALTH_EXPLAIN:
        entity = await _resolve_entity(question, auth_header)
        if entity is None:
            data["error"] = "No matching customer name was found in the question."
        else:
            data["customer"] = entity
            data["health"] = await _call(f"/customers/{entity['id']}/health")
            data["explanation"] = await _call(f"/explain/customer/{entity['id']}")
            sources += ["Health Score API", "SHAP Explanation API"]

    elif intent == Intent.CUSTOMER_PREDICTION_EXPLAIN:
        entity = await _resolve_entity(question, auth_header)
        if entity is None:
            data["error"] = "No matching customer name was found in the question."
        else:
            data["customer"] = entity
            data["prediction"] = await _call(f"/predictions/customer/{entity['id']}")
            data["explanation"] = await _call(f"/explain/customer/{entity['id']}")
            sources += ["Prediction API", "SHAP Explanation API"]

    elif intent == Intent.CONTACT_LIST:
        data["customer_recommendations"] = await _call("/recommendations/customers")
        sources.append("Recommendation Engine")

    elif intent == Intent.HIGH_PROBABILITY:
        data["high_probability_customers"] = await _call("/predictions/high-probability", params={"limit": 10})
        sources.append("Prediction API")

    elif intent == Intent.HIGH_PRIORITY_RECOMMENDATIONS:
        data["high_priority_recommendations"] = await _call("/recommendations/high-priority")
        sources.append("Recommendation Engine")

    elif intent == Intent.AT_RISK:
        data["risk_recommendations"] = await _call("/recommendations/risk")
        data["critical_customers"] = await _call("/customers/critical")
        sources += ["Recommendation Engine", "Health Score API"]

    elif intent == Intent.REGIONAL_PERFORMANCE:
        data["region_performance"] = await _call("/analytics/region-performance")
        sources.append("Analytics API")

    elif intent == Intent.SALES_TREND:
        data["dashboard_summary"] = await _call("/dashboard/summary")
        data["regional_recommendations"] = await _call("/recommendations/regions")
        data["category_distribution"] = await _call("/dashboard/category-distribution")
        data["risk_recommendations"] = await _call("/recommendations/risk")
        sources += ["Analytics API", "Recommendation Engine"]

    else:  # GENERAL fallback — a broad, grounded snapshot so the LLM always has real data to work from
        data["dashboard_summary"] = await _call("/dashboard/summary")
        data["high_priority_recommendations"] = await _call("/recommendations/high-priority")
        sources += ["Analytics API", "Recommendation Engine"]

    return CopilotContext(intent=intent.value, sources=sorted(set(sources)), data=data)


async def answer(question: str, history: list[ChatTurn], auth_header: str | None = None) -> AsyncIterator[str]:
    """Streams the Copilot's answer to `question`, given prior turns for
    conversational context. Every yielded chunk is either LLM-generated text
    (grounded in the retrieved context) or, as the final chunk, the
    deterministic source-citation footer.

    `auth_header` is the asking user's own `Authorization: Bearer ...` value,
    forwarded to every internal tool call (Milestone 11: every backend
    endpoint now requires auth) — the Copilot acts with the caller's own
    permissions, never an elevated service account.
    """
    intent = intent_router.detect_intent(question)
    logger.info("Copilot intent detected: %s", intent.value)

    context = await _gather_context(intent, question, auth_header)
    if response_formatter.has_data_error(context):
        logger.warning("Copilot context for intent=%s contains a tool-call error", intent.value)

    messages = prompt_builder.build_messages(question, context, history)

    try:
        provider = get_llm_provider()
        got_any_chunk = False
        async for chunk in provider.stream_chat(messages):
            got_any_chunk = True
            yield chunk
        if not got_any_chunk:
            yield "The Sales Copilot's language model returned an empty response. Please try again."
    except Exception:
        # The retrieved data above is still real and correct even if the LLM
        # itself is unreachable (no provider configured, Ollama not running,
        # Groq/OpenRouter rate-limited, etc.) — say so honestly instead of
        # silently truncating the stream or inventing an answer.
        logger.exception("Copilot LLM call failed for intent=%s", intent.value)
        yield (
            "I couldn't reach the language model to phrase this answer (no provider is configured or "
            "it's unreachable right now). Set GROQ_API_KEY (or another provider) in the backend's .env "
            "and try again."
        )
        return

    footer = response_formatter.source_footer(context)
    if footer:
        yield footer
