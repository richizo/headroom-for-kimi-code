---
phase: 03-thinking-reasoning
type: plan
status: pending
---

# Phase 3 Plan — Suporte a thinking/reasoning (Moonshot)

## Objetivo de entrega
- Testes de integração do backend Moonshot cobrindo:
  1. Thinking habilitado (`type: enabled`) retorna `reasoning_content`.
  2. Thinking desabilitado (`type: disabled`) não retorna `reasoning_content`.
  3. Modo instant funciona sem enviar `thinking`.
- Fixture de resposta Moonshot com `reasoning_content`.
- Se necessário, ajuste mínimo no backend para garantir pass-through transparente do `thinking` e `reasoning_content`.
- Atualização da documentação wiki/CLI sobre uso de thinking com Moonshot.

## Task breakdown

### Task 03-01 — Verificar pass-through no backend
- Arquivo: `headroom/backends/moonshot_backend.py`
- Confirmar que `send_openai_message` encaminha `thinking` no request body.
- Confirmar que `send_openai_message` retorna `reasoning_content` sem filtrar.
- Se houver filtro, adicionar `reasoning_content` aos campos permitidos/preservados.
- Adicionar docstring/test hint sobre campos thinking.

### Task 03-02 — Fixture de resposta com reasoning
- Arquivo: `tests/fixtures/moonshot/thinking_response.json` (ou local equivalente)
- Criar fixture contendo:
  - `choices[0].message.content`
  - `choices[0].message.reasoning_content`
  - Campos padrão (`id`, `object`, `created`, `model`, `usage`)

### Task 03-03 — Testes de backend
- Arquivo: `tests/test_backends/test_moonshot.py` (criar se não existir)
- Testes:
  - `test_moonshot_thinking_enabled_returns_reasoning_content`
  - `test_moonshot_thinking_disabled_does_not_return_reasoning_content`
  - `test_moonshot_instant_mode_no_thinking_parameter`
  - `test_moonshot_reasoning_content_passed_to_client`
- Usar `responses` ou `httpx.MockTransport` para mockar a upstream Moonshot.

### Task 03-04 — Testes de proxy/integração
- Arquivo: `tests/integrations/test_proxy_moonshot.py` (se existir padrão similar)
- Teste end-to-end simulando request do cliente → proxy → mock upstream → cliente.
- Validar que `reasoning_content` aparece no JSON final.

### Task 03-05 — Documentação
- Arquivo: `wiki/moonshot.md` (criar/atualizar)
- Documentar:
  - Como habilitar thinking (`extra_body` ou `thinking` no body)
  - Modelos suportados
  - Campo `reasoning_content` na resposta
  - Modo instant
- Atualizar `CHANGELOG.md` ou equivalente se o projeto usar.

## Critérios de aceitação
- [ ] Task 03-01 concluída sem quebra de compatibilidade.
- [ ] Fixtures criados e reutilizáveis.
- [ ] Todos os testes novos passam.
- [ ] Suite de testes existente continua passando (`rtk pytest tests/test_backends/ tests/integrations/`).
- [ ] Documentação wiki atualizada.

## Notas
- Não implementar parsing estrutural de `reasoning_content`; manter pass-through.
- Se a API exigir `thinking: null` para desabilitar em modelos que não suportam, testar e documentar.
