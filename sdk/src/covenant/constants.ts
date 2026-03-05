/**
 * Covenant constants for the Qubes CashToken NFT minting system.
 *
 * These are pure values with no runtime dependencies — safe to import
 * in both browser and Node.js environments.
 *
 * @module covenant/constants
 */

// ---------------------------------------------------------------------------
// Token identity
// ---------------------------------------------------------------------------

/** Official Qubes CashToken NFT category ID (genesis txid of minting token). */
export const OFFICIAL_CATEGORY =
  'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

/** Official covenant P2SH32 address holding the minting token. */
export const OFFICIAL_COVENANT_ADDRESS =
  'bitcoincash:rvksvp7vuk4ck0asr3ns9v52h8d9zsywm6psx89hm7zsuqzldu4v5n4h9kyj7';

// ---------------------------------------------------------------------------
// Transaction limits
// ---------------------------------------------------------------------------

/** Minimum funding required from user to mint (1000 NFT dust + ~1000 fee). */
export const MIN_MINT_FUNDING = 2000n;

/** Standard BCH dust threshold in satoshis. */
export const DUST_LIMIT = 546n;

/** Dust amount for token-bearing outputs (required by consensus). */
export const TOKEN_DUST = 1000n;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Check if a category ID matches the official Qubes category.
 *
 * @param categoryId - Hex string to test.
 * @returns `true` when the category matches (case-insensitive).
 */
export function isOfficialQube(categoryId: string): boolean {
  return categoryId?.toLowerCase() === OFFICIAL_CATEGORY;
}
