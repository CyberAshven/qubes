/**
 * Tests for bcmr/generate — per-Qube BCMR metadata generation.
 */
import { describe, it, expect } from 'vitest';
import {
  generateBcmrMetadata,
  createIdentitySnapshot,
  addRevision,
  updateChainSyncMetadata,
  getChainSyncMetadata,
} from '../../src/bcmr/generate.js';
import type { BCMRMetadata, ChainSyncExtension } from '../../src/types/bcmr.js';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const CATEGORY_ID = 'a'.repeat(64);
const QUBE_ID = 'ABCD1234';
const QUBE_NAME = 'TestQube';
const DESCRIPTION = 'A test sovereign AI agent.';

const MINIMAL_PARAMS = {
  categoryId: CATEGORY_ID,
  qubeName: QUBE_NAME,
  qubeId: QUBE_ID,
};

const FULL_PARAMS = {
  categoryId: CATEGORY_ID,
  qubeName: QUBE_NAME,
  qubeId: QUBE_ID,
  description: DESCRIPTION,
  genesisBlockHash: 'b'.repeat(64),
  creator: 'user_001',
  birthTimestamp: 1700000000,
  aiModel: 'claude-opus-4-6',
  blockCount: 42,
  avatarIpfsCid: 'QmTestCid1234567890',
  commitmentData: { key: 'value', nested: { num: 7 } },
};

// ---------------------------------------------------------------------------
// generateBcmrMetadata
// ---------------------------------------------------------------------------

