/**
 * Decode a signed transaction hex and compare with the expected covenant transaction.
 *
 * Usage: npx tsx decode-signed-tx.ts <signed_tx_hex>
 *   or:  npx tsx decode-signed-tx.ts --file signed-mint-tx.hex
 *
 * Builds the expected transaction from the current covenant state, decodes the signed
 * transaction, and reports byte-by-byte differences.
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import { readFileSync } from 'fs';
import {
  decodeTransaction, hexToBin, binToHex, encodeTransaction, stringify
} from '@bitauth/libauth';

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';
const PLATFORM_PUBLIC_KEY = '02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741';

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

// ── Parse CLI args ──────────────────────────────────────────────────

let signedTxHex: string;

if (process.argv[2] === '--file') {
  const filePath = process.argv[3];
  if (!filePath) { console.error('Usage: --file <path>'); process.exit(1); }
  signedTxHex = readFileSync(filePath, 'utf-8').trim();
} else if (process.argv[2]) {
  signedTxHex = process.argv[2].trim();
} else {
  console.error('Usage: npx tsx decode-signed-tx.ts <hex> OR --file <path>');
  process.exit(1);
}

console.log(`Signed tx hex: ${signedTxHex.length} chars (${signedTxHex.length / 2} bytes)`);

// ── Decode signed transaction ───────────────────────────────────────

const signedDecoded = decodeTransaction(hexToBin(signedTxHex));
if (typeof signedDecoded === 'string') {
  console.error('Failed to decode signed transaction:', signedDecoded);
  process.exit(1);
}

console.log(`\n=== Signed Transaction Structure ===`);
console.log(`Version: ${signedDecoded.version}`);
console.log(`Locktime: ${signedDecoded.locktime}`);
console.log(`Inputs: ${signedDecoded.inputs.length}`);
console.log(`Outputs: ${signedDecoded.outputs.length}`);

// ── Dump signed tx details ──────────────────────────────────────────

for (let i = 0; i < signedDecoded.inputs.length; i++) {
  const inp = signedDecoded.inputs[i];
  console.log(`\nInput ${i}:`);
  console.log(`  outpoint: ${binToHex(inp.outpointTransactionHash.slice().reverse())}:${inp.outpointIndex}`);
  console.log(`  sequence: ${inp.sequenceNumber}`);
  console.log(`  unlockingBytecode: ${binToHex(inp.unlockingBytecode)} (${inp.unlockingBytecode.length} bytes)`);
}

for (let i = 0; i < signedDecoded.outputs.length; i++) {
  const out = signedDecoded.outputs[i];
  console.log(`\nOutput ${i}:`);
  console.log(`  lockingBytecode: ${binToHex(out.lockingBytecode)} (${out.lockingBytecode.length} bytes)`);
  console.log(`  valueSatoshis: ${out.valueSatoshis}`);
  if (out.token) {
    const catHex = binToHex(out.token.category);
    const catDisplay = binToHex(out.token.category.slice().reverse());
    console.log(`  token.category: ${catHex} (display: ${catDisplay})`);
    console.log(`  token.amount: ${out.token.amount}`);
    if (out.token.nft) {
      console.log(`  token.nft.capability: ${out.token.nft.capability}`);
      console.log(`  token.nft.commitment: ${binToHex(out.token.nft.commitment)} (${out.token.nft.commitment.length} bytes)`);
    }
  }
}

// ── Build expected transaction for comparison ───────────────────────

console.log(`\n=== Building Expected Transaction ===`);

try {
  const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
  const platformPkh = hash160(pubkeyBytes);
  const provider = new ElectrumNetworkProvider('mainnet');
  const contract = new Contract(artifact, [platformPkh], { provider, addressType: 'p2sh32' });

  console.log(`Contract tokenAddress: ${contract.tokenAddress}`);

  // Get covenant UTXOs
  const contractUtxos = await contract.getUtxos();
  const mintingTokenUtxo = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY && u.token?.nft?.capability === 'minting'
  );

  if (!mintingTokenUtxo) {
    console.log('WARNING: Minting token not found at covenant. Cannot compare inputs.');
  } else {
    console.log(`Minting UTXO: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);

    // Check if signed tx input 0 matches the minting UTXO
    if (signedDecoded.inputs.length > 0) {
      const signedOutpoint = binToHex(signedDecoded.inputs[0].outpointTransactionHash.slice().reverse());
      const signedVout = signedDecoded.inputs[0].outpointIndex;
      const matches = signedOutpoint === mintingTokenUtxo.txid && signedVout === mintingTokenUtxo.vout;
      console.log(`Input 0 outpoint match: ${matches ? '✓' : '✗'} (signed: ${signedOutpoint}:${signedVout})`);
      if (!matches) {
        console.log(`  Expected: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);
        console.log('  The minting UTXO may have changed since the transaction was built!');
      }
    }
  }

  // Check output 0 lockingBytecode against contract's P2SH32
  console.log(`\n=== Covenant Check 1: tx.outputs[0].lockingBytecode == this.activeBytecode ===`);
  const contractBytecode = contract.bytecode;
  const sha256_1 = createHash('sha256').update(contractBytecode).digest();
  const sha256_2 = createHash('sha256').update(sha256_1).digest();
  const expectedP2sh32Lock = Buffer.concat([
    Buffer.from([0xaa]),  // OP_HASH256
    Buffer.from([0x20]),  // Push 32 bytes
    sha256_2,
    Buffer.from([0x87])   // OP_EQUAL
  ]);
  const expectedLockHex = expectedP2sh32Lock.toString('hex');

  if (signedDecoded.outputs.length > 0) {
    const out0Lock = binToHex(signedDecoded.outputs[0].lockingBytecode);
    const match = out0Lock === expectedLockHex;
    console.log(`Expected: ${expectedLockHex}`);
    console.log(`Signed:   ${out0Lock}`);
    console.log(`Check 1:  ${match ? '✓ PASS' : '✗ FAIL'}`);
  }

  // Check output 0 token category (should be minting)
  console.log(`\n=== Covenant Check 2: tx.outputs[0].tokenCategory == input[0].tokenCategory ===`);
  if (signedDecoded.outputs[0]?.token) {
    const out0Cat = binToHex(signedDecoded.outputs[0].token.category);
    const out0Cap = signedDecoded.outputs[0].token.nft?.capability || 'none';
    console.log(`Output 0 category: ${out0Cat} capability: ${out0Cap}`);
    // For minting, introspection returns category || 0x02
    console.log(`Check 2: ${out0Cap === 'minting' ? '✓ Category has minting flag' : '✗ Expected minting capability'}`);
  } else {
    console.log('Check 2: ✗ FAIL — Output 0 has no token!');
  }

  // Check output 0 value >= 1000
  console.log(`\n=== Covenant Check 3: tx.outputs[0].value >= 1000 ===`);
  if (signedDecoded.outputs[0]) {
    const val = signedDecoded.outputs[0].valueSatoshis;
    console.log(`Output 0 value: ${val}`);
    console.log(`Check 3: ${val >= 1000n ? '✓ PASS' : '✗ FAIL'}`);
  }

  // Check output 1 token category (should be immutable)
  console.log(`\n=== Covenant Check 4: tx.outputs[1].tokenCategory == tokenCategoryImmutable ===`);
  if (signedDecoded.outputs[1]?.token) {
    const out1Cat = binToHex(signedDecoded.outputs[1].token.category);
    const out1Cap = signedDecoded.outputs[1].token.nft?.capability || 'none';
    console.log(`Output 1 category: ${out1Cat} capability: ${out1Cap}`);
    // For immutable, introspection returns just category (32 bytes, no capability byte)
    console.log(`Check 4: ${out1Cap === 'none' ? '✓ Immutable category' : '✗ Expected none capability'}`);

    // Also check if category matches output 0's category
    if (signedDecoded.outputs[0]?.token) {
      const out0Cat = binToHex(signedDecoded.outputs[0].token.category);
      console.log(`Category match (out0 vs out1): ${out0Cat === out1Cat ? '✓' : '✗'}`);
    }
  } else {
    console.log('Check 4: ✗ FAIL — Output 1 has no token!');
  }

  // Check output 1 commitment
  console.log(`\n=== Covenant Check 5: tx.outputs[1].nftCommitment == commitment ===`);
  if (signedDecoded.outputs[1]?.token?.nft) {
    const commitment = binToHex(signedDecoded.outputs[1].token.nft.commitment);
    console.log(`Output 1 commitment: ${commitment} (${signedDecoded.outputs[1].token.nft.commitment.length} bytes)`);

    // Extract commitment from covenant unlock script (input 0)
    if (signedDecoded.inputs[0]) {
      const unlockBytes = signedDecoded.inputs[0].unlockingBytecode;
      // CashScript P2SH32 unlock: <commitment_push> <selector> <redeem_script>
      // First byte should be push length (0x20 = 32 bytes for bytes32)
      if (unlockBytes.length > 33 && unlockBytes[0] === 0x20) {
        const covenantCommitment = binToHex(unlockBytes.slice(1, 33));
        console.log(`Covenant arg commitment: ${covenantCommitment}`);
        console.log(`Check 5: ${commitment === covenantCommitment ? '✓ PASS' : '✗ FAIL — commitment mismatch!'}`);
      } else {
        console.log(`Cannot extract commitment from unlock script (first byte: 0x${unlockBytes[0]?.toString(16) || '??'})`);
      }
    }
  } else {
    console.log('Check 5: ✗ FAIL — Output 1 has no NFT!');
  }

  // Check output 1 value >= 1000
  console.log(`\n=== Covenant Check 6: tx.outputs[1].value >= 1000 ===`);
  if (signedDecoded.outputs[1]) {
    const val = signedDecoded.outputs[1].valueSatoshis;
    console.log(`Output 1 value: ${val}`);
    console.log(`Check 6: ${val >= 1000n ? '✓ PASS' : '✗ FAIL'}`);
  }

  console.log('\nDone.');
  process.exit(0);

} catch (e: any) {
  console.error('Error:', e.message || e);
  process.exit(1);
}
