/**
 * Block types and interfaces for the Qubes memory chain.
 *
 * Ported from `core/block.py`. Each Qube maintains a cryptographically
 * linked chain of memory blocks. Blocks are either permanent (hash-linked)
 * or temporary session blocks (index-linked).
 *
 * @module types/block
 */

// ---------------------------------------------------------------------------
// Block Type Enum
// ---------------------------------------------------------------------------

/**
 * Memory block types as defined in the Qubes protocol.
 *
 * Python equivalent: `core.block.BlockType`
 */
export enum BlockType {
  /** Genesis block -- created once at Qube birth (block 0). */
  GENESIS = 'GENESIS',
  /** Internal reasoning / monologue. */
  THOUGHT = 'THOUGHT',
  /** Tool call or external action (includes result). */
  ACTION = 'ACTION',
  /**
   * External observation.
   * @deprecated Observations are now included directly in ACTION blocks.
   */
  OBSERVATION = 'OBSERVATION',
  /** Conversational message (human-to-qube, qube-to-human, qube-to-qube). */
  MESSAGE = 'MESSAGE',
  /** Autonomous decision with reasoning. */
  DECISION = 'DECISION',
  /** Periodic merkle anchor for integrity verification. */
  MEMORY_ANCHOR = 'MEMORY_ANCHOR',
  /** Multi-party shared memory (multi-sig). */
  COLLABORATIVE_MEMORY = 'COLLABORATIVE_MEMORY',
  /** Session or periodic summary. */
  SUMMARY = 'SUMMARY',
  /** Completed game record (e.g. chess). */
  GAME = 'GAME',
  /** Cross-cutting knowledge storage used by multiple Suns. */
  LEARNING = 'LEARNING',
}

// ---------------------------------------------------------------------------
// Content Type Interfaces
// ---------------------------------------------------------------------------

/**
 * Content schema for THOUGHT blocks.
 *
 * Python: `create_thought_block` content dict.
 */
export interface ThoughtContent {
  /** Internal monologue text. */
  internalMonologue: string;
  /** Step-by-step reasoning chain. */
  reasoningChain: string[];
  /** Confidence score (0.0 - 1.0). */
  confidence: number;
}

/**
 * Content schema for ACTION blocks.
 *
 * Python: `create_action_block` content dict.
 * Note: OBSERVATION blocks have been merged into ACTION via the `result` field.
 */
export interface ActionContent {
  /** Tool or action identifier (e.g. "web_search", "send_bch"). */
  actionType: string;
  /** Parameters passed to the action. */
  parameters: Record<string, unknown>;
  /** Who initiated the action: "self", "user", or a qube_id. */
  initiatedBy: string;
  /** Estimated cost in USD. */
  costEstimate: number;
  /** Execution status: "pending", "completed", "failed". */
  status: string;
  /** Action result (replaces the deprecated OBSERVATION block). */
  result: Record<string, unknown> | null;
  /** Turn number within a multi-turn conversation. */
  turnNumber?: number | null;
}

/**
 * Content schema for OBSERVATION blocks.
 *
 * @deprecated Use ActionContent.result instead. Kept for backward compatibility.
 *
 * Python: `create_observation_block` content dict.
 */
export interface ObservationContent {
  /** Source of the observation. */
  observationSource: string;
  /** Raw observation data. */
  observationData: unknown;
  /** Block number of the related ACTION block. */
  relatedActionBlock: number;
  /** Reliability score (0.0 - 1.0). */
  reliabilityScore: number;
}

/**
 * Content schema for MESSAGE blocks.
 *
 * Python: `create_message_block` content dict.
 */
