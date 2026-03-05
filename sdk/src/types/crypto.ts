/**
 * Cryptographic types for the Qubes protocol.
 *
 * Qubes uses ECDSA secp256k1 for identity, AES-256-GCM for encryption,
 * HKDF-SHA256 for key derivation, and PBKDF2-SHA256 for master key derivation.
 *
 * @module types/crypto
 */

// ---------------------------------------------------------------------------
// Key Types
// ---------------------------------------------------------------------------

/**
 * An ECDSA secp256k1 key pair.
 *
 * The private key is 32 bytes; the public key is 33 bytes (compressed).
 */
export interface KeyPair {
  /** 32-byte private key. */
  privateKey: Uint8Array;
  /** 33-byte compressed public key. */
  publicKey: Uint8Array;
}

/**
 * A 66-character hex-encoded compressed secp256k1 public key.
 *
 * Format: starts with `02` or `03` followed by 64 hex characters.
 */
export type CompressedPublicKey = string;

// ---------------------------------------------------------------------------
// Encryption Types
// ---------------------------------------------------------------------------

/**
 * Result of AES-256-GCM encryption.
 *
 * Python equivalent: output of `crypto.encryption.encrypt_block_data()`.
 */
export interface EncryptedData {
  /** Hex-encoded ciphertext (includes GCM auth tag). */
  ciphertext: string;
  /** Hex-encoded 12-byte nonce / initialization vector. */
  nonce: string;
  /** Encryption algorithm identifier. */
  algorithm: 'AES-256-GCM';
}

// ---------------------------------------------------------------------------
// Identity Types
// ---------------------------------------------------------------------------

/**
 * A Qube's cryptographic identity.
 *
 * The Qube ID is derived deterministically from the public key:
 *   `qubeId = SHA256(compressedPublicKey).slice(0, 4).toUpperCase()`
 * which produces an 8-character hex string.
 *
 * Python equivalent: identity derivation in `crypto/keys.py`.
 */
export interface QubeIdentity {
  /** Compressed public key (66 hex chars). Python: `public_key`. */
  publicKey: CompressedPublicKey;
  /** NFT commitment hash derived from the public key. */
  commitment: string;
  /** 8-character uppercase hex Qube identifier. Python: `qube_id`. */
  qubeId: string;
}
