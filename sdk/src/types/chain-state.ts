/**
 * Chain State V2 types for the Qubes protocol.
 *
 * The chain state is the consolidated, encrypted-at-rest state for each Qube.
 * It is organized into namespaced sections and supports bidirectional merge
 * between backend and GUI writes.
 *
 * Ported from `core/chain_state.py` (lines 33-245) and
 * `qubes-gui/src/types/index.ts` (lines 330-582).
 *
 * @module types/chain-state
 */

// ---------------------------------------------------------------------------
// Top-Level Chain State
// ---------------------------------------------------------------------------

/**
 * Complete chain state for a Qube (v2.0).
 *
 * Contains ALL 13 namespaced sections. Encrypted at rest with AES-256-GCM.
 *
 * Python equivalent: return value of `create_default_chain_state()`.
 * GUI equivalent: `ChainStateV2` in `qubes-gui/src/types/index.ts`.
 */
export interface ChainStateV2 {
  /** Schema version. */
  version: '2.0';
  /** Owning Qube's identifier. Python: `qube_id`. */
  qubeId: string;
  /** Last update timestamp (Unix epoch seconds). Python: `last_updated`. */
  lastUpdated: number;

  /** Blockchain / chain tracking. */
  chain: ChainSection;
  /** Current conversation session (ephemeral). */
  session: SessionSection;
  /** Qube-specific settings (GUI-managed). */
  settings: SettingsSection;
  /** Active runtime state (ephemeral). */
  runtime: RuntimeSection;
  /** Usage statistics and metrics. */
  stats: StatsSection;
  /** Block counts by type. Python: `block_counts`. */
  blockCounts: BlockCountsSection;
  /** Unlocked skills and XP. */
  skills: SkillsSection;
  /** Known entities and trust scores. */
  relationships: RelationshipsSection;
  /** Wallet and transaction data. */
  financial: FinancialSection;
  /** Current mood and mood history. */
  mood: MoodSection;
  /** Owner-provided information (learned during conversation). Python: `owner_info`. */
  ownerInfo: OwnerInfoSection;
  /** Self-identity profile (learned during conversation). Python: `qube_profile`. */
  qubeProfile: QubeProfileSection;
  /** System health and integrity. */
  health: HealthSection;
  /** Blockchain attestation tracking. */
  attestation: AttestationSection;
}

// ---------------------------------------------------------------------------
// Section Interfaces
// ---------------------------------------------------------------------------

/**
 * Chain section -- blockchain tracking metadata.
 *
 * Python: `chain_state["chain"]`.
 */
export interface ChainSection {
  /** Total chain length (including genesis). */
  length: number;
  /** Highest block number. Python: `latest_block_number`. */
  latestBlockNumber: number;
  /** Hash of the most recent permanent block. Python: `latest_block_hash`. */
  latestBlockHash: string | null;
  /** Hash of the genesis block. Python: `genesis_hash`. */
  genesisHash: string;
  /** Genesis block timestamp. Python: `genesis_timestamp`. */
  genesisTimestamp: number;
  /** Total number of blocks (permanent + session). Python: `total_blocks`. */
  totalBlocks: number;
  /** Number of permanent (hash-linked) blocks. Python: `permanent_blocks`. */
  permanentBlocks: number;
  /** Number of session (temporary) blocks. Python: `session_blocks`. */
  sessionBlocks: number;
  /** Block number of last memory anchor. Python: `last_anchor_block`. */
  lastAnchorBlock: number | null;
  /** Merkle root from last anchor. Python: `last_merkle_root`. */
  lastMerkleRoot: string | null;
}

/**
 * Session section -- current conversation state (ephemeral).
 *
 * Python: `chain_state["session"]`.
 */
