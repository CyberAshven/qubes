/**
 * Memory block factories — all 10 block types (excluding GENESIS).
 *
 * Each factory creates a QubeBlock with the appropriate content structure.
 * Session blocks (temporary=true) use `previous_block_number`; permanent
 * blocks (temporary=false) use `previous_hash` and have their `block_hash`
 * computed automatically.
 *
 * All keys in the produced dicts are snake_case to match the on-wire
 * Qubes protocol format.
 *
 * Ported from `core/block.py`.
 *
 * @module blocks/memory
 */

import { QubeBlock } from './block.js';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Common parameters shared by most block factories. */
export interface CommonBlockParams {
  /** Owning Qube's identifier. */
  qubeId: string;
  /** Block number in the chain. */
  blockNumber: number;
  /** Hash of previous permanent block (permanent blocks only). */
  previousHash?: string | null;
  /** Previous block number (session blocks only). */
  previousBlockNumber?: number | null;
  /** Whether this is a session (temporary) block. Default false. */
  temporary?: boolean;
  /** Session identifier (set when temporary is true). */
  sessionId?: string | null;
}

/**
 * Build the base block data dict from common params.
 * Handles session vs. permanent linkage.
 */
function buildBase(
  blockType: string,
  params: CommonBlockParams,
  encrypted: boolean,
  content: Record<string, unknown>,
): Record<string, unknown> {
  const temporary = params.temporary ?? false;
  const data: Record<string, unknown> = {
    block_type: blockType,
    qube_id: params.qubeId,
    block_number: params.blockNumber,
    content,
    encrypted,
    temporary,
  };

  if (temporary) {
    if (params.previousBlockNumber != null) {
      data.previous_block_number = params.previousBlockNumber;
    }
    if (params.sessionId != null) {
      data.session_id = params.sessionId;
    }
  } else {
    if (params.previousHash != null) {
      data.previous_hash = params.previousHash;
    }
  }

  return data;
}

/**
 * Finalize a block: compute hash for permanent blocks.
 */
function finalize(data: Record<string, unknown>): QubeBlock {
  const block = new QubeBlock(data);
  if (!block.temporary) {
    block.blockHash = block.computeHash();
  }
  return block;
}

// ===========================================================================
// 1. THOUGHT BLOCK
// ===========================================================================

/** Parameters for creating a THOUGHT block. */
export interface CreateThoughtBlockParams extends CommonBlockParams {
  /** Internal monologue text. */
  internalMonologue?: string;
  /** Step-by-step reasoning chain. */
  reasoningChain?: string[];
  /** Confidence score (0.0 - 1.0). Default 0.9. */
  confidence?: number;
}

/**
 * Create a THOUGHT block for internal reasoning / monologue.
 *
 * Always encrypted. Can be session or permanent.
 *
 * Python equivalent: `core.block.create_thought_block`.
 */
export function createThoughtBlock(params: CreateThoughtBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    internal_monologue: params.internalMonologue ?? '',
    reasoning_chain: params.reasoningChain ?? [],
    confidence: params.confidence ?? 0.9,
  };
  return finalize(buildBase('THOUGHT', params, true, content));
}

// ===========================================================================
// 2. ACTION BLOCK
// ===========================================================================

/** Parameters for creating an ACTION block. */
export interface CreateActionBlockParams extends CommonBlockParams {
  /** Tool or action identifier (e.g. "web_search", "send_bch"). */
  actionType?: string;
  /** Parameters passed to the action. */
  parameters?: Record<string, unknown>;
  /** Who initiated the action: "self", "user", or a qube_id. Default "self". */
  initiatedBy?: string;
  /** Estimated cost in USD. Default 0.0. */
  costEstimate?: number;
  /** Action result (replaces the deprecated OBSERVATION block). */
  result?: Record<string, unknown> | null;
  /** Execution status: "pending", "completed", "failed". Default "pending". */
  status?: string;
  /** AI model used for generation. */
  modelUsed?: string | null;
  /** Turn number within a multi-turn conversation. */
  turnNumber?: number | null;
}

/**
 * Create an ACTION block for tool calls or external actions.
 *
 * Always encrypted. Can be session or permanent.
 *
 * Python equivalent: `core.block.create_action_block`.
 */
