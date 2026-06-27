# Project Research Summary

**Project:** Headroom + Kimi/Moonshot Backend
**Domain:** Integração de backend Moonshot/Kimi em proxy LLM existente
**Researched:** 2026-06-27
**Confidence:** HIGH

## Executive Summary

A Moonshot AI expõe seus modelos Kimi através de uma API OpenAI-compatible (base URLs `https://api.moonshot.ai/v1` e `https://api.moonshot.cn/v1`). Isso significa que o Headroom pode adicionar suporte a esses modelos com um backend relativamente enxuto que implemente a interface OpenAI da classe base `Backend`, em vez de converter tudo para o formato Anthropic Messages canônico.

A abordagem recomendada é criar um backend nativo `MoonshotBackend` em `headroom/backends/moonshot.py`, seguindo o padrão dos backends existentes. Ele deve implementar `send_openai_message()` para o caminho non-streaming, suportar mapeamento de modelos (`kimi-k2`, `kimi-latest`), autenticação via perfil de backend e registro no discovery. O valor do Headroom — cache, compressão e telemetria — é aplicado automaticamente pelo proxy assim que o backend está registrado.

Os principais riscos são supor compatibilidade OpenAI total sem validar campos não-padrão (como `reasoning_content` e restrições de `temperature`), propagar a chave do cliente em vez da chave do perfil, e esquecer de registrar o backend no registry. Todos esses riscos podem ser mitigados com testes unitários/integração e seguindo o padrão dos backends existentes.

## Key Findings

### Recommended Stack

O Headroom já possui todo o stack necessário: Python 3.10+, FastAPI, Pydantic, httpx e uma interface base de backends. Não há necessidade de novas dependências principais. A integração deve reusar `httpx` para chamadas async e seguir a estrutura de configuração Pydantic existente.

**Core technologies:**
- Python 3.10+ / httpx: cliente upstream async — já é stack do Headroom
- Moonshot OpenAI-compatible API: protocolo do provedor — reduz necessidade de tradução complexa
- Pydantic: modelos de configuração — stack existente

### Expected Features

**Must have (table stakes):**
- Chat completions non-streaming
- Autenticação via API key
- Mapeamento de modelos (`kimi-k2`, `kimi-latest`)
- Configuração de endpoint/base_url
- Registro no discovery de backends

**Should have (competitive):**
- Suporte a `reasoning_content` / thinking mode
- Múltiplos perfis de backend
- Cache + compressão + telemetria aplicadas

**Defer (v2+):**
- Streaming
- Embeddings
- Multimodal (imagem/vídeo)

### Architecture Approach

A arquitetura segue o padrão existente do Headroom: cliente faz request OpenAI-compatible para o proxy, o proxy aplica middlewares (cache, compressão, telemetria), o router seleciona `MoonshotBackend` pelo model ID, e o backend encaminha para a API Moonshot. Como a API é OpenAI-compatible, o backend deve implementar `send_openai_message()` diretamente, evitando conversão desnecessária.

**Major components:**
1. `MoonshotBackend` — novo backend em `headroom/backends/moonshot.py`
2. Backend registry — adicionar o backend ao discovery existente
3. Backend profile config — credenciais/endpoint configuráveis
4. Testes em `tests/test_backends/test_moonshot.py`

### Critical Pitfalls

1. **Assumir compatibilidade OpenAI 100% sem validar campos não-padrão** — validar com exemplos reais e adicionar testes
2. **Propagar API key do cliente para o provedor** — sempre usar chave do perfil de backend
3. **Mapeamento de aliases quebrado** — manter mapa explícito e testar `kimi-latest`
4. **Esquecer de registrar o backend no discovery** — adicionar teste de registry

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Implementar backend Moonshot non-streaming
**Rationale:** É o núcleo da integração; todos os outros recursos dependem dele.
**Delivers:** `MoonshotBackend` funcional com `send_openai_message()`, mapeamento de modelos, autenticação e registro no discovery.
**Addresses:** Chat completions non-streaming, autenticação, mapeamento, registro.
**Avoids:** Backend não registrado, API key do cliente propagada, alias não resolvido.

### Phase 2: Integrar middlewares e adicionar testes
**Rationale:** Validar que cache, compressão e telemetria realmente se aplicam ao novo backend.
**Delivers:** Testes de integração cobrindo request/response, e validação de que middlewares estão ativos.
**Uses:** Stack existente do Headroom.
**Implements:** Testes e validação de middlewares.

### Phase 3: Suporte a thinking/reasoning
**Rationale:** Diferenciador competitivo; depende do backend básico funcionando.
**Delivers:** Parsing e exposição de `reasoning_content`, suporte a `enable_thinking`.
**Addresses:** Differentiator de thinking mode.
**Avoids:** Perda de campos OpenAI específicos.

### Phase 4: Streaming
**Rationale:** Requisito de UX, mas adiado intencionalmente pelo usuário.
**Delivers:** `stream_openai_message()` com SSE.
**Addresses:** Streaming.

### Phase Ordering Rationale

- O backend non-streaming deve vir primeiro porque é a base técnica.
- Testes e validação de middlewares vêm em seguida para garantir que o valor do Headroom está sendo entregue.
- Thinking/reasoning vem depois porque é um diferenciador que depende do parsing correto do response.
- Streaming é a última fase porque o usuário explicitamente a adiou.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (thinking/reasoning):** Pode precisar de validação real contra a API para confirmar formato exato de `reasoning_content` e comportamento de `enable_thinking`.

Phases with standard patterns (skip research-phase):
- **Phase 1 e 2:** Padrão bem estabelecido no Headroom; replicar estrutura dos backends existentes.
- **Phase 4 (streaming):** Padrão SSE já existe em outros backends.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Reusa stack existente do Headroom; nenhuma dependência nova necessária |
| Features | HIGH | API OpenAI-compatible bem documentada; escopo claro |
| Architecture | HIGH | Padrão de backend já estabelecido no Headroom |
| Pitfalls | MEDIUM-HIGH | Conhecidos de integrações OpenAI-compatible; mitigáveis com testes |

**Overall confidence:** HIGH

### Gaps to Address

- **Formato exato de `reasoning_content`:** Validar com chamada real à API em ambiente seguro durante a Phase 3.
- **Restrições de parâmetros por modelo:** Confirmar quais valores de `temperature`/`top_p` são aceitos para `kimi-k2` vs `kimi-latest`.
- **Endpoints regionais:** Testar se `api.moonshot.ai` e `api.moonshot.cn` têm comportamentos idênticos.

## Sources

### Primary (HIGH confidence)
- https://platform.moonshot.ai/docs — documentação oficial da API
- https://github.com/MoonshotAI/Kimi-K2.5 — exemplos de uso OpenAI-compatible
- `headroom/backends/base.py` — interface base dos backends
- `headroom/backends/litellm.py` — exemplo de backend com múltiplos provedores

### Secondary (MEDIUM confidence)
- https://www.morphllm.com/kimi-k2 — confirmação de base URL e modelos
- Discussões da comunidade sobre quirks da API Moonshot (temperature, `/v1/models`)

---
*Research completed: 2026-06-27*
*Ready for roadmap: yes*