export interface SessionSection {
  /** Active session identifier. Python: `session_id`. */
  sessionId: string | null;
  /** Session start timestamp. Python: `started_at`. */
  startedAt: number | null;
  /** Messages exchanged in this session. Python: `messages_this_session`. */
  messagesThisSession: number;
  /** Approximate context window usage (tokens). Python: `context_window_used`. */
  contextWindowUsed: number;
  /** Timestamp of last message. Python: `last_message_at`. */
  lastMessageAt: number | null;
  /** Next negative index for session blocks. Python: `next_negative_index`. */
  nextNegativeIndex: number;
}

/**
 * Settings section -- GUI-managed Qube preferences.
 *
 * Python: `chain_state["settings"]`.
 * These fields are preserved from disk during backend saves.
 */
export interface SettingsSection {
  // ── Model mode (mutually exclusive) ────────────────────────────────

  /** Whether the model is locked to a specific model. Python: `model_locked`. */
  modelLocked: boolean;
  /** Model identifier when locked. Python: `model_locked_to`. */
  modelLockedTo: string | null;
  /** Whether Revolver mode (random model per turn) is active. Python: `revolver_mode_enabled`. */
  revolverModeEnabled: boolean;
  /** Pool of models for Revolver mode. Python: `revolver_mode_pool`. */
  revolverModePool: string[];
  /** Whether Autonomous mode is active. Python: `autonomous_mode_enabled`. */
  autonomousModeEnabled: boolean;
  /** Pool of models for Autonomous mode. Python: `autonomous_mode_pool`. */
  autonomousModePool: string[];

  // ── Auto-anchor settings ───────────────────────────────────────────

  /** Whether auto-anchor is enabled for individual conversations. Python: `individual_auto_anchor_enabled`. */
  individualAutoAnchorEnabled: boolean;
  /** Message count threshold for individual auto-anchor. Python: `individual_auto_anchor_threshold`. */
  individualAutoAnchorThreshold: number;
  /** Whether auto-anchor is enabled for group conversations. Python: `group_auto_anchor_enabled`. */
  groupAutoAnchorEnabled: boolean;
  /** Message count threshold for group auto-anchor. Python: `group_auto_anchor_threshold`. */
  groupAutoAnchorThreshold: number;
  /** Whether to auto-sync to IPFS after auto-anchor. Python: `auto_sync_ipfs_on_anchor`. */
  autoSyncIpfsOnAnchor: boolean;

  // ── TTS settings ───────────────────────────────────────────────────

  /** Whether text-to-speech is enabled. Python: `tts_enabled`. */
  ttsEnabled: boolean;
  /** Voice model identifier. Python: `voice_model`. */
  voiceModel: string | null;
  /** Reference to voice library entry. Python: `voice_library_ref`. */
  voiceLibraryRef: string | null;

  // ── Visualizer settings ────────────────────────────────────────────

  /** Whether the audio visualizer is enabled. Python: `visualizer_enabled`. */
  visualizerEnabled: boolean;
  /** Visualizer configuration. Python: `visualizer_settings`. */
  visualizerSettings: Record<string, unknown> | null;
}

/**
 * Runtime section -- active ephemeral state.
 *
 * Python: `chain_state["runtime"]`.
 */
export interface RuntimeSection {
  /** Whether the Qube is currently online. Python: `is_online`. */
  isOnline: boolean;
  /** Currently active AI model. Python: `current_model`. */
  currentModel: string | null;
  /** Currently active AI provider. Python: `current_provider`. */
  currentProvider: string | null;
  /** Timestamp of last API call. Python: `last_api_call`. */
  lastApiCall: number | null;
  /** Tool calls currently in progress. Python: `pending_tool_calls`. */
  pendingToolCalls: string[];
  /** Active conversation identifier. Python: `active_conversation_id`. */
  activeConversationId: string | null;
}

/**
 * Stats section -- cumulative usage metrics.
 *
 * Python: `chain_state["stats"]`.
 */
