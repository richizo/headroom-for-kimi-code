---
phase: 03-thinking-reasoning
type: context
---

# Phase 3 Context — Suporte a thinking/reasoning

## Objetivo
Permitir uso dos modelos Kimi em modo thinking, expondo o conteúdo de raciocínio (`reasoning_content`) ao cliente, e garantir que o modo instant (thinking desabilitado) continue funcionando.

## Escopo
- Non-streaming apenas (streaming é Phase 4).
- Foco no parâmetro `thinking` da API Moonshot e no campo `reasoning_content` da resposta.
- Modelos: `kimi-k2.6`, `kimi-k2.5` e variantes thinking.

## Descobertas da pesquisa

### API Moonshot
- Parâmetro de request: `thinking` (objeto), não `enable_thinking`:
  ```json
  {
    "thinking": {
      "type": "enabled" | "disabled",
      "keep": "all" | null
    }
  }
  ```
- Campo de resposta: `reasoning_content` dentro do objeto `message` do assistente:
  ```json
  {
    "choices": [{
      "message": {
        "role": "assistant",
        "content": "final answer",
        "reasoning_content": "internal chain-of-thought..."
      }
    }]
  }
  ```
- Modelos que suportam thinking:
  - `kimi-k2.6`: thinking habilitado por padrão, pode desabilitar, suporta `keep: "all"`
  - `kimi-k2.5`: thinking habilitado por padrão, pode desabilitar, não suporta `keep`
  - `kimi-k2.7-code`: thinking sempre ativo
  - `kimi-k2-thinking`, `kimi-k2-thinking-turbo`: thinking sempre ativo

### Headroom
- O proxy encaminha o body da request e da response de forma opaca para backends OpenAI-compatible.
- `MoonshotBackend.send_openai_message` já passa o body e retorna o response sem alterações.
- Não há backend Python que parseie `reasoning_content` estruturalmente; ele é tratado como campo opaco.
- Não existem testes para `reasoning_content` ou `thinking` do Moonshot.

## Hipóteses a validar
1. Enviar `"thinking": {"type": "enabled"}` resulta em response com `reasoning_content`.
2. Enviar `"thinking": {"type": "disabled"}` resulta em response sem `reasoning_content` (modo instant).
3. O campo `reasoning_content` é preservado no response ao cliente.
4. O parâmetro `thinking` é encaminhado corretamente para a upstream Moonshot.

## Riscos
- A API Moonshot pode evoluir; nomes de campos ou comportamentos podem mudar.
- Modelos `kimi-k2.7-code` não permitem `thinking.type: disabled`; testes devem refletir isso.
- `reasoning_content` conta para o orçamento de output tokens e deve ser preservado em multi-turn.

## Fora de escopo
- Streaming de reasoning content.
- Validação automática de temperatura/max_tokens por modelo.
- Implementação de reasoning_content em outros backends.