export interface MessageContent {
  /** Direction: "qube_to_human", "human_to_qube", "qube_to_qube", "qube_to_group", "human_to_group". */
  messageType: string;
  /** Recipient Qube ID or user ID. */
  recipientId: string;
  /** Message text body. */
  messageBody: string;
  /** Optional encrypted copy for recipient. */
  messageEncryptedForRecipient?: string | null;
  /** Conversation thread identifier. */
  conversationId: string;
  /** Whether a response is expected. */
  requiresResponse: boolean;
  /** Sender Qube ID (for multi-Qube conversations). */
  senderId?: string;
  /** List of participant Qube IDs (group conversations). */
  participants?: string[];
  /** Turn number within conversation. */
  turnNumber?: number | null;
  /** Speaker Qube/user ID. */
  speakerId?: string;
  /** Speaker display name. */
  speakerName?: string;
  /** Multi-sig attestation: qube_id -> signature. */
  participantSignatures?: Record<string, string>;
}

/**
 * Content schema for DECISION blocks.
 *
 * Python: `create_decision_block` content dict.
 */
export interface DecisionContent {
  /** Description of the decision made. */
  decision: string;
  /** Previous value / state. */
  fromValue: unknown;
  /** New value / state. */
  toValue: unknown;
  /** Reasoning behind the decision. */
  reasoning: string;
  /** Assessment of expected impact. */
  impactAssessment: string;
}

/**
 * Content schema for MEMORY_ANCHOR blocks.
 *
 * Python: `create_memory_anchor_block` content dict.
 * Memory anchors are always unencrypted and permanent.
 */
export interface MemoryAnchorContent {
  /** Merkle root of the anchored block range. */
  merkleRoot: string;
  /** [startBlock, endBlock] range covered by this anchor. */
  blockRange: [number, number];
  /** Total number of blocks in the range. */
  totalBlocks: number;
  /** Anchor trigger: "periodic", "manual", or "significant_event". */
  anchorType: string;
  /** Optional zero-knowledge proof. */
  zkProof?: string | null;
}

/**
 * Content schema for COLLABORATIVE_MEMORY blocks.
 *
 * Python: `create_collaborative_memory_block` content dict.
 * Requires multi-sig from all participants.
 */
export interface CollaborativeMemoryContent {
  /** Description of the shared event. */
  eventDescription: string;
  /** List of participant Qube IDs. */
  participants: string[];
  /** Hash of the shared data / outcome. */
  sharedDataHash: string;
  /** Contribution weight per participant (qube_id -> weight 0.0-1.0). */
  contributionWeights: Record<string, number>;
}

/**
 * Content schema for SUMMARY blocks.
 *
 * Python: `create_summary_block` content dict.
 * Summaries are always permanent.
 */
export interface SummaryContent {
  /** Block numbers that were summarized. */
  summarizedBlocks: number[];
  /** Number of blocks summarized. */
  blockCount: number;
  /** Time period covered (start/end timestamps or other metadata). */
  timePeriod: Record<string, unknown>;
  /** Summary trigger: "periodic", "session", or "manual". */
  summaryType: string;
  /** Generated summary text. */
  summaryText: string;
  /** Key events extracted from the summarized blocks. */
  keyEvents?: Array<Record<string, unknown>>;
  /** Sentiment analysis results. */
  sentimentAnalysis?: Record<string, unknown>;
  /** Topics discussed during the period. */
  topicsCovered?: string[];
  /** Relationships that were affected. */
  relationshipsAffected?: Record<string, Record<string, string>>;
  /** References to archived data. */
  archivalReferences?: Record<string, string>;
  /** Session ID if this is a session summary. */
  sessionId?: string;
  /** Participants grouped by role. */
  participants?: Record<string, string[]>;
  /** Actions taken during the period. */
  actionsTaken?: Array<Record<string, unknown>>;
  /** Key insights extracted. */
  keyInsights?: string[];
  /** Context to carry into the next session. */
  nextSessionContext?: string;
  /** Model used to generate the summary. */
  modelUsed?: string;
}

/**
 * Content schema for GAME blocks.
 *
 * Python: `create_game_block` content dict.
 * GAME blocks are always permanent and unencrypted (public for verification).
 */