export function createActionBlock(params: CreateActionBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    action_type: params.actionType ?? '',
    parameters: params.parameters ?? {},
    initiated_by: params.initiatedBy ?? 'self',
    cost_estimate: params.costEstimate ?? 0.0,
    status: params.status ?? 'pending',
    result: params.result ?? null,
    turn_number: params.turnNumber ?? null,
  };

  const data = buildBase('ACTION', params, true, content);

  if (params.modelUsed != null) {
    data.model_used = params.modelUsed;
  }

  return finalize(data);
}

// ===========================================================================
// 3. OBSERVATION BLOCK (DEPRECATED)
// ===========================================================================

/** Parameters for creating an OBSERVATION block. */
export interface CreateObservationBlockParams extends CommonBlockParams {
  /** Source of the observation. */
  observationSource?: string;
  /** Raw observation data. */
  observationData?: unknown;
  /** Block number of the related ACTION block. Default 0. */
  relatedActionBlock?: number;
  /** Reliability score (0.0 - 1.0). Default 0.9. */
  reliabilityScore?: number;
}

/**
 * Create an OBSERVATION block.
 *
 * @deprecated OBSERVATION blocks are no longer used. Tool results are now
 * included directly in ACTION blocks via the `result` field.
 * Kept for backward compatibility.
 *
 * Always encrypted. Can be session or permanent.
 *
 * Python equivalent: `core.block.create_observation_block`.
 */
export function createObservationBlock(params: CreateObservationBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    observation_source: params.observationSource ?? '',
    observation_data: params.observationData ?? null,
    related_action_block: params.relatedActionBlock ?? 0,
    reliability_score: params.reliabilityScore ?? 0.9,
  };
  return finalize(buildBase('OBSERVATION', params, true, content));
}

// ===========================================================================
// 4. MESSAGE BLOCK
// ===========================================================================

/** Parameters for creating a MESSAGE block. */
export interface CreateMessageBlockParams extends CommonBlockParams {
  /** Direction: "qube_to_human", "human_to_qube", "qube_to_qube", "qube_to_group", "human_to_group". */
  messageType?: string;
  /** Recipient Qube ID or user ID. */
  recipientId?: string;
  /** Message text body. */
  messageBody?: string;
  /** Optional encrypted copy for recipient. */
  messageEncryptedForRecipient?: string | null;
  /** Conversation thread identifier. */
  conversationId?: string;
  /** Whether a response is expected. Default false. */
  requiresResponse?: boolean;
  /** Sender Qube ID (for multi-Qube conversations). */
  senderId?: string | null;
  /** List of participant Qube IDs (group conversations). */
  participants?: string[] | null;
  /** Turn number within conversation. */
  turnNumber?: number | null;
  /** Speaker Qube/user ID. */
  speakerId?: string | null;
  /** Speaker display name. */
  speakerName?: string | null;
  /** Multi-sig attestation: qube_id -> signature. */
  participantSignatures?: Record<string, string> | null;
  // ── Token usage tracking (stored outside encrypted content) ─────────
  /** Input tokens consumed by the AI model. */
  inputTokens?: number | null;
  /** Output tokens generated by the AI model. */
  outputTokens?: number | null;
  /** Total tokens (input + output). */
  totalTokens?: number | null;
  /** AI model identifier used for generation. */
  modelUsed?: string | null;
  /** Estimated API cost in USD. */
  estimatedCostUsd?: number | null;
}

/**
 * Create a MESSAGE block for conversation messages.
 *
 * Supports individual and group conversations. Token usage fields are stored
 * at the block level (outside encrypted content).
 *
 * Always encrypted. Can be session or permanent.
 *
 * Python equivalent: `core.block.create_message_block`.
 */
