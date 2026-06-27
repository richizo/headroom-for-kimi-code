# Technology Stack

**Analysis Date:** 2026-06-27

## Languages

**Primary:**
- Python 3.10+ - All application logic, CLI, proxy server, compression pipelines, integrations (`headroom/`, `tests/`)
- Rust 1.80+ / pinned toolchain 1.95.0 - Performance-critical compression core, native reverse proxy, PyO3 extension (`crates/`)

**Secondary:**
- TypeScript / JavaScript - TypeScript SDK, OpenClaw/OpenCode plugins, docs site (`sdk/typescript/`, `plugins/`, `docs/`)
- TOML, YAML, JSON, Markdown - Configuration, CI, docs, package manifests
- Shell / Bash - Installer scripts, e2e harnesses, git hooks (`scripts/`, `e2e/`)

## Runtime

**Environment:**
- CPython 3.10–3.14 (supported, `requires-python = ">=3.10"` in `pyproject.toml`)
- Rust toolchain pinned to 1.95.0 (`rust-toolchain.toml`)
- Node.js 20+ for SDK/plugin/docs builds (`docs/package.json`, `.github/workflows/release.yml`)

**Package Manager:**
- Python: `uv` 0.11.18 for Docker builds; `pip` for general install; lockfile `uv.lock` present
- Rust: `cargo` with workspace resolver "2"; lockfile `Cargo.lock` present
- Node.js: `npm` (package-lock.json in `docs/`, `sdk/typescript/`, `plugins/openclaw/`)

## Frameworks

**Core:**
- FastAPI 0.100+ + Uvicorn 0.23+ - Headroom optimization proxy server (`headroom/proxy/server.py`, `headroom/cli/proxy.py`)
- Click 8.1+ - CLI framework (`headroom/cli/`)
- Pydantic 2.0+ - Config and data models (`headroom/config.py`, `headroom/proxy/models.py`)
- PyO3 0.24+ - Rust extension bindings for Python (`crates/headroom-py/`)
- Maturin 1.5+ - Builds unified Python wheel containing Python source + compiled `_core.so`

**Web/Proxy (Rust):**
- axum 0.7 + tower 0.5 + tokio 1.x - Native Rust reverse proxy (`crates/headroom-proxy/`)
- reqwest 0.12 + tokio-tungstenite 0.24 - Upstream HTTP and WebSocket forwarding

**Testing:**
- pytest 7+ (with pytest-cov, pytest-asyncio, pytest-split) - Python tests (`tests/`)
- Vitest 4.1.5+ - TypeScript SDK/plugin tests
- cargo test / criterion - Rust unit and benchmark tests
- Playwright - Dashboard UI tests (`tests/test_dashboard_*_playwright.py`)
- Wiremock 0.6 - Rust proxy test mocking

**Build/Dev:**
- tsup 8+ - TypeScript SDK/plugin bundling
- Next.js 16.2.6 + React 19.2.4 + Tailwind CSS 4.2.2 + Fumadocs 16.10.3 - Documentation site (`docs/`)
- ruff 0.15.17+ / mypy 1.20.2+ - Python linting and type checking
- cargo fmt / cargo clippy - Rust formatting and linting
- pre-commit - Git hooks (ruff, mypy, commitlint)

## Key Dependencies

**Critical:**
- `tiktoken` 0.5+ / `tiktoken-rs` 0.11 - Token counting for OpenAI-style models
- `pydantic` 2.0+ - Configuration and request/response models
- `click` 8.1+ - CLI command structure
- `fastapi` / `uvicorn` - Proxy HTTP server
- `httpx` 0.24+ (with HTTP/2) - Async upstream HTTP client
- `openai` 2.14+ / `anthropic` 0.18+ - SDK adapters and evals
- `litellm` 1.86.2+ - Universal model registry, pricing, and provider routing (lazy-loaded)
- `transformers` 4.30+ / `torch` 2.0+ / `onnxruntime` 1.16+ - ML-based compression (Kompress) and embeddings
- `sentence-transformers` 2.2+ / `fastembed` 0.4+ - Semantic relevance scoring and memory embeddings

**Infrastructure:**
- `websockets` 13.0+ - WebSocket proxy for `/v1/responses` (Codex gpt-5.4+)
- `zstandard` 0.20+ - zstd request body decompression
- `sqlite-vec` 0.1.6+ / `hnswlib` 0.8+ - Vector indexes for memory system
- `qdrant-client` 1.9+ / `neo4j` 5.20+ - Optional memory-stack backends
- `redis` 0.27+ (optional Rust feature) - Shared CCR store for multi-worker deployments
- `rusqlite` 0.32+ (bundled) - SQLite-backed CCR and memory stores

## Configuration

**Environment:**
- Environment variables are the primary runtime configuration mechanism; see `.env.example`
- Key per-resource overrides defined in `headroom/paths.py`: `HEADROOM_WORKSPACE_DIR`, `HEADROOM_CONFIG_DIR`, `HEADROOM_SAVINGS_PATH`, `HEADROOM_TOIN_PATH`, `HEADROOM_SUBSCRIPTION_STATE_PATH`
- Proxy config via CLI flags (Click `envvar=` attributes) and environment variables

**Build:**
- `pyproject.toml` - Python project metadata, optional dependency extras, tool configs (ruff, mypy, pytest, coverage, maturin)
- `Cargo.toml` / `Cargo.lock` - Rust workspace, dependencies, release/ci profiles
- `rust-toolchain.toml` - Pinned Rust 1.95.0
- `mkdocs.yml` - MkDocs documentation site configuration
- `docs/next.config.mjs`, `docs/source.config.ts`, `docs/postcss.config.mjs`, `docs/tsconfig.json` - Next.js docs build

## Platform Requirements

**Development:**
- Linux/macOS/Windows supported for Python package install
- Rust toolchain required to build `headroom._core` from sdist; prebuilt wheels available for manylinux_2_28 (x86_64, aarch64), macOS arm64, Windows x86_64
- Docker and Docker Compose optional but recommended for local Neo4j/Qdrant stacks

**Production:**
- Docker container (default image based on `python:3.13-slim` or distroless) exposing port `8787`
- Published to `ghcr.io/chopratejas/headroom` and PyPI as `headroom-ai`
- npm packages `headroom-ai` (SDK) and `headroom-openclaw` published to npmjs.org and GitHub Package Registry
- Supports single-instance SQLite-backed state or stateless/read-only mode (`HEADROOM_STATELESS=true`)

---

*Stack analysis: 2026-06-27*
*Update after major dependency changes*
