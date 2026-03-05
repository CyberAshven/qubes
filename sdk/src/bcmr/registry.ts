/**
 * Platform-level BCMR master registry management.
 *
 * All functions are pure — no filesystem or network I/O. They generate and
 * manipulate BCMR v2 registry structures that contain all minted Qubes under
 * a single platform category ID.
 *
 * Ported from `blockchain/bcmr_registry.py` (BCMRRegistryManager).
 *
 * @module bcmr/registry
 */

import type {
  BCMRMetadata,
  BCMRVersion,
  RegistryIdentity,
  IdentitySnapshot,
  QubeNFTEntry,
} from '../types/bcmr.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BCMR_SCHEMA = 'https://cashtokens.org/bcmr-v2.schema.json';

const DEFAULT_VERSION: BCMRVersion = { major: 1, minor: 0, patch: 0 };

const REGISTRY_IDENTITY: RegistryIdentity = {
  name: 'Qubes Network',
  description: 'Sovereign AI Agent NFT Registry',
  uris: {
    web: 'https://qube.cash',
    support: 'https://github.com/nicholasgasior/qubes',
  },
};

/** Platform-level collection description shown in parsable NFT registries. */
const COLLECTION_NAME = 'Qubes';
const COLLECTION_DESCRIPTION =
  'Sovereign AI Agents with cryptographic identity and persistent memory. Each Qube is a unique self-sovereign digital entity.';
const NFT_COLLECTION_DESCRIPTION =
  'Each Qube is a unique sovereign AI entity with its own personality, memory, and cryptographic identity. Qubes can form relationships, earn reputation, and participate in the decentralized AI economy.';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/**
 * Lightweight data record for a single Qube in the platform registry.
 *
 * Equivalent to the Qube instance attributes consumed by
 * `BCMRRegistryManager._create_qube_entry()` and `_extract_attributes()`.
 */
