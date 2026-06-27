"""Proxy-level integration tests for the Moonshot backend.

Spins up the Headroom proxy with ``backend="moonshot"`` and intercepts the
upstream HTTP traffic by replacing the real ``MoonshotBackend`` transport.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

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


def test_moonshot_chat_completion_passthrough(moonshot_client: TestClient) -> None:
    """The proxy forwards an OpenAI chat completion request to Moonshot and returns the response."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-moonshot-1",
                "object": "chat.completion",
                "created": 1,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello from Moonshot"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "chatcmpl-moonshot-1"
    assert body["model"] == "kimi-k2"
    assert body["choices"][0]["message"]["content"] == "Hello from Moonshot"

    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["authorization"] == "Bearer test-moonshot-key"
    assert captured["body"]["model"] == "kimi-k2"
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]


def test_moonshot_resolves_kimi_latest_alias(moonshot_client: TestClient) -> None:
    """The proxy resolves kimi-latest via /v1/models before forwarding to Moonshot."""
    captured_requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        body = json.loads(request.content) if request.content else {}
        captured_requests.append({"url": url, "body": body})

        if url.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "kimi-latest", "object": "model"},
                        {"id": "kimi-k2", "object": "model"},
                    ]
                },
            )

        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-alias",
                "object": "chat.completion",
                "created": 1,
                "model": body.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-latest",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    chat_request = next(r for r in captured_requests if r["url"].endswith("/chat/completions"))
    assert chat_request["body"]["model"] == "kimi-latest"


def test_moonshot_upstream_error_passthrough(moonshot_client: TestClient) -> None:
    """Upstream errors from Moonshot are propagated to the client unchanged."""
    error_body = {
        "error": {
            "message": "invalid temperature",
            "type": "invalid_request_error",
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=error_body)

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 400
    assert response.json() == error_body
