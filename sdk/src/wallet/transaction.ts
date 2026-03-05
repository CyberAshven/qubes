/**
 * Bitcoin Cash transaction serialization, BIP143 sighash, and P2SH spending.
 *
 * Ported from `crypto/bch_script.py` (lines 346-633).
 *
 * Handles variable-length integer encoding, outpoint/output serialization,
 * BIP143-style sighash with SIGHASH_FORKID, and raw transaction construction
 * for the two spending paths of the asymmetric multisig redeem script.
 *
 * @module wallet/transaction
 */

import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';

import {
  OP_0,
  OP_FALSE,
  OP_TRUE,
  SIGHASH_ALL_FORKID,
  pushData,
} from './script.js';
import { addressToScriptPubkey } from './address.js';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/** An unspent transaction output (UTXO). */
export interface UTXO {
  /** Transaction ID in big-endian hex (display format). */
  txid: string;
  /** Output index within the transaction. */
  vout: number;
  /** Value in satoshis. */
  value: number;
  /** Locking script bytes. */
  scriptPubkey: Uint8Array;
}

/** A transaction output destination. */
export interface TxOutput {
  /** CashAddr destination address. */
  address: string;
  /** Value in satoshis. */
  value: number;
}

// ---------------------------------------------------------------------------
// Helpers: double SHA-256, LE integer writing
// ---------------------------------------------------------------------------

/** Double SHA-256 hash (used for txid, sighash, etc.). */
function doubleSha256(data: Uint8Array): Uint8Array {
  return sha256(sha256(data));
}

/** Write a 32-bit unsigned integer in little-endian into `buf` at `offset`. */
function writeUint32LE(buf: Uint8Array, value: number, offset: number): void {
  buf[offset] = value & 0xff;
  buf[offset + 1] = (value >>> 8) & 0xff;
  buf[offset + 2] = (value >>> 16) & 0xff;
  buf[offset + 3] = (value >>> 24) & 0xff;
}

/**
 * Write a 64-bit unsigned integer in little-endian into `buf` at `offset`.
 *
 * JavaScript numbers can represent integers up to 2^53 safely. For satoshi
 * values this is more than sufficient (max BCH supply < 2^53).
 */
function writeUint64LE(buf: Uint8Array, value: number, offset: number): void {
  // Low 32 bits
  const lo = value >>> 0;          // unsigned truncation
  const hi = Math.floor(value / 0x100000000) >>> 0;
  writeUint32LE(buf, lo, offset);
  writeUint32LE(buf, hi, offset + 4);
}

// ---------------------------------------------------------------------------
// Variable-length integer (CompactSize)
// ---------------------------------------------------------------------------

/**
 * Encode a variable-length integer (Bitcoin CompactSize encoding).
 *
 * | Value range      | Encoding                 |
 * |------------------|--------------------------|
 * | 0 - 0xFC         | 1 byte                   |
 * | 0xFD - 0xFFFF    | 0xFD + LE16              |
 * | 0x10000 - 0xFFFFFFFF | 0xFE + LE32          |
 * | larger           | 0xFF + LE64              |
 *
 * @param n - Non-negative integer.
 * @returns CompactSize-encoded bytes.
 */
export function varInt(n: number): Uint8Array {
  if (n < 0xfd) {
    return new Uint8Array([n]);
  }
  if (n <= 0xffff) {
    const buf = new Uint8Array(3);
    buf[0] = 0xfd;
    buf[1] = n & 0xff;
    buf[2] = (n >> 8) & 0xff;
    return buf;
  }
  if (n <= 0xffffffff) {
    const buf = new Uint8Array(5);
    buf[0] = 0xfe;
    writeUint32LE(buf, n, 1);
    return buf;
  }
  // 0xFF + 8-byte LE — rarely needed for standard txs
  const buf = new Uint8Array(9);
  buf[0] = 0xff;
  writeUint64LE(buf, n, 1);
  return buf;
}

// ---------------------------------------------------------------------------
// Outpoint & output serialization
// ---------------------------------------------------------------------------