export interface QubeRegistryEntry {
  /** Short Qube ID (8-char hex, uppercase). */
  qubeId: string;
  /** Qube display name. */
  qubeName: string;
  /** Description text (≤500 chars). */
  description?: string;
  /** IPFS CID for the Qube avatar (without ipfs:// prefix). */
  avatarIpfsCid?: string;
  /** Hash of the genesis block. */
  genesisBlockHash?: string;
  /** Creator identifier. */
  creator?: string;
  /** Unix timestamp of birth. */
  birthTimestamp?: number;
  /** AI model name. */
  aiModel?: string;
  /** Number of memory blocks. */
  blockCount?: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return a new ISO 8601 UTC timestamp string. */
function nowIso(): string {
  return new Date().toISOString();
}

/**
 * Build a QubeNFTEntry for inclusion in `nfts.parse.types`.
 *
 * Equivalent to `BCMRRegistryManager._create_qube_entry()` combined with
 * `_extract_attributes()`.
 */
function buildQubeNFTEntry(qube: QubeRegistryEntry): QubeNFTEntry {
  const avatarUri = qube.avatarIpfsCid ? `ipfs://${qube.avatarIpfsCid}` : '';

  const description =
    qube.description !== undefined
      ? qube.description.slice(0, 500)
      : `Sovereign AI agent ${qube.qubeName}`;

  // Build flat key-value attribute map (registry format).
  const attributes: Record<string, string> = {
    'Qube ID': qube.qubeId,
    'Home Blockchain': 'Bitcoin Cash',
  };

  if (qube.genesisBlockHash !== undefined) {
    attributes['Genesis Block Hash'] = qube.genesisBlockHash;
  }
  if (qube.creator !== undefined) {
    attributes['Creator'] = qube.creator;
  }
  if (qube.birthTimestamp !== undefined) {
    attributes['Birth Date'] = String(qube.birthTimestamp);
  }
  if (qube.aiModel !== undefined) {
    attributes['AI Model'] = qube.aiModel;
  }
  if (qube.blockCount !== undefined) {
    attributes['Memory Blocks'] = String(qube.blockCount);
  }

  return {
    name: qube.qubeName,
    description,
    uris: {
      icon: avatarUri,
      image: avatarUri,
      web: `https://qube.cash/qube/${qube.qubeId}`,
    },
    extensions: {
      attributes,
    },
  };
}

/**
 * Build the platform-level identity snapshot that wraps all Qube entries.
 *
 * This snapshot lives at `identities[categoryId][timestamp]` and contains
 * the full `nfts.parse.types` map.
 */
function buildCollectionSnapshot(
  categoryId: string,
  nftTypes: Record<string, QubeNFTEntry>,
): IdentitySnapshot {
  return {
    name: COLLECTION_NAME,
    description: COLLECTION_DESCRIPTION,
    token: {
      category: categoryId,
      symbol: 'QUBE',
      decimals: 0,
    },
    uris: {
      icon: 'ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7',
      image: 'ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7',
      web: 'https://qube.cash',
      support: 'https://github.com/nicholasgasior/qubes',
    },
    nfts: {
      description: NFT_COLLECTION_DESCRIPTION,
      parse: {
        types: nftTypes,
      },
    },
  };
}

/**
 * Extract the `nfts.parse.types` map from the latest revision of a registry.
 *
 * Returns an empty object if the category or revision is missing.
 */
function extractNftTypes(
  registry: BCMRMetadata,
  categoryId: string,
): Record<string, QubeNFTEntry> {
  const revisions = registry.identities[categoryId];
  if (!revisions) return {};

  const latestKey = registry.latestRevision;
  const latestSnapshot = revisions[latestKey];
  if (!latestSnapshot) return {};

  return (latestSnapshot.nfts?.parse.types as Record<string, QubeNFTEntry>) ?? {};
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build a complete platform-level BCMR registry from a list of Qubes.
 *
 * Equivalent to `BCMRRegistryManager.create_or_update_registry()`.
 *
 * @param categoryId - Platform minting token category ID.
 * @param qubes - All Qubes to include in the registry.
 * @returns A complete BCMRMetadata document (usable as BCMRRegistry).
 */
export function createRegistry(
  categoryId: string,
  qubes: QubeRegistryEntry[],
): BCMRMetadata {
  const revisionTimestamp = nowIso();

  const nftTypes: Record<string, QubeNFTEntry> = {};
  for (const qube of qubes) {
    nftTypes[qube.qubeId] = buildQubeNFTEntry(qube);
  }

  const snapshot = buildCollectionSnapshot(categoryId, nftTypes);

  return {
    $schema: BCMR_SCHEMA,
    version: { ...DEFAULT_VERSION },
    latestRevision: revisionTimestamp,
    registryIdentity: { ...REGISTRY_IDENTITY, uris: { ...REGISTRY_IDENTITY.uris } },
    identities: {
      [categoryId]: {
        [revisionTimestamp]: snapshot,
      },
    },
  };
}

/**
 * Add a single Qube entry to an existing BCMR registry.
 *
 * Pure function — returns a new BCMRMetadata without mutating the input.
 * If the Qube ID already exists in parse.types, it is overwritten.
 *
 * Equivalent to `BCMRRegistryManager.add_qube_to_registry()`.
 *
 * @param registry - The current platform registry.
 * @param categoryId - The platform category ID.
 * @param qube - The Qube to add.
 * @returns Updated registry with the Qube included.
 */
export function addQubeToRegistry(
  registry: BCMRMetadata,
  categoryId: string,
  qube: QubeRegistryEntry,
): BCMRMetadata {
  const existingTypes = extractNftTypes(registry, categoryId);

  const updatedTypes: Record<string, QubeNFTEntry> = {
    ...existingTypes,
    [qube.qubeId]: buildQubeNFTEntry(qube),
  };

  const revisionTimestamp = nowIso();
  const snapshot = buildCollectionSnapshot(categoryId, updatedTypes);

  // Preserve any existing revisions for other categories.
  const existingRevisions = registry.identities[categoryId] ?? {};

  return {
    ...registry,
    latestRevision: revisionTimestamp,
    identities: {
      ...registry.identities,
      [categoryId]: {
        ...existingRevisions,
        [revisionTimestamp]: snapshot,
      },
    },
  };
}

/**
 * Remove a Qube from a BCMR registry by its Qube ID.
 *
 * Pure function — returns a new BCMRMetadata without mutating the input.
 * If the Qube ID is not found in parse.types the registry is returned
 * unchanged (latestRevision is still updated to reflect the operation
 * was attempted, consistent with the Python implementation).
 *
 * Equivalent to `BCMRRegistryManager.remove_qube_from_registry()`.
 *
 * @param registry - The current platform registry.
 * @param categoryId - The platform category ID.
 * @param qubeId - The Qube ID to remove (exact match against parse.types keys).
 * @returns Updated registry with the Qube removed.
 */
export function removeQubeFromRegistry(
  registry: BCMRMetadata,
  categoryId: string,
  qubeId: string,
): BCMRMetadata {
  const existingTypes = extractNftTypes(registry, categoryId);

  const updatedTypes: Record<string, QubeNFTEntry> = { ...existingTypes };
  delete updatedTypes[qubeId];

  const revisionTimestamp = nowIso();
  const snapshot = buildCollectionSnapshot(categoryId, updatedTypes);

  const existingRevisions = registry.identities[categoryId] ?? {};

  return {
    ...registry,
    latestRevision: revisionTimestamp,
    identities: {
      ...registry.identities,
      [categoryId]: {
        ...existingRevisions,
        [revisionTimestamp]: snapshot,
      },
    },
  };
}
