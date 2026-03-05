/**
 * ECIES (Elliptic Curve Integrated Encryption Scheme) for Qubes.
 *
 * Ported from `crypto/ecies.py` (lines 39-184).
 *
 * Provides asymmetric encryption using secp256k1. Used to encrypt symmetric
 * keys so that only the NFT holder (who controls the private key) can decrypt.
 *
 * Process:
 * 1. Generate ephemeral secp256k1 key pair
 * 2. ECDH with recipient's public key -> shared secret (x-coordinate)
 * 3. HKDF-SHA256(sharedSecret, info="qubes-ecies-v1") -> 32-byte AES key
 * 4. AES-256-GCM encrypt with random 12-byte nonce
 * 5. Output: ephemeralPubKey(33) || nonce(12) || ciphertext+tag
 *
 * Uses `@noble/secp256k1` for ECDH, `@noble/hashes/hkdf` for key derivation,
 * and the Web Crypto API for AES-256-GCM.
 *
 * @module crypto/ecies
 */

import { getPublicKey, getSharedSecret, utils } from '@noble/secp256k1';
import { hkdf } from '@noble/hashes/hkdf';
import { sha256 } from '@noble/hashes/sha256';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Size of compressed ephemeral public key in bytes. */
const EPHEMERAL_PUBLIC_KEY_SIZE = 33;

/** Size of AES-GCM nonce in bytes. */
const NONCE_SIZE = 12;

/** Size of AES-GCM authentication tag in bytes. */
const TAG_SIZE = 16;

/** AES key size in bytes (256-bit). */
const AES_KEY_SIZE = 32;

/** HKDF info string for domain separation. */
const HKDF_INFO = new TextEncoder().encode('qubes-ecies-v1');

/** Minimum valid ciphertext size: pubkey + nonce + tag (no payload). */
const MIN_CIPHERTEXT_SIZE = EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE + TAG_SIZE;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Convert a Uint8Array to an ArrayBuffer slice suitable for Web Crypto API.
 * Needed because TypeScript 5.5+ Uint8Array<ArrayBufferLike> is not assignable
 * to BufferSource (which expects ArrayBufferView<ArrayBuffer>).
 */
function toAB(u8: Uint8Array): ArrayBuffer {
  // Slice creates a new ArrayBuffer (not SharedArrayBuffer), satisfying Web Crypto API types.
  return u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength) as ArrayBuffer;
}

/**
 * Import a raw 32-byte key into Web Crypto as an AES-GCM CryptoKey.
 */
async function importAesKey(key: Uint8Array): Promise<CryptoKey> {
  return globalThis.crypto.subtle.importKey(
    'raw',
    toAB(key),
    { name: 'AES-GCM' },
    false,
    ['encrypt', 'decrypt'],
  );
}

/**
 * Derive the ECDH shared secret (raw x-coordinate) between a private key
 * and a public key.
 *
 * Python equivalent: `private_key.exchange(ec.ECDH(), recipient_public_key)`
 * which returns the raw x-coordinate (32 bytes).
 */
function deriveSharedSecret(
  privateKey: Uint8Array,
  publicKey: Uint8Array,
): Uint8Array {
  // getSharedSecret returns a compressed point (33 bytes: prefix || x).
  // Slice off the prefix byte to get the 32-byte x-coordinate.
  const compressed = getSharedSecret(privateKey, publicKey, true);
  return compressed.slice(1); // 32 bytes (x-coordinate only)
}

/**
 * Derive a 32-byte AES key from a shared secret using HKDF-SHA256.
 */
function deriveAesKey(sharedSecret: Uint8Array): Uint8Array {
  // HKDF(hash, ikm, salt, info, length)
  // Python uses salt=None which maps to undefined (all-zero default).
  return hkdf(sha256, sharedSecret, undefined, HKDF_INFO, AES_KEY_SIZE);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Encrypt data using ECIES so only the holder of the recipient's private key
 * can decrypt.
 *
 * Output format: `ephemeralPubKey (33 bytes) || nonce (12 bytes) || ciphertext+tag`
 *
 * Python equivalent: `ecies_encrypt` in `crypto/ecies.py`.
 *
 * @param plaintext          - Data to encrypt.
 * @param recipientPublicKey - Recipient's 33-byte compressed secp256k1 public key.
 * @returns Encrypted payload.
 */
export async function eciesEncrypt(
  plaintext: Uint8Array,
  recipientPublicKey: Uint8Array,
): Promise<Uint8Array> {
  // 1. Generate ephemeral key pair
  const ephemeralPrivateKey = utils.randomPrivateKey();
  const ephemeralPublicKey = getPublicKey(ephemeralPrivateKey, true); // 33-byte compressed

  // 2. ECDH shared secret (x-coordinate)
  const sharedSecret = deriveSharedSecret(ephemeralPrivateKey, recipientPublicKey);

  // 3. Derive AES key via HKDF
  const aesKeyBytes = deriveAesKey(sharedSecret);

  // 4. AES-256-GCM encrypt
  const nonce = globalThis.crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
  const cryptoKey = await importAesKey(aesKeyBytes);
  const ciphertextBuf = await globalThis.crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(plaintext),
  );
  const ciphertext = new Uint8Array(ciphertextBuf);

  // 5. Combine: ephemeralPubKey || nonce || ciphertext (includes GCM tag)
  const result = new Uint8Array(
    EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE + ciphertext.length,
  );
  result.set(ephemeralPublicKey, 0);
  result.set(nonce, EPHEMERAL_PUBLIC_KEY_SIZE);
  result.set(ciphertext, EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE);

  return result;
}

/**
 * Decrypt ECIES-encrypted data.
 *
 * Expects the format produced by `eciesEncrypt`:
 * `ephemeralPubKey (33) || nonce (12) || ciphertext+tag`
 *
 * Python equivalent: `ecies_decrypt` in `crypto/ecies.py`.
 *
 * @param data       - Encrypted payload from `eciesEncrypt`.
 * @param privateKey - Recipient's 32-byte secp256k1 private key.
 * @returns Decrypted plaintext.
 * @throws If the data is too short, corrupted, or the wrong key is used.
 */
export async function eciesDecrypt(
  data: Uint8Array,
  privateKey: Uint8Array,
): Promise<Uint8Array> {
  // Validate minimum size
  if (data.length < MIN_CIPHERTEXT_SIZE) {
    throw new Error(
      `ECIES ciphertext too short: ${data.length} < ${MIN_CIPHERTEXT_SIZE}`,
    );
  }

  // 1. Extract components
  const ephemeralPublicKey = data.slice(0, EPHEMERAL_PUBLIC_KEY_SIZE);
  const nonce = data.slice(
    EPHEMERAL_PUBLIC_KEY_SIZE,
    EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE,
  );
  const ciphertext = data.slice(EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE);

  // 2. ECDH shared secret (x-coordinate)
  const sharedSecret = deriveSharedSecret(privateKey, ephemeralPublicKey);

  // 3. Derive AES key via HKDF
  const aesKeyBytes = deriveAesKey(sharedSecret);

  // 4. AES-256-GCM decrypt
  const cryptoKey = await importAesKey(aesKeyBytes);
  const plaintextBuf = await globalThis.crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(ciphertext),
  );

  return new Uint8Array(plaintextBuf);
}
