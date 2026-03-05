/**
 * Default chain state factory.
 *
 * Creates the v2.0 chain state dict from a genesis block. This is the single
 * source of truth for what a fresh chain state looks like, matching the Python
 * `core.chain_state.create_default_chain_state()`.
 *
 * All keys are snake_case to match the on-wire protocol format.
 *
 * @module blocks/chain-state
 */

// ---------------------------------------------------------------------------
// Provider detection
// ---------------------------------------------------------------------------

/**
 * Detect the AI provider from a model name string.
 *
 * Matches the Python logic in `create_default_chain_state`.
 */
function detectProvider(
  aiModel: string,
  fallbackProvider?: string,
): string {
  const lower = aiModel.toLowerCase();

  if (lower.includes('claude')) return 'anthropic';
  if (lower.includes('gpt')) return 'openai';
  if (lower.includes('gemini')) return 'google';
  if (lower.includes('sonar')) return 'perplexity';
  if (lower.includes('venice')) return 'venice';
  if (lower.includes('llama') || lower.includes('mistral') || lower.includes('qwen')) {
    return 'ollama';
  }

  return fallbackProvider ?? 'anthropic';
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a default chain state from genesis block data.
 *
 * This is the SINGLE SOURCE OF TRUTH for what a fresh chain state looks like.
 * Used when creating a new Qube or resetting to defaults.
 *
 * Python equivalent: `core.chain_state.create_default_chain_state`.
 *
 * @param genesisBlock - Genesis block data (snake_case dict).
 * @param qubeId       - Qube ID. Extracted from genesis if not provided.
 * @returns Complete chain_state dict with snake_case keys, ready to be saved.
 */
export function createDefaultChainState(
  genesisBlock: Record<string, unknown>,
  qubeId?: string,
): Record<string, unknown> {
  const now = Math.floor(Date.now() / 1000);
  const nowIso = new Date().toISOString().replace(/\.\d{3}Z$/, '.000000Z').replace(/Z$/, '') + 'Z';
  // Python uses datetime.now(timezone.utc).isoformat() + "Z"
  // which produces e.g. "2024-01-01T12:00:00.123456+00:00Z"
  // We approximate with ISO string + 'Z'
  const isoTimestamp = new Date().toISOString();

  const resolvedQubeId = qubeId ?? (genesisBlock.qube_id as string) ?? 'unknown';
  const aiModel = (genesisBlock.ai_model as string) ?? 'claude-sonnet-4-20250514';
  const voiceModel = (genesisBlock.voice_model as string) ?? 'openai:alloy';
  const genesisHash = (genesisBlock.block_hash as string) ?? '0'.repeat(64);
  const birthTimestamp =
    (genesisBlock.birth_timestamp as number) ??
    (genesisBlock.timestamp as number) ??
    now;

  // TTS enabled: check explicit field, then capabilities, then default based on voice_model
  let ttsEnabled = genesisBlock.tts_enabled as boolean | undefined;
  if (ttsEnabled === undefined || ttsEnabled === null) {
    const capabilities = (genesisBlock.capabilities as Record<string, boolean>) ?? {};
    ttsEnabled = capabilities.tts ?? Boolean(voiceModel);
  }

  const provider = detectProvider(
    aiModel,
    genesisBlock.ai_provider as string | undefined,
  );

  return {
    version: '2.0',
    qube_id: resolvedQubeId,
    last_updated: now,

    // Chain section — blockchain tracking
    chain: {
      length: 1,
      latest_block_number: 0,
      latest_block_hash: genesisHash,
      genesis_hash: genesisHash,
      genesis_timestamp: birthTimestamp,
      total_blocks: 1,
      permanent_blocks: 1,
      session_blocks: 0,
      last_anchor_block: null,
      last_merkle_root: null,
    },

    // Session section — current conversation (ephemeral)
    session: {
      session_id: null,
      started_at: null,
      messages_this_session: 0,
      context_window_used: 0,
      last_message_at: null,
      next_negative_index: -1,
    },

    // Settings section — qube-specific from genesis
    settings: {
      model_locked: true,
      model_locked_to: aiModel,
      revolver_mode_enabled: false,
      revolver_mode_pool: [],
      autonomous_mode_enabled: false,
      autonomous_mode_pool: [],
      individual_auto_anchor_enabled: true,
      individual_auto_anchor_threshold: 20,
      group_auto_anchor_enabled: true,
      group_auto_anchor_threshold: 20,
      auto_sync_ipfs_on_anchor: false,
      tts_enabled: ttsEnabled,
      voice_model: voiceModel,
      voice_library_ref: null,
      visualizer_enabled: false,
      visualizer_settings: null,
    },

    // Runtime section — active state (updated during conversation)
    runtime: {
      is_online: false,
      current_model: aiModel,
      current_provider: provider,
      last_api_call: null,
      pending_tool_calls: [],
      active_conversation_id: null,
    },

    // Stats section — usage metrics (all zeroed)
    stats: {
      total_messages_sent: 0,
      total_messages_received: 0,
      total_tokens_used: 0,
      total_api_cost: 0.0,
      tokens_by_model: {},
      api_calls_by_tool: {},
      total_tool_calls: 0,
      model_switches: {
        revolver: 0,
        autonomous: 0,
        manual: 0,
      },
      total_anchors: 0,
      created_at: now,
      first_interaction: null,
      last_interaction: null,
    },

    // Block counts — fresh start
    block_counts: {
      GENESIS: 1,
      MESSAGE: 0,
      ACTION: 0,
      SUMMARY: 0,
      GAME: 0,
    },

    // Skills section — compact format (only stores skills with XP)
    skills: {
      skill_xp: {},
      extra_unlocked: [],
      total_xp: 0,
      last_xp_gain: null,
      history: [],
    },

    // Relationships section — empty
    relationships: {
      entities: {},
      total_entities_known: 0,
      best_friend: null,
      owner: null,
      clearance_settings: null,
    },

    // Financial section — empty wallet
    financial: {
      wallet: {
        address: null,
        balance_satoshis: 0,
        balance_bch: 0.0,
        last_sync: null,
        utxo_count: 0,
      },
      transactions: {
        history: [],
        total_count: 0,
        archived_count: 0,
      },
      pending: [],
    },

    // Mood section — neutral
    mood: {
      current: 'neutral',
      intensity: 0.5,
      last_updated: null,
      history: [],
    },

    // Owner info section — empty (learned during conversation)
    owner_info: {},

    // Qube profile section — empty (self-identity learned during conversation)
    qube_profile: {
      created_at: isoTimestamp,
      last_updated: isoTimestamp,
      preferences: {},
      traits: {},
      opinions: {},
      goals: {},
      style: {},
      interests: {},
      dynamic: [],
      custom_sections: {},
    },

    // Health section — integrity and system status
    health: {
      overall_status: 'healthy',
      last_health_check: null,
      integrity_verified: null,
      last_integrity_check: null,
      issues: [],
    },

    // Attestation section — blockchain attestation tracking
    attestation: {
      last_attestation: null,
      attestation_hash: null,
      signed_by: null,
      verified: false,
    },
  };
}
