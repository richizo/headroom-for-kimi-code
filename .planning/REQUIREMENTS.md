# Requirements: Headroom + Kimi/Moonshot Backend

**Defined:** 2026-06-27
**Core Value:** Qualquer cliente que fale o protocolo OpenAI-compatible (incluindo Kimi Code CLI) pode rotear suas chamadas LLM pelo Headroom e obter cache, compressão e observabilidade sem mudar a aplicação cliente.

## v1 Requirements

### Backend Core

- [ ] **BKND-01**: Headroom possui um backend `MoonshotBackend` implementado em `headroom/backends/moonshot.py`
- [ ] **BKND-02**: `MoonshotBackend` implementa `send_openai_message()` para chat completions non-streaming
- [ ] **BKND-03**: `MoonshotBackend` suporta os modelos `kimi-k2` e `kimi-latest`
- [ ] **BKND-04**: `MoonshotBackend` mapeia model IDs canônicos para IDs esperados pela API Moonshot
- [ ] **BKND-05**: O backend encaminha requests no formato OpenAI chat completions para a API Moonshot
- [ ] **BKND-06**: O backend retorna responses no formato OpenAI chat completions ao proxy

### Configuration & Auth

- [ ] **CONF-01**: Credenciais Moonshot são configuráveis via perfil de backend (api_key)
- [ ] **CONF-02**: Endpoint/base_url da API Moonshot é configurável (e.g., `https://api.moonshot.ai/v1` ou `https://api.moonshot.cn/v1`)
- [ ] **CONF-03**: O backend usa a chave do perfil no header `Authorization: Bearer <key>` de upstream, não a chave do cliente

### Integration

- [ ] **INTG-01**: `MoonshotBackend` está registrado no discovery/registry de backends do Headroom
- [ ] **INTG-02**: O proxy Headroom seleciona `MoonshotBackend` quando o model ID corresponde a um modelo Kimi suportado
- [ ] **INTG-03**: Chamadas ao backend Moonshot passam pelos middlewares de cache do Headroom
- [ ] **INTG-04**: Chamadas ao backend Moonshot passam pelos middlewares de compressão de contexto do Headroom
- [ ] **INTG-05**: Chamadas ao backend Moonshot geram telemetria/traces no Headroom

### Testing

- [ ] **TEST-01**: Existem testes unitários para `map_model_id`, `supports_model` e `send_openai_message`
- [ ] **TEST-02**: Existem testes de integração que simulam request/response através do proxy
- [ ] **TEST-03**: Testes cobrem o cenário de autenticação via perfil de backend
- [ ] **TEST-04**: Testes cobrem o cenário de erro da API upstream (4xx/5xx)

## v2 Requirements

### Streaming

- **STRM-01**: `MoonshotBackend` implementa `stream_openai_message()` para chat completions streaming
- **STRM-02**: Streaming retorna chunks no formato SSE compatível com OpenAI

### Reasoning / Thinking

- **THNK-01**: `MoonshotBackend` expõe `reasoning_content` quando o modelo retorna thinking mode
- **THNK-02**: É possível controlar `enable_thinking` via configuração ou `extra_body`

### Outros modelos

- **MDL-01**: Suporte a modelos adicionais da Moonshot (kimi-k2.5, kimi-k2.6, etc.)
- **EMBD-01**: Suporte a endpoint `/v1/embeddings`
- **MULT-01**: Suporte a input multimodal (imagem/vídeo)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Streaming na v1 | Usuário explicitamente adiou streaming para fase posterior |
| Embeddings na v1 | Fora do escopo inicial; requer validação de uso e padrões de cache diferentes |
| Multimodal (imagem/vídeo) na v1 | Complexidade de upload/base64; não alinhado ao caso de uso Kimi Code CLI |
| Alterar o Kimi Code CLI em si | A integração é do lado do Headroom (proxy); o cliente não precisa ser modificado |
| Novos algoritmos de compressão específicos da Kimi | Reusar os existentes do Headroom |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BKND-01 | Phase 1 | Pending |
| BKND-02 | Phase 1 | Pending |
| BKND-03 | Phase 1 | Pending |
| BKND-04 | Phase 1 | Pending |
| BKND-05 | Phase 1 | Pending |
| BKND-06 | Phase 1 | Pending |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| INTG-01 | Phase 1 | Pending |
| INTG-02 | Phase 2 | Pending |
| INTG-03 | Phase 2 | Pending |
| INTG-04 | Phase 2 | Pending |
| INTG-05 | Phase 2 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 2 | Pending |
| TEST-03 | Phase 1 | Pending |
| TEST-04 | Phase 1 | Pending |
| STRM-01 | Phase 4 | Pending |
| STRM-02 | Phase 4 | Pending |
| THNK-01 | Phase 3 | Pending |
| THNK-02 | Phase 3 | Pending |
| MDL-01 | v2 | Deferred |
| EMBD-01 | v2 | Deferred |
| MULT-01 | v2 | Deferred |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after initial definition*
