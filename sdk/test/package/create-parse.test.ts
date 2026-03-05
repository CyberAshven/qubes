/**
 * Tests for package/create and package/parse — round-trip for both formats.
 *
 * Format A: Binary IPFS package  [4 magic][1 version][12 nonce][N ciphertext+tag]
 * Format B: .qube ZIP file       manifest.json (plain) + data.enc (AES-256-GCM)
 */
import { describe, it, expect } from 'vitest';
import { unzipSync } from 'fflate';
import {
  createBinaryPackage,
  createQubeFile,
  PACKAGE_MAGIC,
  PACKAGE_VERSION,
  NONCE_SIZE,
  KEY_SIZE,
} from '../../src/package/create.js';
import {
  parseBinaryPackage,
  parseQubeFile,
} from '../../src/package/parse.js';
import type { QubePackageData, QubeManifest } from '../../src/types/package.js';

// ---------------------------------------------------------------------------
// Test fixture
// ---------------------------------------------------------------------------

function makeTestPackageData(): QubePackageData {
  return {
    metadata: {
      qubeId: 'TEST1234',
      qubeName: 'Test Qube',
      publicKey: '03' + 'ab'.repeat(32),
      chainLength: 2,
      merkleRoot: 'deadbeef'.repeat(8),
      packageVersion: '1.0',
      packagedAt: 1700000000,
      packagedBy: 'test',
      hasNft: false,
    },
    genesisBlock: {
      block_number: 0,
      block_type: 'genesis',
      block_hash: 'aa'.repeat(32),
      content: { genesis_prompt: 'Hello' },
    },
    memoryBlocks: [
      {
        block_number: 1,
        block_type: 'thought',
        block_hash: 'bb'.repeat(32),
        content: { thought: 'test' },
      },
    ],
    chainState: { version: '2.0' },
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Produce a deterministic 32-byte key filled with a repeated byte value. */
function makeKey(fill: number): Uint8Array {
  return new Uint8Array(KEY_SIZE).fill(fill);
}

// ---------------------------------------------------------------------------
// Format A — Binary IPFS Package
// ---------------------------------------------------------------------------

describe('createBinaryPackage — header layout', () => {
  it('starts with QUBE magic bytes followed by version byte 0x01', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));

    // Magic: "QUBE" = 0x51 0x55 0x42 0x45
    expect(encrypted[0]).toBe(0x51);
    expect(encrypted[1]).toBe(0x55);
    expect(encrypted[2]).toBe(0x42);
    expect(encrypted[3]).toBe(0x45);

    // Version byte immediately after magic
    expect(encrypted[4]).toBe(PACKAGE_VERSION);
  });

  it('total length is 5 (header) + 12 (nonce) + ciphertext + 16 (GCM tag)', async () => {
    const data = makeTestPackageData();
    const plaintext = new TextEncoder().encode(JSON.stringify(data));
    const { encrypted } = await createBinaryPackage(data, makeKey(0x01));

    // header(5) + nonce(12) + plaintext + GCM-tag(16)
    const expectedLength = 5 + NONCE_SIZE + plaintext.length + 16;
    expect(encrypted.length).toBe(expectedLength);
  });

  it('nonce occupies bytes 5–16 (NONCE_SIZE = 12)', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));
    // The nonce slice must be 12 bytes — we just verify slice length here;
    // the round-trip test verifies it decrypts correctly.
    const nonce = encrypted.slice(5, 5 + NONCE_SIZE);
    expect(nonce.length).toBe(NONCE_SIZE);
  });

  it('returns the exact key that was passed in', async () => {
    const key = makeKey(0xaa);
    const { key: returnedKey } = await createBinaryPackage(makeTestPackageData(), key);
    expect(returnedKey).toEqual(key);
  });

  it('auto-generates a 32-byte random key when none is provided', async () => {
    const { key } = await createBinaryPackage(makeTestPackageData());
    expect(key).toHaveLength(KEY_SIZE);
  });

  it('produces different ciphertexts on repeated calls (random nonce)', async () => {
    const data = makeTestPackageData();
    const key = makeKey(0x01);
    const { encrypted: enc1 } = await createBinaryPackage(data, key);
    const { encrypted: enc2 } = await createBinaryPackage(data, key);
    // Nonces differ so the overall buffers must differ
    expect(enc1).not.toEqual(enc2);
  });
});

