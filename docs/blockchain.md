# Blockchain Integration

Qubes uses Bitcoin Cash CashTokens to create immutable NFT identities for AI agents.

## Overview

Each Qube can be "minted" as an NFT on the Bitcoin Cash blockchain:
- **Immutable identity proof**: Public key commitment stored on-chain
- **BCMR metadata**: Rich metadata following Bitcoin Cash Metadata Registry standard
- **Permissionless**: CashScript covenant allows anyone to mint — no server involvement
- **Low cost**: ~$0.01 USD equivalent in BCH
- **Instant**: 0-confirmation accepted, typically confirmed in ~10 minutes

## CashScript Covenant

The minting contract (`covenant/qubes_mint.cash`) is a 2-function CashScript covenant:

```cashscript
contract QubesMint(bytes20 platformPkh) {
    function mint(bytes32 commitment) {
        // Minting token must be returned to covenant (Output 0)
        require(tx.outputs[0].lockingBytecode == tx.inputs[this.activeInputIndex].lockingBytecode);
        require(tx.outputs[0].tokenCategory == tx.inputs[this.activeInputIndex].tokenCategory);
        require(tx.outputs[0].value >= 1000);
        // Immutable NFT with commitment sent to recipient (Output 1)
        bytes tokenCategoryImmutable = tx.inputs[this.activeInputIndex].tokenCategory.split(32)[0];
        require(tx.outputs[1].tokenCategory == tokenCategoryImmutable);
        require(tx.outputs[1].nftCommitment == commitment);
        require(tx.outputs[1].value >= 1000);
    }
    function migrate(pubkey platformPk, sig platformSig) {
        require(hash160(platformPk) == platformPkh);
        require(checkSig(platformSig, platformPk));
    }
}
```

- **`mint(commitment)`**: Permissionless — anyone can call it. Returns the minting token to the covenant and creates an immutable NFT with the given commitment.
- **`migrate(pubkey, sig)`**: Platform-only — moves the minting token to a new covenant version (requires platform signature).

### On-chain Constants
- **Category ID**: `c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f`
- **Covenant address**: `bitcoincash:rdlqc0y2ulzyp0ulk3t6gn56lzrxt2fq7s2j232vzghww6m8mtqr7h0rx97sy` (v2, P2SH32)
- **Platform pubkey**: `02acd9db52e4becd10164ba9e97c2d5ff20a831dde6c9cae89a4b4b2ecc9837741`

## Minting Flow (WalletConnect)

The current minting flow uses WalletConnect v2 to sign transactions client-side. No server or platform key is involved in minting.

```
1. User connects BCH wallet via WalletConnect v2
           │
           ▼
2. Frontend calls create_qube_for_minting
   → Python generates secp256k1 keypair + genesis block
   → Commitment = SHA256(compressed_pubkey_hex)
           │
           ▼
3. Frontend calls prepare_qube_mint
   → Python calls covenant/mint-cli.ts in WC mode
   → mint-cli.ts builds CashScript tx:
     - Input 0: Covenant UTXO (minting token, unlocked by contract.unlock.mint())
     - Input 1+: User's funding UTXOs (placeholder P2PKH unlockers)
     - Output 0: Minting token returned to covenant (1000 sats)
     - Output 1: Immutable NFT to recipient (1000 sats)
     - Output 2: Change to user (if above dust)
   → Returns WC transaction object (broadcast: false)
           │
           ▼
4. Frontend sends tx to wallet via bch_signTransaction
   → Wallet signs P2PKH inputs (covenant input already unlocked)
   → Frontend broadcasts signed tx via Fulcrum WebSocket / REST fallback
           │
           ▼
5. Frontend calls finalize_qube_mint
   → Python saves BCMR metadata, uploads to IPFS via Pinata
   → Updates local registry and Qube chain state
```

### Key Implementation Files
- `covenant/mint-cli.ts` — CLI for building mint transactions (subprocess called by Python)
- `blockchain/covenant_client.py` — `CovenantMinter` class, Python wrapper around mint-cli.ts
- `blockchain/manager.py` — High-level orchestration (`prepare_mint_transaction()`, `finalize_qube_nft()`)
- `qubes-gui/src/services/walletConnect.ts` — WC v2 BCH implementation
- `qubes-gui/src/contexts/WalletContext.tsx` — React context for wallet state

