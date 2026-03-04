/**
 * Qubes Covenant Migration Script
 *
 * Sends the minting token from the platform's wallet to the covenant address.
 * Run this ONCE after deploy.ts to activate the covenant.
 *
 * Can also be used to migrate the minting token to a new covenant version.
 *
 * Usage: npm run migrate
 *
 * Environment:
 *   PLATFORM_BCH_MINTING_KEY - Platform wallet WIF private key
 *   PLATFORM_PUBLIC_KEY       - Platform compressed public key hex (66 chars)
 *   TARGET_CONTRACT_ADDRESS   - (Optional) Override target covenant address
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder, SignatureTemplate
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import {
  lockingBytecodeToCashAddress,
  addressContentsToLockingBytecode,
  LockingBytecodeType
} from '@bitauth/libauth';

// ── Configuration ──────────────────────────────────────────────────

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

const PLATFORM_WIF = process.env.PLATFORM_BCH_MINTING_KEY;
const PLATFORM_PUBLIC_KEY = process.env.PLATFORM_PUBLIC_KEY;

if (!PLATFORM_WIF) {
  console.error('Error: Set PLATFORM_BCH_MINTING_KEY env var (WIF private key)');
  process.exit(1);
}
if (!PLATFORM_PUBLIC_KEY || PLATFORM_PUBLIC_KEY.length !== 66) {
  console.error('Error: Set PLATFORM_PUBLIC_KEY env var (66-char compressed hex pubkey)');
  process.exit(1);
}

// ── Derive platformPkh ────────────────────────────────────────────

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
const platformPkh = hash160(pubkeyBytes);

// ── Instantiate contract ───────────────────────────────────────────

const provider = new ElectrumNetworkProvider('mainnet');
const sigTemplate = new SignatureTemplate(PLATFORM_WIF);

const contract = new Contract(
  artifact,
  [platformPkh],
  { provider, addressType: 'p2sh32' }
);

const targetAddress = process.env.TARGET_CONTRACT_ADDRESS || contract.tokenAddress;

console.log('Qubes Minting Token Migration');
console.log('=============================');
console.log(`Target covenant: ${targetAddress}`);
console.log();

// ── Find minting token in platform wallet ──────────────────────────

// Derive the platform's P2PKH address from the public key
const platformPubkey = sigTemplate.getPublicKey();
const platformPkhFromKey = hash160(Buffer.from(platformPubkey));
const lockingBytecode = Uint8Array.from([
  0x76, 0xa9, 0x14, ...platformPkhFromKey, 0x88, 0xac
]);
const addressResult = lockingBytecodeToCashAddress({ bytecode: lockingBytecode, prefix: 'bitcoincash', tokenSupport: true });
if (typeof addressResult !== 'string') {
  console.error('Error: Could not derive platform address');
  process.exit(1);
}
const platformAddress = addressResult;

console.log(`Platform address: ${platformAddress}`);
console.log('Looking up UTXOs...');

// Query UTXOs at platform address
const platformUtxos = await provider.getUtxos(platformAddress);
console.log(`Found ${platformUtxos.length} UTXOs at platform address`);

const mintingTokenUtxo = platformUtxos.find(
  u => u.token?.category === OFFICIAL_CATEGORY
    && u.token?.nft?.capability === 'minting'
);

if (!mintingTokenUtxo) {
  // Check if it's already at the contract
  const contractUtxos = await contract.getUtxos();
  const alreadyAtContract = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY
      && u.token?.nft?.capability === 'minting'
  );

  if (alreadyAtContract) {
    console.log('Minting token is already at the covenant address. Nothing to do.');
    process.exit(0);
  }

  console.error('Error: Minting token not found in platform wallet or covenant.');
  console.error(`Looking for category: ${OFFICIAL_CATEGORY}`);
  process.exit(1);
}

console.log(`Found minting token: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);
console.log(`  Value: ${mintingTokenUtxo.satoshis} sats`);
console.log(`  Category: ${mintingTokenUtxo.token!.category}`);
console.log(`  Capability: ${mintingTokenUtxo.token!.nft!.capability}`);
console.log();

// ── Build migration transaction ────────────────────────────────────

// Find a BCH-only UTXO for fees (if the minting token UTXO doesn't have enough)
const feeUtxo = platformUtxos.find(
  u => !u.token && u.satoshis >= 1000n
);

console.log('Building migration transaction...');

const txBuilder = new TransactionBuilder({ provider });

// Input 0: minting token UTXO
txBuilder.addInput(mintingTokenUtxo, sigTemplate.unlockP2PKH());

// Input 1: fee UTXO (if separate)
if (feeUtxo && mintingTokenUtxo.satoshis < 2000n) {
  txBuilder.addInput(feeUtxo, sigTemplate.unlockP2PKH());
}

// Output 0: minting token to covenant address
txBuilder.addOutput({
  to: targetAddress,
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

// Output 1: change back to platform (if any)
const totalInput = mintingTokenUtxo.satoshis + (feeUtxo ? feeUtxo.satoshis : 0n);
const change = totalInput - 1000n - 500n; // 500 sat mining fee estimate
if (change >= 546n) {
  txBuilder.addOutput({
    to: platformAddress,
    amount: change
  });
}

// ── Send ────────────────────────────────────────────────────────────

try {
  const tx = await txBuilder.send();
  console.log();
  console.log('Migration successful!');
  console.log(`  TXID: ${tx.txid}`);
  console.log(`  Minting token is now at: ${targetAddress}`);
  console.log();
  console.log('The covenant is ready to mint Qube NFTs.');
} catch (e) {
  console.error('Migration failed:', e);
  process.exit(1);
}
