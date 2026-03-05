/**
 * Cross-compatibility test: identity derivation (commitment, Qube ID)
 */
import { describe, it, expect } from 'vitest';
import { deriveCommitment, deriveQubeId } from '../../src/crypto/identity.js';
import vectors from './vectors.json';

describe('identity ↔ Python derive_commitment / derive_qube_id', () => {
  it('derives the same commitment as Python (SHA-256 of hex STRING)', () => {
    const result = deriveCommitment(vectors.commitment.publicKeyHex);
    expect(result).toBe(vectors.commitment.commitment);
  });

  it('derives the same Qube ID as Python (first 8 chars, uppercase)', () => {
    const result = deriveQubeId(vectors.qubeId.publicKeyHex);
    expect(result).toBe(vectors.qubeId.qubeId);
  });

  it('commitment is 64 hex characters', () => {
    const result = deriveCommitment(vectors.commitment.publicKeyHex);
    expect(result).toHaveLength(64);
    expect(result).toMatch(/^[0-9a-f]{64}$/);
  });

  it('Qube ID is 8 uppercase hex characters', () => {
    const result = deriveQubeId(vectors.qubeId.publicKeyHex);
    expect(result).toHaveLength(8);
    expect(result).toMatch(/^[0-9A-F]{8}$/);
  });
});
