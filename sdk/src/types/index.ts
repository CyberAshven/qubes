/**
 * @qubesai/sdk type definitions.
 *
 * Re-exports all protocol types from their respective modules.
 *
 * @module types
 */

// Block types and content schemas
export {
  BlockType,
  type Block,
  type ParticipantSignature,
  type ThoughtContent,
  type ActionContent,
  type ObservationContent,
  type MessageContent,
  type DecisionContent,
  type MemoryAnchorContent,
  type CollaborativeMemoryContent,
  type SummaryContent,
  type GameContent,
  type LearningContent,
  type LearningType,
} from './block.js';

// Chain state types
export {
  type ChainStateV2,
  type ChainSection,
  type SessionSection,
  type SettingsSection,
  type RuntimeSection,
  type StatsSection,
  type BlockCountsSection,
  type SkillsSection,
  type SkillXpEntry,
  type SkillHistoryEntry,
  type RelationshipsSection,
  type RelationshipEntity,
  type FinancialSection,
  type WalletInfo,
  type TransactionsInfo,
  type TransactionEntry,
  type PendingTransactionEntry,
  type MoodSection,
  type MoodHistoryEntry,
  type OwnerInfoSection,
  type QubeProfileSection,
  type HealthSection,
  type AttestationSection,
} from './chain-state.js';

// Cryptographic types
export {
  type KeyPair,
  type CompressedPublicKey,
  type EncryptedData,
  type QubeIdentity,
} from './crypto.js';

// Covenant minting types
export {
  type MintResult,
  type WcMintResult,
  type MintError,
  type MintOutcome,
} from './covenant.js';

// Package types
export {
  type QubePackageMetadata,
  type QubePackageData,
  type QubeManifest,
} from './package.js';

// BCMR types
export {
  type BCMRVersion,
  type RegistryIdentity,
  type TokenInfo,
  type NFTAttribute,
  type IdentitySnapshot,
  type ChainSyncExtension,
  type QubeNFTEntry,
  type BCMRMetadata,
  type BCMRRegistry,
} from './bcmr.js';

// NFT metadata types
export {
  type NFTMetadata,
} from './nft.js';

// Storage adapter types
export {
  type UploadResult,
  type StorageAdapter,
} from './storage.js';
