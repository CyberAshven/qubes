/**
 * Multi-gateway IPFS download utility.
 *
 * Provides gateway fallback logic mirroring the Python implementation in
 * `blockchain/ipfs.py`.  The function tries each gateway in order and returns
 * the content from the first one that responds successfully.
 *
 * @module storage/download
 */

import { StorageError } from './adapter.js';

// ---------------------------------------------------------------------------
// Default gateway list
// ---------------------------------------------------------------------------

/**
 * Public IPFS gateways tried in order when no custom list is provided.
 *
 * The list mirrors the four-gateway approach used in the Python backend.
 */
export const DEFAULT_GATEWAYS: readonly string[] = [
  'https://gateway.pinata.cloud',
  'https://ipfs.io',
  'https://cloudflare-ipfs.com',
  'https://dweb.link',
];

// ---------------------------------------------------------------------------
// getGatewayUrl
// ---------------------------------------------------------------------------

/**
 * Convert an `ipfs://` URI (or bare CID) to an HTTP gateway URL.
 *
 * @param ipfsUri - Either a full `ipfs://CID` URI or a bare CID string.
 * @param gateway - Base gateway URL.  Defaults to `https://ipfs.io`.
 * @returns Full HTTP URL, e.g. `https://ipfs.io/ipfs/Qm...`.
 *
 * @example
 * ```ts
 * getGatewayUrl('ipfs://QmFoo');
 * // → 'https://ipfs.io/ipfs/QmFoo'
 *
 * getGatewayUrl('QmFoo', 'https://gateway.pinata.cloud');
 * // → 'https://gateway.pinata.cloud/ipfs/QmFoo'
 * ```
 */
export function getGatewayUrl(
  ipfsUri: string,
  gateway: string = 'https://ipfs.io',
): string {
  const base = gateway.replace(/\/$/, '');
  const cid = ipfsUri.startsWith('ipfs://') ? ipfsUri.slice(7) : ipfsUri;
  return `${base}/ipfs/${cid}`;
}

// ---------------------------------------------------------------------------
// downloadFromIpfs
// ---------------------------------------------------------------------------

/**
 * Download content from IPFS using multiple gateway fallbacks.
 *
 * Tries each gateway in `gateways` (or `DEFAULT_GATEWAYS`) in sequence.
 * Returns the raw bytes from the first gateway that responds with HTTP 200.
 * Throws `StorageError` if every gateway fails.
 *
 * @param cid      - Content identifier, with or without an `ipfs://` prefix.
 * @param gateways - Ordered list of gateway base URLs to try.
 * @returns Raw content bytes.
 *
 * @throws {StorageError} When all gateways fail, with a message listing the
 *   attempted URLs.
 *
 * @example
 * ```ts
 * const bytes = await downloadFromIpfs('QmFoo');
 * const text = new TextDecoder().decode(bytes);
 * ```
 */
export async function downloadFromIpfs(
  cid: string,
  gateways: string[] = DEFAULT_GATEWAYS as string[],
): Promise<Uint8Array> {
  // Strip ipfs:// prefix once so each gateway URL is built cleanly.
  const cleanCid = cid.startsWith('ipfs://') ? cid.slice(7) : cid;

  const attempted: string[] = [];

  for (const gateway of gateways) {
    const url = getGatewayUrl(cleanCid, gateway);
    attempted.push(url);

    try {
      const response = await fetch(url);
      if (response.ok) {
        const buffer = await response.arrayBuffer();
        return new Uint8Array(buffer);
      }
      // Non-OK response: try the next gateway rather than throwing immediately.
    } catch {
      // Network-level failure (DNS, timeout, etc.): move to next gateway.
    }
  }

  throw new StorageError(
    `Failed to download CID "${cleanCid}" from all gateways. Tried: ${attempted.join(', ')}`,
    'ALL_GATEWAYS_FAILED',
  );
}
