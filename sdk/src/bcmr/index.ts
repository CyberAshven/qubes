/**
 * BCMR module — Bitcoin Cash Metadata Registry generation and manipulation.
 *
 * Provides pure functions for generating per-Qube BCMR documents and
 * managing the platform-level master registry.
 *
 * No filesystem or network I/O — all functions operate on plain objects.
 *
 * @module bcmr
 */

export {
  generateBcmrMetadata,
  createIdentitySnapshot,
  addRevision,
  updateChainSyncMetadata,
  getChainSyncMetadata,
} from './generate.js';

export type {
  GenerateBcmrParams,
  IdentitySnapshotParams,
} from './generate.js';

export {
  createRegistry,
  addQubeToRegistry,
  removeQubeFromRegistry,
} from './registry.js';

export type { QubeRegistryEntry } from './registry.js';

// Re-export BCMR types for consumers that import from this module path.
export type {
  BCMRMetadata,
  BCMRRegistry,
  BCMRVersion,
  RegistryIdentity,
  TokenInfo,
  IdentitySnapshot,
  ChainSyncExtension,
  NFTAttribute,
  QubeNFTEntry,
} from '../types/bcmr.js';
