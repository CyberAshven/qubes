"""
AES-256-GCM Encryption for Qubes

Production-grade encryption for memory blocks and P2P messages.
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
import secrets
import json
from typing import Any, Dict

from core.exceptions import EncryptionError, DecryptionError
from utils.logging import get_logger

logger = get_logger(__name__)


def encrypt_block_data(data: Dict[str, Any], key: bytes) -> Dict[str, str]:
    """
    Encrypt block data using AES-256-GCM

    Args:
        data: Block data dictionary
        key: 32-byte encryption key

    Returns:
        Dict with ciphertext, nonce, and tag (all base64)
    """
    try:
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce

        plaintext = json.dumps(data, sort_keys=True).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        return {
            "ciphertext": ciphertext.hex(),
            "nonce": nonce.hex(),
            "algorithm": "AES-256-GCM"
        }
    except Exception as e:
        logger.error("block_encryption_failed", exc_info=True)
        raise EncryptionError("Failed to encrypt block data", cause=e)


def decrypt_block_data(encrypted: Dict[str, str], key: bytes) -> Dict[str, Any]:
    """
    Decrypt block data using AES-256-GCM

    Args:
        encrypted: Dict with ciphertext and nonce (hex)
        key: 32-byte decryption key

    Returns:
        Decrypted data dictionary
    """
    try:
        aesgcm = AESGCM(key)
        nonce = bytes.fromhex(encrypted["nonce"])
        ciphertext = bytes.fromhex(encrypted["ciphertext"])

        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode())

    except Exception as e:
        logger.error("block_decryption_failed", exc_info=True)
        raise DecryptionError("Failed to decrypt block data", cause=e)


def derive_block_key(master_key: bytes, block_number: int) -> bytes:
    """
    Derive block-specific encryption key using HKDF

    Args:
        master_key: Qube's master encryption key
        block_number: Block number for context

    Returns:
        32-byte block-specific key
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=f"block_{block_number}".encode(),
        backend=default_backend()
    )
    return hkdf.derive(master_key)


def generate_encryption_key() -> bytes:
    """Generate random 32-byte encryption key"""
    return secrets.token_bytes(32)


def encrypt_data(data: bytes, key: bytes) -> bytes:
    """
    Encrypt raw bytes using AES-256-GCM

    Args:
        data: Raw bytes to encrypt
        key: 32-byte encryption key

    Returns:
        Encrypted bytes (nonce + ciphertext)
    """
    try:
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        ciphertext = aesgcm.encrypt(nonce, data, None)

        # Return nonce + ciphertext
        return nonce + ciphertext
    except Exception as e:
        logger.error("data_encryption_failed", exc_info=True)
        raise EncryptionError("Failed to encrypt data", cause=e)


def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt raw bytes using AES-256-GCM

    Args:
        encrypted_data: Encrypted bytes (nonce + ciphertext)
        key: 32-byte decryption key

    Returns:
        Decrypted bytes
    """
    try:
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    except Exception as e:
        logger.error("data_decryption_failed", exc_info=True)
        raise DecryptionError("Failed to decrypt data", cause=e)
