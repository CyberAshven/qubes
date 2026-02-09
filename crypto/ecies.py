"""
ECIES (Elliptic Curve Integrated Encryption Scheme) for Qubes

Provides asymmetric encryption using secp256k1 (Bitcoin-compatible).
Used for encrypting symmetric keys so only the NFT holder can decrypt.

Key features:
- ECDH for shared secret derivation
- HKDF-SHA256 for key derivation
- AES-256-GCM for authenticated encryption
- Compatible with Bitcoin Cash public keys
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import secrets
import aiohttp
from typing import Optional, Tuple

from core.exceptions import EncryptionError, DecryptionError, CryptoError
from crypto.keys import serialize_public_key, deserialize_public_key
from utils.logging import get_logger

logger = get_logger(__name__)

# ECIES constants
EPHEMERAL_PUBLIC_KEY_SIZE = 33  # Compressed public key
NONCE_SIZE = 12  # AES-GCM nonce
TAG_SIZE = 16  # AES-GCM auth tag
AES_KEY_SIZE = 32  # 256-bit key

# Chaingraph endpoint for blockchain queries
CHAINGRAPH_URL = "https://gql.chaingraph.pat.mn/v1/graphql"


def ecies_encrypt(plaintext: bytes, recipient_public_key: ec.EllipticCurvePublicKey) -> bytes:
    """
    Encrypt data using ECIES so only the recipient can decrypt.

    Process:
    1. Generate ephemeral key pair
    2. Derive shared secret via ECDH
    3. Derive AES key via HKDF
    4. Encrypt with AES-256-GCM

    Args:
        plaintext: Data to encrypt
        recipient_public_key: Recipient's secp256k1 public key

    Returns:
        Encrypted data: ephemeral_pubkey (33) || nonce (12) || ciphertext || tag (16)

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        # Generate ephemeral key pair
        ephemeral_private_key = ec.generate_private_key(
            ec.SECP256K1(),
            backend=default_backend()
        )
        ephemeral_public_key = ephemeral_private_key.public_key()

        # Serialize ephemeral public key (compressed, 33 bytes)
        ephemeral_pubkey_hex = serialize_public_key(ephemeral_public_key)
        ephemeral_pubkey_bytes = bytes.fromhex(ephemeral_pubkey_hex)

        # Derive shared secret via ECDH
        shared_secret = ephemeral_private_key.exchange(
            ec.ECDH(),
            recipient_public_key
        )

        # Derive AES key from shared secret using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE,
            salt=None,  # No salt needed - shared secret is already random
            info=b"qubes-ecies-v1",  # Context info for domain separation
            backend=default_backend()
        )
        aes_key = hkdf.derive(shared_secret)

        # Generate random nonce
        nonce = secrets.token_bytes(NONCE_SIZE)

        # Encrypt with AES-256-GCM
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Combine: ephemeral_pubkey || nonce || ciphertext (includes tag)
        result = ephemeral_pubkey_bytes + nonce + ciphertext

        logger.debug(
            "ecies_encrypted",
            plaintext_size=len(plaintext),
            ciphertext_size=len(result),
            ephemeral_pubkey=ephemeral_pubkey_hex[:16] + "..."
        )

        return result

    except Exception as e:
        logger.error("ecies_encryption_failed", error=str(e))
        raise EncryptionError(
            "Failed to encrypt with ECIES",
            context={"plaintext_size": len(plaintext)},
            cause=e
        )


