/**
 * Covenant minting — build and broadcast (or prepare) NFT mint transactions.
 *
 * This module wraps the CashScript covenant interaction from `mint-cli.ts`
 * into library functions suitable for programmatic use.
 *
 * **Node.js only** — CashScript uses `node:crypto` and `node:net` internally.
 * The two peer dependencies are loaded via dynamic `import()` so the rest of
 * the SDK works even when they are absent.
 *
 * @module covenant/mint
 */

import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { hexToBytes } from '@noble/hashes/utils';
import {
  OFFICIAL_CATEGORY,
  MIN_MINT_FUNDING,
  DUST_LIMIT,
  TOKEN_DUST,
} from './constants.js';
import type {
  MintResult,
  WcMintResult,
  MintError,
  MintOutcome,
} from '../types/covenant.js';

// Note: MintResult, WcMintResult, MintError, MintOutcome are defined in
// types/covenant.ts and re-exported via types/index.ts. We import them here
// for use in function signatures but do NOT re-export to avoid name collisions
// in the top-level barrel (sdk/src/index.ts).

// ---------------------------------------------------------------------------
// Parameter types (new to this module)
// ---------------------------------------------------------------------------

/**
 * Common parameters shared by both broadcast and WalletConnect modes.
 */
export interface MintParams {
  /** 64-char hex commitment (SHA-256 of compressed pubkey hex). */
  commitment: string;
  /** Recipient's token-aware CashAddr (`bitcoincash:z...`). */
  recipientAddress: string;
  /** Platform's compressed public key hex (66 chars). */
  platformPublicKey: string;
  /** Network: `'mainnet'` or `'chipnet'`. Default: `'mainnet'`. */
  network?: string;
  /** Custom CashScript artifact (optional — falls back to bundled). */
  artifact?: unknown;
  /** Override the expected category ID (default: {@link OFFICIAL_CATEGORY}). */
  categoryId?: string;
}

/**
 * Parameters for broadcast mode (platform signs and broadcasts).
 */
export interface BroadcastMintParams extends MintParams {
  /** Platform wallet WIF private key (used to fund and sign). */
  walletWif: string;
}

/**
 * Parameters for WalletConnect mode (user signs via external wallet).
 */
export interface WcMintParams extends MintParams {
  /** User's token-aware address (`bitcoincash:z...`). */
  userAddress: string;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

const HEX64_RE = /^[0-9a-fA-F]{64}$/;
const HEX66_RE = /^[0-9a-fA-F]{66}$/;

function validateCommon(params: MintParams): MintError | null {
  if (!params.commitment || !HEX64_RE.test(params.commitment)) {
    return { success: false, error: 'commitment must be a 64-character hex string (32 bytes)' };
  }
  if (!params.recipientAddress) {
    return { success: false, error: 'recipientAddress is required' };
  }
  if (!params.platformPublicKey || !HEX66_RE.test(params.platformPublicKey)) {
    return { success: false, error: 'platformPublicKey must be a 66-character compressed hex public key' };
  }
  return null;
}

// ---------------------------------------------------------------------------
// Dynamic import helpers
// ---------------------------------------------------------------------------

async function loadCashscript(): Promise<any> {
  try {
    // @ts-ignore — cashscript is an optional peer dependency
    return await import('cashscript');
  } catch {
    throw new Error(
      'cashscript is required for minting. Install it with:  npm install cashscript',
    );
  }
}

async function loadLibauth(): Promise<any> {
  try {
    // @ts-ignore — @bitauth/libauth is an optional peer dependency
    return await import('@bitauth/libauth');
  } catch {
    throw new Error(
      '@bitauth/libauth is required for minting. Install it with:  npm install @bitauth/libauth',
    );
  }
}

/**
 * Load the CashScript artifact (bundled or user-provided).
 */
async function resolveArtifact(artifact: unknown | undefined): Promise<unknown> {
  if (artifact) return artifact;

  // Try JSON import assertion (Node 22+, some bundlers)
  try {
    return (await import('./qubes_mint.json', { with: { type: 'json' } })).default;
  } catch {
    // fall through
  }

  // Try node:fs fallback
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
    'Pass the artifact explicitly via params.artifact.',
  );
}

