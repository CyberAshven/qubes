/**
 * Package module — `.qube` file creation, parsing, and integrity verification.
 *
 * Supports two formats:
 * - Binary IPFS packages (magic header + AES-256-GCM ciphertext)
 * - ZIP file exports (manifest.json + PBKDF2-encrypted data.enc)
 *
 * ```ts
 * import {
 *   createBinaryPackage,
 *   parseBinaryPackage,
 *   createQubeFile,
 *   parseQubeFile,
 *   verifyPackageIntegrity,
 *   PACKAGE_MAGIC,
 *   PACKAGE_VERSION,
 * } from '@qubesai/sdk/package';
 * ```
 *
 * @module package
 */

// Creation
export {
  createBinaryPackage,
  createQubeFile,
  PACKAGE_MAGIC,
  PACKAGE_VERSION,
  NONCE_SIZE,
  KEY_SIZE,
} from './create.js';

// Parsing
export { parseBinaryPackage, parseQubeFile } from './parse.js';

// Integrity verification
export { verifyPackageIntegrity } from './verify.js';
