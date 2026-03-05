/**
 * BCMR (Bitcoin Cash Metadata Registry) types.
 *
 * Implements the CashTokens BCMR v2 specification for Qube NFT metadata.
 * See: https://cashtokens.org/docs/bcmr/chip/
 *
 * Ported from `blockchain/bcmr.py` and `blockchain/bcmr_registry.py`.
 *
 * @module types/bcmr
 */

// ---------------------------------------------------------------------------
// BCMR Version
// ---------------------------------------------------------------------------

/**
 * Semantic version triplet used in BCMR registries.
 */
export interface BCMRVersion {
  major: number;
  minor: number;
  patch: number;
}

// ---------------------------------------------------------------------------
// Registry Identity
// ---------------------------------------------------------------------------

/**
 * Identity of the registry publisher.
 *
 * Python equivalent: `registryIdentity` dict in `BCMRGenerator`.
 */
export interface RegistryIdentity {
  /** Publisher name (e.g. "Qubes Network"). */
  name: string;
  /** Publisher description. */
  description: string;
  /** Publisher URIs. */
  uris: {
    /** Website URL. */
    web: string;
    /** Registry URL. */
    registry?: string;
    /** Support URL. */
    support?: string;
  };
}

// ---------------------------------------------------------------------------
// Token Info
// ---------------------------------------------------------------------------

/**
 * Token metadata within an identity snapshot.
 */
export interface TokenInfo {
  /** CashToken category ID (64-char hex). */
  category: string;
  /** Token symbol (e.g. "QUBE"). */
  symbol: string;
  /** Decimal places (0 for NFTs). */
  decimals: number;
}

// ---------------------------------------------------------------------------
// NFT Attribute
// ---------------------------------------------------------------------------

/**
 * A single NFT attribute (trait) in the BCMR extensions.
 *
 * Python equivalent: attribute dicts in `BCMRGenerator._create_identity_snapshot()`.
 */
export interface NFTAttribute {
  /** Trait name (e.g. "Qube ID", "AI Model"). Python: `trait_type`. */
  traitType: string;
  /** Trait value. */
  value: string | number;
}

// ---------------------------------------------------------------------------
// Identity Snapshot
// ---------------------------------------------------------------------------

/**
 * A single revision snapshot for a CashToken identity.
 *
 * Each identity can have multiple snapshots keyed by ISO timestamp.
 *
 * Python equivalent: return value of `BCMRGenerator._create_identity_snapshot()`.
 */
export interface IdentitySnapshot {
  /** Display name. */
  name: string;
  /** Description text. */
  description: string;
  /** Token metadata. */
  token: TokenInfo;
  /** URIs for icon, image, web, and support. */
  uris: {
    /** IPFS URI for the icon (e.g. "ipfs://Qm..."). */
    icon?: string;
    /** IPFS URI for the image. */
    image?: string;
    /** Web URL. */
    web?: string;
    /** Support URL. */
    support?: string;
  };
  /** BCMR extensions (attributes, commitment data, chain sync). */
  extensions?: {
    /** Original commitment data before hashing. Python: `commitment_data`. */
    commitmentData?: Record<string, unknown>;
    /** NFT attributes / traits. */
    attributes?: NFTAttribute[] | Record<string, string>;
    /** Chain sync metadata for IPFS-backed storage. Python: `chain_sync`. */
    chainSync?: ChainSyncExtension;
    /** Additional extension fields. */
    [key: string]: unknown;
  };
  /** NFT type definitions (only in platform-level registries). */
  nfts?: {
    /** Description of the NFT collection. */
    description: string;
    /** Parsable NFT format with type definitions. */
    parse: {
      /** Map of commitment/qube_id -> NFT type entry. */
      types: Record<string, QubeNFTEntry>;
    };
  };
}

// ---------------------------------------------------------------------------
// Chain Sync Extension
// ---------------------------------------------------------------------------

/**
 * Chain sync metadata stored in BCMR extensions.
 *
 * This extension enables NFT-bundled IPFS storage: the BCMR points to
 * an encrypted Qube package on IPFS, and the symmetric key is ECIES-encrypted
 * so only the NFT holder can decrypt it.
 *
 * Python equivalent: `chain_sync` dict in `BCMRGenerator.update_chain_sync_metadata()`.
 */
