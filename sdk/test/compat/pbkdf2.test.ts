/**
 * Cross-compatibility test: PBKDF2-SHA256 master key derivation
 */
import { describe, it, expect } from 'vitest';
import { deriveMasterKey, deriveMasterKeyBase64 } from '../../src/crypto/pbkdf2.js';
import vectors from './vectors.json';

/** Convert hex string to Uint8Array */
function fromHex(hex: string): Uint8Array {
  const len = hex.length >>> 1;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

describe('PBKDF2 ↔ Python derive_master_key_from_password', () => {
  const password = vectors.pbkdf2.password;
  const salt = fromHex(vectors.pbkdf2.saltHex);

  it('produces identical base64url output for 1000 iterations (fast test)', () => {
    const vec = vectors.pbkdf2.vectors[0]; // 1000 iterations
    const result = deriveMasterKeyBase64(password, salt, vec.iterations);
    expect(result).toBe(vec.derivedKeyBase64url);
  });

  it('produces identical base64url output for 600000 iterations (production)', () => {
    const vec = vectors.pbkdf2.vectors[1]; // 600000 iterations
    const result = deriveMasterKeyBase64(password, salt, vec.iterations);
    expect(result).toBe(vec.derivedKeyBase64url);
  }, 30_000); // Allow 30 seconds for 600K iterations

  it('raw key is 32 bytes', () => {
    const raw = deriveMasterKey(password, salt, 1000);
    expect(raw).toHaveLength(32);
  });
});
