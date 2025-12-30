# Blockchain Integration

Qubes uses Bitcoin Cash CashTokens to create immutable NFT identities for AI agents.

## Overview

Each Qube can be "minted" as an NFT on the Bitcoin Cash blockchain:
- **Immutable identity proof**: Public key hash stored on-chain
- **BCMR metadata**: Rich metadata following Bitcoin Cash Metadata Registry standard
- **Low cost**: ~$0.01 USD equivalent in BCH
- **Instant**: 0-confirmation accepted, typically confirmed in ~10 minutes

## Minting Flow

```
1. User clicks "Mint" in GUI
           │
           ▼
2. Client sends registration request to qube.cash
   POST /api/v2/register
   {
     "name": "Alice",
     "qube_id": "A1B2C3D4",
     "public_key": "04abc...",
     "commitment_hash": "sha256(identity_data)"
   }
           │
           ▼
3. Server returns payment address + OP_RETURN data
   {
     "payment_address": "bitcoincash:qr...",
     "amount_bch": 0.0001,
     "registration_id": "reg_abc123",
     "op_return_hex": "..."
   }
           │
           ▼
4. User sends BCH payment (any wallet)
           │
           ▼
5. Server detects payment in mempool (0-conf)
   PaymentMonitor using Fulcrum ElectrumX
           │
           ▼
6. Server mints NFT with commitment hash
   - Creates immutable CashToken
   - Token ID derived from genesis TX
           │
           ▼
7. Server updates BCMR registry
   qube.cash/.well-known/bitcoin-cash-metadata-registry.json
           │
           ▼
8. Client receives WebSocket notification
   {
     "status": "minted",
     "token_id": "abc123...",
     "tx_hash": "def456..."
   }
           │
           ▼
9. Qube identity updated with NFT info
```

## NFT Structure

### CashToken Properties
- **Category ID**: Derived from genesis transaction
- **Capability**: None (immutable)
- **Commitment**: SHA-256 hash of identity data

### Commitment Data
```python
commitment_data = {
    "name": "Alice",
    "qube_id": "A1B2C3D4",
    "public_key_hash": sha256(public_key),
    "created_at": 1699999999,
    "version": "1.0"
}
commitment_hash = sha256(json.dumps(commitment_data, sort_keys=True))
```

## BCMR Metadata

The server maintains a BCMR registry at:
`https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json`

```json
{
  "version": "2.0.0",
  "identities": {
    "abc123...": {
      "name": "Alice",
      "description": "Sovereign AI Agent",
      "uris": {
        "icon": "ipfs://Qm...",
        "web": "https://qube.cash/qubes/Alice_A1B2C3D4"
      },
      "token": {
        "category": "abc123...",
        "symbol": "QUBE",
        "nfts": {
          "parse": {
            "types": {
              "": {
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
# From blockchain/nft_auth.py

def verify_qube_nft(qube_id: str, token_id: str) -> bool:
    # 1. Fetch token from blockchain
    token = fetch_cashtoken(token_id)

    # 2. Extract commitment hash
    commitment = token.commitment

    # 3. Load local qube identity
    identity = load_qube_identity(qube_id)

    # 4. Recalculate expected commitment
    expected = calculate_commitment_hash(identity)

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

## Chain Sync

Qubes can package their memory chain for backup or transfer:

```python
# From blockchain/chain_package.py

def create_chain_package(qube) -> bytes:
    """Create signed, compressed chain package"""
    package = {
        "qube_id": qube.qube_id,
        "chain_blocks": [b.to_dict() for b in qube.chain.blocks],
        "merkle_root": qube.chain.get_merkle_root(),
        "created_at": time.time()
    }

    # Sign package
    signature = sign_data(json.dumps(package), qube.private_key)
    package["signature"] = signature

    # Compress
    return gzip.compress(json.dumps(package).encode())
```

## Server Components

### Payment Monitor
**Location**: Server at `/var/www/your-domain/api/services/payment_monitor.py`

- Connects to Fulcrum ElectrumX server
- Subscribes to payment addresses
- Detects transactions in mempool (0-conf)
- Triggers minting on payment detection

### Minter Service
**Location**: Server at `/var/www/your-domain/api/services/minter.py`

- Uses `bitcash` library for BCH transactions
- Creates CashToken NFTs
- Manages platform minting wallet

### BCMR Service
**Location**: Server at `/var/www/your-domain/api/services/bcmr_service.py`

- Maintains BCMR registry JSON
- Adds new Qube metadata entries
- Serves registry at `.well-known` endpoint

## IPFS Backup

Qubes can be backed up to IPFS for cross-device portability.

### Backup Flow
```
1. Export full Qube data (memory chain, chain state)
         │
         ▼
2. Encrypt with PBKDF2 (600K iterations) + AES-256-GCM
         │
         ▼
3. Upload to IPFS via Pinata
         │
         ▼
4. Return IPFS CID (can be embedded in NFT commitment)
```

### Backup Command
```python
from storage.ipfs_backup import QubeBackup

backup = QubeBackup(pinata_api_key="...")
result = await backup.backup_to_ipfs(qube, password="user_password")
# Returns: {"ipfs_cid": "Qm...", "ipfs_url": "...", "encrypted_size": 12345}
```

### Restore Command
```python
result = await backup.restore_from_ipfs(
    ipfs_cid="Qm...",
    password="user_password",
    data_dir=Path("data")
)
# Returns: {"qube_id": "...", "qube_name": "...", "chain_length": 42}
```

### Environment Variables
- `PINATA_API_KEY`: Pinata JWT token for IPFS uploads

## Security Considerations

1. **Commitment Hash**: On-chain commitment is a hash, not raw data
2. **Immutable Tokens**: CashTokens with no capability cannot be modified
3. **Server Key**: Platform minting key is stored in environment variables
4. **Payment Verification**: Server verifies payment before minting
5. **0-Conf Risk**: Minimal (~$0.01 value), double-spend unlikely
6. **IPFS Encryption**: Backups encrypted with PBKDF2 (600K iterations) + AES-256-GCM
