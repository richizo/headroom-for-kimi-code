---
phase: quick
plan: kimi-search-fetch-endpoints
type: execute
wave: 1
depends_on: []
files_modified:
  - headroom/proxy/models.py
  - headroom/providers/registry.py
  - headroom/proxy/server.py
  - headroom/providers/proxy_routes.py
  - ~/.kimi-code/config.toml
autonomous: true
requirements:
  - KIMI-SEARCH-01
  - KIMI-FETCH-01
user_setup: []
must_haves:
  truths:
    - Proxy headroom aceita requisições POST /coding/v1/search e /coding/v1/fetch
    - Requisições são encaminhadas verbatim para api.kimi.com/coding/v1/search e /fetch
    - Headers de autenticação (Authorization Bearer) são preservados
    - Kimi Code pode usar http://127.0.0.1:8787 como base_url para search e fetch
  artifacts:
    - Rotas no proxy_routes.py
    - Campo moonshot_api_url no ProxyConfig
  key_links:
    - proxy.handle_passthrough
    - build_copilot_upstream_url
    - register_provider_routes
---

<objective>
Adicionar endpoints /coding/v1/search e /coding/v1/fetch ao proxy Headroom para que o Kimi Code possa rotear chamadas de web search e web fetch pelo proxy.

Purpose: Permitir que ferramentas de search e fetch do Kimi Code passem pelo Headroom, ganhando telemetria e controle de tráfego.
Output: Rotas funcionais no proxy, config.toml do Kimi Code atualizado, teste com curl confirmando pass-through.
</objective>

<execution_context>
@$HOME/.cline/gsd-core/workflows/execute-plan.md
@$HOME/.cline/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@headroom/proxy/models.py
@headroom/providers/registry.py
@headroom/proxy/server.py
@headroom/providers/proxy_routes.py
@headroom/proxy/handlers/openai.py
</context>

<tasks>

<task type="auto">
  <name>Adicionar moonshot_api_url ao ProxyConfig</name>
  <files>headroom/proxy/models.py</files>
  <read_first>headroom/proxy/models.py</read_first>
  <action>
    Adicionar campo `moonshot_api_url: str | None = None` ao ProxyConfig, logo após `vertex_api_url`.
  </action>
  <verify>
    Verificar que ProxyConfig aceita moonshot_api_url sem erro.
  </verify>
  <acceptance_criteria>
    - Campo presente no dataclass
    - Sem quebra de compatibilidade
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Adicionar moonshot ao provider registry</name>
  <files>headroom/providers/registry.py</files>
  <read_first>headroom/providers/registry.py</read_first>
  <action>
    1. Adicionar `moonshot: str | None = None` ao ProviderApiOverrides.
    2. Adicionar `moonshot: str = "https://api.kimi.com/coding/v1"` ao ProviderApiTargets.
    3. Atualizar `resolve_api_overrides` para ler `moonshot_api_url` / `MOONSHOT_TARGET_API_URL` env var.
    4. Atualizar `resolve_api_targets` para normalizar moonshot URL.
    5. Atualizar `build_proxy_provider_runtime` para incluir moonshot no pipeline_providers (se necessário, mas passthrough não precisa de provider pipeline).
    6. Atualizar `api_target` e `select_passthrough_base_url` para suportar "moonshot".
  </action>
  <verify>
    Verificar imports e tipos; ruff check headroom/providers/registry.py.
  </verify>
  <acceptance_criteria>
    - ProviderApiTargets resolve moonshot corretamente
    - Sem regressão nos providers existentes
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Expor MOONSHOT_API_URL no HeadroomProxy</name>
  <files>headroom/proxy/server.py</files>
  <read_first>headroom/proxy/server.py</read_first>
  <action>
    No __init__ do HeadroomProxy, adicionar:
    `HeadroomProxy.MOONSHOT_API_URL = api_targets.moonshot`
    junto com as outras URLs (ANTHROPIC_API_URL, etc.).
  </action>
  <verify>
    Verificar que server.py importa corretamente e não quebra.
  </verify>
</task>

<task type="auto">
  <name>Registrar rotas /coding/v1/search e /coding/v1/fetch</name>
  <files>headroom/providers/proxy_routes.py</files>
  <read_first>headroom/providers/proxy_routes.py</read_first>
  <action>
    1. Adicionar "moonshot" ao `legacy_attrs` no `_api_target`.
    2. Adicionar rotas no `register_provider_routes`:
       @app.post("/coding/v1/search")
       async def moonshot_search(request: Request):
           return await proxy.handle_passthrough(request, _api_target(proxy, "moonshot"), "search", "moonshot")

       @app.post("/coding/v1/fetch")
       async def moonshot_fetch(request: Request):
           return await proxy.handle_passthrough(request, _api_target(proxy, "moonshot"), "fetch", "moonshot")
  </action>
  <verify>
    ruff check headroom/providers/proxy_routes.py
  </verify>
</task>

<task type="auto">
  <name>Atualizar config.toml do Kimi Code</name>
  <files>~/.kimi-code/config.toml</files>
  <action>
    Alterar base_url de services.moonshot_search e services.moonshot_fetch para:
    base_url = "http://127.0.0.1:8787/coding/v1/search"
    base_url = "http://127.0.0.1:8787/coding/v1/fetch"
  </action>
</task>

<task type="auto">
  <name>Testar endpoints com curl</name>
  <action>
    1. Verificar se proxy está rodando em 127.0.0.1:8787.
    2. curl -X POST http://127.0.0.1:8787/coding/v1/search -H "Content-Type: application/json" -H "Authorization: Bearer dummy" -d '{"query":"test"}'
    3. curl -X POST http://127.0.0.1:8787/coding/v1/fetch -H "Content-Type: application/json" -H "Authorization: Bearer dummy" -d '{"url":"https://example.com"}'
    4. Verificar que o proxy encaminha (pode retornar 401/403 da API Kimi se auth for inválida, mas não 404).
  </action>
  <verify>
    Status != 404 (rota existe e foi encaminhada).
  </verify>
</task>

</tasks>

<verification>
Before declaring plan complete:
- [ ] Proxy aceita POST /coding/v1/search (status != 404)
- [ ] Proxy aceita POST /coding/v1/fetch (status != 404)
- [ ] Kimi Code config.toml aponta search/fetch para 127.0.0.1:8787
- [ ] ruff check passa nos arquivos modificados
</verification>

<success_criteria>
- Kimi Code pode usar http://127.0.0.1:8787 para search e fetch
- Proxy encaminha para api.kimi.com/coding/v1
- Não há regressão nos endpoints existentes
</success_criteria>

<output>
After completion, create `.planning/quick/kimi-search-fetch-endpoints-SUMMARY.md`
</output>
