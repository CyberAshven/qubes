/**
 * Tests for bcmr/registry — platform-level BCMR registry management.
 */
import { describe, it, expect } from 'vitest';
import {
  createRegistry,
  addQubeToRegistry,
  removeQubeFromRegistry,
} from '../../src/bcmr/registry.js';
import type { BCMRMetadata } from '../../src/types/bcmr.js';
import type { QubeRegistryEntry } from '../../src/bcmr/registry.js';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const CATEGORY_ID = 'a'.repeat(64);

const QUBE_ALPHA: QubeRegistryEntry = {
  qubeId: 'ALPHA001',
  qubeName: 'AlphaQube',
  description: 'The first test qube.',
  avatarIpfsCid: 'QmAlphaCid',
  genesisBlockHash: 'b'.repeat(64),
  creator: 'user_001',
  birthTimestamp: 1700000000,
  aiModel: 'claude-opus-4-6',
  blockCount: 10,
};

const QUBE_BETA: QubeRegistryEntry = {
  qubeId: 'BETA0002',
  qubeName: 'BetaQube',
  description: 'The second test qube.',
  genesisBlockHash: 'c'.repeat(64),
};

const QUBE_GAMMA: QubeRegistryEntry = {
  qubeId: 'GAMMA003',
  qubeName: 'GammaQube',
};

// ---------------------------------------------------------------------------
// createRegistry
// ---------------------------------------------------------------------------

describe('createRegistry', () => {
  it('returns a valid BCMR structure with required top-level fields', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);

    expect(registry.$schema).toBe('https://cashtokens.org/bcmr-v2.schema.json');
    expect(registry.version).toEqual({ major: 1, minor: 0, patch: 0 });
    expect(typeof registry.latestRevision).toBe('string');
    expect(registry.latestRevision).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(registry.registryIdentity).toBeDefined();
    expect(registry.identities).toBeDefined();
  });

  it('sets registryIdentity to Qubes Network publisher', () => {
    const registry = createRegistry(CATEGORY_ID, []);

    expect(registry.registryIdentity.name).toBe('Qubes Network');
    expect(registry.registryIdentity.description).toBe('Sovereign AI Agent NFT Registry');
    expect(registry.registryIdentity.uris.web).toBe('https://qube.cash');
  });

  it('keys the identity map by categoryId', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);

    expect(Object.keys(registry.identities)).toContain(CATEGORY_ID);
  });

  it('latestRevision key is present in the identity revision map', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const revisions = registry.identities[CATEGORY_ID];

    expect(Object.keys(revisions)).toContain(registry.latestRevision);
  });

  it('creates an entry in nfts.parse.types for each provided qube', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const types = snapshot.nfts?.parse.types;

    expect(types).toBeDefined();
    expect(Object.keys(types!)).toContain(QUBE_ALPHA.qubeId);
    expect(Object.keys(types!)).toContain(QUBE_BETA.qubeId);
  });

  it('creates an empty nfts.parse.types map when given an empty qubes array', () => {
    const registry = createRegistry(CATEGORY_ID, []);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const types = snapshot.nfts?.parse.types;

    expect(types).toBeDefined();
    expect(Object.keys(types!)).toHaveLength(0);
  });

  it('each qube entry contains the Qube ID attribute', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry).toBeDefined();
    expect(entry?.extensions.attributes['Qube ID']).toBe(QUBE_ALPHA.qubeId);
  });

  it('each qube entry contains Home Blockchain attribute set to "Bitcoin Cash"', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['Home Blockchain']).toBe('Bitcoin Cash');
  });

  it('each qube entry contains Genesis Block Hash when provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['Genesis Block Hash']).toBe(QUBE_ALPHA.genesisBlockHash);
  });

  it('omits Genesis Block Hash attribute when not provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_GAMMA.qubeId];

    expect(entry?.extensions.attributes).not.toHaveProperty('Genesis Block Hash');
  });

  it('each qube entry contains Creator when provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['Creator']).toBe(QUBE_ALPHA.creator);
  });

  it('omits Creator attribute when not provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_GAMMA.qubeId];

    expect(entry?.extensions.attributes).not.toHaveProperty('Creator');
  });

  it('each qube entry contains AI Model when provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['AI Model']).toBe(QUBE_ALPHA.aiModel);
  });

  it('omits AI Model attribute when not provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_GAMMA.qubeId];

    expect(entry?.extensions.attributes).not.toHaveProperty('AI Model');
  });

  it('each qube entry contains Birth Date when birthTimestamp is provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['Birth Date']).toBe(String(QUBE_ALPHA.birthTimestamp));
  });

  it('each qube entry contains Memory Blocks when blockCount is provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.extensions.attributes['Memory Blocks']).toBe(String(QUBE_ALPHA.blockCount));
  });

  it('each qube entry uses the provided description', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.description).toBe(QUBE_ALPHA.description);
  });

  it('falls back to default description when description is not provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_GAMMA.qubeId];

    expect(entry?.description).toBe(`Sovereign AI agent ${QUBE_GAMMA.qubeName}`);
  });

  it('truncates description to 500 characters', () => {
    const longDescQube: QubeRegistryEntry = {
      qubeId: 'LONGDESC',
      qubeName: 'LongDescQube',
      description: 'z'.repeat(600),
    };
    const registry = createRegistry(CATEGORY_ID, [longDescQube]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[longDescQube.qubeId];

    expect(entry?.description).toHaveLength(500);
  });

  it('sets the web uri to the qube page for each entry', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];

    expect(entry?.uris.web).toBe(`https://qube.cash/qube/${QUBE_ALPHA.qubeId}`);
  });

  it('sets icon and image uris from avatarIpfsCid when provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_ALPHA.qubeId];
    const expectedUri = `ipfs://${QUBE_ALPHA.avatarIpfsCid}`;

    expect(entry?.uris.icon).toBe(expectedUri);
    expect(entry?.uris.image).toBe(expectedUri);
  });

  it('sets icon and image uris to empty string when avatarIpfsCid is not provided', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const entry = snapshot.nfts?.parse.types[QUBE_GAMMA.qubeId];

    expect(entry?.uris.icon).toBe('');
    expect(entry?.uris.image).toBe('');
  });

  it('collection snapshot has name "Qubes" and token symbol "QUBE"', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];

    expect(snapshot.name).toBe('Qubes');
    expect(snapshot.token.symbol).toBe('QUBE');
    expect(snapshot.token.decimals).toBe(0);
  });

  it('collection snapshot token category matches the provided categoryId', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];

    expect(snapshot.token.category).toBe(CATEGORY_ID);
  });

  it('handles multiple qubes with all entries keyed correctly', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA, QUBE_GAMMA]);
    const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
    const types = snapshot.nfts?.parse.types!;

    expect(Object.keys(types)).toHaveLength(3);
    expect(types[QUBE_ALPHA.qubeId].name).toBe(QUBE_ALPHA.qubeName);
    expect(types[QUBE_BETA.qubeId].name).toBe(QUBE_BETA.qubeName);
    expect(types[QUBE_GAMMA.qubeId].name).toBe(QUBE_GAMMA.qubeName);
  });
});

