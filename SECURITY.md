# Security

## Reporting Vulnerabilities

Report security issues via email or by opening a GitHub issue. Please allow reasonable time for a response before public disclosure.

---

## CashScript Covenant

### What the covenant enforces

The minting covenant is a CashScript contract that enforces the following transaction structure on every `mint()` call:

- **Output 0**: The minting token (NFT with minting capability) is returned to the same covenant address. The contract checks its own locking bytecode, so the token cannot be redirected without a covenant upgrade.
- **Output 1**: An immutable NFT carrying the user-supplied commitment is sent to the address provided by the caller.
- **No platform fee** is enforced at the protocol level. The contract does not require payment to any platform address.
- **`mint()` is permissionless** — any caller can invoke it with a valid transaction structure. There is no allowlist or authentication at the contract layer.

### The `migrate()` function

The covenant includes a `migrate()` function that allows the platform to move the minting token to a new contract address. This is standard practice for early-stage CashScript deployments where contract bugs may need to be corrected.

**What `migrate()` can do:**
- Move the minting token (the capability to mint) to a new covenant address.

**What `migrate()` cannot do:**
- Mint arbitrary NFTs.
- Transfer, modify, or destroy NFTs already held by users.
- Access or modify any user data, keys, or encrypted state.
- Affect any on-chain asset except the single minting token held by the covenant.

**Why it exists:**
- Contract upgrades and bug fixes during the beta period.
- BCH CashScript contracts are immutable once deployed; migration is the standard upgrade path.

**Current governance:**
- `migrate()` is gated by a single platform key. The HASH160 of this key is embedded in the constructor argument at deployment time.

**Roadmap:**
- Once the protocol is stable and there is a meaningful user base, the admin key will be replaced with a timelocked multisig governance scheme. This removes single-key control and requires multiple parties and a time delay for any migration.

---

## SDK Cryptographic Guarantees

### Commitment construction

The NFT commitment is defined as:

```
commitment = SHA256(compressed_pubkey_hex_string)
```

The input to SHA256 is the hex-encoded string representation of the compressed public key, not the raw bytes. This is intentional and documented to ensure cross-platform reproducibility.

### Block hashing

Block hashes use canonical JSON serialization: all object keys are sorted recursively before serialization. This guarantees deterministic hashes across all runtimes and languages.

### Cross-verification

All cryptographic operations in the TypeScript SDK are cross-verified against the Python reference implementation. The test suite includes 518 tests, including explicit Python cross-compatibility vectors.

---

## Encryption

All encryption happens client-side. The server never receives or stores plaintext user data, keys, or block contents.

| Layer | Algorithm |
|---|---|
| Block data and chain state | AES-256-GCM |
| Inter-agent encryption | ECIES (secp256k1) |
| Master key derivation | PBKDF2-SHA256, 600,000 iterations (OWASP 2025 recommendation) |
| Key derivation function | HKDF-SHA256 with 12-byte nonces |

The master key is derived locally from the user's password and is never transmitted. Encrypted blobs uploaded to IPFS or the server are opaque ciphertext.

---

## Identity

- Identity keys use ECDSA on secp256k1.
- Qube ID is derived as `SHA256(pubkey)[:8].hex().upper()` — a short, human-readable identifier derived deterministically from the public key.
- Private keys are stored encrypted under the user's master key and never leave the device in plaintext.
