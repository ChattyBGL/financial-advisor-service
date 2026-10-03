"""Context source: top web search results for the prompt, via DuckDuckGo (ddgs).

The query is the prompt plus the client's holding tickers, so results lean
towards what the client actually owns. Any failure (network, rate limit)
returns an empty list so chat keeps working.
"""

import logging
from typing import Any

from ddgs import DDGS

logger = logging.getLogger(__name__)

MAX_RESULTS = 3
TIMEOUT_SECONDS = 10


def build_query(prompt: str, client: dict[str, Any] | None) -> str:
    """Prompt text followed by the client's distinct tickers, if any."""
    tickers: list[str] = []
    for portfolio in (client or {}).get("portfolios", []):
        for holding in portfolio.get("holdings", []):
            if holding["ticker"] not in tickers:
                tickers.append(holding["ticker"])
    return " ".join([prompt.strip(), *tickers]).strip()


def find_web_context(prompt: str, client: dict[str, Any] | None) -> list[dict[str, str]]:
    """Up to MAX_RESULTS results as {title, url, snippet}; [] on no results or error."""
    query = build_query(prompt, client)
    if not query:
        return []
    try:
        results = DDGS(timeout=TIMEOUT_SECONDS).text(query, max_results=MAX_RESULTS) or []
    except Exception as exc:  # noqa: BLE001 - search is best-effort
        logger.warning("Web search failed for %r: %s", query, exc)
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in results
    ]
