/**
 * Per-Qube BCMR metadata generation.
 *
 * All functions are pure — no filesystem or network I/O. They generate and
 * manipulate BCMR v2 JSON structures that conform to the CashTokens spec.
 *
 * Ported from `blockchain/bcmr.py` (BCMRGenerator).
 *
 * @module bcmr/generate
 */

import type {
  BCMRMetadata,
  BCMRVersion,
  RegistryIdentity,
  IdentitySnapshot,
  ChainSyncExtension,
  NFTAttribute,
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

// ---------------------------------------------------------------------------
// Parameter types
// ---------------------------------------------------------------------------

/**
 * Parameters for generating a full BCMR metadata document.
 */
export interface GenerateBcmrParams {
  /** CashToken category ID (64-char hex). */
  categoryId: string;
  /** Qube display name. */
  qubeName: string;
  /** Short Qube ID (8-char hex, uppercase). */
  qubeId: string;
  /** Qube description (genesis prompt, ≤500 chars). */
  description?: string;
  /** Hash of the genesis block. */
  genesisBlockHash?: string;
  /** Creator identifier. */
  creator?: string;
  /** Unix timestamp of birth. */
  birthTimestamp?: number;
  /** AI model name (e.g. "claude-opus-4-6"). */
  aiModel?: string;
  /** Number of memory blocks in the chain. */
  blockCount?: number;
  /** IPFS CID for the Qube avatar (without ipfs:// prefix). */
  avatarIpfsCid?: string;
  /** Original commitment data before hashing. */
  commitmentData?: Record<string, unknown>;
}

/**
 * Parameters for building a single identity snapshot.
 *
 * Mirrors the fields consumed by `BCMRGenerator._create_identity_snapshot()`.
 */
export interface IdentitySnapshotParams {
  /** CashToken category ID. */
  categoryId: string;
  /** Qube display name. */
  qubeName: string;
  /** Short Qube ID. */
  qubeId: string;
  /** Description text (truncated to 500 chars if longer). */
  description?: string;
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
  /** IPFS CID for the avatar (without ipfs:// prefix). */
  avatarIpfsCid?: string;
  /** Original commitment data. */
  commitmentData?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return a new ISO 8601 UTC timestamp string. */
function nowIso(): string {
  return new Date().toISOString();
}

/**
 * Build the NFT attributes array from discrete Qube fields.
 *
 * Python equivalent: the `attributes` list constructed in
 * `BCMRGenerator._create_identity_snapshot()`.
 */
function buildAttributes(params: {
  qubeId: string;
  genesisBlockHash?: string;
  creator?: string;
  birthTimestamp?: number;
  aiModel?: string;
  blockCount?: number;
}): NFTAttribute[] {
  const attrs: NFTAttribute[] = [
    { traitType: 'Qube ID', value: params.qubeId },
    { traitType: 'Home Blockchain', value: 'Bitcoin Cash' },
  ];

  if (params.genesisBlockHash !== undefined) {
    attrs.push({ traitType: 'Genesis Block Hash', value: params.genesisBlockHash });
  }

  if (params.creator !== undefined) {
    attrs.push({ traitType: 'Creator', value: params.creator });
  }

  if (params.birthTimestamp !== undefined) {
    attrs.push({ traitType: 'Birth Date', value: params.birthTimestamp });
  }

  if (params.aiModel !== undefined) {
    attrs.push({ traitType: 'AI Model', value: params.aiModel });
  }

  if (params.blockCount !== undefined) {
    attrs.push({ traitType: 'Memory Blocks', value: String(params.blockCount) });
  }

  return attrs;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Generate a full BCMR v2 metadata document for a single Qube NFT.
 *
 * Equivalent to `BCMRGenerator.generate_bcmr_metadata()`.
 *
 * @param params - Qube identity and attribute data.
 * @returns A complete, schema-valid BCMRMetadata object.
 */
export function generateBcmrMetadata(params: GenerateBcmrParams): BCMRMetadata {
  const revisionTimestamp = nowIso();

  const snapshot = createIdentitySnapshot({
    categoryId: params.categoryId,
    qubeName: params.qubeName,
    qubeId: params.qubeId,
    description: params.description,
    genesisBlockHash: params.genesisBlockHash,
    creator: params.creator,
    birthTimestamp: params.birthTimestamp,
    aiModel: params.aiModel,
    blockCount: params.blockCount,
    avatarIpfsCid: params.avatarIpfsCid,
    commitmentData: params.commitmentData,
  });

  return {
    $schema: BCMR_SCHEMA,
    version: { ...DEFAULT_VERSION },
    latestRevision: revisionTimestamp,
    registryIdentity: { ...REGISTRY_IDENTITY, uris: { ...REGISTRY_IDENTITY.uris } },
    identities: {
      [params.categoryId]: {
        [revisionTimestamp]: snapshot,
      },
    },
  };
}

/**
 * Build a single identity snapshot for a BCMR revision.
 *
 * Equivalent to `BCMRGenerator._create_identity_snapshot()`.
 *
 * @param params - Snapshot parameters.
 * @returns A fully-formed IdentitySnapshot.
 */
export function createIdentitySnapshot(params: IdentitySnapshotParams): IdentitySnapshot {
  const description =
    params.description !== undefined
      ? params.description.slice(0, 500)
      : `Sovereign AI agent ${params.qubeId}`;

  const avatarUri =
    params.avatarIpfsCid ? `ipfs://${params.avatarIpfsCid}` : undefined;

  const attributes = buildAttributes({
    qubeId: params.qubeId,
    genesisBlockHash: params.genesisBlockHash,
    creator: params.creator,
    birthTimestamp: params.birthTimestamp,
    aiModel: params.aiModel,
    blockCount: params.blockCount,
  });

  const extensions: IdentitySnapshot['extensions'] = {
    attributes,
  };

  if (params.commitmentData !== undefined) {
    extensions.commitmentData = params.commitmentData;
  }

  return {
    name: params.qubeName,
    description,
    token: {
      category: params.categoryId,
      symbol: 'QUBE',
      decimals: 0,
    },
    uris: {
      ...(avatarUri !== undefined ? { icon: avatarUri, image: avatarUri } : {}),
      web: `https://qube.cash/qube/${params.qubeId}`,
      support: 'https://github.com/nicholasgasior/qubes',
    },
    extensions,
  };
}

/**
 * Add a new revision snapshot to an existing BCMR metadata document.
 *
 * Pure function — returns a new BCMRMetadata without mutating the input.
 *
 * Equivalent to the revision-adding logic in `BCMRGenerator.add_revision()`.
 *
 * @param existing - The current BCMRMetadata document.
 * @param categoryId - The category ID under which to add the revision.
 * @param snapshot - The new IdentitySnapshot to record.
 * @returns Updated BCMRMetadata with the new revision appended.
 */
export function addRevision(
  existing: BCMRMetadata,
  categoryId: string,
  snapshot: IdentitySnapshot,
): BCMRMetadata {
  const revisionTimestamp = nowIso();

  const currentIdentityRevisions =
    existing.identities[categoryId] ?? {};

  return {
    ...existing,
    latestRevision: revisionTimestamp,
    identities: {
      ...existing.identities,
      [categoryId]: {
        ...currentIdentityRevisions,
        [revisionTimestamp]: snapshot,
      },
    },
  };
}

/**
 * Add or update the `chain_sync` extension within the latest revision of a
 * BCMR metadata document.
 *
 * Creates a new revision snapshot so that the full history is preserved.
 * Pure function — does not mutate `existing`.
 *
 * Equivalent to `BCMRGenerator.update_chain_sync_metadata()`.
 *
 * @param existing - Current BCMRMetadata document.
 * @param categoryId - Category ID to update.
 * @param syncData - Chain sync extension data.
 * @returns Updated BCMRMetadata with new revision containing chain_sync.
 */
export function updateChainSyncMetadata(
  existing: BCMRMetadata,
  categoryId: string,
  syncData: ChainSyncExtension,
): BCMRMetadata {
  const revisionTimestamp = nowIso();

  // Locate latest revision snapshot to copy its base fields.
  const currentRevisions = existing.identities[categoryId] ?? {};
  const latestKey = existing.latestRevision;
  const latestSnapshot: IdentitySnapshot = currentRevisions[latestKey] ?? {
    name: 'Qube',
    description: 'Sovereign AI Agent',
    token: {
      category: categoryId,
      symbol: 'QUBE',
      decimals: 0,
    },
    uris: {},
  };

  const newSnapshot: IdentitySnapshot = {
    ...latestSnapshot,
    extensions: {
      ...latestSnapshot.extensions,
      chainSync: syncData,
    },
  };

  return {
    ...existing,
    latestRevision: revisionTimestamp,
    identities: {
      ...existing.identities,
      [categoryId]: {
        ...currentRevisions,
        [revisionTimestamp]: newSnapshot,
      },
    },
  };
}

/**
 * Extract the `chain_sync` extension from the latest revision of a BCMR
 * metadata document.
 *
 * Equivalent to `BCMRGenerator.get_chain_sync_metadata()`.
 *
 * @param metadata - The BCMRMetadata document to inspect.
 * @param categoryId - The category ID to look up.
 * @returns The ChainSyncExtension if present, or null.
 */
export function getChainSyncMetadata(
  metadata: BCMRMetadata,
  categoryId: string,
): ChainSyncExtension | null {
  const revisions = metadata.identities[categoryId];
  if (!revisions) return null;

  const latestKey = metadata.latestRevision;
  const latestSnapshot = revisions[latestKey];
  if (!latestSnapshot) return null;

  return latestSnapshot.extensions?.chainSync ?? null;
}
