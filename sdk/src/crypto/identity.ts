/**
 * Qube identity derivation: commitment and Qube ID from public key.
 *
 * Ported from `crypto/keys.py` (lines 202-271).
 *
 * CRITICAL design choice: the commitment is the SHA-256 hash of the public
 * key's **hex string** (the ASCII characters "02abc..."), NOT the raw public
 * key bytes. This is intentional and matches the Python implementation.
 *
 * @module crypto/identity
 */

import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex } from '@noble/hashes/utils';

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Derive the full 64-character commitment from a compressed public key hex.
 *
 * The commitment is `SHA-256(publicKeyHex)` where `publicKeyHex` is the
 * 66-character lowercase hex string of the compressed public key. The hash
 * input is the UTF-8 encoding of the hex string itself, NOT the raw bytes.
 *
 * Python equivalent: `derive_commitment` in `crypto/keys.py`.
 *
 * @param publicKeyHex - 66-character compressed public key hex string.
 * @returns 64-character lowercase hex commitment.
 *
 * @example
 * ```ts
 * const commitment = deriveCommitment("02abc...");
 * // "a3f2c1b8..."  (64 characters)
 * ```
 */
export function deriveCommitment(publicKeyHex: string): string {
  const encoder = new TextEncoder();
  const hash = sha256(encoder.encode(publicKeyHex));
  return bytesToHex(hash);
}

/**
 * Derive an 8-character Qube ID from a compressed public key hex.
 *
 * The Qube ID is the first 4 bytes (8 hex characters) of the commitment,
 * uppercased for readability.
 *
 * Python equivalent: `derive_qube_id` in `crypto/keys.py`.
 *
 * @param publicKeyHex - 66-character compressed public key hex string.
 * @returns 8-character uppercase hex Qube ID (e.g. "A3F2C1B8").
 *
 * @example
 * ```ts
 * const qubeId = deriveQubeId("02abc...");
 * // "A3F2C1B8"
 * ```
 */
export function deriveQubeId(publicKeyHex: string): string {
  return deriveCommitment(publicKeyHex).slice(0, 8).toUpperCase();
}
