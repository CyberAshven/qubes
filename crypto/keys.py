"""
Cryptographic Key Management for Qubes

Provides:
- ECDSA secp256k1 key pair generation
- Public key derivation
- Key serialization/deserialization
- Qube ID derivation from public key
- Key encryption for storage
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import base64
import secrets
from typing import Tuple, Optional

from core.exceptions import (
    KeyGenerationError,
    EncryptionError,
    DecryptionError,
    CryptoError,
)
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# KEY GENERATION
# =============================================================================

def generate_key_pair() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """
    Generate ECDSA secp256k1 key pair for Qube identity

    Returns:
        Tuple of (private_key, public_key)

    Raises:
        KeyGenerationError: If key generation fails
    """
    try:
        # Generate private key using secp256k1 curve (Bitcoin-compatible)
        private_key = ec.generate_private_key(
            ec.SECP256K1(),
            backend=default_backend()
        )

        # Derive public key
        public_key = private_key.public_key()

        logger.debug(
            "key_pair_generated",
            curve="secp256k1",
            public_key_hash=hashlib.sha256(
                serialize_public_key(public_key).encode()
            ).hexdigest()[:16]
        )

        return private_key, public_key

    except Exception as e:
        logger.error("key_generation_failed", exc_info=True)
        raise KeyGenerationError(
            "Failed to generate ECDSA secp256k1 key pair",
            cause=e
        )


# =============================================================================
# KEY SERIALIZATION
# =============================================================================

def serialize_private_key(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """
    Serialize private key to PEM format

    Args:
        private_key: ECDSA private key

    Returns:
        PEM-encoded private key bytes
    """
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )


def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> str:
    """
    Serialize public key to compressed hex format (33 bytes)

    Args:
        public_key: ECDSA public key

    Returns:
        Hex string of compressed public key (66 characters)
    """
    # Get raw public key bytes (uncompressed = 65 bytes)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # Compress to 33 bytes (Bitcoin-style compressed public key)
    # Format: 0x02/0x03 (even/odd) + x-coordinate (32 bytes)
    x_bytes = public_bytes[1:33]  # Skip 0x04 prefix
    y_bytes = public_bytes[33:65]

    # Check if y is even or odd
    y_int = int.from_bytes(y_bytes, byteorder='big')
    prefix = b'\x02' if y_int % 2 == 0 else b'\x03'

    compressed = prefix + x_bytes

    return compressed.hex()


def deserialize_private_key(pem_bytes: bytes) -> ec.EllipticCurvePrivateKey:
    """
    Deserialize private key from PEM format

    Args:
        pem_bytes: PEM-encoded private key

    Returns:
        ECDSA private key

    Raises:
        CryptoError: If deserialization fails
    """
    try:
        return serialization.load_pem_private_key(
            pem_bytes,
            password=None,
            backend=default_backend()
        )
    except Exception as e:
        raise CryptoError(
            "Failed to deserialize private key",
            cause=e
        )


def deserialize_public_key(hex_str: str) -> ec.EllipticCurvePublicKey:
    """
    Deserialize public key from compressed hex format

    Args:
        hex_str: Hex string of compressed public key (66 characters)

    Returns:
        ECDSA public key

    Raises:
        CryptoError: If deserialization fails
    """
    try:
        key_bytes = bytes.fromhex(hex_str)

        # Load public key from uncompressed format
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(),
            key_bytes
        )

        return public_key

    except Exception as e:
        raise CryptoError(
            "Failed to deserialize public key",
            cause=e
        )


# =============================================================================
# QUBE ID DERIVATION
# =============================================================================

def derive_qube_id(public_key: ec.EllipticCurvePublicKey) -> str:
    """
    Derive Qube ID from public key (8-character hex string)

    Process:
    1. Serialize public key to compressed hex
    2. SHA-256 hash
    3. Take first 4 bytes (8 hex characters)
    4. Uppercase for readability

    Args:
        public_key: ECDSA public key

    Returns:
        8-character Qube ID (e.g., "A3F2C1B8")

    Example:
        >>> private_key, public_key = generate_key_pair()
        >>> qube_id = derive_qube_id(public_key)
        >>> print(qube_id)  # "A3F2C1B8"
    """
    # Serialize public key
    public_key_hex = serialize_public_key(public_key)

    # SHA-256 hash
    hash_bytes = hashlib.sha256(public_key_hex.encode()).digest()

    # Take first 4 bytes (8 hex characters)
    qube_id = hash_bytes[:4].hex().upper()

    logger.debug(
        "qube_id_derived",
        qube_id=qube_id,
        public_key_hash=public_key_hex[:16] + "..."
    )

    return qube_id


# =============================================================================
# KEY ENCRYPTION FOR STORAGE
# =============================================================================

def derive_master_key_from_password(password: str, salt: bytes, iterations: int = 600000) -> bytes:
    """
    Derive encryption key from master password using PBKDF2

    Args:
        password: User's master password
        salt: Random salt (16 bytes)
        iterations: Number of PBKDF2 iterations (default: 600000 for OWASP 2025)

    Returns:
        32-byte encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )

    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_private_key(
    private_key: ec.EllipticCurvePrivateKey,
    master_password: str,
    salt: Optional[bytes] = None
) -> dict:
    """
    Encrypt private key for secure storage

    Args:
        private_key: ECDSA private key to encrypt
        master_password: User's master password
        salt: Optional salt (generated if not provided)

    Returns:
        Dict with encrypted_key (base64) and salt (base64)

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        # Generate salt if not provided
        if salt is None:
            salt = secrets.token_bytes(16)

        # Derive encryption key from password
        master_key = derive_master_key_from_password(master_password, salt)

        # Create Fernet cipher
        cipher = Fernet(master_key)

        # Serialize private key
        private_key_bytes = serialize_private_key(private_key)

        # Encrypt
        encrypted = cipher.encrypt(private_key_bytes)

        logger.debug(
            "private_key_encrypted",
            salt_b64=base64.b64encode(salt).decode()[:16] + "..."
        )

        return {
            "encrypted_key": base64.b64encode(encrypted).decode(),
            "salt": base64.b64encode(salt).decode(),
            "kdf": "PBKDF2-SHA256",
            "iterations": 600000  # Increased from 100K to 600K (OWASP 2025)
        }

    except Exception as e:
        logger.error("private_key_encryption_failed", exc_info=True)
        raise EncryptionError(
            "Failed to encrypt private key",
            cause=e
        )


def decrypt_private_key(
    encrypted_data: dict,
    master_password: str
) -> ec.EllipticCurvePrivateKey:
    """
    Decrypt private key from storage (backward compatible with old iteration counts)

    Args:
        encrypted_data: Dict with encrypted_key and salt (base64 encoded)
                       May include "iterations" field for backward compatibility
        master_password: User's master password

    Returns:
        Decrypted ECDSA private key

    Raises:
        DecryptionError: If decryption fails (wrong password or corrupted data)
    """
    try:
        # Decode salt and encrypted key
        salt = base64.b64decode(encrypted_data["salt"])
        encrypted_key = base64.b64decode(encrypted_data["encrypted_key"])

        # Check for iteration count (backward compatibility)
        # Old Qubes encrypted with 100K iterations, new ones with 600K
        iterations = encrypted_data.get("iterations", 100000)  # Default to old value for backward compat

        logger.debug(
            "decrypting_private_key",
            iterations=iterations,
            has_iterations_field="iterations" in encrypted_data
        )

        # Derive decryption key with correct iteration count
        master_key = derive_master_key_from_password(master_password, salt, iterations)

        # Create Fernet cipher
        cipher = Fernet(master_key)

        # Decrypt
        private_key_bytes = cipher.decrypt(encrypted_key)

        # Deserialize private key
        private_key = deserialize_private_key(private_key_bytes)

        logger.debug("private_key_decrypted", iterations=iterations)

        return private_key

    except Exception as e:
        logger.error("private_key_decryption_failed", exc_info=True)
        raise DecryptionError(
            "Failed to decrypt private key (wrong password or corrupted data)",
            cause=e
        )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    from utils.logging import configure_logging

    configure_logging(log_level="DEBUG", console_output=True)

    # Generate and test key pair
    private_key, public_key = generate_key_pair()
    qube_id = derive_qube_id(public_key)

    print(f"Qube ID: {qube_id}")

    # Test encryption/decryption
    master_password = "test_password"
    encrypted_data = encrypt_private_key(private_key, master_password)
    decrypted_key = decrypt_private_key(encrypted_data, master_password)

    # Verify
    assert serialize_private_key(private_key) == serialize_private_key(decrypted_key)
    print("Key encryption/decryption verified")
