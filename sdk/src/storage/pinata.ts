/**
 * Pinata cloud storage adapter.
 *
 * Implements `StorageAdapter` using the Pinata pinning service API.
 * All HTTP calls use the standard `fetch()` API so the adapter works in
 * browsers, Node 18+, and Deno without additional dependencies.
 *
 * @module storage/pinata
 */

import { StorageAdapter, UploadResult } from '../types/storage.js';
import { StorageError } from './adapter.js';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Configuration for the Pinata storage adapter.
 */
export interface PinataConfig {
  /** Pinata JWT (Bearer token). Obtain from https://app.pinata.cloud/keys */
  jwt: string;
  /**
   * Custom IPFS gateway URL used for downloads.
   * @default "https://gateway.pinata.cloud"
   */
  gateway?: string;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Map HTTP error status codes to descriptive messages. */
function describeHttpError(status: number, body: string): string {
  switch (status) {
    case 401: return 'Invalid Pinata JWT';
    case 403: return 'Pinata access forbidden';
    case 429: return 'Pinata rate limit exceeded';
    default:  return `Pinata request failed (HTTP ${status}): ${body.slice(0, 200)}`;
  }
}

/** Map HTTP error status codes to short machine-readable codes. */
function codeForStatus(status: number): string {
  switch (status) {
    case 401: return 'AUTH_FAILED';
    case 403: return 'FORBIDDEN';
    case 429: return 'RATE_LIMITED';
    default:  return `HTTP_${status}`;
  }
}

/**
 * Assert an HTTP response was successful; throw `StorageError` otherwise.
 */
async function assertOk(response: Response): Promise<void> {
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new StorageError(
      describeHttpError(response.status, body),
      codeForStatus(response.status),
    );
  }
}

// ---------------------------------------------------------------------------
// PinataAdapter
// ---------------------------------------------------------------------------

/**
 * Storage adapter backed by the Pinata cloud pinning service.
 *
 * @example
 * ```ts
 * const adapter = new PinataAdapter({ jwt: process.env.PINATA_JWT! });
 * const result = await adapter.uploadJson({ hello: 'world' });
 * console.log(result.uri); // ipfs://Qm...
 * ```
 */
export class PinataAdapter implements StorageAdapter {
  private readonly jwt: string;
  private readonly gateway: string;

  constructor(config: PinataConfig) {
    this.jwt = config.jwt;
    this.gateway = config.gateway?.replace(/\/$/, '') ?? 'https://gateway.pinata.cloud';
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — upload (raw bytes)
  // -------------------------------------------------------------------------

  /**
   * Upload raw bytes to Pinata via the `pinFileToIPFS` endpoint.
   *
   * @param data     - Raw bytes to upload.
   * @param metadata - Optional key/value metadata; `name` is used as the
   *                   filename visible in the Pinata dashboard.
   */
  async upload(data: Uint8Array, metadata?: Record<string, string>): Promise<UploadResult> {
    const filename = metadata?.['name'] ?? 'upload.bin';

    const form = new FormData();
    form.append('file', new Blob([data as unknown as BlobPart]), filename);
    form.append(
      'pinataMetadata',
      JSON.stringify({ name: filename }),
    );

    const response = await fetch('https://api.pinata.cloud/pinning/pinFileToIPFS', {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.jwt}` },
      body: form,
    });

    await assertOk(response);

    const json = (await response.json()) as { IpfsHash: string };
    const cid = json.IpfsHash;
    return { cid, uri: `ipfs://${cid}` };
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — upload (JSON)
  // -------------------------------------------------------------------------

  /**
   * Upload a JSON-serialisable object to Pinata via `pinJSONToIPFS`.
   *
   * @param json     - Object to serialise and store.
   * @param metadata - Optional metadata; `name` is used as the pin name.
   */
  async uploadJson(
    json: Record<string, unknown>,
    metadata?: Record<string, string>,
  ): Promise<UploadResult> {
    const name = metadata?.['name'] ?? 'data.json';

    const response = await fetch('https://api.pinata.cloud/pinning/pinJSONToIPFS', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.jwt}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pinataContent: json,
        pinataMetadata: { name },
      }),
    });

    await assertOk(response);

    const result = (await response.json()) as { IpfsHash: string };
    const cid = result.IpfsHash;
    return { cid, uri: `ipfs://${cid}` };
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — download
  // -------------------------------------------------------------------------

  /**
   * Download content by CID from the configured Pinata gateway.
   *
   * @param cid - Content identifier (with or without `ipfs://` prefix).
   */
  async download(cid: string): Promise<Uint8Array> {
    const cleanCid = cid.startsWith('ipfs://') ? cid.slice(7) : cid;
    const url = `${this.gateway}/ipfs/${cleanCid}`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new StorageError(
        `Failed to download CID ${cleanCid} from ${this.gateway} (HTTP ${response.status})`,
        `HTTP_${response.status}`,
      );
    }

    const buffer = await response.arrayBuffer();
    return new Uint8Array(buffer);
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — pin
  // -------------------------------------------------------------------------

  /**
   * Pin an existing CID via the Pinata `pinByHash` endpoint.
   *
   * @param cid - Content identifier to pin.
   */
  async pin(cid: string): Promise<void> {
    const cleanCid = cid.startsWith('ipfs://') ? cid.slice(7) : cid;

    const response = await fetch('https://api.pinata.cloud/pinning/pinByHash', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.jwt}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hashToPin: cleanCid }),
    });

    await assertOk(response);
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — unpin
  // -------------------------------------------------------------------------

  /**
   * Unpin a CID, allowing Pinata to garbage-collect the content.
   *
   * @param cid - Content identifier to unpin.
   */
  async unpin(cid: string): Promise<void> {
    const cleanCid = cid.startsWith('ipfs://') ? cid.slice(7) : cid;

    const response = await fetch(
      `https://api.pinata.cloud/pinning/unpin/${encodeURIComponent(cleanCid)}`,
      {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${this.jwt}` },
      },
    );

    await assertOk(response);
  }

  // -------------------------------------------------------------------------
  // StorageAdapter — isAvailable
  // -------------------------------------------------------------------------

  /**
   * Check whether the Pinata JWT is valid by hitting the test-authentication
   * endpoint.
   *
   * @returns `true` if Pinata returns HTTP 200, `false` otherwise.
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch('https://api.pinata.cloud/data/testAuthentication', {
        headers: { Authorization: `Bearer ${this.jwt}` },
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}