describe('generateBcmrMetadata', () => {
  it('returns a valid BCMR v2 structure with required top-level fields', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);

    expect(meta.$schema).toBe('https://cashtokens.org/bcmr-v2.schema.json');
    expect(meta.version).toEqual({ major: 1, minor: 0, patch: 0 });
    expect(typeof meta.latestRevision).toBe('string');
    expect(meta.latestRevision).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(meta.registryIdentity).toBeDefined();
    expect(meta.identities).toBeDefined();
  });

  it('sets registryIdentity to Qubes Network publisher', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);

    expect(meta.registryIdentity.name).toBe('Qubes Network');
    expect(meta.registryIdentity.description).toBe('Sovereign AI Agent NFT Registry');
    expect(meta.registryIdentity.uris.web).toBe('https://qube.cash');
  });

  it('keys the identity map by categoryId', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);

    expect(Object.keys(meta.identities)).toContain(CATEGORY_ID);
  });

  it('latestRevision key is present in the identity revision map', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const revisions = meta.identities[CATEGORY_ID];

    expect(revisions).toBeDefined();
    expect(Object.keys(revisions)).toContain(meta.latestRevision);
  });

  it('snapshot contains the qube name', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.name).toBe(QUBE_NAME);
  });

  it('snapshot contains a description', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.description).toBe(DESCRIPTION);
  });

  it('snapshot token has symbol QUBE and decimals 0', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.token.symbol).toBe('QUBE');
    expect(snapshot.token.decimals).toBe(0);
  });

  it('snapshot token category matches the categoryId parameter', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.token.category).toBe(CATEGORY_ID);
  });

  it('populates avatar URI when avatarIpfsCid is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const expectedUri = `ipfs://${FULL_PARAMS.avatarIpfsCid}`;

    expect(snapshot.uris.icon).toBe(expectedUri);
    expect(snapshot.uris.image).toBe(expectedUri);
  });

  it('omits icon and image URIs when avatarIpfsCid is not provided', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.uris.icon).toBeUndefined();
    expect(snapshot.uris.image).toBeUndefined();
  });

  it('includes Qube ID attribute', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const qubeIdAttr = attrs?.find((a) => a.traitType === 'Qube ID');
    expect(qubeIdAttr).toBeDefined();
    expect(qubeIdAttr?.value).toBe(QUBE_ID);
  });

  it('includes Home Blockchain attribute with value "Bitcoin Cash"', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const homeAttr = attrs?.find((a) => a.traitType === 'Home Blockchain');
    expect(homeAttr).toBeDefined();
    expect(homeAttr?.value).toBe('Bitcoin Cash');
  });

  it('includes optional Creator attribute when creator is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const creatorAttr = attrs?.find((a) => a.traitType === 'Creator');
    expect(creatorAttr).toBeDefined();
    expect(creatorAttr?.value).toBe(FULL_PARAMS.creator);
  });

  it('excludes Creator attribute when creator is not provided', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const creatorAttr = attrs?.find((a) => a.traitType === 'Creator');
    expect(creatorAttr).toBeUndefined();
  });

  it('includes optional AI Model attribute when aiModel is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const aiAttr = attrs?.find((a) => a.traitType === 'AI Model');
    expect(aiAttr).toBeDefined();
    expect(aiAttr?.value).toBe(FULL_PARAMS.aiModel);
  });

  it('excludes AI Model attribute when aiModel is not provided', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const aiAttr = attrs?.find((a) => a.traitType === 'AI Model');
    expect(aiAttr).toBeUndefined();
  });

  it('includes optional Birth Date attribute when birthTimestamp is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const birthAttr = attrs?.find((a) => a.traitType === 'Birth Date');
    expect(birthAttr).toBeDefined();
    expect(birthAttr?.value).toBe(FULL_PARAMS.birthTimestamp);
  });

  it('includes optional Memory Blocks attribute when blockCount is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const blocksAttr = attrs?.find((a) => a.traitType === 'Memory Blocks');
    expect(blocksAttr).toBeDefined();
    expect(blocksAttr?.value).toBe(String(FULL_PARAMS.blockCount));
  });

  it('excludes Memory Blocks attribute when blockCount is not provided', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const blocksAttr = attrs?.find((a) => a.traitType === 'Memory Blocks');
    expect(blocksAttr).toBeUndefined();
  });

  it('includes optional Genesis Block Hash attribute when genesisBlockHash is provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    const genesisAttr = attrs?.find((a) => a.traitType === 'Genesis Block Hash');
    expect(genesisAttr).toBeDefined();
    expect(genesisAttr?.value).toBe(FULL_PARAMS.genesisBlockHash);
  });

  it('stores commitmentData in extensions when provided', () => {
    const meta = generateBcmrMetadata(FULL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.extensions?.commitmentData).toEqual(FULL_PARAMS.commitmentData);
  });

  it('omits commitmentData in extensions when not provided', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];

    expect(snapshot.extensions?.commitmentData).toBeUndefined();
  });

  it('does not mutate the DEFAULT_VERSION constant across calls', () => {
    const meta1 = generateBcmrMetadata(MINIMAL_PARAMS);
    const meta2 = generateBcmrMetadata({ ...MINIMAL_PARAMS, categoryId: 'c'.repeat(64) });

    meta1.version.major = 99;
    expect(meta2.version.major).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// createIdentitySnapshot
// ---------------------------------------------------------------------------

describe('createIdentitySnapshot', () => {
  it('returns a snapshot with the correct name', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.name).toBe(QUBE_NAME);
  });

  it('returns a snapshot with the provided description', () => {
    const snapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
      description: DESCRIPTION,
    });

    expect(snapshot.description).toBe(DESCRIPTION);
  });

  it('falls back to default description when description is not provided', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.description).toBe(`Sovereign AI agent ${QUBE_ID}`);
  });

  it('truncates description to 500 characters', () => {
    const longDescription = 'x'.repeat(600);
    const snapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
      description: longDescription,
    });

    expect(snapshot.description).toHaveLength(500);
    expect(snapshot.description).toBe('x'.repeat(500));
  });

  it('preserves a description that is exactly 500 characters', () => {
    const exactDescription = 'y'.repeat(500);
    const snapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
      description: exactDescription,
    });

    expect(snapshot.description).toHaveLength(500);
  });

  it('sets token.category to the provided categoryId', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.token.category).toBe(CATEGORY_ID);
  });

  it('sets token.symbol to QUBE', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.token.symbol).toBe('QUBE');
  });

  it('sets token.decimals to 0', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.token.decimals).toBe(0);
  });

  it('sets icon and image uris when avatarIpfsCid is provided', () => {
    const cid = 'QmAvatarCid';
    const snapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
      avatarIpfsCid: cid,
    });

    expect(snapshot.uris.icon).toBe(`ipfs://${cid}`);
    expect(snapshot.uris.image).toBe(`ipfs://${cid}`);
  });

  it('omits icon and image uris when avatarIpfsCid is not provided', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.uris.icon).toBeUndefined();
    expect(snapshot.uris.image).toBeUndefined();
  });

  it('sets the web uri to the qube page', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.uris.web).toBe(`https://qube.cash/qube/${QUBE_ID}`);
  });

  it('always includes Qube ID and Home Blockchain in attributes', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });
    const attrs = snapshot.extensions?.attributes as Array<{ traitType: string; value: unknown }>;

    expect(attrs?.some((a) => a.traitType === 'Qube ID' && a.value === QUBE_ID)).toBe(true);
    expect(attrs?.some((a) => a.traitType === 'Home Blockchain' && a.value === 'Bitcoin Cash')).toBe(true);
  });

  it('includes commitmentData extension when provided', () => {
    const commitmentData = { genesis: 'hash123', user: 'user_001' };
    const snapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
      commitmentData,
    });

    expect(snapshot.extensions?.commitmentData).toEqual(commitmentData);
  });

  it('omits commitmentData extension when not provided', () => {
    const snapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });

    expect(snapshot.extensions?.commitmentData).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// addRevision
