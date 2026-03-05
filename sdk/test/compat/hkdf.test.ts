/**
 * Cross-compatibility test: HKDF-SHA256 key derivation
 */
import { describe, it, expect } from 'vitest';
import { deriveBlockKey, deriveChainStateKey } from '../../src/crypto/hkdf.js';
import vectors from './vectors.json';

/** Convert Uint8Array to hex string */
function toHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

/** Convert hex string to Uint8Array */
function fromHex(hex: string): Uint8Array {
  const len = hex.length >>> 1;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

describe('HKDF ↔ Python derive_block_key / derive_chain_state_key', () => {
  const masterKey = fromHex(vectors.hkdf.masterKeyHex);

  it('derives identical block keys for block_0, block_1, block_42', () => {
    for (const vec of vectors.hkdf.blockKeys) {
      const derived = deriveBlockKey(masterKey, vec.blockNumber);
      expect(toHex(derived)).toBe(vec.derivedKeyHex);
    }
  });

  it('derives identical chain state key', () => {
    const derived = deriveChainStateKey(masterKey);
    expect(toHex(derived)).toBe(vectors.hkdf.chainStateKey.derivedKeyHex);
  });

  it('derived keys are 32 bytes', () => {
    const key = deriveBlockKey(masterKey, 0);
    expect(key).toHaveLength(32);
  });

  it('different block numbers produce different keys', () => {
    const key0 = deriveBlockKey(masterKey, 0);
    const key1 = deriveBlockKey(masterKey, 1);
    expect(toHex(key0)).not.toBe(toHex(key1));
  });
});
