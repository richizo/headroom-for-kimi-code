---
phase: 02-middleware-integration
type: context
---

# Phase 2 Context — Testes e integração de middlewares

## Objetivo
Garantir que as capacidades de valor do Headroom (cache inteligente, compressão de contexto e telemetria/captura) se aplicam corretamente às chamadas encaminhadas pelo novo backend Moonshot.

## Escopo
- Non-streaming apenas (streaming é Phase 4).
- Foco em `/v1/chat/completions` no formato OpenAI.
- Modelos: `kimi-k2`, `kimi-latest`.

## Descobertas da pesquisa

### Cache
- O proxy gerencia cache através de dois mecanismos:
  - `PrefixCacheTracker` (`headroom/cache/prefix_tracker.py`) — congela prefixos já cacheados pelo provedor.
  - `CompressionCache` (`headroom/cache/compression_cache.py`) — reutiliza compressões anteriores.
- O handler OpenAI (`headroom/proxy/handlers/openai.py`) lê campos de uso da resposta (`cache_read_input_tokens`, `cache_creation_input_tokens`, `prompt_tokens_details.cached_tokens`) e chama `PrefixCacheTracker.update_from_response()`.
- **Conclusão**: `MoonshotBackend` não precisa de mudanças para suportar cache; basta retornar resposta no formato OpenAI com `usage`.

### Compressão
- A decisão de compressão está em `headroom/proxy/compression_decision.py`.
- A compressão é aplicada pelo pipeline (`headroom/transforms/pipeline.py`) no handler OpenAI **antes** de chamar o backend.
- O backend recebe mensagens já otimizadas e apenas encaminha.
- **Conclusão**: `MoonshotBackend` não precisa de mudanças para suportar compressão.

### Telemetria/Capture
- Toda observabilidade flui por `RequestOutcome`/`emit_request_outcome` (`headroom/proxy/outcome.py`).
- O handler OpenAI registra `provider=self.anthropic_backend.name`, que será `"moonshot"`.
- Métricas Prometheus, logs de request, `/stats` e dashboard mostrarão Moonshot automaticamente.
- **Conclusão**: `MoonshotBackend` não precisa de mudanças para telemetria; basta o backend estar registrado com `name == "moonshot"`.

### Testes de integração
- Padrão existente: `ProxyConfig(...) + create_app(config) + TestClient(app)`.
- Backend é mockado via `patch("headroom.proxy.server.AnyLLMBackend")` ou substituindo o transporte HTTP do backend real.
- Não existe teste proxy-level para Moonshot ainda.

## Hipóteses a validar
1. O proxy encaminha requisições `/v1/chat/completions` com `model=kimi-k2` para `MoonshotBackend.send_openai_message`.
2. O response da Moonshot é retornado ao cliente sem alterações.
3. `PrefixCacheTracker.update_from_response` é chamado com os valores corretos quando Moonshot retorna campos de cache.
4. A compressão é aplicada em requests longos com `optimize=True`.
5. Telemetria registra `provider="moonshot"` e tokens corretos.

## Riscos
- `MoonshotBackend` pode precisar de ajustes mínimos se campos de cache/usage da Moonshot tiverem formato diferente do esperado.
- Testes de compressão podem ser instáveis devido a heurísticas de conteúdo.

## Fora de escopo
- Streaming.
- Multimodal/embedding.
- Alterações no dashboard HTML.