/**
 * Serialize a transaction outpoint (txid + vout).
 *
 * The txid is in big-endian display format and must be reversed to
 * little-endian for internal representation.
 *
 * @param txid - 32-byte transaction hash as hex (big-endian display format).
 * @param vout - Output index.
 * @returns 36-byte serialized outpoint.
 */
export function serializeOutpoint(txid: string, vout: number): Uint8Array {
  const txidBytes = hexToBytes(txid);

  // Reverse txid from big-endian display format to little-endian
  const txidLE = new Uint8Array(txidBytes.length);
  for (let i = 0; i < txidBytes.length; i++) {
    txidLE[i] = txidBytes[txidBytes.length - 1 - i];
  }

  const result = new Uint8Array(36);
  result.set(txidLE, 0);
  writeUint32LE(result, vout, 32);
  return result;
}

/**
 * Serialize a transaction output (value + scriptPubKey).
 *
 * @param value        - Output value in satoshis.
 * @param scriptPubkey - The locking script.
 * @returns Serialized output bytes.
 */
export function serializeOutput(
  value: number,
  scriptPubkey: Uint8Array,
): Uint8Array {
  const scriptLen = varInt(scriptPubkey.length);
  const result = new Uint8Array(8 + scriptLen.length + scriptPubkey.length);
  writeUint64LE(result, value, 0);
  result.set(scriptLen, 8);
  result.set(scriptPubkey, 8 + scriptLen.length);
  return result;
}

// ---------------------------------------------------------------------------
// BIP143 sighash with FORKID
// ---------------------------------------------------------------------------

/** Input descriptor for sighash computation. */
interface SighashInput {
  txid: string;
  vout: number;
  value: number;
  scriptPubkey: Uint8Array;
}

/** Output descriptor for sighash computation. */
interface SighashOutput {
  value: number;
  scriptPubkey: Uint8Array;
}

/**
 * Calculate BIP143-style sighash with SIGHASH_FORKID for BCH.
 *
 * Preimage layout (BIP143):
 * 1. nVersion        (4 bytes LE)
 * 2. hashPrevouts    (32 bytes) — double-SHA256 of all outpoints
 * 3. hashSequence    (32 bytes) — double-SHA256 of all sequences
 * 4. outpoint        (36 bytes) — txid + vout of input being signed
 * 5. scriptCode      (varint + script) — the redeem script
 * 6. value           (8 bytes LE) — UTXO value being spent
 * 7. nSequence       (4 bytes LE) — sequence of input being signed
 * 8. hashOutputs     (32 bytes) — double-SHA256 of all serialized outputs
 * 9. nLockTime       (4 bytes LE)
 * 10. sighashType    (4 bytes LE) — includes FORKID flag
 *
 * All input sequences are hardcoded to `0xffffffff`. Locktime is `0`.
 *
 * @param txVersion    - Transaction version (typically 2).
 * @param inputs       - Array of input descriptors.
 * @param outputs      - Array of output descriptors (with pre-computed scriptPubkey).
 * @param inputIdx     - Index of the input being signed.
 * @param redeemScript - The redeem script (for P2SH).
 * @param sighashType  - Sighash flags (default: `SIGHASH_ALL_FORKID`).
 * @returns 32-byte sighash digest.
 */
