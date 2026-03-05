/**
 * Tests for wallet/script — push data encoding, multisig script builder, P2SH scriptPubKey.
 */
import { describe, it, expect } from 'vitest';
import {
  pushData,
  buildAsymmetricMultisigScript,
  buildP2shScriptPubkey,
  OP_IF,
  OP_ELSE,
  OP_ENDIF,
  OP_2,
  OP_CHECKSIG,
  OP_CHECKMULTISIG,
  OP_HASH160,
  OP_EQUAL,
} from '../../src/wallet/script.js';

// ---------------------------------------------------------------------------
// pushData
// ---------------------------------------------------------------------------

describe('pushData', () => {
  it('encodes data <= 75 bytes with direct push prefix', () => {
    // 10 bytes of data
    const data = new Uint8Array(10).fill(0xab);
    const result = pushData(data);

    // First byte is length, then the data
    expect(result.length).toBe(1 + 10);
    expect(result[0]).toBe(10);
    expect(result.slice(1)).toEqual(data);
  });

  it('encodes exactly 75 bytes with direct push prefix', () => {
    const data = new Uint8Array(75).fill(0xff);
    const result = pushData(data);

    expect(result.length).toBe(1 + 75);
    expect(result[0]).toBe(75);
  });

  it('encodes 76 bytes with OP_PUSHDATA1', () => {
    const data = new Uint8Array(76).fill(0x01);
    const result = pushData(data);

    // OP_PUSHDATA1 (0x4c) + 1-byte length + data
    expect(result.length).toBe(2 + 76);
    expect(result[0]).toBe(0x4c);
    expect(result[1]).toBe(76);
    expect(result.slice(2)).toEqual(data);
  });

  it('encodes 200 bytes with OP_PUSHDATA1', () => {
    const data = new Uint8Array(200).fill(0x42);
    const result = pushData(data);

    expect(result.length).toBe(2 + 200);
    expect(result[0]).toBe(0x4c);
    expect(result[1]).toBe(200);
  });

  it('encodes 255 bytes with OP_PUSHDATA1', () => {
    const data = new Uint8Array(255).fill(0x99);
    const result = pushData(data);

    expect(result.length).toBe(2 + 255);
    expect(result[0]).toBe(0x4c);
    expect(result[1]).toBe(255);
  });

  it('encodes 256 bytes with OP_PUSHDATA2', () => {
    const data = new Uint8Array(256).fill(0xcc);
    const result = pushData(data);

    // OP_PUSHDATA2 (0x4d) + 2-byte LE length + data
    expect(result.length).toBe(3 + 256);
    expect(result[0]).toBe(0x4d);
    // 256 in LE = [0x00, 0x01]
    expect(result[1]).toBe(0x00);
    expect(result[2]).toBe(0x01);
  });

  it('encodes 1000 bytes with OP_PUSHDATA2', () => {
    const data = new Uint8Array(1000).fill(0x55);
    const result = pushData(data);

    expect(result.length).toBe(3 + 1000);
    expect(result[0]).toBe(0x4d);
    // 1000 = 0x03E8 -> LE [0xE8, 0x03]
    expect(result[1]).toBe(0xe8);
    expect(result[2]).toBe(0x03);
  });

  it('encodes empty data (0 bytes)', () => {
    const data = new Uint8Array(0);
    const result = pushData(data);

    expect(result.length).toBe(1);
    expect(result[0]).toBe(0);
  });

  it('throws for data larger than 65535 bytes', () => {
    const data = new Uint8Array(65536);
    expect(() => pushData(data)).toThrow('Data too large');
  });
});

// ---------------------------------------------------------------------------
// buildAsymmetricMultisigScript
// ---------------------------------------------------------------------------

describe('buildAsymmetricMultisigScript', () => {
  const ownerPubkey = new Uint8Array(33);
  ownerPubkey[0] = 0x02;
  ownerPubkey.fill(0xaa, 1);

  const qubePubkey = new Uint8Array(33);
  qubePubkey[0] = 0x03;
  qubePubkey.fill(0xbb, 1);

  it('produces correct script structure with expected opcodes', () => {
    const script = buildAsymmetricMultisigScript(ownerPubkey, qubePubkey);

    // Expected layout:
    // OP_IF(1) + push(33-byte owner) + OP_CHECKSIG(1)
    // + OP_ELSE(1) + OP_2(1) + push(33-byte owner) + push(33-byte qube) + OP_2(1) + OP_CHECKMULTISIG(1)
    // + OP_ENDIF(1)
    // push(33) = 1 + 33 = 34 bytes
    const pushLen = 1 + 33; // direct push for 33-byte data
    const expectedLen = 1 + pushLen + 1 + 1 + 1 + pushLen + pushLen + 1 + 1 + 1;
    expect(script.length).toBe(expectedLen);

    // Check opcodes at known positions
    let offset = 0;
    expect(script[offset]).toBe(OP_IF);
    offset += 1;

    // owner pubkey push: [33] + 33 bytes
    expect(script[offset]).toBe(33);
    offset += 1 + 33;

    expect(script[offset]).toBe(OP_CHECKSIG);
    offset += 1;

    expect(script[offset]).toBe(OP_ELSE);
    offset += 1;

    expect(script[offset]).toBe(OP_2);
    offset += 1;

    // owner pubkey push again
    expect(script[offset]).toBe(33);
    offset += 1 + 33;

    // qube pubkey push
    expect(script[offset]).toBe(33);
    offset += 1 + 33;

    expect(script[offset]).toBe(OP_2);
    offset += 1;

    expect(script[offset]).toBe(OP_CHECKMULTISIG);
    offset += 1;

    expect(script[offset]).toBe(OP_ENDIF);
    offset += 1;

    expect(offset).toBe(script.length);
  });

  it('rejects owner pubkey that is not 33 bytes', () => {
    const badOwner = new Uint8Array(32);
    expect(() => buildAsymmetricMultisigScript(badOwner, qubePubkey))
      .toThrow('Owner pubkey must be 33 bytes');
  });

  it('rejects qube pubkey that is not 33 bytes', () => {
    const badQube = new Uint8Array(65);
    expect(() => buildAsymmetricMultisigScript(ownerPubkey, badQube))
      .toThrow('Qube pubkey must be 33 bytes');
  });

  it('produces a deterministic script for the same inputs', () => {
    const script1 = buildAsymmetricMultisigScript(ownerPubkey, qubePubkey);
    const script2 = buildAsymmetricMultisigScript(ownerPubkey, qubePubkey);
    expect(script1).toEqual(script2);
  });
});

// ---------------------------------------------------------------------------
// buildP2shScriptPubkey
// ---------------------------------------------------------------------------

describe('buildP2shScriptPubkey', () => {
  it('produces correct OP_HASH160 <hash> OP_EQUAL script', () => {
    const scriptHash = new Uint8Array(20).fill(0xde);
    const result = buildP2shScriptPubkey(scriptHash);

    // OP_HASH160(1) + push(20-byte hash) + OP_EQUAL(1)
    // push(20) = 1 + 20 = 21
    expect(result.length).toBe(1 + 21 + 1);
    expect(result[0]).toBe(OP_HASH160);
    expect(result[1]).toBe(20); // push length byte
    expect(result.slice(2, 22)).toEqual(scriptHash);
    expect(result[22]).toBe(OP_EQUAL);
  });

  it('rejects script hash that is not 20 bytes', () => {
    const badHash = new Uint8Array(16);
    expect(() => buildP2shScriptPubkey(badHash))
      .toThrow('Script hash must be 20 bytes');
  });
});
