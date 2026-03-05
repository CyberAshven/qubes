/**
 * Tests for blocks/genesis — createGenesisBlock factory.
 */
import { describe, it, expect } from 'vitest';
import { createGenesisBlock } from '../../src/blocks/genesis.js';

const GENESIS_PARAMS = {
  qubeId: 'ABCD1234',
  qubeName: 'TestQube',
  creator: 'user_001',
  publicKey: '0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2',
  genesisPrompt: 'You are a helpful AI assistant.',
  aiModel: 'claude-sonnet-4-20250514',
  voiceModel: 'openai:alloy',
  avatar: { style: 'pixel', seed: 42 },
};

describe('createGenesisBlock', () => {
  it('produces block 0 with GENESIS type', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.blockType).toBe('GENESIS');
    expect(block.blockNumber).toBe(0);
  });

  it('has previous_hash = "0" x 64', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.previousHash).toBe('0'.repeat(64));
  });

  it('has a computed block_hash (64-char hex)', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.blockHash).toBeTruthy();
    expect(block.blockHash).toHaveLength(64);
    expect(block.blockHash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('has encrypted = false', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.encrypted).toBe(false);
  });

  it('has temporary = false', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.temporary).toBe(false);
  });

  it('stores qube_id from params', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    expect(block.qubeId).toBe('ABCD1234');
  });

  it('has a valid timestamp', () => {
    const before = Math.floor(Date.now() / 1000);
    const block = createGenesisBlock(GENESIS_PARAMS);
    const after = Math.floor(Date.now() / 1000);

    expect(block.timestamp).toBeGreaterThanOrEqual(before);
    expect(block.timestamp).toBeLessThanOrEqual(after);
  });

  it('stores identity fields in toDict()', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);
    const dict = block.toDict();

    expect(dict.qube_name).toBe('TestQube');
    expect(dict.creator).toBe('user_001');
    expect(dict.public_key).toBe(GENESIS_PARAMS.publicKey);
    expect(dict.genesis_prompt).toBe('You are a helpful AI assistant.');
    expect(dict.ai_model).toBe('claude-sonnet-4-20250514');
    expect(dict.voice_model).toBe('openai:alloy');
    expect(dict.avatar).toEqual({ style: 'pixel', seed: 42 });
  });

  it('uses default values for optional fields', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);
    const dict = block.toDict();

    expect(dict.favorite_color).toBe('#4A90E2');
    expect(dict.home_blockchain).toBe('bitcoin_cash');
    expect(dict.default_trust_level).toBe(50);
    expect(dict.genesis_prompt_encrypted).toBe(false);
  });

  it('allows overriding optional fields', () => {
    const block = createGenesisBlock({
      ...GENESIS_PARAMS,
      favoriteColor: '#FF0000',
      homeBlockchain: 'ethereum',
      defaultTrustLevel: 75,
      genesisPromptEncrypted: true,
    });
    const dict = block.toDict();

    expect(dict.favorite_color).toBe('#FF0000');
    expect(dict.home_blockchain).toBe('ethereum');
    expect(dict.default_trust_level).toBe(75);
    expect(dict.genesis_prompt_encrypted).toBe(true);
  });

  it('includes NFT fields when provided', () => {
    const block = createGenesisBlock({
      ...GENESIS_PARAMS,
      nftContract: '0xabc123',
      nftTokenId: '42',
    });
    const dict = block.toDict();

    expect(dict.nft_contract).toBe('0xabc123');
    expect(dict.nft_token_id).toBe('42');
  });

  it('excludes NFT fields when not provided', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);
    const dict = block.toDict();

    expect(dict).not.toHaveProperty('nft_contract');
    expect(dict).not.toHaveProperty('nft_token_id');
  });

  it('block_hash matches computeHash()', () => {
    const block = createGenesisBlock(GENESIS_PARAMS);

    // The factory sets block_hash = computeHash()
    // computeHash() excludes block_hash from the computation, so calling
    // it again should return the same value
    expect(block.blockHash).toBe(block.computeHash());
  });
});
