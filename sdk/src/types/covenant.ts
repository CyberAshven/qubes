/**
 * Covenant minting types for the Qubes protocol.
 *
 * The Qubes covenant is a CashScript contract that handles permissionless
 * NFT minting on Bitcoin Cash. There are two modes:
 *
 * 1. **Broadcast mode**: The SDK builds, signs, and broadcasts the mint
 *    transaction directly using a funded wallet WIF.
 *
 * 2. **WalletConnect mode**: The SDK builds an unsigned transaction object
 *    that is sent to the user's wallet (via WalletConnect v2) for signing.
 *
 * Ported from `covenant/mint-cli.ts` output schemas and
 * `blockchain/manager.py` return values.
 *
 * @module types/covenant
 */

// ---------------------------------------------------------------------------
// Broadcast Mode Result
// ---------------------------------------------------------------------------

/**
 * Result of a covenant mint transaction in broadcast mode.
 *
 * Returned when the SDK builds, signs, and broadcasts the transaction
 * using a wallet WIF key.
 *
 * Python equivalent: return value of `BlockchainManager.mint_qube_nft()`.
 * CLI equivalent: stdout JSON from `covenant/mint-cli.ts` (broadcast mode).
 */
export interface MintResult {
  /** Whether the mint was successful. */
  success: boolean;
  /** Transaction ID of the mint transaction. Python: `mint_txid`. */
  mintTxid: string;
  /** CashToken category ID (same as the genesis outpoint txid). Python: `category_id`. */
  categoryId: string;
  /** 64-character hex commitment hash. */
  commitment: string;
  /** Covenant contract address (bitcoincash:p...). Python: `covenant_address`. */
  covenantAddress: string;
  /** Recipient's token-aware address (bitcoincash:z...). Python: `recipient_address`. */
  recipientAddress: string;
}

// ---------------------------------------------------------------------------
// WalletConnect Mode Result
// ---------------------------------------------------------------------------

/**
 * Result of a covenant mint transaction in WalletConnect mode.
 *
 * Instead of broadcasting, the SDK returns an unsigned transaction object
 * for the user's wallet to sign and broadcast.
 *
 * Python equivalent: return value of `BlockchainManager.prepare_wc_mint_transaction()`.
 * CLI equivalent: stdout JSON from `covenant/mint-cli.ts` (walletconnect mode).
 */
export interface WcMintResult {
  /** Whether the transaction was built successfully. */
  success: boolean;
  /** Mode discriminator. */
  mode: 'walletconnect';
  /** Stringified WalletConnect transaction object for wallet signing. Python: `wc_transaction`. */
  wcTransaction: string;
  /** CashToken category ID. Python: `category_id`. */
  categoryId: string;
  /** 64-character hex commitment hash. */
  commitment: string;
  /** Covenant contract address (bitcoincash:p...). Python: `covenant_address`. */
  covenantAddress: string;
  /** Recipient's token-aware address (bitcoincash:z...). Python: `recipient_address`. */
  recipientAddress: string;
}

// ---------------------------------------------------------------------------
// Error Result
// ---------------------------------------------------------------------------

/**
 * Error result from a failed covenant operation.
 */
export interface MintError {
  /** Always false for errors. */
  success: false;
  /** Error description. */
  error: string;
}

/**
 * Union type for all possible mint results.
 */
export type MintOutcome = MintResult | WcMintResult | MintError;

// ---------------------------------------------------------------------------
// NFT Transfer — WalletConnect Mode
// ---------------------------------------------------------------------------

/**
 * Result of a WalletConnect NFT transfer transaction build.
 *
 * The transfer is a pure P2PKH → P2PKH send (no covenant involved).
 * The SDK builds an unsigned transaction; the wallet signs all inputs
 * via `bch_signTransaction`.
 *
 * Python equivalent: return value of `BlockchainManager.prepare_transfer_wc()`.
 * CLI equivalent: stdout JSON from `covenant/transfer-cli.ts`.
 */
export interface WcTransferResult {
  /** Whether the transaction was built successfully. */
  success: boolean;
  /** Stringified WalletConnect transaction object for wallet signing. Python: `wc_transaction`. */
  wcTransaction: string;
  /** CashToken category ID (64-char hex). Python: `category_id`. */
  categoryId: string;
  /** 64-character hex NFT commitment. */
  commitment: string;
}

/**
 * Error result from a failed transfer operation.
 */
export interface TransferError {
  /** Always false for errors. */
  success: false;
  /** Error description. */
  error: string;
}

/**
 * Union type for all possible transfer results.
 */
export type TransferOutcome = WcTransferResult | TransferError;
