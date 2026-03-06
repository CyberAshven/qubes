/**
 * Verify WC round-trip: simulates what Cashonize does with our WC transaction.
 *
 * Builds a mint transaction, creates the WC object, simulates the stringify→parse
 * round-trip, then compares the original and reconstructed transactions byte-by-byte.
 *
 * Usage: npx tsx verify-wc-roundtrip.ts
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import {
  stringify, decodeTransaction, hexToBin, binToHex, encodeTransaction
} from '@bitauth/libauth';

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';
const PLATFORM_PUBLIC_KEY = '02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741';

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

// Simulate Cashonize's parseExtendedJson
function parseExtendedJson(jsonString: string) {
  const uint8ArrayRegex = /^<Uint8Array: 0x(?<hex>[0-9a-f]*)>$/u;
  const bigIntRegex = /^<bigint: (?<bigint>[0-9]*)n>$/;

  return JSON.parse(jsonString, (_key, value) => {
    if (typeof value === "string") {
      const bigintMatch = value.match(bigIntRegex);
      if (bigintMatch?.groups?.bigint !== undefined) {
        return BigInt(bigintMatch.groups.bigint);
      }
      const uint8ArrayMatch = value.match(uint8ArrayRegex);
      if (uint8ArrayMatch?.groups?.hex !== undefined) {
        return hexToBin(uint8ArrayMatch.groups.hex);
      }
    }
    return value;
  });
}

const testCommitment = createHash('sha256').update('test_debug_key').digest('hex');
const testUserAddress = 'bitcoincash:zrh9uhpnrd8zym5tzxvftv9g8mqa3ly83g7ytuq96y';
const testUserFundingAddress = 'bitcoincash:qrh9uhpnrd8zym5tzxvftv9g8mqa3ly83gewczwr9h';

try {
  const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
  const platformPkh = hash160(pubkeyBytes);

  const provider = new ElectrumNetworkProvider('mainnet');
  const contract = new Contract(artifact, [platformPkh], { provider, addressType: 'p2sh32' });

  console.log(`Contract tokenAddress: ${contract.tokenAddress}`);

  const contractUtxos = await contract.getUtxos();
  const mintingTokenUtxo = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY && u.token?.nft?.capability === 'minting'
  );

  if (!mintingTokenUtxo) {
    console.log('ERROR: Minting token not found!');
    process.exit(1);
  }

  console.log(`Minting UTXO: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);

  // Get user UTXOs for funding
  const userUtxos = await provider.getUtxos(testUserFundingAddress);
  const fundingUtxos = userUtxos.filter(u => !u.token);
  console.log(`User funding UTXOs: ${fundingUtxos.length}`);

  if (fundingUtxos.length === 0) {
    console.log('No funding UTXOs available — using minimal transaction for analysis');
  }

  // Build transaction
  const txBuilder = new TransactionBuilder({ provider });

  txBuilder.addInput(
    mintingTokenUtxo,
    contract.unlock.mint(Buffer.from(testCommitment, 'hex'))
  );

  for (const utxo of fundingUtxos) {
    txBuilder.addInput(utxo, placeholderP2PKHUnlocker(testUserFundingAddress));
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

  // Change output
  const totalFunding = fundingUtxos.reduce((sum, u) => sum + u.satoshis, 0n);
  const estimatedFee = BigInt(10 + 300 + fundingUtxos.length * 148 + 90 * 2 + 34) * 2n;
  const change = mintingTokenUtxo.satoshis + totalFunding - 2000n - estimatedFee;
  if (change >= 546n) {
    txBuilder.addOutput({ to: testUserFundingAddress, amount: change });
  }

  // ═══ STEP 1: Build original encoded transaction ═══
  const originalEncodedHex = (txBuilder as any).build() as string;
  console.log(`\n=== Original Transaction ===`);
  console.log(`Encoded hex length: ${originalEncodedHex.length / 2} bytes`);

  const originalDecoded = decodeTransaction(hexToBin(originalEncodedHex));
  if (typeof originalDecoded === 'string') {
    console.log('ERROR: Failed to decode:', originalDecoded);
    process.exit(1);
  }

  // ═══ STEP 2: Generate WC transaction object ═══
  const wcTxObj = txBuilder.generateWcTransactionObject({
    broadcast: false,
    userPrompt: 'Debug Mint'
  });

  // Strip contract metadata (like our production code does)
  for (const so of (wcTxObj as any).sourceOutputs) {
    delete so.contract;
  }

  // ═══ STEP 3: Simulate stringify → parse round-trip ═══
  const stringified = stringify(wcTxObj);
  console.log(`\nStringified WC object length: ${stringified.length} chars`);

  // Simulate what our frontend does: JSON.parse
  const frontendParsed = JSON.parse(stringified);

  // Simulate what WC transport does: JSON.stringify → JSON.parse (it's already JSON)
  // Simulate what Cashonize does: parseExtendedJson
  const cashonizeParsed = parseExtendedJson(JSON.stringify(frontendParsed));

  // ═══ STEP 4: Extract and compare transactions ═══
  const wcTransaction = cashonizeParsed.transaction;
  const wcSourceOutputs = cashonizeParsed.sourceOutputs;

  console.log(`\n=== Round-trip Comparison ===`);

  // Compare outputs
  for (let i = 0; i < originalDecoded.outputs.length; i++) {
    const origOut = originalDecoded.outputs[i];
    const wcOut = wcTransaction.outputs[i];

    if (!wcOut) {
      console.log(`Output ${i}: MISSING in WC transaction!`);
      continue;
    }

    const origLocking = binToHex(origOut.lockingBytecode);
    const wcLocking = binToHex(wcOut.lockingBytecode);
    const lockingMatch = origLocking === wcLocking;

    const origValue = origOut.valueSatoshis;
    const wcValue = wcOut.valueSatoshis;
    const valueMatch = origValue === wcValue;

    console.log(`\nOutput ${i}:`);
    console.log(`  lockingBytecode: ${lockingMatch ? '✓ MATCH' : '✗ MISMATCH'}`);
    if (!lockingMatch) {
      console.log(`    orig: ${origLocking}`);
      console.log(`    wc:   ${wcLocking}`);
    }
    console.log(`  valueSatoshis: ${valueMatch ? '✓ MATCH' : '✗ MISMATCH'} (${origValue} vs ${wcValue})`);

    // Compare token data
    if (origOut.token || wcOut.token) {
      const origCat = origOut.token ? binToHex(origOut.token.category) : 'none';
      const wcCat = wcOut.token ? binToHex(wcOut.token.category) : 'none';
      const catMatch = origCat === wcCat;
      console.log(`  token.category: ${catMatch ? '✓ MATCH' : '✗ MISMATCH'}`);
      if (!catMatch) {
        console.log(`    orig: ${origCat}`);
        console.log(`    wc:   ${wcCat}`);
      }

      const origCap = origOut.token?.nft?.capability || 'none';
      const wcCap = wcOut.token?.nft?.capability || 'none';
      const capMatch = origCap === wcCap;
      console.log(`  token.nft.capability: ${capMatch ? '✓ MATCH' : '✗ MISMATCH'} (${origCap} vs ${wcCap})`);

      const origCommit = origOut.token?.nft?.commitment ? binToHex(origOut.token.nft.commitment) : '';
      const wcCommit = wcOut.token?.nft?.commitment ? binToHex(wcOut.token.nft.commitment) : '';
      const commitMatch = origCommit === wcCommit;
      console.log(`  token.nft.commitment: ${commitMatch ? '✓ MATCH' : '✗ MISMATCH'}`);
      if (!commitMatch) {
        console.log(`    orig: ${origCommit}`);
        console.log(`    wc:   ${wcCommit}`);
      }
    }
  }

  // Compare inputs
  for (let i = 0; i < originalDecoded.inputs.length; i++) {
    const origIn = originalDecoded.inputs[i];
    const wcIn = wcTransaction.inputs[i];
    const wcSo = wcSourceOutputs[i];

    console.log(`\nInput ${i}:`);
    const origUnlock = binToHex(origIn.unlockingBytecode);
    const wcUnlock = binToHex(wcIn.unlockingBytecode);
    const unlockMatch = origUnlock === wcUnlock;
    console.log(`  unlockingBytecode: ${unlockMatch ? '✓ MATCH' : '✗ MISMATCH'} (${origUnlock.length / 2} vs ${wcUnlock.length / 2} bytes)`);

    if (wcSo) {
      const soUnlock = wcSo.unlockingBytecode ? binToHex(wcSo.unlockingBytecode) : '(empty)';
      console.log(`  sourceOutput.unlockingBytecode: ${soUnlock.length / 2} bytes`);
      console.log(`  sourceOutput.lockingBytecode: ${binToHex(wcSo.lockingBytecode)}`);
      console.log(`  sourceOutput.valueSatoshis: ${wcSo.valueSatoshis}`);
      console.log(`  sourceOutput.contract: ${wcSo.contract ? 'PRESENT' : 'stripped'}`);
    }
  }

  // ═══ STEP 5: Re-encode the WC transaction and compare ═══
  console.log(`\n=== Re-encoding Comparison ===`);
  try {
    const reEncoded = encodeTransaction(wcTransaction);
    const reEncodedHex = binToHex(reEncoded);
    const match = originalEncodedHex === reEncodedHex;
    console.log(`Full transaction: ${match ? '✓ MATCH' : '✗ MISMATCH'}`);
    if (!match) {
      console.log(`  Original length: ${originalEncodedHex.length / 2} bytes`);
      console.log(`  Re-encoded length: ${reEncodedHex.length / 2} bytes`);
      // Find first difference
      for (let i = 0; i < Math.max(originalEncodedHex.length, reEncodedHex.length); i += 2) {
        if (originalEncodedHex.substring(i, i + 2) !== reEncodedHex.substring(i, i + 2)) {
          console.log(`  First diff at byte ${i / 2}: orig=${originalEncodedHex.substring(i, i + 20)} wc=${reEncodedHex.substring(i, i + 20)}`);
          break;
        }
      }
    }
  } catch (e: any) {
    console.log(`Re-encoding failed: ${e.message}`);
  }

  // ═══ STEP 6: Check covenant-specific values ═══
  console.log(`\n=== Covenant Check Values ===`);
  const contractBytecode = contract.bytecode;
  console.log(`Contract bytecode (redeemScript): ${binToHex(contractBytecode)} (${contractBytecode.length} bytes)`);

  // this.activeBytecode for P2SH32 = OP_HASH256 <32-byte-hash> OP_EQUAL
  const sha256_1 = createHash('sha256').update(contractBytecode).digest();
  const sha256_2 = createHash('sha256').update(sha256_1).digest();
  const p2sh32Lock = Buffer.concat([
    Buffer.from([0xaa]),  // OP_HASH256
    Buffer.from([0x20]),  // Push 32 bytes
    sha256_2,
    Buffer.from([0x87])   // OP_EQUAL
  ]);
  console.log(`Expected P2SH32 lockingBytecode (this.activeBytecode): ${p2sh32Lock.toString('hex')}`);

  if (wcTransaction.outputs[0]) {
    const out0Lock = binToHex(wcTransaction.outputs[0].lockingBytecode);
    console.log(`Output 0 lockingBytecode: ${out0Lock}`);
    console.log(`Check 1 (activeBytecode): ${p2sh32Lock.toString('hex') === out0Lock ? '✓ PASS' : '✗ FAIL'}`);
  }

  console.log('\nDone.');
  process.exit(0);

} catch (e: any) {
  console.error('Error:', e.message || e);
  process.exit(1);
}
