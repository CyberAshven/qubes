# Server API

The qube.cash server provides NFT minting services for Qubes.

## Overview

**Base URL**: `https://qube.cash/api`

The server handles:
- Qube registration for minting
- Payment monitoring
- NFT creation on Bitcoin Cash
- BCMR metadata registry

## Endpoints

### Health Check

```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 123456
}
```

### Register Qube (V2)

```
POST /api/v2/register
```

**Request**:
```json
{
  "name": "Alice",
  "qube_id": "A1B2C3D4",
  "public_key": "04abc123...",
  "commitment_hash": "sha256_hex_string",
  "avatar_ipfs": "Qm...",  // Optional
  "metadata": {            // Optional
    "description": "My AI agent",
    "created_at": 1699999999
  }
}
```

**Response**:
```json
{
  "success": true,
  "registration_id": "reg_abc123def456",
  "payment": {
    "address": "bitcoincash:qr...",
    "amount_bch": 0.0001,
    "amount_satoshis": 10000,
    "op_return_hex": "6a04...",
    "expires_at": 1700000000
  },
  "websocket_url": "wss://qube.cash/ws/reg_abc123def456"
}
```

### Check Registration Status

```
GET /api/v2/register/{registration_id}
```

**Response**:
```json
{
  "registration_id": "reg_abc123def456",
  "status": "pending",  // pending, paid, minting, completed, expired
  "payment_detected": false,
  "tx_hash": null,
  "token_id": null,
  "created_at": 1699999999,
  "expires_at": 1700000000
}
```

### Get Qube NFT Info

```
GET /api/v2/qubes/{qube_id}
```

**Response**:
```json
{
  "qube_id": "A1B2C3D4",
  "name": "Alice",
  "token_id": "abc123...",
  "commitment_hash": "def456...",
  "minted_at": 1699999999,
  "tx_hash": "ghi789...",
  "bcmr_url": "https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json"
}
```

## WebSocket API

Connect to receive real-time minting updates:

```
wss://qube.cash/ws/{registration_id}
```

### Events

**Payment Detected**:
```json
{
  "event": "payment_detected",
  "tx_hash": "abc123...",
  "confirmations": 0,
  "amount_satoshis": 10000
}
```

**Minting Started**:
```json
{
  "event": "minting_started",
  "timestamp": 1699999999
}
```

**Minting Complete**:
```json
{
  "event": "minting_complete",
  "token_id": "abc123...",
  "tx_hash": "def456...",
  "bcmr_updated": true
}
```

**Error**:
```json
{
  "event": "error",
  "message": "Payment expired",
  "code": "PAYMENT_EXPIRED"
}
```

## BCMR Registry

The server maintains a BCMR (Bitcoin Cash Metadata Registry) at:

```
GET /.well-known/bitcoin-cash-metadata-registry.json
```

This file follows the BCMR v2.0.0 specification and contains metadata for all minted Qubes.

### Registry Structure

```json
{
  "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
  "version": "2.0.0",
  "latestRevision": "2024-11-14T12:00:00.000Z",
  "registryIdentity": {
    "name": "Qubes Registry",
    "description": "Sovereign AI Agent NFT Registry"
  },
  "identities": {
    "abc123...": {
      "name": "Alice",
      "description": "Sovereign AI Agent - Qube ID: A1B2C3D4",
      "uris": {
        "icon": "ipfs://Qm...",
        "web": "https://qube.cash/qubes/Alice_A1B2C3D4"
      },
      "token": {
        "category": "abc123...",
        "symbol": "QUBE"
      }
    }
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_QUBE_ID` | Qube ID format invalid |
| `INVALID_PUBLIC_KEY` | Public key format invalid |
| `DUPLICATE_QUBE` | Qube already registered |
| `PAYMENT_EXPIRED` | Payment window expired |
| `PAYMENT_INSUFFICIENT` | Payment amount too low |
| `MINTING_FAILED` | NFT creation failed |
| `RATE_LIMITED` | Too many requests |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /api/v2/register | 10/hour per IP |
| GET endpoints | 100/minute per IP |
| WebSocket | 1 connection per registration |

## Server Architecture

```
                    ┌─────────────────┐
                    │   Nginx Proxy   │
                    │   (SSL/TLS)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   FastAPI App   │
                    │   (main.py)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│ Registration  │   │    Payment    │   │    Minter     │
│   Service     │   │   Monitor     │   │   Service     │
└───────────────┘   └───────────────┘   └───────────────┘
                             │                    │
                    ┌────────▼────────┐   ┌──────▼──────┐
                    │    Fulcrum     │   │   bitcash   │
                    │   (ElectrumX)   │   │  (BCH lib)  │
                    └─────────────────┘   └─────────────┘
```

## Self-Hosting

The minting server can be self-hosted:

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables:
   ```
   PLATFORM_BCH_MINTING_KEY=...
   FULCRUM_HOST=...
   FULCRUM_PORT=...
   ```
4. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

See `website/DEPLOY.md` for full deployment instructions.