export function createMessageBlock(params: CreateMessageBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    message_type: params.messageType ?? 'qube_to_human',
    recipient_id: params.recipientId ?? '',
    message_body: params.messageBody ?? '',
    message_encrypted_for_recipient: params.messageEncryptedForRecipient ?? null,
    conversation_id: params.conversationId ?? '',
    requires_response: params.requiresResponse ?? false,
  };

  // Add optional multi-Qube fields (match Python: only if truthy/not-null)
  if (params.senderId) {
    content.sender_id = params.senderId;
  }
  if (params.participants) {
    content.participants = params.participants;
  }
  if (params.turnNumber != null) {
    content.turn_number = params.turnNumber;
  }
  if (params.speakerId) {
    content.speaker_id = params.speakerId;
  }
  if (params.speakerName) {
    content.speaker_name = params.speakerName;
  }
  if (params.participantSignatures) {
    content.participant_signatures = params.participantSignatures;
  }

  const data = buildBase('MESSAGE', params, true, content);

  // Token usage tracking at block level
  if (params.inputTokens != null) {
    data.input_tokens = params.inputTokens;
  }
  if (params.outputTokens != null) {
    data.output_tokens = params.outputTokens;
  }
  if (params.totalTokens != null) {
    data.total_tokens = params.totalTokens;
  }
  if (params.modelUsed != null) {
    data.model_used = params.modelUsed;
  }
  if (params.estimatedCostUsd != null) {
    data.estimated_cost_usd = params.estimatedCostUsd;
  }

  return finalize(data);
}

// ===========================================================================
// 5. DECISION BLOCK
// ===========================================================================

/** Parameters for creating a DECISION block. */
export interface CreateDecisionBlockParams extends CommonBlockParams {
  /** Description of the decision made. */
  decision?: string;
  /** Previous value / state. */
  fromValue?: unknown;
  /** New value / state. */
  toValue?: unknown;
  /** Reasoning behind the decision. */
  reasoning?: string;
  /** Assessment of expected impact. */
  impactAssessment?: string;
}

/**
 * Create a DECISION block for autonomous decisions.
 *
 * Always encrypted. Can be session or permanent.
 *
 * Python equivalent: `core.block.create_decision_block`.
 */
export function createDecisionBlock(params: CreateDecisionBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    decision: params.decision ?? '',
    from_value: params.fromValue ?? null,
    to_value: params.toValue ?? null,
    reasoning: params.reasoning ?? '',
    impact_assessment: params.impactAssessment ?? '',
  };
  return finalize(buildBase('DECISION', params, true, content));
}

// ===========================================================================
// 6. MEMORY_ANCHOR BLOCK
// ===========================================================================

/** Parameters for creating a MEMORY_ANCHOR block. */
export interface CreateMemoryAnchorBlockParams {
  /** Owning Qube's identifier. */
  qubeId: string;
  /** Block number in the chain. */
  blockNumber: number;
  /** Hash of previous permanent block. */
  previousHash: string;
  /** Merkle root of the anchored block range. */
  merkleRoot: string;
  /** [startBlock, endBlock] range covered by this anchor. */
  blockRange: [number, number];
  /** Total number of blocks in the range. */
  totalBlocks: number;
  /** Anchor trigger: "periodic", "manual", or "significant_event". Default "periodic". */
  anchorType?: string;
  /** Optional zero-knowledge proof. */
  zkProof?: string | null;
}

/**
 * Create a MEMORY_ANCHOR block for integrity verification.
 *
 * Memory anchors are always unencrypted (public for verification) and always
 * permanent. The merkle root is stored both at the top level and in content.
 *
 * Python equivalent: `core.block.create_memory_anchor_block`.
 */
export function createMemoryAnchorBlock(params: CreateMemoryAnchorBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    merkle_root: params.merkleRoot,
    block_range: params.blockRange,
    total_blocks: params.totalBlocks,
    anchor_type: params.anchorType ?? 'periodic',
    zk_proof: params.zkProof ?? null,
  };

  const data: Record<string, unknown> = {
    block_type: 'MEMORY_ANCHOR',
    qube_id: params.qubeId,
    block_number: params.blockNumber,
    content,
    encrypted: false,
    temporary: false,
    previous_hash: params.previousHash,
    merkle_root: params.merkleRoot,
  };

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}

// ===========================================================================
// 7. COLLABORATIVE_MEMORY BLOCK
// ===========================================================================

/** Parameters for creating a COLLABORATIVE_MEMORY block. */
export interface CreateCollaborativeMemoryBlockParams extends CommonBlockParams {
  /** Description of the shared event. */
  eventDescription: string;
  /** List of participant Qube IDs. */
  participants: string[];
  /** Hash of the shared data / outcome. */
  sharedDataHash: string;
  /** Contribution weight per participant (qube_id -> weight 0.0-1.0). */
  contributionWeights: Record<string, number>;
  /** Dict of qube_id -> signature for multi-sig validation. */
  signatures: Record<string, string>;
}