export interface StatsSection {
  /** Total messages sent by this Qube. Python: `total_messages_sent`. */
  totalMessagesSent: number;
  /** Total messages received by this Qube. Python: `total_messages_received`. */
  totalMessagesReceived: number;
  /** Total tokens consumed across all models. Python: `total_tokens_used`. */
  totalTokensUsed: number;
  /** Total estimated API cost in USD. Python: `total_api_cost`. */
  totalApiCost: number;
  /** Token usage broken down by model. Python: `tokens_by_model`. */
  tokensByModel: Record<string, number>;
  /** API calls broken down by tool. Python: `api_calls_by_tool`. */
  apiCallsByTool: Record<string, number>;
  /** Total tool calls made. Python: `total_tool_calls`. */
  totalToolCalls: number;
  /** Model switch counts by mode type. Python: `model_switches`. */
  modelSwitches: {
    revolver: number;
    autonomous: number;
    manual: number;
  };
  /** Total memory anchors created. Python: `total_anchors`. */
  totalAnchors: number;
  /** Qube creation timestamp. Python: `created_at`. */
  createdAt: number;
  /** Timestamp of first user interaction. Python: `first_interaction`. */
  firstInteraction: number | null;
  /** Timestamp of most recent interaction. Python: `last_interaction`. */
  lastInteraction: number | null;
}

/**
 * Block counts section -- count of blocks by type.
 *
 * Python: `chain_state["block_counts"]`.
 */
export interface BlockCountsSection {
  /** Number of GENESIS blocks (always 1). */
  GENESIS: number;
  /** Number of MESSAGE blocks. */
  MESSAGE: number;
  /** Number of ACTION blocks. */
  ACTION: number;
  /** Number of SUMMARY blocks. */
  SUMMARY: number;
  /** Number of GAME blocks. */
  GAME: number;
  /** Additional block types may appear as the protocol evolves. */
  [blockType: string]: number;
}

/**
 * Skills section -- skill XP, unlocks, and history.
 *
 * Python: `chain_state["skills"]`.
 */
export interface SkillsSection {
  /** XP per skill. Keys are skill IDs, values contain XP and level. Python: `skill_xp`. */
  skillXp: Record<string, SkillXpEntry>;
  /** Skills unlocked beyond the defaults. Python: `extra_unlocked`. */
  extraUnlocked: string[];
  /** Total cumulative XP across all skills. Python: `total_xp`. */
  totalXp: number;
  /** Timestamp of last XP gain. Python: `last_xp_gain`. */
  lastXpGain: number | null;
  /** XP gain history entries. */
  history: SkillHistoryEntry[];
}

/** XP and level for a single skill. */
export interface SkillXpEntry {
  /** Current XP amount. */
  xp: number;
  /** Current skill level. */
  level: number;
}

/** A single skill XP gain event. */
export interface SkillHistoryEntry {
  /** When the XP was earned. */
  timestamp: number;
  /** Skill identifier. Python: `skill_id`. */
  skillId: string;
  /** Amount of XP gained. Python: `xp_gained`. */
  xpGained: number;
  /** Reason for the XP gain. */
  reason: string;
  /** Related block identifier. Python: `block_id`. */
  blockId?: string;
}

/**
 * Relationships section -- known entities and trust metrics.
 *
 * Python: `chain_state["relationships"]`.
 */
export interface RelationshipsSection {
  /** Map of entity_id -> relationship data. */
  entities: Record<string, RelationshipEntity>;
  /** Count of known entities. Python: `total_entities_known`. */
  totalEntitiesKnown: number;
  /** Entity ID of the best friend. Python: `best_friend`. */
  bestFriend: string | null;
  /** Entity ID of the owner. */
  owner: string | null;
  /** Clearance settings for information sharing. Python: `clearance_settings`. */
  clearanceSettings: Record<string, unknown> | null;
}

/**
 * A single relationship entity with trust metrics.
 *
 * Python: `chain_state["relationships"]["entities"][entity_id]`.
 * GUI: `RelationshipEntity` in `qubes-gui/src/types/index.ts`.
 */
