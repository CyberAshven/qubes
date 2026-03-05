/**
 * Address derivation and conversion utilities for Bitcoin Cash.
 *
 * Ported from `crypto/bch_script.py` (lines 639-898).
 *
 * Handles P2PKH address derivation from public keys, token-aware (z) vs.
 * standard (q) address conversion, scriptPubKey generation, and end-to-end
 * P2SH wallet creation from owner + Qube key pairs.
 *
 * @module wallet/address
 */

import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';

import {
  encodeCashAddr,
  decodeCashAddr,
  convertBits,
  createChecksum,
  CASHADDR_CHARSET,
  scriptToP2shAddress,
} from './cashaddr.js';

import {
  OP_DUP,
  OP_HASH160,
  OP_EQUAL,
  OP_EQUALVERIFY,
  OP_CHECKSIG,
  pushData,
  buildAsymmetricMultisigScript,
  buildP2shScriptPubkey,
} from './script.js';

// ---------------------------------------------------------------------------
// Hash helper
// ---------------------------------------------------------------------------

/** HASH160 = RIPEMD-160(SHA-256(data)). */
function hash160(data: Uint8Array): Uint8Array {
  return ripemd160(sha256(data));
}

// ---------------------------------------------------------------------------
// P2PKH address derivation
// ---------------------------------------------------------------------------

/**
 * Convert a compressed public key to a P2PKH CashAddr address.
 *
 * Version byte layout (CashAddr spec):
 * - Bits 7-5: reserved (0)
 * - Bit 4: token-aware flag (0 = standard, 1 = token-aware)
 * - Bit 3: address type (0 = P2PKH, 1 = P2SH)
 * - Bits 2-0: hash size (0 = 160-bit)
 *
 * | Version | Prefix char | Description           |
 * |---------|-------------|-----------------------|
 * | 0x00    | q           | Standard P2PKH        |
 * | 0x10    | z           | Token-aware P2PKH     |
 * | 0x08    | p           | Standard P2SH         |
 * | 0x18    | r           | Token-aware P2SH      |
 *
 * @param pubkeyHex   - 33-byte compressed public key as hex string (66 chars).
 * @param network     - `"mainnet"` (default) or `"testnet"`.
 * @param tokenAware  - If `true`, produces a `z` address; otherwise a `q` address.
 * @returns CashAddr string.
 */
export function pubkeyToP2pkhAddress(
  pubkeyHex: string,
  network: string = 'mainnet',
  tokenAware: boolean = false,
): string {
  const pubkey = hexToBytes(pubkeyHex);
  if (pubkey.length !== 33) {
    throw new Error(
      `Public key must be 33 bytes (compressed), got ${pubkey.length}`,
    );
  }

  const pubkeyHash = hash160(pubkey);
  const versionByte = tokenAware ? 0x10 : 0x00;
  const prefix = network === 'mainnet' ? 'bitcoincash' : 'bchtest';

  return encodeCashAddr(prefix, versionByte, pubkeyHash);
}

/**
 * Convenience: convert public key to a token-aware `z` address.
 *
 * This is the address format required for receiving CashTokens (NFTs).
 *
 * @param pubkeyHex - 33-byte compressed public key as hex string.
 * @param network   - `"mainnet"` (default) or `"testnet"`.
 * @returns Token-aware CashAddr (`bitcoincash:z...`).
 */
export function pubkeyToTokenAddress(
  pubkeyHex: string,
  network: string = 'mainnet',
): string {
  return pubkeyToP2pkhAddress(pubkeyHex, network, true);
}

/**
 * Convenience: convert public key to a standard `q` address.
 *
 * @param pubkeyHex - 33-byte compressed public key as hex string.
 * @param network   - `"mainnet"` (default) or `"testnet"`.
 * @returns Standard CashAddr (`bitcoincash:q...`).
 */
export function pubkeyToCashAddress(
  pubkeyHex: string,
  network: string = 'mainnet',
): string {
  return pubkeyToP2pkhAddress(pubkeyHex, network, false);
}

// ---------------------------------------------------------------------------
// q ↔ z address conversion
// ---------------------------------------------------------------------------

