"""Builds the message list sent to the LLM for one Copilot turn.

The LLM only ever sees: (1) a system prompt describing its role and hard
anti-hallucination rules, (2) a JSON-serialized snapshot of exactly what the
backend APIs returned for this question (`context.data` — assembled by
`copilot_service._gather_context`, never raw SQL rows), and (3) recent
conversation history. It never sees a database connection, a SQLAlchemy
model, or a SQL query — none of those exist anywhere in this module's import
graph.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.copilot.config import get_copilot_settings

if TYPE_CHECKING:
    from app.copilot.copilot_service import ChatTurn, CopilotContext

SYSTEM_PROMPT = """You are SalesPilot AI's Sales Copilot, a business intelligence assistant for a \
laboratory equipment company's sales managers.

Hard rules:
- Answer using ONLY the "Retrieved Data" JSON given to you in the user message below. Never invent \
a number, customer name, region, or percentage that is not present in that data.
- If the data needed to answer is missing, empty, or a tool call returned an "error" field, say so \
plainly rather than guessing or making something up.
- Structure every answer with exactly these labeled sections, in this order:
  Business Insight: one or two sentences stating the key finding.
  Supporting Data: a short bulleted list of the specific numbers behind that finding, pulled directly \
from the retrieved data.
  Recommended Action: one to three concrete next steps a sales manager could take today.
- Do NOT write a "Data Sources" section yourself — it is appended automatically after your answer.
- Use plain, professional business language. Avoid technical jargon such as "SHAP", "JSON", "API", \
"vector", "model version", "endpoint" — translate everything into terms a sales manager cares about.
- Currency is Indian Rupees. Format large amounts in Lakhs/Crores (e.g. "₹11.6 Lakh", "₹2.3 Cr").
"""


def build_messages(question: str, context: "CopilotContext", history: list["ChatTurn"]) -> list[dict]:
    settings = get_copilot_settings()
    context_json = json.dumps(context.data, indent=2, default=str)
    history_messages = [
        {"role": turn.role, "content": turn.content} for turn in history[-settings.max_history_turns :]
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history_messages,
        {
            "role": "user",
            "content": (
                f"Retrieved Data (from live backend APIs — this is your source of truth):\n"
                f"{context_json}\n\nQuestion: {question}"
            ),
        },
    ]
