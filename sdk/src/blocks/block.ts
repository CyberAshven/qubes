/**
 * QubeBlock — lightweight wrapper around a snake_case block dict.
 *
 * The internal representation uses snake_case keys to match the on-wire
 * Qubes protocol format (Python `json.dumps(sort_keys=True)`). TypeScript
 * consumers access fields through camelCase getters/setters for ergonomics.
 *
 * @module blocks/block
 */

import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex } from '@noble/hashes/utils';
import { canonicalStringify } from '../utils/canonical-stringify.js';

// ---------------------------------------------------------------------------
// UTF-8 encoder singleton
// ---------------------------------------------------------------------------

const utf8 = new TextEncoder();

// ---------------------------------------------------------------------------
// QubeBlock class
// ---------------------------------------------------------------------------

/**
 * A memory block in the Qubes chain.
 *
 * Stores data in snake_case (protocol format). Provides camelCase getters
 * for TypeScript ergonomics.
 *
 * Python equivalent: `core.block.Block` (Pydantic model).
 */
export class QubeBlock {
  /** Internal snake_case dict (protocol format). */
  private data: Record<string, unknown>;

  /**
   * Create a QubeBlock from a snake_case dict.
   *
   * Auto-sets `timestamp` to current UTC seconds if not provided.
   *
   * @param data - Snake_case block dict.
   */
  constructor(data: Record<string, unknown>) {
    if (!data.timestamp) {
      data.timestamp = Math.floor(Date.now() / 1000);
    }
    this.data = { ...data };
  }

  // ── Core field getters ──────────────────────────────────────────────

  get blockType(): string {
    return this.data.block_type as string;
  }
  get blockNumber(): number {
    return this.data.block_number as number;
  }
  get qubeId(): string {
    return this.data.qube_id as string;
  }
  get timestamp(): number {
    return this.data.timestamp as number;
  }
  get content(): Record<string, unknown> | null {
    return (this.data.content as Record<string, unknown>) ?? null;
  }
  get encrypted(): boolean {
    return this.data.encrypted as boolean;
  }
  get temporary(): boolean {
    return this.data.temporary as boolean;
  }

  // ── Chain linkage getters ───────────────────────────────────────────

  get previousHash(): string | null {
    return (this.data.previous_hash as string) ?? null;
  }
  get blockHash(): string | null {
    return (this.data.block_hash as string) ?? null;
  }
  get signature(): string | null {
    return (this.data.signature as string) ?? null;
  }
  get merkleRoot(): string | null {
    return (this.data.merkle_root as string) ?? null;
  }

  // ── Setters for mutable chain fields ────────────────────────────────

  set blockHash(hash: string | null) {
    this.data.block_hash = hash;
  }
  set signature(sig: string | null) {
    this.data.signature = sig;
  }
  set merkleRoot(root: string | null) {
    this.data.merkle_root = root;
  }

  // ── Hashing ─────────────────────────────────────────────────────────

  /**
   * Compute the SHA-256 hash of this block.
   *
   * Excludes `block_hash`, `signature`, `participant_signatures`, and
   * `content_hash` — matching the Python `Block.compute_hash()` method.
   *
   * @returns 64-character lowercase hex hash.
   */
  computeHash(): string {
    const copy = { ...this.data };
    delete copy.block_hash;
    delete copy.signature;
    delete copy.participant_signatures;
    delete copy.content_hash;

    const json = canonicalStringify(copy);
    return bytesToHex(sha256(utf8.encode(json)));
  }

  /**
   * Compute the hash of just the content (for multi-party signing).
   *
   * This excludes chain-specific metadata so all participants can sign the
   * same content even though their chain positions differ.
   *
   * Python equivalent: `Block.compute_content_hash()`.
   *
   * @returns 64-character lowercase hex hash.
   */
  computeContentHash(): string {
    const target = this.content ?? {};
    const json = canonicalStringify(target);
    return bytesToHex(sha256(utf8.encode(json)));
  }

  // ── Serialization ───────────────────────────────────────────────────

  /**
   * Convert to a snake_case dict, excluding null/undefined values.
   *
   * Matches Python's `Block.to_dict()` which uses `model_dump(exclude_none=True)`.
   *
   * @returns Plain object with snake_case keys.
   */
  toDict(): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(this.data)) {
      if (value !== null && value !== undefined) {
        result[key] = value;
      }
    }
    return result;
  }

  /**
   * Create a QubeBlock from a snake_case dict.
   *
   * Auto-sets `timestamp` if missing.
   *
   * @param data - Snake_case block dict.
   * @returns New QubeBlock instance.
   */
  static fromDict(data: Record<string, unknown>): QubeBlock {
    return new QubeBlock(data);
  }
}
