# Plan 01-02 Summary — Moonshot `send_openai_message` & Alias Resolution

## Status
✅ Completed

## What Changed
- Modified `headroom/backends/moonshot.py`:
  - Added `_FALLBACK_MODEL_ALIASES` static map (`kimi-latest` → `kimi-k2`).
  - Added `self._supported_models` set for explicit model support checks.
  - Implemented async `_resolve_model_alias(alias)`:
    - Resolves `kimi-latest` dynamically via `GET {base_url}/models`.
    - Caches resolved values.
    - Falls back to static map on network/auth/parse failures.
  - Updated `supports_model` to return `True` for any `kimi-*` model or supported alias.
  - Implemented `send_openai_message(body, headers)`:
    - Resolves `kimi-latest` before forwarding (without mutating original `body`).
    - POSTs to `{base_url}/chat/completions` using `httpx.AsyncClient`.
    - Uses backend profile/API key for `Authorization: Bearer <key>`; does not forward client `Authorization`.
    - Returns upstream body and status code as-is.
    - Propagates upstream errors with original status/body.
    - Maps transport errors to `502` with an OpenAI-style error body.
  - Kept `stream_message` and `stream_openai_message` as `NotImplementedError` stubs for Phase 4.

## Verification
- `python -m ruff check headroom/backends/moonshot.py` ✅ All checks passed.
- `mypy headroom/backends/moonshot.py` — not run; `mypy` is not installed in this environment.
- Manual model support check:
  ```python
  from headroom.backends.moonshot import MoonshotBackend
  b = MoonshotBackend()
  assert b.supports_model("kimi-k2") is True
  assert b.supports_model("kimi-latest") is True
  assert b.supports_model("gpt-4") is False
  ```
  ✅ Passed.
- Manual mock transport check:
  - Mocked `POST /v1/chat/completions` and `GET /v1/models`.
  - Confirmed `Authorization` header equals `Bearer test-key`.
  - Confirmed `kimi-latest` is resolved before sending upstream.
  - Confirmed response body is returned as-is. ✅ Passed.
- `python -m pytest tests/test_backends/ -q` — 3 skipped (pre-existing, async tests need `pytest-asyncio` plugin).

## Commit
- `195d4ba5` — `feat(backend): implement Moonshot send_openai_message and alias resolution`

## Next Step
Proceed to Plan 01-03: register the Moonshot backend in `headroom/backends/__init__.py`, `headroom/providers/registry.py`, update CLI help, and add tests.
