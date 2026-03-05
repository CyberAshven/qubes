/**
 * Tests for package/verify — Merkle-root based integrity verification.
 *
 * `verifyPackageIntegrity` collects block_hash (or blockHash) from the genesis
 * block and all memory blocks, recomputes the Merkle root, and compares it
 * against `metadata.merkleRoot`.
 */
import { describe, it, expect } from 'vitest';
import { verifyPackageIntegrity } from '../../src/package/verify.js';
import { computeMerkleRoot } from '../../src/crypto/merkle.js';
import type { QubePackageData } from '../../src/types/package.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a QubePackageData with a correct merkleRoot computed from the supplied hashes. */
function makeValidPackage(
  genesisHash: string,
  memoryHashes: string[],
  overrides: Partial<QubePackageData['metadata']> = {},
): QubePackageData {
  const allHashes = [genesisHash, ...memoryHashes];
  const merkleRoot = computeMerkleRoot(allHashes);

  return {
    metadata: {
      qubeId: 'TEST1234',
      qubeName: 'Test Qube',
      publicKey: '03' + 'ab'.repeat(32),
      chainLength: allHashes.length,
      merkleRoot,
      packageVersion: '1.0',
      packagedAt: 1700000000,
      packagedBy: 'test',
      hasNft: false,
      ...overrides,
    },
    genesisBlock: {
      block_number: 0,
      block_type: 'genesis',
      block_hash: genesisHash,
      content: { genesis_prompt: 'Hello' },
    },
    memoryBlocks: memoryHashes.map((h, i) => ({
      block_number: i + 1,
      block_type: 'thought',
      block_hash: h,
      content: { thought: `block ${i + 1}` },
    })),
    chainState: { version: '2.0' },
  };
}

// Deterministic test hashes — 64 lowercase hex characters each.
const HASH_A = 'aa'.repeat(32);
const HASH_B = 'bb'.repeat(32);
const HASH_C = 'cc'.repeat(32);
const HASH_D = 'dd'.repeat(32);

// ---------------------------------------------------------------------------
// Valid packages
// ---------------------------------------------------------------------------

