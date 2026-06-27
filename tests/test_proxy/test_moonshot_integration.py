"""Proxy-level integration tests for the Moonshot backend.

Spins up the Headroom proxy with ``backend="moonshot"`` and intercepts the
upstream HTTP traffic by replacing the real ``MoonshotBackend`` transport.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
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


def test_moonshot_thinking_enabled_returns_reasoning_content(moonshot_client: TestClient) -> None:
    """When thinking is enabled, reasoning_content is preserved end-to-end."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-thinking-proxy",
                "object": "chat.completion",
                "created": 1700000000,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "A resposta final é 42.",
                            "reasoning_content": "Preciso somar 40 + 2. 40 + 2 = 42.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25,
                },
            },
        )

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": False,
            "thinking": {"type": "enabled", "keep": "all"},
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "A resposta final é 42."
    assert body["choices"][0]["message"]["reasoning_content"] == "Preciso somar 40 + 2. 40 + 2 = 42."
    assert captured["body"]["thinking"] == {"type": "enabled", "keep": "all"}


def test_moonshot_thinking_disabled_does_not_return_reasoning_content(
    moonshot_client: TestClient,
) -> None:
    """When thinking is disabled, reasoning_content is absent from the response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-instant-proxy",
                "object": "chat.completion",
                "created": 1700000001,
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "A resposta final é 42.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": False,
            "thinking": {"type": "disabled"},
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    message = response.json()["choices"][0]["message"]
    assert message["content"] == "A resposta final é 42."
    assert "reasoning_content" not in message


def test_moonshot_instant_mode_no_thinking_parameter(moonshot_client: TestClient) -> None:
    """Instant mode works when no thinking parameter is sent by the client."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-instant-proxy-2",
                "object": "chat.completion",
                "created": 1700000002,
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "42",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 1,
                    "total_tokens": 9,
                },
            },
        )

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": False,
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    message = response.json()["choices"][0]["message"]
    assert message["content"] == "42"
    assert "reasoning_content" not in message
    assert "thinking" not in captured["body"]


def _read_streaming_fixture(name: str) -> str:
    """Load an SSE fixture for streaming tests."""
    return (Path(__file__).parent.parent / "fixtures" / "moonshot" / name).read_text()


def _parse_sse_stream(response: Any) -> list[dict[str, Any]]:
    """Parse a raw SSE response into a list of data payloads."""
    events: list[dict[str, Any]] = []
    buffer = ""
    for line in response.iter_text():
        buffer += line
        while "\n\n" in buffer:
            event, buffer = buffer.split("\n\n", 1)
            event = event.strip()
            if event.startswith("data: "):
                payload = event[6:]
                if payload == "[DONE]":
                    events.append({"done": True})
                else:
                    events.append(json.loads(payload))
    return events


def test_moonshot_streaming_thinking_end_to_end(moonshot_client: TestClient) -> None:
    """Streaming request with thinking returns reasoning_content in SSE chunks."""
    fixture = _read_streaming_fixture("streaming_thinking.txt")
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(200, text=fixture)

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
            "thinking": {"type": "enabled"},
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    events = _parse_sse_stream(response)

    # Last meaningful event before [DONE] should contain the final content
    reasoning_parts = []
    content_parts = []
    for event in events:
        if event.get("done"):
            continue
        delta = event.get("choices", [{}])[0].get("delta", {})
        if "reasoning_content" in delta:
            reasoning_parts.append(delta["reasoning_content"])
        if "content" in delta:
            content_parts.append(delta["content"])

    assert "".join(reasoning_parts) == "Preciso somar 40 + 2. 40 + 2 = 42."
    assert "".join(content_parts) == "A resposta final é 42."
    assert captured["body"]["thinking"] == {"type": "enabled"}


def test_moonshot_streaming_instant_mode(moonshot_client: TestClient) -> None:
    """Streaming request without thinking does not emit reasoning_content."""
    fixture = _read_streaming_fixture("streaming_instant.txt")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    events = _parse_sse_stream(response)

    for event in events:
        if event.get("done"):
            continue
        delta = event.get("choices", [{}])[0].get("delta", {})
        assert "reasoning_content" not in delta


def test_moonshot_streaming_usage_chunk(moonshot_client: TestClient) -> None:
    """Streaming usage chunk is forwarded when stream_options.include_usage is set."""
    fixture = _read_streaming_fixture("streaming_usage.txt")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    _install_mock_handler(moonshot_client, handler)

    response = moonshot_client.post(
        "/v1/chat/completions",
        json={
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
            "stream_options": {"include_usage": True},
        },
        headers={"Authorization": "Bearer client-key"},
    )

    assert response.status_code == 200, response.text
    events = _parse_sse_stream(response)

    usage_event = next(e for e in events if "usage" in e)
    assert usage_event["usage"] == {"prompt_tokens": 8, "completion_tokens": 1, "total_tokens": 9}
