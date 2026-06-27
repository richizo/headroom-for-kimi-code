# Architecture Research

**Domain:** Integração de backend Moonshot/Kimi no Headroom
**Researched:** 2026-06-27
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Kimi Code CLI)                       │
│              OpenAI-compatible request (base_url = Headroom)         │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Headroom Proxy (FastAPI/Uvicorn)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    Cache     │  │ Compression  │  │  Telemetry   │              │
│  │   Middleware │  │  Middleware  │  │  Middleware  │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼─────────────────┼─────────────────┼──────────────────────┘
          │                 │                 │
          └─────────────────┴─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Backend Router / Discovery                       │
│              Seleciona backend com base no model ID                  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MoonshotBackend (novo)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  map_model_id()  │  send_openai_message()  │  supports_model()│  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│              httpx async request → Moonshot API                      │
│         (https://api.moonshot.ai/v1/chat/completions)                │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Client (Kimi Code CLI) | Envia requisições OpenAI-compatible | Configurado com `base_url` do Headroom e `model=kimi-k2` |
| Proxy Middlewares | Aplicam cache, compressão e telemetria | Reutilizar implementações existentes |
| Backend Router | Seleciona backend pelo model ID | `headroom/backends/__init__.py` ou registry similar |
| MoonshotBackend | Traduz/faz forward para API Moonshot | Nova classe em `headroom/backends/moonshot.py` |
| httpx client | Requisições HTTP async upstream | Reutilizar cliente existente ou criar um novo no backend |

## Recommended Project Structure

```
headroom/backends/
├── __init__.py           # Registro de backends (já existe)
├── base.py               # Classe base Backend (já existe)
├── litellm.py            # Backend LiteLLM (já existe)
├── anyllm.py             # Backend genérico (já existe)
└── moonshot.py           # NOVO: implementação MoonshotBackend

tests/test_backends/
├── test_moonshot.py      # NOVO: testes do backend Moonshot
└── ...                   # testes existentes

headroom/config.py        # Possível extensão para perfis de backend
```

### Structure Rationale

- **`headroom/backends/moonshot.py`:** Segue a convenção dos backends existentes (`litellm.py`, `anyllm.py`)
- **`tests/test_backends/test_moonshot.py`:** Segue a estrutura de testes existente
- **Não criar um novo diretório:** A mudança é pequena o suficiente para caber em um arquivo novo no diretório existente

## Architectural Patterns

### Pattern 1: OpenAI-Compatible Passthrough

**What:** O backend recebe um body no formato OpenAI chat completion e o encaminha quase sem alteração para a API Moonshot, ajustando apenas autenticação e mapeamento de modelo.

**When to use:** Quando o provedor (Moonshot) declara compatibilidade OpenAI, reduzindo drasticamente a necessidade de tradução.

**Trade-offs:**
- Pros: Menos código, menos bugs de tradução, fácil manutenção
- Cons: Campos não-padrão (`enable_thinking`, `reasoning_content`) precisam de tratamento explícito

### Pattern 2: Backend Profile Configuration

**What:** Credenciais, endpoint e mapeamentos de modelo vivem em um perfil de backend configurável, não hardcoded.

**When to use:** Sempre que há necessidade de múltiplos ambientes ou provedores.

**Trade-offs:**
- Pros: Flexibilidade, testabilidade, consistência com Headroom
- Cons: Pequena complexidade adicional de configuração

### Pattern 3: Canonical Anthropic + OpenAI Dual Interface

**What:** A classe base do Headroom usa Anthropic Messages como canônico, mas expõe métodos OpenAI (`send_openai_message`).

**When to use:** Para provedores OpenAI-compatible, implementar apenas a interface OpenAI.

**Trade-offs:**
- Pros: Evita perda de campos OpenAI específicos
- Cons: Proxy deve saber rotear requests OpenAI para `send_openai_message` em vez de `send_message`

## Data Flow

### Request Flow

```
[Client request /v1/chat/completions]
    ↓
[Proxy parses model ID → "kimi-k2"]
    ↓
[Backend Router → MoonshotBackend]
    ↓
[map_model_id("kimi-k2") → "kimi-k2" ou alias interno]
    ↓
[send_openai_message(body, headers)]
    ↓
[httpx POST https://api.moonshot.ai/v1/chat/completions]
    ↓
[Parse OpenAI response → BackendResponse]
    ↓
[Proxy aplica cache/telemetria e retorna ao cliente]
```

### Key Data Flows

1. **Autenticação:** API key vem do perfil de backend e é enviada no header `Authorization: Bearer <key>`; não é propagada do cliente por padrão.
2. **Mapeamento de modelo:** Model ID do cliente é mapeado para o ID esperado pela Moonshot; para Kimi geralmente é 1:1, mas aliases como `kimi-latest` precisam ser resolvidos.
3. **Response parsing:** Response OpenAI é passado quase intacto; campos extras como `reasoning_content` podem ser extraídos em fases futuras.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single dev | Perfil local com `api_key` em env var é suficiente |
| Small team | Múltiplos perfis (dev/staging/prod) no arquivo de config |
| Production multi-worker | Stateless; chave e endpoint no config do deploy; CCR pode usar Redis se habilitado |

### Scaling Priorities

1. **First bottleneck:** Latência de upstream Moonshot. Mitigar via cache inteligente do Headroom.
2. **Second bottleneck:** Taxa de requisições da Moonshot. O Headroom pode aplicar throttling ou fallback entre perfis.

## Anti-Patterns

### Anti-Pattern 1: Mapear tudo para Anthropic primeiro

**What people do:** Implementam `send_message()` e convertem OpenAI→Anthropic→OpenAI.

**Why it's wrong:** Perde campos OpenAI específicos da Moonshot (`reasoning_content`, `enable_thinking`) e aumenta a superfície de bugs.

**Do this instead:** Implementar `send_openai_message()` diretamente.

### Anti-Pattern 2: Hardcoded credentials

**What people do:** Deixam `api_key` como constante no código.

**Why it's wrong:** Impede múltiplos ambientes e é risco de segurança.

**Do this instead:** Ler do perfil de backend/configuração.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Moonshot API | HTTP POST OpenAI-compatible | Validar base URL (`.ai` internacional vs `.cn` China); testar com chave real em ambiente seguro |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Proxy ↔ MoonshotBackend | Chamada de método Python | Manter interface base estável |
| Backend ↔ Config | Leitura de perfil | Reutilizar config Pydantic existente |

## Sources

- `headroom/backends/base.py` — interface base
- `headroom/backends/litellm.py` — exemplo de backend com múltiplos provedores
- Documentação Moonshot OpenAI-compatible API

---
*Architecture research for: Moonshot/Kimi backend integration into Headroom*
*Researched: 2026-06-27*
