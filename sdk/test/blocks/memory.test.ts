/**
 * Tests for blocks/memory — all 10 block type factories.
 */
import { describe, it, expect } from 'vitest';
import {
  createThoughtBlock,
  createActionBlock,
  createObservationBlock,
  createMessageBlock,
  createDecisionBlock,
  createMemoryAnchorBlock,
  createCollaborativeMemoryBlock,
  createSummaryBlock,
  createGameBlock,
  createLearningBlock,
  VALID_LEARNING_TYPES,
} from '../../src/blocks/memory.js';

const COMMON_PERMANENT = {
  qubeId: 'ABCD1234',
  blockNumber: 5,
  previousHash: 'a'.repeat(64),
  temporary: false,
};

const COMMON_SESSION = {
  qubeId: 'ABCD1234',
  blockNumber: -1,
  previousBlockNumber: 4,
  temporary: true,
  sessionId: 'session_001',
};

// ---------------------------------------------------------------------------
// Each factory produces correct block_type
// ---------------------------------------------------------------------------

describe('block type factories produce correct block_type', () => {
  it('THOUGHT block', () => {
    const block = createThoughtBlock(COMMON_PERMANENT);
    expect(block.blockType).toBe('THOUGHT');
  });

  it('ACTION block', () => {
    const block = createActionBlock(COMMON_PERMANENT);
    expect(block.blockType).toBe('ACTION');
  });

  it('OBSERVATION block', () => {
    const block = createObservationBlock(COMMON_PERMANENT);
    expect(block.blockType).toBe('OBSERVATION');
  });

  it('MESSAGE block', () => {
    const block = createMessageBlock(COMMON_PERMANENT);
    expect(block.blockType).toBe('MESSAGE');
  });

  it('DECISION block', () => {
    const block = createDecisionBlock(COMMON_PERMANENT);
    expect(block.blockType).toBe('DECISION');
  });

  it('MEMORY_ANCHOR block', () => {
    const block = createMemoryAnchorBlock({
      qubeId: 'ABCD1234',
      blockNumber: 5,
      previousHash: 'a'.repeat(64),
      merkleRoot: 'b'.repeat(64),
      blockRange: [1, 4],
      totalBlocks: 4,
    });
    expect(block.blockType).toBe('MEMORY_ANCHOR');
  });

  it('COLLABORATIVE_MEMORY block', () => {
    const block = createCollaborativeMemoryBlock({
      ...COMMON_PERMANENT,
      eventDescription: 'shared event',
      participants: ['Q1', 'Q2'],
      sharedDataHash: 'c'.repeat(64),
      contributionWeights: { Q1: 0.5, Q2: 0.5 },
      signatures: { Q1: 'sig1', Q2: 'sig2' },
    });
    expect(block.blockType).toBe('COLLABORATIVE_MEMORY');
  });

  it('SUMMARY block', () => {
    const block = createSummaryBlock({
      qubeId: 'ABCD1234',
      blockNumber: 5,
      previousHash: 'a'.repeat(64),
      summarizedBlocks: [1, 2, 3],
      blockCount: 3,
      timePeriod: { start: 1000, end: 2000 },
      summaryText: 'A summary of events.',
    });
    expect(block.blockType).toBe('SUMMARY');
  });

  it('GAME block', () => {
    const block = createGameBlock({
      qubeId: 'ABCD1234',
      blockNumber: 5,
      previousHash: 'a'.repeat(64),
      gameId: 'game_001',
      gameType: 'chess',
      whitePlayer: { id: 'user1', type: 'human' },
      blackPlayer: { id: 'Q1', type: 'qube' },
      result: '1-0',
      termination: 'checkmate',
      totalMoves: 40,
      pgn: '1. e4 e5 2. Nf3 ...',
      durationSeconds: 600,
      xpEarned: 100,
    });
    expect(block.blockType).toBe('GAME');
  });

  it('LEARNING block', () => {
    const block = createLearningBlock({
      qubeId: 'ABCD1234',
      blockNumber: 5,
      previousHash: 'a'.repeat(64),
      learningType: 'fact',
      contentData: { knowledge: 'The sky is blue.' },
    });
    expect(block.blockType).toBe('LEARNING');
  });
});

// ---------------------------------------------------------------------------
// Session blocks don't have block_hash
// ---------------------------------------------------------------------------

describe('session blocks', () => {
  it('THOUGHT session block has no block_hash', () => {
    const block = createThoughtBlock(COMMON_SESSION);
    expect(block.blockHash).toBeNull();
    expect(block.temporary).toBe(true);
  });

  it('ACTION session block has no block_hash', () => {
    const block = createActionBlock(COMMON_SESSION);
    expect(block.blockHash).toBeNull();
    expect(block.temporary).toBe(true);
  });

  it('MESSAGE session block has no block_hash', () => {
    const block = createMessageBlock(COMMON_SESSION);
    expect(block.blockHash).toBeNull();
    expect(block.temporary).toBe(true);
  });

  it('session block toDict() includes session_id and previous_block_number', () => {
    const block = createThoughtBlock(COMMON_SESSION);
    const dict = block.toDict();

    expect(dict.session_id).toBe('session_001');
    expect(dict.previous_block_number).toBe(4);
    expect(dict).not.toHaveProperty('previous_hash');
  });
});

