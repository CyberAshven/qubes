/**
 * Qubes Covenant Deployment Script
 *
 * One-time script to instantiate the QubesMint covenant and display
 * the contract address. After running this, send the minting token
 * to the contract address using migrate.ts.
 *
 * Usage: npm run deploy
 *
 * Environment:
 *   PLATFORM_PUBLIC_KEY - Compressed public key hex (33 bytes / 66 chars)
 *                         of the platform's BCH key (fee recipient for migrate())
 */

import { Contract, ElectrumNetworkProvider } from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';

// ── Configuration ──────────────────────────────────────────────────

// The official Qubes CashToken category ID (genesis txid of minting token)
const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

// Platform public key (compressed hex, 33 bytes)
// This is the key that controls migrate() — NOT used for minting.
const PLATFORM_PUBLIC_KEY = process.env.PLATFORM_PUBLIC_KEY;

if (!PLATFORM_PUBLIC_KEY || PLATFORM_PUBLIC_KEY.length !== 66) {
  console.error('Error: Set PLATFORM_PUBLIC_KEY env var (66-char compressed hex pubkey)');
  console.error('Example: PLATFORM_PUBLIC_KEY=02abc123... npm run deploy');
  process.exit(1);
}

// ── Derive platformPkh (HASH160 of public key) ────────────────────

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
const platformPkh = hash160(pubkeyBytes);

console.log('Qubes Minting Covenant Deployment');
console.log('=================================');
console.log(`Platform public key: ${PLATFORM_PUBLIC_KEY}`);
console.log(`Platform PKH (HASH160): ${platformPkh.toString('hex')}`);
console.log(`Official category: ${OFFICIAL_CATEGORY}`);
console.log();

// ── Instantiate contract ───────────────────────────────────────────

const provider = new ElectrumNetworkProvider('mainnet');

const contract = new Contract(
  artifact,
  [platformPkh],
  { provider, addressType: 'p2sh32' }
);

console.log(`Contract address:       ${contract.address}`);
console.log(`Contract token address: ${contract.tokenAddress}`);
console.log(`Contract bytecode size: ${contract.bytesize} bytes`);
console.log();

// ── Check if minting token is already at the contract ──────────────

async function checkBalance() {
  try {
    const balance = await contract.getBalance();
    const utxos = await contract.getUtxos();

    console.log(`Contract balance: ${balance} satoshis`);
    console.log(`Contract UTXOs:   ${utxos.length}`);

    const mintingToken = utxos.find(
      u => u.token?.category === OFFICIAL_CATEGORY
        && u.token?.nft?.capability === 'minting'
    );

    if (mintingToken) {
      console.log();
      console.log('Minting token is already at the contract address!');
      console.log('The covenant is ready to mint.');
    } else {
      console.log();
      console.log('Minting token NOT found at contract address.');
      console.log('Next step: Run migrate.ts to send the minting token here.');
      console.log(`  Send to: ${contract.tokenAddress}`);
    }
  } catch (e) {
    console.error('Could not check balance:', e);
  }
}

await checkBalance();

// ── Output config for the app ──────────────────────────────────────

console.log();
console.log('Add to core/official_category.py:');
console.log(`  OFFICIAL_COVENANT_ADDRESS = "${contract.tokenAddress}"`);
