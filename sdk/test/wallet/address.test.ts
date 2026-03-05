/**
 * Tests for wallet/address — P2PKH/token address derivation, q/z conversion,
 * createWalletAddress, addressToScriptPubkey.
 */
import { describe, it, expect } from 'vitest';
import { hexToBytes } from '@noble/hashes/utils';
import {
  pubkeyToP2pkhAddress,
  pubkeyToTokenAddress,
  pubkeyToCashAddress,
  cashAddressToTokenAddress,
  tokenAddressToCashAddress,
  addressToScriptPubkey,
  createWalletAddress,
} from '../../src/wallet/address.js';
import { decodeCashAddr } from '../../src/wallet/cashaddr.js';
import {
  OP_DUP,
  OP_HASH160,
  OP_EQUALVERIFY,
  OP_CHECKSIG,
  OP_EQUAL,
} from '../../src/wallet/script.js';

// A well-known compressed public key (BIP32 test vector)
const TEST_PUBKEY = '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2';

// Two 33-byte compressed pubkeys for wallet tests
const OWNER_PUBKEY = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const QUBE_PUBKEY  = '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2';

// ---------------------------------------------------------------------------
// pubkeyToP2pkhAddress
// ---------------------------------------------------------------------------

describe('pubkeyToP2pkhAddress', () => {
  it('produces a bitcoincash:q... address for standard P2PKH', () => {
    const addr = pubkeyToP2pkhAddress(TEST_PUBKEY);
    expect(addr.startsWith('bitcoincash:q')).toBe(true);
  });

  it('produces a deterministic address', () => {
    const addr1 = pubkeyToP2pkhAddress(TEST_PUBKEY);
    const addr2 = pubkeyToP2pkhAddress(TEST_PUBKEY);
    expect(addr1).toBe(addr2);
  });

  it('decodes to version 0x00 (P2PKH)', () => {
    const addr = pubkeyToP2pkhAddress(TEST_PUBKEY);
    const decoded = decodeCashAddr(addr);
    expect(decoded.version).toBe(0x00);
    expect(decoded.hash.length).toBe(20);
  });

  it('rejects non-33-byte pubkey', () => {
    const badPubkey = 'aabbcc'; // 3 bytes
    expect(() => pubkeyToP2pkhAddress(badPubkey)).toThrow('33 bytes');
  });
});

// ---------------------------------------------------------------------------
// pubkeyToTokenAddress
// ---------------------------------------------------------------------------

describe('pubkeyToTokenAddress', () => {
  it('produces a bitcoincash:z... address', () => {
    const addr = pubkeyToTokenAddress(TEST_PUBKEY);
    expect(addr.startsWith('bitcoincash:z')).toBe(true);
  });

  it('decodes to version 0x10 (token-aware P2PKH)', () => {
    const addr = pubkeyToTokenAddress(TEST_PUBKEY);
    const decoded = decodeCashAddr(addr);
    expect(decoded.version).toBe(0x10);
  });
});

// ---------------------------------------------------------------------------
// cashAddressToTokenAddress (q -> z)
// ---------------------------------------------------------------------------

describe('cashAddressToTokenAddress', () => {
  it('converts a q address to a z address', () => {
    const qAddr = pubkeyToCashAddress(TEST_PUBKEY);
    const zAddr = cashAddressToTokenAddress(qAddr);

    expect(qAddr.startsWith('bitcoincash:q')).toBe(true);
    expect(zAddr.startsWith('bitcoincash:z')).toBe(true);
  });

  it('preserves the same hash when converting q -> z', () => {
    const qAddr = pubkeyToCashAddress(TEST_PUBKEY);
    const zAddr = cashAddressToTokenAddress(qAddr);

    const qDecoded = decodeCashAddr(qAddr);
    const zDecoded = decodeCashAddr(zAddr);

    expect(zDecoded.hash).toEqual(qDecoded.hash);
  });

  it('returns same address if already token-aware', () => {
    const zAddr = pubkeyToTokenAddress(TEST_PUBKEY);
    const result = cashAddressToTokenAddress(zAddr);
    expect(result).toBe(zAddr);
  });
});

// ---------------------------------------------------------------------------
// tokenAddressToCashAddress (z -> q)
// ---------------------------------------------------------------------------

