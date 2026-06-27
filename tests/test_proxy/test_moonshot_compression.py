"""Compression integration tests for the Moonshot backend.

Verifies that the Headroom compression pipeline is applied to Moonshot
chat-completion requests when optimization is enabled.
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
    """Create a Headroom proxy with Moonshot backend and optimization enabled."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-moonshot-key")

    config = ProxyConfig(
        backend="moonshot",
        optimize=True,
        cache_enabled=False,
        rate_limit_enabled=False,
        log_requests=True,
    )
    app = create_app(config)
    return TestClient(app)


def _install_mock_handler(client: TestClient, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    """Replace the Moonshot backend HTTP client transport with a mock handler."""
    backend = client.app.state.proxy.anthropic_backend
    assert backend is not None
    assert backend.name == "moonshot"
    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))


def _large_tool_output() -> str:
    """Return a large JSON tool output that the pipeline compresses."""
    return json.dumps(
        [
            {
                "id": i,
                "name": f"Item {i}",
                "description": f"This is a detailed description for item number {i}. "
                f"It contains various attributes and metadata that are typical "
                f"of API responses. The item has a status of active and was "
                f"created on 2024-01-{(i % 28) + 1:02d}. Additional fields "
                f"include category=electronics, price={i * 10.99:.2f}, "
                f"rating={4.0 + (i % 10) / 10:.1f}, stock={i * 5}.",
                "tags": ["electronics", "sale", "featured", "new-arrival"],
                "metadata": {
                    "created_by": "system",
                    "updated_at": "2024-01-15T00:00:00Z",
                    "version": i,
                    "source": "api",
                },
            }
            for i in range(200)
        ]
    )


def test_compression_is_applied_to_long_moonshot_request(moonshot_client: TestClient) -> None:
    """A long Moonshot request with tool output is compressed before being sent upstream."""
    large_data = _large_tool_output()
    original_messages = [
        {"role": "user", "content": "What items are available?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "list_items", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_123", "content": large_data},
        {"role": "user", "content": "Summarize the first 5 items."},
    ]
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-compressed",
                "object": "chat.completion",
                "created": 1,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Summary."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
            },
        )

    _install_mock_handler(moonshot_client, handler)

    resp = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": original_messages,
            "stream": False,
        },
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 200, resp.text
    upstream_messages = captured["body"]["messages"]
    # Compression should have altered the large tool output.
    assert upstream_messages != original_messages
    # The tool output should be smaller after compression.
    upstream_tool = next(
        (m for m in upstream_messages if m.get("role") == "tool"),
        {},
    )
    assert len(upstream_tool.get("content", "")) < len(large_data)


def test_short_moonshot_request_is_not_compressed(moonshot_client: TestClient) -> None:
    """A short Moonshot request is forwarded unchanged."""
    original_messages = [{"role": "user", "content": "hi"}]
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-short",
                "object": "chat.completion",
                "created": 1,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hi!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    _install_mock_handler(moonshot_client, handler)

    resp = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2",
            "messages": original_messages,
            "stream": False,
        },
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 200, resp.text
    assert captured["body"]["messages"] == original_messages