// ---------------------------------------------------------------------------
// Permanent blocks have computed block_hash
// ---------------------------------------------------------------------------

describe('permanent blocks', () => {
  it('THOUGHT permanent block has block_hash', () => {
    const block = createThoughtBlock(COMMON_PERMANENT);
    expect(block.blockHash).toBeTruthy();
    expect(block.blockHash).toHaveLength(64);
    expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
    expect(block.temporary).toBe(false);
  });

  it('ACTION permanent block has block_hash', () => {
    const block = createActionBlock(COMMON_PERMANENT);
    expect(block.blockHash).toBeTruthy();
    expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('MESSAGE permanent block has block_hash', () => {
    const block = createMessageBlock(COMMON_PERMANENT);
    expect(block.blockHash).toBeTruthy();
    expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('permanent block toDict() includes previous_hash', () => {
    const block = createThoughtBlock(COMMON_PERMANENT);
    const dict = block.toDict();

    expect(dict.previous_hash).toBe('a'.repeat(64));
    expect(dict).not.toHaveProperty('session_id');
  });

  it('block_hash matches computeHash()', () => {
    const block = createActionBlock(COMMON_PERMANENT);
    expect(block.blockHash).toBe(block.computeHash());
  });
});

// ---------------------------------------------------------------------------
// createLearningBlock rejects invalid learning types
// ---------------------------------------------------------------------------

describe('createLearningBlock validation', () => {
  it('accepts all valid learning types', () => {
    for (const lt of VALID_LEARNING_TYPES) {
      expect(() =>
        createLearningBlock({
          qubeId: 'Q1',
          blockNumber: 1,
          previousHash: 'a'.repeat(64),
          learningType: lt,
          contentData: {},
        }),
      ).not.toThrow();
    }
  });

  it('rejects invalid learning type', () => {
    expect(() =>
      createLearningBlock({
        qubeId: 'Q1',
        blockNumber: 1,
        previousHash: 'a'.repeat(64),
        learningType: 'invalid_type',
        contentData: {},
      }),
    ).toThrow('Invalid learning_type');
  });

  it('rejects empty learning type', () => {
    expect(() =>
      createLearningBlock({
        qubeId: 'Q1',
        blockNumber: 1,
        previousHash: 'a'.repeat(64),
        learningType: '',
        contentData: {},
      }),
    ).toThrow('Invalid learning_type');
  });
});

// ---------------------------------------------------------------------------
// createMemoryAnchorBlock is always permanent and unencrypted
// ---------------------------------------------------------------------------

describe('createMemoryAnchorBlock', () => {
  const anchorParams = {
    qubeId: 'ABCD1234',
    blockNumber: 10,
    previousHash: 'a'.repeat(64),
    merkleRoot: 'b'.repeat(64),
    blockRange: [1, 9] as [number, number],
    totalBlocks: 9,
  };

  it('is always permanent (temporary = false)', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    expect(block.temporary).toBe(false);
  });

  it('is always unencrypted (encrypted = false)', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    expect(block.encrypted).toBe(false);
  });

  it('has a computed block_hash', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    expect(block.blockHash).toBeTruthy();
    expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('stores merkle_root at block level', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    expect(block.merkleRoot).toBe('b'.repeat(64));
  });

  it('stores merkle_root in content', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    const content = block.content!;
    expect(content.merkle_root).toBe('b'.repeat(64));
  });

  it('stores block_range and total_blocks in content', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    const content = block.content!;
    expect(content.block_range).toEqual([1, 9]);
    expect(content.total_blocks).toBe(9);
  });

  it('defaults anchor_type to "periodic"', () => {
    const block = createMemoryAnchorBlock(anchorParams);
    const content = block.content!;
    expect(content.anchor_type).toBe('periodic');
  });
});

// ---------------------------------------------------------------------------
// Additional factory-specific tests
// ---------------------------------------------------------------------------

describe('createGameBlock', () => {
  it('is always permanent and unencrypted', () => {
    const block = createGameBlock({
      qubeId: 'Q1',
      blockNumber: 3,
      previousHash: 'a'.repeat(64),
      gameId: 'g1',
      gameType: 'chess',
      whitePlayer: { id: 'u1', type: 'human' },
      blackPlayer: { id: 'q1', type: 'qube' },
      result: '1-0',
      termination: 'checkmate',
      totalMoves: 30,
      pgn: '1. e4 ...',
      durationSeconds: 300,
      xpEarned: 50,
    });

    expect(block.encrypted).toBe(false);
    expect(block.temporary).toBe(false);
    expect(block.blockHash).toBeTruthy();
  });
});

describe('createSummaryBlock', () => {
  it('is always permanent and encrypted', () => {
    const block = createSummaryBlock({
      qubeId: 'Q1',
      blockNumber: 3,
      previousHash: 'a'.repeat(64),
      summarizedBlocks: [1, 2],
      blockCount: 2,
      timePeriod: { start: 1000, end: 2000 },
      summaryText: 'Summary.',
    });

    expect(block.encrypted).toBe(true);
    expect(block.temporary).toBe(false);
    expect(block.blockHash).toBeTruthy();
  });
});
