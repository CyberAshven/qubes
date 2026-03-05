/**
 * End-to-end integration test for the @qubesai/sdk.
 *
 * Exercises the full Qube lifecycle in a single progressive describe block:
 *   keygen → genesis → memory blocks → sign → verify → merkle → chain state
 *   → AES round-trip → ECIES round-trip → binary package → ZIP package → BCMR
 *   → per-block HKDF encryption round-trip
 *
 * All state is accumulated across `it` blocks via shared variables so that
 * later steps can operate on artifacts produced by earlier steps. The test
 * suite is intentionally ordered — earlier failures cascade naturally.
 */

import { describe, it, expect, beforeAll } from 'vitest';

// Crypto primitives
import { generateKeyPair, serializePublicKey } from '../../src/crypto/keys.js';
import { deriveCommitment, deriveQubeId } from '../../src/crypto/identity.js';
import { signBlock, verifyBlockSignature, hashBlock } from '../../src/crypto/signing.js';
import { encryptBlockData, decryptBlockData } from '../../src/crypto/aes.js';
import { deriveBlockKey, deriveChainStateKey } from '../../src/crypto/hkdf.js';
import { deriveMasterKey } from '../../src/crypto/pbkdf2.js';
import { eciesEncrypt, eciesDecrypt } from '../../src/crypto/ecies.js';
import { computeMerkleRoot } from '../../src/crypto/merkle.js';

// Block factories
import { createGenesisBlock } from '../../src/blocks/genesis.js';
import {
  createThoughtBlock,
  createMessageBlock,
  createDecisionBlock,
} from '../../src/blocks/memory.js';
import { QubeBlock } from '../../src/blocks/block.js';
import { createDefaultChainState } from '../../src/blocks/chain-state.js';

// Package create / parse / verify
import { createBinaryPackage, createQubeFile } from '../../src/package/create.js';
import { parseBinaryPackage, parseQubeFile } from '../../src/package/parse.js';
import { verifyPackageIntegrity } from '../../src/package/verify.js';

// BCMR metadata generation
import { generateBcmrMetadata } from '../../src/bcmr/generate.js';

// Types
import { BlockType } from '../../src/types/block.js';
import type { QubePackageData } from '../../src/types/package.js';

// ---------------------------------------------------------------------------
// Shared state — built up progressively across test steps
// ---------------------------------------------------------------------------

let ownerKeyPair: { privateKey: Uint8Array; publicKey: Uint8Array };
let qubeKeyPair: { privateKey: Uint8Array; publicKey: Uint8Array };

let ownerPublicKeyHex: string;
let qubePublicKeyHex: string;

let qubeId: string;
let commitment: string;

let genesisBlock: QubeBlock;
let genesisSignature: string;

let thoughtBlock: QubeBlock;
let messageBlock: QubeBlock;
let decisionBlock: QubeBlock;
let memoryBlocks: QubeBlock[];

let allBlockHashes: string[];
let merkleRoot: string;

let chainState: Record<string, unknown>;

let masterKey: Uint8Array;

// ---------------------------------------------------------------------------
// Test password (deliberately lightweight iterations for test speed)
// ---------------------------------------------------------------------------

const TEST_PASSWORD = 'test-integration-password-2025';
const TEST_SALT = new Uint8Array(16).fill(0x42); // deterministic salt for tests

// ---------------------------------------------------------------------------
// Helper: Uint8Array deep equality (for decryption round-trip checks)
// ---------------------------------------------------------------------------

function uint8ArrayEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// The lifecycle suite
// ---------------------------------------------------------------------------

