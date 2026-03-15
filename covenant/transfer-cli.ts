/**
 * Qubes NFT Transfer CLI
 *
 * Builds an unsigned WalletConnect transaction to transfer a Qube NFT from
 * the current owner to a new owner. No private keys required — the wallet
 * signs all inputs via WalletConnect.
 *
 * Usage: tsx transfer-cli.ts '<json_args>'
 *
 * JSON args:
 *   {
 *     "category_id": "64-char hex (NFT category ID)",
 *     "sender_address": "bitcoincash:q... (current owner's address from WC session)",
 *     "recipient_address": "bitcoincash:q... (new owner's token-aware address)",
 *     "change_address": "bitcoincash:q... (optional, defaults to sender_address)"
 *   }
 *
 * Output (JSON to stdout):
 *   {
 *     "success": true,
 *     "wc_transaction": "...stringified WC transaction object...",
 *     "category_id": "...",
 *     "commitment": "..."
 *   }
 *
 * Errors:
 *   { "success": false, "error": "..." }
 */

import {
  ElectrumNetworkProvider, TransactionBuilder, placeholderP2PKHUnlocker
} from 'cashscript';
import { stringify, binToHex } from '@bitauth/libauth';

// ── Helpers ────────────────────────────────────────────────────────

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
  category_id: string;
  sender_address: string;
  recipient_address: string;
  change_address?: string;
};

try {
  args = JSON.parse(rawArgs);
} catch {
  output({ success: false, error: 'Invalid JSON argument' });
  process.exit(1);
}

if (!args.category_id || args.category_id.length !== 64) {
  output({ success: false, error: 'category_id must be 64-char hex' });
  process.exit(1);
}
if (!args.sender_address) {
  output({ success: false, error: 'sender_address is required' });
  process.exit(1);
}
if (!args.recipient_address) {
  output({ success: false, error: 'recipient_address is required' });
  process.exit(1);
}

// ── Build transfer transaction ─────────────────────────────────────

try {
  const provider = new ElectrumNetworkProvider('mainnet');
  const senderAddress = args.sender_address;
  const changeAddress = args.change_address || senderAddress;

  // Fetch all UTXOs for the sender
  const senderUtxos = await provider.getUtxos(senderAddress);

  // Find the NFT UTXO with matching category_id
  const nftUtxo = senderUtxos.find(
    u => u.token?.category === args.category_id && u.token?.nft !== undefined
  );

  if (!nftUtxo) {
    output({
      success: false,
      error: `NFT not found in sender's wallet. category_id=${args.category_id} address=${senderAddress}`
    });
    process.exit(1);
  }

  const commitment = nftUtxo.token!.nft!.commitment;
  const capability = nftUtxo.token!.nft!.capability;

  // Convert commitment to hex string for output
  const commitmentHex = commitment instanceof Uint8Array
    ? binToHex(commitment)
    : typeof commitment === 'string' ? commitment : '';

  // Find non-token UTXOs for fee funding
  const fundingUtxos = senderUtxos.filter(u => !u.token);
  const totalFunding = fundingUtxos.reduce((sum, u) => sum + u.satoshis, 0n);

  const NFT_DUST = 1000n;

  // Fee estimate: NFT input + funding inputs + NFT output + change output
  const estimatedSize = BigInt(
    10 +                          // tx overhead
    148 +                         // NFT P2PKH input
    fundingUtxos.length * 148 +   // funding P2PKH inputs
    90 +                          // token output (NFT to recipient)
    34                            // change output
  );
  const feeRate = 2n; // sats/byte — safe margin above 1 sat/byte relay fee
  const estimatedFee = estimatedSize * feeRate;
  const MIN_FUNDING = estimatedFee + 200n; // small safety buffer

  if (totalFunding < MIN_FUNDING) {
    output({
      success: false,
      error: `Insufficient funds for fee. Need ~${MIN_FUNDING} sats, have ${totalFunding} sats at ${senderAddress}`
    });
    process.exit(1);
  }

  // Build transaction
  const txBuilder = new TransactionBuilder({ provider });

  // Input 0: NFT UTXO — wallet will sign with placeholder
  txBuilder.addInput(nftUtxo, placeholderP2PKHUnlocker(senderAddress));

  // Inputs 1+: funding UTXOs for fee
  for (const utxo of fundingUtxos) {
    txBuilder.addInput(utxo, placeholderP2PKHUnlocker(senderAddress));
  }

  // Output 0: NFT to recipient
  txBuilder.addOutput({
    to: args.recipient_address,
    amount: NFT_DUST,
    token: {
      amount: 0n,
      category: args.category_id,
      nft: { capability, commitment }
    }
  });

  // Output 1: change back to sender
  const totalInput = nftUtxo.satoshis + totalFunding;
  const change = totalInput - NFT_DUST - estimatedFee;
  if (change >= 546n) {
    txBuilder.addOutput({ to: changeAddress, amount: change });
  }

  // Build WC transaction object (wallet signs all P2PKH inputs)
  const wcTxObj = txBuilder.generateWcTransactionObject({
    broadcast: false,
    userPrompt: `Transfer Qube NFT to ${args.recipient_address.slice(0, 28)}...`
  });

  output({
    success: true,
    wc_transaction: stringify(wcTxObj),
    category_id: args.category_id,
    commitment: commitmentHex
  });

} catch (e: any) {
  output({
    success: false,
    error: e?.message || String(e)
  });
  process.exit(1);
}