describe('parseBinaryPackage — round-trip with provided key', () => {
  it('decrypts back to the original data with a user-provided key', async () => {
    const original = makeTestPackageData();
    const key = makeKey(0x42);
    const { encrypted } = await createBinaryPackage(original, key);
    const parsed = await parseBinaryPackage(encrypted, key);

    expect(parsed.metadata.qubeId).toBe(original.metadata.qubeId);
    expect(parsed.metadata.qubeName).toBe(original.metadata.qubeName);
    expect(parsed.metadata.chainLength).toBe(original.metadata.chainLength);
    expect(parsed.metadata.merkleRoot).toBe(original.metadata.merkleRoot);
    expect(parsed.genesisBlock).toEqual(original.genesisBlock);
    expect(parsed.memoryBlocks).toEqual(original.memoryBlocks);
    expect(parsed.chainState).toEqual(original.chainState);
  });

  it('preserves all optional metadata fields through the round-trip', async () => {
    const original: QubePackageData = {
      ...makeTestPackageData(),
      relationships: { friends: ['AAAA0001'] },
      skills: { coding: 500 },
      skillHistory: [{ skill: 'coding', xp: 10, ts: 1700000001 }],
      avatarData: 'base64encodedimage==',
      avatarFilename: 'avatar.png',
      nftMetadata: { category_id: 'aabbcc', mint_txid: '1234' },
      bcmrData: { name: 'Test Qube', description: 'A test' },
      privateKeyHex: 'deadbeef'.repeat(8),
    };

    const key = makeKey(0x11);
    const { encrypted } = await createBinaryPackage(original, key);
    const parsed = await parseBinaryPackage(encrypted, key);

    expect(parsed.relationships).toEqual(original.relationships);
    expect(parsed.skills).toEqual(original.skills);
    expect(parsed.skillHistory).toEqual(original.skillHistory);
    expect(parsed.avatarData).toBe(original.avatarData);
    expect(parsed.avatarFilename).toBe(original.avatarFilename);
    expect(parsed.nftMetadata).toEqual(original.nftMetadata);
    expect(parsed.bcmrData).toEqual(original.bcmrData);
    expect(parsed.privateKeyHex).toBe(original.privateKeyHex);
  });
});

describe('parseBinaryPackage — round-trip with auto-generated key', () => {
  it('decrypts back to the original data using the returned key', async () => {
    const original = makeTestPackageData();
    const { encrypted, key } = await createBinaryPackage(original);
    const parsed = await parseBinaryPackage(encrypted, key);

    expect(parsed.metadata.qubeId).toBe(original.metadata.qubeId);
    expect(parsed.memoryBlocks).toEqual(original.memoryBlocks);
  });
});

