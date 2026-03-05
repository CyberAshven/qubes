/**
 * Cross-compatibility test: AES-256-GCM encryption
 */
import { describe, it, expect } from 'vitest';
import {
  encryptBlockData,
  decryptBlockData,
  encryptBytes,
  decryptBytes,
} from '../../src/crypto/aes.js';
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

/** Convert Uint8Array to hex string */
function toHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

describe('AES-256-GCM ↔ Python encrypt_block_data', () => {
  const key = fromHex(vectors.aes256gcm.keyHex);

  it('encryptBlockData → decryptBlockData round-trip preserves data', async () => {
    const plaintext = vectors.aes256gcm.plaintext;
    const encrypted = await encryptBlockData(plaintext, key);

    expect(encrypted.algorithm).toBe('AES-256-GCM');
    expect(encrypted.nonce).toHaveLength(24); // 12 bytes = 24 hex chars
    expect(encrypted.ciphertext.length).toBeGreaterThan(0);

    const decrypted = await decryptBlockData(encrypted, key);
    expect(decrypted).toEqual(plaintext);
  });

  it('can decrypt Python-generated ciphertext', async () => {
    const encrypted = vectors.aes256gcm.result;
    const decrypted = await decryptBlockData(encrypted, key);
    expect(decrypted).toEqual(vectors.aes256gcm.plaintext);
  });

  it('encryptBytes → decryptBytes round-trip', async () => {
    const plaintext = new TextEncoder().encode('hello world');
    const encrypted = await encryptBytes(plaintext, key);

    // Format: nonce(12) || ciphertext+tag
    expect(encrypted.length).toBe(12 + plaintext.length + 16); // 16 = GCM tag

    const decrypted = await decryptBytes(encrypted, key);
    expect(new TextDecoder().decode(decrypted)).toBe('hello world');
  });

  it('wrong key fails decryption', async () => {
    const encrypted = vectors.aes256gcm.result;
    const wrongKey = fromHex('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff');

    await expect(decryptBlockData(encrypted, wrongKey)).rejects.toThrow();
  });
});
