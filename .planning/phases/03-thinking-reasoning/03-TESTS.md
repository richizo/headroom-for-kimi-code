---
phase: 03-thinking-reasoning
type: tests
---

# Phase 3 — Test Strategy

## Testes unitários/backend
- Local: `tests/test_backends/test_moonshot.py`
- Mock da upstream Moonshot via `responses`/`httpx`.
- Fixtures: `tests/fixtures/moonshot/thinking_response.json`, `instant_response.json`.

## Testes de integração
- Local: `tests/integrations/test_proxy_moonshot.py`
- Subir proxy em memória (`TestClient`) e mockar upstream.

## Comandos de execução
```bash
rtk pytest tests/test_backends/test_moonshot.py -v
rtk pytest tests/integrations/test_proxy_moonshot.py -v
rtk pytest tests/test_backends/ tests/integrations/ -v
```

## Critérios
- Todos os novos testes passam.
- Testes existentes de backend/integração continuam passando.