/**
 * Create a COLLABORATIVE_MEMORY block for multi-party shared memory.
 *
 * Requires multi-sig from all participants. Always encrypted.
 *
 * Python equivalent: `core.block.create_collaborative_memory_block`.
 */
export function createCollaborativeMemoryBlock(
  params: CreateCollaborativeMemoryBlockParams,
): QubeBlock {
  const content: Record<string, unknown> = {
    event_description: params.eventDescription,
    participants: params.participants,
    shared_data_hash: params.sharedDataHash,
    contribution_weights: params.contributionWeights,
  };

  const data = buildBase('COLLABORATIVE_MEMORY', params, true, content);

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}

// ===========================================================================
// 8. SUMMARY BLOCK
// ===========================================================================

/** Parameters for creating a SUMMARY block. */
export interface CreateSummaryBlockParams {
  /** Owning Qube's identifier. */
  qubeId: string;
  /** Block number in the chain. */
  blockNumber: number;
  /** Hash of previous permanent block. */
  previousHash: string;
  /** Block numbers that were summarized. */
  summarizedBlocks: number[];
  /** Number of blocks summarized. */
  blockCount: number;
  /** Time period covered (start/end timestamps or other metadata). */
  timePeriod: Record<string, unknown>;
  /** Generated summary text. */
  summaryText: string;
  /** Summary trigger: "periodic", "session", or "manual". Default "periodic". */
  summaryType?: string;
  /** Key events extracted from the summarized blocks. */
  keyEvents?: Array<Record<string, unknown>> | null;
  /** Sentiment analysis results. */
  sentimentAnalysis?: Record<string, unknown> | null;
  /** Topics discussed during the period. */
  topicsCovered?: string[] | null;
  /** Relationships that were affected. */
  relationshipsAffected?: Record<string, Record<string, string>> | null;
  /** References to archived data. */
  archivalReferences?: Record<string, string> | null;
  /** Session ID if this is a session summary. */
  sessionId?: string | null;
  /** Participants grouped by role. */
  participants?: Record<string, string[]> | null;
  /** Actions taken during the period. */
  actionsTaken?: Array<Record<string, unknown>> | null;
  /** Key insights extracted. */
  keyInsights?: string[] | null;
  /** Context to carry into the next session. */
  nextSessionContext?: string | null;
  /** Model used to generate the summary. */
  modelUsed?: string | null;
}

/**
 * Create a SUMMARY block for session or periodic summaries.
 *
 * Summaries are always permanent and encrypted.
 *
 * Python equivalent: `core.block.create_summary_block`.
 */
export function createSummaryBlock(params: CreateSummaryBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    summarized_blocks: params.summarizedBlocks,
    block_count: params.blockCount,
    time_period: params.timePeriod,
    summary_type: params.summaryType ?? 'periodic',
    summary_text: params.summaryText,
  };

  // Optional fields (match Python: only add if truthy)
  if (params.keyEvents) {
    content.key_events = params.keyEvents;
  }
  if (params.sentimentAnalysis) {
    content.sentiment_analysis = params.sentimentAnalysis;
  }
  if (params.topicsCovered) {
    content.topics_covered = params.topicsCovered;
  }
  if (params.relationshipsAffected) {
    content.relationships_affected = params.relationshipsAffected;
  }
  if (params.archivalReferences) {
    content.archival_references = params.archivalReferences;
  }
  if (params.sessionId) {
    content.session_id = params.sessionId;
  }
  if (params.participants) {
    content.participants = params.participants;
  }
  if (params.actionsTaken) {
    content.actions_taken = params.actionsTaken;
  }
  if (params.keyInsights) {
    content.key_insights = params.keyInsights;
  }
  if (params.nextSessionContext) {
    content.next_session_context = params.nextSessionContext;
  }
  if (params.modelUsed) {
    content.model_used = params.modelUsed;
  }

  const data: Record<string, unknown> = {
    block_type: 'SUMMARY',
    qube_id: params.qubeId,
    block_number: params.blockNumber,
    content,
    encrypted: true,
    temporary: false,
    previous_hash: params.previousHash,
  };

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}