// ---------------------------------------------------------------------------

/**
 * Build a BCMRMetadata document with a fixed past latestRevision so that any
 * subsequent call to addRevision / updateChainSyncMetadata will always generate
 * a strictly later ISO timestamp — even when both calls land in the same ms.
 */
function makeMetaWithPastRevision(): BCMRMetadata {
  const meta = generateBcmrMetadata(MINIMAL_PARAMS);
  const pastKey = '2000-01-01T00:00:00.000Z';
  // Move the single revision to the fixed past key so the real nowIso() call
  // inside addRevision / updateChainSyncMetadata always produces a newer key.
  const snapshot = meta.identities[CATEGORY_ID][meta.latestRevision];
  return {
    ...meta,
    latestRevision: pastKey,
    identities: {
      [CATEGORY_ID]: { [pastKey]: snapshot },
    },
  };
}

describe('addRevision', () => {
  it('adds a new revision entry under the given categoryId', () => {
    const original = makeMetaWithPastRevision();
    const newSnapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: 'UpdatedQube',
      qubeId: QUBE_ID,
      description: 'Updated description',
    });

    const updated = addRevision(original, CATEGORY_ID, newSnapshot);
    const revisions = updated.identities[CATEGORY_ID];

    expect(Object.keys(revisions)).toHaveLength(2);
  });

  it('updates latestRevision to a newer timestamp', () => {
    const original = makeMetaWithPastRevision();
    const originalLatest = original.latestRevision; // '2000-01-01T00:00:00.000Z'

    const newSnapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });
    const updated = addRevision(original, CATEGORY_ID, newSnapshot);

    expect(updated.latestRevision).not.toBe(originalLatest);
  });

  it('new revision snapshot is accessible via the updated latestRevision key', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const newSnapshot = createIdentitySnapshot({
      categoryId: CATEGORY_ID,
      qubeName: 'NewName',
      qubeId: QUBE_ID,
    });

    const updated = addRevision(original, CATEGORY_ID, newSnapshot);
    const latestSnapshot = updated.identities[CATEGORY_ID][updated.latestRevision];

    expect(latestSnapshot.name).toBe('NewName');
  });

  it('does not mutate the original metadata object', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const originalRevisionCount = Object.keys(original.identities[CATEGORY_ID]).length;
    const originalLatest = original.latestRevision;

    const newSnapshot = createIdentitySnapshot({ categoryId: CATEGORY_ID, qubeName: QUBE_NAME, qubeId: QUBE_ID });
    addRevision(original, CATEGORY_ID, newSnapshot);

    expect(Object.keys(original.identities[CATEGORY_ID])).toHaveLength(originalRevisionCount);
    expect(original.latestRevision).toBe(originalLatest);
  });

  it('creates a new category entry if the categoryId does not yet exist', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const differentCategory = 'd'.repeat(64);
    const newSnapshot = createIdentitySnapshot({
      categoryId: differentCategory,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
    });

    const updated = addRevision(original, differentCategory, newSnapshot);

    expect(updated.identities[differentCategory]).toBeDefined();
    expect(Object.keys(updated.identities[differentCategory])).toHaveLength(1);
  });

  it('preserves existing revisions for other categories', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const differentCategory = 'e'.repeat(64);
    const newSnapshot = createIdentitySnapshot({
      categoryId: differentCategory,
      qubeName: QUBE_NAME,
      qubeId: QUBE_ID,
    });

    const updated = addRevision(original, differentCategory, newSnapshot);

    expect(updated.identities[CATEGORY_ID]).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// updateChainSyncMetadata and getChainSyncMetadata
// ---------------------------------------------------------------------------

const SYNC_DATA: ChainSyncExtension = {
  ipfsCid: 'QmSyncCid0000000000000000000000000000000000000000',
  encryptedKey: 'deadbeef'.repeat(8),
  keyVersion: 1,
  syncTimestamp: 1700000000,
  chainLength: 10,
  merkleRoot: 'f'.repeat(64),
  packageVersion: '1.0',
};

describe('updateChainSyncMetadata', () => {
  it('returns a new metadata document with chain_sync in the latest revision', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const updated = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);
    const latestSnapshot = updated.identities[CATEGORY_ID][updated.latestRevision];

    expect(latestSnapshot.extensions?.chainSync).toEqual(SYNC_DATA);
  });

  it('updates latestRevision to a new timestamp', () => {
    const original = makeMetaWithPastRevision();
    const originalLatest = original.latestRevision; // '2000-01-01T00:00:00.000Z'
    const updated = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);

    expect(updated.latestRevision).not.toBe(originalLatest);
  });

  it('does not mutate the original metadata document', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const originalLatest = original.latestRevision;
    const originalRevisionCount = Object.keys(original.identities[CATEGORY_ID]).length;

    updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);

    expect(original.latestRevision).toBe(originalLatest);
    expect(Object.keys(original.identities[CATEGORY_ID])).toHaveLength(originalRevisionCount);
  });

  it('preserves base snapshot fields (name, token, description) in the new revision', () => {
    const original = generateBcmrMetadata(FULL_PARAMS);
    const updated = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);
    const latestSnapshot = updated.identities[CATEGORY_ID][updated.latestRevision];

    expect(latestSnapshot.name).toBe(QUBE_NAME);
    expect(latestSnapshot.token.symbol).toBe('QUBE');
    expect(latestSnapshot.description).toBe(DESCRIPTION);
  });

  it('creates a fallback snapshot if categoryId is not present in the registry', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const missingCategory = 'f'.repeat(64);
    const updated = updateChainSyncMetadata(original, missingCategory, SYNC_DATA);
    const latestSnapshot = updated.identities[missingCategory][updated.latestRevision];

    expect(latestSnapshot.extensions?.chainSync).toEqual(SYNC_DATA);
  });

  it('can overwrite an existing chain_sync entry with new sync data', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const first = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);
    const newSyncData: ChainSyncExtension = { ...SYNC_DATA, keyVersion: 2, chainLength: 20 };
    const second = updateChainSyncMetadata(first, CATEGORY_ID, newSyncData);
    const latestSnapshot = second.identities[CATEGORY_ID][second.latestRevision];

    expect(latestSnapshot.extensions?.chainSync?.keyVersion).toBe(2);
    expect(latestSnapshot.extensions?.chainSync?.chainLength).toBe(20);
  });
});

