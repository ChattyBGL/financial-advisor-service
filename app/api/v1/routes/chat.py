from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import LLMDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# These are plain `def` on purpose: the Groq client is synchronous, so FastAPI
# runs them in a worker thread instead of blocking the event loop.


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, llm: LLMDep) -> ChatResponse:
    reply = llm.chat(
        body.prompt,
        system=body.system,
        history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return ChatResponse(reply=reply, model=llm.model)


@router.post("/stream")
def chat_stream(body: ChatRequest, llm: LLMDep) -> StreamingResponse:
    """Streams plain-text chunks as they arrive from Groq."""
    return StreamingResponse(
        llm.stream(
            body.prompt,
            system=body.system,
            history=[m.model_dump() for m in body.history],  # type: ignore[arg-type]
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ),
        media_type="text/plain",
    )
