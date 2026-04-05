/**
 * Helper function to format model names for display
 * Converts technical model IDs to human-readable names
 */
export function formatModelName(modelId: string): string {
  // Common model mappings - includes both full API names and short aliases
  const modelMap: Record<string, string> = {
    // OpenAI - GPT 5.x series (2025-2026)
    'gpt-5.4': 'GPT-5.4',
    'gpt-5.4-mini': 'GPT-5.4 Mini',
    'gpt-5.4-nano': 'GPT-5.4 Nano',
    'gpt-5.2': 'GPT-5.2',
    'gpt-5': 'GPT-5',
    'gpt-5-mini': 'GPT-5 Mini',
    'gpt-4.1': 'GPT-4.1',
    'gpt-4.1-mini': 'GPT-4.1 Mini',
    'o4-mini': 'O4 Mini',
    'o3': 'O3',
    'o3-pro': 'O3 Pro',
    'o3-mini': 'O3 Mini',
    'o1': 'O1',
    'gpt-4o': 'GPT-4o',
    'gpt-4o-mini': 'GPT-4o Mini',
    // Anthropic - full API names
    'claude-opus-4-6-20260204': 'Claude Opus 4.6',
    'claude-sonnet-4-6-20260217': 'Claude Sonnet 4.6',
    'claude-haiku-4-5-20251001': 'Claude Haiku 4.5',
    'claude-sonnet-4-5-20250929': 'Claude Sonnet 4.5',
    'claude-opus-4-1-20250805': 'Claude Opus 4.1',
    'claude-sonnet-4-20250514': 'Claude Sonnet 4',
    'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
    // Anthropic - short aliases
    'claude-opus-4-6': 'Claude Opus 4.6',
    'claude-sonnet-4-6': 'Claude Sonnet 4.6',
    'claude-haiku-4-5': 'Claude Haiku 4.5',
    'claude-sonnet-4.5': 'Claude Sonnet 4.5',
    'claude-opus-4.1': 'Claude Opus 4.1',
    'claude-sonnet-4': 'Claude Sonnet 4',
    'claude-3.5-haiku': 'Claude 3.5 Haiku',
    // Google - Gemini 3.1 and 2.5 series (2025-2026)
    'gemini-3.1-pro-preview': 'Gemini 3.1 Pro',
    'gemini-3-flash-preview': 'Gemini 3 Flash',
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'gemini-1.5-pro': 'Gemini 1.5 Pro',
    // Perplexity
    'sonar': 'Sonar',
    'sonar-pro': 'Sonar Pro',
    'sonar-reasoning-pro': 'Sonar Reasoning Pro',
    'sonar-deep-research': 'Sonar Deep Research',
    // DeepSeek
    'deepseek-chat': 'DeepSeek Chat',
    'deepseek-reasoner': 'DeepSeek Reasoner',
    // Venice - Privacy AI (2025-2026)
    'openai-gpt-54': 'GPT-5.4 (Venice)',
    'claude-opus-46': 'Claude Opus 4.6 (Venice)',
    'claude-sonnet-46': 'Claude Sonnet 4.6 (Venice)',
    'venice-uncensored': 'Venice Uncensored',
    'llama-3.3-70b': 'Llama 3.3 70B',
    'llama-3.2-3b': 'Llama 3.2 3B',
    'qwen3-235b-a22b-instruct-2507': 'Qwen3 235B Instruct',
    'qwen3-235b-a22b-thinking-2507': 'Qwen3 235B Thinking',
    'qwen3-next-80b': 'Qwen3 Next 80B',
    'qwen3-coder-480b-a35b-instruct': 'Qwen3 Coder 480B',
    'qwen3.5-35b-a3b': 'Qwen 3.5 35B',
    'qwen3-4b': 'Venice Small',
    'mistral-31-24b': 'Venice Medium',
    'grok-41-fast': 'Grok 4.1 Fast',
    'grok-code-fast-1': 'Grok Code Fast',
    'glm-5': 'GLM 5',
    'zai-org-glm-4.7': 'GLM 4.7',
    'kimi-k2-thinking': 'Kimi K2 Thinking',
    'minimax-m25': 'MiniMax M2.5',
    'minimax-m21': 'MiniMax M2.1',
    'deepseek-v3.2': 'DeepSeek V3.2',
    'google-gemma-3-27b-it': 'Gemma 3 27B',
    'hermes-3-llama-3.1-405b': 'Hermes 3 405B',
    'dolphin-2.9.3-mistral-7b': 'Venice Uncensored',
    // Ollama models
    'llama3.3:70b': 'Llama 3.3 70B',
    'llama3.2': 'Llama 3.2',
    'llama3.2:1b': 'Llama 3.2 1B',
    'llama3.2:3b': 'Llama 3.2 3B',
    'llama3.2-vision:11b': 'Llama 3.2 Vision 11B',
    'llama3.2-vision:90b': 'Llama 3.2 Vision 90B',
    'qwen3:235b': 'Qwen 3 235B',
    'qwen3:30b': 'Qwen 3 30B',
    'qwen2.5:7b': 'Qwen 2.5 7B',
    'deepseek-r1:8b': 'DeepSeek R1 8B',
    'phi4:14b': 'Phi 4 14B',
    'gemma2:9b': 'Gemma 2 9B',
    'mistral:7b': 'Mistral 7B',
    'codellama:7b': 'CodeLlama 7B',
    // NanoGPT models
    'nanogpt/gpt-4o': 'GPT-4o (NanoGPT)',
    'nanogpt/gpt-4o-mini': 'GPT-4o Mini (NanoGPT)',
    'nanogpt/claude-3-5-sonnet': 'Claude 3.5 Sonnet (NanoGPT)',
    'nanogpt/claude-3-haiku': 'Claude 3 Haiku (NanoGPT)',
    'nanogpt/llama-3.1-70b': 'Llama 3.1 70B (NanoGPT)',
    'nanogpt/llama-3.1-8b': 'Llama 3.1 8B (NanoGPT)',
    'nanogpt/mistral-large': 'Mistral Large (NanoGPT)',
    'nanogpt/mixtral-8x7b': 'Mixtral 8x7B (NanoGPT)',
  };

  if (modelMap[modelId]) return modelMap[modelId];

  // Fallback formatting for unknown models
  if (modelId.startsWith('gpt-')) {
    return modelId.toUpperCase().replace('GPT-', 'GPT-');
  }
  if (modelId.startsWith('claude-')) {
    const parts = modelId.replace('claude-', '').split('-');
    const name = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
    if (parts.length >= 3) {
      return `Claude ${name} ${parts[1]}.${parts[2]}`;
    }
    return `Claude ${name}`;
  }
  if (modelId.startsWith('gemini-')) {
    return modelId.split('-').map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
  }

  return modelId;
}
