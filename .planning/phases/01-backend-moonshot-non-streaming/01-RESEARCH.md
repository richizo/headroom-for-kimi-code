# Phase 1 Research: Backend Moonshot non-streaming

**Phase:** 01 — Backend Moonshot non-streaming
**Researched:** 2026-06-27
**Goal:** Descobrir o que é necessário para planejar e implementar o backend nativo Moonshot no Headroom.

## Key Findings

### 1. Arquitetura de backends do Headroom

O Headroom possui uma interface base abstrata em `headroom/backends/base.py` chamada `Backend`. Todos os backends devem implementar:

- `name` (property)
- `send_message(body, headers)` — formato Anthropic Messages
- `stream_message(body, headers)` — formato Anthropic SSE
- `map_model_id(anthropic_model)`
- `supports_model(model)`
- Opcionalmente: `send_openai_message(body, headers)` e `stream_openai_message(body, headers)`

A API Moonshot é OpenAI-compatible. Portanto, o novo backend deve implementar principalmente `send_openai_message()` (passthrough de request/response OpenAI), evitando conversão desnecessária para o formato Anthropic.

### 2. Como backends são instanciados

A função `create_proxy_backend` em `headroom/providers/registry.py` é responsável por criar a instância de backend com base na flag `--backend`. Ela suporta:

- `"anthropic"` → retorna `None` (caminho direto)
- `"anyllm"` ou `"anyllm-<provider>"` → `AnyLLMBackend`
- `"litellm-<provider>"` → `LiteLLMBackend`

Para adicionar Moonshot, devemos adicionar uma branch `backend == "moonshot"` que instancie `MoonshotBackend`.

### 3. Como o backend é usado no proxy

Em `headroom/proxy/server.py`, o backend criado é armazenado em `self.anthropic_backend` (nome herdado). Em `headroom/proxy/handlers/openai.py`, a função de chat completions verifica `if self.anthropic_backend is not None` e chama `self.anthropic_backend.send_openai_message(body, headers)` para requisições non-streaming, e `stream_openai_message()` para streaming.

Isso significa que, ao implementar `send_openai_message`, o backend Moonshot será automaticamente utilizado para requisições OpenAI-style feitas ao proxy.

### 4. Configuração do proxy CLI

A flag `--backend` é definida em `headroom/cli/proxy.py` com default `"anthropic"`. O help text lista as opções atuais e deve ser atualizado para incluir `"moonshot"`.

A configuração do proxy é centralizada em `ProxyConfig` (em `headroom/proxy/server.py`). A flag `backend` é passada diretamente para `ProxyConfig(backend=backend, ...)`. Não é necessário adicionar novos campos obrigatórios a `ProxyConfig` para a Phase 1.

### 5. Decisões de design confirmadas

Com base no CONTEXT.md da fase:

- Ativação via `--backend moonshot`
- Um perfil por instância de proxy
- API key de `MOONSHOT_API_KEY` ou perfil em config (env como fallback)
- `base_url` default `https://api.moonshot.ai/v1`, override via `MOONSHOT_BASE_URL`
- `kimi-latest` resolvido dinamicamente via `/v1/models` no startup
- Erros propagados como passthrough (status code + body originais)

### 6. Estrutura recomendada do MoonshotBackend

```python
class MoonshotBackend(Backend):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        ...

    @property
    def name(self) -> str:
        return "moonshot"

    def map_model_id(self, model: str) -> str:
        # Resolve aliases (kimi-latest) e retorna ID Moonshot
        ...

    def supports_model(self, model: str) -> bool:
        return model in self._supported_models or model.startswith("kimi-")

    async def send_openai_message(self, body, headers) -> BackendResponse:
        # Forward para Moonshot API OpenAI-compatible
        ...
```

### 7. Resolução de alias `kimi-latest`

No `__init__`, fazer uma chamada async ou sync para `GET {base_url}/models` com a API key. Extrair a lista de modelos e identificar qual modelo o alias `kimi-latest` aponta. Como `__init__` não pode ser async, a resolução pode ser:

- **Opção A:** Resolver lazy no primeiro `send_openai_message` (mais simples, mas adiciona latência na primeira requisição).
- **Opção B:** Usar `httpx.Client` sync dentro do `__init__` para buscar `/v1/models` no startup (bloqueia brevemente no boot).

Para um proxy async, a Opção A é mais idiomática e evita bloquear o event loop no startup. O alias pode ser cacheado após a primeira resolução.

### 8. Autenticação

A API Moonshot usa header `Authorization: Bearer <api_key>`. O backend deve:

1. Ler a API key do perfil de backend/config (ou env var).
2. Substituir o header `Authorization` do request do cliente pelo da chave do backend.
3. Nunca propagar a chave do cliente para o upstream.

Isso difere do `LiteLLMBackend`, que forwarda a chave do cliente quando presente. Para Moonshot, usamos sempre a chave configurada no perfil.

### 9. Passthrough de request/response

Como a API Moonshot é OpenAI-compatible, o body do request pode ser encaminhado quase intacto, trocando apenas:

- `model` → ID resolvido (se alias)
- Header `Authorization` → chave do perfil

A resposta da Moonshot já está no formato OpenAI chat completion, então pode ser retornada diretamente no `BackendResponse.body`.

### 10. Tratamento de erros

Erros da upstream devem ser propagados como passthrough:

```python
BackendResponse(
    body=response.json(),
    status_code=response.status_code,
    headers={"content-type": "application/json"},
)
```

Isso preserva a compatibilidade OpenAI para clientes como Kimi Code CLI.

### 11. Testes

Os testes de backend existentes estão em `tests/test_backends/` (atualmente apenas `test_litellm_cache_stats.py` e `__init__.py`). O padrão do projeto sugere criar `tests/test_backends/test_moonshot.py`.

Testes recomendados:

- `test_map_model_id` — mapeamento de `kimi-k2` e `kimi-latest`
- `test_supports_model` — suporte a modelos Kimi
- `test_send_openai_message_success` — mock de request/response via `httpx` ou `respx`
- `test_send_openai_message_uses_profile_api_key` — verifica que a chave do perfil é usada, não a do cliente
- `test_send_openai_message_passthrough_error` — verifica passthrough de 4xx/5xx

### 12. Arquivos a modificar/criar

**Criar:**
- `headroom/backends/moonshot.py` — implementação do backend
- `tests/test_backends/test_moonshot.py` — testes unitários

**Modificar:**
- `headroom/backends/__init__.py` — exportar `MoonshotBackend`
- `headroom/providers/registry.py` — adicionar branch `moonshot` em `create_proxy_backend`
- `headroom/cli/proxy.py` — atualizar help text da flag `--backend`

### 13. Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Alias `kimi-latest` não resolvido se `/v1/models` falhar | Fallback para mapa estático (`kimi-latest` → `kimi-k2`) |
| API key do cliente propagada para upstream | Sempre substituir header `Authorization` pela chave do perfil |
| Timeout na chamada upstream | Configurar timeout padrão (60s) e permitir override |
| Modelo não reconhecido | `supports_model` aceita qualquer `kimi-*` para flexibilidade |

## Recommendations

1. Implementar `MoonshotBackend` focado em `send_openai_message`; adiar `send_message` e streaming para fases futuras.
2. Usar `httpx.AsyncClient` para chamadas upstream, reusando conexões.
3. Resolver `kimi-latest` lazy no primeiro request, com fallback estático.
4. Adicionar testes com `pytest-asyncio` e `httpx` mock (ou `respx` se disponível).
5. Manter a implementação enxuta — o valor está na integração com cache/compressão/telemetria do Headroom, não na lógica do backend em si.

## Sources

- `headroom/backends/base.py`
- `headroom/backends/anyllm.py`
- `headroom/backends/litellm.py`
- `headroom/backends/__init__.py`
- `headroom/providers/registry.py`
- `headroom/cli/proxy.py`
- `headroom/proxy/server.py`
- `headroom/proxy/handlers/openai.py`
- Documentação Moonshot OpenAI-compatible API
- `.planning/phases/01-backend-moonshot-non-streaming/01-CONTEXT.md`
