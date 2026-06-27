# Feature Research

**Domain:** Backend Moonshot/Kimi para Headroom
**Researched:** 2026-06-27
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Chat completions non-streaming | Funcionalidade básica de qualquer backend LLM | LOW | Endpoint `/v1/chat/completions` com `stream: false` |
| Autenticação via API key | Padrão de mercado; sem isso não funciona | LOW | Header `Authorization: Bearer <key>` |
| Mapeamento de modelos | Usuário espera usar `kimi-k2`, `kimi-latest` | LOW | Mapa simples de IDs canônicos para IDs do provedor |
| Configuração de endpoint/base_url | Permite usar endpoints China (`api.moonshot.cn`) ou internacional (`api.moonshot.ai`) | LOW | Campo no perfil de backend |
| Compatibilidade OpenAI | A Moonshot promete compatibilidade; quebrar isso gera surpresa | MEDIUM | Testar campos não-padrão (`reasoning_content`, `enable_thinking`) |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Suporte a thinking/reasoning | Permite usar `kimi-k2` no modo raciocínio, expondo `reasoning_content` | MEDIUM | Requer parsing de campo extra no response |
| Controle de `enable_thinking` | Alternar entre modo thinking e instant via config/extra_body | LOW-MEDIUM | Parâmetro não-padrão OpenAI |
| Múltiplos perfis de backend | Suportar diferentes keys/endpoints para dev/prod | LOW | Seguir padrão de config do Headroom |
| Cache + compressão + telemetria aplicadas ao Kimi | Este é o valor principal do Headroom | LOW | Reaproveitar middlewares existentes do proxy |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Suporte a embeddings na v1 | "Já que estamos integrando, suportar tudo" | Aumenta escopo sem validar uso real; embeddings têm padrões de cache diferentes | Deixar fora do escopo inicial |
| Suporte a imagem/vídeo na v1 | Modelos K2.5+ suportam multimodal | Complexidade de upload/base64; não alinhado ao caso de uso Kimi Code CLI | Deferir para fase posterior |
| Implementar SDK próprio da Moonshot | "SDK oficial pode ser mais robusto" | Não há SDK oficial maduro; adiciona dependência desnecessária | Usar OpenAI SDK ou httpx |
| Streaming na v1 | "Streaming é essencial para UX" | Complexidade inicial; non-streaming valida conversão primeiro | Implementar em fase posterior |

## Feature Dependencies

```
[Chat completions non-streaming]
    └──requires──> [Autenticação + mapeamento de modelos]
        └──requires──> [Configuração de perfil de backend]

[Thinking/reasoning support]
    └──requires──> [Chat completions non-streaming]
        └──enhances──> [Differentiator]

[Cache/compressão/telemetria]
    └──requires──> [Backend registrado no proxy]
```

### Dependency Notes

- **Chat completions requer autenticação/mapeamento:** sem mapear modelos e autenticar, o backend não consegue fazer uma request válida.
- **Thinking depende de chat completions:** é uma variação do response parsing, não uma feature independente.
- **Cache/compressão/telemetria dependem do backend estar registrado:** os middlewares do proxy descobrem o backend pelo model ID; sem registro, as otimizações não são aplicadas.

## MVP Definition

### Launch With (v1)

- [ ] Chat completions non-streaming para modelos `kimi-k2` e `kimi-latest`
- [ ] Autenticação via perfil de backend (`api_key`)
- [ ] Mapeamento de modelos canônicos para IDs Moonshot
- [ ] Registro do backend no discovery de backends do Headroom
- [ ] Testes unitários/integração cobrindo request/response básicos

### Add After Validation (v1.x)

- [ ] Streaming de respostas (`stream: true`)
- [ ] Suporte a `reasoning_content` / thinking mode
- [ ] Suporte a `enable_thinking` via config ou extra_body

### Future Consideration (v2+)

- [ ] Embeddings `/v1/embeddings`
- [ ] Multimodal (image/video input)
- [ ] Tool calling específico da Moonshot

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Chat completions non-streaming | HIGH | LOW | P1 |
| Autenticação/mapeamento | HIGH | LOW | P1 |
| Registro no discovery | HIGH | LOW | P1 |
| Cache/compressão/telemetria | HIGH | LOW | P1 |
| Streaming | MEDIUM | MEDIUM | P2 |
| Thinking/reasoning | MEDIUM | MEDIUM | P2 |
| Embeddings | LOW | MEDIUM | P3 |
| Multimodal | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | LiteLLM (backend existente) | Backend nativo Moonshot (nosso plano) |
|---------|------------------------------|----------------------------------------|
| Provedores suportados | 100+ | Apenas Moonshot/Kimi |
| Controle de mapeamento | Limitado ao que LiteLLM expõe | Total |
| Telemetria granular | Genérica | Específica para Moonshot |
| Overhead | Depende do LiteLLM | Direto, menor overhead |
| Manutenção | Terceirizada | Própria |

## Sources

- Documentação oficial Moonshot/OpenAI-compatible
- GitHub MoonshotAI/Kimi-K2.5
- Backends existentes do Headroom (`litellm.py`, `anyllm.py`, `base.py`)

---
*Feature research for: Moonshot/Kimi backend integration into Headroom*
*Researched: 2026-06-27*
