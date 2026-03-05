/**
 * Package types for Qube export, import, and IPFS backup.
 *
 * A Qube package contains everything needed to fully restore a Qube:
 * genesis block, memory chain, chain state, relationships, skills, avatar,
 * and NFT metadata -- all encrypted with AES-256-GCM.
 *
 * Two package formats exist:
 * 1. **IPFS package**: Binary format with magic header (`QUBE` + version + nonce + ciphertext).
 *    Ported from `blockchain/chain_package.py`.
 * 2. **File export**: ZIP file with `manifest.json` (unencrypted) and `data.enc` (encrypted).
 *    Ported from `gui_bridge.py` export/import methods.
 *
 * @module types/package
 */

// ---------------------------------------------------------------------------
// IPFS Package Types (chain_package.py)
// ---------------------------------------------------------------------------

/**
 * Metadata about a packaged Qube (stored inside the encrypted payload).
 *
 * Python equivalent: `blockchain.chain_package.QubePackageMetadata`.
 */
export interface QubePackageMetadata {
  /** Qube identifier. Python: `qube_id`. */
  qubeId: string;
  /** Qube display name. Python: `qube_name`. */
  qubeName: string;
  /** Compressed public key (hex). Python: `public_key`. */
  publicKey: string;
  /** Number of blocks in the chain. Python: `chain_length`. */
  chainLength: number;
  /** Merkle root of all block hashes. Python: `merkle_root`. */
  merkleRoot: string;
  /** Package format version. Python: `package_version`. */
  packageVersion: string;
  /** Unix timestamp when the package was created. Python: `packaged_at`. */
  packagedAt: number;
  /** User ID of the person who created the package. Python: `packaged_by`. */
  packagedBy: string;
  /** Whether the Qube has a minted NFT. Python: `has_nft`. */
  hasNft: boolean;
  /** CashToken category ID if minted. Python: `nft_category_id`. */
  nftCategoryId?: string | null;
}

/**
 * Complete Qube data structure for packaging.
 *
 * This represents everything needed to fully restore a Qube from an
 * IPFS backup or file transfer.
 *
 * Python equivalent: `blockchain.chain_package.QubePackageData`.
 */
export interface QubePackageData {
  /** Package metadata. */
  metadata: QubePackageMetadata;
  /** Genesis block data (block 0). Python: `genesis_block`. */
  genesisBlock: Record<string, unknown>;
  /** All permanent memory blocks. Python: `memory_blocks`. */
  memoryBlocks: Array<Record<string, unknown>>;
  /** Full chain state snapshot. Python: `chain_state`. */
  chainState: Record<string, unknown>;
  /** Relationship data. */
  relationships?: Record<string, unknown> | null;
  /** Skill XP and unlock data. */
  skills?: Record<string, unknown> | null;
  /** Skill XP gain history. Python: `skill_history`. */
  skillHistory?: Array<Record<string, unknown>> | null;
  /** Base64-encoded avatar image data. Python: `avatar_data`. */
  avatarData?: string | null;
  /** Avatar filename (e.g. "avatar.png"). Python: `avatar_filename`. */
  avatarFilename?: string | null;
  /** NFT metadata (category_id, mint_txid, etc.). Python: `nft_metadata`. */
  nftMetadata?: Record<string, unknown> | null;
  /** BCMR metadata JSON. Python: `bcmr_data`. */
  bcmrData?: Record<string, unknown> | null;
  /** Hex-encoded identity private key (safe because the package is encrypted). Python: `private_key_hex`. */
  privateKeyHex?: string | null;
}

// ---------------------------------------------------------------------------
// File Export Types (gui_bridge.py)
// ---------------------------------------------------------------------------

/**
 * Manifest stored as `manifest.json` inside the `.qube` ZIP export file.
 *
 * This is the unencrypted header that allows identifying the Qube
 * without decrypting the payload.
 *
 * Python equivalent: manifest dict in `gui_bridge.py` export_qube_to_file().
 */
export interface QubeManifest {
  /** Export format version. */
  version: string;
  /** Qube identifier. Python: `qube_id`. */
  qubeId: string;
  /** Qube display name. Python: `qube_name`. */
  qubeName: string;
  /** ISO 8601 export timestamp. Python: `export_date`. */
  exportDate: string;
  /** Number of memory blocks included. Python: `block_count`. */
  blockCount: number;
  /** Whether the Qube has a minted NFT. Python: `has_nft`. */
  hasNft: boolean;
  /** Hex-encoded PBKDF2 salt (16 bytes). */
  salt: string;
  /** Hex-encoded AES-GCM nonce (12 bytes). */
  nonce: string;
}
