/**
 * CashAddr encoding and decoding for Bitcoin Cash addresses.
 *
 * Ported from `crypto/bch_script.py` (lines 183-314).
 *
 * The CashAddr format is similar to Bech32 but uses a different polynomial
 * and character set. This implementation uses BigInt for the polymod
 * calculation because the 40-bit accumulator overflows JavaScript's 32-bit
 * bitwise operator range.
 *
 * @module wallet/cashaddr
 */

import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** CashAddr base-32 character set */
export const CASHADDR_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';

/**
 * Generator constants for the BCH polynomial checksum.
 * These are 40-bit values and MUST be handled as BigInt.
 */
const GENERATORS: bigint[] = [
  0x98f2bc8e61n,
  0x79b76d99e2n,
  0xf33e5fb3c4n,
  0xae2eabe2a8n,
  0x1e4f43e470n,
];

// ---------------------------------------------------------------------------
// Hash helper (hash160 = RIPEMD160(SHA256(x)))
// ---------------------------------------------------------------------------

/**
 * Compute HASH160: RIPEMD-160(SHA-256(data)).
 *
 * Uses pure-JS implementations from `@noble/hashes` so this works in both
 * browser and Node.js with zero `node:` dependencies.
 */
function hash160(data: Uint8Array): Uint8Array {
  return ripemd160(sha256(data));
}

// ---------------------------------------------------------------------------
// Polymod & checksum
// ---------------------------------------------------------------------------

/**
 * CashAddr BCH polynomial checksum.
 *
 * Uses BigInt internally because the accumulator (`c`) is 40 bits wide and
 * JavaScript bitwise operators truncate to 32 bits.
 *
 * @param values - Array of 5-bit integers.
 * @returns Polymod value as a regular number.
 */
export function cashAddrPolymod(values: number[]): number {
  let c = 1n;
  for (const d of values) {
    const c0 = c >> 35n;
    c = ((c & 0x07ffffffffn) << 5n) ^ BigInt(d);
    for (let i = 0; i < 5; i++) {
      if ((c0 >> BigInt(i)) & 1n) {
        c ^= GENERATORS[i];
      }
    }
  }
  return Number(c ^ 1n);
}

/**
 * Expand the human-readable part (prefix) for checksum computation.
 *
 * Each character is mapped to `charCode & 0x1f`, followed by a `[0]` separator.
 */
export function cashAddrHrpExpand(hrp: string): number[] {
  const result: number[] = [];
  for (let i = 0; i < hrp.length; i++) {
    result.push(hrp.charCodeAt(i) & 0x1f);
  }
  result.push(0);
  return result;
}

/**
 * Create an 8-value CashAddr checksum.
 *
 * @param hrp  - Human-readable prefix (e.g. "bitcoincash").
 * @param data - 5-bit payload values.
 * @returns 8 five-bit checksum values.
 */
export function createChecksum(hrp: string, data: number[]): number[] {
  const values = cashAddrHrpExpand(hrp).concat(data).concat([0, 0, 0, 0, 0, 0, 0, 0]);
  const polymod = BigInt(cashAddrPolymod(values));
  const result: number[] = [];
  for (let i = 0; i < 8; i++) {
    result.push(Number((polymod >> BigInt(5 * (7 - i))) & 31n));
  }
  return result;
}

// ---------------------------------------------------------------------------
// Bit conversion
// ---------------------------------------------------------------------------

/**
 * Convert between arbitrary bit-width representations.
 *
 * For example, convert 8-bit bytes to 5-bit groups (or vice-versa).
 *
 * @param data     - Source values.
 * @param fromBits - Bit width of each source value.
 * @param toBits   - Bit width of each output value.
 * @param pad      - Whether to pad the final group with zero bits (default `true`).
 * @returns Array of `toBits`-wide values.
 */
