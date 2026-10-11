"""Allow-listed tool registry.

Agents never call functions directly: they go through the registry, which
(1) enforces an allow-list and (2) labels every result as UNTRUSTED so the
caller knows it must be guarded before use (indirect-injection defence).
"""
from __future__ import annotations

from typing import Callable

from . import config
from .guardrails.errors import ToolNotAllowed


def news_signals(region: str) -> str:
    """Simulated news/market feed. Swap for Tavily / a news API in production."""
    return (f"Found significant volatility in {region} region. Geopolitical tensions are "
            "increasing insurance premiums for maritime transit.")


class ToolRegistry:
    def __init__(self, tools: dict[str, Callable[..., str]] | None = None):
        self._tools = dict(tools or {"news_signals": news_signals})

    def call(self, name: str, **kwargs) -> str:
        if name not in config.ALLOWED_TOOLS or name not in self._tools:
            raise ToolNotAllowed(f"Tool {name!r} is not allow-listed.", ["tool_allowlist"])
        return self._tools[name](**kwargs)   # result is UNTRUSTED - caller must guard it
