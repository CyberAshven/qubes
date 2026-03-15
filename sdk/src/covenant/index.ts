/**
 * Covenant module — CashScript contract interaction for NFT minting and verification.
 *
 * Sub-modules:
 * - **constants** — Category IDs, dust limits, helpers (browser-safe)
 * - **contract** — Contract instantiation (Node.js only, requires `cashscript`)
 * - **mint**     — Build/broadcast mint transactions (Node.js only, requires `cashscript` + `@bitauth/libauth`)
 * - **transfer** — Build WalletConnect NFT transfer transactions (Node.js only, requires `cashscript` + `@bitauth/libauth`)
 * - **verify**   — NFT ownership verification via Chaingraph GraphQL (browser-safe)
 *
 * `cashscript` and `@bitauth/libauth` are **optional** peer dependencies.
 * They are loaded via dynamic `import()` and only required when actually
 * calling minting functions. The constants and verify sub-modules work
 * everywhere.
 *
 * @module covenant
 */

export * from './constants.js';
export * from './contract.js';
export * from './mint.js';
export * from './transfer.js';
export * from './verify.js';
