/**
 * Genesis block factory.
 *
 * Creates the genesis block (block 0) for a new Qube. The genesis block
 * stores identity fields at the top level (not in `content`), is never
 * encrypted, and is always permanent.
 *
 * Ported from `core/block.py::create_genesis_block`.
 *
 * @module blocks/genesis
 */

import { QubeBlock } from './block.js';

// ---------------------------------------------------------------------------
// Factory params
// ---------------------------------------------------------------------------

/** Parameters for creating a genesis block. */
export interface CreateGenesisBlockParams {
  /** Qube identifier (SHA256(pubkey)[:8].hex().upper()). */
  qubeId: string;
  /** Qube display name. */
  qubeName: string;
  /** Creator user ID. */
  creator: string;
  /** Compressed public key hex. */
  publicKey: string;
  /** System prompt / personality seed. */
  genesisPrompt: string;
  /** AI model identifier. */
  aiModel: string;
  /** Voice model identifier. */
  voiceModel: string;
  /** Avatar configuration. */
  avatar: Record<string, unknown>;
  /** Favorite color hex. Default "#4A90E2". */
  favoriteColor?: string;
  /** Home blockchain identifier. Default "bitcoin_cash". */
  homeBlockchain?: string;
  /** Whether the genesis prompt is stored encrypted. Default false. */
  genesisPromptEncrypted?: boolean;
  /** Default trust level for new relationships. Default 50. */
  defaultTrustLevel?: number;
  /** NFT contract address. */
  nftContract?: string | null;
  /** NFT token ID. */
  nftTokenId?: string | null;
}

// ---------------------------------------------------------------------------
// Factory function
// ---------------------------------------------------------------------------

/**
 * Create a genesis block (block 0) for a new Qube.
 *
 * The block hash is computed automatically. The genesis block uses top-level
 * fields for identity data; `content` is set to an empty object.
 *
 * Python equivalent: `core.block.create_genesis_block`.
 *
 * @param params - Genesis block parameters.
 * @returns A new QubeBlock with block_hash set.
 */
export function createGenesisBlock(params: CreateGenesisBlockParams): QubeBlock {
  const birthTimestamp = Math.floor(Date.now() / 1000);

  const data: Record<string, unknown> = {
    block_type: 'GENESIS',
    block_number: 0,
    qube_id: params.qubeId,
    timestamp: birthTimestamp,
    birth_timestamp: birthTimestamp,
    qube_name: params.qubeName,
    creator: params.creator,
    public_key: params.publicKey,
    genesis_prompt: params.genesisPrompt,
    genesis_prompt_encrypted: params.genesisPromptEncrypted ?? false,
    ai_model: params.aiModel,
    voice_model: params.voiceModel,
    avatar: params.avatar,
    favorite_color: params.favoriteColor ?? '#4A90E2',
    home_blockchain: params.homeBlockchain ?? 'bitcoin_cash',
    default_trust_level: params.defaultTrustLevel ?? 50,
    merkle_root: null,
    previous_hash: '0'.repeat(64),
    content: {},
    encrypted: false,
    temporary: false,
  };

  // Only include NFT fields if provided (match Python exclude_none)
  if (params.nftContract != null) {
    data.nft_contract = params.nftContract;
  }
  if (params.nftTokenId != null) {
    data.nft_token_id = params.nftTokenId;
  }

  const block = new QubeBlock(data);
  block.blockHash = block.computeHash();
  return block;
}
