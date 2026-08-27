"""Post-processes the LLM's answer: appends a deterministic "Data Sources"
footer built from the actual backend endpoints `tool_executor` called for
this turn — never from what the LLM itself claims. This is a real
anti-hallucination guardrail, not cosmetic: the LLM is explicitly told not to
write its own sources section (see `prompt_builder.SYSTEM_PROMPT`), and this
module supplies the one and only source list, which is guaranteed to match
what was actually retrieved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.copilot.copilot_service import CopilotContext


def source_footer(context: "CopilotContext") -> str:
    if not context.sources:
        return ""
    bullet_list = "\n".join(f"- {source}" for source in context.sources)
    return f"\n\nData Sources:\n{bullet_list}"


def has_data_error(context: "CopilotContext") -> bool:
    """True if any retrieved-data entry is a failed tool call — used only for
    logging/observability, not to block the answer (the LLM is instructed to
    surface missing data honestly instead).
    """
    return any(isinstance(value, dict) and "error" in value for value in context.data.values())
