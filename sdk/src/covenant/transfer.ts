/**
 * NFT Transfer — build a WalletConnect unsigned P2PKH → P2PKH transfer transaction.
 *
 * Unlike minting, NFT transfers require no covenant. The existing immutable NFT
 * UTXO is simply moved from the sender's address to the recipient's address.
 * All inputs are placeholder P2PKH unlockers that the wallet fills in via
 * WalletConnect `bch_signTransaction`.
 *
 * **Node.js only** — requires `cashscript` and `@bitauth/libauth` peer deps
 * loaded via dynamic `import()`.
 *
 * @module covenant/transfer
 */

import type { WcTransferResult, TransferError } from '../types/covenant.js';

// ---------------------------------------------------------------------------
// Parameter types
// ---------------------------------------------------------------------------

/**
 * Parameters for building a WalletConnect NFT transfer transaction.
 */
export interface WcTransferParams {
  /** 64-char hex NFT category ID. */
  categoryId: string;
  /** Current owner's BCH address (from WalletConnect session). */
  senderAddress: string;
  /** New owner's token-aware BCH address (`bitcoincash:z...`). */
  recipientAddress: string;
  /** Change address. Defaults to `senderAddress`. */
  changeAddress?: string;
  /** Network: `'mainnet'` or `'chipnet'`. Default: `'mainnet'`. */
  network?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HEX64_RE = /^[0-9a-fA-F]{64}$/;
/** Minimum satoshis to attach to an NFT output (token dust). */
const NFT_DUST = 1000n;
/** Change output dust threshold. */
const DUST_LIMIT = 546n;

// ---------------------------------------------------------------------------
// Dynamic import helpers
// ---------------------------------------------------------------------------

async function loadCashscript(): Promise<any> {
  try {
    // @ts-ignore — cashscript is an optional peer dependency
    return await import('cashscript');
  } catch {
    throw new Error(
      'cashscript is required for NFT transfers. Install it with:  npm install cashscript',
    );
  }
}

async function loadLibauth(): Promise<any> {
  try {
    // @ts-ignore — @bitauth/libauth is an optional peer dependency
    return await import('@bitauth/libauth');
  } catch {
    throw new Error(
      '@bitauth/libauth is required for NFT transfers. Install it with:  npm install @bitauth/libauth',
    );
  }
}

// ---------------------------------------------------------------------------
// prepareTransferTransaction
// ---------------------------------------------------------------------------

/**
 * Build an unsigned WalletConnect transaction for a Qube NFT transfer.
 *
 * The transaction is a simple P2PKH → P2PKH NFT send:
 * - Input 0: the NFT UTXO (wallet signs via WC)
 * - Inputs 1+: non-token funding UTXOs for the fee (wallet signs via WC)
 * - Output 0: NFT to `recipientAddress`
 * - Output 1: BCH change back to `changeAddress` (if above dust)
 *
 * No covenant, no admin key, no private key ever required.
 *
 * @param params - Transfer parameters.
 * @returns Structured result with the WC transaction object, or error details.
 *
 * @example
 * ```ts
 * import { prepareTransferTransaction } from '@qubesai/sdk/covenant';
 *
 * const result = await prepareTransferTransaction({
 *   categoryId: 'abcd...64chars',
 *   senderAddress: 'bitcoincash:q...',
 *   recipientAddress: 'bitcoincash:z...',
 * });
 *
 * if (result.success) {
 *   // Pass result.wcTransaction to wallet via bch_signTransaction
 * }
 * ```
 */
export async function prepareTransferTransaction(
  params: WcTransferParams,
): Promise<WcTransferResult | TransferError> {
  // ── Validate ──────────────────────────────────────────────────────────────
  if (!params.categoryId || !HEX64_RE.test(params.categoryId)) {
    return { success: false, error: 'categoryId must be a 64-character hex string' };
  }
  if (!params.senderAddress) {
    return { success: false, error: 'senderAddress is required' };
  }
  if (!params.recipientAddress) {
    return { success: false, error: 'recipientAddress is required' };
  }

  const network = params.network ?? 'mainnet';
  const changeAddress = params.changeAddress ?? params.senderAddress;

  try {
    // ── Dynamic imports ──────────────────────────────────────────────────
    const [cashscript, libauth] = await Promise.all([loadCashscript(), loadLibauth()]);
    const { ElectrumNetworkProvider, TransactionBuilder, placeholderP2PKHUnlocker } = cashscript;
    const { stringify: libauthStringify, binToHex } = libauth;

    // ── Fetch UTXOs ──────────────────────────────────────────────────────
    const provider = new ElectrumNetworkProvider(network);
    const senderUtxos = await provider.getUtxos(params.senderAddress);

    // Find the NFT UTXO
    const nftUtxo = senderUtxos.find(
      (u: any) =>
        u.token?.category === params.categoryId && u.token?.nft !== undefined,
    );

    if (!nftUtxo) {
      return {
        success: false,
        error: `NFT not found in sender's wallet. category_id=${params.categoryId} address=${params.senderAddress}`,
      };
    }

    const { commitment, capability } = nftUtxo.token!.nft!;
    const commitmentHex: string =
      commitment instanceof Uint8Array
        ? binToHex(commitment)
        : typeof commitment === 'string'
          ? commitment
          : '';

    // Non-token UTXOs for fee
    const fundingUtxos = senderUtxos.filter((u: any) => !u.token);
    const totalFunding = fundingUtxos.reduce(
      (sum: bigint, u: any) => sum + u.satoshis,
      0n,
    );

    // ── Fee estimate (2 sat/byte) ────────────────────────────────────────
    const estimatedSize = BigInt(
      10 +                           // tx overhead
      148 +                          // NFT P2PKH input
      fundingUtxos.length * 148 +    // funding P2PKH inputs
      90 +                           // token output (NFT to recipient)
      34,                            // change output
    );
    const estimatedFee = estimatedSize * 2n;
    const minFunding = estimatedFee + 200n; // small safety buffer

    if (totalFunding < minFunding) {
      return {
        success: false,
        error: `Insufficient funds for fee. Need ~${minFunding} sats, have ${totalFunding} sats at ${params.senderAddress}`,
      };
    }

    // ── Build transaction ────────────────────────────────────────────────
    const txBuilder = new TransactionBuilder({ provider });

    // Input 0: NFT UTXO — wallet signs
    txBuilder.addInput(nftUtxo, placeholderP2PKHUnlocker(params.senderAddress));

    // Inputs 1+: funding UTXOs — wallet signs
    for (const utxo of fundingUtxos) {
      txBuilder.addInput(utxo, placeholderP2PKHUnlocker(params.senderAddress));
    }

    // Output 0: NFT to recipient
    txBuilder.addOutput({
      to: params.recipientAddress,
      amount: NFT_DUST,
      token: {
        amount: 0n,
        category: params.categoryId,
        nft: { capability, commitment },
      },
    });

    // Output 1: change back to sender (if above dust)
    const totalInput = nftUtxo.satoshis + totalFunding;
    const change = totalInput - NFT_DUST - estimatedFee;
    if (change >= DUST_LIMIT) {
      txBuilder.addOutput({ to: changeAddress, amount: change });
    }

    // ── Generate WC transaction object ───────────────────────────────────
    const wcTxObj = txBuilder.generateWcTransactionObject({
      broadcast: false,
      userPrompt: `Transfer Qube NFT to ${params.recipientAddress.slice(0, 28)}...`,
    });

    return {
      success: true,
      wcTransaction: libauthStringify(wcTxObj),
      categoryId: params.categoryId,
      commitment: commitmentHex,
    };
  } catch (err: any) {
    return {
      success: false,
      error: err?.message ?? String(err),
    };
  }
}