export interface ChainSyncExtension {
  /** IPFS CID of the encrypted Qube package. Python: `ipfs_cid`. */
  ipfsCid: string;
  /** ECIES-encrypted symmetric key (hex). Only the NFT holder can decrypt. Python: `encrypted_key`. */
  encryptedKey: string;
  /** Key version number (incremented on transfer). Python: `key_version`. */
  keyVersion: number;
  /** Unix timestamp of the sync. Python: `sync_timestamp`. */
  syncTimestamp: number;
  /** Number of blocks in the chain at sync time. Python: `chain_length`. */
  chainLength: number;
  /** Merkle root for integrity verification. Python: `merkle_root`. */
  merkleRoot: string;
  /** Package format version. Python: `package_version`. */
  packageVersion: string;
  /** Password-wrapped key for Option A import (hex). Python: `password_wrapped_key`. */
  passwordWrappedKey?: string;
  /** Timestamp of last ownership transfer. Python: `transfer_timestamp`. */
  transferTimestamp?: number;
}

// ---------------------------------------------------------------------------
// Qube NFT Entry (for parsable registries)
// ---------------------------------------------------------------------------

/**
 * A single Qube's entry in the BCMR registry's `nfts.parse.types`.
 *
 * Used in the platform-level master registry that contains all minted Qubes.
 *
 * Python equivalent: return value of `BCMRRegistryManager._create_qube_entry()`.
 */
export interface QubeNFTEntry {
  /** Qube display name. */
  name: string;
  /** Qube description (truncated genesis prompt, max 500 chars). */
  description: string;
  /** URIs for icon, image, and web page. */
  uris: {
    /** IPFS URI for the Qube avatar icon. */
    icon: string;
    /** IPFS URI for the Qube avatar image. */
    image: string;
    /** Web URL for the Qube's page. */
    web: string;
  };
  /** Extension data including attributes. */
  extensions: {
    /** Qube attributes as key-value pairs. */
    attributes: Record<string, string>;
    /** Additional extension fields. */
    [key: string]: unknown;
  };
}

// ---------------------------------------------------------------------------
// Complete BCMR Metadata
// ---------------------------------------------------------------------------

/**
 * Complete BCMR metadata document (per-Qube level).
 *
 * This is the full BCMR JSON structure for a single Qube's NFT,
 * as generated by `BCMRGenerator.generate_bcmr_metadata()`.
 *
 * Conforms to the CashTokens BCMR v2 schema:
 * https://cashtokens.org/bcmr-v2.schema.json
 */
export interface BCMRMetadata {
  /** JSON schema URI. Python: `$schema`. */
  $schema: string;
  /** Registry version. */
  version: BCMRVersion;
  /** ISO timestamp of the latest revision. Python: `latestRevision`. */
  latestRevision: string;
  /** Registry publisher identity. Python: `registryIdentity`. */
  registryIdentity: RegistryIdentity;
  /**
   * Map of category_id -> (revision_timestamp -> identity_snapshot).
   *
   * Each category can have multiple revision snapshots keyed by ISO timestamp.
   */
  identities: Record<string, Record<string, IdentitySnapshot>>;
}

/**
 * Complete BCMR registry document (platform level).
 *
 * This is the master registry containing all minted Qubes under
 * a single platform category ID. Used for wallet integration
 * (Paytaca, Cashonize, Zapit).
 *
 * Python equivalent: return value of `BCMRRegistryManager.create_or_update_registry()`.
 */
export interface BCMRRegistry {
  /** JSON schema URI. */
  $schema: string;
  /** Registry version. */
  version: BCMRVersion;
  /** ISO timestamp of the latest revision. Python: `latestRevision`. */
  latestRevision: string;
  /** Registry publisher identity. Python: `registryIdentity`. */
  registryIdentity: RegistryIdentity;
  /**
   * Map of platform_category_id -> (revision_timestamp -> identity_snapshot).
   *
   * The identity snapshot at the platform level includes `nfts.parse.types`
   * containing all individual Qube entries.
   */
  identities: Record<string, Record<string, IdentitySnapshot>>;
}