/**
 * Convert a standard `q` address to its corresponding token-aware `z` address.
 *
 * Both addresses share the same pubkey hash; only the version byte differs
 * (bit 4 is set for token-aware).
 *
 * @param qAddress - Standard CashAddr (`bitcoincash:q...` or just `q...`).
 * @returns Token-aware CashAddr (`bitcoincash:z...`).
 */
export function cashAddressToTokenAddress(qAddress: string): string {
  const { prefix, version, hash } = decodeCashAddr(qAddress);

  // Verify it is a P2PKH address (bit 3 = 0)
  const addrType = (version >> 3) & 0x01;
  if (addrType !== 0) {
    throw new Error(
      `Address is P2SH (version 0x${version.toString(16)}), not P2PKH. Cannot convert to token address.`,
    );
  }

  // If already token-aware (bit 4 set), return unchanged
  if ((version >> 4) & 0x01) {
    return qAddress;
  }

  // Set bit 4 for token-aware
  const tokenVersion = version | 0x10;
  return encodeCashAddr(prefix, tokenVersion, hash);
}

/**
 * Convert a token-aware `z` address to its corresponding standard `q` address.
 *
 * @param zAddress - Token-aware CashAddr (`bitcoincash:z...`).
 * @returns Standard CashAddr (`bitcoincash:q...`).
 */
export function tokenAddressToCashAddress(zAddress: string): string {
  const { prefix, version, hash } = decodeCashAddr(zAddress);

  // Clear bit 4
  const standardVersion = version & ~0x10;
  return encodeCashAddr(prefix, standardVersion, hash);
}

// ---------------------------------------------------------------------------
// Address → scriptPubKey
// ---------------------------------------------------------------------------

/**
 * Convert a CashAddr address to its corresponding scriptPubKey.
 *
 * - **P2PKH** (version bit 3 = 0):
 *   `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`
 * - **P2SH** (version bit 3 = 1):
 *   `OP_HASH160 <hash> OP_EQUAL`
 *
 * @param address - CashAddr string.
 * @returns scriptPubKey bytes.
 */
export function addressToScriptPubkey(address: string): Uint8Array {
  const { version, hash } = decodeCashAddr(address);

  const addrType = (version >> 3) & 0x01;

  if (addrType === 0) {
    // P2PKH: OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG
    const hashPush = pushData(hash);
    const result = new Uint8Array(2 + hashPush.length + 2);
    result[0] = OP_DUP;
    result[1] = OP_HASH160;
    result.set(hashPush, 2);
    result[2 + hashPush.length] = OP_EQUALVERIFY;
    result[3 + hashPush.length] = OP_CHECKSIG;
    return result;
  }

  // P2SH: OP_HASH160 <hash> OP_EQUAL
  return buildP2shScriptPubkey(hash);
}

// ---------------------------------------------------------------------------
// End-to-end P2SH wallet creation
// ---------------------------------------------------------------------------

/**
 * Create a P2SH multisig wallet address from owner and Qube public keys.
 *
 * This builds the asymmetric multisig redeem script, hashes it, and derives
 * the P2SH CashAddr address.
 *
 * @param ownerPubkeyHex - Owner's 33-byte compressed public key (hex).
 * @param qubePubkeyHex  - Qube's 33-byte compressed public key (hex).
 * @param network        - `"mainnet"` (default) or `"testnet"`.
 * @returns Object with `p2shAddress`, `redeemScript`, `redeemScriptHex`, and `scriptHash`.
 */
export function createWalletAddress(
  ownerPubkeyHex: string,
  qubePubkeyHex: string,
  network: string = 'mainnet',
): {
  p2shAddress: string;
  redeemScript: Uint8Array;
  redeemScriptHex: string;
  scriptHash: string;
} {
  const ownerPubkey = hexToBytes(ownerPubkeyHex);
  const qubePubkey = hexToBytes(qubePubkeyHex);

  // Build redeem script
  const redeemScript = buildAsymmetricMultisigScript(ownerPubkey, qubePubkey);

  // Derive P2SH address
  const p2shAddress = scriptToP2shAddress(redeemScript, network);

  // Script hash for verification
  const scriptHash = hash160(redeemScript);

  return {
    p2shAddress,
    redeemScript,
    redeemScriptHex: bytesToHex(redeemScript),
    scriptHash: bytesToHex(scriptHash),
  };
}
