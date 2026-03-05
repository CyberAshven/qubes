/**
 * Tests for wallet/cashaddr — CashAddr encoding, decoding, round-trip, and scriptToP2shAddress.
 */
import { describe, it, expect } from 'vitest';
import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { hexToBytes } from '@noble/hashes/utils';
import {
  encodeCashAddr,
  decodeCashAddr,
  scriptToP2shAddress,
  convertBits,
  cashAddrPolymod,
  cashAddrHrpExpand,
  createChecksum,
} from '../../src/wallet/cashaddr.js';

// ---------------------------------------------------------------------------
// encodeCashAddr / decodeCashAddr round-trip
// ---------------------------------------------------------------------------

describe('encodeCashAddr / decodeCashAddr round-trip', () => {
  it('round-trips a P2PKH address (version 0x00)', () => {
    const hash = new Uint8Array(20).fill(0x42);
    const addr = encodeCashAddr('bitcoincash', 0x00, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.version).toBe(0x00);
    expect(decoded.hash).toEqual(hash);
  });

  it('round-trips a P2SH address (version 0x08)', () => {
    const hash = new Uint8Array(20).fill(0xab);
    const addr = encodeCashAddr('bitcoincash', 0x08, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.version).toBe(0x08);
    expect(decoded.hash).toEqual(hash);
  });

  it('round-trips a token-aware P2PKH address (version 0x10)', () => {
    const hash = new Uint8Array(20).fill(0xff);
    const addr = encodeCashAddr('bitcoincash', 0x10, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.version).toBe(0x10);
    expect(decoded.hash).toEqual(hash);
  });

  it('round-trips a testnet address', () => {
    const hash = new Uint8Array(20).fill(0x01);
    const addr = encodeCashAddr('bchtest', 0x00, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.prefix).toBe('bchtest');
    expect(decoded.version).toBe(0x00);
    expect(decoded.hash).toEqual(hash);
  });

  it('round-trips with random byte hash', () => {
    // Deterministic pseudo-random hash via sha256
    const seed = new Uint8Array([1, 2, 3, 4, 5]);
    const hash = ripemd160(sha256(seed));
    const addr = encodeCashAddr('bitcoincash', 0x00, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.hash).toEqual(hash);
  });
});

// ---------------------------------------------------------------------------
// scriptToP2shAddress
// ---------------------------------------------------------------------------

describe('scriptToP2shAddress', () => {
  it('produces a valid bitcoincash:p... address from a script', () => {
    // Use a dummy 76-byte redeem script
    const script = new Uint8Array(76).fill(0x63);
    const addr = scriptToP2shAddress(script);

    expect(addr.startsWith('bitcoincash:p')).toBe(true);

    // Decode and verify version byte is P2SH (0x08)
    const decoded = decodeCashAddr(addr);
    expect(decoded.version).toBe(0x08);
    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.hash.length).toBe(20);
  });

  it('produces a testnet p... address when network is testnet', () => {
    const script = new Uint8Array(50).fill(0x01);
    const addr = scriptToP2shAddress(script, 'testnet');

    expect(addr.startsWith('bchtest:p')).toBe(true);
  });

  it('produces deterministic address for same script', () => {
    const script = new Uint8Array(40).fill(0xaa);
    const addr1 = scriptToP2shAddress(script);
    const addr2 = scriptToP2shAddress(script);
    expect(addr1).toBe(addr2);
  });
});

// ---------------------------------------------------------------------------
// decodeCashAddr handles with and without prefix
// ---------------------------------------------------------------------------

describe('decodeCashAddr prefix handling', () => {
  it('decodes address with explicit prefix', () => {
    const hash = new Uint8Array(20).fill(0x55);
    const addr = encodeCashAddr('bitcoincash', 0x00, hash);
    const decoded = decodeCashAddr(addr);

    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.hash).toEqual(hash);
  });

  it('decodes address without prefix (assumes bitcoincash)', () => {
    const hash = new Uint8Array(20).fill(0x77);
    const addr = encodeCashAddr('bitcoincash', 0x00, hash);
    // Strip the prefix
    const withoutPrefix = addr.split(':')[1];
    const decoded = decodeCashAddr(withoutPrefix);

    expect(decoded.prefix).toBe('bitcoincash');
    expect(decoded.hash).toEqual(hash);
  });

  it('throws on invalid characters', () => {
    expect(() => decodeCashAddr('bitcoincash:INVALID!')).toThrow();
  });
});

// ---------------------------------------------------------------------------
// Known test vector: pubkey -> deterministic P2PKH address
// ---------------------------------------------------------------------------

describe('known test vector', () => {
  it('produces a deterministic P2PKH address from a known public key', () => {
    // BIP32 test vector public key
    const pubkeyHex = '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2';
    const pubkeyBytes = hexToBytes(pubkeyHex);

    // Compute HASH160(pubkey)
    const pubkeyHash = ripemd160(sha256(pubkeyBytes));

    // Encode as P2PKH CashAddr (version 0x00)
    const addr = encodeCashAddr('bitcoincash', 0x00, pubkeyHash);

    // The address should start with "bitcoincash:q"
    expect(addr.startsWith('bitcoincash:q')).toBe(true);

    // Decode and verify round-trip
    const decoded = decodeCashAddr(addr);
    expect(decoded.version).toBe(0x00);
    expect(decoded.hash).toEqual(pubkeyHash);

    // The address should be deterministic
    const addr2 = encodeCashAddr('bitcoincash', 0x00, pubkeyHash);
    expect(addr).toBe(addr2);
  });
});

// ---------------------------------------------------------------------------
// convertBits
// ---------------------------------------------------------------------------

describe('convertBits', () => {
  it('converts 8-bit to 5-bit and back', () => {
    const original = new Uint8Array([0xff, 0x00, 0xab, 0xcd]);
    const fiveBit = convertBits(original, 8, 5, true);
    const backToEight = convertBits(fiveBit, 5, 8, false);

    // The round-trip should recover original bytes
    for (let i = 0; i < original.length; i++) {
      expect(backToEight[i]).toBe(original[i]);
    }
  });
});
