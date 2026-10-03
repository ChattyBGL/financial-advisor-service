"""Builds extra context for a chat prompt from named sources.

The client is resolved from `client_id` once, up front. Sources then receive
the loaded client dict (or None) rather than the id, so the context only ever
refers to the client by name.

A source is any function `(prompt, client) -> JSON-able value or None`.
Return None when the source has nothing useful to add.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from opentelemetry import trace

from app.db.session import get_db_client
from app.services.client_portfolio import load_client_portfolio
from app.services.policy import find_policy_context
from app.services.web_search import find_web_context

tracer = trace.get_tracer(__name__)

Client = dict[str, Any]
Source = Callable[[str, Client | None], Any]
ClientLoader = Callable[[int], Client | None]


@dataclass
class Context:
    data: dict[str, Any] = field(default_factory=dict)  # source name -> payload
    client_name: str | None = None


class ContextService:
    def __init__(self, sources: dict[str, Source], load_client: ClientLoader) -> None:
        self.sources = sources
        self._load_client = load_client

    def build(self, prompt: str, client_id: int | None = None) -> Context:
        """Resolve the client, run every source, keep the non-empty payloads by name.

        Recorded as a `build_context` span (a no-op unless Phoenix tracing is on)
        so the trace shows exactly what context was handed to the LLM.
        """
        with tracer.start_as_current_span("build_context") as span:
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("input.value", prompt)

            client = self._load_client(client_id) if client_id is not None else None
            client_name = client["client_name"] if client else None

            data = {}
            for name, source in self.sources.items():
                payload = source(prompt, client)
                if payload:
                    data[name] = payload

            span.set_attribute("context.client_name", client_name or "")
            span.set_attribute("context.sources", list(data))
            span.set_attribute("output.value", json.dumps(data, default=str))
            span.set_attribute("output.mime_type", "application/json")
            return Context(data=data, client_name=client_name)


@lru_cache
def get_context_service() -> ContextService:
    db = get_db_client()
    return ContextService(
        sources={
            "client_portfolio": lambda _prompt, client: client,
            "policy_context": lambda prompt, _client: find_policy_context(prompt),
            "web_context": find_web_context,
        },
        load_client=lambda client_id: load_client_portfolio(db, client_id),
    )