### SDK Minting
The `@qubesai/sdk` package provides equivalent functions for programmatic use:
- `broadcastMint(params)` — Platform signs and broadcasts (for server-side use)
- `prepareMintTransaction(params)` — Builds WC transaction object (for client-side use)

## NFT Structure

### CashToken Properties
- **Category ID**: `c9054d53...` (shared across all Qube NFTs)
- **Capability**: None (immutable — cannot be modified after minting)
- **Commitment**: SHA-256 hash of compressed public key hex (32 bytes)

### Commitment Derivation
```python
# From crypto/keys.py
commitment = SHA256(compressed_pubkey_hex_string)  # 32 bytes, hex-encoded = 64 chars
```

The commitment binds the on-chain NFT to the Qube's cryptographic identity without revealing the public key itself.

## BCMR Metadata

The server maintains a BCMR registry at:
`https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json`

```json
{
  "version": "2.0.0",
  "identities": {
    "<category_id>": {
      "name": "Alice",
      "description": "Sovereign AI Agent",
      "uris": {
        "icon": "ipfs://Qm...",
        "web": "https://qube.cash/qubes/Alice_A1B2C3D4"
      },
      "token": {
        "category": "<category_id>",
        "symbol": "QUBE",
        "nfts": {
          "parse": {
            "types": {
              "<commitment>": {
                "name": "Alice",
                "description": "Qube ID: A1B2C3D4"
              }
            }
          }
        }
      }
    }
  }
}
```

## Verification

### Verify Qube Identity
```python
def verify_qube_nft(qube_id: str, token_id: str) -> bool:
    # 1. Fetch token from blockchain
    token = fetch_cashtoken(token_id)

    # 2. Extract commitment hash
    commitment = token.commitment

    # 3. Load local qube identity
    identity = load_qube_identity(qube_id)

    # 4. Recalculate expected commitment
    expected = SHA256(serialize_public_key(identity.public_key))

    # 5. Compare
    return commitment == expected
```

### Verify Chain Integrity
```python
def verify_chain_integrity(qube_id: str) -> bool:
    chain = load_memory_chain(qube_id)

    # Verify each block links to previous
    for i, block in enumerate(chain.blocks[1:], 1):
        if block.previous_hash != chain.blocks[i-1].hash:
            return False

    # Verify Merkle roots at anchor points
    for anchor in chain.get_anchors():
        if not verify_merkle_root(chain, anchor):
            return False

    return True
```

## IPFS Backup

Qubes can be backed up to IPFS for cross-device portability.

### Backup Flow
```
1. Export full Qube data (memory chain, chain state)
         │
         ▼
2. Encrypt with PBKDF2-SHA256 (600K iterations) + AES-256-GCM
         │
         ▼
3. Upload to IPFS via Pinata
         │
         ▼
4. Return IPFS CID (can be embedded in NFT commitment)
```

### Environment Variables
- `PINATA_API_KEY`: Pinata JWT token for IPFS uploads

## Legacy Server-Side Minting

The original minting flow used a server at `qube.cash` (FastAPI). This is still running but no longer used by the app:
- `POST /api/v2/register` → Returns payment address → PaymentMonitor detects payment → Server mints with platform key
- Server code at `/var/www/qube.cash/api/`

## Security Considerations

1. **Permissionless minting**: No platform key needed — the covenant enforces rules on-chain
2. **Commitment privacy**: On-chain commitment is a hash of the pubkey, not the raw key
3. **Immutable tokens**: CashTokens with no capability cannot be modified after creation
4. **Client-side signing**: Private keys never leave the user's wallet
5. **Platform key scope**: Only used for `migrate()` — moving the minting token between covenant versions
6. **0-Conf risk**: Minimal (~$0.01 value), double-spend economically irrational
7. **IPFS encryption**: Backups encrypted with PBKDF2-SHA256 (600K iterations) + AES-256-GCM
