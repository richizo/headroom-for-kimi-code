"""Cache integration tests for the Moonshot backend.

Verifies that the proxy's PrefixCacheTracker is updated correctly from
Moonshot OpenAI-format responses.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from headroom.proxy.server import ProxyConfig, create_app  # noqa: E402


class _MockTransport(httpx.AsyncBaseTransport):
    """Async transport that delegates request handling to a callable."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self.handler(request)


class _RecordingTracker:
    """Stub PrefixCacheTracker that records update_from_response calls."""

    def __init__(self, provider: str = "moonshot") -> None:
        self.provider = provider
        self.calls: list[dict[str, Any]] = []
        self._frozen = 0
        self._last_original: list[dict] = []
        self._last_forwarded: list[dict] = []

    def update_from_response(
        self,
        cache_read_tokens: int,
        cache_write_tokens: int,
        messages: list[dict],
        message_token_counts: list[int] | None = None,
        original_messages: list[dict] | None = None,
    ) -> None:
        self.calls.append(
            {
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
                "messages": messages,
            }
        )
        self._last_original = list(original_messages or messages)
        self._last_forwarded = list(messages)

    def get_frozen_message_count(self) -> int:
        return self._frozen

    def get_last_original_messages(self) -> list[dict]:
        return list(self._last_original)

    def get_last_forwarded_messages(self) -> list[dict]:
        return list(self._last_forwarded)


@pytest.fixture
def moonshot_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a Headroom proxy with the Moonshot backend and a mock upstream."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-moonshot-key")

    config = ProxyConfig(
        backend="moonshot",
        optimize=False,
        cache_enabled=False,
        rate_limit_enabled=False,
        log_requests=False,
    )
    app = create_app(config)
    return TestClient(app)


def _install_mock_handler(client: TestClient, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    """Replace the Moonshot backend HTTP client transport with a mock handler."""
    backend = client.app.state.proxy.anthropic_backend
    assert backend is not None
    assert backend.name == "moonshot"
    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))


def _install_tracker_stub(client: TestClient) -> _RecordingTracker:
    """Force the session_tracker_store to hand out our recording tracker."""
    tracker = _RecordingTracker(provider="moonshot")
    proxy = client.app.state.proxy
    proxy.session_tracker_store.get_or_create = MagicMock(return_value=tracker)
    return tracker


def _chat_completion_response(model: str, cache_read: int, cache_creation: int | None = None) -> dict:
    usage: dict[str, Any] = {
        "prompt_tokens": 1000,
        "completion_tokens": 20,
        "total_tokens": 1020,
    }
    if cache_creation is not None:
        usage["cache_read_input_tokens"] = cache_read
        usage["cache_creation_input_tokens"] = cache_creation
        usage["prompt_tokens_details"] = {"cached_tokens": cache_read}
    else:
        usage["prompt_tokens_details"] = {"cached_tokens": cache_read}
    return {
        "id": "chatcmpl-moonshot-cache",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi!"},
                "finish_reason": "stop",
            }
        ],
        "usage": usage,
    }


def test_moonshot_cache_read_and_creation_tokens_update_tracker(moonshot_client: TestClient) -> None:
    """Moonshot responses with Anthropic-style cache fields update the tracker."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_response("kimi-k2", 700, 100))

    _install_mock_handler(moonshot_client, handler)
    tracker = _install_tracker_stub(moonshot_client)

    resp = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 200, resp.text
    assert len(tracker.calls) == 1
    call = tracker.calls[0]
    assert call["cache_read_tokens"] == 700
    assert call["cache_write_tokens"] == 100


def test_moonshot_falls_back_to_openai_cached_tokens(moonshot_client: TestClient) -> None:
    """Moonshot responses with only OpenAI-style cached_tokens fall back and infer write."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_response("kimi-k2", 200))

    _install_mock_handler(moonshot_client, handler)
    tracker = _install_tracker_stub(moonshot_client)

    resp = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 200, resp.text
    assert len(tracker.calls) == 1
    call = tracker.calls[0]
    assert call["cache_read_tokens"] == 200
    assert call["cache_write_tokens"] == 800  # 1000 - 200
