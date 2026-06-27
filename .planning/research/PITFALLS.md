# Pitfalls Research

**Domain:** Integração de backend Moonshot/Kimi no Headroom
**Researched:** 2026-06-27
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Assumir compatibilidade OpenAI 100% sem validar campos não-padrão

**What goes wrong:**
A API Moonshot é OpenAI-compatible, mas possui campos e comportamentos específicos (`reasoning_content`, restrições de `temperature`, `enable_thinking`). Ignorá-los pode causar falhas silenciosas ou erros `400`/`422` vindos da upstream.

**Why it happens:**
Desenvolvedores veem "OpenAI-compatible" e tratam o provedor como idêntico à OpenAI.

**How to avoid:**
- Validar request/response com exemplos reais da Moonshot
- Documentar campos não-padrão suportados
- Adicionar testes de integração que usem respostas reais (sanitizadas)

**Warning signs:**
- Erros `invalid temperature: only 1 is allowed for this model`
- Responses vindo sem `reasoning_content` esperado
- Diferenças entre `.cn` e `.ai` endpoints

**Phase to address:**
Fase 1 — implementação do backend non-streaming

---

### Pitfall 2: Propagar API key do cliente para o provedor

**What goes wrong:**
O proxy pode acidentalmente usar a chave enviada pelo cliente no header `Authorization`, em vez da chave configurada no perfil de backend. Isso pode causar autenticação inesperada ou vazamento de credenciais.

**Why it happens:**
Backends OpenAI-compatible tendem a reaproveitar headers do cliente.

**How to avoid:**
- Sempre substituir o header `Authorization` pela chave do perfil de backend
- Não logar a chave em telemetria
- Testar que o header de upstream não contém a chave do cliente

**Warning signs:**
- Testes passam localmente mas falham em staging (chave diferente)
- Logs expondo prefixos de chaves

**Phase to address:**
Fase 1 — configuração e autenticação

---

### Pitfall 3: Mapeamento de modelos quebrado para aliases

**What goes wrong:**
Aliases como `kimi-latest` podem apontar para modelos diferentes ao longo do tempo. Se o backend não resolver o alias corretamente, o request pode falhar ou usar modelo inesperado.

**Why it happens:**
Aliases são convenientes para usuários, mas voláteis do lado do provedor.

**How to avoid:**
- Manter mapa explícito de aliases para IDs estáveis
- Atualizar o mapa quando novos modelos forem lançados
- Documentar que `kimi-latest` é resolvido no Headroom

**Warning signs:**
- `model_not_found` errors após deploy
- Mudanças de comportamento sem alteração de código

**Phase to address:**
Fase 1 — mapeamento de modelos

---

### Pitfall 4: Esquecer de registrar o backend no discovery

**What goes wrong:**
O backend pode estar implementado e testado, mas o proxy nunca o seleciona porque não foi registrado no registry/discovery de backends.

**Why it happens:**
O registry pode ser uma lista explícita em `__init__.py` ou uma factory; esquecer de adicionar o novo backend é comum.

**How to avoid:**
- Adicionar teste que itera todos os backends registrados e verifica que `MoonshotBackend` está presente
- Seguir o padrão dos backends existentes

**Warning signs:**
- Requests para `kimi-k2` retornam "model not supported" mesmo com backend implementado

**Phase to address:**
Fase 1 — registro e integração

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded base URL | Rápido de implementar | Impede múltiplos ambientes | Apenas em spike/POC descartável |
| Ignorar campos `extra_body` | Menos código | Perde funcionalidades Moonshot (thinking) | MVP sem reasoning |
| Não testar contra upstream real | Testes rápidos | Bugs só aparecem em produção | Nunca; usar mocks bem construídos + teste manual |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Moonshot API | Usar sempre `api.moonshot.cn` | Permitir configurar base URL (`api.moonshot.ai` ou `.cn`) |
| Moonshot API | Enviar `temperature` padrão 0.7 | Validar parâmetros suportados por modelo; usar defaults compatíveis |
| Moonshot API | Tratar `reasoning_content` como `content` | Separar reasoning_content em campo próprio no response mapping |
| Headroom proxy | Rotear requests OpenAI para `send_message()` | Usar `send_openai_message()` para provedores OpenAI-compatible |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Síncrono no caminho hot | Alta latência, bloqueio do event loop | Manter `send_openai_message` async | Qualquer carga simultânea |
| Criar novo httpx client por request | Fuga de conexões, lentidão | Reusar cliente ou usar singleton | A partir de dezenas de req/s |
| Não limitar timeout | Requests travam indefinidamente | Configurar timeout padrão (ex.: 60s) | Qualquer instabilidade upstream |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logar `api_key` | Vazamento de credencial | Sanitizar logs; nunca logar headers de autorização |
| Aceitar chave do cliente | Bypass de controles de custo/acesso | Sempre usar chave do perfil de backend |
| HTTP em vez de HTTPS | Man-in-the-middle | Default para `https://` e validar URLs |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Mensagem de erro genérica quando upstream falha | Usuário não sabe se é Headroom ou Moonshot | Propagar mensagem de erro da upstream de forma segura |
| Model ID não documentado | Usuário não sabe como chamar | Documentar IDs suportados em README/wiki |

## "Looks Done But Isn't" Checklist

- [ ] **Backend implementado:** Está registrado no discovery?
- [ ] **Autenticação:** A chave do perfil está sendo usada, não a do cliente?
- [ ] **Mapeamento:** Aliases como `kimi-latest` estão resolvidos?
- [ ] **Erros:** Mensagens de erro da Moonshot estão sendo propagadas corretamente?
- [ ] **Middlewares:** Cache/compressão/telemetria estão realmente aplicando ao backend novo?
- [ ] **Tests:** Existe teste que cobre request/response com body realístico?

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Compatibilidade quebrada | LOW | Ajustar parsing/serialização; adicionar teste de regressão |
| Chave vazada | HIGH | Rotacionar chave; revisar logs; auditar acessos |
| Modelo não encontrado | LOW | Atualizar mapa de modelos; comunicar aliases suportados |
| Backend não registrado | LOW | Adicionar ao registry; validar com teste de discovery |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Compatibilidade OpenAI não validada | Fase 1 | Teste de integração com mock de response Moonshot real |
| API key do cliente propagada | Fase 1 | Teste unitário verificando header de upstream |
| Alias não resolvido | Fase 1 | Teste de `map_model_id` para todos os aliases |
| Backend não registrado | Fase 1 | Teste de discovery listando todos os backends |
| Síncrono no caminho hot | Fase 1 | mypy + teste async |

## Sources

- Discussões da comunidade sobre compatibilidade Moonshot/OpenAI
- Documentação oficial Moonshot
- Padrões de segurança do Headroom
- Backends existentes do Headroom

---
*Pitfalls research for: Moonshot/Kimi backend integration into Headroom*
*Researched: 2026-06-27*
