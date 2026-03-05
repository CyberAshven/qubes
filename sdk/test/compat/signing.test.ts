/**
 * Cross-compatibility test: block hashing and signing
 */
import { describe, it, expect } from 'vitest';
import {
  hashBlock,
  signBlock,
  verifyBlockSignature,
  signMessage,
  verifyMessage,
} from '../../src/crypto/signing.js';
import {
  getPublicKey,
  privateKeyFromHex,
} from '../../src/crypto/keys.js';
import vectors from './vectors.json';

const privateKey = privateKeyFromHex(vectors.keyDerivation.privateKeyHex);
const publicKey = getPublicKey(privateKey);

describe('block hashing ↔ Python hash_block', () => {
  it('produces identical hash for a genesis block', () => {
    const hash = hashBlock(vectors.blockHashing.block);
    expect(hash).toBe(vectors.blockHashing.blockHash);
  });

  it('produces identical hash for a standard block', () => {
    const hash = hashBlock(vectors.blockSigningStandard.block);
    expect(hash).toBe(vectors.blockSigningStandard.blockHash);
  });
});

describe('block signing ↔ Python sign_block', () => {
  it('genesis block: TS signature verifiable with Python pubkey', () => {
    const block = vectors.blockSigningGenesis.block;
    const sig = signBlock(block, privateKey);

    // Verify our own signature
    const valid = verifyBlockSignature(block, sig, publicKey);
    expect(valid).toBe(true);
  });

  it('genesis block: Python signature verifiable in TS', () => {
    const block = vectors.blockSigningGenesis.block;
    const pythonSig = vectors.blockSigningGenesis.signature;
    const pubKeyBytes = getPublicKey(privateKey);

    const valid = verifyBlockSignature(block, pythonSig, pubKeyBytes);
    expect(valid).toBe(true);
  });

  it('standard block: TS signature verifiable with Python pubkey', () => {
    const block = vectors.blockSigningStandard.block;
    const sig = signBlock(block, privateKey);

    const valid = verifyBlockSignature(block, sig, publicKey);
    expect(valid).toBe(true);
  });

  it('standard block: Python signature verifiable in TS', () => {
    const block = vectors.blockSigningStandard.block;
    const pythonSig = vectors.blockSigningStandard.signature;
    const pubKeyBytes = getPublicKey(privateKey);

    const valid = verifyBlockSignature(block, pythonSig, pubKeyBytes);
    expect(valid).toBe(true);
  });

  it('invalid signature returns false (not throws)', () => {
    const block = vectors.blockSigningGenesis.block;
    const valid = verifyBlockSignature(block, 'deadbeef', publicKey);
    expect(valid).toBe(false);
  });
});

describe('message signing ↔ Python sign_message', () => {
  it('sign and verify round-trip', () => {
    const message = 'test message for signing';
    const sig = signMessage(message, privateKey);
    const valid = verifyMessage(message, sig, publicKey);
    expect(valid).toBe(true);
  });

  it('wrong message fails verification', () => {
    const sig = signMessage('correct message', privateKey);
    const valid = verifyMessage('wrong message', sig, publicKey);
    expect(valid).toBe(false);
  });
});
