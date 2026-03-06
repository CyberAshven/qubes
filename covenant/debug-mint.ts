/**
 * Debug script: builds a mint transaction and dumps all covenant check values.
 * Usage: npx tsx debug-mint.ts
 */

import {
  Contract, ElectrumNetworkProvider, TransactionBuilder,
  placeholderP2PKHUnlocker
} from 'cashscript';
import artifact from './qubes_mint.json' with { type: 'json' };
import { createHash } from 'crypto';
import {
  lockingBytecodeToCashAddress, stringify,
  decodeTransaction, hexToBin, binToHex, encodeTransaction
} from '@bitauth/libauth';

const OFFICIAL_CATEGORY = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';
const PLATFORM_PUBLIC_KEY = '02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741';

function hash160(data: Buffer): Buffer {
  const sha256 = createHash('sha256').update(data).digest();
  return createHash('ripemd160').update(sha256).digest();
}

// Use a dummy commitment and user address for testing
const testCommitment = createHash('sha256').update('test_debug_key').digest('hex');
// Token-aware address for the user (z prefix = can receive tokens)
const testUserAddress = 'bitcoincash:zrh9uhpnrd8zym5tzxvftv9g8mqa3ly83g7ytuq96y';
// Regular address for funding/change (q prefix)
const testUserFundingAddress = 'bitcoincash:qrh9uhpnrd8zym5tzxvftv9g8mqa3ly83gewczwr9h';