// ---------------------------------------------------------------------------
// addQubeToRegistry
// ---------------------------------------------------------------------------

/**
 * Build a registry with a fixed past latestRevision so that any subsequent
 * call to addQubeToRegistry / removeQubeFromRegistry always generates a
 * strictly later ISO timestamp — even when both calls land in the same ms.
 */
function makeRegistryWithPastRevision(qubes: QubeRegistryEntry[]): BCMRMetadata {
  const registry = createRegistry(CATEGORY_ID, qubes);
  const pastKey = '2000-01-01T00:00:00.000Z';
  const snapshot = registry.identities[CATEGORY_ID][registry.latestRevision];
  return {
    ...registry,
    latestRevision: pastKey,
    identities: {
      [CATEGORY_ID]: { [pastKey]: snapshot },
    },
  };
}

describe('addQubeToRegistry', () => {
  it('adds the new qube to nfts.parse.types', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);
    const snapshot = updated.identities[CATEGORY_ID][updated.latestRevision];
    const types = snapshot.nfts?.parse.types!;

    expect(types[QUBE_BETA.qubeId]).toBeDefined();
    expect(types[QUBE_BETA.qubeId].name).toBe(QUBE_BETA.qubeName);
  });

  it('preserves previously existing qubes', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);
    const snapshot = updated.identities[CATEGORY_ID][updated.latestRevision];
    const types = snapshot.nfts?.parse.types!;

    expect(types[QUBE_ALPHA.qubeId]).toBeDefined();
  });

  it('does not mutate the original registry', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const originalLatest = registry.latestRevision;
    const originalTypes = registry.identities[CATEGORY_ID][originalLatest].nfts?.parse.types!;

    addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);

    expect(originalTypes[QUBE_BETA.qubeId]).toBeUndefined();
    expect(registry.latestRevision).toBe(originalLatest);
  });

  it('updates latestRevision to a new timestamp', () => {
    // Use a past-pinned registry so nowIso() always produces a later key.
    const registry = makeRegistryWithPastRevision([QUBE_ALPHA]);
    const originalLatest = registry.latestRevision; // '2000-01-01T00:00:00.000Z'
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);

    expect(updated.latestRevision).not.toBe(originalLatest);
  });

  it('new qube is accessible via the updated latestRevision key', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;

    expect(latestTypes[QUBE_BETA.qubeId]).toBeDefined();
  });

  it('overwrites an existing qube entry with the same qubeId', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const updatedAlpha: QubeRegistryEntry = {
      ...QUBE_ALPHA,
      qubeName: 'AlphaQubeV2',
      blockCount: 99,
    };

    const updated = addQubeToRegistry(registry, CATEGORY_ID, updatedAlpha);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;

    expect(latestTypes[QUBE_ALPHA.qubeId].name).toBe('AlphaQubeV2');
    expect(latestTypes[QUBE_ALPHA.qubeId].extensions.attributes['Memory Blocks']).toBe('99');
  });

  it('adds correct attributes to the new qube entry', () => {
    const registry = createRegistry(CATEGORY_ID, []);
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_ALPHA);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;
    const attrs = latestTypes[QUBE_ALPHA.qubeId].extensions.attributes;

    expect(attrs['Qube ID']).toBe(QUBE_ALPHA.qubeId);
    expect(attrs['Home Blockchain']).toBe('Bitcoin Cash');
    expect(attrs['Creator']).toBe(QUBE_ALPHA.creator);
    expect(attrs['AI Model']).toBe(QUBE_ALPHA.aiModel);
  });

  it('preserves existing revisions for the category in identities', () => {
    // Pin to a past revision so addQubeToRegistry always produces a new key.
    const registry = makeRegistryWithPastRevision([QUBE_ALPHA]);
    const originalRevisionCount = Object.keys(registry.identities[CATEGORY_ID]).length;
    const updated = addQubeToRegistry(registry, CATEGORY_ID, QUBE_BETA);

    // There should be one more revision than before (original + new)
    expect(Object.keys(updated.identities[CATEGORY_ID]).length).toBe(originalRevisionCount + 1);
  });
});

