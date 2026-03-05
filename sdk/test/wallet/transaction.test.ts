/**
 * Tests for wallet/transaction — varInt encoding, outpoint serialization,
 * tx size estimation, fee calculation.
 */
import { describe, it, expect } from 'vitest';
import { hexToBytes, bytesToHex } from '@noble/hashes/utils';
import {
  varInt,
  serializeOutpoint,
  estimateTxSize,
  calculateFee,
} from '../../src/wallet/transaction.js';

// ---------------------------------------------------------------------------
// varInt encoding
// ---------------------------------------------------------------------------

describe('varInt', () => {
  it('encodes 0 as a single byte', () => {
    const result = varInt(0);
    expect(result).toEqual(new Uint8Array([0]));
  });

  it('encodes values < 0xFD as a single byte', () => {
    expect(varInt(1)).toEqual(new Uint8Array([1]));
    expect(varInt(100)).toEqual(new Uint8Array([100]));
    expect(varInt(0xfc)).toEqual(new Uint8Array([0xfc]));
  });

  it('encodes 0xFD as 0xFD + LE16', () => {
    const result = varInt(0xfd);
    expect(result.length).toBe(3);
    expect(result[0]).toBe(0xfd);
    expect(result[1]).toBe(0xfd);
    expect(result[2]).toBe(0x00);
  });

  it('encodes 0xFFFF as 0xFD + LE16', () => {
    const result = varInt(0xffff);
    expect(result.length).toBe(3);
    expect(result[0]).toBe(0xfd);
    expect(result[1]).toBe(0xff);
    expect(result[2]).toBe(0xff);
  });

  it('encodes 256 as 0xFD + LE16', () => {
    const result = varInt(256);
    expect(result.length).toBe(3);
    expect(result[0]).toBe(0xfd);
    // 256 = 0x0100 -> LE [0x00, 0x01]
    expect(result[1]).toBe(0x00);
    expect(result[2]).toBe(0x01);
  });

  it('encodes 0x10000 as 0xFE + LE32', () => {
    const result = varInt(0x10000);
    expect(result.length).toBe(5);
    expect(result[0]).toBe(0xfe);
    // 0x10000 in LE = [0x00, 0x00, 0x01, 0x00]
    expect(result[1]).toBe(0x00);
    expect(result[2]).toBe(0x00);
    expect(result[3]).toBe(0x01);
    expect(result[4]).toBe(0x00);
  });

  it('encodes 0xFFFFFFFF as 0xFE + LE32', () => {
    const result = varInt(0xffffffff);
    expect(result.length).toBe(5);
    expect(result[0]).toBe(0xfe);
    expect(result[1]).toBe(0xff);
    expect(result[2]).toBe(0xff);
    expect(result[3]).toBe(0xff);
    expect(result[4]).toBe(0xff);
  });
});

// ---------------------------------------------------------------------------
// serializeOutpoint
// ---------------------------------------------------------------------------

describe('serializeOutpoint', () => {
  it('produces 36 bytes (32 txid + 4 vout)', () => {
    const txid = 'aa'.repeat(32);
    const result = serializeOutpoint(txid, 0);
    expect(result.length).toBe(36);
  });

  it('reverses the txid from big-endian to little-endian', () => {
    // txid as big-endian hex: first byte = 0x01, last byte = 0x20 (32 bytes)
    const txidBytes = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
      txidBytes[i] = i + 1;
    }
    const txidHex = bytesToHex(txidBytes);

    const result = serializeOutpoint(txidHex, 0);

    // First 32 bytes should be reversed
    for (let i = 0; i < 32; i++) {
      expect(result[i]).toBe(txidBytes[31 - i]);
    }
  });

  it('encodes vout in little-endian at offset 32', () => {
    const txid = '00'.repeat(32);
    const result = serializeOutpoint(txid, 1);

    // vout = 1 in LE at offset 32
    expect(result[32]).toBe(1);
    expect(result[33]).toBe(0);
    expect(result[34]).toBe(0);
    expect(result[35]).toBe(0);
  });

  it('handles vout > 255 correctly', () => {
    const txid = '00'.repeat(32);
    const result = serializeOutpoint(txid, 300);

    // 300 = 0x012C -> LE [0x2C, 0x01, 0x00, 0x00]
    expect(result[32]).toBe(0x2c);
    expect(result[33]).toBe(0x01);
    expect(result[34]).toBe(0x00);
    expect(result[35]).toBe(0x00);
  });
});

// ---------------------------------------------------------------------------
// estimateTxSize
// ---------------------------------------------------------------------------

describe('estimateTxSize', () => {
  it('returns a positive number for owner_only path', () => {
    const size = estimateTxSize(1, 2, 'owner_only');
    expect(size).toBeGreaterThan(0);
  });

  it('returns a positive number for multisig path', () => {
    const size = estimateTxSize(1, 2, 'multisig');
    expect(size).toBeGreaterThan(0);
  });

  it('multisig is larger than owner_only for same inputs/outputs', () => {
    const ownerSize = estimateTxSize(1, 2, 'owner_only');
    const multiSize = estimateTxSize(1, 2, 'multisig');
    expect(multiSize).toBeGreaterThan(ownerSize);
  });

  it('size increases with more inputs', () => {
    const size1 = estimateTxSize(1, 1, 'owner_only');
    const size2 = estimateTxSize(2, 1, 'owner_only');
    expect(size2).toBeGreaterThan(size1);
  });

  it('size increases with more outputs', () => {
    const size1 = estimateTxSize(1, 1, 'owner_only');
    const size2 = estimateTxSize(1, 3, 'owner_only');
    expect(size2).toBeGreaterThan(size1);
  });

  it('returns reasonable size for a typical 1-in-2-out transaction', () => {
    const size = estimateTxSize(1, 2, 'owner_only');
    // Should be in the 150-350 byte range for a typical P2SH tx
    expect(size).toBeGreaterThan(100);
    expect(size).toBeLessThan(500);
  });
});

// ---------------------------------------------------------------------------
// calculateFee
// ---------------------------------------------------------------------------

describe('calculateFee', () => {
  it('returns txSize * 1 for default fee rate', () => {
    expect(calculateFee(200)).toBe(200);
  });

  it('returns txSize * feePerByte for custom rate', () => {
    expect(calculateFee(200, 2)).toBe(400);
    expect(calculateFee(150, 3)).toBe(450);
  });

  it('returns 0 for zero-size transaction', () => {
    expect(calculateFee(0)).toBe(0);
  });

  it('returns 0 for zero fee rate', () => {
    expect(calculateFee(200, 0)).toBe(0);
  });
});
