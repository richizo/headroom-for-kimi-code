# Moonshot (Kimi)

Headroom can proxy OpenAI-compatible chat requests to [Moonshot AI](https://www.moonshot.cn/) (Kimi models). Set the backend when starting the proxy:

```bash
export MOONSHOT_API_KEY="sk-..."
headroom proxy --backend moonshot
```

## Supported models

Any model ID starting with `kimi-` is accepted. Common examples:

- `kimi-k2`
- `kimi-k2.6`
- `kimi-k2.5`
- `kimi-latest`

`kimi-latest` is resolved dynamically against the Moonshot `/v1/models` endpoint before forwarding.

## Thinking / reasoning mode

Moonshot thinking models accept a `thinking` object in the request body:

```json
{
  "model": "kimi-k2.6",
  "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
  "thinking": {"type": "enabled", "keep": "all"}
}
```

When thinking is enabled, the response includes the model's internal reasoning in `choices[0].message.reasoning_content`:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "A resposta final é 42.",
      "reasoning_content": "Preciso somar 40 + 2. 40 + 2 = 42."
    }
  }]
}
```

Headroom forwards both the `thinking` parameter and the `reasoning_content` response field transparently, so downstream clients receive the full reasoning output.

### Instant mode

To disable thinking, send `thinking.type: disabled`:

```json
{
  "model": "kimi-k2.6",
  "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
  "thinking": {"type": "disabled"}
}
```

In instant mode the response will not contain `reasoning_content`.

## Streaming

Moonshot streaming is supported for `/v1/chat/completions`. Send `stream: true` as usual:

```json
{
  "model": "kimi-k2.6",
  "messages": [{"role": "user", "content": "Quanto é 40 + 2?"}],
  "stream": true,
  "thinking": {"type": "enabled"}
}
```

The proxy returns a standard SSE stream. When thinking is enabled, reasoning tokens appear in `delta.reasoning_content`:

```text
data: {"choices":[{"delta":{"reasoning_content":"Preciso somar"}}]}

data: {"choices":[{"delta":{"reasoning_content":" 40 + 2."}}]}

data: {"choices":[{"delta":{"content":"A resposta final é 42."}}]}

data: [DONE]

```

You can also set `stream_options: {"include_usage": true}` to receive a final usage chunk, just like OpenAI.
