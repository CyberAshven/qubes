/**
 * Check covenant conditions by building the actual WC transaction
 * and verifying each condition against the blockchain state.
 *
 * This does NOT need the signed tx — it builds the same transaction
 * as mint-cli.ts and checks the conditions independently.
 *
 * Usage: npx tsx check-covenant-conditions.ts
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import {
  decodeTransaction, hexToBin, binToHex, encodeTransaction,
  encodeTransactionOutput, decodeTransactionOutput
} from '@bitauth/libauth';

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';
const PLATFORM_PUBLIC_KEY = '02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741';

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

try {
  const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
  const platformPkh = hash160(pubkeyBytes);

  const provider = new ElectrumNetworkProvider('mainnet');
  const contract = new Contract(artifact, [platformPkh], { provider, addressType: 'p2sh32' });

  console.log(`Contract address: ${contract.address}`);
  console.log(`Contract tokenAddress: ${contract.tokenAddress}`);

  // ── Get minting token ──────────────────────────────────────────────
  const contractUtxos = await contract.getUtxos();
  console.log(`Contract UTXOs: ${contractUtxos.length}`);

  for (const u of contractUtxos) {
    console.log(`  UTXO: ${u.txid}:${u.vout} sat=${u.satoshis} token=${u.token?.category || 'none'} cap=${u.token?.nft?.capability || 'n/a'}`);
  }

  const mintingTokenUtxo = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY && u.token?.nft?.capability === 'minting'
  );

  if (!mintingTokenUtxo) {
    console.log('ERROR: Minting token not found!');
    console.log(`Looking for category: ${OFFICIAL_CATEGORY}`);
    // Check if category might be in different byte order
    const reversed = OFFICIAL_CATEGORY.match(/../g)!.reverse().join('');
    console.log(`Reversed category: ${reversed}`);
    const altMatch = contractUtxos.find(u => u.token?.category === reversed);
    if (altMatch) {
      console.log(`FOUND with reversed category! UTXO token category is in different byte order.`);
    }
    process.exit(1);
  }

  console.log(`\nMinting UTXO: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);
  console.log(`  satoshis: ${mintingTokenUtxo.satoshis}`);
  console.log(`  category (from ElectrumProvider): ${mintingTokenUtxo.token!.category}`);
  console.log(`  capability: ${mintingTokenUtxo.token!.nft!.capability}`);
  console.log(`  commitment: ${mintingTokenUtxo.token!.nft!.commitment}`);

  // ── Build transaction (same as mint-cli.ts WC mode) ──────────────
  const testCommitment = createHash('sha256').update('test_covenant_check').digest('hex');
  const testUserAddress = 'bitcoincash:zrh9uhpnrd8zym5tzxvftv9g8mqa3ly83g7ytuq96y';

  const txBuilder = new TransactionBuilder({ provider });

  txBuilder.addInput(mintingTokenUtxo, contract.unlock.mint(Buffer.from(testCommitment, 'hex')));

  // No P2PKH inputs for this test

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

  txBuilder.addOutput({
    to: testUserAddress,
    amount: 1000n,
    token: {
      amount: 0n,
      category: OFFICIAL_CATEGORY,
      nft: {
        capability: 'none',
        commitment: testCommitment
      }
    }
  });

  // Build and decode
  const encodedHex = (txBuilder as any).build() as string;
  const decoded = decodeTransaction(hexToBin(encodedHex));
  if (typeof decoded === 'string') {
    console.error('Failed to decode:', decoded);
    process.exit(1);
  }

  console.log(`\n${'═'.repeat(60)}`);
  console.log(`TRANSACTION ANALYSIS`);
  console.log(`${'═'.repeat(60)}`);
  console.log(`Encoded: ${encodedHex.length / 2} bytes`);
  console.log(`Inputs: ${decoded.inputs.length}, Outputs: ${decoded.outputs.length}`);

  // ── Output 0 details ───────────────────────────────────────────────
  const out0 = decoded.outputs[0];
  console.log(`\n── Output 0 ──`);
  console.log(`  lockingBytecode: ${binToHex(out0.lockingBytecode)} (${out0.lockingBytecode.length} bytes)`);
  console.log(`  valueSatoshis: ${out0.valueSatoshis}`);
  if (out0.token) {
    console.log(`  token.category: ${binToHex(out0.token.category)} (${out0.token.category.length} bytes)`);
    console.log(`  token.category (reversed): ${binToHex(out0.token.category.slice().reverse())}`);
    console.log(`  token.amount: ${out0.token.amount}`);
    console.log(`  token.nft.capability: ${out0.token.nft?.capability}`);
    console.log(`  token.nft.commitment: ${out0.token.nft ? binToHex(out0.token.nft.commitment) : 'none'}`);
  } else {
    console.log(`  NO TOKEN DATA!`);
  }

  // ── Output 1 details ───────────────────────────────────────────────
  const out1 = decoded.outputs[1];
  console.log(`\n── Output 1 ──`);
  console.log(`  lockingBytecode: ${binToHex(out1.lockingBytecode)} (${out1.lockingBytecode.length} bytes)`);
  console.log(`  valueSatoshis: ${out1.valueSatoshis}`);
  if (out1.token) {
    console.log(`  token.category: ${binToHex(out1.token.category)} (${out1.token.category.length} bytes)`);
    console.log(`  token.category (reversed): ${binToHex(out1.token.category.slice().reverse())}`);
    console.log(`  token.amount: ${out1.token.amount}`);
    console.log(`  token.nft.capability: ${out1.token.nft?.capability}`);
    console.log(`  token.nft.commitment: ${out1.token.nft ? binToHex(out1.token.nft.commitment) : 'none'}`);
  } else {
    console.log(`  NO TOKEN DATA!`);
  }

  // ── Input 0 (covenant) details ─────────────────────────────────────
  console.log(`\n── Input 0 (covenant) ──`);
  const in0 = decoded.inputs[0];
  console.log(`  outpoint: ${binToHex(in0.outpointTransactionHash.slice().reverse())}:${in0.outpointIndex}`);
  console.log(`  unlockingBytecode: ${in0.unlockingBytecode.length} bytes`);

  // ── Covenant Check 1: lockingBytecode == activeBytecode ────────────
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`COVENANT CHECKS`);
  console.log(`${'═'.repeat(60)}`);

  // Compute the expected P2SH32 locking bytecode
  const redeemScript = contract.bytecode;
  // Convert to regular Uint8Array to avoid issues with CashScript's internal types
  const redeemBytes = Uint8Array.from(redeemScript);
  console.log(`\nRedeemScript (contract bytecode): ${binToHex(redeemBytes)} (${redeemBytes.length} bytes)`);

  // HASH256 = SHA256(SHA256(x))
  const hash1 = createHash('sha256').update(Buffer.from(redeemBytes)).digest();
  const hash2 = createHash('sha256').update(hash1).digest();

  // P2SH32 locking bytecode: OP_HASH256 PUSH32 <hash> OP_EQUAL
  const expectedActiveBytecode = new Uint8Array(35);
  expectedActiveBytecode[0] = 0xaa; // OP_HASH256
  expectedActiveBytecode[1] = 0x20; // Push 32 bytes
  expectedActiveBytecode.set(hash2, 2);
  expectedActiveBytecode[34] = 0x87; // OP_EQUAL

  const expectedHex = binToHex(expectedActiveBytecode);
  const out0LockHex = binToHex(out0.lockingBytecode);

  console.log(`\nCheck 1: tx.outputs[0].lockingBytecode == this.activeBytecode`);
  console.log(`  Expected (activeBytecode): ${expectedHex}`);
  console.log(`  Output 0 lockingBytecode:  ${out0LockHex}`);
  console.log(`  Match: ${expectedHex === out0LockHex ? '✓ PASS' : '✗ FAIL'}`);

  // ── Covenant Check 2: output[0].tokenCategory == input[0].tokenCategory ──
  console.log(`\nCheck 2: tx.outputs[0].tokenCategory == tx.inputs[0].tokenCategory`);
  if (out0.token) {
    // For minting capability: introspection returns category(32) || 0x02
    const out0IntrospectionCategory = new Uint8Array(33);
    out0IntrospectionCategory.set(out0.token.category, 0);
    if (out0.token.nft?.capability === 'minting') {
      out0IntrospectionCategory[32] = 0x02;
    } else if (out0.token.nft?.capability === 'mutable') {
      out0IntrospectionCategory[32] = 0x01;
    }
    // For 'none', it's just 32 bytes (no capability byte appended in introspection)
    const out0CatLen = out0.token.nft?.capability === 'none' ? 32 : 33;
    const out0IntCat = binToHex(out0IntrospectionCategory.slice(0, out0CatLen));

    // For input: the UTXO's category from CashScript is in display-order hex
    // But the introspection opcode OP_UTXOTOKENCATEGORY returns the category
    // as it appears in the encoded transaction (internal byte order).
    // We need to check: what byte order does CashScript's hexToBin produce?
    const cashscriptCategoryBytes = hexToBin(OFFICIAL_CATEGORY);
    const reversedCategoryBytes = cashscriptCategoryBytes.slice().reverse();

    console.log(`  OFFICIAL_CATEGORY hex:             ${OFFICIAL_CATEGORY}`);
    console.log(`  hexToBin(OFFICIAL_CATEGORY):        ${binToHex(cashscriptCategoryBytes)}`);
    console.log(`  hexToBin reversed:                  ${binToHex(reversedCategoryBytes)}`);
    console.log(`  Output 0 token.category (decoded):  ${binToHex(out0.token.category)}`);

    // Check which byte order the output category uses
    if (binToHex(out0.token.category) === OFFICIAL_CATEGORY) {
      console.log(`  Output 0 category matches OFFICIAL_CATEGORY directly (same byte order)`);
    } else if (binToHex(out0.token.category) === binToHex(reversedCategoryBytes)) {
      console.log(`  Output 0 category matches REVERSED OFFICIAL_CATEGORY`);
    } else {
      console.log(`  Output 0 category matches NEITHER order!`);
    }

    // Now simulate what the VM would do:
    // OP_OUTPUTTOKENCATEGORY reads from the encoded output
    // OP_UTXOTOKENCATEGORY reads from the UTXO's encoded output on the blockchain
    // Both should use the same encoding, so they should be in the same byte order
    console.log(`\n  Simulating introspection opcodes:`);
    console.log(`  OP_OUTPUTTOKENCATEGORY(0) = cat(${out0.token.category.length}B) + cap_byte = ${out0IntCat}`);

    // The UTXO's introspection value depends on the actual on-chain encoding
    // Since we're using CashScript which encodes via libauth, the byte order should be consistent
    const inputMintingCat = new Uint8Array(33);
    inputMintingCat.set(cashscriptCategoryBytes, 0);
    inputMintingCat[32] = 0x02; // minting
    const inputIntCat = binToHex(inputMintingCat);
    console.log(`  OP_UTXOTOKENCATEGORY(0) (from CashScript hexToBin) = ${inputIntCat}`);
    console.log(`  Match: ${out0IntCat === inputIntCat ? '✓ PASS' : '✗ FAIL'}`);
  }

  // ── Covenant Check 3: output[0].value >= 1000 ──
  console.log(`\nCheck 3: tx.outputs[0].value >= 1000`);
  console.log(`  Value: ${out0.valueSatoshis}`);
  console.log(`  Check: ${out0.valueSatoshis >= 1000n ? '✓ PASS' : '✗ FAIL'}`);

  // ── Covenant Check 4: output[1].tokenCategory == tokenCategoryImmutable ──
  console.log(`\nCheck 4: tx.outputs[1].tokenCategory == tokenCategoryImmutable`);
  if (out1.token) {
    // tokenCategoryImmutable = tx.inputs[0].tokenCategory.split(32)[0]
    // This takes the first 32 bytes (strips the capability byte)
    const out1IntCat = binToHex(out1.token.category);
    const tokenCategoryImmutable = binToHex(hexToBin(OFFICIAL_CATEGORY)); // just the 32 bytes

    // For immutable NFT (capability 'none'), OP_OUTPUTTOKENCATEGORY returns just 32 bytes
    console.log(`  tokenCategoryImmutable (from input, first 32 bytes): ${tokenCategoryImmutable}`);
    console.log(`  OP_OUTPUTTOKENCATEGORY(1): ${out1IntCat} (${out1.token.category.length} bytes, cap=${out1.token.nft?.capability})`);
    console.log(`  Match: ${out1IntCat === tokenCategoryImmutable ? '✓ PASS' : '✗ FAIL'}`);
  }

  // ── Covenant Check 5: output[1].nftCommitment == commitment ──
  console.log(`\nCheck 5: tx.outputs[1].nftCommitment == commitment`);
  if (out1.token?.nft) {
    const out1Commit = binToHex(out1.token.nft.commitment);
    console.log(`  Output 1 commitment: ${out1Commit}`);
    console.log(`  Expected commitment: ${testCommitment}`);

    // Check both direct and reversed
    const commitBytes = hexToBin(testCommitment);
    const commitReversed = binToHex(commitBytes.slice().reverse());

    if (out1Commit === testCommitment) {
      console.log(`  Match: ✓ PASS (direct match)`);
    } else if (out1Commit === commitReversed) {
      console.log(`  Match: ✗ FAIL — commitment is REVERSED!`);
    } else {
      console.log(`  Match: ✗ FAIL — no match in either byte order`);
    }

    // Also check what's in the unlock script
    const unlockBytes = decoded.inputs[0].unlockingBytecode;
    if (unlockBytes.length > 33 && unlockBytes[0] === 0x20) {
      const unlockCommit = binToHex(unlockBytes.slice(1, 33));
      console.log(`  Unlock script commitment arg: ${unlockCommit}`);
      console.log(`  Matches output 1: ${unlockCommit === out1Commit ? '✓' : '✗'}`);
    }
  }

  // ── Covenant Check 6: output[1].value >= 1000 ──
  console.log(`\nCheck 6: tx.outputs[1].value >= 1000`);
  console.log(`  Value: ${out1.valueSatoshis}`);
  console.log(`  Check: ${out1.valueSatoshis >= 1000n ? '✓ PASS' : '✗ FAIL'}`);

  // ── Try CashScript's built-in debug ────────────────────────────────
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`CASHSCRIPT DEBUG (local VM validation)`);
  console.log(`${'═'.repeat(60)}`);
  try {
    (txBuilder as any).debug();
    console.log(`✓ CashScript debug() PASSED — local VM says transaction is valid`);
  } catch (e: any) {
    console.log(`✗ CashScript debug() FAILED:`);
    console.log(`  ${e.message}`);
  }

  // ── Raw hex dump for analysis ──────────────────────────────────────
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`RAW TRANSACTION HEX`);
  console.log(`${'═'.repeat(60)}`);
  console.log(encodedHex);

  console.log('\nDone.');
  process.exit(0);

} catch (e: any) {
  console.error('Error:', e.message || e);
  process.exit(1);
}
