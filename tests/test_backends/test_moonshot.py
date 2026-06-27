"""Unit tests for the native Moonshot/Kimi backend."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from headroom.backends.base import BackendResponse
from headroom.backends.moonshot import DEFAULT_MOONSHOT_BASE_URL, MoonshotBackend


class _MockTransport(httpx.AsyncBaseTransport):
    """Simple async transport that delegates to a handler function."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self.handler(request)


@pytest.fixture
def backend() -> MoonshotBackend:
    return MoonshotBackend(api_key="test-key")


def test_name(backend: MoonshotBackend) -> None:
    assert backend.name == "moonshot"


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MOONSHOT_API_KEY is required"):
        MoonshotBackend()


def test_api_key_from_argument() -> None:
    backend = MoonshotBackend(api_key="arg-key")
    assert backend.api_key == "arg-key"


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOONSHOT_API_KEY", "env-key")
    backend = MoonshotBackend()
    assert backend.api_key == "env-key"


def test_default_base_url() -> None:
    backend = MoonshotBackend(api_key="test-key")
    assert backend.base_url == DEFAULT_MOONSHOT_BASE_URL


def test_custom_base_url() -> None:
    backend = MoonshotBackend(api_key="test-key", base_url="https://api.moonshot.cn/v1/")
    assert backend.base_url == "https://api.moonshot.cn/v1"


@pytest.mark.parametrize(
    "model",
    [
        "kimi-k2",
        "kimi-latest",
        "kimi-k2-0711-preview",
    ],
)
def test_supports_model_kimi(backend: MoonshotBackend, model: str) -> None:
    assert backend.supports_model(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "gpt-4",
        "claude-3-opus",
        "",
    ],
)
def test_supports_model_rejects_others(backend: MoonshotBackend, model: str) -> None:
    assert backend.supports_model(model) is False


def test_map_model_id_passes_through(backend: MoonshotBackend) -> None:
    assert backend.map_model_id("kimi-k2") == "kimi-k2"
    assert backend.map_model_id("kimi-latest") == "kimi-latest"


@pytest.mark.asyncio
async def test_send_openai_message_uses_profile_api_key(backend: MoonshotBackend) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "hello"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message(
        {"model": "kimi-k2", "messages": []},
        {"Authorization": "Bearer client-key", "x-api-key": "client-key"},
    )

    assert isinstance(response, BackendResponse)
    assert response.status_code == 200
    assert response.body["id"] == "chatcmpl-test"
    assert captured["headers"]["authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "kimi-k2"


@pytest.mark.asyncio
async def test_send_openai_message_resolves_kimi_latest() -> None:
    backend = MoonshotBackend(api_key="test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [{"id": "kimi-latest", "object": "model"}]},
            )
        body = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-alias",
                "object": "chat.completion",
                "created": 1,
                "model": body.get("model"),
                "choices": [],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            },
        )

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message({"model": "kimi-latest", "messages": []}, {})

    assert response.status_code == 200
    assert response.body["model"] == "kimi-latest"


@pytest.mark.asyncio
async def test_send_openai_message_passthrough_error(backend: MoonshotBackend) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "invalid temperature", "type": "invalid_request_error"}},
        )

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message(
        {"model": "kimi-k2", "messages": []},
        {},
    )

    assert response.status_code == 400
    assert response.body == {"error": {"message": "invalid temperature", "type": "invalid_request_error"}}
    assert response.error is not None


@pytest.mark.asyncio
async def test_send_openai_message_transport_error(backend: MoonshotBackend) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message({"model": "kimi-k2", "messages": []}, {})

    assert response.status_code == 502
    assert response.body["error"]["type"] == "api_error"
    assert "connection refused" in response.body["error"]["message"]


@pytest.mark.asyncio
async def test_send_openai_message_thinking_enabled_returns_reasoning_content(
    backend: MoonshotBackend,
) -> None:
    """When thinking is enabled, reasoning_content is preserved in the response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-thinking-001",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "kimi-k2.6",
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

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "thinking": {"type": "enabled", "keep": "all"},
        },
        {},
    )

    assert response.status_code == 200
    message = response.body["choices"][0]["message"]
    assert message["content"] == "A resposta final é 42."
    assert message["reasoning_content"] == "Preciso somar 40 + 2. 40 + 2 = 42."


@pytest.mark.asyncio
async def test_send_openai_message_thinking_disabled_does_not_return_reasoning_content(
    backend: MoonshotBackend,
) -> None:
    """When thinking is explicitly disabled, reasoning_content is absent."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-instant-001",
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

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "thinking": {"type": "disabled"},
        },
        {},
    )

    assert response.status_code == 200
    message = response.body["choices"][0]["message"]
    assert message["content"] == "A resposta final é 42."
    assert "reasoning_content" not in message