describe('SDK end-to-end lifecycle', () => {

  // ── Step 1: Key generation ────────────────────────────────────────────────

  it('generates owner and qube key pairs with 33-byte compressed public keys', () => {
    ownerKeyPair = generateKeyPair();
    qubeKeyPair = generateKeyPair();

    // Private keys must be 32 bytes
    expect(ownerKeyPair.privateKey).toBeInstanceOf(Uint8Array);
    expect(ownerKeyPair.privateKey).toHaveLength(32);
    expect(qubeKeyPair.privateKey).toBeInstanceOf(Uint8Array);
    expect(qubeKeyPair.privateKey).toHaveLength(32);

    // Compressed public keys must be 33 bytes (02 or 03 prefix)
    expect(ownerKeyPair.publicKey).toBeInstanceOf(Uint8Array);
    expect(ownerKeyPair.publicKey).toHaveLength(33);
    expect(qubeKeyPair.publicKey).toBeInstanceOf(Uint8Array);
    expect(qubeKeyPair.publicKey).toHaveLength(33);

    // First byte must be 0x02 or 0x03 (compressed secp256k1 prefix)
    expect([0x02, 0x03]).toContain(ownerKeyPair.publicKey[0]);
    expect([0x02, 0x03]).toContain(qubeKeyPair.publicKey[0]);

    // Owner and qube keys must differ (astronomically unlikely to collide)
    expect(ownerKeyPair.privateKey).not.toEqual(qubeKeyPair.privateKey);
    expect(ownerKeyPair.publicKey).not.toEqual(qubeKeyPair.publicKey);

    // Serialize to hex for use in subsequent steps
    ownerPublicKeyHex = serializePublicKey(ownerKeyPair.publicKey);
    qubePublicKeyHex = serializePublicKey(qubeKeyPair.publicKey);

    expect(ownerPublicKeyHex).toHaveLength(66);
    expect(qubePublicKeyHex).toHaveLength(66);
    expect(ownerPublicKeyHex).toMatch(/^[0-9a-f]{66}$/);
    expect(qubePublicKeyHex).toMatch(/^[0-9a-f]{66}$/);
  });

  // ── Step 2: Identity derivation ───────────────────────────────────────────

  it('derives a 64-char commitment and 8-char uppercase Qube ID from the qube public key', () => {
    commitment = deriveCommitment(qubePublicKeyHex);
    qubeId = deriveQubeId(qubePublicKeyHex);

    // Commitment: 64-char lowercase hex (SHA-256 output)
    expect(commitment).toHaveLength(64);
    expect(commitment).toMatch(/^[0-9a-f]{64}$/);

    // Qube ID: first 8 chars of commitment, uppercased
    expect(qubeId).toHaveLength(8);
    expect(qubeId).toMatch(/^[0-9A-F]{8}$/);
    expect(qubeId).toBe(commitment.slice(0, 8).toUpperCase());

    // Deterministic: same public key → same IDs
    expect(deriveCommitment(qubePublicKeyHex)).toBe(commitment);
    expect(deriveQubeId(qubePublicKeyHex)).toBe(qubeId);

    // Different keys → different commitments
    expect(deriveCommitment(ownerPublicKeyHex)).not.toBe(commitment);
  });

  // ── Step 3: Genesis block creation ────────────────────────────────────────

  it('creates a genesis block with correct structure and computed hash', () => {
    genesisBlock = createGenesisBlock({
      qubeId,
      qubeName: 'IntegrationTestQube',
      creator: 'test-user-001',
      publicKey: qubePublicKeyHex,
      genesisPrompt: 'You are a test AI agent used for integration testing of the Qubes SDK.',
      aiModel: 'claude-opus-4-6',
      voiceModel: 'openai:alloy',
      avatar: { style: 'pixel', seed: 99, color: '#4A90E2' },
      favoriteColor: '#4A90E2',
      homeBlockchain: 'bitcoin_cash',
      defaultTrustLevel: 50,
    });

    // Block number must be 0 for genesis
    expect(genesisBlock.blockNumber).toBe(0);

    // Block type must be GENESIS
    expect(genesisBlock.blockType).toBe(BlockType.GENESIS);
    expect(genesisBlock.blockType).toBe('GENESIS');

    // Must not be encrypted or temporary
    expect(genesisBlock.encrypted).toBe(false);
    expect(genesisBlock.temporary).toBe(false);

    // Previous hash must be 64 zeros (chain root)
    expect(genesisBlock.previousHash).toBe('0'.repeat(64));

    // block_hash must be a 64-char lowercase hex string
    expect(genesisBlock.blockHash).not.toBeNull();
    expect(genesisBlock.blockHash).toHaveLength(64);
    expect(genesisBlock.blockHash).toMatch(/^[0-9a-f]{64}$/);

    // block_hash must be deterministically reproducible
    expect(genesisBlock.blockHash).toBe(genesisBlock.computeHash());

    // Identity fields must be stored correctly
    const dict = genesisBlock.toDict();
    expect(dict.qube_id).toBe(qubeId);
    expect(dict.qube_name).toBe('IntegrationTestQube');
    expect(dict.creator).toBe('test-user-001');
    expect(dict.public_key).toBe(qubePublicKeyHex);
    expect(dict.ai_model).toBe('claude-opus-4-6');
    expect(dict.voice_model).toBe('openai:alloy');
    expect(dict.home_blockchain).toBe('bitcoin_cash');
  });

  // ── Step 4: Sign genesis block ────────────────────────────────────────────

  it('signs the genesis block and verifies the signature', () => {
    const dict = genesisBlock.toDict();
    genesisSignature = signBlock(dict, qubeKeyPair.privateKey);

    // DER-encoded ECDSA signature: starts with 0x30, typically 70-72 bytes = 140-144 hex chars
    expect(genesisSignature).toMatch(/^[0-9a-f]+$/);
    expect(genesisSignature.length).toBeGreaterThanOrEqual(140);
    expect(genesisSignature.length).toBeLessThanOrEqual(146);
    // DER SEQUENCE tag
    expect(genesisSignature.startsWith('30')).toBe(true);

    // Verification against the correct key must return true
    expect(verifyBlockSignature(dict, genesisSignature, qubeKeyPair.publicKey)).toBe(true);

    // Verification against a different (owner) key must return false
    expect(verifyBlockSignature(dict, genesisSignature, ownerKeyPair.publicKey)).toBe(false);

    // Store signature on block
    genesisBlock.signature = genesisSignature;
  });

  // ── Step 5: Create memory blocks ──────────────────────────────────────────

  it('creates thought, message, and decision blocks with correct types and incrementing block numbers', () => {
    const genesisHash = genesisBlock.blockHash!;

    thoughtBlock = createThoughtBlock({
      qubeId,
      blockNumber: 1,
      previousHash: genesisHash,
      internalMonologue: 'I need to analyze the test scenario and prepare my response.',
      reasoningChain: [
        'Identify the user request',
        'Retrieve relevant context from memory',
        'Formulate a coherent response',
      ],
      confidence: 0.95,
    });

    messageBlock = createMessageBlock({
      qubeId,
      blockNumber: 2,
      previousHash: thoughtBlock.blockHash!,
      messageType: 'qube_to_human',
      recipientId: 'test-user-001',
      messageBody: 'Hello! I have processed your integration test request successfully.',
      conversationId: 'conv-test-001',
      requiresResponse: false,
    });

    decisionBlock = createDecisionBlock({
      qubeId,
      blockNumber: 3,
      previousHash: messageBlock.blockHash!,
      decision: 'Adopt a more concise communication style',
      fromValue: 'verbose',
      toValue: 'concise',
      reasoning: 'Analysis of past messages shows the user prefers brevity.',
      impactAssessment: 'Minor style adjustment; content quality unchanged.',
    });

    memoryBlocks = [thoughtBlock, messageBlock, decisionBlock];

    // Verify block numbers are sequential
    expect(thoughtBlock.blockNumber).toBe(1);
    expect(messageBlock.blockNumber).toBe(2);
    expect(decisionBlock.blockNumber).toBe(3);

    // Verify block types
    expect(thoughtBlock.blockType).toBe(BlockType.THOUGHT);
    expect(messageBlock.blockType).toBe(BlockType.MESSAGE);
    expect(decisionBlock.blockType).toBe(BlockType.DECISION);

    // All memory blocks are encrypted and permanent
    expect(thoughtBlock.encrypted).toBe(true);
    expect(messageBlock.encrypted).toBe(true);
    expect(decisionBlock.encrypted).toBe(true);

    expect(thoughtBlock.temporary).toBe(false);
    expect(messageBlock.temporary).toBe(false);
    expect(decisionBlock.temporary).toBe(false);

    // All must have 64-char block hashes
    for (const block of memoryBlocks) {
      expect(block.blockHash).not.toBeNull();
      expect(block.blockHash).toHaveLength(64);
      expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
    }

    // Chain linkage: each block must reference the previous block's hash
    expect(thoughtBlock.toDict().previous_hash).toBe(genesisHash);
    expect(messageBlock.toDict().previous_hash).toBe(thoughtBlock.blockHash);
    expect(decisionBlock.toDict().previous_hash).toBe(messageBlock.blockHash);

    // Block hashes must be distinct
    const hashes = memoryBlocks.map((b) => b.blockHash);
    const uniqueHashes = new Set(hashes);
    expect(uniqueHashes.size).toBe(3);
  });

  // ── Step 6: Sign memory blocks ────────────────────────────────────────────

  it('signs all memory blocks with the qube private key and verifies each signature', () => {
    for (const block of memoryBlocks) {
      const dict = block.toDict();
      const sig = signBlock(dict, qubeKeyPair.privateKey);

      // Signature must be a non-empty DER hex string
      expect(sig).toMatch(/^[0-9a-f]+$/);
      expect(sig.length).toBeGreaterThanOrEqual(140);
      expect(sig.startsWith('30')).toBe(true);

      // Correct key → valid
      expect(verifyBlockSignature(dict, sig, qubeKeyPair.publicKey)).toBe(true);

      // Wrong key → invalid
      expect(verifyBlockSignature(dict, sig, ownerKeyPair.publicKey)).toBe(false);

      // Persist signature on the block
      block.signature = sig;
    }

    // All blocks now have signatures
    for (const block of memoryBlocks) {
      expect(block.signature).not.toBeNull();
      expect(block.signature).toBeTruthy();
    }
  });

  // ── Step 7: Merkle root ───────────────────────────────────────────────────

  it('computes a 64-char Merkle root from genesis and all memory block hashes', () => {
    allBlockHashes = [
      genesisBlock.blockHash!,
      ...memoryBlocks.map((b) => b.blockHash!),
    ];

    expect(allBlockHashes).toHaveLength(4);

    merkleRoot = computeMerkleRoot(allBlockHashes);

    // Merkle root must be a 64-char hex string
    expect(merkleRoot).toHaveLength(64);
    expect(merkleRoot).toMatch(/^[0-9a-f]{64}$/);

    // A single-element list returns the element itself unchanged
    expect(computeMerkleRoot([genesisBlock.blockHash!])).toBe(genesisBlock.blockHash!);

    // Empty list returns 64 zeros
    expect(computeMerkleRoot([])).toBe('0'.repeat(64));

    // Deterministic: same inputs → same root
    expect(computeMerkleRoot(allBlockHashes)).toBe(merkleRoot);

    // Changing any hash changes the root
    const alteredHashes = [...allBlockHashes];
    alteredHashes[0] = '0'.repeat(64);
    expect(computeMerkleRoot(alteredHashes)).not.toBe(merkleRoot);
  });

  // ── Step 8: Chain state creation ─────────────────────────────────────────

  it('creates a default chain state with version "2.0" from the genesis block', () => {
    const genesisDict = genesisBlock.toDict();
    chainState = createDefaultChainState(genesisDict, qubeId);

    // Version must be '2.0'
    expect(chainState.version).toBe('2.0');

    // Qube ID must match
    expect(chainState.qube_id).toBe(qubeId);

    // Chain section must reflect genesis block
    const chain = chainState.chain as Record<string, unknown>;
    expect(chain.length).toBe(1);
    expect(chain.latest_block_number).toBe(0);
    expect(chain.latest_block_hash).toBe(genesisBlock.blockHash);
    expect(chain.genesis_hash).toBe(genesisBlock.blockHash);
    expect(chain.total_blocks).toBe(1);
    expect(chain.permanent_blocks).toBe(1);
    expect(chain.session_blocks).toBe(0);

    // Settings must reflect genesis AI model
    const settings = chainState.settings as Record<string, unknown>;
    expect(settings.model_locked).toBe(true);
    expect(settings.model_locked_to).toBe('claude-opus-4-6');

    // Stats must start at zero
    const stats = chainState.stats as Record<string, unknown>;
    expect(stats.total_messages_sent).toBe(0);
    expect(stats.total_messages_received).toBe(0);
    expect(stats.total_tokens_used).toBe(0);
    expect(stats.total_api_cost).toBe(0.0);
    expect(stats.total_tool_calls).toBe(0);

    // Block counts section
    const blockCounts = chainState.block_counts as Record<string, unknown>;
    expect(blockCounts.GENESIS).toBe(1);
    expect(blockCounts.MESSAGE).toBe(0);

    // Health must start healthy
    const health = chainState.health as Record<string, unknown>;
    expect(health.overall_status).toBe('healthy');
  });

  // ── Step 9: Chain state AES encryption round-trip ────────────────────────

  it('encrypts and decrypts chain state using an HKDF-derived chain state key', async () => {
    // Use a short iteration count for test speed (the real app uses 600K)
    masterKey = deriveMasterKey(TEST_PASSWORD, TEST_SALT, 1000);

    expect(masterKey).toBeInstanceOf(Uint8Array);
    expect(masterKey).toHaveLength(32);

    const chainStateKey = deriveChainStateKey(masterKey);
    expect(chainStateKey).toBeInstanceOf(Uint8Array);
    expect(chainStateKey).toHaveLength(32);

    // Keys must differ from master (domain-separated by HKDF)
    expect(chainStateKey).not.toEqual(masterKey);

    // Encrypt the chain state dict
    const encrypted = await encryptBlockData(chainState, chainStateKey);

    // Encrypted output structure
    expect(encrypted).toHaveProperty('ciphertext');
    expect(encrypted).toHaveProperty('nonce');
    expect(encrypted).toHaveProperty('algorithm');
    expect(encrypted.algorithm).toBe('AES-256-GCM');
    expect(encrypted.nonce).toMatch(/^[0-9a-f]{24}$/); // 12 bytes = 24 hex chars
    expect(encrypted.ciphertext.length).toBeGreaterThan(0);

    // Decrypt and verify round-trip
    const decrypted = await decryptBlockData(encrypted, chainStateKey);

    // Key fields must survive the round-trip
    expect(decrypted.version).toBe('2.0');
    expect(decrypted.qube_id).toBe(qubeId);

    const chain = decrypted.chain as Record<string, unknown>;
    expect(chain.latest_block_hash).toBe(genesisBlock.blockHash);

    // Decryption with wrong key must throw
    const wrongKey = deriveMasterKey('wrong-password', TEST_SALT, 1000);
    const wrongChainKey = deriveChainStateKey(wrongKey);
    await expect(decryptBlockData(encrypted, wrongChainKey)).rejects.toThrow();
  });

  // ── Step 10: ECIES asymmetric encryption round-trip ──────────────────────

  it('encrypts a secret from owner to qube via ECIES and decrypts it with the qube private key', async () => {
    const secretMessage = new TextEncoder().encode(
      'This is a secret only the qube can read: session_key=0xdeadbeef',
    );

    // Encrypt for the qube public key
    const ciphertext = await eciesEncrypt(secretMessage, qubeKeyPair.publicKey);

    // Output layout: ephemeral pubkey (33) + nonce (12) + ciphertext+tag (>= 16)
    expect(ciphertext).toBeInstanceOf(Uint8Array);
    expect(ciphertext.length).toBeGreaterThan(33 + 12 + 16);

    // Decrypt with qube private key
    const recovered = await eciesDecrypt(ciphertext, qubeKeyPair.privateKey);

    expect(uint8ArrayEqual(recovered, secretMessage)).toBe(true);

    // Decryption with wrong (owner) private key must throw
    await expect(eciesDecrypt(ciphertext, ownerKeyPair.privateKey)).rejects.toThrow();

    // Encrypt an empty payload — edge case
    const emptyPayload = new Uint8Array(0);
    const encryptedEmpty = await eciesEncrypt(emptyPayload, qubeKeyPair.publicKey);
    const recoveredEmpty = await eciesDecrypt(encryptedEmpty, qubeKeyPair.privateKey);
    expect(uint8ArrayEqual(recoveredEmpty, emptyPayload)).toBe(true);

    // Encrypt a larger binary blob
    const largePayload = globalThis.crypto.getRandomValues(new Uint8Array(1024));
    const encryptedLarge = await eciesEncrypt(largePayload, qubeKeyPair.publicKey);
    const recoveredLarge = await eciesDecrypt(encryptedLarge, qubeKeyPair.privateKey);
    expect(uint8ArrayEqual(recoveredLarge, largePayload)).toBe(true);
  });

  // ── Step 11: Binary package create / parse / verify ──────────────────────

  it('creates, parses, and verifies integrity of a binary IPFS package', async () => {
    const packageData: QubePackageData = {
      metadata: {
        qubeId,
        qubeName: 'IntegrationTestQube',
        publicKey: qubePublicKeyHex,
        chainLength: 4,
        merkleRoot,
        packageVersion: '1.0',
        packagedAt: Math.floor(Date.now() / 1000),
        packagedBy: 'test-user-001',
        hasNft: false,
      },
      genesisBlock: genesisBlock.toDict(),
      memoryBlocks: memoryBlocks.map((b) => b.toDict()),
      chainState,
    };

    // Create binary package with auto-generated key
    const { encrypted, key } = await createBinaryPackage(packageData);

    // Verify binary structure: starts with magic "QUBE" + version byte 0x01
    expect(encrypted).toBeInstanceOf(Uint8Array);
    expect(encrypted.length).toBeGreaterThan(5 + 12 + 16); // header + nonce + min ciphertext
    expect(encrypted[0]).toBe(0x51); // 'Q'
    expect(encrypted[1]).toBe(0x55); // 'U'
    expect(encrypted[2]).toBe(0x42); // 'B'
    expect(encrypted[3]).toBe(0x45); // 'E'
    expect(encrypted[4]).toBe(0x01); // version 1

    expect(key).toBeInstanceOf(Uint8Array);
    expect(key).toHaveLength(32);

    // Parse the binary package back
    const parsed = await parseBinaryPackage(encrypted, key);

    expect(parsed.metadata.qubeId).toBe(qubeId);
    expect(parsed.metadata.qubeName).toBe('IntegrationTestQube');
    expect(parsed.metadata.merkleRoot).toBe(merkleRoot);
    expect(parsed.metadata.chainLength).toBe(4);
    expect(parsed.metadata.hasNft).toBe(false);
    expect(parsed.genesisBlock.qube_id).toBe(qubeId);
    expect(parsed.genesisBlock.block_hash).toBe(genesisBlock.blockHash);
    expect(parsed.memoryBlocks).toHaveLength(3);

    // Verify integrity: Merkle root computed from block hashes must match stored root
    expect(verifyPackageIntegrity(parsed)).toBe(true);

    // Tamper-detection: change a block hash and verify integrity fails
    const tamperedData: QubePackageData = {
      ...parsed,
      metadata: { ...parsed.metadata, merkleRoot: '0'.repeat(64) },
    };
    expect(verifyPackageIntegrity(tamperedData)).toBe(false);

    // Wrong decryption key must throw
    const wrongKey = globalThis.crypto.getRandomValues(new Uint8Array(32));
    await expect(parseBinaryPackage(encrypted, wrongKey)).rejects.toThrow();

    // Create with a specific key (deterministic)
    const specificKey = masterKey;
    const { encrypted: enc2 } = await createBinaryPackage(packageData, specificKey);
    const parsed2 = await parseBinaryPackage(enc2, specificKey);
    expect(verifyPackageIntegrity(parsed2)).toBe(true);
  });

  // ── Step 12: ZIP .qube file create / parse / verify ──────────────────────

  it('creates, parses, and verifies integrity of a ZIP .qube file', async () => {
    const packageData: QubePackageData = {
      metadata: {
        qubeId,
        qubeName: 'IntegrationTestQube',
        publicKey: qubePublicKeyHex,
        chainLength: 4,
        merkleRoot,
        packageVersion: '1.0',
        packagedAt: Math.floor(Date.now() / 1000),
        packagedBy: 'test-user-001',
        hasNft: false,
      },
      genesisBlock: genesisBlock.toDict(),
      memoryBlocks: memoryBlocks.map((b) => b.toDict()),
      chainState,
    };

    const zipBytes = await createQubeFile(packageData, TEST_PASSWORD);

    // ZIP files start with PK signature 0x50 0x4B
    expect(zipBytes).toBeInstanceOf(Uint8Array);
    expect(zipBytes.length).toBeGreaterThan(100);
    expect(zipBytes[0]).toBe(0x50); // 'P'
    expect(zipBytes[1]).toBe(0x4b); // 'K'

    // Parse with correct password
    const parsed = await parseQubeFile(zipBytes, TEST_PASSWORD);

    expect(parsed.metadata.qubeId).toBe(qubeId);
    expect(parsed.metadata.qubeName).toBe('IntegrationTestQube');
    expect(parsed.metadata.merkleRoot).toBe(merkleRoot);
    expect(parsed.genesisBlock.block_hash).toBe(genesisBlock.blockHash);
    expect(parsed.memoryBlocks).toHaveLength(3);

    // Integrity must pass
    expect(verifyPackageIntegrity(parsed)).toBe(true);

    // Wrong password must throw
    await expect(parseQubeFile(zipBytes, 'wrong-password')).rejects.toThrow();
  });

  // ── Step 13: BCMR metadata generation ────────────────────────────────────

  it('generates valid BCMR v2 metadata with the correct schema, structure, and Qube ID in attributes', () => {
    // Use genesis block hash as the categoryId for the test
    const categoryId = genesisBlock.blockHash!;
    const genesisDict = genesisBlock.toDict();

    const bcmr = generateBcmrMetadata({
      categoryId,
      qubeName: 'IntegrationTestQube',
      qubeId,
      description: 'A sovereign AI agent created for SDK integration testing.',
      genesisBlockHash: genesisBlock.blockHash!,
      creator: 'test-user-001',
      birthTimestamp: genesisDict.birth_timestamp as number,
      aiModel: 'claude-opus-4-6',
      blockCount: 4,
    });

    // Schema must be the official BCMR v2 schema URI
    expect(bcmr.$schema).toBe('https://cashtokens.org/bcmr-v2.schema.json');

    // Version must be v1.0.0
    expect(bcmr.version).toEqual({ major: 1, minor: 0, patch: 0 });

    // latestRevision must be an ISO 8601 timestamp
    expect(bcmr.latestRevision).toMatch(/^\d{4}-\d{2}-\d{2}T/);

    // Registry identity must be Qubes Network
    expect(bcmr.registryIdentity.name).toBe('Qubes Network');
    expect(bcmr.registryIdentity.uris.web).toBe('https://qube.cash');

    // Identities must be keyed by categoryId
    expect(bcmr.identities).toHaveProperty(categoryId);

    // The identity snapshot must exist under the revision timestamp
    const revisions = bcmr.identities[categoryId];
    expect(Object.keys(revisions)).toHaveLength(1);

    const snapshot = Object.values(revisions)[0];
    expect(snapshot.name).toBe('IntegrationTestQube');
    expect(snapshot.description).toContain('integration testing');
    expect(snapshot.token.category).toBe(categoryId);
    expect(snapshot.token.symbol).toBe('QUBE');
    expect(snapshot.token.decimals).toBe(0);

    // The Qube page URI must contain the qubeId
    expect(snapshot.uris.web).toContain(qubeId);

    // Extensions must have attributes array containing the Qube ID
    const attributes = snapshot.extensions?.attributes;
    expect(Array.isArray(attributes)).toBe(true);

    const qubeIdAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'Qube ID',
    );
    expect(qubeIdAttr).toBeDefined();
    expect(qubeIdAttr?.value).toBe(qubeId);

    // Additional expected attributes
    const genesisHashAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'Genesis Block Hash',
    );
    expect(genesisHashAttr?.value).toBe(genesisBlock.blockHash);

    const creatorAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'Creator',
    );
    expect(creatorAttr?.value).toBe('test-user-001');

    const aiModelAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'AI Model',
    );
    expect(aiModelAttr?.value).toBe('claude-opus-4-6');

    const blockCountAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'Memory Blocks',
    );
    expect(blockCountAttr?.value).toBe('4');

    // Home Blockchain attribute must be present
    const homeBlockchainAttr = (attributes as Array<{ traitType: string; value: unknown }>).find(
      (a) => a.traitType === 'Home Blockchain',
    );
    expect(homeBlockchainAttr?.value).toBe('Bitcoin Cash');

    // Description must be truncated at 500 characters
    const longDescription = 'x'.repeat(600);
    const truncatedBcmr = generateBcmrMetadata({
      categoryId,
      qubeName: 'TruncTest',
      qubeId,
      description: longDescription,
    });
    const truncatedSnapshot = Object.values(truncatedBcmr.identities[categoryId])[0];
    expect(truncatedSnapshot.description.length).toBeLessThanOrEqual(500);
  });

  // ── Step 14: Per-block HKDF key derivation and AES encryption round-trip ──

  it('derives unique HKDF block keys and performs AES encryption round-trip for each memory block', async () => {
    for (const block of memoryBlocks) {
      const blockNumber = block.blockNumber;
      const blockKey = deriveBlockKey(masterKey, blockNumber);

      // Each key must be 32 bytes
      expect(blockKey).toBeInstanceOf(Uint8Array);
      expect(blockKey).toHaveLength(32);

      // Block keys must differ from the master key and from each other
      expect(blockKey).not.toEqual(masterKey);

      // Encrypt the block dict
      const blockDict = block.toDict();
      const encrypted = await encryptBlockData(blockDict, blockKey);

      expect(encrypted.algorithm).toBe('AES-256-GCM');
      expect(encrypted.nonce).toMatch(/^[0-9a-f]{24}$/);
      expect(encrypted.ciphertext.length).toBeGreaterThan(0);

      // Decrypt and verify round-trip
      const decrypted = await decryptBlockData(encrypted, blockKey);

      expect(decrypted.block_type).toBe(blockDict.block_type);
      expect(decrypted.block_number).toBe(blockDict.block_number);
      expect(decrypted.qube_id).toBe(qubeId);
      expect(decrypted.block_hash).toBe(blockDict.block_hash);
      expect(decrypted.encrypted).toBe(true);

      // Content must round-trip faithfully
      expect(decrypted.content).toEqual(blockDict.content);

      // Wrong key must throw
      const wrongKey = deriveBlockKey(masterKey, blockNumber + 100);
      await expect(decryptBlockData(encrypted, wrongKey)).rejects.toThrow();
    }

    // Verify that block keys for different block numbers are distinct
    const key1 = deriveBlockKey(masterKey, 1);
    const key2 = deriveBlockKey(masterKey, 2);
    const key3 = deriveBlockKey(masterKey, 3);

    expect(key1).not.toEqual(key2);
    expect(key2).not.toEqual(key3);
    expect(key1).not.toEqual(key3);

    // Chain state key must also differ from all block keys (domain separation)
    const chainStateKey = deriveChainStateKey(masterKey);
    expect(chainStateKey).not.toEqual(key1);
    expect(chainStateKey).not.toEqual(key2);
    expect(chainStateKey).not.toEqual(key3);
  });
});
