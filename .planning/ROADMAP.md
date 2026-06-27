# Roadmap: Headroom + Kimi/Moonshot Backend

## Overview

Este roadmap leva o Headroom de "sem suporte a Kimi" até "Kimi Code CLI pode rotear chamadas pelo Headroom com cache, compressão e telemetria". O trabalho começa com o backend non-streaming, valida a integração com os middlewares existentes, adiciona suporte a reasoning e finaliza com streaming.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Moonshot non-streaming** - Implementar MoonshotBackend com chat completions non-streaming, mapeamento de modelos, autenticação e registro no discovery
- [ ] **Phase 2: Testes e integração de middlewares** - Validar que cache, compressão e telemetria do Headroom se aplicam ao backend Moonshot
- [ ] **Phase 3: Suporte a thinking/reasoning** - Expor `reasoning_content` e suportar `enable_thinking` da API Moonshot
- [ ] **Phase 4: Streaming** - Implementar `stream_openai_message` com Server-Sent Events

## Phase Details

### Phase 1: Backend Moonshot non-streaming

**Goal**: Ter um backend funcional no Headroom capaz de encaminhar chat completions non-streaming para a API Moonshot/Kimi.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: Backend Moonshot, mapeamento de modelos, autenticação via perfil, registro no discovery
**Success Criteria** (what must be TRUE):

  1. O proxy Headroom aceita requisições `/v1/chat/completions` com `model=kimi-k2`
  2. `MoonshotBackend` está registrado no discovery de backends
  3. A chave do perfil de backend é usada no header `Authorization` de upstream
  4. O response é retornado ao cliente no formato OpenAI chat completion

**Plans**: 3/3 plans executed

Plans:

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md
- [x] 01-03-PLAN.md
- [x] 01-01: Criar estrutura inicial de `MoonshotBackend` e configuração de perfil
- [x] 01-02: Implementar `send_openai_message`, `map_model_id` e `supports_model`
- [x] 01-03: Registrar backend no discovery e adicionar testes unitários básicos

### Phase 2: Testes e integração de middlewares

**Goal**: Garantir que as capacidades de valor do Headroom (cache, compressão, telemetria) realmente se aplicam às chamadas Kimi.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: Cache inteligente, compressão de contexto, captura/telemetria
**Success Criteria** (what must be TRUE):

  1. Chamadas repetidas com mesmo prompt são cacheadas quando aplicável
  2. Compressão de contexto é acionada em requests longos
  3. Traces/telemetria das chamadas Kimi aparecem no dashboard ou logs
  4. Testes de integração cobrem request/response através do proxy

**Plans**: 2 plans

Plans:

- [ ] 02-01: Adicionar testes de integração do backend através do proxy
- [ ] 02-02: Validar e ajustar aplicação de cache, compressão e telemetria sobre o backend Moonshot

### Phase 3: Suporte a thinking/reasoning

**Goal**: Permitir uso dos modelos Kimi em modo thinking, expondo o conteúdo de raciocínio ao cliente.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: Suporte a thinking/reasoning
**Success Criteria** (what must be TRUE):

  1. Requests com `enable_thinking=true` (ou equivalente) retornam `reasoning_content`
  2. Modo instant (thinking disabled) continua funcionando
  3. Testes cobrem ambos os modos com mocks realísticos

**Plans**: 2 plans

Plans:

- [ ] 03-01: Adicionar parsing e exposição de `reasoning_content` no response mapping
- [ ] 03-02: Suportar `enable_thinking` via config/extra_body e adicionar testes

### Phase 4: Streaming

**Goal**: Suportar respostas em streaming para chat completions Kimi.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: Streaming
**Success Criteria** (what must be TRUE):

  1. Requests com `stream=true` recebem chunks SSE do modelo Kimi
  2. O formato SSE segue o padrão OpenAI chat completions streaming
  3. Testes cobrem o caminho de streaming

**Plans**: 1 plan

Plans:

- [ ] 04-01: Implementar `stream_openai_message` com SSE e testes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Moonshot non-streaming | 3/3 | Completed    | 2026-06-27 |
| 2. Testes e integração de middlewares | 0/2 | Planned | - |
| 3. Suporte a thinking/reasoning | 0/2 | Not started | - |
| 4. Streaming | 0/1 | Not started | - |