export interface RelationshipEntity {
  /** Entity identifier. Python: `entity_id`. */
  entityId: string;
  /** Entity type. Python: `entity_type`. */
  entityType: 'human' | 'qube' | 'system';
  /** Relationship identifier. Python: `relationship_id`. */
  relationshipId: string;
  /** Entity's public key (hex). Python: `public_key`. */
  publicKey: string | null;

  // ── Positive metrics (0-100) ───────────────────────────────────────

  reliability: number;
  honesty: number;
  responsiveness: number;
  expertise: number;
  trust: number;
  friendship: number;
  affection: number;
  respect: number;
  loyalty: number;
  support: number;
  engagement: number;
  depth: number;
  humor: number;
  understanding: number;
  compatibility: number;
  admiration: number;
  warmth: number;
  openness: number;
  patience: number;
  empowerment: number;

  // ── Negative metrics (0-100) ───────────────────────────────────────

  antagonism: number;
  resentment: number;
  annoyance: number;
  distrust: number;
  rivalry: number;
  tension: number;
  condescension: number;
  manipulation: number;
  dismissiveness: number;
  betrayal: number;

  // ── Interaction stats ──────────────────────────────────────────────

  /** Messages sent to this entity. Python: `messages_sent`. */
  messagesSent: number;
  /** Messages received from this entity. Python: `messages_received`. */
  messagesReceived: number;
  /** Average response time in seconds. Python: `response_time_avg`. */
  responseTimeAvg: number;
  /** Last interaction timestamp. Python: `last_interaction`. */
  lastInteraction: number;
  /** Total collaborative tasks. */
  collaborations: number;
  /** Successful joint tasks. Python: `collaborations_successful`. */
  collaborationsSuccessful: number;
  /** Failed joint tasks. Python: `collaborations_failed`. */
  collaborationsFailed: number;

  // ── Status ─────────────────────────────────────────────────────────

  /** First contact timestamp. Python: `first_contact`. */
  firstContact: number;
  /** Days since first contact. Python: `days_known`. */
  daysKnown: number;
  /** Whether a face-to-face interaction has occurred. Python: `has_met`. */
  hasMet: boolean;
  /** Relationship status tier. */
  status: 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'best_friend';
  /** Whether this entity is the best friend. Python: `is_best_friend`. */
  isBestFriend: boolean;

  // ── Clearance ──────────────────────────────────────────────────────

  /** Information clearance profile. Python: `clearance_profile`. */
  clearanceProfile: string;
  /** Allowed information categories. Python: `clearance_categories`. */
  clearanceCategories: string[];
  /** Allowed information fields. Python: `clearance_fields`. */
  clearanceFields: string[];
}

/**
 * Financial section -- wallet balance, transactions, and pending.
 *
 * Python: `chain_state["financial"]`.
 */
export interface FinancialSection {
  /** Wallet information. */
  wallet: WalletInfo;
  /** Transaction history. */
  transactions: TransactionsInfo;
  /** Pending outgoing transactions. */
  pending: PendingTransactionEntry[];
}

/** Wallet balance and sync information. */
export interface WalletInfo {
  /** P2SH wallet address (bitcoincash:p...). */
  address: string | null;
  /** Balance in satoshis. Python: `balance_satoshis`. */
  balanceSatoshis: number;
  /** Balance in BCH. Python: `balance_bch`. */
  balanceBch: number;
  /** Last balance sync timestamp. Python: `last_sync`. */
  lastSync: number | null;
  /** Number of unspent transaction outputs. Python: `utxo_count`. */
  utxoCount: number;
}

/** Transaction history summary. */
export interface TransactionsInfo {
  /** Recent transaction entries. */
  history: TransactionEntry[];
  /** Total number of transactions. Python: `total_count`. */
  totalCount: number;
  /** Number of archived transactions. Python: `archived_count`. */
  archivedCount: number;
}

