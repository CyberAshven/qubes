# AI Models

Qubes supports 46+ AI models across 6 providers with automatic fallback chains.

## Supported Providers

| Provider | Models | Strengths |
|----------|--------|-----------|
| OpenAI | GPT-4o, GPT-4 Turbo, o1, o3-mini | Best all-around, vision support |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus | Strong reasoning, long context |
| Google | Gemini 2.0, Gemini 1.5 Pro | Multimodal, large context |
| Perplexity | Sonar Pro, Sonar | Real-time web search |
| DeepSeek | DeepSeek Chat, Reasoner | Cost-effective, good reasoning |
| Ollama | Llama, Mistral, etc. | Local/private, no API costs |

## Model Registry

Models are defined in `ai/model_registry.py`:

```python
MODELS = {
    "gpt-4o": {
        "provider": "openai",
        "context_window": 128000,
        "supports_vision": True,
        "supports_tools": True,
        "cost_per_1k_input": 0.0025,
        "cost_per_1k_output": 0.01
    },
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "context_window": 200000,
        "supports_vision": True,
        "supports_tools": True,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015
    },
    # ... 44 more models
}
```

## Configuration

### Per-Qube Model Selection
Each Qube can have its own preferred model:

```yaml
# In qube's config
ai:
  model: "gpt-4o"
  fallback_models:
    - "claude-3-5-sonnet-20241022"
    - "gemini-2.0-flash"
  temperature: 0.7
  max_tokens: 4096
```

### Global Defaults
Set in user settings:

```yaml
ai:
  default_model: "gpt-4o"
  fallback_chain:
    - "claude-3-5-sonnet-20241022"
    - "gemini-1.5-pro"
    - "deepseek-chat"
```

## Fallback Chain

When a model fails (rate limit, error, etc.), the reasoner automatically tries the next model:

```
Primary Model (gpt-4o)
    │ fails
    ▼
Fallback 1 (claude-3-5-sonnet)
    │ fails
    ▼
Fallback 2 (gemini-1.5-pro)
    │ fails
    ▼
Error returned to user
```

## Tool Calling

Most models support tool/function calling:

```python
# From ai/reasoner.py
tools = [
    {
        "name": "search_memory",
        "description": "Search the Qube's memory chain",
        "parameters": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
        }
    },
    {
        "name": "web_search",
        "description": "Search the web for information",
        "parameters": {
            "query": {"type": "string"}
        }
    }
]
```

Available tools depend on Qube's unlocked skills.

## Vision Support

Models with vision support can analyze images:

```python
# Image in message
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
}
```

Supported: GPT-4o, GPT-4 Turbo, Claude 3.x, Gemini 1.5+

## Streaming

All providers support streaming responses:

```python
async for chunk in reasoner.reason_stream(message):
    yield chunk.content
```

## Cost Tracking

The system tracks API costs:

```python
# From monitoring/metrics.py
MetricsRecorder.record_ai_cost("openai", 0.0025)
MetricsRecorder.record_ai_api_call("openai", "gpt-4o", "success")
```

## Provider-Specific Notes

### OpenAI
- Best tool calling support
- o1/o3 models use "reasoning tokens" (more expensive)
- Rate limits vary by tier

### Anthropic
- 200K context window (largest)
- Strong at following complex instructions
- Cache-aware for repeated contexts

### Google
- 1M context window on Gemini 1.5 Pro
- Good multimodal (images, audio, video)
- Free tier available

### Perplexity
- Real-time web search built-in
- Best for current events
- No tool calling support

### DeepSeek
- Very cost-effective
- Good reasoning with DeepSeek-Reasoner
- Chinese company (consider data residency)

### Ollama
- Runs locally, no API costs
- Privacy-preserving
- Requires local GPU for good performance
- Configure endpoint in settings