// ---------------------------------------------------------------------------
// Internal: build the contract + find minting UTXO
// ---------------------------------------------------------------------------

interface ContractContext {
  cashscript: any;
  contract: any;
  mintingTokenUtxo: any;
  provider: any;
  categoryId: string;
}

async function setupContract(params: MintParams): Promise<ContractContext | MintError> {
  const cashscript = await loadCashscript();
  const { Contract, ElectrumNetworkProvider } = cashscript;

  const { platformPublicKey, network = 'mainnet' } = params;
  const categoryId = params.categoryId ?? OFFICIAL_CATEGORY;

  // Derive platformPkh = HASH160(pubkey)
  const pubkeyBytes = hexToBytes(platformPublicKey);
  const platformPkh = ripemd160(sha256(pubkeyBytes));

  const artifact = await resolveArtifact(params.artifact);
  const provider = new ElectrumNetworkProvider(network);
  const contract = new Contract(
    artifact as any,
    [platformPkh],
    { provider, addressType: 'p2sh32' },
  );

  // Find the minting token UTXO at the covenant address
  const contractUtxos = await contract.getUtxos();
  const mintingTokenUtxo = contractUtxos.find(
    (u: any) =>
      u.token?.category === categoryId &&
      u.token?.nft?.capability === 'minting',
  );

  if (!mintingTokenUtxo) {
    return {
      success: false,
      error: `Minting token not found at covenant address ${contract.tokenAddress}`,
    };
  }

  return { cashscript, contract, mintingTokenUtxo, provider, categoryId };
}

// ---------------------------------------------------------------------------
// broadcastMint
// ---------------------------------------------------------------------------

/**
 * Build and broadcast a mint transaction (platform signs).
 *
 * Flow:
 * 1. Validate inputs
 * 2. Instantiate the CashScript covenant contract
 * 3. Find the minting token UTXO
 * 4. Derive user address from WIF
 * 5. Gather funding UTXOs
 * 6. Build the transaction via `TransactionBuilder`
 * 7. Broadcast and return the txid
 *
 * Requires `cashscript` and `@bitauth/libauth` as peer dependencies.
 *
 * @param params - Broadcast mint parameters.
 * @returns Structured result with txid on success, or error details.
 *
 * @example
 * ```ts
 * import { broadcastMint } from '@qubesai/sdk/covenant';
 *
 * const result = await broadcastMint({
 *   commitment: 'abcd...64chars',
 *   recipientAddress: 'bitcoincash:z...',
 *   platformPublicKey: '02abc...66chars',
 *   walletWif: 'L...',
 * });
 *
 * if (result.success) {
 *   console.log('Minted!', result.mintTxid);
 * }
 * ```
 */
