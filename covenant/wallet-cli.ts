/**
 * Qubes Wallet CLI
 *
 * Builds and optionally broadcasts CashScript wallet transactions.
 * Called by Python (blockchain/wallet_contract_client.py) via subprocess.
 *
 * Usage: tsx wallet-cli.ts '<json_args>'
 *
 * Modes:
 *
 * 1. derive_address — Derive contract address from owner + qube pubkeys
 *    { "mode": "derive_address", "owner_pubkey": "66-char hex", "qube_pubkey": "66-char hex" }
 *    → { "success": true, "contract_address": "bitcoincash:p...", "token_address": "bitcoincash:r..." }
 *
 * 2. owner_spend_broadcast — Owner withdraws, sign + broadcast immediately
 *    { "mode": "owner_spend_broadcast", "owner_pubkey": "...", "qube_pubkey": "...",
 *      "owner_wif": "WIF", "outputs": [{"address": "...", "value": 1000}] }
 *    → { "success": true, "txid": "..." }
 *
 * 3. owner_spend_wc — Owner withdraws via WalletConnect
 *    { "mode": "owner_spend_wc", "owner_pubkey": "...", "qube_pubkey": "...",
 *      "owner_address": "bitcoincash:q...", "outputs": [...] }
 *    → { "success": true, "wc_transaction": "..." }
 *
 * 4. qube_approved_broadcast — Qube proposes + owner co-signs, broadcast immediately
 *    { "mode": "qube_approved_broadcast", "owner_pubkey": "...", "qube_pubkey": "...",
 *      "qube_wif": "WIF", "owner_wif": "WIF", "outputs": [...] }
 *    → { "success": true, "txid": "..." }
 *
 * 5. qube_approved_wc — Qube proposes, owner signs via WalletConnect
 *    { "mode": "qube_approved_wc", "owner_pubkey": "...", "qube_pubkey": "...",
 *      "qube_wif": "WIF", "owner_address": "bitcoincash:q...", "outputs": [...] }
 *    → { "success": true, "wc_transaction": "..." }
 *
 * Errors: { "success": false, "error": "..." }
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder, SignatureTemplate,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_wallet.json' with { type: 'json' };
import { createHash } from 'crypto';
import { lockingBytecodeToCashAddress, stringify } from '@bitauth/libauth';

// ── Helpers ────────────────────────────────────────────────────────

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

function output(data: object) {
  console.log(JSON.stringify(data));
}

function addressFromWif(wif: string): string {
  const template = new SignatureTemplate(wif);
  const pubkey = template.getPublicKey();
  const pkh = hash160(Buffer.from(pubkey));
  const lockingBytecode = Uint8Array.from([0x76, 0xa9, 0x14, ...pkh, 0x88, 0xac]);
  const result = lockingBytecodeToCashAddress({
    bytecode: lockingBytecode, prefix: 'bitcoincash', tokenSupport: false
  }) as any;
  const addr = typeof result === 'string' ? result : result?.address;
  if (!addr) throw new Error(`Could not derive address from WIF: ${JSON.stringify(result)}`);
  return addr;
}

// ── Parse args ─────────────────────────────────────────────────────

const rawArgs = process.argv[2];
if (!rawArgs) {
  output({ success: false, error: 'Missing JSON argument' });
  process.exit(1);
}

let args: {
  mode: string;
  owner_pubkey: string;
  qube_pubkey: string;
  owner_wif?: string;
  qube_wif?: string;
  owner_address?: string;
  outputs?: { address: string; value: number }[];
};

try {
  args = JSON.parse(rawArgs);
} catch {
  output({ success: false, error: 'Invalid JSON argument' });
  process.exit(1);
}

// Validate common fields
if (!args.mode) {
  output({ success: false, error: 'mode is required' });
  process.exit(1);
}
if (!args.owner_pubkey || args.owner_pubkey.length !== 66) {
  output({ success: false, error: 'owner_pubkey must be 66-char compressed hex' });
  process.exit(1);
}
if (!args.qube_pubkey || args.qube_pubkey.length !== 66) {
  output({ success: false, error: 'qube_pubkey must be 66-char compressed hex' });
  process.exit(1);
}

// ── Set up contract ────────────────────────────────────────────────

try {
  const ownerPkh = hash160(Buffer.from(args.owner_pubkey, 'hex'));
  const qubePkh = hash160(Buffer.from(args.qube_pubkey, 'hex'));

  // For derive_address, skip network provider (no network needed)
  if (args.mode === 'derive_address') {
    const provider = new ElectrumNetworkProvider('mainnet');
    const contract = new Contract(
      artifact,
      [ownerPkh, qubePkh],
      { provider, addressType: 'p2sh32' }
    );
    output({
      success: true,
      contract_address: contract.address,
      token_address: contract.tokenAddress
    });
    process.exit(0);
  }

  // Transaction modes need network access
  const provider = new ElectrumNetworkProvider('mainnet');

  const contract = new Contract(
    artifact,
    [ownerPkh, qubePkh],
    { provider, addressType: 'p2sh32' }
  );

  // ── Validate outputs for transaction modes ─────────────────────

  if (!args.outputs || !Array.isArray(args.outputs) || args.outputs.length === 0) {
    output({ success: false, error: 'outputs array is required for transaction modes' });
    process.exit(1);
  }

  // ── Resolve owner address ─────────────────────────────────────

  let ownerAddress: string;
  const isWcMode = args.mode.endsWith('_wc');

  if (isWcMode) {
    if (!args.owner_address) {
      output({ success: false, error: 'owner_address is required in WC modes' });
      process.exit(1);
    }
    ownerAddress = args.owner_address;
  } else {
    if (!args.owner_wif) {
      output({ success: false, error: 'owner_wif is required in broadcast modes' });
      process.exit(1);
    }
    ownerAddress = addressFromWif(args.owner_wif);
  }

  // ── Get contract UTXOs ────────────────────────────────────────

  const contractUtxos = await contract.getUtxos();
  const bchUtxos = contractUtxos.filter(u => !u.token);

  if (bchUtxos.length === 0) {
    output({ success: false, error: `No BCH UTXOs at contract address ${contract.address}` });
    process.exit(1);
  }

  // ── Get owner P2PKH UTXOs (for the authorization input) ───────

  const ownerUtxos = await provider.getUtxos(ownerAddress);
  const ownerBchUtxos = ownerUtxos.filter(u => !u.token);

  if (ownerBchUtxos.length === 0) {
    output({
      success: false,
      error: `No BCH UTXOs at owner address ${ownerAddress}. Owner needs at least one UTXO for authorization.`
    });
    process.exit(1);
  }

  // Use the smallest owner UTXO for authorization (minimize locked value)
  const ownerAuthUtxo = ownerBchUtxos.sort((a, b) =>
    Number(a.satoshis - b.satoshis)
  )[0];

  // ── Calculate amounts ─────────────────────────────────────────

  const totalOutputValue = args.outputs.reduce((sum, o) => sum + BigInt(o.value), 0n);
  const totalContractValue = bchUtxos.reduce((sum, u) => sum + u.satoshis, 0n);
  const ownerAuthValue = ownerAuthUtxo.satoshis;

  // Fee estimation:
  // - Each P2SH32 contract input: ~200 bytes (redeem script is small for this contract)
  // - Owner P2PKH input: ~148 bytes
  // - Each output: ~34 bytes
  // - Tx overhead: ~10 bytes
  const estimatedSize = BigInt(
    10
    + bchUtxos.length * 200   // contract inputs
    + 148                      // owner P2PKH input
    + (args.outputs.length + 2) * 34  // outputs + potential change (contract + owner)
  );
  const estimatedFee = estimatedSize * 2n; // 2 sat/byte safety margin

  const totalInput = totalContractValue + ownerAuthValue;
  const contractChange = totalContractValue - totalOutputValue;
  const ownerChange = ownerAuthValue;
  // Fee comes out of the combined change
  const totalChange = totalInput - totalOutputValue - estimatedFee;

  if (totalChange < 0n) {
    output({
      success: false,
      error: `Insufficient funds. Contract has ${totalContractValue} sats, owner auth UTXO has ${ownerAuthValue} sats, need ${totalOutputValue + estimatedFee} sats (${totalOutputValue} + ~${estimatedFee} fee)`
    });
    process.exit(1);
  }

  // ── Build transaction ─────────────────────────────────────────

  const txBuilder = new TransactionBuilder({ provider });

  const isQubeApproved = args.mode.startsWith('qube_approved');
  const isOwnerSpend = args.mode.startsWith('owner_spend');

  if (!isQubeApproved && !isOwnerSpend) {
    output({ success: false, error: `Unknown mode: ${args.mode}` });
    process.exit(1);
  }

  // Add contract inputs (all BCH UTXOs at the contract address)
  // The owner P2PKH input will be at index = bchUtxos.length
  const ownerInputIndex = BigInt(bchUtxos.length);

  if (isOwnerSpend) {
    for (const utxo of bchUtxos) {
      txBuilder.addInput(utxo, contract.unlock.ownerSpend(ownerInputIndex));
    }
  } else {
    // qube_approved — need qube signature
    if (!args.qube_wif) {
      output({ success: false, error: 'qube_wif is required for qube_approved modes' });
      process.exit(1);
    }
    const qubeTemplate = new SignatureTemplate(args.qube_wif);
    const qubePubkeyBytes = qubeTemplate.getPublicKey();

    for (const utxo of bchUtxos) {
      txBuilder.addInput(
        utxo,
        contract.unlock.qubeApproved(qubeTemplate, qubePubkeyBytes, ownerInputIndex)
      );
    }
  }

  // Add owner P2PKH input (authorization)
  if (isWcMode) {
    txBuilder.addInput(ownerAuthUtxo, placeholderP2PKHUnlocker(ownerAddress));
  } else {
    const ownerTemplate = new SignatureTemplate(args.owner_wif!);
    txBuilder.addInput(ownerAuthUtxo, ownerTemplate.unlockP2PKH());
  }

  // Add requested outputs
  for (const out of args.outputs) {
    txBuilder.addOutput({ to: out.address, amount: BigInt(out.value) });
  }

  // Add change outputs
  // Contract change goes back to contract address, owner change back to owner
  // Split the total change: contract gets back what it had minus what was sent,
  // owner gets back their auth UTXO value minus any fee contribution
  const contractChangeAmount = totalContractValue - totalOutputValue;
  const ownerChangeAmount = totalChange - (contractChangeAmount > 0n ? contractChangeAmount : 0n);

  if (contractChangeAmount >= 546n) {
    txBuilder.addOutput({ to: contract.address, amount: contractChangeAmount });
  }
  if (ownerChangeAmount >= 546n) {
    txBuilder.addOutput({ to: ownerAddress, amount: ownerChangeAmount });
  }

  // ── Execute ──────────────────────────────────────────────────────

  if (isWcMode) {
    const wcTxObj = txBuilder.generateWcTransactionObject({
      broadcast: false,
      userPrompt: isOwnerSpend ? 'Wallet: Owner Withdraw' : 'Wallet: Approve Transaction'
    });

    // Remove contract metadata from sourceOutputs — contract inputs are already unlocked
    for (const so of (wcTxObj as any).sourceOutputs) {
      delete so.contract;
    }

    output({
      success: true,
      mode: 'walletconnect',
      wc_transaction: stringify(wcTxObj),
      contract_address: contract.address
    });
  } else {
    const tx = await txBuilder.send();

    output({
      success: true,
      txid: tx.txid,
      contract_address: contract.address
    });
  }

} catch (e: any) {
  output({
    success: false,
    error: e?.message || String(e)
  });
  process.exit(1);
}
