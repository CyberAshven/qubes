/**
 * Storage adapter types for the Qubes protocol.
 *
 * The SDK uses a pluggable storage interface so that consumers can provide
 * their own IPFS (or other) storage backend. The default implementation
 * uses Pinata, but any service that implements `StorageAdapter` can be used.
 *
 * @module types/storage
 */

// ---------------------------------------------------------------------------
// Upload Result
// ---------------------------------------------------------------------------

/**
 * Result of a successful storage upload.
 */
export interface UploadResult {
  /** Content identifier (IPFS CID or equivalent). */
  cid: string;
  /** Full URI for accessing the content (e.g. "ipfs://Qm..."). */
  uri: string;
}

// ---------------------------------------------------------------------------
// Storage Adapter Interface
// ---------------------------------------------------------------------------

/**
 * Pluggable storage adapter interface.
 *
 * Implementations should handle content-addressed storage operations
 * (upload, download, pin, unpin). The SDK ships with a Pinata adapter
 * but consumers can provide their own.
 *
 * All methods are async to support network-based storage backends.
 */
export interface StorageAdapter {
  /**
   * Upload data to storage.
   *
   * @param data - Raw bytes to upload.
   * @param metadata - Optional metadata to associate with the upload
   *                   (e.g. filename, content type, pin name).
   * @returns Upload result with CID and URI.
   */
  upload(data: Uint8Array, metadata?: Record<string, string>): Promise<UploadResult>;

  /**
   * Download data from storage by CID.
   *
   * @param cid - Content identifier to retrieve.
   * @returns Raw bytes of the stored content.
   */
  download(cid: string): Promise<Uint8Array>;

  /**
   * Pin content to ensure it persists in storage.
   *
   * @param cid - Content identifier to pin.
   */
  pin(cid: string): Promise<void>;

  /**
   * Unpin content to allow garbage collection.
   *
   * @param cid - Content identifier to unpin.
   */
  unpin(cid: string): Promise<void>;

  /**
   * Check whether the storage backend is available and configured.
   *
   * @returns `true` if the adapter is ready for use.
   */
  isAvailable(): Promise<boolean>;
}
