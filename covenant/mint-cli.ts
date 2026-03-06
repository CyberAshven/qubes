/**
 * Qubes Covenant Mint CLI
 *
 * Builds and broadcasts a covenant mint transaction.
 * Called by Python (blockchain/covenant_client.py) via subprocess.
 *
 * Usage: tsx mint-cli.ts '<json_args>'
 *
 * JSON args (broadcast mode — default):
 *   {
 *     "commitment": "64-char hex (32 bytes)",
 *     "recipient_address": "bitcoincash:z... (token-aware cashaddr)",
 *     "wallet_wif": "WIF private key for funding",
 *     "platform_public_key": "66-char compressed hex pubkey"
 *   }
 *
 * JSON args (walletconnect mode):
 *   {
 *     "commitment": "64-char hex (32 bytes)",
 *     "recipient_address": "bitcoincash:z... (token-aware cashaddr)",
 *     "user_address": "bitcoincash:z... (user's token-aware address from WC)",
 *     "platform_public_key": "66-char compressed hex pubkey",
 *     "mode": "walletconnect"
 *   }
 *
 * Output — broadcast mode (JSON to stdout):
 *   {
 *     "success": true,
 *     "mint_txid": "...",
 *     "category_id": "...",
 *     "commitment": "...",
 *     "covenant_address": "..."
 *   }
 *
 * Output — walletconnect mode (JSON to stdout):
 *   {
 *     "success": true,
 *     "mode": "walletconnect",
 *     "wc_transaction": "...stringified WC transaction object...",
 *     "category_id": "...",
 *     "commitment": "...",
 *     "covenant_address": "..."
 *   }
 *
 * Errors (JSON to stdout):
 *   { "success": false, "error": "..." }
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder, SignatureTemplate,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import { lockingBytecodeToCashAddress, stringify } from '@bitauth/libauth';

// ── Constants ──────────────────────────────────────────────────────

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

// ── Helpers ────────────────────────────────────────────────────────

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

function output(data: object) {
  console.log(JSON.stringify(data));
}

// ── Parse args ─────────────────────────────────────────────────────

const rawArgs = process.argv[2];
if (!rawArgs) {
  output({ success: false, error: 'Missing JSON argument' });
  process.exit(1);
}

let args: {
  commitment: string;
  recipient_address: string;
  wallet_wif?: string;
  user_address?: string;
  platform_public_key: string;
  mode?: 'walletconnect';
};

try {
  args = JSON.parse(rawArgs);
} catch {
  output({ success: false, error: 'Invalid JSON argument' });
  process.exit(1);
}

const isWcMode = args.mode === 'walletconnect';

// Validate common fields
if (!args.commitment || args.commitment.length !== 64) {
  output({ success: false, error: 'commitment must be 64-char hex (32 bytes)' });
  process.exit(1);
}
if (!args.recipient_address) {
  output({ success: false, error: 'recipient_address is required' });
  process.exit(1);
}
if (!args.platform_public_key || args.platform_public_key.length !== 66) {
  output({ success: false, error: 'platform_public_key must be 66-char compressed hex' });
  process.exit(1);
}

// Mode-specific validation
if (isWcMode) {
  if (!args.user_address) {
    output({ success: false, error: 'user_address is required in walletconnect mode' });
    process.exit(1);
  }
} else {
  if (!args.wallet_wif) {
    output({ success: false, error: 'wallet_wif is required in broadcast mode' });
    process.exit(1);
  }
}

// ── Set up contract ────────────────────────────────────────────────

try {
  const pubkeyBytes = Buffer.from(args.platform_public_key, 'hex');
  const platformPkh = hash160(pubkeyBytes);

  const provider = new ElectrumNetworkProvider('mainnet');

  const contract = new Contract(
    artifact,
    [platformPkh],
    { provider, addressType: 'p2sh32' }
  );

  // ── Find minting token at covenant ─────────────────────────────

  const contractUtxos = await contract.getUtxos();
  const mintingTokenUtxo = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY
      && u.token?.nft?.capability === 'minting'
  );

  if (!mintingTokenUtxo) {
    output({
      success: false,
      error: `Minting token not found at covenant address ${contract.tokenAddress}`
    });
    process.exit(1);
  }

  // ── Resolve user address ─────────────────────────────────────────

  let userAddress: string;

  if (isWcMode) {
    // WalletConnect mode: address provided directly by the connected wallet
    userAddress = args.user_address!;
  } else {
    // Broadcast mode: derive address from WIF
    const userTemplate = new SignatureTemplate(args.wallet_wif!);
    const userPubkey = userTemplate.getPublicKey();
    const userPkh = hash160(Buffer.from(userPubkey));
    const userLockingBytecode = Uint8Array.from([
      0x76, 0xa9, 0x14, ...userPkh, 0x88, 0xac
    ]);
    const userAddrResult = lockingBytecodeToCashAddress({ bytecode: userLockingBytecode, prefix: 'bitcoincash', tokenSupport: true }) as any;
    userAddress = typeof userAddrResult === 'string' ? userAddrResult : userAddrResult?.address;
    if (!userAddress) {
      output({ success: false, error: `Could not derive user address from WIF: ${JSON.stringify(userAddrResult)}` });
      process.exit(1);
    }
  }

  // ── Get user's funding UTXOs ───────────────────────────────────

  const userUtxos = await provider.getUtxos(userAddress);

  // Find non-token UTXOs for funding (need enough for 1000 sats NFT dust + mining fee)
  const fundingUtxos = userUtxos.filter(u => !u.token);
  const totalFunding = fundingUtxos.reduce((sum, u) => sum + u.satoshis, 0n);

  const MIN_FUNDING = 3000n; // 1000 NFT dust + ~2000 mining fee (covenant txs are large)
  if (totalFunding < MIN_FUNDING) {
    output({
      success: false,
      error: `Insufficient funds. Need at least ${MIN_FUNDING} sats, have ${totalFunding} sats at ${userAddress}`
    });
    process.exit(1);
  }

  // ── Build mint transaction ─────────────────────────────────────

  const txBuilder = new TransactionBuilder({ provider });

  // Input 0: covenant UTXO (minting token) — unlocked via contract.unlock.mint()
  txBuilder.addInput(
    mintingTokenUtxo,
    contract.unlock.mint(Buffer.from(args.commitment, 'hex'))
  );

  // Input 1+: user's funding UTXOs
  if (isWcMode) {
    // WalletConnect: use placeholder unlocker — wallet will substitute real sig
    for (const utxo of fundingUtxos) {
      txBuilder.addInput(utxo, placeholderP2PKHUnlocker(userAddress));
    }
  } else {
    // Broadcast: use real signature template
    const userTemplate = new SignatureTemplate(args.wallet_wif!);
    for (const utxo of fundingUtxos) {
      txBuilder.addInput(utxo, userTemplate.unlockP2PKH());
    }
  }

  // Output 0: minting token returned to covenant
  txBuilder.addOutput({
    to: contract.tokenAddress,
    amount: 1000n,
    token: {
      amount: 0n,
      category: OFFICIAL_CATEGORY,
      nft: {
        capability: 'minting',
        commitment: mintingTokenUtxo.token!.nft!.commitment
      }
    }
  });

  // Output 1: immutable NFT to user
  txBuilder.addOutput({
    to: args.recipient_address,
    amount: 1000n,
    token: {
      amount: 0n,
      category: OFFICIAL_CATEGORY,
      nft: {
        capability: 'none',
        commitment: args.commitment
      }
    }
  });

  // Output 2: change back to user (if any)
  // Fee estimation: P2SH32 covenant input is large (~300 bytes for redeem script),
  // each P2PKH input ~148 bytes, token outputs ~90 bytes, change ~34 bytes.
  // Use 2 sat/byte for safety margin above the 1 sat/byte minimum relay fee.
  const estimatedSize = BigInt(
    10                          // tx overhead
    + 300                       // covenant P2SH32 input (with redeem script)
    + fundingUtxos.length * 148 // P2PKH funding inputs
    + 90 * 2                    // 2 token outputs (covenant return + NFT)
    + 34                        // change output
  );
  const feeRate = 2n; // sats per byte
  const estimatedFee = estimatedSize * feeRate;

  const totalInput = mintingTokenUtxo.satoshis + totalFunding;
  const totalOutputs = 1000n + 1000n; // covenant dust + NFT dust
  const change = totalInput - totalOutputs - estimatedFee;

  if (change >= 546n) {
    txBuilder.addOutput({
      to: userAddress,
      amount: change
    });
  }

  // ── Execute ──────────────────────────────────────────────────────

  if (isWcMode) {
    // WalletConnect mode: return transaction object for wallet signing.
    // The covenant input (input 0) is fully unlocked by CashScript — no wallet
    // interaction needed. Only the user's P2PKH inputs (1+) need wallet signatures.
    //
    // We strip the `contract` metadata from sourceOutputs because:
    // - Our mint() function is permissionless (no sig/pubkey args from wallet)
    // - The unlock script is already complete with the commitment value
    // - Contract metadata causes wallets to try to re-process the covenant input
    // The wallet will see input 0 as a non-wallet input and leave it unchanged.
    const wcTxObj = txBuilder.generateWcTransactionObject({
      broadcast: false,
      userPrompt: 'Mint Qube NFT'
    });

    // Remove contract metadata — covenant input is already fully unlocked
    for (const so of (wcTxObj as any).sourceOutputs) {
      delete so.contract;
    }

    output({
      success: true,
      mode: 'walletconnect',
      wc_transaction: stringify(wcTxObj),
      category_id: OFFICIAL_CATEGORY,
      commitment: args.commitment,
      covenant_address: contract.tokenAddress,
      recipient_address: args.recipient_address
    });
  } else {
    // Broadcast mode: sign and broadcast immediately
    const tx = await txBuilder.send();

    output({
      success: true,
      mint_txid: tx.txid,
      category_id: OFFICIAL_CATEGORY,
      commitment: args.commitment,
      covenant_address: contract.tokenAddress,
      recipient_address: args.recipient_address
    });
  }

} catch (e: any) {
  output({
    success: false,
    error: e.message || String(e)
  });
  process.exit(1);
}
