/**
 * Cryptographic primitives for the Qubes protocol.
 *
 * Re-exports all crypto sub-modules for convenient access:
 *
 * ```ts
 * import { generateKeyPair, signBlock, eciesEncrypt } from '@qubesai/sdk/crypto';
 * ```
 *
 * @module crypto
 */

// AES-256-GCM encryption
export {
  encryptBlockData,
  decryptBlockData,
  encryptBytes,
  decryptBytes,
} from './aes.js';

// HKDF-SHA256 key derivation
export { deriveBlockKey, deriveChainStateKey } from './hkdf.js';

// PBKDF2-SHA256 master key derivation
export {
  deriveMasterKey,
  deriveMasterKeyBase64,
  DEFAULT_ITERATIONS,
} from './pbkdf2.js';

// ECDSA secp256k1 key management
export {
  generateKeyPair,
  getPublicKey,
  serializePublicKey,
  deserializePublicKey,
  privateKeyToHex,
  privateKeyFromHex,
} from './keys.js';

// Qube identity derivation
export { deriveCommitment, deriveQubeId } from './identity.js';

// Block signing & verification
export {
  hashBlock,
  signBlock,
  verifyBlockSignature,
  signMessage,
  verifyMessage,
} from './signing.js';

// Merkle tree
export {
  computeMerkleRoot,
  verifyMerkleProof,
  type MerkleProofStep,
} from './merkle.js';

// ECIES asymmetric encryption
export { eciesEncrypt, eciesDecrypt } from './ecies.js';
