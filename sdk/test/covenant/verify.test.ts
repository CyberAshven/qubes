/**
 * Tests for covenant NFT verification utilities.
 *
 * Note: Actual Chaingraph queries are not tested here (would need mocking).
 * We test the addressToLockingBytecodeHex helper which is pure.
 */
import { describe, it, expect } from 'vitest';
import { addressToLockingBytecodeHex } from '../../src/covenant/verify.js';
import { pubkeyToCashAddress, pubkeyToTokenAddress } from '../../src/wallet/address.js';
import { scriptToP2shAddress } from '../../src/wallet/cashaddr.js';

const TEST_PUBKEY = '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2';

describe('addressToLockingBytecodeHex', () => {
  it('converts P2PKH address to OP_DUP OP_HASH160 ... OP_EQUALVERIFY OP_CHECKSIG', () => {
    const address = pubkeyToCashAddress(TEST_PUBKEY);
    const bytecode = addressToLockingBytecodeHex(address);

    expect(bytecode).toBeTruthy();
    // P2PKH: 76 a9 14 <20bytes> 88 ac = 25 bytes = 50 hex chars
    expect(bytecode).toHaveLength(50);
    expect(bytecode!.startsWith('76a914')).toBe(true);
    expect(bytecode!.endsWith('88ac')).toBe(true);
  });

  it('converts token-aware (z) address to same locking bytecode as standard (q)', () => {
    const qAddr = pubkeyToCashAddress(TEST_PUBKEY);
    const zAddr = pubkeyToTokenAddress(TEST_PUBKEY);

    const qBytecode = addressToLockingBytecodeHex(qAddr);
    const zBytecode = addressToLockingBytecodeHex(zAddr);

    // Token flag only affects the address encoding, not the locking bytecode
    expect(qBytecode).toBe(zBytecode);
  });

  it('converts P2SH address to OP_HASH160 ... OP_EQUAL', () => {
    const script = new Uint8Array(33).fill(0xab);
    const p2shAddr = scriptToP2shAddress(script);
    const bytecode = addressToLockingBytecodeHex(p2shAddr);

    expect(bytecode).toBeTruthy();
    // P2SH-20: a9 14 <20bytes> 87 = 23 bytes = 46 hex chars
    expect(bytecode).toHaveLength(46);
    expect(bytecode!.startsWith('a914')).toBe(true);
    expect(bytecode!.endsWith('87')).toBe(true);
  });

  it('returns null for invalid address', () => {
    expect(addressToLockingBytecodeHex('not-an-address')).toBeNull();
  });
});
