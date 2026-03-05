/**
 * Cross-compatibility test: canonicalStringify vs Python json.dumps(sort_keys=True)
 */
import { describe, it, expect } from 'vitest';
import { canonicalStringify } from '../../src/utils/canonical-stringify.js';
import vectors from './vectors.json';

describe('canonicalStringify ↔ Python json.dumps(sort_keys=True)', () => {
  it('produces identical output to Python for nested objects', () => {
    const result = canonicalStringify(vectors.canonicalStringify.input);
    expect(result).toBe(vectors.canonicalStringify.canonical);
  });

  it('matches Python separators (", " and ": ")', () => {
    const result = canonicalStringify(vectors.canonicalStringify.input);
    expect(result).toBe(vectors.canonicalStringify.canonicalWithSeparators);
  });

  it('sorts keys at every nesting level', () => {
    const input = { z: { y: { x: 1, w: 2 }, v: 3 }, a: 0 };
    const result = canonicalStringify(input);
    // Keys should appear in order: a, z, v, y, w, x
    expect(result).toBe('{"a": 0, "z": {"v": 3, "y": {"w": 2, "x": 1}}}');
  });

  it('preserves array order (does not sort arrays)', () => {
    const input = { items: [3, 1, 2] };
    const result = canonicalStringify(input);
    expect(result).toBe('{"items": [3, 1, 2]}');
  });

  it('sorts keys inside objects within arrays', () => {
    const input = { list: [{ b: 2, a: 1 }] };
    const result = canonicalStringify(input);
    expect(result).toBe('{"list": [{"a": 1, "b": 2}]}');
  });

  it('handles null, boolean, numbers correctly', () => {
    expect(canonicalStringify(null)).toBe('null');
    expect(canonicalStringify(true)).toBe('true');
    expect(canonicalStringify(false)).toBe('false');
    expect(canonicalStringify(42)).toBe('42');
    expect(canonicalStringify(3.14)).toBe('3.14');
  });

  it('handles empty objects and arrays', () => {
    expect(canonicalStringify({})).toBe('{}');
    expect(canonicalStringify([])).toBe('[]');
  });

  it('produces correct canonical JSON for block hashing', () => {
    const result = canonicalStringify(vectors.blockHashing.block);
    expect(result).toBe(vectors.blockHashing.canonicalJson);
  });
});