describe('getChainSyncMetadata', () => {
  it('returns the ChainSyncExtension after updateChainSyncMetadata', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const updated = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);

    const result = getChainSyncMetadata(updated, CATEGORY_ID);
    expect(result).toEqual(SYNC_DATA);
  });

  it('returns null when no chain_sync data exists on the snapshot', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);

    const result = getChainSyncMetadata(meta, CATEGORY_ID);
    expect(result).toBeNull();
  });

  it('returns null when the categoryId is not present in identities', () => {
    const meta = generateBcmrMetadata(MINIMAL_PARAMS);
    const missingCategory = '0'.repeat(64);

    const result = getChainSyncMetadata(meta, missingCategory);
    expect(result).toBeNull();
  });

  it('returns null when the latestRevision key does not match any revision', () => {
    const meta: BCMRMetadata = {
      $schema: 'https://cashtokens.org/bcmr-v2.schema.json',
      version: { major: 1, minor: 0, patch: 0 },
      latestRevision: '2099-01-01T00:00:00.000Z',
      registryIdentity: {
        name: 'Test',
        description: 'Test registry',
        uris: { web: 'https://example.com' },
      },
      identities: {
        [CATEGORY_ID]: {
          '2020-01-01T00:00:00.000Z': {
            name: 'Old',
            description: 'Old snapshot',
            token: { category: CATEGORY_ID, symbol: 'QUBE', decimals: 0 },
            uris: {},
          },
        },
      },
    };

    const result = getChainSyncMetadata(meta, CATEGORY_ID);
    expect(result).toBeNull();
  });

  it('returns the most recent chain_sync after multiple updates', () => {
    const original = generateBcmrMetadata(MINIMAL_PARAMS);
    const first = updateChainSyncMetadata(original, CATEGORY_ID, SYNC_DATA);
    const updatedSync: ChainSyncExtension = { ...SYNC_DATA, keyVersion: 5, chainLength: 100 };
    const second = updateChainSyncMetadata(first, CATEGORY_ID, updatedSync);

    const result = getChainSyncMetadata(second, CATEGORY_ID);
    expect(result?.keyVersion).toBe(5);
    expect(result?.chainLength).toBe(100);
  });
});
