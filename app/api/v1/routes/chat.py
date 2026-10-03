import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import ContextDep, LLMDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# These are plain `def` on purpose: the Groq client is synchronous, so FastAPI
# runs them in a worker thread instead of blocking the event loop.


def _system_prompt(body: ChatRequest, data: dict[str, Any]) -> str | None:
    """Caller's system prompt, with gathered context appended as JSON when there is any."""
    if not data:
        return body.system
    block = json.dumps(data, indent=2, default=str)
    return f"{body.system or ''}\n\nContext (JSON):\n{block}".strip()


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, llm: LLMDep, ctx: ContextDep) -> ChatResponse:
    context = ctx.build(body.prompt, client_id=body.client_id)
    reply = llm.chat(
        body.prompt,
        system=_system_prompt(body, context.data),
        history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return ChatResponse(reply=reply, model=llm.model, client_name=context.client_name)


@router.post("/stream")
def chat_stream(body: ChatRequest, llm: LLMDep, ctx: ContextDep) -> StreamingResponse:
    """Streams plain-text chunks as they arrive from Groq."""
    context = ctx.build(body.prompt, client_id=body.client_id)
    return StreamingResponse(
        llm.stream(
            body.prompt,
            system=_system_prompt(body, context.data),
            history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ),
        media_type="text/plain",
    )
