/**
 * Qube package parsing — Binary IPFS format and ZIP file import.
 *
 * Inverse of `package/create.ts`. Validates magic bytes / version, extracts
 * the nonce, decrypts the payload, and returns a typed `QubePackageData`.
 *
 * @module package/parse
 */

import { unzipSync } from 'fflate';
import { decryptBytes } from '../crypto/aes.js';
import { deriveMasterKey, DEFAULT_ITERATIONS } from '../crypto/pbkdf2.js';
import type { QubePackageData, QubeManifest } from '../types/package.js';
import { PACKAGE_MAGIC, PACKAGE_VERSION, NONCE_SIZE } from './create.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const decoder = new TextDecoder();

/** Convert lowercase hex string to Uint8Array. */
function fromHex(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) {
    throw new Error(`Invalid hex string length: ${hex.length}`);
  }
  const len = hex.length >>> 1;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

// ---------------------------------------------------------------------------
// Format A — Binary IPFS Package
// ---------------------------------------------------------------------------

/**
 * Parse and decrypt a binary IPFS package.
 *
 * Expected layout:
 * ```
 * [4 magic][1 version][12 nonce][N ciphertext+tag]
 * ```
 *
 * Python equivalent: `unpack_package` in `blockchain/chain_package.py`.
 *
 * @param encrypted - Raw binary package bytes.
 * @param key       - 32-byte AES-256-GCM decryption key.
 * @returns Decrypted and parsed `QubePackageData`.
 * @throws If the magic bytes are invalid, the version is unsupported, or
 *         decryption fails (wrong key / corrupted data).
 */
export async function parseBinaryPackage(
  encrypted: Uint8Array,
  key: Uint8Array,
): Promise<QubePackageData> {
  const HEADER_SIZE = PACKAGE_MAGIC.length + 1 + NONCE_SIZE; // 4 + 1 + 12 = 17

  if (encrypted.length < HEADER_SIZE) {
    throw new Error(
      `Binary package too short: ${encrypted.length} bytes (minimum ${HEADER_SIZE})`,
    );
  }

  // Validate magic bytes
  for (let i = 0; i < PACKAGE_MAGIC.length; i++) {
    if (encrypted[i] !== PACKAGE_MAGIC[i]) {
      throw new Error(
        `Invalid magic bytes: expected "QUBE", got 0x${encrypted[i].toString(16).padStart(2, '0')} at offset ${i}`,
      );
    }
  }

  // Validate version
  const version = encrypted[4];
  if (version !== PACKAGE_VERSION) {
    throw new Error(
      `Unsupported package version: ${version} (expected ${PACKAGE_VERSION})`,
    );
  }

  // Extract nonce (bytes 5–16) and ciphertext (bytes 17+)
  const nonce = encrypted.slice(5, 5 + NONCE_SIZE);
  const ciphertext = encrypted.slice(5 + NONCE_SIZE);

  // decryptBytes expects nonce(12) || ciphertext — reconstruct that layout
  const noncePlusCiphertext = new Uint8Array(nonce.length + ciphertext.length);
  noncePlusCiphertext.set(nonce, 0);
  noncePlusCiphertext.set(ciphertext, nonce.length);

  let plaintext: Uint8Array;
  try {
    plaintext = await decryptBytes(noncePlusCiphertext, key);
  } catch (err) {
    throw new Error(
      `Failed to decrypt binary package: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  let data: QubePackageData;
  try {
    data = JSON.parse(decoder.decode(plaintext)) as QubePackageData;
  } catch (err) {
    throw new Error(
      `Failed to parse decrypted package JSON: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  return data;
}

// ---------------------------------------------------------------------------
// Format B — ZIP File Export
// ---------------------------------------------------------------------------

/**
 * Parse and decrypt a `.qube` ZIP export file.
 *
 * The ZIP must contain:
 * - `manifest.json` — unencrypted metadata with `salt` and `nonce` fields
 * - `data.enc` — raw AES-256-GCM ciphertext (no nonce prepended)
 *
 * Key derivation: PBKDF2-HMAC-SHA256, 600K iterations using the salt from the manifest.
 *
 * Python equivalent: `import_qube_from_file` in `gui_bridge.py`.
 *
 * @param zipData  - Raw ZIP file bytes.
 * @param password - User password for PBKDF2 key derivation.
 * @returns Decrypted and parsed `QubePackageData`.
 * @throws If the ZIP is malformed, manifest is missing required fields, or
 *         decryption fails.
 */
export async function parseQubeFile(
  zipData: Uint8Array,
  password: string,
): Promise<QubePackageData> {
  // Unzip
  let files: Record<string, Uint8Array>;
  try {
    files = unzipSync(zipData);
  } catch (err) {
    throw new Error(
      `Failed to unzip .qube file: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  // Extract manifest.json
  const manifestBytes = files['manifest.json'];
  if (!manifestBytes) {
    throw new Error('Missing manifest.json in .qube ZIP file');
  }

  let manifest: QubeManifest;
  try {
    manifest = JSON.parse(decoder.decode(manifestBytes)) as QubeManifest;
  } catch (err) {
    throw new Error(
      `Failed to parse manifest.json: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  if (!manifest.salt || !manifest.nonce) {
    throw new Error('manifest.json is missing required "salt" or "nonce" fields');
  }

  // Extract data.enc
  const ciphertext = files['data.enc'];
  if (!ciphertext) {
    throw new Error('Missing data.enc in .qube ZIP file');
  }

  // Decode salt and nonce from hex
  const salt = fromHex(manifest.salt);
  const nonce = fromHex(manifest.nonce);

  // Derive key from password
  const derivedKey = deriveMasterKey(password, salt, DEFAULT_ITERATIONS);

  // decryptBytes expects nonce(12) || ciphertext
  const noncePlusCiphertext = new Uint8Array(nonce.length + ciphertext.length);
  noncePlusCiphertext.set(nonce, 0);
  noncePlusCiphertext.set(ciphertext, nonce.length);

  let plaintext: Uint8Array;
  try {
    plaintext = await decryptBytes(noncePlusCiphertext, derivedKey);
  } catch (err) {
    throw new Error(
      `Failed to decrypt .qube file (wrong password?): ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  let data: QubePackageData;
  try {
    data = JSON.parse(decoder.decode(plaintext)) as QubePackageData;
  } catch (err) {
    throw new Error(
      `Failed to parse decrypted .qube file JSON: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  return data;
}
