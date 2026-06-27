# Headroom + Kimi/Moonshot Backend

## What This Is

Adicionar ao Headroom um backend configurável para a API Moonshot/Kimi, permitindo que chamadas de LLM feitas por clientes como o Kimi Code CLI passem pelo proxy do Headroom. O backend reutilizará as capacidades existentes do Headroom — cache inteligente, compressão de contexto e captura/telemetria — sobre os modelos `kimi-k2` e `kimi-latest`.

## Core Value

Qualquer cliente que fale o protocolo OpenAI-compatible (incluindo Kimi Code CLI) pode rotear suas chamadas LLM pelo Headroom e obter cache, compressão e observabilidade sem mudar a aplicação cliente.

## Requirements

### Validated

- ✓ Headroom expõe um proxy HTTP(s) com FastAPI/Uvicorn — existente
- ✓ Backends implementam uma interface base (`Backend`) com conversão para o formato Anthropic Messages como canônico — existente
- ✓ Suporte a APIs compatíveis com OpenAI chat completions já existe na interface base (`send_openai_message` / `stream_openai_message`) — existente
- ✓ Cache, compressão e captura/telemetria são aplicadas no caminho do proxy independentemente do backend — existente
- ✓ Configuração de runtime usa Pydantic + variáveis de ambiente/CLI flags — existente
- ✓ Stack inclui `httpx` para requisições upstream async e `litellm` para registro de provedores — existente

### Active

- [x] Implementar backend `MoonshotBackend` seguindo a interface `Backend` do Headroom
- [x] Suportar modelos `kimi-k2` e `kimi-latest` no mapeamento de modelos
- [x] Implementar caminho non-streaming (`send_openai_message`) para chat completions OpenAI-compatible
- [ ] Permitir configuração de credenciais e endpoint via perfil de backend (não apenas variável de ambiente única)
- [x] Integrar o backend ao registro/discovery de backends existente
- [x] Garantir que cache inteligente, compressão de contexto e captura/telemetria sejam aplicadas às chamadas Kimi
- [x] Adicionar testes unitários/integração para o novo backend

### Out of Scope

- Suporte a streaming na primeira fase — adiado para fase posterior; foco em non-streaming primeiro
- Modelos multimodais/embedding da Moonshot — fora do escopo inicial; apenas chat completions
- Alterar o Kimi Code CLI em si — a integração é do lado do Headroom (proxy)
- Novos algoritmos de compressão específicos da Kimi — reusar os existentes do Headroom

## Context

O Headroom é um proxy de otimização para LLMs com backend Python (FastAPI/Click/Pydantic) e núcleo de compressão em Rust. A arquitetura de backends atual já abstrai provedores (Anthropic, OpenAI, LiteLLM etc.) e converte para um formato canônico Anthropic. Como a API da Moonshot é compatível com OpenAI chat completions, o novo backend pode implementar principalmente a interface OpenAI-compatible da classe base, reduzindo a quantidade de tradução necessária.

O cliente desejado (Kimi Code CLI) pode ser configurado para usar um endpoint OpenAI customizado (`base_url`) e uma API key, o que o torna compatível com o proxy do Headroom assim que o backend Moonshot estiver disponível.

## Constraints

- **Tech stack**: Backend deve ser escrito em Python 3.10+, seguindo o padrão dos backends existentes em `headroom/backends/`
- **API da Moonshot**: Usa formato OpenAI-compatible (`/v1/chat/completions`); deve respeitar headers de autenticação e mapeamento de modelos
- **Padrão de configuração**: Credenciais/endpoint devem ser configuráveis via perfil de backend, alinhado à configuração Pydantic existente
- **Compatibilidade**: Não quebrar backends existentes nem mudar a interface `Backend`
- **Testes**: Deve incluir testes no estilo existente (`tests/test_backends/`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Implementar como backend próprio (`MoonshotBackend`) em vez de usar apenas LiteLLM | Maior controle sobre mapeamento de modelos, headers e telemetria; segue o padrão dos backends nativos do Headroom | — Pending |
| Priorizar caminho non-streaming | Reduz complexidade inicial e permite validar conversão de request/response antes de adicionar SSE | — Pending |
| Suportar `kimi-k2` e `kimi-latest` inicialmente | Cobrem o caso de uso principal do Kimi Code CLI sem multiplicar modelos | — Pending |
| Configuração via perfil de backend | Permite múltiplos ambientes/credenciais e mantém consistência com a configuração existente do Headroom | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-27 after initialization*