describe('tokenAddressToCashAddress', () => {
  it('converts a z address to a q address', () => {
    const zAddr = pubkeyToTokenAddress(TEST_PUBKEY);
    const qAddr = tokenAddressToCashAddress(zAddr);

    expect(zAddr.startsWith('bitcoincash:z')).toBe(true);
    expect(qAddr.startsWith('bitcoincash:q')).toBe(true);
  });

  it('preserves the same hash when converting z -> q', () => {
    const zAddr = pubkeyToTokenAddress(TEST_PUBKEY);
    const qAddr = tokenAddressToCashAddress(zAddr);

    const zDecoded = decodeCashAddr(zAddr);
    const qDecoded = decodeCashAddr(qAddr);

    expect(qDecoded.hash).toEqual(zDecoded.hash);
  });
});

// ---------------------------------------------------------------------------
// Round-trip: pubkey -> q -> z -> q
// ---------------------------------------------------------------------------

describe('address round-trip', () => {
  it('pubkey -> q address -> z address -> q address produces original', () => {
    const qAddr = pubkeyToCashAddress(TEST_PUBKEY);
    const zAddr = cashAddressToTokenAddress(qAddr);
    const qAddrBack = tokenAddressToCashAddress(zAddr);

    expect(qAddrBack).toBe(qAddr);
  });
});

// ---------------------------------------------------------------------------
// createWalletAddress
// ---------------------------------------------------------------------------

describe('createWalletAddress', () => {
  it('produces a valid P2SH address (bitcoincash:p...)', () => {
    const result = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY);

    expect(result.p2shAddress.startsWith('bitcoincash:p')).toBe(true);

    // Verify the P2SH version byte
    const decoded = decodeCashAddr(result.p2shAddress);
    expect(decoded.version).toBe(0x08);
  });

  it('returns redeemScript, redeemScriptHex, and scriptHash', () => {
    const result = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY);

    expect(result.redeemScript).toBeInstanceOf(Uint8Array);
    expect(result.redeemScript.length).toBeGreaterThan(0);
    expect(typeof result.redeemScriptHex).toBe('string');
    expect(result.redeemScriptHex.length).toBe(result.redeemScript.length * 2);
    expect(typeof result.scriptHash).toBe('string');
    expect(result.scriptHash.length).toBe(40); // 20 bytes = 40 hex chars
  });

  it('is deterministic for same inputs', () => {
    const result1 = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY);
    const result2 = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY);

    expect(result1.p2shAddress).toBe(result2.p2shAddress);
    expect(result1.redeemScriptHex).toBe(result2.redeemScriptHex);
    expect(result1.scriptHash).toBe(result2.scriptHash);
  });

  it('produces testnet address when specified', () => {
    const result = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY, 'testnet');
    expect(result.p2shAddress.startsWith('bchtest:p')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// addressToScriptPubkey
// ---------------------------------------------------------------------------

describe('addressToScriptPubkey', () => {
  it('produces P2PKH scriptPubkey for a q address', () => {
    const addr = pubkeyToCashAddress(TEST_PUBKEY);
    const script = addressToScriptPubkey(addr);

    // P2PKH: OP_DUP OP_HASH160 <20-byte hash> OP_EQUALVERIFY OP_CHECKSIG
    // = 1 + 1 + (1 + 20) + 1 + 1 = 25 bytes
    expect(script.length).toBe(25);
    expect(script[0]).toBe(OP_DUP);
    expect(script[1]).toBe(OP_HASH160);
    expect(script[2]).toBe(20); // push data length
    expect(script[23]).toBe(OP_EQUALVERIFY);
    expect(script[24]).toBe(OP_CHECKSIG);
  });

  it('produces P2SH scriptPubkey for a p address', () => {
    const wallet = createWalletAddress(OWNER_PUBKEY, QUBE_PUBKEY);
    const script = addressToScriptPubkey(wallet.p2shAddress);

    // P2SH: OP_HASH160 <20-byte hash> OP_EQUAL
    // = 1 + (1 + 20) + 1 = 23 bytes
    expect(script.length).toBe(23);
    expect(script[0]).toBe(OP_HASH160);
    expect(script[1]).toBe(20); // push data length
    expect(script[22]).toBe(OP_EQUAL);
  });

  it('P2PKH script hash matches the address hash', () => {
    const addr = pubkeyToCashAddress(TEST_PUBKEY);
    const decoded = decodeCashAddr(addr);
    const script = addressToScriptPubkey(addr);

    // Extract the 20-byte hash from the script (bytes 3-22)
    const scriptHash = script.slice(3, 23);
    expect(scriptHash).toEqual(decoded.hash);
  });
});
