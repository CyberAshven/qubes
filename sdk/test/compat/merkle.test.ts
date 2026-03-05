/**
 * Cross-compatibility test: Merkle tree root computation
 */
import { describe, it, expect } from 'vitest';
import { computeMerkleRoot, verifyMerkleProof } from '../../src/crypto/merkle.js';
import vectors from './vectors.json';

describe('Merkle root ↔ Python compute_merkle_root', () => {
  for (const tc of vectors.merkleRoot.cases) {
    it(`case: ${tc.name}`, () => {
      const root = computeMerkleRoot(tc.hashes);
      expect(root).toBe(tc.root);
    });
  }
});

describe('Merkle proof verification', () => {
  it('valid proof verifies correctly', () => {
    // Build a simple 2-hash tree and verify leaf inclusion
    const hashes = vectors.merkleRoot.cases[2].hashes; // "two" case
    const root = vectors.merkleRoot.cases[2].root;
    const leaf = hashes[0];
    const sibling = hashes[1];

    // For a 2-hash tree, the proof for the left leaf is: sibling on the right
    const valid = verifyMerkleProof(leaf, [{ hash: sibling, position: 'right' }], root);
    expect(valid).toBe(true);
  });

  it('invalid proof fails', () => {
    const root = vectors.merkleRoot.cases[2].root;
    const leaf = vectors.merkleRoot.cases[2].hashes[0];

    const valid = verifyMerkleProof(leaf, [{ hash: 'ff'.repeat(32), position: 'right' }], root);
    expect(valid).toBe(false);
  });
});
