"""Arize Phoenix tracing (OpenTelemetry).

When PHOENIX_ENABLED=true, every Groq chat completion is recorded as an LLM
span (messages, reply, model, token usage) and the context build is recorded
as its parent span. Run a local server with `phoenix serve` and open
http://localhost:6006 to view traces.
"""

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


def configure_tracing(settings: Settings) -> bool:
    """Set up the Phoenix exporter and Groq auto-instrumentation. Returns True if enabled."""
    if not settings.phoenix_enabled:
        return False

    from openinference.instrumentation.groq import GroqInstrumentor
    from phoenix.otel import register

    tracer_provider = register(
        project_name=settings.phoenix_project,
        endpoint=settings.phoenix_collector_endpoint,
        batch=True,
        set_global_tracer_provider=True,
    )
    GroqInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info(
        "Phoenix tracing enabled project=%s endpoint=%s",
        settings.phoenix_project,
        settings.phoenix_collector_endpoint,
    )
    return True