// ---------------------------------------------------------------------------
// removeQubeFromRegistry
// ---------------------------------------------------------------------------

describe('removeQubeFromRegistry', () => {
  it('removes the specified qube from nfts.parse.types', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA]);
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;

    expect(latestTypes[QUBE_ALPHA.qubeId]).toBeUndefined();
  });

  it('retains all other qubes after removal', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA, QUBE_GAMMA]);
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;

    expect(latestTypes[QUBE_BETA.qubeId]).toBeDefined();
    expect(latestTypes[QUBE_GAMMA.qubeId]).toBeDefined();
  });

  it('does not mutate the original registry', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA]);
    const originalLatest = registry.latestRevision;
    const originalTypes = registry.identities[CATEGORY_ID][originalLatest].nfts?.parse.types!;

    removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);

    expect(originalTypes[QUBE_ALPHA.qubeId]).toBeDefined();
    expect(registry.latestRevision).toBe(originalLatest);
  });

  it('updates latestRevision to a new timestamp', () => {
    // Pin to a past revision so removeQubeFromRegistry always produces a later key.
    const registry = makeRegistryWithPastRevision([QUBE_ALPHA, QUBE_BETA]);
    const originalLatest = registry.latestRevision; // '2000-01-01T00:00:00.000Z'
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);

    expect(updated.latestRevision).not.toBe(originalLatest);
  });

  it('produces an empty types map when the only qube is removed', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;

    expect(Object.keys(latestTypes)).toHaveLength(0);
  });

  it('still returns a new registry when the qubeId does not exist in types', () => {
    // Pin to a past revision so the timestamp always changes.
    const registry = makeRegistryWithPastRevision([QUBE_ALPHA]);
    const originalLatest = registry.latestRevision; // '2000-01-01T00:00:00.000Z'
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, 'NONEXIST');

    // A new revision is always written, so latestRevision changes
    expect(updated.latestRevision).not.toBe(originalLatest);
    // The existing qube is untouched
    const latestTypes = updated.identities[CATEGORY_ID][updated.latestRevision].nfts?.parse.types!;
    expect(latestTypes[QUBE_ALPHA.qubeId]).toBeDefined();
  });

  it('preserves existing revisions in the category identities map', () => {
    // Pin to a past revision so a new key is always generated.
    const registry = makeRegistryWithPastRevision([QUBE_ALPHA, QUBE_BETA]);
    const originalRevisionCount = Object.keys(registry.identities[CATEGORY_ID]).length;
    const updated = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);

    expect(Object.keys(updated.identities[CATEGORY_ID]).length).toBe(originalRevisionCount + 1);
  });

  it('can remove qubes one by one until empty', () => {
    const registry = createRegistry(CATEGORY_ID, [QUBE_ALPHA, QUBE_BETA, QUBE_GAMMA]);
    const afterFirst = removeQubeFromRegistry(registry, CATEGORY_ID, QUBE_ALPHA.qubeId);
    const afterSecond = removeQubeFromRegistry(afterFirst, CATEGORY_ID, QUBE_BETA.qubeId);
    const afterThird = removeQubeFromRegistry(afterSecond, CATEGORY_ID, QUBE_GAMMA.qubeId);
    const finalTypes = afterThird.identities[CATEGORY_ID][afterThird.latestRevision].nfts?.parse.types!;

    expect(Object.keys(finalTypes)).toHaveLength(0);
  });

  it('round-trips add then remove cleanly', () => {
    const base = createRegistry(CATEGORY_ID, [QUBE_ALPHA]);
    const withBeta = addQubeToRegistry(base, CATEGORY_ID, QUBE_BETA);
    const withoutBeta = removeQubeFromRegistry(withBeta, CATEGORY_ID, QUBE_BETA.qubeId);
    const latestTypes = withoutBeta.identities[CATEGORY_ID][withoutBeta.latestRevision].nfts?.parse.types!;

    expect(latestTypes[QUBE_ALPHA.qubeId]).toBeDefined();
    expect(latestTypes[QUBE_BETA.qubeId]).toBeUndefined();
  });
});
