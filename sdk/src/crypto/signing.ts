/**
 * ECDSA signing and verification for Qubes memory blocks.
 *
 * Ported from `crypto/signing.py` (154 lines).
 *
 * Uses `@noble/secp256k1` v2 for ECDSA operations and the canonicalStringify
 * utility for deterministic JSON serialization matching Python's
 * `json.dumps(sort_keys=True)`.
 *
 * Signatures are DER-encoded hex strings for compatibility with the existing
 * Python codebase. Since noble/secp256k1 v2 only supports compact (r || s)
 * format, this module includes DER encoding/decoding helpers.
 *
 * @module crypto/signing
 */

import { sign as nobleSign, verify as nobleVerify, Signature, etc } from '@noble/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { hmac } from '@noble/hashes/hmac';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';
import { canonicalStringify } from '../utils/canonical-stringify.js';

// noble/secp256k1 v2 requires HMAC-SHA256 to be configured for signing (RFC 6979)
etc.hmacSha256Sync = (k: Uint8Array, ...m: Uint8Array[]) => {
  const h = hmac.create(sha256, k);
  for (const msg of m) h.update(msg);
  return h.digest();
};

// ---------------------------------------------------------------------------
// DER encoding / decoding helpers
// ---------------------------------------------------------------------------

/**
 * Encode a bigint as a DER INTEGER byte array.
 * DER integers are signed, so a leading 0x00 is prepended if the high bit is set.
 */
function bigintToDerInteger(n: bigint): Uint8Array {
  // Convert bigint to minimal big-endian bytes
  let hex = n.toString(16);
  if (hex.length % 2 !== 0) hex = '0' + hex;
  const bytes = hexToBytes(hex);

  // If high bit set, prepend 0x00 (DER signed integer)
  if (bytes[0] & 0x80) {
    const padded = new Uint8Array(bytes.length + 1);
    padded[0] = 0x00;
    padded.set(bytes, 1);
    return padded;
  }
  return bytes;
}

/**
 * Encode an ECDSA signature (r, s) as DER.
 *
 * DER format: 0x30 <total-len> 0x02 <r-len> <r> 0x02 <s-len> <s>
 */
function signatureToDer(r: bigint, s: bigint): Uint8Array {
  const rBytes = bigintToDerInteger(r);
  const sBytes = bigintToDerInteger(s);

  // SEQUENCE header: 0x30 <length of contents>
  const contentLength = 2 + rBytes.length + 2 + sBytes.length;
  const der = new Uint8Array(2 + contentLength);

  let offset = 0;
  der[offset++] = 0x30; // SEQUENCE tag
  der[offset++] = contentLength;
  der[offset++] = 0x02; // INTEGER tag
  der[offset++] = rBytes.length;
  der.set(rBytes, offset);
  offset += rBytes.length;
  der[offset++] = 0x02; // INTEGER tag
  der[offset++] = sBytes.length;
  der.set(sBytes, offset);

  return der;
}

/**
 * Decode a DER-encoded ECDSA signature back to (r, s) bigints.
 *
 * @throws If the DER encoding is malformed.
 */
function derToSignature(der: Uint8Array): { r: bigint; s: bigint } {
  let offset = 0;

  if (der[offset++] !== 0x30) {
    throw new Error('Invalid DER signature: missing SEQUENCE tag');
  }

  // Read sequence length (may be 1 or 2 bytes, but typically 1 for ECDSA sigs)
  let seqLen = der[offset++];
  if (seqLen & 0x80) {
    // Long form length (unlikely for ECDSA, but handle gracefully)
    const lenBytes = seqLen & 0x7f;
    seqLen = 0;
    for (let i = 0; i < lenBytes; i++) {
      seqLen = (seqLen << 8) | der[offset++];
    }
  }

  // Read r INTEGER
  if (der[offset++] !== 0x02) {
    throw new Error('Invalid DER signature: missing INTEGER tag for r');
  }
  const rLen = der[offset++];
  const rBytes = der.slice(offset, offset + rLen);
  offset += rLen;

  // Read s INTEGER
  if (der[offset++] !== 0x02) {
    throw new Error('Invalid DER signature: missing INTEGER tag for s');
  }
  const sLen = der[offset++];
  const sBytes = der.slice(offset, offset + sLen);

  // Convert to bigint (strip leading zeros from DER signed encoding)
  const r = bytesToBigint(rBytes);
  const s = bytesToBigint(sBytes);

  return { r, s };
}

/** Convert big-endian bytes to bigint. */
function bytesToBigint(bytes: Uint8Array): bigint {
  let result = 0n;
  for (let i = 0; i < bytes.length; i++) {
    result = (result << 8n) | BigInt(bytes[i]);
  }
  return result;
}

// ---------------------------------------------------------------------------
// UTF-8 encoder singleton
// ---------------------------------------------------------------------------

const utf8 = new TextEncoder();

// ---------------------------------------------------------------------------
// Block hashing
// ---------------------------------------------------------------------------

/**
 * Compute the SHA-256 hash of a block's content (excluding `block_hash` and
 * `signature` fields).
 *
 * The block is serialized using `canonicalStringify` (recursive key-sorted
 * JSON, identical to Python's `json.dumps(sort_keys=True)`).
 *
 * Python equivalent: `hash_block` in `crypto/signing.py`.
 *
 * @param block - Block dictionary.
 * @returns 64-character lowercase hex hash.
 */
