# @qubesai/sdk

TypeScript SDK for the Qubes protocol — sovereign AI agents with cryptographic identity on Bitcoin Cash.

## Install

```bash
npm install @qubesai/sdk
```

For NFT minting, add the optional peer dependencies:

```bash
npm install cashscript @bitauth/libauth
```

## Modules

| Module | Import path | Description |
|--------|-------------|-------------|
| types | `@qubesai/sdk/types` | Shared TypeScript types (blocks, crypto, covenant, package, BCMR) |
| crypto | `@qubesai/sdk/crypto` | Key generation, signing, AES-256-GCM encryption, PBKDF2, HKDF, ECIES |
| wallet | `@qubesai/sdk/wallet` | BCH script builder, CashAddr, P2SH multisig, WalletConnect helpers |
| blocks | `@qubesai/sdk/blocks` | Genesis block factory, block class, memory chain, chain state |
| covenant | `@qubesai/sdk/covenant` | CashScript covenant mint (broadcast or WalletConnect mode) |
| package | `@qubesai/sdk/package` | Binary IPFS package and `.qube` ZIP export/import |
| bcmr | `@qubesai/sdk/bcmr` | Bitcoin Cash Metadata Registry generation and registry management |
| storage | `@qubesai/sdk/storage` | Pluggable storage adapters (Pinata/IPFS) |

All modules are also re-exported from the root `@qubesai/sdk` entry point.

---

## Quick Start

### Generate Identity

```ts
import {
  generateKeyPair,
  serializePublicKey,
  deriveCommitment,
  deriveQubeId,
} from '@qubesai/sdk/crypto';

const { privateKey, publicKey } = generateKeyPair();
const publicKeyHex = serializePublicKey(publicKey); // 66-char hex, e.g. "02abc..."

// commitment = SHA256(publicKeyHex)  — hashes the hex string, not raw bytes
const commitment = deriveCommitment(publicKeyHex); // 64-char hex

// qubeId = first 4 bytes of commitment, uppercase
const qubeId = deriveQubeId(publicKeyHex); // e.g. "A3F2C1B8"
```

### Create Genesis Block

```ts
import { createGenesisBlock } from '@qubesai/sdk/blocks';

const genesis = createGenesisBlock({
  qubeId,
  qubeName: 'Aria',
  creator: 'user_abc123',
  publicKey: publicKeyHex,
  genesisPrompt: 'You are Aria, a helpful assistant.',
  aiModel: 'gpt-4o',
  voiceModel: 'kokoro',
  avatar: { style: 'anime', color: '#4A90E2' },
});

console.log(genesis.blockHash); // SHA256(canonicalStringify(block))
```

### Sign Blocks

```ts
import { signBlock, verifyBlockSignature, hashBlock } from '@qubesai/sdk/crypto';

// Sign (genesis block uses double-hash; standard blocks use canonical JSON)
const signature = signBlock(genesis.toDict(), privateKey);

// Verify
const valid = verifyBlockSignature(genesis.toDict(), signature, publicKey);
```

### Derive Encryption Key

```ts
import { deriveMasterKey } from '@qubesai/sdk/crypto';

// PBKDF2-HMAC-SHA256, 600K iterations (OWASP 2025)
const salt = crypto.getRandomValues(new Uint8Array(16));
const masterKey = deriveMasterKey('user-password', salt); // 32-byte Uint8Array
```

### Encrypt Data

```ts
import { encryptBlockData, decryptBlockData } from '@qubesai/sdk/crypto';

const encrypted = await encryptBlockData({ message: 'hello' }, masterKey);
// { ciphertext: '...hex', nonce: '...hex', algorithm: 'AES-256-GCM' }

const decrypted = await decryptBlockData(encrypted, masterKey);
```

### Package for Export

```ts
import { createQubeFile, parseQubeFile } from '@qubesai/sdk/package';

// Export — password-protected ZIP (.qube file)
const zipBytes = await createQubeFile(qubePackageData, 'user-password');

// Import
const data = await parseQubeFile(zipBytes, 'user-password');
```