describe('parseBinaryPackage — error cases', () => {
  it('rejects a wrong key with a decryption error', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));
    const wrongKey = makeKey(0xff);

    await expect(parseBinaryPackage(encrypted, wrongKey)).rejects.toThrow(
      /decrypt/i,
    );
  });

  it('rejects truncated data that is shorter than the minimum header', async () => {
    // Minimum header is 4 (magic) + 1 (version) + 12 (nonce) = 17 bytes
    const truncated = new Uint8Array(16).fill(0x00);

    await expect(parseBinaryPackage(truncated, makeKey(0x01))).rejects.toThrow(
      /too short/i,
    );
  });

  it('rejects an empty buffer', async () => {
    await expect(parseBinaryPackage(new Uint8Array(0), makeKey(0x01))).rejects.toThrow(
      /too short/i,
    );
  });

  it('rejects invalid magic bytes (wrong first byte)', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));
    // Corrupt the first magic byte
    const corrupted = new Uint8Array(encrypted);
    corrupted[0] = 0x00;

    await expect(parseBinaryPackage(corrupted, makeKey(0x01))).rejects.toThrow(
      /magic/i,
    );
  });

  it('rejects invalid magic bytes (wrong fourth byte)', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));
    const corrupted = new Uint8Array(encrypted);
    corrupted[3] = 0x46; // 'F' instead of 'E'

    await expect(parseBinaryPackage(corrupted, makeKey(0x01))).rejects.toThrow(
      /magic/i,
    );
  });

  it('rejects an unsupported version byte', async () => {
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), makeKey(0x01));
    const corrupted = new Uint8Array(encrypted);
    corrupted[4] = 0x99; // unsupported version

    await expect(parseBinaryPackage(corrupted, makeKey(0x01))).rejects.toThrow(
      /version/i,
    );
  });

  it('rejects data with valid header but corrupted ciphertext (wrong key)', async () => {
    const key = makeKey(0x01);
    const { encrypted } = await createBinaryPackage(makeTestPackageData(), key);
    const corrupted = new Uint8Array(encrypted);
    // Flip a bit deep in the ciphertext (after the 17-byte header)
    corrupted[20] ^= 0xff;

    await expect(parseBinaryPackage(corrupted, key)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Format B — .qube ZIP File
// ---------------------------------------------------------------------------

describe('createQubeFile — ZIP structure', () => {
  it('produces a valid ZIP that contains manifest.json and data.enc', async () => {
    const zipBytes = await createQubeFile(makeTestPackageData(), 'test-password');
    const files = unzipSync(zipBytes);

    expect(files['manifest.json']).toBeDefined();
    expect(files['data.enc']).toBeDefined();
  });

  it('manifest.json contains all required fields', async () => {
    const data = makeTestPackageData();
    const zipBytes = await createQubeFile(data, 'test-password');
    const files = unzipSync(zipBytes);

    const manifest: QubeManifest = JSON.parse(
      new TextDecoder().decode(files['manifest.json']),
    );

    expect(manifest.version).toBe('1.0');
    expect(manifest.qubeId).toBe(data.metadata.qubeId);
    expect(manifest.qubeName).toBe(data.metadata.qubeName);
    expect(manifest.blockCount).toBe(data.memoryBlocks.length);
    expect(manifest.hasNft).toBe(data.metadata.hasNft);
    expect(manifest.exportDate).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO 8601
    expect(manifest.salt).toMatch(/^[0-9a-f]{32}$/);  // 16 bytes = 32 hex chars
    expect(manifest.nonce).toMatch(/^[0-9a-f]{24}$/); // 12 bytes = 24 hex chars
  });

  it('manifest blockCount reflects the number of memory blocks', async () => {
    const data: QubePackageData = {
      ...makeTestPackageData(),
      memoryBlocks: [
        { block_number: 1, block_type: 'thought', block_hash: 'aa'.repeat(32), content: {} },
        { block_number: 2, block_type: 'thought', block_hash: 'bb'.repeat(32), content: {} },
        { block_number: 3, block_type: 'thought', block_hash: 'cc'.repeat(32), content: {} },
      ],
    };

    const zipBytes = await createQubeFile(data, 'pw');
    const files = unzipSync(zipBytes);
    const manifest: QubeManifest = JSON.parse(
      new TextDecoder().decode(files['manifest.json']),
    );

    expect(manifest.blockCount).toBe(3);
  });

  it('manifest hasNft is true when the Qube has an NFT', async () => {
    const data: QubePackageData = {
      ...makeTestPackageData(),
      metadata: { ...makeTestPackageData().metadata, hasNft: true, nftCategoryId: 'deadbeef' },
    };

    const zipBytes = await createQubeFile(data, 'pw');
    const files = unzipSync(zipBytes);
    const manifest: QubeManifest = JSON.parse(
      new TextDecoder().decode(files['manifest.json']),
    );

    expect(manifest.hasNft).toBe(true);
  });

  it('data.enc length equals ciphertext-only (no nonce prepended)', async () => {
    const data = makeTestPackageData();
    const plaintext = new TextEncoder().encode(JSON.stringify(data));
    const zipBytes = await createQubeFile(data, 'pw');
    const files = unzipSync(zipBytes);

    // data.enc = AES-GCM ciphertext + 16-byte tag (nonce is in manifest)
    const expectedEncSize = plaintext.length + 16;
    expect(files['data.enc'].length).toBe(expectedEncSize);
  });
});

describe('parseQubeFile — round-trip', () => {
  it('decrypts back to the original data with the correct password', async () => {
    const original = makeTestPackageData();
    const zipBytes = await createQubeFile(original, 'correct-password');
    const parsed = await parseQubeFile(zipBytes, 'correct-password');

    expect(parsed.metadata.qubeId).toBe(original.metadata.qubeId);
    expect(parsed.metadata.qubeName).toBe(original.metadata.qubeName);
    expect(parsed.metadata.chainLength).toBe(original.metadata.chainLength);
    expect(parsed.metadata.merkleRoot).toBe(original.metadata.merkleRoot);
    expect(parsed.genesisBlock).toEqual(original.genesisBlock);
    expect(parsed.memoryBlocks).toEqual(original.memoryBlocks);
    expect(parsed.chainState).toEqual(original.chainState);
  });

  it('preserves all optional fields through the ZIP round-trip', async () => {
    const original: QubePackageData = {
      ...makeTestPackageData(),
      relationships: { rivals: ['BBBB0002'] },
      skills: { art: 200 },
      avatarData: 'iVBORw0KGgoAAAANSUhEUgAA',
      avatarFilename: 'avatar.jpg',
      privateKeyHex: 'cafe'.repeat(16),
    };

    const zipBytes = await createQubeFile(original, 'secure123');
    const parsed = await parseQubeFile(zipBytes, 'secure123');

    expect(parsed.relationships).toEqual(original.relationships);
    expect(parsed.skills).toEqual(original.skills);
    expect(parsed.avatarData).toBe(original.avatarData);
    expect(parsed.avatarFilename).toBe(original.avatarFilename);
    expect(parsed.privateKeyHex).toBe(original.privateKeyHex);
  });
});

describe('parseQubeFile — error cases', () => {
  it('rejects a wrong password with a decryption error', async () => {
    const zipBytes = await createQubeFile(makeTestPackageData(), 'correct-password');

    await expect(parseQubeFile(zipBytes, 'wrong-password')).rejects.toThrow(
      /decrypt/i,
    );
  });

  it('rejects an empty password when the correct password is non-empty', async () => {
    const zipBytes = await createQubeFile(makeTestPackageData(), 'secret');

    await expect(parseQubeFile(zipBytes, '')).rejects.toThrow(/decrypt/i);
  });

  it('rejects non-ZIP data', async () => {
    const notAZip = new Uint8Array([0x00, 0x01, 0x02, 0x03, 0x04]);

    await expect(parseQubeFile(notAZip, 'pw')).rejects.toThrow(/unzip/i);
  });

  it('rejects a ZIP missing manifest.json', async () => {
    // Build a ZIP that only has data.enc
    const { zipSync } = await import('fflate');
    const badZip = zipSync({ 'data.enc': new Uint8Array([0xde, 0xad]) });

    await expect(parseQubeFile(badZip, 'pw')).rejects.toThrow(/manifest\.json/i);
  });

  it('rejects a ZIP missing data.enc', async () => {
    const { zipSync } = await import('fflate');
    const manifest: QubeManifest = {
      version: '1.0',
      qubeId: 'TEST1234',
      qubeName: 'Test',
      exportDate: new Date().toISOString(),
      blockCount: 0,
      hasNft: false,
      salt: 'aa'.repeat(16),
      nonce: 'bb'.repeat(12),
    };
    const badZip = zipSync({
      'manifest.json': new TextEncoder().encode(JSON.stringify(manifest)),
    });

    await expect(parseQubeFile(badZip, 'pw')).rejects.toThrow(/data\.enc/i);
  });

  it('rejects a manifest missing the salt field', async () => {
    const { zipSync } = await import('fflate');
    // Manifest with salt omitted
    const badManifest = {
      version: '1.0',
      qubeId: 'TEST1234',
      qubeName: 'Test',
      exportDate: new Date().toISOString(),
      blockCount: 0,
      hasNft: false,
      nonce: 'bb'.repeat(12),
      // salt intentionally missing
    };
    const badZip = zipSync({
      'manifest.json': new TextEncoder().encode(JSON.stringify(badManifest)),
      'data.enc': new Uint8Array([0xde, 0xad]),
    });

    await expect(parseQubeFile(badZip, 'pw')).rejects.toThrow(/"salt"/i);
  });

  it('rejects a manifest missing the nonce field', async () => {
    const { zipSync } = await import('fflate');
    const badManifest = {
      version: '1.0',
      qubeId: 'TEST1234',
      qubeName: 'Test',
      exportDate: new Date().toISOString(),
      blockCount: 0,
      hasNft: false,
      salt: 'aa'.repeat(16),
      // nonce intentionally missing
    };
    const badZip = zipSync({
      'manifest.json': new TextEncoder().encode(JSON.stringify(badManifest)),
      'data.enc': new Uint8Array([0xde, 0xad]),
    });

    await expect(parseQubeFile(badZip, 'pw')).rejects.toThrow(/"nonce"/i);
  });
});
