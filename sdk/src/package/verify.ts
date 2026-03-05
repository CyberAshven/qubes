/**
 * Qube package integrity verification.
 *
 * Recomputes the Merkle root from all block hashes in a package and checks it
 * against the stored `metadata.merkleRoot`. This verifies that the chain has
 * not been tampered with since the package was created.
 *
 * @module package/verify
 */

import { computeMerkleRoot } from '../crypto/merkle.js';
import type { QubePackageData } from '../types/package.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract the `block_hash` field from a block record, tolerating both
 * camelCase and snake_case key names used across different code paths.
 */
function extractBlockHash(block: Record<string, unknown>): string | null {
  if (typeof block['block_hash'] === 'string') return block['block_hash'];
  if (typeof block['blockHash'] === 'string') return block['blockHash'];
  return null;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Verify the integrity of a Qube package by recomputing its Merkle root.
 *
 * Collects the `block_hash` from the genesis block and all memory blocks,
 * computes the Merkle root, and compares it against `data.metadata.merkleRoot`.
 *
 * Returns `false` (rather than throwing) on any mismatch or missing hash so
 * callers can decide how to handle a corrupt or tampered package.
 *
 * Python equivalent: Merkle root check inside `verify_chain_integrity` in
 * `blockchain/chain_package.py`.
 *
 * @param data - Decrypted Qube package data.
 * @returns `true` if the recomputed Merkle root matches the stored root,
 *          `false` otherwise (including when any block hash is missing).
 */
export function verifyPackageIntegrity(data: QubePackageData): boolean {
  const hashes: string[] = [];

  // Collect genesis block hash
  const genesisHash = extractBlockHash(data.genesisBlock);
  if (genesisHash === null) {
    return false;
  }
  hashes.push(genesisHash);

  // Collect all memory block hashes in order
  for (const block of data.memoryBlocks) {
    const blockHash = extractBlockHash(block);
    if (blockHash === null) {
      return false;
    }
    hashes.push(blockHash);
  }

  // Recompute Merkle root and compare
  const computedRoot = computeMerkleRoot(hashes);
  return computedRoot === data.metadata.merkleRoot;
}
