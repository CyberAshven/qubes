/**
 * Electrum Connectivity Test — Mainnet
 *
 * Proves that CashScript's ElectrumNetworkProvider connects to
 * real BCH infrastructure (Fulcrum/Electrum servers backed by full nodes).
 *
 * Run: npx tsx test-electrum.ts
 */

import { ElectrumNetworkProvider } from 'cashscript';

const COVENANT_ADDRESS = 'bitcoincash:rdlqc0y2ulzyp0ulk3t6gn56lzrxt2fq7s2j232vzghww6m8mtqr7h0rx97sy';
const CATEGORY_ID = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

async function main() {
  console.log('=== Electrum Connectivity Test (Mainnet) ===\n');

  // Step 1: Connect to Electrum network
  console.log('1. Connecting to ElectrumNetworkProvider("mainnet")...');
  const provider = new ElectrumNetworkProvider('mainnet');
  console.log('   OK — Provider created\n');

  // Step 2: Query the known covenant address directly
  console.log('2. Querying covenant address for UTXOs...');
  console.log(`   Address: ${COVENANT_ADDRESS}`);
  const utxos = await provider.getUtxos(COVENANT_ADDRESS);
  console.log(`   PASS — Electrum responded with ${utxos.length} UTXO(s)\n`);

  // Step 3: Find minting token
  console.log('3. Looking for minting token...');
  const mintingUtxo = utxos.find(
    (u: any) =>
      u.token?.category === CATEGORY_ID &&
      u.token?.nft?.capability === 'minting',
  );

  if (mintingUtxo) {
    console.log('   PASS — Minting token FOUND');
    console.log(`   Category:   ${mintingUtxo.token!.category}`);
    console.log(`   Capability: ${mintingUtxo.token!.nft!.capability}`);
    console.log(`   Satoshis:   ${mintingUtxo.satoshis}`);
    console.log(`   TXID:       ${mintingUtxo.txid}`);
    console.log(`   Vout:       ${mintingUtxo.vout}\n`);
  } else {
    console.log('   WARN — Minting token not found at this address');
    if (utxos.length > 0) {
      console.log('   UTXOs present:');
      for (const u of utxos) {
        console.log(`     txid=${u.txid}:${u.vout} sats=${u.satoshis} token=${u.token?.category ?? 'none'} cap=${u.token?.nft?.capability ?? 'n/a'}`);
      }
    }
    console.log();
  }

  // Step 4: List all UTXOs at covenant address
  if (utxos.length > 0) {
    console.log('4. All UTXOs at covenant address:');
    for (const u of utxos) {
      console.log(`   - ${u.txid}:${u.vout}`);
      console.log(`     sats: ${u.satoshis}`);
      if (u.token) {
        console.log(`     token category: ${u.token.category}`);
        console.log(`     nft capability: ${u.token.nft?.capability ?? 'none'}`);
        console.log(`     nft commitment: ${u.token.nft?.commitment ?? 'none'}`);
      }
    }
    console.log();
  }

  // Summary
  console.log('=== RESULTS ===');
  console.log(`Electrum connected:    PASS — successfully queried mainnet`);
  console.log(`Covenant has UTXOs:    ${utxos.length > 0 ? 'PASS' : 'WARN — 0 UTXOs'}`);
  console.log(`Minting token live:    ${mintingUtxo ? 'PASS' : 'WARN — not found'}`);
  console.log();
  console.log('ElectrumNetworkProvider connects to Fulcrum servers');
  console.log('(Electrum protocol backed by full BCH nodes).');
  console.log('Same architecture as Electron Cash, Cashonize, etc.');
  console.log('No RpcKit needed — CashScript speaks Electrum natively.');

  process.exit(0);
}

main().catch((err) => {
  console.error('FAIL:', err.message || err);
  process.exit(1);
});
