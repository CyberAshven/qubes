/**
 * ECDSA secp256k1 key pair generation and serialization.
 *
 * Ported from `crypto/keys.py` (lines 37-138).
 *
 * Uses `@noble/secp256k1` v2 for all elliptic curve operations.
 *
 * @module crypto/keys
 */

import {
  getPublicKey as nobleGetPublicKey,
  utils,
  etc,
} from '@noble/secp256k1';

import type { KeyPair } from '../types/crypto.js';

// ---------------------------------------------------------------------------
// Key generation
// ---------------------------------------------------------------------------

/**
 * Generate a new ECDSA secp256k1 key pair.
 *
 * Python equivalent: `generate_key_pair` in `crypto/keys.py`.
 *
 * @returns Object with 32-byte `privateKey` and 33-byte compressed `publicKey`.
 */
export function generateKeyPair(): KeyPair {
  const privateKey = utils.randomPrivateKey();
  const publicKey = nobleGetPublicKey(privateKey, true); // true = compressed
  return { privateKey, publicKey };
}

// ---------------------------------------------------------------------------
// Public key derivation
// ---------------------------------------------------------------------------

/**
 * Derive the compressed public key from a 32-byte private key.
 *
 * Python equivalent: `private_key.public_key()` followed by
 * `serialize_public_key(public_key)`.
 *
 * @param privateKey - Raw 32-byte private key.
 * @returns 33-byte compressed public key (02/03 prefix).
 */
export function getPublicKey(privateKey: Uint8Array): Uint8Array {
  return nobleGetPublicKey(privateKey, true);
}

// ---------------------------------------------------------------------------
// Serialization
// ---------------------------------------------------------------------------

/**
 * Serialize a compressed public key to a 66-character hex string.
 *
 * Python equivalent: `serialize_public_key` in `crypto/keys.py`.
 *
 * @param publicKey - 33-byte compressed public key.
 * @returns 66-character lowercase hex string (e.g. "02abc...").
 */
export function serializePublicKey(publicKey: Uint8Array): string {
  return etc.bytesToHex(publicKey);
}

/**
 * Parse a 66-character compressed public key hex string back to bytes.
 *
 * Python equivalent: `deserialize_public_key` in `crypto/keys.py` (returning
 * raw bytes instead of a library key object).
 *
 * @param hex - 66-character compressed hex string.
 * @returns 33-byte compressed public key.
 * @throws If the hex string is invalid.
 */
export function deserializePublicKey(hex: string): Uint8Array {
  if (hex.length !== 66) {
    throw new Error(
      `Expected 66-character compressed public key hex, got ${hex.length} characters`,
    );
  }
  return etc.hexToBytes(hex);
}

/**
 * Convert a 32-byte private key to a 64-character hex string.
 *
 * @param privateKey - Raw 32-byte private key.
 * @returns 64-character lowercase hex string.
 */
export function privateKeyToHex(privateKey: Uint8Array): string {
  return etc.bytesToHex(privateKey);
}

/**
 * Parse a 64-character hex string back to a 32-byte private key.
 *
 * @param hex - 64-character hex string.
 * @returns Raw 32-byte private key.
 * @throws If the hex string is invalid.
 */
export function privateKeyFromHex(hex: string): Uint8Array {
  if (hex.length !== 64) {
    throw new Error(
      `Expected 64-character private key hex, got ${hex.length} characters`,
    );
  }
  return etc.hexToBytes(hex);
}
