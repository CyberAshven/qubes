/**
 * NFT metadata types for the Qubes protocol.
 *
 * Each minted Qube has an NFT metadata file (`nft_metadata.json`) stored
 * in its chain directory. This metadata links the on-chain NFT to the
 * off-chain Qube data.
 *
 * Ported from `blockchain/manager.py` `_save_nft_metadata_to_qube()` and
 * `orchestrator/user_orchestrator.py` finalize_minting().
 *
 * @module types/nft
 */

/**
 * NFT metadata for a minted Qube.
 *
 * Stored at `{qube_dir}/chain/nft_metadata.json` after successful minting.
 *
 * Python equivalent: `nft_metadata` dict in `BlockchainManager._save_nft_metadata_to_qube()`.
 */
export interface NFTMetadata {
  /** Qube identifier. Python: `qube_id`. */
  qubeId: string;
  /** CashToken category ID (64-char hex, same as genesis outpoint txid). Python: `category_id`. */
  categoryId: string;
  /** Minting transaction ID. Python: `mint_txid`. */
  mintTxid: string;
  /** BCH address that received the NFT (token-aware cashaddr). Python: `recipient_address`. */
  recipientAddress: string;
  /** IPFS CID for the BCMR metadata JSON. Python: `bcmr_ipfs_cid`. */
  bcmrIpfsCid?: string;
  /** IPFS CID for the avatar image. Python: `avatar_ipfs_cid`. */
  avatarIpfsCid?: string;
  /** NFT commitment hash (64-char hex). */
  commitment: string;
  /** Network: "mainnet" or "testnet". */
  network: string;
  /** ISO 8601 timestamp of when the NFT was minted. Python: `minted_at`. */
  mintedAt?: string;
  /** Local path to BCMR file within the Qube directory. Python: `bcmr_location`. */
  bcmrLocation?: string;
}
