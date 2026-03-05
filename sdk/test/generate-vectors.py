#!/usr/bin/env python3
"""
Generate deterministic test vectors for Qubes SDK crypto compatibility tests.

Uses the exact same algorithms as the Qubes Python crypto modules:
  - crypto/keys.py        (key derivation, serialization, commitment, qube ID, PBKDF2)
  - crypto/signing.py     (block hashing, block signing, message signing)
  - crypto/encryption.py  (AES-256-GCM, HKDF)
  - crypto/ecies.py       (ECIES encrypt/decrypt)
  - crypto/merkle.py      (Merkle root computation)

Outputs: sdk/test/compat/vectors.json
"""

import hashlib
import json
import os
import sys
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# =============================================================================
# FIXED SEED - deterministic private key for reproducible tests
# =============================================================================
FIXED_PRIVATE_KEY_HEX = (
    "e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
)

# Second key for ECIES recipient tests
FIXED_PRIVATE_KEY_2_HEX = (
    "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
)


# =============================================================================
# Helper functions (mirror the Python crypto modules exactly)
# =============================================================================

def private_key_from_hex(hex_str: str) -> ec.EllipticCurvePrivateKey:
    """Load a private key from a raw 32-byte hex scalar."""
    scalar = int(hex_str, 16)
    return ec.derive_private_key(scalar, ec.SECP256K1(), default_backend())


def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> str:
    """Compressed public key hex (66 chars) -- mirrors crypto/keys.py."""
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    x_bytes = public_bytes[1:33]
    y_bytes = public_bytes[33:65]
    y_int = int.from_bytes(y_bytes, byteorder="big")
    prefix = b"\x02" if y_int % 2 == 0 else b"\x03"
    compressed = prefix + x_bytes
    return compressed.hex()


def derive_commitment(public_key_hex: str) -> str:
    """SHA-256 of the hex STRING -- mirrors crypto/keys.py."""
    return hashlib.sha256(public_key_hex.encode()).hexdigest()


def derive_qube_id(public_key_hex: str) -> str:
    """First 8 chars of commitment, uppercased -- mirrors crypto/keys.py."""
    return derive_commitment(public_key_hex)[:8].upper()


def hash_block(block: dict) -> str:
    """SHA-256 of canonical JSON (minus block_hash & signature) -- mirrors crypto/signing.py."""
    block_copy = block.copy()
    block_copy.pop("block_hash", None)
    block_copy.pop("signature", None)
    block_json = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_json.encode()).hexdigest()


def sign_block(block: dict, private_key: ec.EllipticCurvePrivateKey) -> str:
    """Sign a block -- mirrors crypto/signing.py exactly."""
    if block.get("block_number") == 0:
        # Genesis: sign the hash hex string
        block_hash = hash_block(block)
        signature = private_key.sign(
            block_hash.encode(),
            ec.ECDSA(hashes.SHA256()),
        )
    else:
        # Standard: sign canonical JSON
        block_copy = block.copy()
        block_copy.pop("block_hash", None)
        block_copy.pop("signature", None)
        block_json = json.dumps(block_copy, sort_keys=True)
        signature = private_key.sign(
            block_json.encode(),
            ec.ECDSA(hashes.SHA256()),
        )
    return signature.hex()


def verify_signature(
    public_key: ec.EllipticCurvePublicKey,
    signature_hex: str,
    data: bytes,
) -> bool:
    """Verify ECDSA signature."""
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            data,
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except Exception:
        return False


