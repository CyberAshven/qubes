/**
 * CashScript contract instantiation for the Qubes minting covenant.
 *
 * This module dynamically imports `cashscript` so the SDK does not crash
 * when the optional peer dependency is not installed. Errors are deferred
 * until the user actually calls {@link createCovenantContract}.
 *
 * **Node.js only** — CashScript uses `node:crypto` and `node:net` internally.
 *
 * @module covenant/contract
 */

import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { hexToBytes } from '@noble/hashes/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Options for creating a covenant contract instance.
 */
export interface CovenantContractOptions {
  /** Platform compressed public key hex (66 chars). Used to derive platformPkh. */
  platformPublicKey: string;
  /** Network: `'mainnet'` or `'chipnet'`. Default: `'mainnet'`. */
  network?: string;
  /**
   * Custom CashScript artifact object.
   * If not provided the bundled `qubes_mint.json` is loaded at runtime.
   */
  artifact?: unknown;
}

/**
 * Result of instantiating the covenant contract.
 */
export interface CovenantContract {
  /** The CashScript `Contract` instance (typed as `unknown` to avoid requiring the peer dep at compile time). */
  contract: unknown;
  /** The contract's token-aware address (where the minting token lives). */
  tokenAddress: string;
  /** The contract's regular (non-token) address. */
  address: string;
}

// ---------------------------------------------------------------------------
// Artifact loader
// ---------------------------------------------------------------------------

/**
 * Attempt to load the bundled CashScript artifact.
 *
 * Multiple strategies are tried because JSON imports with
 * `{ with: { type: 'json' } }` are not supported in every bundler / runtime.
 */
async function loadBundledArtifact(): Promise<unknown> {
  // Strategy 1: dynamic import with import assertion (Node 22+, some bundlers)
  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-return
    return (await import('./qubes_mint.json', { with: { type: 'json' } })).default;
  } catch {
    // fall through
  }

  // Strategy 2: fs.readFile (Node.js)
  try {
    // @ts-ignore — node:fs/promises may not have types in this project
    const fs = await import('node:fs/promises');
    // @ts-ignore
    const url = await import('node:url');
    // @ts-ignore
    const path = await import('node:path');
    const thisFile = url.fileURLToPath(import.meta.url);
    const jsonPath = path.join(path.dirname(thisFile), 'qubes_mint.json');
    const raw = await fs.readFile(jsonPath, 'utf-8');
    return JSON.parse(raw);
  } catch {
    // fall through
  }

  throw new Error(
    'Could not load bundled qubes_mint.json. ' +
    'Pass the artifact explicitly via options.artifact.',
  );
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Instantiate the QubesMint covenant contract.
 *
 * Requires `cashscript` as an optional peer dependency.
 *
 * @param options - Contract configuration.
 * @returns The instantiated contract and its addresses.
 * @throws If `cashscript` is not installed or `platformPublicKey` is invalid.
 *
 * @example
 * ```ts
 * import { createCovenantContract } from '@qubesai/sdk/covenant';
 *
 * const { contract, tokenAddress } = await createCovenantContract({
 *   platformPublicKey: '02abc...', // 66 hex chars
 * });
 * ```
 */
export async function createCovenantContract(
  options: CovenantContractOptions,
): Promise<CovenantContract> {
  // ── Dynamic import of cashscript ────────────────────────────────────
  let cashscript: any;
  try {
    // @ts-ignore — cashscript is an optional peer dependency
    cashscript = await import('cashscript');
  } catch {
    throw new Error(
      'cashscript is required for covenant operations. ' +
      'Install it with:  npm install cashscript',
    );
  }

  const { Contract, ElectrumNetworkProvider } = cashscript;

  // ── Validate public key ─────────────────────────────────────────────
  const { platformPublicKey, network = 'mainnet' } = options;

  if (!platformPublicKey || platformPublicKey.length !== 66) {
    throw new Error(
      'platformPublicKey must be a 66-character compressed public key hex string',
    );
  }

  // ── Derive platformPkh = HASH160(pubkey) ────────────────────────────
  const pubkeyBytes = hexToBytes(platformPublicKey);
  const platformPkh = ripemd160(sha256(pubkeyBytes));

  // ── Load artifact ───────────────────────────────────────────────────
  const artifact = options.artifact ?? await loadBundledArtifact();

  // ── Create provider & contract ──────────────────────────────────────
  const provider = new ElectrumNetworkProvider(network);
  const contract = new Contract(
    artifact as any,
    [platformPkh],
    { provider, addressType: 'p2sh32' },
  );

  return {
    contract,
    tokenAddress: contract.tokenAddress as string,
    address: contract.address as string,
  };
}
