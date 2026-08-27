import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.copilot.copilot_service import ChatTurn, answer
from app.schemas.copilot import CopilotChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
def copilot_chat(request: CopilotChatRequest, http_request: Request) -> StreamingResponse:
    """Streams the Sales Copilot's answer as plain text chunks.

    Grounded entirely in this backend's own REST APIs (analytics, predictions,
    health scores, SHAP explanations, recommendations) — never a direct
    database query. See `app/copilot/copilot_service.py` for the pipeline:
    intent detection -> tool calls -> context assembly -> LLM -> formatted
    answer with a verified data-sources footer.

    This endpoint is itself behind `get_current_user` (see `api.py`'s
    protected router), so `http_request` always carries a valid bearer token
    by the time we get here — it's forwarded as-is to every internal tool
    call the Copilot makes, so those calls run with the asking user's own
    permissions rather than some elevated service account.
    """
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in request.history]
    auth_header = http_request.headers.get("authorization")

    async def _stream():
        async for chunk in answer(request.question, history, auth_header):
            yield chunk

    return StreamingResponse(_stream(), media_type="text/plain; charset=utf-8")