def ecies_decrypt(ciphertext: bytes, private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """
    Decrypt ECIES-encrypted data.

    Process:
    1. Extract ephemeral public key from ciphertext
    2. Derive shared secret via ECDH
    3. Derive AES key via HKDF
    4. Decrypt with AES-256-GCM

    Args:
        ciphertext: Encrypted data from ecies_encrypt
        private_key: Recipient's secp256k1 private key

    Returns:
        Decrypted plaintext

    Raises:
        DecryptionError: If decryption fails (wrong key, corrupted data)
    """
    try:
        # Validate minimum size
        min_size = EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE + TAG_SIZE
        if len(ciphertext) < min_size:
            raise ValueError(f"Ciphertext too short: {len(ciphertext)} < {min_size}")

        # Extract components
        ephemeral_pubkey_bytes = ciphertext[:EPHEMERAL_PUBLIC_KEY_SIZE]
        nonce = ciphertext[EPHEMERAL_PUBLIC_KEY_SIZE:EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE]
        encrypted_data = ciphertext[EPHEMERAL_PUBLIC_KEY_SIZE + NONCE_SIZE:]

        # Deserialize ephemeral public key
        ephemeral_pubkey_hex = ephemeral_pubkey_bytes.hex()
        ephemeral_public_key = deserialize_public_key(ephemeral_pubkey_hex)

        # Derive shared secret via ECDH
        shared_secret = private_key.exchange(
            ec.ECDH(),
            ephemeral_public_key
        )

        # Derive AES key from shared secret using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE,
            salt=None,
            info=b"qubes-ecies-v1",
            backend=default_backend()
        )
        aes_key = hkdf.derive(shared_secret)

        # Decrypt with AES-256-GCM
        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(nonce, encrypted_data, None)

        logger.debug(
            "ecies_decrypted",
            ciphertext_size=len(ciphertext),
            plaintext_size=len(plaintext)
        )

        return plaintext

    except Exception as e:
        logger.error("ecies_decryption_failed", error=str(e))
        raise DecryptionError(
            "Failed to decrypt with ECIES - wrong key or corrupted data",
            context={"ciphertext_size": len(ciphertext)},
            cause=e
        )


