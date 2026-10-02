"""Thin wrapper around the Groq chat completions API (synchronous client).

Usage:
    llm = get_llm_service()
    reply = llm.chat("Summarise my portfolio risk in two sentences.")

Routes that call this should be plain `def` (not `async def`) so FastAPI runs
them in a worker thread and the blocking HTTP call doesn't stall the event loop.
"""

import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import Literal, TypedDict

import groq
from groq import Groq

from app.core.config import get_settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMError(AppError):
    """Raised when the Groq call fails; mapped to an HTTP response by the app handlers."""

    status_code = 502
    code = "llm_error"


class LLMNotConfiguredError(LLMError):
    status_code = 503
    code = "llm_not_configured"


class LLMService:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        if not api_key:
            raise LLMNotConfiguredError("GROQ_API_KEY is not set")
        self.model = model
        self._client = Groq(api_key=api_key, timeout=timeout, max_retries=max_retries)

    def chat(
        self,
        prompt: str,
        *,
        system: str | None = None,
        history: list[Message] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Send a single-turn (or history-aware) chat request and return the reply text."""
        messages = self._build_messages(prompt, system=system, history=history)
        try:
            response = self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except groq.AuthenticationError as exc:
            raise LLMError("Groq authentication failed", status_code=401) from exc
        except groq.RateLimitError as exc:
            raise LLMError("Groq rate limit exceeded", status_code=429) from exc
        except groq.APIError as exc:
            logger.exception("Groq API error")
            raise LLMError(f"Groq request failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else None
        if not content:
            if choice and choice.finish_reason == "length":
                # Reasoning models (e.g. openai/gpt-oss-*) spend tokens on hidden
                # reasoning first; a small max_tokens leaves nothing for the reply.
                raise LLMError(
                    "Groq hit max_tokens before producing a reply; raise max_tokens",
                    status_code=422,
                    code="llm_max_tokens_exceeded",
                )
            raise LLMError("Groq returned an empty response")
        return content

    def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        history: list[Message] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Yield reply text chunks as they arrive."""
        messages = self._build_messages(prompt, system=system, history=history)
        try:
            stream = self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except groq.APIError as exc:
            logger.exception("Groq streaming error")
            raise LLMError(f"Groq request failed: {exc}") from exc

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _build_messages(
        prompt: str,
        *,
        system: str | None,
        history: list[Message] | None,
    ) -> list[Message]:
        messages: list[Message] = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages


@lru_cache
def get_llm_service() -> LLMService:
    settings = get_settings()
    return LLMService(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout=settings.groq_timeout_seconds,
        max_retries=settings.groq_max_retries,
    )
