/**
 * Migrate the minting token from v1 contract to v2 contract.
 *
 * v1 had a bug: `this.activeBytecode` returns the redeem script in P2SH32 context,
 * not the P2SH32 locking pattern. v2 fixes this by comparing against
 * `tx.inputs[this.activeInputIndex].lockingBytecode` instead.
 *
 * Usage: npx tsx migrate-to-v2.ts <platform_wif>
 *
 * The platform WIF is the private key corresponding to PLATFORM_PUBLIC_KEY.
 * This calls the migrate() function on the v1 contract which requires
 * a valid signature from the platform key.
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder, SignatureTemplate, HashType
} from 'cashscript';
import artifactV1 from './qubes_mint.json' with { type: 'json' };
import artifactV2 from './qubes_mint_v2.json' with { type: 'json' };
import { createHash } from 'crypto';

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';
const PLATFORM_PUBLIC_KEY = '02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741';

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

// ── Parse CLI args ──────────────────────────────────────────────────
const platformWif = process.argv[2];
if (!platformWif) {
  console.error('Usage: npx tsx migrate-to-v2.ts <platform_wif>');
  console.error('\nThe platform WIF is the private key for:');
  console.error(`  Public key: ${PLATFORM_PUBLIC_KEY}`);
  process.exit(1);
}

try {
  const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
  const platformPkh = hash160(pubkeyBytes);
  const provider = new ElectrumNetworkProvider('mainnet');

  // Instantiate both contracts
  const contractV1 = new Contract(artifactV1, [platformPkh], { provider, addressType: 'p2sh32' });
  const contractV2 = new Contract(artifactV2, [platformPkh], { provider, addressType: 'p2sh32' });

  console.log(`v1 contract address:      ${contractV1.address}`);
  console.log(`v1 token address:         ${contractV1.tokenAddress}`);
  console.log(`v2 contract address:      ${contractV2.address}`);
  console.log(`v2 token address:         ${contractV2.tokenAddress}`);

  // Find the minting token at v1
  const v1Utxos = await contractV1.getUtxos();
  const mintingUtxo = v1Utxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY && u.token?.nft?.capability === 'minting'
  );

  if (!mintingUtxo) {
    console.error('\nERROR: Minting token not found at v1 contract!');
    console.error(`Looking for category: ${OFFICIAL_CATEGORY}`);
    console.error(`Available UTXOs: ${v1Utxos.length}`);
    for (const u of v1Utxos) {
      console.error(`  ${u.txid}:${u.vout} sat=${u.satoshis} cat=${u.token?.category || 'none'}`);
    }
    process.exit(1);
  }

  console.log(`\nMinting token UTXO: ${mintingUtxo.txid}:${mintingUtxo.vout}`);
  console.log(`  satoshis: ${mintingUtxo.satoshis}`);
  console.log(`  category: ${mintingUtxo.token!.category}`);
  console.log(`  capability: ${mintingUtxo.token!.nft!.capability}`);
  console.log(`  commitment: ${mintingUtxo.token!.nft!.commitment || '(empty)'}`);

  // Build migration transaction
  // The migrate() function only checks: hash160(platformPk) == platformPkh && checkSig(platformSig, platformPk)
  // It does NOT constrain outputs, so we can send the minting token anywhere.
  console.log(`\nBuilding migration transaction...`);

  const sigTemplate = new SignatureTemplate(platformWif, HashType.SIGHASH_ALL);

  const txBuilder = new TransactionBuilder({ provider });

  // Input: minting token from v1 contract, unlocked via migrate()
  txBuilder.addInput(
    mintingUtxo,
    contractV1.unlock.migrate(pubkeyBytes, sigTemplate)
  );

  // Output: minting token sent to v2 contract
  // 800 sat output + 200 sat fee = 1000 sat input
  txBuilder.addOutput({
    to: contractV2.tokenAddress,
    amount: 678n,
    token: {
      category: OFFICIAL_CATEGORY,
      amount: 0n,
      nft: {
        capability: 'minting',
        commitment: mintingUtxo.token!.nft!.commitment
      }
    }
  });

  // Debug first (local VM validation)
  console.log('Running local VM validation (debug)...');
  try {
    (txBuilder as any).debug();
    console.log('✓ Local VM validation PASSED');
  } catch (e: any) {
    console.error('✗ Local VM validation FAILED:', e.message);
    console.error('\nAborting migration — the transaction would fail on-chain.');
    process.exit(1);
  }

  // Send the transaction
  console.log('\nBroadcasting migration transaction...');
  const txResult = await txBuilder.send();
  console.log(`\n✓ Migration successful!`);
  console.log(`  TX ID: ${txResult.txid}`);
  console.log(`\nMinting token is now at v2 contract:`);
  console.log(`  Address: ${contractV2.tokenAddress}`);
  console.log(`\nNext steps:`);
  console.log(`  1. Replace qubes_mint.json with qubes_mint_v2.json`);
  console.log(`  2. Update OFFICIAL_CATEGORY if needed (it shouldn't change)`);
  console.log(`  3. Update server and frontend with new artifact`);

  process.exit(0);
} catch (e: any) {
  console.error('Error:', e.message || e);
  if (e.message?.includes('Signature')) {
    console.error('\nHint: Make sure the WIF matches the platform public key.');
  }
  process.exit(1);
}
