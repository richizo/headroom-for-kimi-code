# Phase 1: Backend Moonshot non-streaming - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 1-Backend Moonshot non-streaming
**Areas discussed:** Ativação do backend, Fonte de configuração, Mapeamento de aliases, Propagação de erros

---

## Ativação do backend

| Option | Description | Selected |
|--------|-------------|----------|
| Flag `--backend moonshot` | O usuário passa explicitamente `--backend moonshot` no CLI do proxy; `create_proxy_backend` instancia MoonshotBackend | ✓ |
| Auto-detecção pelo model ID | O proxy detecta model IDs `kimi-*` no request e roteia automaticamente para MoonshotBackend, sem flag extra | |
| Ambos: flag padrão, auto-detecção como fallback | Se `--backend moonshot` estiver setado, usa o backend; caso contrário, detecta pelo model ID quando receber `kimi-*` | |

**User's choice:** Flag `--backend moonshot` (igual aos backends existentes)
**Notes:** Decisão alinhada com o padrão de `create_proxy_backend` em `headroom/providers/registry.py`.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Apenas `/v1/chat/completions` OpenAI-style | O backend implementa `send_openai_message`; requisições Anthropic Messages seriam rejeitadas ou convertidas pelo proxy | |
| Tanto OpenAI quanto Anthropic, convertendo internamente | O backend implementa `send_message` também, convertendo Anthropic → OpenAI → Moonshot | |
| Você decide | Deixar a escolha para o agente de planejamento baseado no padrão dos backends existentes | ✓ |

**User's choice:** Você decide
**Notes:** Planejador deve avaliar se implementa apenas `send_openai_message` (preferido por ser OpenAI-compatible) ou também `send_message`.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sim, múltiplos perfis | `--backend moonshot:<profile>` permite múltiplas credenciais/endpoint | |
| Não, um perfil por instância | Simples: `--backend moonshot` usa o perfil default/configurado | ✓ |

**User's choice:** Não, um perfil por instância de proxy
**Notes:** Mantém a implementação inicial simples.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Reutilizar config existente | API key/base_url vêm de variáveis de ambiente ou arquivo de config do Headroom; sem novas flags CLI | ✓ |
| Adicionar flags CLI dedicadas | Criar `--moonshot-api-key` e `--moonshot-base-url` no `headroom proxy` | |
| Você decide | Planejador decide baseado no padrão dos backends existentes | |

**User's choice:** Reutilizar config existente
**Notes:** Evita aumentar a surface area do CLI.

---

| Option | Description | Selected |
|--------|-------------|----------|
| `--backend moonshot` | Simples e consistente com a convenção dos backends nativos | ✓ |
| `--backend native-moonshot` | Diferencia backends nativos de wrappers LiteLLM/anyllm | |
| `--backend moonshot:<profile>` | Namespaceia perfis (reservado para futuro) | |

**User's choice:** `--backend moonshot`
**Notes:** Nome final confirmado.

---

## Fonte de configuração

| Option | Description | Selected |
|--------|-------------|----------|
| Variável de ambiente `MOONSHOT_API_KEY` | Simples, consistente com a maioria dos provedores | |
| Arquivo de config YAML/JSON | Permite múltiplos perfis e ambientes | |
| Ambos: env var como fallback, arquivo opcional | Flexível: usa arquivo se existir, senão env var | ✓ |

**User's choice:** Ambos: env var como fallback, arquivo de config opcional
**Notes:** API key pode vir de `MOONSHOT_API_KEY` ou de perfil em arquivo de config.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Default `https://api.moonshot.ai/v1` | Padrão internacional; override via `MOONSHOT_BASE_URL` | ✓ |
| Default `https://api.moonshot.cn/v1` | Padrão China; override para .ai | |
| Sem default — obrigatório especificar | Força o usuário a escolher endpoint | |
| Você decide | Planejador decide baseado em convenções do Headroom | |

**User's choice:** Default `https://api.moonshot.ai/v1` com override via env var `MOONSHOT_BASE_URL`
**Notes:** Endpoint internacional como padrão; variável para customização.

---

## Mapeamento de aliases

| Option | Description | Selected |
|--------|-------------|----------|
| Mapa estático hardcoded | `kimi-latest` → modelo atual; simples, mas requer atualização manual | |
| Buscar dinamicamente de `/v1/models` | Descobre o modelo apontado por `kimi-latest` no startup | ✓ |
| Permitir override via config | Usuário pode definir seus próprios aliases | |

**User's choice:** Buscar dinamicamente de `/v1/models` no startup
**Notes:** Resolve alias no boot, evitando surpresas quando a Moonshot atualizar.

---

## Propagação de erros

| Option | Description | Selected |
|--------|-------------|----------|
| Passthrough — retornar status code e body exatos | Máxima fidelidade com a API OpenAI-compatible | ✓ |
| Normalizar para formato de erro padrão do Headroom | Consistência, mas perde detalhes específicos | |
| Passthrough com logging/telemetria interna | Retorna erro original, mas loga normalizado internamente | |

**User's choice:** Passthrough — retornar status code e body exatos da upstream
**Notes:** Preserva compatibilidade OpenAI para clientes como Kimi Code CLI.

---

## Claude's Discretion

- Decisão sobre atender apenas endpoint OpenAI-style vs também converter Anthropic Messages foi delegada ao planejador.

## Deferred Ideas

None — discussion stayed within phase scope