For the binary IPFS format:

```ts
import { createBinaryPackage, parseBinaryPackage } from '@qubesai/sdk/package';

const { encrypted, key } = await createBinaryPackage(qubePackageData);
// Store `key` separately (e.g. on-chain in NFT commitment)

const data = await parseBinaryPackage(encrypted, key);
```

### Mint NFT (WalletConnect)

Requires `cashscript` and `@bitauth/libauth` peer dependencies.

```ts
import { prepareMintTransaction } from '@qubesai/sdk/covenant';

// Build a transaction for the user's wallet to sign
const result = await prepareMintTransaction({
  commitment,                              // 64-char hex (SHA256 of pubkey hex)
  recipientAddress: 'bitcoincash:z...',   // token-aware CashAddr
  platformPublicKey: '02abc...',           // 66-char compressed pubkey hex
  userAddress: 'bitcoincash:z...',        // user's token-aware address
  network: 'mainnet',                     // or 'chipnet' for testing
});

if (result.success) {
  // Pass result.wcTransaction to WalletConnect bch_signTransaction
  console.log(result.wcTransaction);
}
```

For server-side broadcast (platform holds the WIF):

```ts
import { broadcastMint } from '@qubesai/sdk/covenant';

const result = await broadcastMint({
  commitment,
  recipientAddress: 'bitcoincash:z...',
  platformPublicKey: '02abc...',
  walletWif: 'L...',
});

if (result.success) {
  console.log(result.mintTxid);
}
```

### IPFS Storage

```ts
import { PinataAdapter, downloadFromIpfs } from '@qubesai/sdk/storage';

const storage = new PinataAdapter({ jwt: process.env.PINATA_JWT! });
const { cid } = await storage.uploadJson(qubePackageData);

const bytes = await downloadFromIpfs(cid);
```

### BCMR Metadata

```ts
import { generateBcmrMetadata, createRegistry, addQubeToRegistry } from '@qubesai/sdk/bcmr';

const bcmr = generateBcmrMetadata({
  qubeId,
  qubeName: 'Aria',
  commitment,
  description: 'An AI assistant',
  // ...
});

const registry = createRegistry();
const updated = addQubeToRegistry(registry, { qubeId, commitment, bcmr });
```

---

## Protocol Compatibility

Cross-verified against the Python implementation (518 tests).

| Operation | Algorithm |
|-----------|-----------|
| Block hashing | `SHA256(canonicalStringify(block))` — recursive key-sorted JSON |
| Genesis block signing | `ECDSA(SHA256(SHA256(blockHash).hex.encode()))` |
| Standard block signing | `ECDSA(SHA256(canonicalStringify(block)))` |
| Commitment | `SHA256(compressedPubKeyHexString)` — hashes the ASCII hex characters |
| Qube ID | `commitment[:8].upper()` |
| Master key | `PBKDF2-HMAC-SHA256`, 600K iterations, 32-byte output |
| Block encryption | `AES-256-GCM`, 12-byte random nonce |
| Signatures | DER-encoded ECDSA, secp256k1 |

---

## Browser Support

Works in all modern browsers. No Node.js APIs required for crypto, blocks, package, bcmr, or storage modules. The `covenant/mint` module is Node.js only (CashScript peer dependency).

---

## Dependencies

**Core** (always installed):

| Package | Purpose |
|---------|---------|
| `@noble/secp256k1` | ECDSA key generation and signing |
| `@noble/hashes` | SHA256, RIPEMD160, PBKDF2, HKDF, HMAC |
| `fflate` | ZIP creation and parsing (`.qube` export) |

**Optional peer dependencies** (required only for `@qubesai/sdk/covenant`):

| Package | Purpose |
|---------|---------|
| `cashscript` | CashScript covenant interaction and transaction building |
| `@bitauth/libauth` | BCH address encoding and transaction serialization |

---

## License

MIT
