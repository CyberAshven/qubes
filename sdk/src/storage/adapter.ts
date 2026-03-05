/**
 * Storage adapter base types and error class.
 *
 * Re-exports the core `StorageAdapter` interface and `UploadResult` type
 * from the canonical types module, and provides a typed error class for
 * storage-related failures.
 *
 * @module storage/adapter
 */

export { StorageAdapter, UploadResult } from '../types/storage.js';

// ---------------------------------------------------------------------------
// StorageError
// ---------------------------------------------------------------------------

/**
 * Error thrown by storage adapter operations.
 *
 * Carries an optional machine-readable `code` string so callers can branch
 * on specific failure modes (e.g. `"RATE_LIMITED"`, `"AUTH_FAILED"`) without
 * parsing the human-readable message.
 *
 * @example
 * ```ts
 * throw new StorageError('Invalid Pinata JWT', 'AUTH_FAILED');
 * ```
 */
export class StorageError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = 'StorageError';
  }
}