@pytest.mark.asyncio
async def test_send_openai_message_instant_mode_no_thinking_parameter(
    backend: MoonshotBackend,
) -> None:
    """Instant mode works when no thinking parameter is sent."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-instant-002",
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

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    response = await backend.send_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
        },
        {},
    )

    assert response.status_code == 200
    message = response.body["choices"][0]["message"]
    assert message["content"] == "42"
    assert "reasoning_content" not in message


@pytest.mark.asyncio
async def test_send_openai_message_thinking_parameter_forwarded_to_upstream(
    backend: MoonshotBackend,
) -> None:
    """The thinking object must reach the upstream Moonshot API unchanged."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-thinking-002",
                "object": "chat.completion",
                "created": 1700000003,
                "model": captured["body"].get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "ok",
                            "reasoning_content": "chain-of-thought",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    await backend.send_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "hi"}],
            "thinking": {"type": "enabled", "keep": "all"},
        },
        {},
    )

    assert captured["body"]["thinking"] == {"type": "enabled", "keep": "all"}


@pytest.mark.asyncio
async def test_stream_openai_message_yields_sse_chunks(backend: MoonshotBackend) -> None:
    """Streaming yields each upstream SSE event as a separate string."""
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_thinking.txt").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
        },
        {},
    )]

    assert len(chunks) == 7
    assert all(chunk.startswith("data: ") for chunk in chunks)
    assert chunks[-1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_stream_openai_message_preserves_reasoning_content(backend: MoonshotBackend) -> None:
    """Streaming preserves delta.reasoning_content from Moonshot."""
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_thinking.txt").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
            "thinking": {"type": "enabled"},
        },
        {},
    )]

    reasoning_parts = []
    for chunk in chunks:
        if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
            data = json.loads(chunk[6:].strip())
            delta = data["choices"][0].get("delta", {})
            if "reasoning_content" in delta:
                reasoning_parts.append(delta["reasoning_content"])

    assert "".join(reasoning_parts) == "Preciso somar 40 + 2. 40 + 2 = 42."


@pytest.mark.asyncio
async def test_stream_openai_message_instant_mode_no_reasoning(backend: MoonshotBackend) -> None:
    """Streaming without thinking does not contain reasoning_content deltas."""
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_instant.txt").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
        },
        {},
    )]

    assert chunks[-1] == "data: [DONE]\n\n"
    for chunk in chunks:
        if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
            data = json.loads(chunk[6:].strip())
            delta = data["choices"][0].get("delta", {})
            assert "reasoning_content" not in delta


@pytest.mark.asyncio
async def test_stream_openai_message_usage_chunk(backend: MoonshotBackend) -> None:
    """Streaming usage chunk is forwarded when stream_options.include_usage is set."""
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_usage.txt").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
            "stream": True,
            "stream_options": {"include_usage": True},
        },
        {},
    )]

    assert chunks[-1] == "data: [DONE]\n\n"
    usage_chunk = json.loads(chunks[-2][6:].strip())
    assert usage_chunk["usage"] == {"prompt_tokens": 8, "completion_tokens": 1, "total_tokens": 9}


@pytest.mark.asyncio
async def test_stream_openai_message_forwards_thinking_parameter(backend: MoonshotBackend) -> None:
    """The thinking object reaches the upstream on streaming requests."""
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_instant.txt").read_text()
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    _ = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
            "thinking": {"type": "enabled", "keep": "all"},
        },
        {},
    )]

    assert captured["body"]["thinking"] == {"type": "enabled", "keep": "all"}


@pytest.mark.asyncio
async def test_stream_openai_message_handles_upstream_error(backend: MoonshotBackend) -> None:
    """Upstream errors on the streaming path are emitted as SSE error events."""
    error_body = {"error": {"message": "invalid temperature", "type": "invalid_request_error"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=error_body)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
        {},
    )]

    assert len(chunks) == 2
    assert json.loads(chunks[0][6:].strip()) == error_body
    assert chunks[1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_stream_openai_message_resolves_kimi_latest_alias() -> None:
    """kimi-latest is resolved before the streaming request is forwarded."""
    backend = MoonshotBackend(api_key="test-key")
    fixture = (Path(__file__).parent.parent / "fixtures" / "moonshot" / "streaming_instant.txt").read_text()
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [{"id": "kimi-latest", "object": "model"}]},
            )
        captured["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(200, text=fixture)

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    _ = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-latest",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
        {},
    )]

    assert captured["body"]["model"] == "kimi-latest"


@pytest.mark.asyncio
async def test_stream_openai_message_transport_error(backend: MoonshotBackend) -> None:
    """Transport errors on the streaming path are emitted as SSE error events."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    backend._client = httpx.AsyncClient(transport=_MockTransport(handler))
    chunks = [chunk async for chunk in backend.stream_openai_message(
        {
            "model": "kimi-k2.6",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
        {},
    )]

    assert len(chunks) == 2
    error = json.loads(chunks[0][6:].strip())
    assert error["error"]["type"] == "api_error"
    assert "connection refused" in error["error"]["message"]
    assert chunks[1] == "data: [DONE]\n\n"
