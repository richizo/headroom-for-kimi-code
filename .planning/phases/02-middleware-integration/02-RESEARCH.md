---
phase: 02-middleware-integration
type: research
---

# Phase 2 Research — Cache, Compression, Telemetry, Integration Tests

## Cache

### Arquivos relevantes
- `headroom/proxy/semantic_cache.py` — cache semântico de respostas (short-lived).
- `headroom/cache/prefix_tracker.py` — rastreamento de prefix cache do provedor.
- `headroom/cache/compression_cache.py` — reutilização de compressões anteriores.
- `headroom/proxy/handlers/openai.py:1844-1910` — cálculo de sessão e frozen prefix.
- `headroom/proxy/handlers/openai.py:2413-2431` — leitura de cache fields do response.
- `tests/test_proxy_openai_cache_stability.py` — testes de estabilidade de cache.

### Como funciona para backends
1. Handler OpenAI cria/obtém `PrefixCacheTracker` para a sessão.
2. Computa `frozen_message_count` baseado em mensagens anteriores já cacheadas.
3. Pipeline de compressão respeita o prefixo congelado.
4. Após resposta, lê `usage.cache_read_input_tokens`, `usage.cache_creation_input_tokens` ou `usage.prompt_tokens_details.cached_tokens`.
5. Chama `tracker.update_from_response(cache_read_tokens, cache_write_tokens, ...)`.

### O que Moonshot precisa fazer
- Retornar `usage` no formato OpenAI. Se a API Moonshot retornar campos de cache (ainda não confirmado), eles devem ser mapeados para o formato esperado. Inicialmente, assumimos que não há campos especiais e o proxy infere cache write a partir de `prompt_tokens - cached_tokens`.

## Compressão

### Arquivos relevantes
- `headroom/proxy/compression_decision.py::CompressionDecision.decide`
- `headroom/proxy/handlers/openai.py::handle_openai_chat`
- `headroom/transforms/pipeline.py::TransformPipeline`
- `headroom/transforms/content_router.py::ContentRouter`
- `headroom/transforms/compression_policy.py`
- `tests/test_proxy_compress_endpoint.py`
- `tests/test_transforms/`

### Como funciona
1. `CompressionDecision.decide` verifica flags (`optimize`, bypass, modo, licença).
2. `handle_openai_chat` chama `self.openai_pipeline.apply(...)`.
3. `TransformPipeline` executa `CacheAligner` e `ContentRouter`.
4. `ContentRouter` detecta tipo de conteúdo e aplica compressores específicos.
5. Mensagens otimizadas substituem `body["messages"]`.
6. Backend recebe body já comprimido.

### O que Moonshot precisa fazer
- Nada. O backend é transparente à compressão.

## Telemetria/Capture

### Arquivos relevantes
- `headroom/proxy/outcome.py::RequestOutcome`, `emit_request_outcome`
- `headroom/proxy/prometheus_metrics.py`
- `headroom/proxy/cost.py`
- `headroom/proxy/request_logger.py`
- `headroom/dashboard/__init__.py`
- `headroom/proxy/server.py` — endpoints `/stats`, `/stats-history`
- `tests/test_request_outcome.py`
- `tests/test_proxy/test_request_logger.py`
- `tests/test_proxy_stats_recent_requests.py`

### Como funciona
1. Handlers constroem `RequestOutcome` ao final da requisição.
2. `emit_request_outcome` grava em:
   - Métricas Prometheus
   - Cost tracker
   - Request logger
   - PERF log
3. O provider é obtido de `self.anthropic_backend.name`, que para Moonshot será `"moonshot"`.
4. Dashboard classifica agente por title-case do provider.

### O que Moonshot precisa fazer
- Garantir que `MoonshotBackend.name` retorna `"moonshot"` (já implementado).
- Nenhuma outra mudança necessária.

## Testes de integração

### Arquivos relevantes
- `tests/test_proxy/test_openai_backend_path.py` — padrão de mock de backend.
- `tests/test_proxy/test_bedrock_passthrough.py` — mock de transporte HTTP.
- `tests/test_backends/test_moonshot.py` — mock transport simples.
- `headroom/proxy/server.py::create_app`, `ProxyConfig`

### Padrão recomendado para Moonshot
1. `ProxyConfig(backend="moonshot", optimize=False, cache_enabled=False, rate_limit_enabled=False)`.
2. `create_app(config)` + `TestClient(app)`.
3. Acessar `client.app.state.proxy.anthropic_backend` para obter instância real do `MoonshotBackend`.
4. Substituir `backend._client` por um `httpx.AsyncClient` com `MockTransport`.
5. POST `/v1/chat/completions` e verificar resposta/headers/modelo.
6. Para cache: instalar `PrefixCacheTracker` stub como em `test_openai_backend_path.py`.
7. Para compressão: usar `optimize=True` e verificar que mensagens foram alteradas.
8. Para telemetria: verificar `RequestLog` ou `/stats`.
