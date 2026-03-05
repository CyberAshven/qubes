/**
 * PBKDF2-SHA256 master key derivation from user password.
 *
 * Ported from `crypto/keys.py` (lines 278-298).
 *
 * Uses `@noble/hashes/pbkdf2` and `@noble/hashes/sha256` for a pure-JS
 * implementation that works in both browsers and Node.js.
 *
 * The Python code returns `base64.urlsafe_b64encode(kdf.derive(password))` which
 * is used as a Fernet key. We expose both the raw 32-byte key (for AES-GCM
 * usage in the SDK) and the base64url-encoded variant (for interop with existing
 * Python Fernet-encrypted data).
 *
 * @module crypto/pbkdf2
 */

import { pbkdf2 } from '@noble/hashes/pbkdf2';
import { sha256 } from '@noble/hashes/sha256';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Default PBKDF2 iterations per OWASP 2025 recommendation. */
export const DEFAULT_ITERATIONS = 600_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const encoder = new TextEncoder();

/**
 * Base64url encode (RFC 4648 section 5, no padding).
 * Matches Python's `base64.urlsafe_b64encode` output (WITH padding).
 */
function base64urlEncode(bytes: Uint8Array): string {
  // Build a standard base64 string first
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const b64 = btoa(binary);
  // Replace +/ with -_ for URL safety (Python urlsafe_b64encode keeps padding)
  return b64.replace(/\+/g, '-').replace(/\//g, '_');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Derive a 32-byte master encryption key from a user password and salt
 * using PBKDF2-HMAC-SHA256.
 *
 * This returns the **raw key bytes** suitable for direct use with AES-256-GCM.
 *
 * Python equivalent: the inner `kdf.derive(password.encode())` call in
 * `derive_master_key_from_password` (before base64 encoding).
 *
 * @param password   - User's master password (UTF-8).
 * @param salt       - Random salt (typically 16 bytes).
 * @param iterations - Number of PBKDF2 iterations. Default: 600,000.
 * @returns Raw 32-byte derived key.
 */
export function deriveMasterKey(
  password: string,
  salt: Uint8Array,
  iterations: number = DEFAULT_ITERATIONS,
): Uint8Array {
  return pbkdf2(sha256, encoder.encode(password), salt, {
    c: iterations,
    dkLen: 32,
  });
}

/**
 * Derive a master key and return it as a base64url-encoded string.
 *
 * This matches the full output of Python's `derive_master_key_from_password`
 * which wraps the raw bytes with `base64.urlsafe_b64encode`. The resulting
 * 44-character string is a valid Fernet key (used by the existing Python
 * application for private key encryption).
 *
 * @param password   - User's master password (UTF-8).
 * @param salt       - Random salt (typically 16 bytes).
 * @param iterations - Number of PBKDF2 iterations. Default: 600,000.
 * @returns Base64url-encoded 32-byte key (44 characters with padding).
 */
export function deriveMasterKeyBase64(
  password: string,
  salt: Uint8Array,
  iterations: number = DEFAULT_ITERATIONS,
): string {
  const raw = deriveMasterKey(password, salt, iterations);
  return base64urlEncode(raw);
}
