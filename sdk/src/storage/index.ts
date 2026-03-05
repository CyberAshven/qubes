/**
 * Storage module — Pluggable storage adapters for IPFS/Pinata.
 *
 * Provides a `StorageAdapter` interface for content-addressed storage and a
 * Pinata cloud implementation, plus a multi-gateway download utility.
 *
 * ```ts
 * import { PinataAdapter, downloadFromIpfs, StorageError } from '@qubesai/sdk/storage';
 *
 * const storage = new PinataAdapter({ jwt: process.env.PINATA_JWT! });
 * const result = await storage.uploadJson({ hello: 'world' });
 * const bytes  = await downloadFromIpfs(result.cid);
 * ```
 *
 * @module storage
 */

// Core interface + base error
export { StorageAdapter, UploadResult, StorageError } from './adapter.js';

// Pinata adapter
export { PinataAdapter, type PinataConfig } from './pinata.js';

// Multi-gateway download utility
export {
  downloadFromIpfs,
  getGatewayUrl,
  DEFAULT_GATEWAYS,
} from './download.js';