try {
  const pubkeyBytes = Buffer.from(PLATFORM_PUBLIC_KEY, 'hex');
  const platformPkh = hash160(pubkeyBytes);

  console.log('=== Covenant Debug ===');
  console.log(`Platform public key: ${PLATFORM_PUBLIC_KEY}`);
  console.log(`Platform PKH (HASH160): ${platformPkh.toString('hex')}`);

  const provider = new ElectrumNetworkProvider('mainnet');

  const contract = new Contract(
    artifact,
    [platformPkh],
    { provider, addressType: 'p2sh32' }
  );

  console.log(`Contract address: ${contract.address}`);
  console.log(`Contract tokenAddress: ${contract.tokenAddress}`);
  console.log(`Expected address: bitcoincash:rdlqc0y2ulzyp0ulk3t6gn56lzrxt2fq7s2j232vzghww6m8mtqr7h0rx97sy`);
  console.log(`Address match: ${contract.tokenAddress === 'bitcoincash:rdlqc0y2ulzyp0ulk3t6gn56lzrxt2fq7s2j232vzghww6m8mtqr7h0rx97sy'}`);

  // Get contract UTXOs
  const contractUtxos = await contract.getUtxos();
  console.log(`\nContract UTXOs: ${contractUtxos.length}`);

  const mintingTokenUtxo = contractUtxos.find(
    u => u.token?.category === OFFICIAL_CATEGORY
      && u.token?.nft?.capability === 'minting'
  );

  if (!mintingTokenUtxo) {
    console.log('ERROR: Minting token not found!');
    process.exit(1);
  }

  console.log(`Minting UTXO: ${mintingTokenUtxo.txid}:${mintingTokenUtxo.vout}`);
  console.log(`Minting UTXO satoshis: ${mintingTokenUtxo.satoshis}`);
  console.log(`Minting UTXO token category: ${mintingTokenUtxo.token?.category}`);
  console.log(`Minting UTXO token capability: ${mintingTokenUtxo.token?.nft?.capability}`);

  // Get user UTXOs
  const userUtxos = await provider.getUtxos(testUserFundingAddress);
  const fundingUtxos = userUtxos.filter(u => !u.token);
  console.log(`\nUser funding UTXOs: ${fundingUtxos.length}`);
  const totalFunding = fundingUtxos.reduce((sum, u) => sum + u.satoshis, 0n);
  console.log(`Total funding: ${totalFunding} sats`);

  if (fundingUtxos.length === 0) {
    console.log('No funding UTXOs — using dummy for analysis');
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
  const estimatedSize = BigInt(10 + 300 + fundingUtxos.length * 148 + 90 * 2 + 34);
  const estimatedFee = estimatedSize * 2n;
  const totalInput = mintingTokenUtxo.satoshis + totalFunding;
  const change = totalInput - 2000n - estimatedFee;
  if (change >= 546n) {
    txBuilder.addOutput({ to: testUserFundingAddress, amount: change });
  }

  // Build and decode
  const encodedTx = (txBuilder as any).build();
  const decodedResult = decodeTransaction(hexToBin(encodedTx));
  if (typeof decodedResult === 'string') {
    console.log('ERROR: Failed to decode transaction:', decodedResult);
    process.exit(1);
  }
  const tx = decodedResult;

  console.log('\n=== Transaction Analysis ===');
  console.log(`Inputs: ${tx.inputs.length}`);
  console.log(`Outputs: ${tx.outputs.length}`);

  // Analyze Output 0 (covenant return)
  console.log('\n--- Output 0 (covenant return) ---');
  const out0 = tx.outputs[0];
  console.log(`lockingBytecode: ${binToHex(out0.lockingBytecode)}`);
  console.log(`valueSatoshis: ${out0.valueSatoshis}`);
  if (out0.token) {
    console.log(`token.category: ${binToHex(out0.token.category)}`);
    console.log(`token.nft.capability: ${out0.token.nft?.capability}`);
    console.log(`token.nft.commitment: ${binToHex(out0.token.nft?.commitment || new Uint8Array())}`);
  }

  // Analyze Output 1 (NFT to user)
  console.log('\n--- Output 1 (NFT to user) ---');
  const out1 = tx.outputs[1];
  console.log(`lockingBytecode: ${binToHex(out1.lockingBytecode)}`);
  console.log(`valueSatoshis: ${out1.valueSatoshis}`);
  if (out1.token) {
    console.log(`token.category: ${binToHex(out1.token.category)}`);
    console.log(`token.nft.capability: ${out1.token.nft?.capability}`);
    console.log(`token.nft.commitment: ${binToHex(out1.token.nft?.commitment || new Uint8Array())}`);
  }

  // Analyze Input 0 (covenant)
  console.log('\n--- Input 0 (covenant) ---');
  const in0 = tx.inputs[0];
  console.log(`unlockingBytecode length: ${in0.unlockingBytecode.length}`);
  console.log(`unlockingBytecode: ${binToHex(in0.unlockingBytecode)}`);

  // Contract's activeBytecode (P2SH32 locking script)
  const contractBytecode = contract.bytecode;
  console.log(`\nContract bytecode (redeemScript): ${binToHex(contractBytecode)}`);
  console.log(`Contract bytecode length: ${contractBytecode.length}`);

  // The activeBytecode for a P2SH32 is: OP_HASH256 <32-byte-hash> OP_EQUAL
  // But actually, for CashScript contracts, activeBytecode refers to the
  // locking bytecode of the contract's address
  // Let me check what the locking bytecode of output 0 should be

  // Compare: what the covenant check actually compares
  // Check 1: tx.outputs[0].lockingBytecode == this.activeBytecode
  // this.activeBytecode = locking bytecode of the input being spent (the covenant UTXO)
  // We can derive this from the contract address

  // For P2SH32, lockingBytecode = OP_HASH256 <sha256(redeemScript)> OP_EQUAL
  const redeemScriptHash = createHash('sha256').update(createHash('sha256').update(contractBytecode).digest()).digest();
  const p2sh32LockingBytecode = Buffer.concat([
    Buffer.from([0xaa]),           // OP_HASH256
    Buffer.from([0x20]),           // Push 32 bytes
    redeemScriptHash,              // 32-byte hash
    Buffer.from([0x87])            // OP_EQUAL
  ]);
  console.log(`\nExpected P2SH32 locking bytecode: ${p2sh32LockingBytecode.toString('hex')}`);
  console.log(`Output 0 locking bytecode:         ${binToHex(out0.lockingBytecode)}`);
  console.log(`Match (Check 1): ${p2sh32LockingBytecode.toString('hex') === binToHex(out0.lockingBytecode)}`);

  // Check 2: tx.outputs[0].tokenCategory == tx.inputs[0].tokenCategory
  // The input's tokenCategory = category_id + capability_byte (for minting)
  // For minting capability, the encoded tokenCategory in the raw tx has a specific format
  if (out0.token) {
    console.log(`\nOutput 0 tokenCategory: ${binToHex(out0.token.category)}`);
    console.log(`Output 0 nft capability: ${out0.token.nft?.capability}`);
  }

  // Check commitment
  console.log(`\nExpected commitment: ${testCommitment}`);
  if (out1.token?.nft) {
    console.log(`Output 1 commitment: ${binToHex(out1.token.nft.commitment)}`);
    console.log(`Match (Check 4): ${testCommitment === binToHex(out1.token.nft.commitment)}`);
  }

  // Also dump the WC transaction object
  const wcTxObj = txBuilder.generateWcTransactionObject({
    broadcast: true,
    userPrompt: 'Debug Mint'
  });
  console.log('\n=== WC Transaction Object (first 2000 chars) ===');
  const wcStr = stringify(wcTxObj);
  console.log(wcStr.substring(0, 2000));

} catch (e: any) {
  console.error('Error:', e.message || e);
}
