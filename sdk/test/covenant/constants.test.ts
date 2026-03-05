/**
 * Tests for covenant constants and validators.
 */
import { describe, it, expect } from 'vitest';
import {
  OFFICIAL_CATEGORY,
  OFFICIAL_COVENANT_ADDRESS,
  MIN_MINT_FUNDING,
  DUST_LIMIT,
  TOKEN_DUST,
  isOfficialQube,
} from '../../src/covenant/constants.js';

describe('covenant constants', () => {
  it('OFFICIAL_CATEGORY is 64-char hex', () => {
    expect(OFFICIAL_CATEGORY).toHaveLength(64);
    expect(OFFICIAL_CATEGORY).toMatch(/^[0-9a-f]{64}$/);
  });

  it('OFFICIAL_COVENANT_ADDRESS starts with bitcoincash:r (P2SH32)', () => {
    expect(OFFICIAL_COVENANT_ADDRESS).toMatch(/^bitcoincash:r/);
  });

  it('MIN_MINT_FUNDING >= TOKEN_DUST * 2', () => {
    expect(MIN_MINT_FUNDING).toBeGreaterThanOrEqual(TOKEN_DUST * 2n);
  });

  it('DUST_LIMIT is 546 sats', () => {
    expect(DUST_LIMIT).toBe(546n);
  });

  it('TOKEN_DUST is 1000 sats', () => {
    expect(TOKEN_DUST).toBe(1000n);
  });
});

describe('isOfficialQube', () => {
  it('returns true for official category', () => {
    expect(isOfficialQube(OFFICIAL_CATEGORY)).toBe(true);
  });

  it('is case-insensitive', () => {
    expect(isOfficialQube(OFFICIAL_CATEGORY.toUpperCase())).toBe(true);
  });

  it('returns false for wrong category', () => {
    expect(isOfficialQube('deadbeef'.repeat(8))).toBe(false);
  });

  it('returns false for null/undefined/empty', () => {
    expect(isOfficialQube('')).toBe(false);
    expect(isOfficialQube(null as any)).toBe(false);
    expect(isOfficialQube(undefined as any)).toBe(false);
  });
});