export function calculateSighashForkid(
  txVersion: number,
  inputs: SighashInput[],
  outputs: SighashOutput[],
  inputIdx: number,
  redeemScript: Uint8Array,
  sighashType: number = SIGHASH_ALL_FORKID,
): Uint8Array {
  // ------- 1. nVersion (4 bytes) -------
  const nVersion = new Uint8Array(4);
  writeUint32LE(nVersion, txVersion, 0);

  // ------- 2. hashPrevouts -------
  const prevoutsChunks: Uint8Array[] = [];
  for (const inp of inputs) {
    prevoutsChunks.push(serializeOutpoint(inp.txid, inp.vout));
  }
  const prevoutsConcat = concatBytes(...prevoutsChunks);
  const hashPrevouts = doubleSha256(prevoutsConcat);

  // ------- 3. hashSequence -------
  // All sequences = 0xffffffff
  const seqBuf = new Uint8Array(4 * inputs.length);
  for (let i = 0; i < inputs.length; i++) {
    writeUint32LE(seqBuf, 0xffffffff, i * 4);
  }
  const hashSequence = doubleSha256(seqBuf);

  // ------- 4. outpoint of input being signed -------
  const outpoint = serializeOutpoint(inputs[inputIdx].txid, inputs[inputIdx].vout);

  // ------- 5. scriptCode (varint len + script) -------
  const scriptLenVI = varInt(redeemScript.length);
  const scriptCode = concatBytes(scriptLenVI, redeemScript);

  // ------- 6. value of UTXO being spent (8 bytes LE) -------
  const valueBuf = new Uint8Array(8);
  writeUint64LE(valueBuf, inputs[inputIdx].value, 0);

  // ------- 7. nSequence of input being signed (4 bytes LE) -------
  const nSeq = new Uint8Array(4);
  writeUint32LE(nSeq, 0xffffffff, 0);

  // ------- 8. hashOutputs -------
  const outputChunks: Uint8Array[] = [];
  for (const out of outputs) {
    outputChunks.push(serializeOutput(out.value, out.scriptPubkey));
  }
  const outputsConcat = concatBytes(...outputChunks);
  const hashOutputs = doubleSha256(outputsConcat);

  // ------- 9. nLockTime (4 bytes LE) -------
  const nLockTime = new Uint8Array(4); // all zeros = locktime 0

  // ------- 10. sighashType (4 bytes LE) -------
  const sighashBuf = new Uint8Array(4);
  writeUint32LE(sighashBuf, sighashType, 0);

  // Build preimage
  const preimage = concatBytes(
    nVersion,
    hashPrevouts,
    hashSequence,
    outpoint,
    scriptCode,
    valueBuf,
    nSeq,
    hashOutputs,
    nLockTime,
    sighashBuf,
  );

  return doubleSha256(preimage);
}

// ---------------------------------------------------------------------------
// Raw transaction building
// ---------------------------------------------------------------------------

/**
 * Build a signed P2SH spending transaction (single input only).
 *
 * Spending paths:
 * - `"owner_only"`: scriptSig = `push(sig) OP_TRUE push(redeemScript)`
 * - `"multisig"`: scriptSig = `OP_0 push(ownerSig) push(qubeSig) OP_FALSE push(redeemScript)`
 *
 * Transaction version is always 2. Locktime is 0.
 *
 * @param utxo          - The single UTXO to spend.
 * @param outputs       - Array of destination outputs.
 * @param redeemScript  - The redeem script.
 * @param signatures    - 1 signature for owner_only, 2 for multisig.
 * @param spendingPath  - `"owner_only"` or `"multisig"`.
 * @returns Serialized raw transaction bytes.
 */
