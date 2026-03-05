/**
 * BCH Script opcodes, push-data encoding, and asymmetric multisig script builder.
 *
 * Ported from `crypto/bch_script.py` (lines 19-178).
 *
 * @module wallet/script
 */

// ---------------------------------------------------------------------------
// Opcodes
// ---------------------------------------------------------------------------

/** OP_0 / OP_FALSE — push empty byte array */
export const OP_0 = 0x00;
/** Alias for OP_0 */
export const OP_FALSE = 0x00;
/** OP_TRUE / OP_1 — push the number 1 */
export const OP_TRUE = 0x51;
/** Alias for OP_TRUE */
export const OP_1 = 0x51;
/** OP_2 — push the number 2 */
export const OP_2 = 0x52;
/** OP_IF — conditional branch */
export const OP_IF = 0x63;
/** OP_ELSE — alternative branch */
export const OP_ELSE = 0x67;
/** OP_ENDIF — end conditional */
export const OP_ENDIF = 0x68;
/** OP_DUP — duplicate top stack element */
export const OP_DUP = 0x76;
/** OP_HASH160 — RIPEMD160(SHA256(x)) */
export const OP_HASH160 = 0xa9;
/** OP_EQUAL — check equality */
export const OP_EQUAL = 0x87;
/** OP_EQUALVERIFY — check equality then verify */
export const OP_EQUALVERIFY = 0x88;
/** OP_CHECKSIG — verify ECDSA signature */
export const OP_CHECKSIG = 0xac;
/** OP_CHECKMULTISIG — verify multiple ECDSA signatures */
export const OP_CHECKMULTISIG = 0xae;

// ---------------------------------------------------------------------------
// Sighash types
// ---------------------------------------------------------------------------

/** SIGHASH_ALL — sign all inputs and outputs */
export const SIGHASH_ALL = 0x01;
/** SIGHASH_FORKID — BCH replay protection flag */
export const SIGHASH_FORKID = 0x40;
/** SIGHASH_ALL | SIGHASH_FORKID — standard BCH sighash type */
export const SIGHASH_ALL_FORKID = 0x41;

// ---------------------------------------------------------------------------
// Push data encoding
// ---------------------------------------------------------------------------

/**
 * Create a Bitcoin script push-data opcode sequence.
 *
 * - `len <= 75`: `[len] + data` (direct push)
 * - `76 <= len <= 255`: `OP_PUSHDATA1 [len] + data`
 * - `256 <= len <= 65535`: `OP_PUSHDATA2 LE16(len) + data`
 *
 * @param data - The raw bytes to push onto the script stack.
 * @returns Encoded push-data opcode sequence.
 */
export function pushData(data: Uint8Array): Uint8Array {
  const length = data.length;

  if (length <= 75) {
    const result = new Uint8Array(1 + length);
    result[0] = length;
    result.set(data, 1);
    return result;
  }

  if (length <= 255) {
    // OP_PUSHDATA1 (0x4c) + 1-byte length
    const result = new Uint8Array(2 + length);
    result[0] = 0x4c;
    result[1] = length;
    result.set(data, 2);
    return result;
  }

  if (length <= 65535) {
    // OP_PUSHDATA2 (0x4d) + 2-byte LE length
    const result = new Uint8Array(3 + length);
    result[0] = 0x4d;
    result[1] = length & 0xff;
    result[2] = (length >> 8) & 0xff;
    result.set(data, 3);
    return result;
  }

  throw new Error(`Data too large: ${length} bytes`);
}

// ---------------------------------------------------------------------------
// Script builders
// ---------------------------------------------------------------------------

/**
 * Build an asymmetric multisig redeem script (IF/ELSE).
 *
 * Script structure:
 * ```
 * OP_IF
 *   <owner_pubkey> OP_CHECKSIG         // owner alone
 * OP_ELSE
 *   OP_2 <owner_pubkey> <qube_pubkey> OP_2 OP_CHECKMULTISIG  // 2-of-2
 * OP_ENDIF
 * ```
 *
 * Spending paths:
 * 1. Owner alone: `<owner_sig> OP_TRUE <redeem_script>`
 * 2. Both required: `OP_0 <owner_sig> <qube_sig> OP_FALSE <redeem_script>`
 *
 * @param ownerPubkey - 33-byte compressed public key (02... or 03...).
 * @param qubePubkey  - 33-byte compressed public key (02... or 03...).
 * @returns The redeem script bytes.
 */
export function buildAsymmetricMultisigScript(
  ownerPubkey: Uint8Array,
  qubePubkey: Uint8Array,
): Uint8Array {
  if (ownerPubkey.length !== 33) {
    throw new Error(
      `Owner pubkey must be 33 bytes (compressed), got ${ownerPubkey.length}`,
    );
  }
  if (qubePubkey.length !== 33) {
    throw new Error(
      `Qube pubkey must be 33 bytes (compressed), got ${qubePubkey.length}`,
    );
  }

  const ownerPush = pushData(ownerPubkey);
  const qubePush = pushData(qubePubkey);

  // Calculate total length to avoid repeated concatenation
  // OP_IF(1) + ownerPush + OP_CHECKSIG(1)
  // + OP_ELSE(1) + OP_2(1) + ownerPush + qubePush + OP_2(1) + OP_CHECKMULTISIG(1)
  // + OP_ENDIF(1)
  const totalLen =
    1 + ownerPush.length + 1 +
    1 + 1 + ownerPush.length + qubePush.length + 1 + 1 +
    1;

  const script = new Uint8Array(totalLen);
  let offset = 0;

  // OP_IF
  script[offset++] = OP_IF;

  // <owner_pubkey> OP_CHECKSIG
  script.set(ownerPush, offset);
  offset += ownerPush.length;
  script[offset++] = OP_CHECKSIG;

  // OP_ELSE
  script[offset++] = OP_ELSE;

  // OP_2 <owner_pubkey> <qube_pubkey> OP_2 OP_CHECKMULTISIG
  script[offset++] = OP_2;
  script.set(ownerPush, offset);
  offset += ownerPush.length;
  script.set(qubePush, offset);
  offset += qubePush.length;
  script[offset++] = OP_2;
  script[offset++] = OP_CHECKMULTISIG;

  // OP_ENDIF
  script[offset++] = OP_ENDIF;

  return script;
}

/**
 * Build a P2SH locking script (scriptPubKey).
 *
 * Format: `OP_HASH160 <20-byte-hash> OP_EQUAL`
 *
 * @param scriptHash - 20-byte HASH160 of the redeem script.
 * @returns The P2SH scriptPubKey bytes.
 */
export function buildP2shScriptPubkey(scriptHash: Uint8Array): Uint8Array {
  if (scriptHash.length !== 20) {
    throw new Error(
      `Script hash must be 20 bytes, got ${scriptHash.length}`,
    );
  }

  const hashPush = pushData(scriptHash);
  const result = new Uint8Array(1 + hashPush.length + 1);
  result[0] = OP_HASH160;
  result.set(hashPush, 1);
  result[1 + hashPush.length] = OP_EQUAL;
  return result;
}