export interface GameContent {
  /** Unique game identifier. */
  gameId: string;
  /** Type of game (e.g. "chess"). */
  gameType: string;
  /** White player info: { id, type: "human" | "qube" }. */
  whitePlayer: Record<string, unknown>;
  /** Black player info: { id, type: "human" | "qube" }. */
  blackPlayer: Record<string, unknown>;
  /** Game result: "1-0", "0-1", "1/2-1/2", or "*". */
  result: string;
  /** How the game ended: "checkmate", "resignation", "stalemate", etc. */
  termination: string;
  /** Total number of moves played. */
  totalMoves: number;
  /** Complete game in PGN format. */
  pgn: string;
  /** Game duration in seconds. */
  durationSeconds: number;
  /** XP awarded for this game. */
  xpEarned: number;
  /** Significant moves with reasoning. */
  keyMoments?: Array<Record<string, unknown>>;
  /** In-game chat messages. */
  chatLog?: Array<Record<string, unknown>>;
}

/** Valid learning types for LEARNING blocks. */
export type LearningType =
  | 'fact'
  | 'procedure'
  | 'synthesis'
  | 'insight'
  | 'pattern'
  | 'relationship'
  | 'threat'
  | 'trust';

/**
 * Content schema for LEARNING blocks.
 *
 * Python: `create_learning_block` content dict.
 * LEARNING blocks are always permanent and encrypted.
 *
 * Type-specific fields are spread into the content object alongside
 * the base fields below. For example, a "fact" learning includes
 * `fact`, `subject`, and `source` fields.
 */
export interface LearningContent {
  /** Category of knowledge learned. */
  learningType: LearningType;
  /** Confidence level 0-100. */
  confidence: number;
  /** Block number that triggered this learning. */
  sourceBlock?: number;
  /** Type of the source block (e.g. "MESSAGE", "ACTION"). */
  sourceBlockType?: string;
  /** Which Sun or context created this learning (e.g. "social_intelligence"). */
  sourceCategory?: string;
  /** Additional type-specific fields (fact, subject, steps, etc.). */
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Participant Signature
// ---------------------------------------------------------------------------

/**
 * A single participant's signature on a collaborative block.
 *
 * Each participant signs the `contentHash` (not `blockHash`) so the
 * signature is valid across different chains.
 */
export interface ParticipantSignature {
  /** Qube ID of the signer. */
  qubeId: string;
  /** Hex-encoded compressed public key. */
  publicKey: string;
  /** Hex-encoded ECDSA signature over the content hash. */
  signature: string;
}

// ---------------------------------------------------------------------------
// Block Interface
// ---------------------------------------------------------------------------

/**
 * A memory block in the Qubes chain.
 *
 * This interface covers ALL block types including genesis-specific fields.
 * Optional fields are marked with `?` to match their Python `Optional[...]`
 * counterparts.
 *
 * Python equivalent: `core.block.Block` (Pydantic model).
 *
 * Field naming: TypeScript uses camelCase; the original Python snake_case
 * name is noted in JSDoc where they differ.
 */
export interface Block {
  // ── Core fields (all block types) ──────────────────────────────────

  /** Block type discriminator. Python: `block_type`. */
  blockType: BlockType;
  /** Sequential block number in the chain. Python: `block_number`. */
  blockNumber: number;
  /** Owning Qube's identifier. Python: `qube_id`. */
  qubeId: string;
  /** Unix epoch timestamp in seconds. */
  timestamp?: number | null;
  /** Block content (schema depends on blockType). */
  content?: Record<string, unknown> | null;
  /** Whether the content is AES-256-GCM encrypted. */
  encrypted: boolean;
  /** Whether this is a session (temporary) block. */
  temporary: boolean;
  /** Session identifier (set when temporary is true). Python: `session_id`. */
  sessionId?: string | null;
  /** Original session index before anchoring. Python: `original_session_index`. */
  originalSessionIndex?: number | null;

  // ── Chain linkage ──────────────────────────────────────────────────

