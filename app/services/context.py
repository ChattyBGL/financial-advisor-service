"""Builds extra context for a chat prompt from a list of sources.

A source is any function that takes the user's prompt and returns a string.
Return "" when the source has nothing useful to add.
"""

from collections.abc import Callable
from functools import lru_cache

Source = Callable[[str], str]


class ContextService:
    def __init__(self, sources: list[Source]) -> None:
        self.sources = sources

    def build(self, prompt: str) -> str:
        """Run every source and join the non-empty results."""
        parts = [text for source in self.sources if (text := source(prompt).strip())]
        return "\n\n".join(parts)


@lru_cache
def get_context_service() -> ContextService:
    return ContextService(sources=[])
