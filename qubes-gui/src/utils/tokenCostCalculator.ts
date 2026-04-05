/**
 * Token cost calculator for AI models
 * Calculates costs in USD and BCH with 8 decimal precision
 */

// Model pricing (per 1M tokens) - Updated April 2026
const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  // Anthropic Claude models
  'claude-opus-4-6-20260204': { input: 5.00, output: 25.00 },
  'claude-sonnet-4-6-20260217': { input: 3.00, output: 15.00 },
  'claude-haiku-4-5-20251001': { input: 1.00, output: 5.00 },
  'claude-sonnet-4-5-20250929': { input: 3.00, output: 15.00 },
  'claude-opus-4-1-20250805': { input: 15.00, output: 75.00 },
  'claude-sonnet-4-20250514': { input: 3.00, output: 15.00 },
  'claude-3-5-haiku-20241022': { input: 0.25, output: 1.25 },

  // OpenAI models
  'gpt-5.4': { input: 5.00, output: 15.00 },
  'gpt-4o': { input: 2.50, output: 10.00 },
  'gpt-4o-mini': { input: 0.15, output: 0.60 },
  'gpt-4-turbo': { input: 10.00, output: 30.00 },
  'gpt-4': { input: 30.00, output: 60.00 },
  'gpt-3.5-turbo': { input: 0.50, output: 1.50 },
  'o1': { input: 15.00, output: 60.00 },
  'o1-mini': { input: 3.00, output: 12.00 },
  
  // Google Gemini models
  'gemini-2.0-flash-exp': { input: 0.00, output: 0.00 }, // Free tier
  'gemini-1.5-pro': { input: 1.25, output: 5.00 },
  'gemini-1.5-flash': { input: 0.075, output: 0.30 },
  
  // DeepSeek models
  'deepseek-chat': { input: 0.14, output: 0.28 },
  'deepseek-reasoner': { input: 0.55, output: 2.19 },
  
  // xAI models
  'grok-beta': { input: 5.00, output: 15.00 },
};

// Current BCH/USD exchange rate (should be updated periodically)
// As of October 2025: ~$350 per BCH (estimate)
const BCH_USD_RATE = 350.00;

export interface TokenCost {
  usd: number;
  bch: number;
  breakdown: {
    inputCostUSD: number;
    outputCostUSD: number;
  };
}

/**
 * Calculate cost for AI model usage
 * @param modelName - The AI model identifier
 * @param inputTokens - Number of input tokens
 * @param outputTokens - Number of output tokens
 * @returns Cost breakdown in USD and BCH
 */
export function calculateTokenCost(
  modelName: string,
  inputTokens: number,
  outputTokens: number
): TokenCost | null {
  const pricing = MODEL_PRICING[modelName];
  
  if (!pricing) {
    // Unknown model, return null
    return null;
  }
  
  // Calculate costs (pricing is per 1M tokens)
  const inputCostUSD = (inputTokens / 1_000_000) * pricing.input;
  const outputCostUSD = (outputTokens / 1_000_000) * pricing.output;
  const totalUSD = inputCostUSD + outputCostUSD;
  
  // Convert to BCH
  const totalBCH = totalUSD / BCH_USD_RATE;
  
  return {
    usd: totalUSD,
    bch: totalBCH,
    breakdown: {
      inputCostUSD,
      outputCostUSD,
    },
  };
}

/**
 * Format USD amount with 8 decimal places
 */
export function formatUSD(amount: number): string {
  return amount.toFixed(8);
}

/**
 * Format BCH amount with 8 decimal places
 */
export function formatBCH(amount: number): string {
  return amount.toFixed(8);
}

/**
 * Get pricing info for a model (for display purposes)
 */
export function getModelPricing(modelName: string): { input: number; output: number } | null {
  return MODEL_PRICING[modelName] || null;
}