/** A single transaction entry. */
export interface TransactionEntry {
  /** Transaction identifier. */
  txid: string;
  /** Transaction type. Python: `tx_type`. */
  txType: 'deposit' | 'withdrawal' | 'qube_spend';
  /** Amount in satoshis. */
  amount: number;
  /** Transaction timestamp. */
  timestamp: number;
  /** Block height (null if unconfirmed). Python: `block_height`. */
  blockHeight: number | null;
  /** Number of confirmations. */
  confirmations: number;
  /** Transaction memo. */
  memo: string | null;
}

/** A pending outgoing transaction. */
export interface PendingTransactionEntry {
  /** Transaction identifier. */
  txid: string;
  /** When the transaction was created. Python: `created_at`. */
  createdAt: number;
  /** Amount in satoshis. */
  amount: number;
  /** Destination address. */
  destination: string;
  /** Transaction status. */
  status: 'pending' | 'broadcast' | 'confirmed' | 'failed';
}

/**
 * Mood section -- current emotional state and history.
 *
 * Python: `chain_state["mood"]`.
 */
export interface MoodSection {
  /** Current mood label. */
  current: string;
  /** Mood intensity (0.0 - 1.0). */
  intensity: number;
  /** Last mood update timestamp. Python: `last_updated`. */
  lastUpdated: number | null;
  /** Recent mood change history. */
  history: MoodHistoryEntry[];
}

/** A single mood change event. */
export interface MoodHistoryEntry {
  /** When the mood changed. */
  timestamp: number;
  /** Mood label. */
  mood: string;
  /** Energy level at the time. */
  energy: number;
  /** What triggered the mood change. */
  trigger: string | null;
}

/**
 * Owner info section -- information about the owner, learned during conversation.
 *
 * Python: `chain_state["owner_info"]`.
 * This is a freeform key-value store populated by the Qube as it learns about
 * its owner through interactions.
 */
export type OwnerInfoSection = Record<string, unknown>;

/**
 * Qube profile section -- self-identity learned during conversation.
 *
 * Python: `chain_state["qube_profile"]`.
 */
export interface QubeProfileSection {
  /** When the profile was first created. Python: `created_at`. */
  createdAt: string;
  /** When the profile was last updated. Python: `last_updated`. */
  lastUpdated: string;
  /** Personal preferences discovered through interaction. */
  preferences: Record<string, unknown>;
  /** Personality traits. */
  traits: Record<string, unknown>;
  /** Opinions on various topics. */
  opinions: Record<string, unknown>;
  /** Goals and aspirations. */
  goals: Record<string, unknown>;
  /** Communication style preferences. */
  style: Record<string, unknown>;
  /** Areas of interest. */
  interests: Record<string, unknown>;
  /** Dynamic entries (freeform). */
  dynamic: unknown[];
  /** User-defined custom profile sections. Python: `custom_sections`. */
  customSections: Record<string, unknown>;
}

/**
 * Health section -- system integrity and health status.
 *
 * Python: `chain_state["health"]`.
 */
export interface HealthSection {
  /** Overall health status. Python: `overall_status`. */
  overallStatus: 'healthy' | 'degraded' | 'critical';
  /** Last health check timestamp. Python: `last_health_check`. */
  lastHealthCheck: number | null;
  /** Whether chain integrity has been verified. Python: `integrity_verified`. */
  integrityVerified: boolean | null;
  /** Last integrity check timestamp. Python: `last_integrity_check`. */
  lastIntegrityCheck: number | null;
  /** List of active issues. */
  issues: string[];
}

/**
 * Attestation section -- blockchain attestation tracking (ephemeral).
 *
 * Python: `chain_state["attestation"]`.
 */
export interface AttestationSection {
  /** Timestamp of last attestation. Python: `last_attestation`. */
  lastAttestation: number | null;
  /** Hash that was attested. Python: `attestation_hash`. */
  attestationHash: string | null;
  /** Qube ID or key that signed the attestation. Python: `signed_by`. */
  signedBy: string | null;
  /** Whether the attestation has been verified on-chain. */
  verified: boolean;
}