  /** Previous block number (session blocks only, simple reference). Python: `previous_block_number`. */
  previousBlockNumber?: number | null;
  /** SHA-256 hash of the previous permanent block. Python: `previous_hash`. */
  previousHash?: string | null;
  /** SHA-256 hash of this block (permanent blocks only). Python: `block_hash`. */
  blockHash?: string | null;
  /** ECDSA signature over blockHash (single signer). */
  signature?: string | null;

  // ── Multi-party signatures (GAME, COLLABORATIVE_MEMORY, etc.) ─────

  /**
   * Participant signatures for collaborative blocks.
   * Each entry signs the `contentHash`, not the `blockHash`.
   * Python: `participant_signatures`.
   */
  participantSignatures?: ParticipantSignature[] | null;
  /** Hash of just the content (signed by all participants). Python: `content_hash`. */
  contentHash?: string | null;

  // ── Token usage tracking ───────────────────────────────────────────

  /** Input tokens consumed by the AI model. Python: `input_tokens`. */
  inputTokens?: number | null;
  /** Output tokens generated by the AI model. Python: `output_tokens`. */
  outputTokens?: number | null;
  /** Total tokens (input + output). Python: `total_tokens`. */
  totalTokens?: number | null;
  /** AI model identifier used for generation. Python: `model_used`. */
  modelUsed?: string | null;
  /** Estimated API cost in USD. Python: `estimated_cost_usd`. */
  estimatedCostUsd?: number | null;

  // ── Relationship tracking ──────────────────────────────────────────

  /** Relationship metric updates from asymmetric anchoring. Python: `relationship_updates`. */
  relationshipUpdates?: Record<string, Record<string, unknown>> | null;

  // ── GENESIS-specific fields ────────────────────────────────────────

  /** Qube display name (genesis only). Python: `qube_name`. */
  qubeName?: string | null;
  /** Creator user ID (genesis only). */
  creator?: string | null;
  /** Compressed public key hex (genesis only). Python: `public_key`. */
  publicKey?: string | null;
  /** Birth timestamp in seconds (genesis only). Python: `birth_timestamp`. */
  birthTimestamp?: number | null;
  /** System prompt / personality seed (genesis only). Python: `genesis_prompt`. */
  genesisPrompt?: string | null;
  /** Whether the genesis prompt is stored encrypted. Python: `genesis_prompt_encrypted`. */
  genesisPromptEncrypted?: boolean | null;
  /** AI provider identifier (genesis only). Python: `ai_provider`. */
  aiProvider?: string | null;
  /** AI model identifier (genesis only). Python: `ai_model`. */
  aiModel?: string | null;
  /** Voice model identifier (genesis only). Python: `voice_model`. */
  voiceModel?: string | null;
  /** Avatar configuration (genesis only). */
  avatar?: Record<string, unknown> | null;
  /** Qube's favorite color hex (genesis only). Python: `favorite_color`. */
  favoriteColor?: string | null;
  /** Home blockchain identifier (genesis only). Python: `home_blockchain`. */
  homeBlockchain?: string | null;
  /** P2SH co-signing wallet info (genesis only). */
  wallet?: Record<string, unknown> | null;
  /** NFT contract address (genesis only). Python: `nft_contract`. */
  nftContract?: string | null;
  /** NFT token ID (genesis only). Python: `nft_token_id`. */
  nftTokenId?: string | null;
  /** Capability flags (genesis only). */
  capabilities?: Record<string, boolean> | null;
  /** Default trust level for new relationships (genesis only). Python: `default_trust_level`. */
  defaultTrustLevel?: number | null;
  /** Merkle root (genesis / memory anchor). Python: `merkle_root`. */
  merkleRoot?: string | null;

  // ── NFT minting fields (populated after minting) ───────────────────

  /** CashToken NFT category ID. Python: `nft_category_id`. */
  nftCategoryId?: string | null;
  /** Minting transaction ID. Python: `mint_txid`. */
  mintTxid?: string | null;
  /** IPFS URI for BCMR metadata. Python: `bcmr_uri`. */
  bcmrUri?: string | null;
  /** NFT commitment hash. */
  commitment?: string | null;
}
