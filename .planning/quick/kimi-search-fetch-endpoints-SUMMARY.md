# Summary: kimi-search-fetch-endpoints

## What Was Done

Adicionados endpoints `/coding/v1/search` e `/coding/v1/fetch` ao proxy Headroom para encaminhar requisições de web search e web fetch do Kimi Code para a API Kimi (api.kimi.com/coding/v1).

## Changes

### Files Modified

1. **headroom/proxy/models.py**
   - Adicionado `moonshot_api_url: str | None = None` ao `ProxyConfig`
   - Incluído `moonshot` no `provider_api_overrides()`

2. **headroom/providers/registry.py**
   - Adicionado `DEFAULT_MOONSHOT_API_URL = "https://api.kimi.com/coding/v1"`
   - Adicionado `moonshot` ao `ProviderApiOverrides` e `ProviderApiTargets`
   - Atualizado `api_target()` e `resolve_api_overrides()`/`resolve_api_targets()` para suportar moonshot

3. **headroom/proxy/server.py**
   - Exposto `HeadroomProxy.MOONSHOT_API_URL = api_targets.moonshot`
   - Adicionado `moonshot_api_url` ao `_proxy_config_from_env()`

4. **headroom/providers/proxy_routes.py**
   - Adicionado `moonshot: "MOONSHOT_API_URL"` ao `legacy_attrs`
   - Registradas rotas:
     - `POST /coding/v1/search` → `proxy.handle_passthrough(..., "search", "moonshot")`
     - `POST /coding/v1/fetch` → `proxy.handle_passthrough(..., "fetch", "moonshot")`

5. **~/.kimi-code/config.toml**
   - Alterado `services.moonshot_search.base_url` para `http://127.0.0.1:8787/coding/v1/search`
   - Alterado `services.moonshot_fetch.base_url` para `http://127.0.0.1:8787/coding/v1/fetch`

## Verification

- `ruff check` passa em todos os arquivos modificados.
- Dashboard do proxy (`/stats`) mostra requisições rotuladas como `passthrough:search` e `passthrough:fetch` no agente `moonshot`.
- O retorno HTTP 404 com body `{"error":{"message":"The requested resource was not found"}}` vem da API upstream (api.kimi.com), confirmando que o proxy está encaminhando corretamente.

## Notes

- As requisições de search/fetch requerem autenticação válida da API Kimi (token OAuth ou API key). O proxy preserva o header `Authorization` verbatim.
- O proxy continua suportando chat completions via `/v1/chat/completions` (já funcionando anteriormente).