describe('verifyPackageIntegrity — valid packages', () => {
  it('returns true for a single-block chain (genesis only, no memory blocks)', () => {
    const pkg = makeValidPackage(HASH_A, []);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('returns true for a two-block chain (genesis + one memory block)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('returns true for a four-block chain (genesis + three memory blocks)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C, HASH_D]);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('returns true when memory blocks use camelCase blockHash instead of block_hash', () => {
    // verify.ts tolerates both snake_case and camelCase key names.
    const genesisHash = HASH_A;
    const memHash = HASH_B;
    const merkleRoot = computeMerkleRoot([genesisHash, memHash]);

    const pkg: QubePackageData = {
      metadata: {
        qubeId: 'TEST1234',
        qubeName: 'Test Qube',
        publicKey: '03' + 'ab'.repeat(32),
        chainLength: 2,
        merkleRoot,
        packageVersion: '1.0',
        packagedAt: 1700000000,
        packagedBy: 'test',
        hasNft: false,
      },
      genesisBlock: {
        block_number: 0,
        block_type: 'genesis',
        block_hash: genesisHash, // snake_case on genesis
        content: {},
      },
      memoryBlocks: [
        {
          block_number: 1,
          block_type: 'thought',
          blockHash: memHash, // camelCase on memory block
          content: {},
        },
      ],
      chainState: {},
    };

    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('returns true when genesis block uses camelCase blockHash', () => {
    const genesisHash = HASH_A;
    const merkleRoot = computeMerkleRoot([genesisHash]);

    const pkg: QubePackageData = {
      metadata: {
        qubeId: 'TEST1234',
        qubeName: 'Test Qube',
        publicKey: '03' + 'ab'.repeat(32),
        chainLength: 1,
        merkleRoot,
        packageVersion: '1.0',
        packagedAt: 1700000000,
        packagedBy: 'test',
        hasNft: false,
      },
      genesisBlock: {
        block_number: 0,
        blockHash: genesisHash, // camelCase
        content: {},
      },
      memoryBlocks: [],
      chainState: {},
    };

    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('returns true for empty memoryBlocks with a correct single-hash merkle root', () => {
    // Single hash Merkle root == the hash itself (no hashing performed).
    const pkg = makeValidPackage(HASH_A, []);
    // The merkleRoot should equal HASH_A directly
    expect(pkg.metadata.merkleRoot).toBe(HASH_A);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Tampered / invalid packages
// ---------------------------------------------------------------------------

describe('verifyPackageIntegrity — tampered packages', () => {
  it('returns false when merkleRoot is tampered (one bit flipped)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    // Replace first character of the root to corrupt it
    pkg.metadata.merkleRoot = 'ff' + pkg.metadata.merkleRoot.slice(2);
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when merkleRoot is replaced with zeros', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    pkg.metadata.merkleRoot = '0'.repeat(64);
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when a memory block hash is altered', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    // Corrupt the second memory block's hash
    (pkg.memoryBlocks[1] as Record<string, unknown>)['block_hash'] = 'ee'.repeat(32);
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when the genesis block hash is altered', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    (pkg.genesisBlock as Record<string, unknown>)['block_hash'] = 'ff'.repeat(32);
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when a memory block is appended (hash not in root)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    // Inject an extra block without updating the merkle root
    pkg.memoryBlocks.push({
      block_number: 2,
      block_type: 'thought',
      block_hash: HASH_C,
      content: {},
    });
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when a memory block is removed (root still reflects original chain)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    // Remove a block without recalculating the root
    pkg.memoryBlocks.pop();
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when block order is swapped', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    // Swap the two memory blocks — same hashes, different order changes Merkle root
    [pkg.memoryBlocks[0], pkg.memoryBlocks[1]] = [pkg.memoryBlocks[1], pkg.memoryBlocks[0]];
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Missing hash fields
// ---------------------------------------------------------------------------

describe('verifyPackageIntegrity — missing block_hash fields', () => {
  it('returns false when genesis block has no block_hash or blockHash', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    // Remove the hash field from genesis
    delete (pkg.genesisBlock as Record<string, unknown>)['block_hash'];

    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when a memory block has no block_hash or blockHash', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    // Remove the hash from the first memory block
    delete (pkg.memoryBlocks[0] as Record<string, unknown>)['block_hash'];

    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when block_hash is set to a non-string (number)', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    (pkg.genesisBlock as Record<string, unknown>)['block_hash'] = 12345;
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });

  it('returns false when block_hash is set to null', () => {
    const pkg = makeValidPackage(HASH_A, [HASH_B]);
    (pkg.genesisBlock as Record<string, unknown>)['block_hash'] = null;
    expect(verifyPackageIntegrity(pkg)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Consistency with computeMerkleRoot
// ---------------------------------------------------------------------------

describe('verifyPackageIntegrity — consistency with computeMerkleRoot', () => {
  it('computed root matches what computeMerkleRoot returns for the same hashes', () => {
    const hashes = [HASH_A, HASH_B, HASH_C];
    const expectedRoot = computeMerkleRoot(hashes);

    const pkg = makeValidPackage(HASH_A, [HASH_B, HASH_C]);
    expect(pkg.metadata.merkleRoot).toBe(expectedRoot);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('single-hash root equals the hash itself (Merkle base case)', () => {
    const root = computeMerkleRoot([HASH_A]);
    expect(root).toBe(HASH_A);

    const pkg = makeValidPackage(HASH_A, []);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });

  it('large chain (10 blocks) verifies correctly', () => {
    // Generate 10 distinct 64-char hashes
    const hashes = Array.from({ length: 10 }, (_, i) =>
      i.toString(16).padStart(2, '0').repeat(32),
    );

    const [genesisHash, ...memHashes] = hashes;
    const pkg = makeValidPackage(genesisHash, memHashes);
    expect(verifyPackageIntegrity(pkg)).toBe(true);
  });
});
