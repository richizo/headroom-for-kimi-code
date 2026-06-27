# Stack Research

**Domain:** Adicionar backend Moonshot/Kimi ao Headroom (proxy LLM Python/Rust)
**Researched:** 2026-06-27
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python 3.10+ | >=3.10 | Backend do Headroom | Stack existente; backend deve seguir o padrão dos backends atuais |
| Moonshot OpenAI-compatible API | v1 | Provedor upstream | API oficial OpenAI-compatible; permite reusar lógica de conversão já existente para OpenAI |
| httpx 0.24+ | >=0.24 | Cliente HTTP async upstream | Já usado pelo Headroom para requisições a provedores |
| Pydantic 2.0+ | >=2.0 | Modelos de config/request/response | Stack existente do Headroom |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openai` Python SDK | 2.14+ | SDK adapter e testes | Pode ser usado em testes de integração para validar formato de request/response |
| `pytest-asyncio` | compatível com pytest 7+ | Testes async do backend | Necessário para testar métodos `send_openai_message`/`stream_openai_message` |
| `respx` / `pytest-httpx` | compatível com httpx | Mock de requisições HTTP em testes | Alternativa ao mock manual do cliente httpx |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Lint/format | Padrão do projeto |
| mypy | Type check | Padrão do projeto |
| pytest | Test runner | Padrão do projeto |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Backend nativo `MoonshotBackend` | Apenas LiteLLM | Se quiser suportar dezenas de provedores sem código próprio; perde controle fino de mapeamento e telemetria |
| `httpx` direto | `aiohttp` | `httpx` já é dependência do Headroom e tem suporte HTTP/2 |
| API oficial Moonshot | OpenRouter | OpenRouter pode servir Kimi, mas adiciona intermediário e custo; usar quando não houver acesso direto à Moonshot |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SDK próprio da Moonshot | Não há SDK oficial amplamente usado; a API é OpenAI-compatible | OpenAI SDK ou `httpx` direto |
| Mapear tudo para formato Anthropic primeiro | Perde campos OpenAI específicos (reasoning_content, enable_thinking) | Implementar `send_openai_message`/`stream_openai_message` diretamente |
| Hardcoded endpoint/credenciais | Impede múltiplos ambientes | Configuração via perfil de backend |

## Stack Patterns by Variant

**Se o usuário quiser suporte a streaming em fase posterior:**
- Implementar `stream_openai_message` gerando SSE strings no formato OpenAI
- Reusar padrão de streaming já existente em outros backends (ex.: LiteLLM)

**Se o usuário quiser suporte a reasoning/thinking:**
- Preservar `reasoning_content` no response mapping
- Aceitar `enable_thinking` via `extra_body` ou campo dedicado na configuração

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `httpx` >=0.24 | Python 3.10+ | Já compatível com o Headroom |
| OpenAI API schema | Moonshot API v1 | Moonshot declara compatibilidade total; validar campos não-padrão (`reasoning_content`, `enable_thinking`) |

## Sources

- https://platform.moonshot.ai/docs — documentação oficial da API Moonshot
- https://github.com/MoonshotAI/Kimi-K2.5 — exemplos de uso da API (OpenAI-compatible)
- https://www.morphllm.com/kimi-k2 — base URL e modelos confirmados
- Stack existente do Headroom (`headroom/backends/base.py`, `headroom/backends/litellm.py`)

---
*Stack research for: Moonshot/Kimi backend integration into Headroom*
*Researched: 2026-06-27*
