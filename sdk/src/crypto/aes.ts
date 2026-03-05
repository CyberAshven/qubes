/**
 * AES-256-GCM encryption/decryption for Qubes memory blocks and raw data.
 *
 * Ported from `crypto/encryption.py` (lines 1-71, 122-166).
 *
 * Uses the Web Crypto API (`globalThis.crypto.subtle`) which is available in
 * all modern browsers and Node.js 18+.
 *
 * @module crypto/aes
 */

import { canonicalStringify } from '../utils/canonical-stringify.js';
import type { EncryptedData } from '../types/crypto.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const NONCE_BYTES = 12; // 96-bit nonce for AES-GCM

/** Convert Uint8Array to lowercase hex string. */
function toHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

/** Convert hex string to Uint8Array. */
function fromHex(hex: string): Uint8Array {
  const len = hex.length >>> 1;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

const encoder = new TextEncoder();
const decoder = new TextDecoder();

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
async function importKey(key: Uint8Array): Promise<CryptoKey> {
  return globalThis.crypto.subtle.importKey(
    'raw',
    toAB(key),
    { name: 'AES-GCM' },
    false,
    ['encrypt', 'decrypt'],
  );
}

// ---------------------------------------------------------------------------
// Block data encryption (JSON <-> hex)
// ---------------------------------------------------------------------------

/**
 * Encrypt a block data dictionary using AES-256-GCM.
 *
 * The data is serialized with `canonicalStringify` (recursive key-sorted JSON,
 * compatible with Python's `json.dumps(sort_keys=True)`), then encrypted.
 *
 * Python equivalent: `encrypt_block_data` in `crypto/encryption.py`.
 *
 * @param data  - Block data dictionary.
 * @param key   - 32-byte AES encryption key.
 * @returns Object with hex-encoded ciphertext, nonce, and algorithm tag.
 */
export async function encryptBlockData(
  data: Record<string, unknown>,
  key: Uint8Array,
): Promise<EncryptedData> {
  const nonce = globalThis.crypto.getRandomValues(new Uint8Array(NONCE_BYTES));
  const plaintext = encoder.encode(canonicalStringify(data));
  const cryptoKey = await importKey(key);

  const ciphertextBuf = await globalThis.crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(plaintext),
  );

  return {
    ciphertext: toHex(new Uint8Array(ciphertextBuf)),
    nonce: toHex(nonce),
    algorithm: 'AES-256-GCM',
  };
}

/**
 * Decrypt AES-256-GCM encrypted block data back to a dictionary.
 *
 * Python equivalent: `decrypt_block_data` in `crypto/encryption.py`.
 *
 * @param encrypted - Object with hex-encoded ciphertext and nonce.
 * @param key       - 32-byte AES decryption key.
 * @returns Decrypted data dictionary.
 */
export async function decryptBlockData(
  encrypted: EncryptedData,
  key: Uint8Array,
): Promise<Record<string, unknown>> {
  const nonce = fromHex(encrypted.nonce);
  const ciphertext = fromHex(encrypted.ciphertext);
  const cryptoKey = await importKey(key);

  const plaintextBuf = await globalThis.crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(ciphertext),
  );

  return JSON.parse(decoder.decode(plaintextBuf)) as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Raw byte encryption (nonce || ciphertext)
// ---------------------------------------------------------------------------

/**
 * Encrypt raw bytes using AES-256-GCM.
 *
 * Returns `nonce (12 bytes) || ciphertext+tag`.
 *
 * Python equivalent: `encrypt_data` in `crypto/encryption.py`.
 *
 * @param plaintext - Raw bytes to encrypt.
 * @param key       - 32-byte AES encryption key.
 * @returns Concatenated nonce + ciphertext (includes GCM auth tag).
 */
export async function encryptBytes(
  plaintext: Uint8Array,
  key: Uint8Array,
): Promise<Uint8Array> {
  const nonce = globalThis.crypto.getRandomValues(new Uint8Array(NONCE_BYTES));
  const cryptoKey = await importKey(key);

  const ciphertextBuf = await globalThis.crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(plaintext),
  );

  // Prepend nonce to ciphertext
  const ciphertext = new Uint8Array(ciphertextBuf);
  const result = new Uint8Array(NONCE_BYTES + ciphertext.length);
  result.set(nonce, 0);
  result.set(ciphertext, NONCE_BYTES);
  return result;
}

/**
 * Decrypt raw bytes (nonce || ciphertext) using AES-256-GCM.
 *
 * Python equivalent: `decrypt_data` in `crypto/encryption.py`.
 *
 * @param data - Concatenated nonce (12 bytes) + ciphertext+tag.
 * @param key  - 32-byte AES decryption key.
 * @returns Decrypted plaintext bytes.
 */
export async function decryptBytes(
  data: Uint8Array,
  key: Uint8Array,
): Promise<Uint8Array> {
  const nonce = data.slice(0, NONCE_BYTES);
  const ciphertext = data.slice(NONCE_BYTES);
  const cryptoKey = await importKey(key);

  const plaintextBuf = await globalThis.crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: toAB(nonce) },
    cryptoKey,
    toAB(ciphertext),
  );

  return new Uint8Array(plaintextBuf);
}
