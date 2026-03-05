/**
 * Qube package creation — Binary IPFS format and ZIP file export.
 *
 * Two package formats:
 *
 * **Format A — Binary IPFS Package** (ported from `blockchain/chain_package.py`):
 * ```
 * Offset  Size  Content
 * 0       4     Magic bytes "QUBE" (0x51 0x55 0x42 0x45)
 * 4       1     Version byte (0x01)
 * 5       12    AES-GCM nonce (random)
 * 17      N     AES-256-GCM ciphertext (JSON payload + 16-byte auth tag)
 * ```
 *
 * **Format B — ZIP File Export** (ported from `gui_bridge.py`):
 * ZIP containing `manifest.json` (unencrypted) + `data.enc` (AES-256-GCM
 * encrypted with PBKDF2-derived key).
 *
 * @module package/create
 */

import { zipSync } from 'fflate';
import { encryptBytes } from '../crypto/aes.js';
import { deriveMasterKey, DEFAULT_ITERATIONS } from '../crypto/pbkdf2.js';
import type { QubePackageData, QubeManifest } from '../types/package.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Magic bytes identifying a binary QUBE package: ASCII "QUBE". */
export const PACKAGE_MAGIC = new Uint8Array([0x51, 0x55, 0x42, 0x45]);

/** Binary package format version. */
export const PACKAGE_VERSION = 1;

/** AES-GCM nonce size in bytes. */
export const NONCE_SIZE = 12;

/** AES-256-GCM key size in bytes. */
export const KEY_SIZE = 32;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const encoder = new TextEncoder();

/** Convert bytes to lowercase hex string. */
function toHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

// ---------------------------------------------------------------------------
// Format A — Binary IPFS Package
// ---------------------------------------------------------------------------

/**
 * Create a binary IPFS package from Qube data.
 *
 * The package layout is:
 * ```
 * [4 magic][1 version][12 nonce][N ciphertext+tag]
 * ```
 *
 * The payload is the JSON serialization of `data` encrypted with AES-256-GCM
 * using a random 12-byte nonce and no AAD.
 *
 * Python equivalent: `create_package` in `blockchain/chain_package.py`.
 *
 * @param data - Complete Qube package data to encrypt.
 * @param key  - Optional 32-byte encryption key. If omitted, a random key is generated.
 * @returns Object containing the full encrypted binary and the 32-byte key used.
 */
export async function createBinaryPackage(
  data: QubePackageData,
  key?: Uint8Array,
): Promise<{ encrypted: Uint8Array; key: Uint8Array }> {
  // Generate or validate key
  const encKey = key ?? globalThis.crypto.getRandomValues(new Uint8Array(KEY_SIZE));

  // Serialize payload to UTF-8 JSON
  const plaintext = encoder.encode(JSON.stringify(data));

  // Encrypt: encryptBytes returns nonce(12) || ciphertext+tag
  const noncePlusCiphertext = await encryptBytes(plaintext, encKey);

  // noncePlusCiphertext layout: [12 nonce][N ciphertext+tag]
  // We need: [4 magic][1 version][12 nonce][N ciphertext+tag]
  const headerSize = PACKAGE_MAGIC.length + 1; // 5 bytes
  const result = new Uint8Array(headerSize + noncePlusCiphertext.length);

  result.set(PACKAGE_MAGIC, 0);
  result[4] = PACKAGE_VERSION;
  result.set(noncePlusCiphertext, headerSize); // nonce and ciphertext follow header

  return { encrypted: result, key: encKey };
}

// ---------------------------------------------------------------------------
// Format B — ZIP File Export
// ---------------------------------------------------------------------------

/**
 * Create a `.qube` ZIP export file from Qube data and a user password.
 *
 * The ZIP contains:
 * - `manifest.json` — unencrypted metadata (version, qubeId, salt, nonce, etc.)
 * - `data.enc` — raw AES-256-GCM ciphertext of the JSON payload
 *
 * Key derivation: PBKDF2-HMAC-SHA256, 600K iterations, 16-byte random salt.
 *
 * Python equivalent: `export_qube_to_file` in `gui_bridge.py`.
 *
 * @param data     - Complete Qube package data to encrypt.
 * @param password - User password for PBKDF2 key derivation.
 * @returns ZIP file as a Uint8Array.
 */
export async function createQubeFile(
  data: QubePackageData,
  password: string,
): Promise<Uint8Array> {
  // Generate random salt (16 bytes) and derive key via PBKDF2
  const salt = globalThis.crypto.getRandomValues(new Uint8Array(16));
  const derivedKey = deriveMasterKey(password, salt, DEFAULT_ITERATIONS);

  // Serialize payload to UTF-8 JSON
  const plaintext = encoder.encode(JSON.stringify(data));

  // Encrypt: encryptBytes returns nonce(12) || ciphertext+tag
  const noncePlusCiphertext = await encryptBytes(plaintext, derivedKey);

  // Split out nonce for the manifest
  const nonce = noncePlusCiphertext.slice(0, NONCE_SIZE);
  // Ciphertext is everything after the nonce (includes 16-byte GCM auth tag)
  const ciphertext = noncePlusCiphertext.slice(NONCE_SIZE);

  // Build manifest
  const manifest: QubeManifest = {
    version: '1.0',
    qubeId: data.metadata.qubeId,
    qubeName: data.metadata.qubeName,
    exportDate: new Date().toISOString(),
    blockCount: data.memoryBlocks.length,
    hasNft: data.metadata.hasNft,
    salt: toHex(salt),
    nonce: toHex(nonce),
  };

  const manifestBytes = encoder.encode(JSON.stringify(manifest, null, 2));

  // Build ZIP synchronously using fflate
  const zip = zipSync({
    'manifest.json': manifestBytes,
    'data.enc': ciphertext,
  });

  return zip;
}
