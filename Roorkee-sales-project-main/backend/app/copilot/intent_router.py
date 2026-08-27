"""Deterministic intent detection for the Sales Copilot (Milestone 10).

Keyword/pattern matching, not an LLM function-calling loop. Free-tier LLMs
(Groq/OpenRouter free models, Ollama) have inconsistent tool-calling support,
and a fully deterministic router means the exact same question always
triggers the exact same backend calls — auditable, testable, and immune to
the LLM inventing a tool that doesn't exist. Patterns are checked in order;
the first match wins, so more specific phrasings are listed before the
broader fallback ones.
"""

from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    SALES_SUMMARY = "sales_summary"
    CUSTOMER_HEALTH_EXPLAIN = "customer_health_explain"
    CUSTOMER_PREDICTION_EXPLAIN = "customer_prediction_explain"
    CONTACT_LIST = "contact_list"
    HIGH_PROBABILITY = "high_probability"
    HIGH_PRIORITY_RECOMMENDATIONS = "high_priority_recommendations"
    AT_RISK = "at_risk"
    REGIONAL_PERFORMANCE = "regional_performance"
    SALES_TREND = "sales_trend"
    GENERAL = "general"


_PATTERNS: list[tuple[Intent, re.Pattern]] = [
    (Intent.SALES_SUMMARY, re.compile(r"\bsummar\w*\s+(today|this month|sales)\b|\btoday'?s sales\b", re.I)),
    (Intent.CUSTOMER_HEALTH_EXPLAIN, re.compile(r"\bhealth\s*score\b", re.I)),
    (Intent.CUSTOMER_PREDICTION_EXPLAIN, re.compile(r"\bpredict\w*\b", re.I)),
    (Intent.CONTACT_LIST, re.compile(r"\bcontact\b.*\b(this week|customers?)\b|\bwho should i contact\b", re.I)),
    (Intent.HIGH_PROBABILITY, re.compile(r"\bhighest purchase probability\b|\bmost likely to (buy|purchase)\b", re.I)),
    (
        Intent.HIGH_PRIORITY_RECOMMENDATIONS,
        re.compile(r"\brecommendation\w*\b.*\bpriorit\w*\b|\bhighest priority\b", re.I),
    ),
    (Intent.AT_RISK, re.compile(r"\bat[- ]risk\b|\bcritical customers?\b|\bdormant\b", re.I)),
    (Intent.REGIONAL_PERFORMANCE, re.compile(r"\bregion\w*\b.*\b(highest|best|top|revenue)\b|\bwhich region\b", re.I)),
    (
        Intent.SALES_TREND,
        re.compile(r"\b(sales|revenue)\b.*\b(decrease|decline|drop|down|fell|fall)\w*\b|\bwhy\b.*\b(sales|revenue)\b", re.I),
    ),
]


def detect_intent(question: str) -> Intent:
    for intent, pattern in _PATTERNS:
        if pattern.search(question):
            return intent
    return Intent.GENERAL
