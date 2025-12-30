# Security

Qubes implements multiple layers of cryptographic security.

## Key Management

### Key Generation
Each Qube has an ECDSA secp256k1 keypair (same curve as Bitcoin):

```python
# From crypto/keys.py
from cryptography.hazmat.primitives.asymmetric import ec

private_key = ec.generate_private_key(ec.SECP256K1())
public_key = private_key.public_key()
```

### Key Derivation
The Qube ID is derived from the public key:

```python
qube_id = sha256(public_key_bytes)[:8].hex().upper()
# Example: "A1B2C3D4"
```

### Key Encryption at Rest
Private keys are encrypted using:
- **PBKDF2**: 600,000 iterations (OWASP 2025 compliant)
- **AES-256-GCM**: Authenticated encryption
- **Salt**: Random 16 bytes per key

```python
# Key derivation
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=600000
)
encryption_key = kdf.derive(password.encode())

# Encryption
cipher = AESGCM(encryption_key)
encrypted = cipher.encrypt(nonce, private_key_bytes, None)
```

## Content Encryption

All block content is encrypted:

```python
# From crypto/encryption.py
def encrypt_content(content: str, key: bytes) -> bytes:
    cipher = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = cipher.encrypt(nonce, content.encode(), None)
    return nonce + encrypted

def decrypt_content(encrypted: bytes, key: bytes) -> str:
    cipher = AESGCM(key)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    return cipher.decrypt(nonce, ciphertext, None).decode()
```

## Digital Signatures

Blocks are signed with the Qube's private key:

```python
# From crypto/signing.py
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

def sign_block(block_data: bytes, private_key) -> bytes:
    signature = private_key.sign(
        block_data,
        ec.ECDSA(hashes.SHA256())
    )
    return signature

def verify_signature(block_data: bytes, signature: bytes, public_key) -> bool:
    try:
        public_key.verify(signature, block_data, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
```

## Chain Integrity

### Merkle Trees
Memory chains use Merkle trees for efficient verification:

```python
# From crypto/merkle.py
def build_merkle_tree(block_hashes: List[bytes]) -> bytes:
    if not block_hashes:
        return b'\x00' * 32

    while len(block_hashes) > 1:
        if len(block_hashes) % 2 == 1:
            block_hashes.append(block_hashes[-1])  # Duplicate last

        new_level = []
        for i in range(0, len(block_hashes), 2):
            combined = block_hashes[i] + block_hashes[i + 1]
            new_level.append(sha256(combined))
        block_hashes = new_level

    return block_hashes[0]  # Root
```

### Block Linking
Each block references the previous block's hash:

```python
block = {
    "block_number": n,
    "previous_hash": sha256(previous_block),
    "content_hash": sha256(encrypted_content),
    "timestamp": time.time(),
    "signature": sign(block_data, private_key)
}
```

## Input Validation

The Rust layer validates all inputs before passing to Python:

```rust
// From src-tauri/src/lib.rs

fn validate_qube_id(id: &str) -> Result<(), String> {
    // Must be 8 hex characters
    if id.len() != 8 || !id.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("Invalid qube_id format".to_string());
    }
    Ok(())
}

fn validate_path(path: &str) -> Result<(), String> {
    // Prevent path traversal
    if path.contains("..") || path.contains("~") {
        return Err("Invalid path".to_string());
    }
    Ok(())
}
```

## Secret Handling

Secrets are never passed via command line:

```rust
// Good: Pass via stdin
let mut child = Command::new("python")
    .arg("gui_bridge.py")
    .stdin(Stdio::piped())
    .spawn()?;

child.stdin.as_mut().unwrap()
    .write_all(password.as_bytes())?;

// Bad: Would expose in process listing
// Command::new("python").arg("--password").arg(password)
```

## NFT Security

### Commitment Hash
The on-chain NFT contains only a hash, not raw data:

```python
commitment = sha256(json.dumps({
    "qube_id": qube_id,
    "public_key_hash": sha256(public_key),
    "created_at": timestamp
}, sort_keys=True))
```

### Immutable Tokens
CashTokens are minted with no capability, making them immutable:

```python
# Cannot be modified after minting
token = create_cashtoken(
    commitment=commitment_hash,
    capability=None  # Immutable
)
```

## API Key Storage

API keys are encrypted with the master password:

```python
# From config/settings.py
def save_api_key(provider: str, key: str, password: str):
    encrypted = encrypt_content(key, derive_key(password))
    config['api_keys'][provider] = base64.b64encode(encrypted)
```

## Security Boundaries

```
┌─────────────────────────────────────┐
│           User Browser              │
│  (Tauri WebView, sandboxed)         │
└─────────────┬───────────────────────┘
              │ Tauri IPC
              ▼
┌─────────────────────────────────────┐
│           Rust Backend              │
│  - Input validation                 │
│  - Path sanitization                │
│  - Secret handling                  │
└─────────────┬───────────────────────┘
              │ subprocess + stdin
              ▼
┌─────────────────────────────────────┐
│          Python Backend             │
│  - Business logic                   │
│  - Cryptographic operations         │
│  - AI API calls                     │
└─────────────────────────────────────┘
```

## Threat Model

### Protected Against
- Path traversal attacks
- Command injection
- Secret exposure in process lists
- Memory chain tampering (detected via signatures)
- Unauthorized key access (encryption at rest)

### Trust Assumptions
- User's machine is not compromised
- Master password is not shared
- AI providers handle data per their policies
- Server (qube.cash) is trusted for minting

## Best Practices

1. **Use a strong master password** - This protects all Qube keys
2. **Don't share private keys** - Each Qube should have unique keys
3. **Review AI provider policies** - Understand data retention
4. **Use local models for sensitive data** - Ollama, Whisper.cpp, Piper
5. **Keep software updated** - Auto-update is enabled by default
