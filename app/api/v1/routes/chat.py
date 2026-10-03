from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import ContextDep, LLMDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# These are plain `def` on purpose: the Groq client is synchronous, so FastAPI
# runs them in a worker thread instead of blocking the event loop.


def _system_prompt(body: ChatRequest, context: str) -> str | None:
    """Caller's system prompt, with gathered context appended when there is any."""
    if not context:
        return body.system
    return f"{body.system or ''}\n\nContext:\n{context}".strip()


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, llm: LLMDep, ctx: ContextDep) -> ChatResponse:
    context = ctx.build(body.prompt)
    reply = llm.chat(
        body.prompt,
        system=_system_prompt(body, context),
        history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return ChatResponse(reply=reply, model=llm.model)


@router.post("/stream")
def chat_stream(body: ChatRequest, llm: LLMDep, ctx: ContextDep) -> StreamingResponse:
    """Streams plain-text chunks as they arrive from Groq."""
    context = ctx.build(body.prompt)
    return StreamingResponse(
        llm.stream(
            body.prompt,
            system=_system_prompt(body, context),
            history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ),
        media_type="text/plain",
    )
