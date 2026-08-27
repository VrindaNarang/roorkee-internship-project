from pydantic import BaseModel


class ChatTurnIn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class CopilotChatRequest(BaseModel):
    question: str
    history: list[ChatTurnIn] = []