// ===========================================================================
// 9. GAME BLOCK
// ===========================================================================

/** Parameters for creating a GAME block. */
export interface CreateGameBlockParams {
  /** Owning Qube's identifier. */
  qubeId: string;
  /** Block number in the chain. */
  blockNumber: number;
  /** Hash of previous permanent block. */
  previousHash: string;
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
  keyMoments?: Array<Record<string, unknown>> | null;
  /** In-game chat messages. */
  chatLog?: Array<Record<string, unknown>> | null;
}

/**
 * Create a GAME block for completed game records.
 *
 * GAME blocks are always permanent and unencrypted (public for verification
 * and signature checks by third parties).
 *
 * Python equivalent: `core.block.create_game_block`.
 */
export function createGameBlock(params: CreateGameBlockParams): QubeBlock {
  const content: Record<string, unknown> = {
    game_id: params.gameId,
    game_type: params.gameType,
    white_player: params.whitePlayer,
    black_player: params.blackPlayer,
    result: params.result,
    termination: params.termination,
    total_moves: params.totalMoves,
    pgn: params.pgn,
    duration_seconds: params.durationSeconds,
    xp_earned: params.xpEarned,
  };

  // Optional fields
  if (params.keyMoments) {
    content.key_moments = params.keyMoments;
  }
  if (params.chatLog) {
    content.chat_log = params.chatLog;
  }

  const data: Record<string, unknown> = {
    block_type: 'GAME',
    qube_id: params.qubeId,
    block_number: params.blockNumber,
    content,
    encrypted: false,
    temporary: false,
    previous_hash: params.previousHash,
  };

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}

// ===========================================================================
// 10. LEARNING BLOCK
// ===========================================================================

/** Valid learning types for LEARNING blocks. */
export const VALID_LEARNING_TYPES = [
  'fact',
  'procedure',
  'synthesis',
  'insight',
  'pattern',
  'relationship',
  'threat',
  'trust',
] as const;

/** Parameters for creating a LEARNING block. */
export interface CreateLearningBlockParams {
  /** Owning Qube's identifier. */
  qubeId: string;
  /** Block number in the chain. */
  blockNumber: number;
  /** Hash of previous permanent block. */
  previousHash: string;
  /** Learning type (one of VALID_LEARNING_TYPES). */
  learningType: string;
  /** Type-specific content fields (spread into content alongside base fields). */
  contentData: Record<string, unknown>;
  /** Block number that triggered this learning. */
  sourceBlock?: number | null;
  /** Type of the source block (e.g. "MESSAGE", "ACTION"). */
  sourceBlockType?: string | null;
  /** Which Sun or context created this learning (e.g. "social_intelligence"). */
  sourceCategory?: string | null;
  /** Confidence level 0-100. Default 80. */
  confidence?: number;
}

/**
 * Create a LEARNING block for persisting knowledge.
 *
 * LEARNING blocks are always permanent and encrypted. They capture facts,
 * procedures, insights, patterns, and relationships learned through
 * interactions across multiple Suns.
 *
 * Python equivalent: `core.block.create_learning_block`.
 *
 * @throws {Error} If learningType is not one of the valid types.
 */
export function createLearningBlock(params: CreateLearningBlockParams): QubeBlock {
  if (!VALID_LEARNING_TYPES.includes(params.learningType as typeof VALID_LEARNING_TYPES[number])) {
    throw new Error(
      `Invalid learning_type: ${params.learningType}. Must be one of ${VALID_LEARNING_TYPES.join(', ')}`,
    );
  }

  const content: Record<string, unknown> = {
    learning_type: params.learningType,
    confidence: params.confidence ?? 80,
    ...params.contentData,
  };

  // Optional source tracking
  if (params.sourceBlock != null) {
    content.source_block = params.sourceBlock;
  }
  if (params.sourceBlockType != null) {
    content.source_block_type = params.sourceBlockType;
  }
  if (params.sourceCategory != null) {
    content.source_category = params.sourceCategory;
  }

  const data: Record<string, unknown> = {
    block_type: 'LEARNING',
    qube_id: params.qubeId,
    block_number: params.blockNumber,
    content,
    encrypted: true,
    temporary: false,
    previous_hash: params.previousHash,
  };

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}
