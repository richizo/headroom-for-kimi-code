"""Telemetry integration tests for the Moonshot backend.

Verifies that Moonshot requests are captured in request logs and stats.
"""

from __future__ import annotations

from collections.abc import Callable

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


@pytest.fixture
def moonshot_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a Headroom proxy with the Moonshot backend and request logging enabled."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-moonshot-key")

    config = ProxyConfig(
        backend="moonshot",
        optimize=False,
        cache_enabled=False,
        rate_limit_enabled=False,
        log_requests=True,
        log_full_messages=True,
    )
    app = create_app(config)
    return TestClient(app)


def _install_mock_handler(client: TestClient, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    """Replace the Moonshot backend HTTP client transport with a mock handler."""
    backend = client.app.state.proxy.anthropic_backend
    assert backend is not None
    assert backend.name == "moonshot"
    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))


def _make_response(model: str, prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "id": "chatcmpl-telemetry",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def test_moonshot_request_logs_provider_and_tokens(moonshot_client: TestClient) -> None:
    """A Moonshot request is recorded in the request logger with provider and tokens."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_response("kimi-k2", 50, 10))

    _install_mock_handler(moonshot_client, handler)

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
    proxy = moonshot_client.app.state.proxy
    logger = proxy.logger
    assert logger is not None
    recent = logger.get_recent_with_messages(1)
    assert len(recent) == 1
    entry = recent[0]
    assert entry["provider"] == "moonshot"
    assert entry["model"] == "kimi-k2"
    assert entry["output_tokens"] == 10


def test_moonshot_appears_in_stats(moonshot_client: TestClient) -> None:
    """Moonshot requests are reflected in the /stats endpoint."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_response("kimi-k2", 30, 5))

    _install_mock_handler(moonshot_client, handler)

    moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer test-key"},
    )

    stats_resp = moonshot_client.get("/stats")
    assert stats_resp.status_code == 200, stats_resp.text
    stats = stats_resp.json()
    # Aggregate request counters always include provider breakdown.
    assert stats["requests"]["by_provider"].get("moonshot") == 1
