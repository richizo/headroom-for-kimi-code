"""Unit tests for the native Moonshot/Kimi backend."""

from __future__ import annotations

import json
from collections.abc import Callable
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
