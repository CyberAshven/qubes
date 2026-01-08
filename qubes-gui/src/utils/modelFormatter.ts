/**
 * Helper function to format model names for display
 * Converts technical model IDs to human-readable names
 */
export function formatModelName(modelId: string): string {
  // Common model mappings - includes both full API names and short aliases
  const modelMap: Record<string, string> = {
    // OpenAI
    'gpt-5-turbo': 'GPT-5 Turbo',
    'gpt-5': 'GPT-5',
    'gpt-5-mini': 'GPT-5 Mini',
    'gpt-5-nano': 'GPT-5 Nano',
    'gpt-5-codex': 'GPT-5 Codex',
    'gpt-4.1': 'GPT-4.1',
    'gpt-4.1-mini': 'GPT-4.1 Mini',
    'o4': 'GPT-O4',
    'o4-mini': 'GPT-O4 Mini',
    'o3-mini': 'GPT-O3 Mini',
    'o1': 'GPT-O1',
    'gpt-4o': 'GPT-4o',
    'gpt-4o-mini': 'GPT-4o Mini',
    // Anthropic - full API names
    'claude-sonnet-4-5-20250929': 'Claude Sonnet 4.5',
    'claude-opus-4-1-20250805': 'Claude Opus 4.1',
    'claude-opus-4-20250514': 'Claude Opus 4',
    'claude-sonnet-4-20250514': 'Claude Sonnet 4',
    'claude-3-7-sonnet-20250219': 'Claude 3.7 Sonnet',
    'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
    'claude-3-haiku-20240307': 'Claude 3 Haiku',
    // Anthropic - short aliases
    'claude-sonnet-4.5': 'Claude Sonnet 4.5',
    'claude-opus-4.1': 'Claude Opus 4.1',
    'claude-opus-4': 'Claude Opus 4',
    'claude-sonnet-4': 'Claude Sonnet 4',
    'claude-3.5-sonnet': 'Claude 3.5 Sonnet',
    'claude-3.5-haiku': 'Claude 3.5 Haiku',
    'claude-3-haiku': 'Claude 3 Haiku',
    // Google
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'gemini-1.5-pro': 'Gemini 1.5 Pro',
    // Perplexity
    'sonar': 'Sonar',
    'sonar-pro': 'Sonar Pro',
    'sonar-reasoning': 'Sonar Reasoning',
    'sonar-reasoning-pro': 'Sonar Reasoning Pro',
    'sonar-deep-research': 'Sonar Deep Research',
    // DeepSeek
    'deepseek-chat': 'DeepSeek Chat',
    'deepseek-reasoner': 'DeepSeek Reasoner',
    // Venice
    'venice-uncensored': 'Venice Uncensored',
    'llama-3.3-70b': 'Llama 3.3 70B',
    'qwen3-235b-a22b-instruct-2507': 'Qwen3 235B Instruct',
    'qwen3-4b': 'Qwen3 4B',
    'mistral-31-24b': 'Mistral 3.1 24B',
    'claude-opus-45': 'Claude Opus 4.5',
    'gemini-3-flash-preview': 'Gemini 3 Flash',
    'grok-41-fast': 'Grok 4.1 Fast',
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
