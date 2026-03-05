/**
 * HKDF-SHA256 key derivation for block-specific and chain-state encryption keys.
 *
 * Ported from `crypto/encryption.py` (lines 73-120).
 *
 * Uses `@noble/hashes/hkdf` and `@noble/hashes/sha256` for a pure-JS
 * implementation that works in both browsers and Node.js.
 *
 * @module crypto/hkdf
 */

import { hkdf } from '@noble/hashes/hkdf';
import { sha256 } from '@noble/hashes/sha256';

// ---------------------------------------------------------------------------
// Key derivation functions
// ---------------------------------------------------------------------------

/**
 * Derive a block-specific encryption key from the Qube's master key using
 * HKDF-SHA256.
 *
 * Each block gets a unique key so that compromising one block key does not
 * reveal data from other blocks.
 *
 * Python equivalent: `derive_block_key` in `crypto/encryption.py`.
 *
 * @param masterKey   - Qube's 32-byte master encryption key.
 * @param blockNumber - Block number (used as HKDF `info` context).
 * @returns 32-byte block-specific AES key.
 */
export function deriveBlockKey(
  masterKey: Uint8Array,
  blockNumber: number,
): Uint8Array {
  const info = new TextEncoder().encode(`block_${blockNumber}`);
  // hkdf(hash, ikm, salt, info, length)
  // Python uses salt=None which is equivalent to a zero-length salt.
  // @noble/hashes hkdf treats undefined salt as the default (all-zero of hash length).
  return hkdf(sha256, masterKey, undefined, info, 32);
}

/**
 * Derive a chain-state-specific encryption key from the Qube's master key
 * using HKDF-SHA256.
 *
 * Uses the fixed info string `"chain_state"` to produce a key that is
 * domain-separated from block encryption keys.
 *
 * Python equivalent: `derive_chain_state_key` in `crypto/encryption.py`.
 *
 * @param masterKey - Qube's 32-byte master encryption key.
 * @returns 32-byte chain-state AES key.
 */
export function deriveChainStateKey(masterKey: Uint8Array): Uint8Array {
  const info = new TextEncoder().encode('chain_state');
  return hkdf(sha256, masterKey, undefined, info, 32);
}