export function hashBlock(block: Record<string, unknown>): string {
  const blockCopy = { ...block };
  delete blockCopy['block_hash'];
  delete blockCopy['signature'];

  const blockJson = canonicalStringify(blockCopy);
  return bytesToHex(sha256(utf8.encode(blockJson)));
}

// ---------------------------------------------------------------------------
// Block signing
// ---------------------------------------------------------------------------

/**
 * Sign a memory block with an ECDSA private key.
 *
 * **Genesis blocks** (block_number === 0) use a legacy signing method for
 * backward compatibility with NFT commitments on the Bitcoin Cash blockchain.
 * They sign the UTF-8 encoding of the hash hex string.
 *
 * **Standard blocks** sign the canonically-serialized JSON directly.
 *
 * In both cases, the data is SHA-256 hashed before ECDSA signing (matching
 * Python's `ec.ECDSA(hashes.SHA256())`).
 *
 * Python equivalent: `sign_block` in `crypto/signing.py`.
 *
 * @param block      - Block dictionary.
 * @param privateKey - Raw 32-byte secp256k1 private key.
 * @returns DER-encoded ECDSA signature as a hex string.
 */
export function signBlock(
  block: Record<string, unknown>,
  privateKey: Uint8Array,
): string {
  let messageHash: Uint8Array;

  if (block['block_number'] === 0) {
    // Genesis block: sign hash hex string
    // Python: private_key.sign(block_hash.encode(), ec.ECDSA(hashes.SHA256()))
    // This means: SHA256(UTF-8(hashHex)) is the message hash for ECDSA
    const blockHash = hashBlock(block);
    messageHash = sha256(utf8.encode(blockHash));
  } else {
    // Standard block: sign the canonical JSON directly
    // Python: private_key.sign(block_json.encode(), ec.ECDSA(hashes.SHA256()))
    const blockCopy = { ...block };
    delete blockCopy['block_hash'];
    delete blockCopy['signature'];
    const blockJson = canonicalStringify(blockCopy);
    messageHash = sha256(utf8.encode(blockJson));
  }

  // noble/secp256k1 sign expects a pre-hashed message
  // lowS: false to match Python's cryptography library which does not normalize S
  const sig = nobleSign(messageHash, privateKey, { lowS: false });
  const der = signatureToDer(sig.r, sig.s);
  return bytesToHex(der);
}

// ---------------------------------------------------------------------------
// Block signature verification
// ---------------------------------------------------------------------------

/**
 * Verify the ECDSA signature on a memory block.
 *
 * Handles the same genesis/standard bifurcation as `signBlock`.
 *
 * Python equivalent: `verify_block_signature` in `crypto/signing.py`.
 *
 * @param block     - Block dictionary.
 * @param signature - DER-encoded ECDSA signature as hex.
 * @param publicKey - 33-byte compressed secp256k1 public key.
 * @returns `true` if the signature is valid, `false` otherwise.
 */
export function verifyBlockSignature(
  block: Record<string, unknown>,
  signature: string,
  publicKey: Uint8Array,
): boolean {
  let messageHash: Uint8Array;

  if (block['block_number'] === 0) {
    // Genesis block: verify against hash hex string
    const blockHash = hashBlock(block);
    messageHash = sha256(utf8.encode(blockHash));
  } else {
    // Standard block: verify against canonical JSON
    const blockCopy = { ...block };
    delete blockCopy['block_hash'];
    delete blockCopy['signature'];
    const blockJson = canonicalStringify(blockCopy);
    messageHash = sha256(utf8.encode(blockJson));
  }

  try {
    const derBytes = hexToBytes(signature);
    const { r, s } = derToSignature(derBytes);
    const sig = new Signature(r, s);

    // lowS: false to accept both high-S and low-S signatures (Python doesn't normalize)
    return nobleVerify(sig, messageHash, publicKey, { lowS: false });
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Message signing
// ---------------------------------------------------------------------------

/**
 * Sign an arbitrary UTF-8 message with ECDSA-SHA256.
 *
 * Used for P2P protocol operations like signing introduction block hashes.
 *
 * Python equivalent: `sign_message` in `crypto/signing.py`.
 *
 * @param message    - String message to sign (e.g. a block hash).
 * @param privateKey - Raw 32-byte secp256k1 private key.
 * @returns DER-encoded ECDSA signature as hex.
 */
export function signMessage(
  message: string,
  privateKey: Uint8Array,
): string {
  // Python: private_key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
  // = ECDSA(SHA256(UTF-8(message)))
  const messageHash = sha256(utf8.encode(message));
  const sig = nobleSign(messageHash, privateKey, { lowS: false });
  const der = signatureToDer(sig.r, sig.s);
  return bytesToHex(der);
}

/**
 * Verify a DER-encoded ECDSA-SHA256 signature on an arbitrary UTF-8 message.
 *
 * @param message   - Original string message.
 * @param signature - DER-encoded ECDSA signature as hex.
 * @param publicKey - 33-byte compressed secp256k1 public key.
 * @returns `true` if valid, `false` otherwise.
 */
export function verifyMessage(
  message: string,
  signature: string,
  publicKey: Uint8Array,
): boolean {
  try {
    const messageHash = sha256(utf8.encode(message));
    const derBytes = hexToBytes(signature);
    const { r, s } = derToSignature(derBytes);
    const sig = new Signature(r, s);
    return nobleVerify(sig, messageHash, publicKey, { lowS: false });
  } catch {
    return false;
  }
}
