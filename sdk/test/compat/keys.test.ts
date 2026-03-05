/**
 * Cross-compatibility test: secp256k1 key derivation
 */
import { describe, it, expect } from 'vitest';
import {
  getPublicKey,
  serializePublicKey,
  deserializePublicKey,
  privateKeyFromHex,
  generateKeyPair,
} from '../../src/crypto/keys.js';
import vectors from './vectors.json';

describe('keys ↔ Python key derivation', () => {
  it('derives the same compressed public key from a private key', () => {
    const privateKey = privateKeyFromHex(vectors.keyDerivation.privateKeyHex);
    const publicKey = getPublicKey(privateKey);
    const publicKeyHex = serializePublicKey(publicKey);
    expect(publicKeyHex).toBe(vectors.keyDerivation.publicKeyHex);
  });

  it('serializePublicKey produces 66-character lowercase hex', () => {
    const privateKey = privateKeyFromHex(vectors.keyDerivation.privateKeyHex);
    const publicKey = getPublicKey(privateKey);
    const hex = serializePublicKey(publicKey);
    expect(hex).toHaveLength(66);
    expect(hex).toMatch(/^0[23][0-9a-f]{64}$/);
  });

  it('deserializePublicKey round-trips with serializePublicKey', () => {
    const hex = vectors.keyDerivation.publicKeyHex;
    const bytes = deserializePublicKey(hex);
    const roundTripped = serializePublicKey(bytes);
    expect(roundTripped).toBe(hex);
  });

  it('generateKeyPair produces valid 33-byte compressed public key', () => {
    const { privateKey, publicKey } = generateKeyPair();
    expect(privateKey).toHaveLength(32);
    expect(publicKey).toHaveLength(33);
    expect(publicKey[0] === 0x02 || publicKey[0] === 0x03).toBe(true);
  });
});
