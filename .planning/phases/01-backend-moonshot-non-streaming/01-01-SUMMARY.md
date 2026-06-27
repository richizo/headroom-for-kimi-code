---
phase: 01-backend-moonshot-non-streaming
plan: 01
status: complete
completed: 2026-06-27
---

# Plan 01-01 Summary: MoonshotBackend Skeleton

## What Was Done

Created `headroom/backends/moonshot.py` with the initial `MoonshotBackend` class:

- Inherits from `Backend` and imports `BackendResponse`/`StreamEvent` from `.base`
- Constructor accepts `api_key`, `base_url`, `timeout`
- `api_key` falls back to `MOONSHOT_API_KEY` env var; raises `ValueError` if missing
- Default `base_url` is `https://api.moonshot.ai/v1`
- Uses `httpx.AsyncClient` for upstream requests
- `name` property returns `"moonshot"`
- `supports_model("kimi-*")` returns `True`
- `send_message`/`stream_message` raise `NotImplementedError` (Moonshot is OpenAI-compatible)
- `send_openai_message`/`stream_openai_message` raise `NotImplementedError` (implemented in later plans)
- `close()` closes the httpx client

## Verification

- `python -c "from headroom.backends.moonshot import MoonshotBackend"` succeeds
- Instantiation with `MOONSHOT_API_KEY=test` succeeds
- Instantiation without API key raises `ValueError`
- `ruff check headroom/backends/moonshot.py` passes
- `mypy` not available in this environment (module not installed)

## Files Modified

- `headroom/backends/moonshot.py` (created)

## Next Plan

Plan 01-02: Implement `send_openai_message`, model mapping, and alias resolution.
