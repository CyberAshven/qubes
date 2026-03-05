/**
 * Binary Merkle tree for memory chain integrity verification.
 *
 * Ported from `crypto/merkle.py`.
 *
 * The Merkle tree uses SHA-256 and concatenates sibling hashes as UTF-8
 * hex strings (matching the Python implementation which does
 * `hashlib.sha256((left + right).encode()).hexdigest()`).
 *
 * @module crypto/merkle
 */

import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex } from '@noble/hashes/utils';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const utf8 = new TextEncoder();

/** SHA-256 hash of a UTF-8 string, returned as hex. */
function sha256Hex(str: string): string {
  return bytesToHex(sha256(utf8.encode(str)));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Compute the Merkle root of a list of block hashes.
 *
 * If the list is empty, returns 64 zero characters. If odd-length at any
 * level, the last hash is duplicated.
 *
 * Python equivalent: `compute_merkle_root` in `crypto/merkle.py`.
 *
 * @param hashes - Array of 64-character hex block hash strings.
 * @returns 64-character hex Merkle root.
 */
export function computeMerkleRoot(hashes: string[]): string {
  if (hashes.length === 0) {
    return '0'.repeat(64);
  }

  if (hashes.length === 1) {
    return hashes[0];
  }

  // Build Merkle tree bottom-up
  let currentLevel = [...hashes];

  while (currentLevel.length > 1) {
    const nextLevel: string[] = [];

    for (let i = 0; i < currentLevel.length; i += 2) {
      const left = currentLevel[i];

      // If odd number of nodes, duplicate the last one
      const right =
        i + 1 < currentLevel.length ? currentLevel[i + 1] : left;

      // Hash the concatenation of the two hex strings (as UTF-8)
      nextLevel.push(sha256Hex(left + right));
    }

    currentLevel = nextLevel;
  }

  return currentLevel[0];
}

/** A single step in a Merkle proof path. */
export interface MerkleProofStep {
  /** Sibling hash at this tree level. */
  hash: string;
  /** Whether the sibling is on the left or right. */
  position: 'left' | 'right';
}

/**
 * Verify a Merkle inclusion proof for a given block hash.
 *
 * Python equivalent: `verify_merkle_proof` in `crypto/merkle.py`.
 *
 * @param hash  - Block hash to verify.
 * @param proof - Array of proof steps from leaf to root.
 * @param root  - Expected Merkle root.
 * @returns `true` if the proof is valid.
 */
export function verifyMerkleProof(
  hash: string,
  proof: MerkleProofStep[],
  root: string,
): boolean {
  let currentHash = hash;

  for (const step of proof) {
    if (step.position === 'left') {
      // Sibling is on the left
      currentHash = sha256Hex(step.hash + currentHash);
    } else {
      // Sibling is on the right
      currentHash = sha256Hex(currentHash + step.hash);
    }
  }

  return currentHash === root;
}
