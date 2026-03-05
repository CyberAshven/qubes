/**
 * Tests for blocks/block — QubeBlock constructor, toDict, computeHash, fromDict.
 */
import { describe, it, expect } from 'vitest';
import { QubeBlock } from '../../src/blocks/block.js';

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

describe('QubeBlock constructor', () => {
  it('auto-sets timestamp if not provided', () => {
    const before = Math.floor(Date.now() / 1000);
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ABCD1234',
    });
    const after = Math.floor(Date.now() / 1000);

    expect(block.timestamp).toBeGreaterThanOrEqual(before);
    expect(block.timestamp).toBeLessThanOrEqual(after);
  });

  it('preserves an explicit timestamp', () => {
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ABCD1234',
      timestamp: 1700000000,
    });
    expect(block.timestamp).toBe(1700000000);
  });

  it('exposes core field getters', () => {
    const block = new QubeBlock({
      block_type: 'MESSAGE',
      block_number: 5,
      qube_id: 'DEADBEEF',
      timestamp: 1000,
      content: { message_body: 'hello' },
      encrypted: true,
      temporary: false,
    });

    expect(block.blockType).toBe('MESSAGE');
    expect(block.blockNumber).toBe(5);
    expect(block.qubeId).toBe('DEADBEEF');
    expect(block.timestamp).toBe(1000);
    expect(block.content).toEqual({ message_body: 'hello' });
    expect(block.encrypted).toBe(true);
    expect(block.temporary).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// toDict
// ---------------------------------------------------------------------------

describe('QubeBlock.toDict()', () => {
  it('excludes null values', () => {
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 0,
      qube_id: 'ID',
      previous_hash: null,
      block_hash: null,
      timestamp: 1000,
    });

    const dict = block.toDict();
    expect(dict).not.toHaveProperty('previous_hash');
    expect(dict).not.toHaveProperty('block_hash');
  });

  it('excludes undefined values', () => {
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 0,
      qube_id: 'ID',
      signature: undefined,
      timestamp: 1000,
    });

    const dict = block.toDict();
    expect(dict).not.toHaveProperty('signature');
  });

  it('includes non-null/non-undefined values', () => {
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 0,
      qube_id: 'ID',
      encrypted: false,
      temporary: true,
      timestamp: 1000,
    });

    const dict = block.toDict();
    expect(dict.block_type).toBe('TEST');
    expect(dict.block_number).toBe(0);
    expect(dict.encrypted).toBe(false);
    expect(dict.temporary).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// computeHash
// ---------------------------------------------------------------------------

describe('QubeBlock.computeHash()', () => {
  it('produces a 64-character lowercase hex hash', () => {
    const block = new QubeBlock({
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ABCD1234',
      timestamp: 1700000000,
      content: { key: 'value' },
      encrypted: false,
      temporary: false,
    });

    const hash = block.computeHash();
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('produces consistent hash for same data', () => {
    const data = {
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ABCD1234',
      timestamp: 1700000000,
      content: {},
      encrypted: false,
      temporary: false,
    };

    const block1 = new QubeBlock({ ...data });
    const block2 = new QubeBlock({ ...data });

    expect(block1.computeHash()).toBe(block2.computeHash());
  });

  it('excludes block_hash, signature, participant_signatures, content_hash from hash', () => {
    const base = {
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ID',
      timestamp: 1000,
      content: {},
      encrypted: false,
      temporary: false,
    };

    const block1 = new QubeBlock({ ...base });
    const block2 = new QubeBlock({
      ...base,
      block_hash: 'some_hash',
      signature: 'some_sig',
      participant_signatures: { q1: 'sig1' },
      content_hash: 'some_content_hash',
    });

    // Both should produce the same hash since those fields are excluded
    expect(block1.computeHash()).toBe(block2.computeHash());
  });

  it('changes hash when block data changes', () => {
    const block1 = new QubeBlock({
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ID',
      timestamp: 1000,
      content: { a: 1 },
      encrypted: false,
      temporary: false,
    });

    const block2 = new QubeBlock({
      block_type: 'TEST',
      block_number: 1,
      qube_id: 'ID',
      timestamp: 1000,
      content: { a: 2 },
      encrypted: false,
      temporary: false,
    });

    expect(block1.computeHash()).not.toBe(block2.computeHash());
  });
});

// ---------------------------------------------------------------------------
// fromDict round-trip
// ---------------------------------------------------------------------------

describe('QubeBlock.fromDict()', () => {
  it('creates a QubeBlock from a dict', () => {
    const data = {
      block_type: 'MESSAGE',
      block_number: 10,
      qube_id: 'QUBE0001',
      timestamp: 1700000000,
      content: { message_body: 'test' },
      encrypted: true,
      temporary: false,
    };

    const block = QubeBlock.fromDict(data);
    expect(block.blockType).toBe('MESSAGE');
    expect(block.blockNumber).toBe(10);
    expect(block.qubeId).toBe('QUBE0001');
  });

  it('round-trips through toDict() and fromDict()', () => {
    const data = {
      block_type: 'ACTION',
      block_number: 5,
      qube_id: 'DEADBEEF',
      timestamp: 1700000000,
      content: { action_type: 'web_search', parameters: { query: 'test' } },
      encrypted: true,
      temporary: false,
      previous_hash: 'a'.repeat(64),
    };

    const block1 = new QubeBlock(data);
    block1.blockHash = block1.computeHash();

    const dict = block1.toDict();
    const block2 = QubeBlock.fromDict(dict);

    expect(block2.blockType).toBe(block1.blockType);
    expect(block2.blockNumber).toBe(block1.blockNumber);
    expect(block2.qubeId).toBe(block1.qubeId);
    expect(block2.timestamp).toBe(block1.timestamp);
    expect(block2.blockHash).toBe(block1.blockHash);
    expect(block2.previousHash).toBe(block1.previousHash);
    expect(block2.content).toEqual(block1.content);
  });
});