export function buildP2shSpendingTx(
  utxo: UTXO,
  outputs: TxOutput[],
  redeemScript: Uint8Array,
  signatures: Uint8Array[],
  spendingPath: 'owner_only' | 'multisig',
): Uint8Array {
  // Build scriptSig based on spending path
  let scriptSig: Uint8Array;

  if (spendingPath === 'owner_only') {
    if (signatures.length !== 1) {
      throw new Error('Owner-only path requires exactly 1 signature');
    }
    // <owner_sig> OP_TRUE <redeem_script>
    scriptSig = concatBytes(
      pushData(signatures[0]),
      new Uint8Array([OP_TRUE]),
      pushData(redeemScript),
    );
  } else if (spendingPath === 'multisig') {
    if (signatures.length !== 2) {
      throw new Error('Multisig path requires exactly 2 signatures');
    }
    // OP_0 <owner_sig> <qube_sig> OP_FALSE <redeem_script>
    // OP_CHECKMULTISIG has an off-by-one bug requiring OP_0 prefix
    scriptSig = concatBytes(
      new Uint8Array([OP_0]),
      pushData(signatures[0]),
      pushData(signatures[1]),
      new Uint8Array([OP_FALSE]),
      pushData(redeemScript),
    );
  } else {
    throw new Error(`Unknown spending path: ${spendingPath}`);
  }

  // Calculate output scripts
  const outputScripts: Array<{ value: number; script: Uint8Array }> = [];
  for (const out of outputs) {
    outputScripts.push({
      value: out.value,
      script: addressToScriptPubkey(out.address),
    });
  }

  // --- Assemble transaction ---

  // Version (4 bytes)
  const version = new Uint8Array(4);
  writeUint32LE(version, 2, 0);

  // Input count
  const inputCount = varInt(1);

  // Input: outpoint + scriptSig + sequence
  const outpointBytes = serializeOutpoint(utxo.txid, utxo.vout);
  const scriptSigLen = varInt(scriptSig.length);
  const sequence = new Uint8Array(4);
  writeUint32LE(sequence, 0xffffffff, 0);

  // Output count
  const outputCount = varInt(outputScripts.length);

  // Serialized outputs
  const serializedOutputs: Uint8Array[] = [];
  for (const { value, script } of outputScripts) {
    serializedOutputs.push(serializeOutput(value, script));
  }

  // Locktime (4 bytes, all zeros)
  const locktime = new Uint8Array(4);

  return concatBytes(
    version,
    inputCount,
    outpointBytes,
    scriptSigLen,
    scriptSig,
    sequence,
    outputCount,
    ...serializedOutputs,
    locktime,
  );
}

// ---------------------------------------------------------------------------
// Fee estimation
// ---------------------------------------------------------------------------

/**
 * Estimate the size of a transaction in bytes.
 *
 * @param numInputs    - Number of inputs.
 * @param numOutputs   - Number of outputs.
 * @param spendingPath - `"owner_only"` or `"multisig"`.
 * @returns Estimated transaction size in bytes.
 */
export function estimateTxSize(
  numInputs: number,
  numOutputs: number,
  spendingPath: 'owner_only' | 'multisig',
): number {
  // Base: version(4) + locktime(4) + varint for input/output counts(~2)
  const base = 10;

  let inputSize: number;

  if (spendingPath === 'owner_only') {
    // <sig>(~72) + OP_TRUE(1) + <redeem_script>(~76) + push overheads(~3)
    // outpoint(36) + scriptSigLen(~3) + sequence(4)
    inputSize = 36 + 3 + 4 + 72 + 1 + 76 + 3; // ~195
  } else {
    // OP_0(1) + <sig1>(~72) + <sig2>(~72) + OP_FALSE(1) + <redeem_script>(~76) + push overheads(~3)
    // outpoint(36) + scriptSigLen(~3) + sequence(4)
    inputSize = 36 + 3 + 4 + 1 + 72 + 72 + 1 + 76 + 3; // ~268
  }

  // P2PKH output: ~34 bytes on average
  const outputSize = 34;

  return base + inputSize * numInputs + outputSize * numOutputs;
}

/**
 * Calculate the transaction fee based on size and fee rate.
 *
 * @param txSize     - Transaction size in bytes.
 * @param feePerByte - Fee rate in satoshis per byte (default 1).
 * @returns Fee in satoshis.
 */
export function calculateFee(txSize: number, feePerByte: number = 1): number {
  return txSize * feePerByte;
}

// ---------------------------------------------------------------------------
// Utility: concatenate Uint8Arrays
// ---------------------------------------------------------------------------

/**
 * Concatenate multiple Uint8Array values into a single Uint8Array.
 */
function concatBytes(...arrays: Uint8Array[]): Uint8Array {
  let totalLen = 0;
  for (const a of arrays) {
    totalLen += a.length;
  }
  const result = new Uint8Array(totalLen);
  let offset = 0;
  for (const a of arrays) {
    result.set(a, offset);
    offset += a.length;
  }
  return result;
}