def encrypt_aes_gcm(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    """AES-256-GCM encrypt with explicit nonce -- mirrors crypto/encryption.py."""
    aesgcm = AESGCM(key)
    return aesgcm.encrypt(nonce, plaintext, None)


def decrypt_aes_gcm(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """AES-256-GCM decrypt -- mirrors crypto/encryption.py."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def derive_block_key(master_key: bytes, block_number: int) -> bytes:
    """HKDF block key -- mirrors crypto/encryption.py."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=f"block_{block_number}".encode(),
        backend=default_backend(),
    )
    return hkdf.derive(master_key)


def derive_chain_state_key(master_key: bytes) -> bytes:
    """HKDF chain-state key -- mirrors crypto/encryption.py."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"chain_state",
        backend=default_backend(),
    )
    return hkdf.derive(master_key)


def derive_master_key_from_password(
    password: str, salt: bytes, iterations: int = 600000
) -> bytes:
    """PBKDF2-SHA256 → base64url -- mirrors crypto/keys.py."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def compute_merkle_root(block_hashes: list) -> str:
    """Merkle root -- mirrors crypto/merkle.py."""
    if not block_hashes:
        return "0" * 64
    if len(block_hashes) == 1:
        return block_hashes[0]
    current_level = block_hashes[:]
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = left + right
            parent_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(parent_hash)
        current_level = next_level
    return current_level[0]


def ecies_encrypt(
    plaintext: bytes,
    recipient_public_key: ec.EllipticCurvePublicKey,
    ephemeral_private_key: ec.EllipticCurvePrivateKey,
    nonce: bytes,
) -> bytes:
    """
    ECIES encrypt with explicit ephemeral key and nonce for deterministic output.
    Mirrors crypto/ecies.py structure.
    """
    ephemeral_public_key = ephemeral_private_key.public_key()
    ephemeral_pubkey_hex = serialize_public_key(ephemeral_public_key)
    ephemeral_pubkey_bytes = bytes.fromhex(ephemeral_pubkey_hex)

    shared_secret = ephemeral_private_key.exchange(ec.ECDH(), recipient_public_key)

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"qubes-ecies-v1",
        backend=default_backend(),
    )
    aes_key = hkdf.derive(shared_secret)

    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return ephemeral_pubkey_bytes + nonce + ciphertext


def ecies_decrypt(ciphertext: bytes, private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """ECIES decrypt -- mirrors crypto/ecies.py."""
    ephemeral_pubkey_bytes = ciphertext[:33]
    nonce = ciphertext[33:45]
    encrypted_data = ciphertext[45:]

    ephemeral_pubkey_hex = ephemeral_pubkey_bytes.hex()
    ephemeral_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256K1(), bytes.fromhex(ephemeral_pubkey_hex)
    )

    shared_secret = private_key.exchange(ec.ECDH(), ephemeral_public_key)

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"qubes-ecies-v1",
        backend=default_backend(),
    )
    aes_key = hkdf.derive(shared_secret)

    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(nonce, encrypted_data, None)


# =============================================================================
# MAIN: Generate all test vectors
# =============================================================================

