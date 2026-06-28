# Kimi Code + Headroom

Este guia mostra como usar o Headroom como proxy de otimização de contexto para o [Kimi Code](https://www.kimi.com/code), o agente de coding da Moonshot AI.

## O que é Kimi Code

Kimi Code é um agente de coding em terminal (e extensão VS Code) da Moonshot AI. Ele expõe uma API compatível com OpenAI em:

```text
https://api.kimi.com/coding/v1
```

Modelo padrão: `kimi-for-coding` (o backend resolve automaticamente para a versão mais recente do modelo de coding).

## Compilar e instalar o Headroom

O Headroom usa uma extensão Rust (`headroom._core`) exposta via [maturin](https://www.maturin.rs/). Para compilar e instalar em modo editável:

```bash
# Clone (se ainda não tiver)
cd /caminho/para/headroom

# Instala o maturin e as dependências do proxy
pip install maturin
pip install -e ".[proxy]"
```

Verifique a instalação:

```bash
headroom --version
python -c "import headroom._core; print('Rust core OK')"
```

## Iniciar o proxy para Kimi Code

O Headroom já possui backend nativo para Moonshot (`--backend moonshot`). Aponte a URL base para o endpoint de coding da Moonshot:

```bash
export MOONSHOT_API_KEY="<sua-chave-do-kimi-code>"
export MOONSHOT_BASE_URL="https://api.kimi.com/coding/v1"
export ANTHROPIC_API_KEY="sk-ant-dummy"  # obrigatório para o proxy, mas ignorado no modo moonshot

headroom proxy \
  --backend moonshot \
  --host 127.0.0.1 \
  --port 8787 \
  --no-telemetry
```

O proxy vai expor:

- `http://127.0.0.1:8787/v1/chat/completions` — compatível com OpenAI/Kimi Code
- `http://127.0.0.1:8787/coding/v1/search` — web search do Kimi Code
- `http://127.0.0.1:8787/coding/v1/fetch` — web fetch do Kimi Code
- `/health`, `/stats`, `/metrics` — observabilidade

## Configurar o Kimi Code CLI para usar o Headroom

O Kimi Code CLI permite configurar providers customizados em `~/.kimi-code/config.toml`. Crie ou edite o arquivo:

```toml
# Modelo padrão via proxy Headroom
default_model = "headroom/kimi-for-coding"

# Modelo que usa o proxy Headroom
[models."headroom/kimi-for-coding"]
provider = "headroom"
model = "kimi-for-coding"
max_context_size = 262144
capabilities = [ "thinking", "always_thinking", "image_in", "video_in", "tool_use" ]
display_name = "Headroom Kimi"

# Provider Headroom (OpenAI-compatible) apontando para o proxy local
[providers."headroom"]
name = "Headroom Proxy"
base_url = "http://127.0.0.1:8787/v1"
api_key = "sk-dummy"  # o Headroom ignora essa chave; ela só satisfaz o client
model = "kimi-for-coding"
type = "openai"

# Ferramentas de search e fetch também roteadas pelo proxy
[services.moonshot_search]
base_url = "http://127.0.0.1:8787/coding/v1/search"
api_key = ""

[services.moonshot_search.oauth]
storage = "file"
key = "oauth/kimi-code"

[services.moonshot_fetch]
base_url = "http://127.0.0.1:8787/coding/v1/fetch"
api_key = ""

[services.moonshot_fetch.oauth]
storage = "file"
key = "oauth/kimi-code"
```

Depois, dentro do Kimi Code, use `/provider headroom` (ou o comando equivalente do seu `kimi-code`) para trocar para o provider Headroom.

> **Nota:** A chave `api_key` no client é obrigatória no formato, mas o Headroom descarta esse valor e envia `MOONSHOT_API_KEY` para a upstream. Nunca coloque sua chave real do Kimi Code no client quando estiver usando o proxy local.

## Usar com outras ferramentas compatíveis

Qualquer ferramenta que aceite OpenAI-compatible base URL pode usar o Headroom + Kimi Code:

```bash
# Claude Code (modo OpenAI-compatible, se suportado)
OPENAI_BASE_URL=http://127.0.0.1:8787/v1 \
OPENAI_API_KEY=sk-dummy \
claude

# Roo Code / Cline / OpenCode
# Configure no app:
#   Base URL: http://127.0.0.1:8787/v1
#   Model: kimi-for-coding
#   API Key: sk-dummy
```

## Ativar thinking/reasoning

Kimi Code suporta thinking via parâmetro `thinking`. Com Headroom, basta enviá-lo no body da request:

```json
{
  "model": "kimi-for-coding",
  "messages": [{"role": "user", "content": "Refatore essa função"}],
  "thinking": {"type": "enabled", "keep": "all"}
}
```

No modo não-streaming, o raciocínio vem em `choices[0].message.reasoning_content`.  
No modo streaming, vem em `delta.reasoning_content`.

## Streaming

O Kimi Code também funciona com `stream: true` através do Headroom:

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dummy" \
  -d '{
    "model": "kimi-for-coding",
    "messages": [{"role": "user", "content": "Escreva um hello world em Python"}],
    "stream": true
  }'
```

## Verificar se está funcionando

Teste o proxy com curl (não-streaming):

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dummy" \
  -d '{
    "model": "kimi-for-coding",
    "messages": [{"role": "user", "content": "Oi"}]
  }'
```

Se a configuração estiver correta, você verá uma resposta do Kimi Code passando pelo Headroom.

## Observabilidade

Enquanto o proxy roda, você pode acompanhar:

```bash
# Estatísticas de compressão e savings
curl -s http://127.0.0.1:8787/stats | python -m json.tool

# Dashboard (se houver processo headroom dashboard)
headroom dashboard
```

O dashboard mostra o agente `moonshot` com as requisições de `chat/completions`, `search` e `fetch` agrupadas.

## Notas importantes

- A API do Kimi Code usa autenticação via API Key criada no [Kimi Code Console](https://www.kimi.com/code/console).
- O Kimi Code Console permite até 5 chaves; cada chave é exibida apenas uma vez no momento da criação.
- O quota do Kimi Code é compartilhado entre CLI, VS Code e requisições via API Key.
- Não altere o `User-Agent` do client; isso pode violar os termos de uso da Moonshot.
- As ferramentas `search` e `fetch` do Kimi Code agora passam pelo proxy Headroom; o encaminhamento é passthrough (verbatim) para a API Kimi, mantendo a mesma autenticação e formato de request.