async def fetch_public_key_from_address(address: str) -> Optional[str]:
    """
    Fetch public key from blockchain by finding a transaction where the address spent funds.

    When someone spends from an address, their public key is revealed in the transaction
    input's signature script. We query Chaingraph to find this.

    Args:
        address: Bitcoin Cash address (cashaddr format, e.g., "bitcoincash:qz...")

    Returns:
        Compressed public key hex (66 chars) or None if not found

    Note:
        This only works if the address has made outgoing transactions.
        New/receive-only addresses will return None.
    """
    try:
        # Remove prefix if present
        clean_address = address.replace("bitcoincash:", "")

        # Query Chaingraph for transactions where this address was an input
        query = """
        query GetPublicKey($address: String!) {
            output(
                where: {
                    locking_bytecode_pattern: {_regex: $address},
                    spent_by: {_is_null: false}
                }
                limit: 1
            ) {
                spent_by {
                    inputs {
                        unlocking_bytecode
                    }
                }
            }
        }
        """

        async with aiohttp.ClientSession() as session:
            async with session.post(
                CHAINGRAPH_URL,
                json={
                    "query": query,
                    "variables": {"address": clean_address}
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    logger.warning(
                        "chaingraph_query_failed",
                        status=response.status,
                        address=clean_address[:20] + "..."
                    )
                    return None

                data = await response.json()

                # Extract public key from unlocking bytecode
                outputs = data.get("data", {}).get("output", [])
                if not outputs:
                    logger.info(
                        "no_spending_transactions",
                        address=clean_address[:20] + "..."
                    )
                    return None

                # Parse unlocking bytecode to extract public key
                # P2PKH unlocking script format: <signature> <public_key>
                inputs = outputs[0].get("spent_by", {}).get("inputs", [])
                if not inputs:
                    return None

                unlocking_bytecode = inputs[0].get("unlocking_bytecode", "")
                public_key_hex = _extract_public_key_from_script(unlocking_bytecode)

                if public_key_hex:
                    logger.info(
                        "public_key_found",
                        address=clean_address[:20] + "...",
                        pubkey_prefix=public_key_hex[:8]
                    )

                return public_key_hex

    except Exception as e:
        logger.error(
            "fetch_public_key_failed",
            address=address[:20] + "...",
            error=str(e)
        )
        return None


def _extract_public_key_from_script(unlocking_bytecode: str) -> Optional[str]:
    """
    Extract public key from P2PKH unlocking script.

    P2PKH unlocking script format:
    - <signature_length> <signature> <pubkey_length> <pubkey>
    - Signature is typically 71-73 bytes (DER encoded)
    - Public key is 33 bytes (compressed) or 65 bytes (uncompressed)

    Args:
        unlocking_bytecode: Hex string of the unlocking script

    Returns:
        Compressed public key hex or None
    """
    try:
        script_bytes = bytes.fromhex(unlocking_bytecode)

        if len(script_bytes) < 2:
            return None

        # First byte is signature length
        sig_length = script_bytes[0]

        # Skip signature
        offset = 1 + sig_length

        if offset >= len(script_bytes):
            return None

        # Next byte is public key length
        pubkey_length = script_bytes[offset]
        offset += 1

        # Extract public key
        if offset + pubkey_length > len(script_bytes):
            return None

        pubkey_bytes = script_bytes[offset:offset + pubkey_length]

        # Validate and convert to compressed format
        if pubkey_length == 33:
            # Already compressed
            if pubkey_bytes[0] in (0x02, 0x03):
                return pubkey_bytes.hex()
        elif pubkey_length == 65:
            # Uncompressed - convert to compressed
            if pubkey_bytes[0] == 0x04:
                x_bytes = pubkey_bytes[1:33]
                y_bytes = pubkey_bytes[33:65]
                y_int = int.from_bytes(y_bytes, byteorder='big')
                prefix = b'\x02' if y_int % 2 == 0 else b'\x03'
                return (prefix + x_bytes).hex()

        return None

    except Exception as e:
        logger.debug("script_parse_failed", error=str(e))
        return None


def public_key_to_cashaddr(public_key: ec.EllipticCurvePublicKey, network: str = "mainnet") -> str:
    """
    Convert secp256k1 public key to Bitcoin Cash cashaddr format.

    Args:
        public_key: ECDSA secp256k1 public key
        network: "mainnet" or "testnet"

    Returns:
        Bitcoin Cash address (e.g., "bitcoincash:qz...")
    """
    import hashlib

    # Get compressed public key bytes
    pubkey_hex = serialize_public_key(public_key)
    pubkey_bytes = bytes.fromhex(pubkey_hex)

    # SHA256 then RIPEMD160
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    try:
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash, usedforsecurity=False).digest()
    except (ValueError, TypeError):
        from bitcash._ripemd160 import ripemd160 as _ripemd160
        ripemd160_hash = _ripemd160(sha256_hash)
    pubkey_hash = ripemd160_hash

    # Convert to cashaddr format
    # Using simple base32 encoding (full cashaddr implementation is more complex)
    # For production, use a proper cashaddr library
    prefix = "bitcoincash" if network == "mainnet" else "bchtest"

    # For now, return a simplified format
    # In production, use proper cashaddr encoding (bech32-like)
    return f"{prefix}:q{pubkey_hash.hex()}"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def encrypt_symmetric_key_for_recipient(
    symmetric_key: bytes,
    recipient_public_key_hex: str
) -> str:
    """
    Encrypt a symmetric key so only the recipient can decrypt it.

    Convenience wrapper for ECIES encryption of symmetric keys.

    Args:
        symmetric_key: AES key to encrypt (typically 32 bytes)
        recipient_public_key_hex: Recipient's public key in compressed hex format

    Returns:
        Hex-encoded ECIES ciphertext
    """
    recipient_pubkey = deserialize_public_key(recipient_public_key_hex)
    encrypted = ecies_encrypt(symmetric_key, recipient_pubkey)
    return encrypted.hex()


def decrypt_symmetric_key(
    encrypted_key_hex: str,
    private_key: ec.EllipticCurvePrivateKey
) -> bytes:
    """
    Decrypt a symmetric key using ECIES.

    Convenience wrapper for ECIES decryption of symmetric keys.

    Args:
        encrypted_key_hex: Hex-encoded ECIES ciphertext
        private_key: Recipient's private key

    Returns:
        Decrypted symmetric key
    """
    encrypted = bytes.fromhex(encrypted_key_hex)
    return ecies_decrypt(encrypted, private_key)
