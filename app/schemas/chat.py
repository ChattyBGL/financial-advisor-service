from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    system: str | None = Field(default=None, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class ChatResponse(BaseModel):
    reply: str
    model: str
