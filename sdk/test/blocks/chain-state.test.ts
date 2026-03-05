/**
 * Tests for blocks/chain-state — createDefaultChainState factory and provider detection.
 */
import { describe, it, expect } from 'vitest';
import { createDefaultChainState } from '../../src/blocks/chain-state.js';

const MOCK_GENESIS = {
  block_type: 'GENESIS',
  block_number: 0,
  qube_id: 'ABCD1234',
  timestamp: 1700000000,
  birth_timestamp: 1700000000,
  qube_name: 'TestQube',
  creator: 'user_001',
  public_key: '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2',
  ai_model: 'claude-sonnet-4-20250514',
  voice_model: 'openai:alloy',
  block_hash: 'f'.repeat(64),
  encrypted: false,
  temporary: false,
};

// ---------------------------------------------------------------------------
// Version
// ---------------------------------------------------------------------------

describe('createDefaultChainState version', () => {
  it('returns version "2.0"', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    expect(state.version).toBe('2.0');
  });
});

// ---------------------------------------------------------------------------
// Provider detection
// ---------------------------------------------------------------------------

describe('provider detection', () => {
  it('detects anthropic for claude model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'claude-sonnet-4-20250514',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('anthropic');
  });

  it('detects openai for gpt model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'gpt-4o',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('openai');
  });

  it('detects google for gemini model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'gemini-pro',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('google');
  });

  it('detects perplexity for sonar model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'sonar-medium-online',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('perplexity');
  });

  it('detects venice for venice model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'venice-uncensored',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('venice');
  });

  it('detects ollama for llama model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'llama-3.1-70b',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('ollama');
  });

  it('detects ollama for mistral model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'mistral-large',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('ollama');
  });

  it('detects ollama for qwen model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'qwen-72b',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('ollama');
  });

  it('defaults to anthropic for unknown model', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'some-unknown-model',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('anthropic');
  });

  it('uses fallback ai_provider if provided', () => {
    const state = createDefaultChainState({
      ...MOCK_GENESIS,
      ai_model: 'custom-model',
      ai_provider: 'custom_provider',
    });
    const runtime = state.runtime as Record<string, unknown>;
    expect(runtime.current_provider).toBe('custom_provider');
  });
});

// ---------------------------------------------------------------------------
// All 15 sections
// ---------------------------------------------------------------------------

describe('chain state sections', () => {
  const state = createDefaultChainState(MOCK_GENESIS);

  const expectedSections = [
    'chain',
    'session',
    'settings',
    'runtime',
    'stats',
    'block_counts',
    'skills',
    'relationships',
    'financial',
    'mood',
    'owner_info',
    'qube_profile',
    'health',
    'attestation',
  ];

  for (const section of expectedSections) {
    it(`has "${section}" section`, () => {
      expect(state).toHaveProperty(section);
    });
  }

  it('has all 15 expected sections (14 sections + version/qube_id/last_updated)', () => {
    // 14 domain sections + version + qube_id + last_updated = 17 top-level keys
    for (const section of expectedSections) {
      expect(state).toHaveProperty(section);
    }
    expect(state).toHaveProperty('version');
    expect(state).toHaveProperty('qube_id');
    expect(state).toHaveProperty('last_updated');
  });
});

// ---------------------------------------------------------------------------
// Chain section starts with length=1
// ---------------------------------------------------------------------------

describe('chain section initial values', () => {
  it('has length=1 (genesis block)', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const chain = state.chain as Record<string, unknown>;
    expect(chain.length).toBe(1);
  });

  it('has latest_block_number=0', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const chain = state.chain as Record<string, unknown>;
    expect(chain.latest_block_number).toBe(0);
  });

  it('has latest_block_hash matching genesis block_hash', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const chain = state.chain as Record<string, unknown>;
    expect(chain.latest_block_hash).toBe('f'.repeat(64));
    expect(chain.genesis_hash).toBe('f'.repeat(64));
  });

  it('has total_blocks=1, permanent_blocks=1, session_blocks=0', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const chain = state.chain as Record<string, unknown>;
    expect(chain.total_blocks).toBe(1);
    expect(chain.permanent_blocks).toBe(1);
    expect(chain.session_blocks).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Additional checks
// ---------------------------------------------------------------------------

describe('chain state qube_id', () => {
  it('uses qube_id from genesis block', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    expect(state.qube_id).toBe('ABCD1234');
  });

  it('uses explicit qubeId parameter if provided', () => {
    const state = createDefaultChainState(MOCK_GENESIS, 'CUSTOM_ID');
    expect(state.qube_id).toBe('CUSTOM_ID');
  });
});

describe('chain state settings', () => {
  it('locks model to genesis ai_model', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const settings = state.settings as Record<string, unknown>;
    expect(settings.model_locked).toBe(true);
    expect(settings.model_locked_to).toBe('claude-sonnet-4-20250514');
  });

  it('stores voice_model from genesis', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const settings = state.settings as Record<string, unknown>;
    expect(settings.voice_model).toBe('openai:alloy');
  });
});

describe('chain state block_counts', () => {
  it('starts with GENESIS=1 and all others at 0', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const counts = state.block_counts as Record<string, number>;
    expect(counts.GENESIS).toBe(1);
    expect(counts.MESSAGE).toBe(0);
    expect(counts.ACTION).toBe(0);
    expect(counts.SUMMARY).toBe(0);
    expect(counts.GAME).toBe(0);
  });
});

describe('chain state financial', () => {
  it('has empty wallet with balance 0', () => {
    const state = createDefaultChainState(MOCK_GENESIS);
    const financial = state.financial as Record<string, unknown>;
    const wallet = financial.wallet as Record<string, unknown>;
    expect(wallet.address).toBeNull();
    expect(wallet.balance_satoshis).toBe(0);
    expect(wallet.balance_bch).toBe(0.0);
  });
});
