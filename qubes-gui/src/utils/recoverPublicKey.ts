/**
 * Bitcoin Signed Message public key recovery.
 *
 * Recovers the signer's compressed public key from a Bitcoin Signed Message
 * recoverable ECDSA signature (65 bytes: [recovery_flag, r(32), s(32)]).
 */

import { secp256k1 } from '@noble/curves/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { concatBytes, bytesToHex } from '@noble/hashes/utils';

/**
 * Encode an integer as a Bitcoin-style varint (CompactSize).
 */
function encodeVarint(n: number): Uint8Array {
  if (n < 0xfd) return new Uint8Array([n]);
  if (n <= 0xffff) {
    const buf = new Uint8Array(3);
    buf[0] = 0xfd;
    buf[1] = n & 0xff;
    buf[2] = (n >> 8) & 0xff;
    return buf;
  }
  throw new Error(`Varint too large: ${n}`);
}

/**
 * Compute the Bitcoin Signed Message hash (double-SHA256).
 *
 * Format: SHA256(SHA256("\x18Bitcoin Signed Message:\n" + varint(len) + message))
 */
function bitcoinMessageHash(message: string): Uint8Array {
  const prefix = new TextEncoder().encode('\x18Bitcoin Signed Message:\n');
  const msgBytes = new TextEncoder().encode(message);
  const varint = encodeVarint(msgBytes.length);
  return sha256(sha256(concatBytes(prefix, varint, msgBytes)));
}

/**
 * Recover a compressed public key from a Bitcoin Signed Message signature.
 *
 * @param message - The original signed message (plaintext)
 * @param signatureBase64 - Base64-encoded 65-byte recoverable signature
 *   Byte layout: [recovery_flag(1), r(32), s(32)]
 *   recovery_flag: 27-30 (uncompressed) or 31-34 (compressed)
 * @returns 66-character hex string (compressed pubkey: 02... or 03...)
 */
export function recoverCompressedPubkey(
  message: string,
  signatureBase64: string,
): string {
  const raw = Uint8Array.from(atob(signatureBase64), (c) => c.charCodeAt(0));
  if (raw.length !== 65) {
    throw new Error(`Invalid signature length: expected 65 bytes, got ${raw.length}`);
  }

  const recoveryFlag = raw[0];
  if (recoveryFlag < 27 || recoveryFlag > 34) {
    throw new Error(`Invalid recovery flag: ${recoveryFlag} (expected 27-34)`);
  }

  const recoveryBit = (recoveryFlag - 27) & 3;
  const compactSig = raw.slice(1, 65);
  const msgHash = bitcoinMessageHash(message);

  const sig = secp256k1.Signature.fromCompact(compactSig).addRecoveryBit(recoveryBit);
  const point = sig.recoverPublicKey(msgHash);

  return bytesToHex(point.toRawBytes(true));
}