def main():
    vectors = {}

    # -------------------------------------------------------------------------
    # (a) Key Derivation
    # -------------------------------------------------------------------------
    priv_key = private_key_from_hex(FIXED_PRIVATE_KEY_HEX)
    pub_key = priv_key.public_key()
    pub_key_hex = serialize_public_key(pub_key)

    vectors["keyDerivation"] = {
        "privateKeyHex": FIXED_PRIVATE_KEY_HEX,
        "publicKeyHex": pub_key_hex,
        "description": "From fixed private key scalar, derive compressed secp256k1 public key",
    }

    # -------------------------------------------------------------------------
    # (b) Commitment
    # -------------------------------------------------------------------------
    commitment = derive_commitment(pub_key_hex)
    vectors["commitment"] = {
        "publicKeyHex": pub_key_hex,
        "commitment": commitment,
        "description": "SHA-256 of the public key hex STRING (not raw bytes)",
    }

    # -------------------------------------------------------------------------
    # (c) Qube ID
    # -------------------------------------------------------------------------
    qube_id = derive_qube_id(pub_key_hex)
    vectors["qubeId"] = {
        "publicKeyHex": pub_key_hex,
        "qubeId": qube_id,
        "description": "First 8 chars of commitment, uppercased",
    }

    # -------------------------------------------------------------------------
    # (d) Canonical Stringify
    # -------------------------------------------------------------------------
    nested_object = {
        "zebra": 1,
        "alpha": {"delta": True, "beta": [3, 2, 1]},
        "middle": "hello",
        "numbers": 42,
    }
    canonical = json.dumps(nested_object, sort_keys=True)
    # Also with the default separators explicitly
    canonical_with_separators = json.dumps(
        nested_object, sort_keys=True, separators=(", ", ": ")
    )

    vectors["canonicalStringify"] = {
        "input": nested_object,
        "canonical": canonical,
        "canonicalWithSeparators": canonical_with_separators,
        "description": (
            "json.dumps(sort_keys=True) - Python default separators are "
            "', ' and ': ' which matches the SDK's canonicalStringify"
        ),
    }

    # -------------------------------------------------------------------------
    # (e) Block Hashing
    # -------------------------------------------------------------------------
    minimal_block = {
        "block_number": 0,
        "timestamp": "2025-01-01T00:00:00Z",
        "qube_id": qube_id,
        "data": {"message": "genesis"},
        "previous_hash": "0" * 64,
    }
    block_hash = hash_block(minimal_block)
    # Show the canonical JSON that was hashed
    block_copy = minimal_block.copy()
    block_copy.pop("block_hash", None)
    block_copy.pop("signature", None)
    canonical_block_json = json.dumps(block_copy, sort_keys=True)

    vectors["blockHashing"] = {
        "block": minimal_block,
        "canonicalJson": canonical_block_json,
        "blockHash": block_hash,
        "description": "SHA-256 of canonical JSON (block_hash and signature fields excluded)",
    }

    # -------------------------------------------------------------------------
    # (f) Block Signing - Genesis (block_number == 0)
    # -------------------------------------------------------------------------
    genesis_block = {
        "block_number": 0,
        "timestamp": "2025-01-01T00:00:00Z",
        "qube_id": qube_id,
        "data": {"message": "genesis"},
        "previous_hash": "0" * 64,
    }
    genesis_hash = hash_block(genesis_block)
    genesis_signature = sign_block(genesis_block, priv_key)

    # Verify it ourselves
    assert verify_signature(pub_key, genesis_signature, genesis_hash.encode()), (
        "Genesis signature self-verification failed!"
    )

    vectors["blockSigningGenesis"] = {
        "block": genesis_block,
        "blockHash": genesis_hash,
        "signedData": genesis_hash,
        "signedDataDescription": "Genesis blocks sign the block hash hex string (UTF-8 encoded)",
        "signature": genesis_signature,
        "publicKeyHex": pub_key_hex,
        "description": (
            "Genesis (block_number=0): sign(hash_hex.encode('utf-8'), ECDSA+SHA256). "
            "ECDSA signatures are non-deterministic; verify with public key instead of comparing bytes."
        ),
    }

    # -------------------------------------------------------------------------
    # (g) Block Signing - Standard (block_number > 0)
    # -------------------------------------------------------------------------
    standard_block = {
        "block_number": 1,
        "timestamp": "2025-01-01T00:01:00Z",
        "qube_id": qube_id,
        "data": {"message": "hello world"},
        "previous_hash": genesis_hash,
    }
    standard_block_copy = standard_block.copy()
    standard_block_copy.pop("block_hash", None)
    standard_block_copy.pop("signature", None)
    standard_canonical_json = json.dumps(standard_block_copy, sort_keys=True)
    standard_hash = hash_block(standard_block)
    standard_signature = sign_block(standard_block, priv_key)

    # Verify it ourselves
    assert verify_signature(
        pub_key, standard_signature, standard_canonical_json.encode()
    ), "Standard signature self-verification failed!"

    vectors["blockSigningStandard"] = {
        "block": standard_block,
        "blockHash": standard_hash,
        "signedData": standard_canonical_json,
        "signedDataDescription": "Standard blocks sign the canonical JSON string (UTF-8 encoded)",
        "signature": standard_signature,
        "publicKeyHex": pub_key_hex,
        "description": (
            "Standard (block_number>0): sign(json.dumps(block, sort_keys=True).encode('utf-8'), ECDSA+SHA256). "
            "ECDSA signatures are non-deterministic; verify with public key instead of comparing bytes."
        ),
    }

    # -------------------------------------------------------------------------
    # (h) AES-256-GCM with fixed key and nonce
    # -------------------------------------------------------------------------
    aes_key = bytes.fromhex(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    aes_nonce = bytes.fromhex("000102030405060708090a0b")
    aes_plaintext_obj = {"message": "hello world", "count": 42}
    aes_plaintext_json = json.dumps(aes_plaintext_obj, sort_keys=True)
    aes_plaintext_bytes = aes_plaintext_json.encode()
    aes_ciphertext = encrypt_aes_gcm(aes_plaintext_bytes, aes_key, aes_nonce)

    # Verify round-trip
    assert decrypt_aes_gcm(aes_ciphertext, aes_key, aes_nonce) == aes_plaintext_bytes

    vectors["aes256gcm"] = {
        "keyHex": aes_key.hex(),
        "nonceHex": aes_nonce.hex(),
        "plaintext": aes_plaintext_obj,
        "plaintextJson": aes_plaintext_json,
        "ciphertextHex": aes_ciphertext.hex(),
        "result": {
            "ciphertext": aes_ciphertext.hex(),
            "nonce": aes_nonce.hex(),
            "algorithm": "AES-256-GCM",
        },
        "description": (
            "AES-256-GCM encrypt: plaintext is json.dumps(data, sort_keys=True).encode(). "
            "Ciphertext includes 16-byte auth tag appended."
        ),
    }

    # -------------------------------------------------------------------------
    # (i) HKDF
    # -------------------------------------------------------------------------
    hkdf_master_key = bytes.fromhex(
        "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    )
    block_key_0 = derive_block_key(hkdf_master_key, 0)
    block_key_1 = derive_block_key(hkdf_master_key, 1)
    block_key_42 = derive_block_key(hkdf_master_key, 42)
    chain_state_key = derive_chain_state_key(hkdf_master_key)

    vectors["hkdf"] = {
        "masterKeyHex": hkdf_master_key.hex(),
        "blockKeys": [
            {
                "blockNumber": 0,
                "info": "block_0",
                "derivedKeyHex": block_key_0.hex(),
            },
            {
                "blockNumber": 1,
                "info": "block_1",
                "derivedKeyHex": block_key_1.hex(),
            },
            {
                "blockNumber": 42,
                "info": "block_42",
                "derivedKeyHex": block_key_42.hex(),
            },
        ],
        "chainStateKey": {
            "info": "chain_state",
            "derivedKeyHex": chain_state_key.hex(),
        },
        "description": (
            "HKDF-SHA256 with salt=None, length=32. "
            "Info strings: 'block_{n}' for block keys, 'chain_state' for chain state key."
        ),
    }

    # -------------------------------------------------------------------------
    # (j) PBKDF2
    # -------------------------------------------------------------------------
    pbkdf2_password = "test-password-123"
    pbkdf2_salt = bytes.fromhex("deadbeefcafebabe1234567890abcdef")

    # Fast vector (1000 iterations) for quick tests
    pbkdf2_key_fast = derive_master_key_from_password(
        pbkdf2_password, pbkdf2_salt, iterations=1000
    )
    # Production vector (600000 iterations)
    pbkdf2_key_production = derive_master_key_from_password(
        pbkdf2_password, pbkdf2_salt, iterations=600000
    )

    vectors["pbkdf2"] = {
        "password": pbkdf2_password,
        "saltHex": pbkdf2_salt.hex(),
        "vectors": [
            {
                "iterations": 1000,
                "derivedKeyBase64url": pbkdf2_key_fast.decode("ascii"),
                "description": "Fast test vector (1000 iterations)",
            },
            {
                "iterations": 600000,
                "derivedKeyBase64url": pbkdf2_key_production.decode("ascii"),
                "description": "Production vector (600000 iterations, OWASP 2025)",
            },
        ],
        "description": (
            "PBKDF2-SHA256, length=32, output is base64url-encoded "
            "(for Fernet compatibility). Password is UTF-8 encoded."
        ),
    }

    # -------------------------------------------------------------------------
    # (k) Merkle Root
    # -------------------------------------------------------------------------
    merkle_hashes_empty = []
    merkle_hashes_one = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
    merkle_hashes_two = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ]
    merkle_hashes_three = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    ]
    merkle_hashes_four = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    ]

    vectors["merkleRoot"] = {
        "cases": [
            {
                "name": "empty",
                "hashes": merkle_hashes_empty,
                "root": compute_merkle_root(merkle_hashes_empty),
                "description": "Empty list returns 64 zeros",
            },
            {
                "name": "single",
                "hashes": merkle_hashes_one,
                "root": compute_merkle_root(merkle_hashes_one),
                "description": "Single hash returns itself",
            },
            {
                "name": "two",
                "hashes": merkle_hashes_two,
                "root": compute_merkle_root(merkle_hashes_two),
                "description": "Two hashes: SHA-256(left + right) where + is string concatenation",
            },
            {
                "name": "three_odd",
                "hashes": merkle_hashes_three,
                "root": compute_merkle_root(merkle_hashes_three),
                "description": "Odd count: last hash is duplicated",
            },
            {
                "name": "four",
                "hashes": merkle_hashes_four,
                "root": compute_merkle_root(merkle_hashes_four),
                "description": "Four hashes: balanced binary tree",
            },
        ],
        "description": (
            "Merkle tree: bottom-up, pairs concatenated as strings (not bytes), "
            "SHA-256 of concatenated hex string. Odd levels duplicate the last hash."
        ),
    }

    # -------------------------------------------------------------------------
    # (l) ECIES round-trip
    # -------------------------------------------------------------------------
    # Use a deterministic ephemeral key for the encrypt side so the output is fixed
    ephemeral_priv_hex = (
        "1111111111111111111111111111111111111111111111111111111111111111"
    )
    ephemeral_priv = private_key_from_hex(ephemeral_priv_hex)
    ecies_nonce = bytes.fromhex("aabbccddeeff00112233aabb")

    recipient_priv = private_key_from_hex(FIXED_PRIVATE_KEY_2_HEX)
    recipient_pub = recipient_priv.public_key()
    recipient_pub_hex = serialize_public_key(recipient_pub)

    ecies_plaintext = b"secret message for ECIES test"

    ecies_ciphertext = ecies_encrypt(
        ecies_plaintext, recipient_pub, ephemeral_priv, ecies_nonce
    )
    # Verify round-trip
    ecies_decrypted = ecies_decrypt(ecies_ciphertext, recipient_priv)
    assert ecies_decrypted == ecies_plaintext, "ECIES round-trip failed!"

    ephemeral_pub_hex = serialize_public_key(ephemeral_priv.public_key())

    vectors["ecies"] = {
        "recipientPrivateKeyHex": FIXED_PRIVATE_KEY_2_HEX,
        "recipientPublicKeyHex": recipient_pub_hex,
        "ephemeralPrivateKeyHex": ephemeral_priv_hex,
        "ephemeralPublicKeyHex": ephemeral_pub_hex,
        "nonceHex": ecies_nonce.hex(),
        "plaintext": ecies_plaintext.decode("utf-8"),
        "plaintextHex": ecies_plaintext.hex(),
        "ciphertextHex": ecies_ciphertext.hex(),
        "format": "ephemeral_pubkey(33) || nonce(12) || ciphertext+tag",
        "hkdfInfo": "qubes-ecies-v1",
        "description": (
            "ECIES: ECDH shared secret → HKDF-SHA256(info='qubes-ecies-v1') → AES-256-GCM. "
            "Deterministic test uses fixed ephemeral key and nonce. "
            "In production, both are random. SDK tests should verify round-trip."
        ),
    }

    # -------------------------------------------------------------------------
    # Write output
    # -------------------------------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "compat", "vectors.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(vectors, f, indent=2)

    print(f"Test vectors written to: {output_path}")
    print(f"Total sections: {len(vectors)}")
    for key in vectors:
        print(f"  - {key}")


if __name__ == "__main__":
    main()
