"""Native Moonshot/Kimi backend for Headroom.

Forwards OpenAI-compatible chat completion requests to the Moonshot API.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import Backend, BackendResponse, StreamEvent

logger = logging.getLogger(__name__)

DEFAULT_MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MOONSHOT_TIMEOUT = 60.0

_FALLBACK_MODEL_ALIASES: dict[str, str] = {
    "kimi-latest": "kimi-k2",
}


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
        self._supported_models: set[str] = {"kimi-k2", "kimi-latest"}

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
        return model.startswith("kimi-") or model in self._supported_models

    async def _resolve_model_alias(self, alias: str) -> str:
        """Resolve a model alias to a concrete Moonshot model ID.

        ``kimi-latest`` is resolved dynamically via the ``/v1/models`` endpoint.
        On any failure, a static fallback map is used and the result is cached.
        """
        if alias != "kimi-latest":
            return alias

        if alias in self._model_alias_cache:
            return self._model_alias_cache[alias]

        try:
            response = await self._client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()

            resolved: str | None = None
            data = payload.get("data", []) if isinstance(payload, dict) else []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                model_id = entry.get("id")
                if model_id == alias:
                    resolved = alias
                    break
                if isinstance(model_id, str) and model_id.endswith("kimi-latest"):
                    resolved = model_id
                    break

            if not resolved:
                resolved = _FALLBACK_MODEL_ALIASES.get(alias, alias)
                logger.warning(
                    "Moonshot alias resolution fell back to %s for %s",
                    resolved,
                    alias,
                )

            self._model_alias_cache[alias] = resolved
            return resolved

        except Exception as exc:
            resolved = _FALLBACK_MODEL_ALIASES.get(alias, alias)
            logger.warning(
                "Moonshot alias resolution failed (%s); using fallback %s",
                exc,
                resolved,
            )
            self._model_alias_cache[alias] = resolved
            return resolved

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
        """Stream Anthropic-format message (not supported; Phase 4)."""
        raise NotImplementedError(
            "Moonshot backend only supports OpenAI-compatible requests; use stream_openai_message"
        )
        yield StreamEvent(event_type="error", data={})  # type: ignore[misc]  # pragma: no cover

    async def send_openai_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> BackendResponse:
        """Send an OpenAI-format chat completion request to Moonshot.

        Resolves model aliases such as ``kimi-latest`` before forwarding the
        request unchanged to the Moonshot API. The response body and status
        code are returned as-is.
        """
        model = body.get("model", "")
        request_body = body
        if model == "kimi-latest":
            resolved = await self._resolve_model_alias(model)
            request_body = {**body, "model": resolved}

        upstream_headers: dict[str, str] = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=request_body,
                headers=upstream_headers,
                timeout=self.timeout,
            )

            try:
                response_body = response.json()
            except Exception:
                response_body = {"error": {"message": response.text, "type": "api_error"}}

            if response.status_code >= 400:
                logger.error(
                    "Moonshot upstream error: status=%d body=%s",
                    response.status_code,
                    response.text[:200],
                )
                return BackendResponse(
                    body=response_body,
                    status_code=response.status_code,
                    headers={"content-type": "application/json"},
                    error=response.text,
                )

            return BackendResponse(
                body=response_body,
                status_code=response.status_code,
                headers={"content-type": "application/json"},
            )

        except httpx.HTTPError as exc:
            logger.error("Moonshot request failed: %s", exc)
            return BackendResponse(
                body={"error": {"message": str(exc), "type": "api_error"}},
                status_code=502,
                headers={"content-type": "application/json"},
                error=str(exc),
            )

    async def stream_openai_message(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> AsyncIterator[str]:
        """Stream an OpenAI-format chat completion from Moonshot.

        Resolves model aliases such as ``kimi-latest`` before forwarding the
        request with ``stream: true`` to the Moonshot API. Yields SSE events
        as received, preserving provider-specific fields like
        ``delta.reasoning_content``.
        """
        model = body.get("model", "")
        request_body = body
        if model == "kimi-latest":
            resolved = await self._resolve_model_alias(model)
            request_body = {**body, "model": resolved}

        upstream_headers: dict[str, str] = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=request_body,
                headers=upstream_headers,
                timeout=self.timeout,
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    try:
                        response_body = response.json()
                    except Exception:
                        response_body = {
                            "error": {"message": response.text, "type": "api_error"}
                        }
                    logger.error(
                        "Moonshot upstream streaming error: status=%d body=%s",
                        response.status_code,
                        str(response_body)[:200],
                    )
                    yield f"data: {json.dumps(response_body)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                event_lines: list[str] = []
                async for line in response.aiter_lines():
                    if line == "":
                        if event_lines:
                            event = "\n".join(event_lines)
                            yield f"{event}\n\n"
                            if event == "data: [DONE]":
                                return
                            event_lines = []
                    else:
                        event_lines.append(line)

                if event_lines:
                    yield "\n".join(event_lines) + "\n\n"

        except httpx.HTTPError as exc:
            logger.error("Moonshot streaming request failed: %s", exc)
            error_body = {"error": {"message": str(exc), "type": "api_error"}}
            yield f"data: {json.dumps(error_body)}\n\n"

        yield "data: [DONE]\n\n"

    async def close(self) -> None:
        """Close the upstream HTTP client."""
        await self._client.aclose()
