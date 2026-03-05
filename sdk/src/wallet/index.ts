/**
 * Wallet module — BCH script builder, CashAddr, P2SH multisig, transactions.
 *
 * Re-exports all wallet sub-modules for convenient access:
 *
 * ```ts
 * import { buildAsymmetricMultisigScript, createWalletAddress } from '@qubesai/sdk/wallet';
 * ```
 *
 * @module wallet
 */

export * from './script.js';
export * from './cashaddr.js';
export * from './address.js';
export * from './transaction.js';
export * from './walletconnect.js';
