# Phase 1: Backend Moonshot non-streaming - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

## Phase Boundary

Esta fase entrega um backend nativo `MoonshotBackend` no Headroom, capaz de encaminhar requisições de chat completions no formato OpenAI-compatible para a API Moonshot/Kimi (modelos `kimi-k2` e `kimi-latest`). O escopo é non-streaming apenas; cache, compressão e telemetria serão validados na Phase 2. Streaming, embeddings e multimodal permanecem fora de escopo.

## Implementation Decisions

### Ativação do backend
- **D-01:** O backend será ativado via flag `--backend moonshot` no CLI do proxy, seguindo o padrão dos backends existentes (`anyllm-*`, `litellm-*`).
- **D-02:** Um perfil por instância de proxy: não haverá suporte a múltiplos perfis simultâneos na mesma instância (e.g., `moonshot:prod` fica fora do escopo inicial).
- **D-03:** Não serão adicionadas flags CLI dedicadas (`--moonshot-api-key`, `--moonshot-base-url`); a configuração reutiliza o mecanismo existente de variáveis de ambiente/arquivo de config do Headroom.

### Fonte de configuração
- **D-04:** A API key da Moonshot pode vir de variável de ambiente `MOONSHOT_API_KEY` **ou** de um perfil de backend em arquivo de config YAML/JSON do Headroom; env var funciona como fallback quando o arquivo não define a chave.
- **D-05:** O `base_url` padrão é `https://api.moonshot.ai/v1`, podendo ser sobrescrito via variável de ambiente `MOONSHOT_BASE_URL`.

### Mapeamento de aliases
- **D-06:** O alias `kimi-latest` será resolvido dinamicamente consultando o endpoint `/v1/models` da Moonshot no startup do backend.

### Propagação de erros
- **D-07:** Erros da API Moonshot são propagados ao cliente como passthrough — status code e body exatos da upstream são retornados, preservando compatibilidade OpenAI.

### Claude's Discretion
- Quando `--backend moonshot` está ativo, o planejador deve decidir se o backend atende apenas `/v1/chat/completions` OpenAI-style (implementando `send_openai_message`) ou também converte requests Anthropic Messages (implementando `send_message`). A preferência implícita do projeto é usar `send_openai_message` por ser OpenAI-compatible, mas a decisão final fica a critério do planejador baseado no padrão dos backends existentes.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — objetivo, escopo, decisões-chave e restrições do projeto
- `.planning/REQUIREMENTS.md` — requisitos v1 mapeados para fases (BKND-01..06, CONF-01..03, INTG-01, TEST-01,03,04)
- `.planning/ROADMAP.md` — detalhes da Phase 1, success criteria e planos sugeridos
- `.planning/research/SUMMARY.md` — resumo executivo da pesquisa com implicações de roadmap

### Codebase patterns
- `headroom/backends/base.py` — interface base `Backend` com `send_openai_message` / `stream_openai_message`
- `headroom/backends/litellm.py` — exemplo de backend com registro de provedores e mapeamento de modelos
- `headroom/backends/anyllm.py` — exemplo de backend simples
- `headroom/backends/__init__.py` — exports dos backends
- `headroom/providers/registry.py` — `create_proxy_backend` e lógica de seleção de backend no proxy

### Provider API docs
- Documentação Moonshot OpenAI-compatible (`https://platform.moonshot.ai/docs`) — formato de request/response e endpoint `/v1/models`

## Existing Code Insights

### Reusable Assets
- `headroom/providers/registry.py:create_proxy_backend` — ponto de extensão para adicionar o novo backend `moonshot`
- `headroom/backends/base.py:Backend` — interface a ser implementada
- `headroom/backends/litellm.py` — referência para configuração de provedor e mapeamento de modelos
- `httpx` (já dependência do projeto) — cliente HTTP async para upstream

### Established Patterns
- Backends são instanciados em `create_proxy_backend` com base em CLI flag `--backend`
- Backends nativos são importados em `headroom/backends/__init__.py`
- Configuração usa Pydantic + variáveis de ambiente
- Testes de backend ficam em `tests/test_backends/`

### Integration Points
- `headroom/providers/registry.py` — adicionar branch `backend == "moonshot"` em `create_proxy_backend`
- `headroom/backends/__init__.py` — exportar `MoonshotBackend`
- `headroom/cli/proxy.py` (ou equivalente) — garantir que `--backend moonshot` seja aceito/help text atualizado
- Proxy server — rotear requests OpenAI-style para `send_openai_message` quando backend Moonshot estiver selecionado

## Specific Ideas

- O backend deve ser o mais enxuto possível: como a API Moonshot é OpenAI-compatible, a implementação pode ser principalmente passthrough de request/response, com mapeamento mínimo de modelos e injeção de autenticação.
- `kimi-latest` deve ser resolvido no startup via `/v1/models` para evitar surpresas quando a Moonshot atualizar o alias.

## Deferred Ideas

None — discussion stayed within phase scope

---

*Phase: 1-Backend Moonshot non-streaming*
*Context gathered: 2026-06-27*
