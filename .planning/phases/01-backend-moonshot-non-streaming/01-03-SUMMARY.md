# Plan 01-03 Summary — Register MoonshotBackend and Add Tests

## Status
✅ Completed

## What Changed
- Modified `headroom/backends/__init__.py`:
  - Imports and exports `MoonshotBackend`.
  - Updated module docstring to mention Moonshot support.
- Modified `headroom/providers/registry.py`:
  - Added `_load_moonshot_backend` lazy loader.
  - Added `moonshot_backend_cls` parameter to `create_proxy_backend`.
  - Added `backend == "moonshot"` branch that instantiates `MoonshotBackend` from `MOONSHOT_API_KEY` / `MOONSHOT_BASE_URL` env vars.
  - Updated `format_backend_status` to return `"Moonshot"` for the moonshot backend.
- Modified `headroom/cli/proxy.py`:
  - Added `'moonshot' (Moonshot/Kimi)` to the `--backend` help text.
- Created `tests/test_backends/test_moonshot.py`:
  - `test_name`
  - `test_requires_api_key`
  - `test_api_key_from_argument`
  - `test_api_key_from_env`
  - `test_default_base_url`
  - `test_custom_base_url`
  - `test_supports_model_kimi` (parametrized)
  - `test_supports_model_rejects_others` (parametrized)
  - `test_map_model_id_passes_through`
  - `test_send_openai_message_uses_profile_api_key`
  - `test_send_openai_message_resolves_kimi_latest`
  - `test_send_openai_message_passthrough_error`
  - `test_send_openai_message_transport_error`

## Verification
- `python -c "from headroom.backends import MoonshotBackend"` ✅
- `MOONSHOT_API_KEY=test python -c "from headroom.providers.registry import create_proxy_backend; ... create_proxy_backend(backend='moonshot', ...)"` ✅ prints `moonshot`
- `python -m headroom.cli proxy --help | grep -i moonshot` ✅ mentions moonshot
- `python -m pytest tests/test_backends/test_moonshot.py -v`:
  - In the base environment, async tests were skipped because `pytest-asyncio` is not installed.
  - In a temporary venv with `pytest-asyncio` installed (`/tmp/headroom-moonshot-venv`), all **17 tests passed**.
- `python -m ruff check headroom/backends/moonshot.py headroom/backends/__init__.py headroom/providers/registry.py headroom/cli/proxy.py tests/test_backends/test_moonshot.py` ✅ All checks passed.
- `mypy` — not run; `mypy` is not installed in this environment.

## Commits
- `486a6449` — `feat(backend): register MoonshotBackend and add unit tests`

## Phase 1 Status
All three plans of Phase 1 are complete:
- Plan 01-01: Native `MoonshotBackend` skeleton
- Plan 01-02: `send_openai_message`, alias resolution, error passthrough
- Plan 01-03: Backend registration, CLI help, unit tests

## Next Step
Phase 2: validate cache, compression, and telemetry integration for the Moonshot backend.
