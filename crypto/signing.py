"""
ECDSA Signing and Verification for Memory Blocks
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import hashlib
import json
from typing import Dict, Any

from core.exceptions import SignatureError, InvalidSignatureError
from utils.logging import get_logger

logger = get_logger(__name__)


def hash_block(block: Dict[str, Any]) -> str:
    """
    Create SHA-256 hash of block data

    Args:
        block: Block dictionary (excluding block_hash and signature)

    Returns:
        64-character hex string
    """
    block_copy = block.copy()
    block_copy.pop("block_hash", None)
    block_copy.pop("signature", None)

    block_json = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_json.encode()).hexdigest()


def sign_message(private_key: ec.EllipticCurvePrivateKey, message: str) -> str:
    """
    Sign an arbitrary message with ECDSA private key.

    This is used for P2P protocol operations like signing introduction
    block hashes for verification.

    Args:
        private_key: ECDSA private key
        message: String message to sign (e.g., block hash)

    Returns:
        Hex-encoded signature
    """
    try:
        signature = private_key.sign(
            message.encode(),  # UTF-8 encode the message
            ec.ECDSA(hashes.SHA256())
        )
        return signature.hex()
    except Exception as e:
        logger.error("message_signing_failed", exc_info=True)
        raise SignatureError("Failed to sign message", cause=e)


def sign_block(block: Dict[str, Any], private_key: ec.EllipticCurvePrivateKey) -> str:
    """
    Sign block with ECDSA private key

    SPECIAL CASE: Genesis blocks (block_number == 0) use legacy signing method
    for backward compatibility with NFT commitments on Bitcoin Cash blockchain.
    All other blocks use the correct ECDSA signing method.

    Args:
        block: Block dictionary
        private_key: ECDSA private key

    Returns:
        Hex-encoded signature
    """
    try:
        # Genesis blocks MUST use legacy method (NFT commitment on BCH mainnet)
        if block.get("block_number") == 0:
            # Legacy method: sign hash hex string (for BCH NFT compatibility)
            block_hash = hash_block(block)
            signature = private_key.sign(
                block_hash.encode(),  # Signs UTF-8 encoded hex string
                ec.ECDSA(hashes.SHA256())
            )
        else:
            # Correct method: sign JSON directly (all non-genesis blocks)
            block_copy = block.copy()
            block_copy.pop("block_hash", None)
            block_copy.pop("signature", None)
            block_json = json.dumps(block_copy, sort_keys=True)
            signature = private_key.sign(
                block_json.encode(),  # Signs JSON UTF-8 bytes
                ec.ECDSA(hashes.SHA256())
            )

        return signature.hex()

    except Exception as e:
        logger.error("block_signing_failed", exc_info=True)
        raise SignatureError("Failed to sign block", cause=e)


def verify_block_signature(
    block: Dict[str, Any],
    signature: str,
    public_key: ec.EllipticCurvePublicKey
) -> bool:
    """
    Verify block signature

    SPECIAL CASE: Genesis blocks (block_number == 0) use legacy verification
    for backward compatibility with NFT commitments on Bitcoin Cash blockchain.
    All other blocks use the correct ECDSA verification method.

    Args:
        block: Block dictionary
        signature: Hex-encoded signature
        public_key: ECDSA public key

    Returns:
        True if valid

    Raises:
        InvalidSignatureError: If signature is invalid
    """
    try:
        # Genesis blocks: use legacy verification
        if block.get("block_number") == 0:
            # Legacy method: verify against hash hex string
            block_hash = hash_block(block)
            data_to_verify = block_hash.encode()  # UTF-8 encoded hex string
        else:
            # Correct method: verify against JSON (all non-genesis blocks)
            block_copy = block.copy()
            block_copy.pop("block_hash", None)
            block_copy.pop("signature", None)
            block_json = json.dumps(block_copy, sort_keys=True)
            data_to_verify = block_json.encode()  # JSON UTF-8 bytes

        public_key.verify(
            bytes.fromhex(signature),
            data_to_verify,
            ec.ECDSA(hashes.SHA256())
        )
        return True

    except Exception as e:
        logger.error("signature_verification_failed", block_hash=hash_block(block)[:16])
        raise InvalidSignatureError(
            "Block signature verification failed",
            context={"block_hash": hash_block(block)[:16]},
            cause=e
        )
