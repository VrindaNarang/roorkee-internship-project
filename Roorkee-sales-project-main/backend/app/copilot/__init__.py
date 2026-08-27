# AI Sales Copilot (see PROJECT_SPEC.md Milestone 10).
#
# A business-intelligence chat assistant embedded in the Analytics page — NOT
# a separate AI Assistant page, NOT RAG/FAISS/a vector database. Every answer
# is grounded in live data pulled from this backend's own REST API (never a
# direct database query), then handed to a free OpenAI-compatible LLM
# (Groq / OpenRouter / Ollama, in that preference order) purely to phrase the
# answer in business language — the LLM never sees a SQL row it wasn't
# explicitly given.
#
# config.py             - LLM provider selection/credentials, tunables
# llm_provider.py        - abstraction over any OpenAI-compatible chat API
# tool_executor.py       - calls this backend's own REST endpoints (in-process, no DB access)
# intent_router.py       - deterministic keyword-based intent detection (no LLM function-calling)
# prompt_builder.py      - builds the message list sent to the LLM from retrieved data
# response_formatter.py  - appends a verified (non-hallucinated) Data Sources footer
# copilot_service.py     - orchestrates one chat turn end-to-end; the only public entrypoint
