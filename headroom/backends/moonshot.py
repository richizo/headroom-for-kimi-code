"""Native Moonshot/Kimi backend for Headroom.

Forwards OpenAI-compatible chat completion requests to the Moonshot API.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import Backend, BackendResponse, StreamEvent

logger = logging.getLogger(__name__)

DEFAULT_MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MOONSHOT_TIMEOUT = 60.0


class MoonshotBackend(Backend):
    """Backend for Moonshot AI's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_MOONSHOT_BASE_URL,
        timeout: float = DEFAULT_MOONSHOT_TIMEOUT,
    ) -> None:
        """Initialize the Moonshot backend.

        Args:
            api_key: Moonshot API key. Falls back to ``MOONSHOT_API_KEY`` env var.
            base_url: Moonshot API base URL. Defaults to ``https://api.moonshot.ai/v1``.
            timeout: Upstream request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("MOONSHOT_API_KEY")
        if not self.api_key:
            raise ValueError("MOONSHOT_API_KEY is required")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._model_alias_cache: dict[str, str] = {}

        logger.info("Moonshot backend initialized (base_url=%s)", self.base_url)

    @property
    def name(self) -> str:
        """Backend name."""
        return "moonshot"

    def map_model_id(self, model: str) -> str:
        """Map model ID to Moonshot model ID.

        Alias resolution (e.g. ``kimi-latest``) happens at request time in
        ``send_openai_message``; this method returns the ID unchanged.
        """
        return model

    def supports_model(self, model: str) -> bool:
        """Return True for Moonshot/Kimi model IDs."""
        return model.startswith("kimi-")

    async def send_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> BackendResponse:
        """Send Anthropic-format message (not supported)."""
        raise NotImplementedError(
            "Moonshot backend only supports OpenAI-compatible requests; use send_openai_message"
        )

    async def stream_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> AsyncIterator[StreamEvent]:
        """Stream Anthropic-format message (not supported)."""
        raise NotImplementedError(
            "Moonshot backend only supports OpenAI-compatible requests; use stream_openai_message"
        )
        yield StreamEvent(event_type="error", data={})  # type: ignore[misc]  # pragma: no cover

    async def send_openai_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> BackendResponse:
        """Send OpenAI-format chat completion request (implemented in Plan 02)."""
        raise NotImplementedError(
            "send_openai_message is implemented in the next plan"
        )

    async def stream_openai_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> AsyncIterator[str]:
        """Stream OpenAI-format chat completion (implemented in Phase 4)."""
        raise NotImplementedError(
            "stream_openai_message is implemented in Phase 4"
        )
        yield ""  # type: ignore[misc]  # pragma: no cover

    async def close(self) -> None:
        """Close the upstream HTTP client."""
        await self._client.aclose()