export function convertBits(
  data: Uint8Array | number[],
  fromBits: number,
  toBits: number,
  pad = true,
): number[] {
  let acc = 0;
  let bits = 0;
  const result: number[] = [];
  const maxv = (1 << toBits) - 1;

  for (let i = 0; i < data.length; i++) {
    const value = data[i];
    acc = (acc << fromBits) | value;
    bits += fromBits;
    while (bits >= toBits) {
      bits -= toBits;
      result.push((acc >> bits) & maxv);
    }
  }

  if (pad && bits > 0) {
    result.push((acc << (toBits - bits)) & maxv);
  }

  return result;
}

// ---------------------------------------------------------------------------
// Encoding
// ---------------------------------------------------------------------------

/**
 * Encode a CashAddr address from prefix, version byte, and hash.
 *
 * @param prefix  - Network prefix (e.g. "bitcoincash" or "bchtest").
 * @param version - Version byte (encodes type + size, e.g. 0x00 for P2PKH, 0x08 for P2SH).
 * @param hash    - The address hash (typically 20 bytes).
 * @returns Full CashAddr string with prefix (e.g. "bitcoincash:qr...").
 */
export function encodeCashAddr(
  prefix: string,
  version: number,
  hash: Uint8Array,
): string {
  // Prepend version byte to hash, then convert 8-bit to 5-bit
  const payload = new Uint8Array(1 + hash.length);
  payload[0] = version;
  payload.set(hash, 1);

  const data = convertBits(payload, 8, 5);
  const checksum = createChecksum(prefix, data);
  const combined = data.concat(checksum);

  let addr = '';
  for (const d of combined) {
    addr += CASHADDR_CHARSET[d];
  }

  return `${prefix}:${addr}`;
}

// ---------------------------------------------------------------------------
// Decoding
// ---------------------------------------------------------------------------

/**
 * Decode a CashAddr address to its prefix, version byte, and hash.
 *
 * @param address - Full or unprefixed CashAddr string.
 * @returns Object with `prefix`, `version`, and `hash`.
 */
export function decodeCashAddr(
  address: string,
): { prefix: string; version: number; hash: Uint8Array } {
  let prefix: string;
  let addr: string;

  if (address.includes(':')) {
    const idx = address.indexOf(':');
    prefix = address.slice(0, idx);
    addr = address.slice(idx + 1);
  } else {
    // Assume mainnet if no prefix
    prefix = 'bitcoincash';
    addr = address;
  }

  // Decode base-32 characters to 5-bit values
  const data: number[] = [];
  for (const ch of addr.toLowerCase()) {
    const idx = CASHADDR_CHARSET.indexOf(ch);
    if (idx === -1) {
      throw new Error(`Invalid CashAddr character: '${ch}'`);
    }
    data.push(idx);
  }

  // Verify checksum
  const hrpExpanded = cashAddrHrpExpand(prefix);
  if (cashAddrPolymod(hrpExpanded.concat(data)) !== 0) {
    throw new Error('Invalid CashAddr checksum');
  }

  // Remove checksum (last 8 five-bit values)
  const payload5bit = data.slice(0, -8);

  // Convert 5-bit groups back to 8-bit bytes
  const payloadBytes = convertBits(payload5bit, 5, 8, false);

  const version = payloadBytes[0];
  const hash = new Uint8Array(payloadBytes.slice(1));

  return { prefix, version, hash };
}

// ---------------------------------------------------------------------------
// High-level: script → P2SH address
// ---------------------------------------------------------------------------

/**
 * Derive a P2SH CashAddr address from a redeem script.
 *
 * 1. HASH160 the redeem script.
 * 2. Encode with version byte 0x08 (P2SH, 160-bit hash).
 * 3. Prefix: "bitcoincash" (mainnet) or "bchtest" (testnet/chipnet).
 *
 * @param script  - The redeem script bytes.
 * @param network - `"mainnet"` (default) or `"testnet"`.
 * @returns CashAddr string (e.g. "bitcoincash:pr...").
 */
export function scriptToP2shAddress(
  script: Uint8Array,
  network: string = 'mainnet',
): string {
  const scriptHash = hash160(script);
  const versionByte = 0x08; // P2SH, 160-bit hash
  const prefix = network === 'mainnet' ? 'bitcoincash' : 'bchtest';
  return encodeCashAddr(prefix, versionByte, scriptHash);
}