export async function broadcastMint(
  params: BroadcastMintParams,
): Promise<MintResult | MintError> {
  // ── Validate ────────────────────────────────────────────────────────
  const validationError = validateCommon(params);
  if (validationError) return validationError;

  if (!params.walletWif) {
    return { success: false, error: 'walletWif is required for broadcast mode' };
  }

  try {
    // ── Dynamic imports ─────────────────────────────────────────────
    const libauth = await loadLibauth();
    const { lockingBytecodeToCashAddress } = libauth;

    const ctxOrError = await setupContract(params);
    if ('error' in ctxOrError) return ctxOrError as MintError;
    const { cashscript, contract, mintingTokenUtxo, provider, categoryId } = ctxOrError;
    const { TransactionBuilder, SignatureTemplate } = cashscript;

    // ── Derive user address from WIF ──────────────────────────────
    const userTemplate = new SignatureTemplate(params.walletWif);
    const userPubkey: Uint8Array = userTemplate.getPublicKey();
    const userPkh = ripemd160(sha256(userPubkey));
    const userLockingBytecode = new Uint8Array([
      0x76, 0xa9, 0x14, ...userPkh, 0x88, 0xac,
    ]);
    const userAddrResult = lockingBytecodeToCashAddress({
      bytecode: userLockingBytecode,
      prefix: 'bitcoincash',
      tokenSupport: true,
    });
    const userAddress: string | undefined =
      typeof userAddrResult === 'string'
        ? userAddrResult
        : (userAddrResult as any)?.address;

    if (!userAddress) {
      return {
        success: false,
        error: `Could not derive user address from WIF: ${JSON.stringify(userAddrResult)}`,
      };
    }

    // ── Gather funding UTXOs ──────────────────────────────────────
    const userUtxos = await provider.getUtxos(userAddress);
    const fundingUtxos = userUtxos.filter((u: any) => !u.token);
    const totalFunding = fundingUtxos.reduce(
      (sum: bigint, u: any) => sum + u.satoshis,
      0n,
    );

    if (totalFunding < MIN_MINT_FUNDING) {
      return {
        success: false,
        error: `Insufficient funds. Need at least ${MIN_MINT_FUNDING} sats, have ${totalFunding} sats at ${userAddress}`,
      };
    }

    // ── Build transaction ─────────────────────────────────────────
    const txBuilder = new TransactionBuilder({ provider });

    // Input 0: covenant UTXO (minting token)
    txBuilder.addInput(
      mintingTokenUtxo,
      contract.unlock.mint(Uint8Array.from(hexToBytes(params.commitment))),
    );

    // Input 1+: user funding UTXOs (signed by WIF)
    for (const utxo of fundingUtxos) {
      txBuilder.addInput(utxo, userTemplate.unlockP2PKH());
    }

    // Output 0: minting token returned to covenant
    txBuilder.addOutput({
      to: contract.tokenAddress,
      amount: TOKEN_DUST,
      token: {
        amount: 0n,
        category: categoryId,
        nft: {
          capability: 'minting',
          commitment: mintingTokenUtxo.token!.nft!.commitment,
        },
      },
    });

    // Output 1: immutable NFT to recipient
    txBuilder.addOutput({
      to: params.recipientAddress,
      amount: TOKEN_DUST,
      token: {
        amount: 0n,
        category: categoryId,
        nft: {
          capability: 'none',
          commitment: params.commitment,
        },
      },
    });

    // Output 2: change back to user (if above dust)
    const totalInput = mintingTokenUtxo.satoshis + totalFunding;
    const totalOutputs = TOKEN_DUST + TOKEN_DUST;
    const estimatedFee = 500n;
    const change = totalInput - totalOutputs - estimatedFee;

    if (change >= DUST_LIMIT) {
      txBuilder.addOutput({
        to: userAddress,
        amount: change,
      });
    }

    // ── Broadcast ─────────────────────────────────────────────────
    const tx = await txBuilder.send();

    return {
      success: true,
      mintTxid: tx.txid as string,
      categoryId,
      commitment: params.commitment,
      covenantAddress: contract.tokenAddress as string,
      recipientAddress: params.recipientAddress,
    };
  } catch (err: any) {
    return {
      success: false,
      error: err?.message ?? String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// prepareMintTransaction (WalletConnect)
// ---------------------------------------------------------------------------

/**
 * Build a WalletConnect-compatible mint transaction object.
 *
 * The returned `wcTransaction` string should be passed to the user's wallet
 * for signing via WalletConnect's `bch_signTransaction` method.
 *
 * Flow:
 * 1. Validate inputs
 * 2. Instantiate the CashScript covenant contract
 * 3. Find the minting token UTXO
 * 4. Gather user funding UTXOs
 * 5. Build the transaction with placeholder unlockers
 * 6. Generate WC transaction object
 *
 * Requires `cashscript` and `@bitauth/libauth` as peer dependencies.
 *
 * @param params - WalletConnect mint parameters.
 * @returns Structured result with the WC transaction object, or error details.
 *
 * @example
 * ```ts
 * import { prepareMintTransaction } from '@qubesai/sdk/covenant';
 *
 * const result = await prepareMintTransaction({
 *   commitment: 'abcd...64chars',
 *   recipientAddress: 'bitcoincash:z...',
 *   platformPublicKey: '02abc...66chars',
 *   userAddress: 'bitcoincash:z...',
 * });
 *
 * if (result.success) {
 *   // Send result.wcTransaction to wallet via WalletConnect
 * }
 * ```
 */
export async function prepareMintTransaction(
  params: WcMintParams,
): Promise<WcMintResult | MintError> {
  // ── Validate ────────────────────────────────────────────────────────
  const validationError = validateCommon(params);
  if (validationError) return validationError;

  if (!params.userAddress) {
    return { success: false, error: 'userAddress is required in walletconnect mode' };
  }

  try {
    // ── Dynamic imports ─────────────────────────────────────────────
    const libauth = await loadLibauth();
    const { stringify: libauthStringify } = libauth;

    const ctxOrError = await setupContract(params);
    if ('error' in ctxOrError) return ctxOrError as MintError;
    const { cashscript, contract, mintingTokenUtxo, provider, categoryId } = ctxOrError;
    const { TransactionBuilder, placeholderP2PKHUnlocker } = cashscript;

    // ── Gather funding UTXOs ──────────────────────────────────────
    const userUtxos = await provider.getUtxos(params.userAddress);
    const fundingUtxos = userUtxos.filter((u: any) => !u.token);
    const totalFunding = fundingUtxos.reduce(
      (sum: bigint, u: any) => sum + u.satoshis,
      0n,
    );

    if (totalFunding < MIN_MINT_FUNDING) {
      return {
        success: false,
        error: `Insufficient funds. Need at least ${MIN_MINT_FUNDING} sats, have ${totalFunding} sats at ${params.userAddress}`,
      };
    }

    // ── Build transaction ─────────────────────────────────────────
    const txBuilder = new TransactionBuilder({ provider });

    // Input 0: covenant UTXO (minting token)
    txBuilder.addInput(
      mintingTokenUtxo,
      contract.unlock.mint(Uint8Array.from(hexToBytes(params.commitment))),
    );

    // Input 1+: user funding UTXOs (placeholder — wallet signs later)
    for (const utxo of fundingUtxos) {
      txBuilder.addInput(utxo, placeholderP2PKHUnlocker(params.userAddress));
    }

    // Output 0: minting token returned to covenant
    txBuilder.addOutput({
      to: contract.tokenAddress,
      amount: TOKEN_DUST,
      token: {
        amount: 0n,
        category: categoryId,
        nft: {
          capability: 'minting',
          commitment: mintingTokenUtxo.token!.nft!.commitment,
        },
      },
    });

    // Output 1: immutable NFT to recipient
    txBuilder.addOutput({
      to: params.recipientAddress,
      amount: TOKEN_DUST,
      token: {
        amount: 0n,
        category: categoryId,
        nft: {
          capability: 'none',
          commitment: params.commitment,
        },
      },
    });

    // Output 2: change back to user (if above dust)
    const totalInput = mintingTokenUtxo.satoshis + totalFunding;
    const totalOutputs = TOKEN_DUST + TOKEN_DUST;
    const estimatedFee = 500n;
    const change = totalInput - totalOutputs - estimatedFee;

    if (change >= DUST_LIMIT) {
      txBuilder.addOutput({
        to: params.userAddress,
        amount: change,
      });
    }

    // ── Generate WC transaction object ────────────────────────────
    const wcTxObj = txBuilder.generateWcTransactionObject({
      broadcast: true,
      userPrompt: 'Mint Qube NFT',
    });

    return {
      success: true,
      mode: 'walletconnect',
      wcTransaction: libauthStringify(wcTxObj),
      categoryId,
      commitment: params.commitment,
      covenantAddress: contract.tokenAddress as string,
      recipientAddress: params.recipientAddress,
    };
  } catch (err: any) {
    return {
      success: false,
      error: err?.message ?? String(err),
    };
  }
}
