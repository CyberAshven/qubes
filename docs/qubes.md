# Qubes

A Qube is a sovereign AI agent with cryptographic identity, persistent memory, and the ability to form relationships.

## Identity

Each Qube has:
- **Name**: Human-readable identifier (e.g., "Alice")
- **Qube ID**: 8-character hex identifier derived from public key (e.g., "A1B2C3D4")
- **Full ID**: `{Name}_{QubeID}` (e.g., "Alice_A1B2C3D4")
- **ECDSA Keypair**: secp256k1 curve, same as Bitcoin
- **NFT Token** (optional): Bitcoin Cash CashToken proving identity on-chain

### Key Generation
```python
# From crypto/keys.py
private_key = ec.generate_private_key(ec.SECP256K1())
public_key = private_key.public_key()
qube_id = sha256(public_key_bytes)[:8].hex().upper()
```

Keys are encrypted at rest using:
- PBKDF2 with 600,000 iterations (OWASP 2025 compliant)
- AES-256-GCM encryption
- User's master password as key derivation input

## Memory Chain

Each Qube maintains a blockchain-like memory structure:

```
Block 0 (GENESIS)
    │
    ▼
Block 1 (MESSAGE)
    │
    ▼
Block 2 (THOUGHT) ──► Block 3 (ACTION) ──► Block 4 (OBSERVATION)
    │
    ▼
Block 5 (MESSAGE)
    │
    ...
```

### Block Types

| Type | Purpose | Created When |
|------|---------|--------------|
| `GENESIS` | Birth block with identity metadata | Qube creation |
| `MESSAGE` | Chat messages | User/Qube communication |
| `THOUGHT` | Internal reasoning | Complex analysis (optional) |
| `ACTION` | Tool calls | AI invokes a tool |
| `OBSERVATION` | Tool results | Tool returns data |
| `DECISION` | Choices with reasoning | Decision points |
| `MEMORY_ANCHOR` | Checkpoint with Merkle root | Periodic anchoring |
| `SUMMARY` | Compressed history | Context management |

### Block Structure
```json
{
  "block_number": 42,
  "block_type": "MESSAGE",
  "timestamp": 1699999999,
  "previous_hash": "abc123...",
  "content_hash": "def456...",
  "encrypted_content": "...",  // AES-256-GCM encrypted
  "signature": "..."           // ECDSA signature
}
```

### Message Subtypes
Messages have a `direction` field:
- `human_to_qube`: User speaking to Qube
- `qube_to_human`: Qube responding to user
- `qube_to_qube`: Qube-to-Qube communication
- `group`: Multi-participant message

### Chain Integrity
- Each block references previous block's hash
- Periodic `MEMORY_ANCHOR` blocks store Merkle root
- Full chain can be verified cryptographically
- NFT commitment hash proves chain state on blockchain

## Personality

Qubes have configurable personality traits:

```python
personality = {
    "tone": "friendly",           # friendly, professional, casual, formal
    "verbosity": "balanced",      # concise, balanced, detailed
    "emoji_usage": "moderate",    # none, minimal, moderate, frequent
    "humor": "occasional",        # none, occasional, frequent
    "formality": "casual"         # casual, neutral, formal
}
```

These traits are included in the system prompt sent to AI models.

## Voice

Each Qube can have voice settings:

```python
voice_settings = {
    "tts_provider": "openai",     # openai, elevenlabs, google, piper
    "tts_voice": "alloy",         # Provider-specific voice ID
    "stt_provider": "openai",     # openai, deepgram, whisper_cpp
    "speed": 1.0,                 # 0.5 to 2.0
    "pitch": 1.0                  # Provider-dependent
}
```

## Avatar

Qubes can have AI-generated avatars:
- Generated via DALL-E or similar
- Stored as base64 in identity.json
- Can be uploaded to IPFS for NFT metadata

## Creation Flow

```python
# Simplified from orchestrator/user_orchestrator.py

def create_qube(name: str, personality: dict, password: str):
    # 1. Generate keypair
    private_key, public_key = generate_keypair()
    qube_id = derive_qube_id(public_key)

    # 2. Create directory structure
    qube_dir = data_dir / f"{name}_{qube_id}"
    qube_dir.mkdir()

    # 3. Encrypt and save private key
    encrypted_key = encrypt_private_key(private_key, password)
    save_key(qube_dir / "private_key.pem", encrypted_key)

    # 4. Initialize memory chain with genesis block
    chain = MemoryChain(qube_dir)
    chain.create_genesis_block(name, qube_id, public_key)

    # 5. Initialize relationships and skills
    RelationshipStorage(qube_dir)
    SkillsManager(qube_dir)

    return Qube(qube_dir)
```

## Loading a Qube

```python
def load_qube(qube_id: str, password: str):
    # 1. Find qube directory
    qube_dir = find_qube_dir(qube_id)

    # 2. Decrypt private key
    private_key = decrypt_private_key(
        qube_dir / "private_key.pem",
        password
    )

    # 3. Load identity and chain
    identity = load_json(qube_dir / "identity.json")
    chain = MemoryChain(qube_dir)

    # 4. Load relationships and skills
    relationships = RelationshipStorage(qube_dir)
    skills = SkillsManager(qube_dir)

    return Qube(identity, chain, relationships, skills, private_key)
```
