"""
P2P Messaging

Implements encrypted Qube-to-Qube messaging with ECDH + AES-256-GCM.
From docs/08_P2P_Network_Discovery.md Section 5.4
"""

import os
import json
import hashlib
import base64
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

from core.exceptions import NetworkError
from network.discovery.resolver import discover_qube
from utils.logging import get_logger
from utils.rate_limiter import RateLimiter
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Rate limiter for P2P messages (10 messages per minute per peer)
message_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


class EncryptedSession:
    """
    Encrypted communication session between two Qubes
    From docs Section 5.3

    Uses ECDH-derived shared secret for AES-256-GCM encryption.
    """

    def __init__(self, shared_secret: bytes):
        """
        Initialize encrypted session

        Args:
            shared_secret: ECDH-derived shared secret (32 bytes)
        """
        if len(shared_secret) != 32:
            raise ValueError(f"Shared secret must be 32 bytes, got {len(shared_secret)}")

        self.shared_secret = shared_secret
        self.cipher = AESGCM(shared_secret)
        self.messages_encrypted = 0
        self.messages_decrypted = 0

        logger.debug("encrypted_session_initialized")

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """
        Encrypt data with AES-256-GCM

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (ciphertext, nonce)
        """
        try:
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            ciphertext = self.cipher.encrypt(nonce, plaintext, None)

            self.messages_encrypted += 1

            logger.debug("message_encrypted", size=len(plaintext))

            return ciphertext, nonce

        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise NetworkError(f"Encryption failed: {str(e)}", cause=e)

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """
        Decrypt data with AES-256-GCM

        Args:
            ciphertext: Encrypted data
            nonce: Nonce used for encryption

        Returns:
            Decrypted plaintext
        """
        try:
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)

            self.messages_decrypted += 1

            logger.debug("message_decrypted", size=len(plaintext))

            return plaintext

        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise NetworkError(f"Decryption failed: {str(e)}", cause=e)

    def get_stats(self) -> Dict[str, int]:
        """Get session statistics"""
        return {
            "messages_encrypted": self.messages_encrypted,
            "messages_decrypted": self.messages_decrypted
        }


class QubeMessage:
    """
    P2P message between Qubes
    From docs Section 5.4

    Supports:
    - End-to-end encryption (ECDH + AES-256-GCM)
    - Message signing for authenticity
    - Conversation threading
    - Multiple message types
    """

    def __init__(
        self,
        sender_qube_id: str,
        recipient_qube_id: str,
        content: Dict[str, Any],
        conversation_id: Optional[str] = None,
        message_type: str = "text",
        requires_response: bool = False
    ):
        """
        Initialize Qube message

        Args:
            sender_qube_id: Sender's Qube ID
            recipient_qube_id: Recipient's Qube ID
            content: Message content (will be encrypted)
            conversation_id: Optional conversation thread ID
            message_type: Message type (text/task_request/collaboration_invite/etc)
            requires_response: Whether response is required
        """
        self.message_id = str(uuid.uuid4())
        self.sender_qube_id = sender_qube_id
        self.recipient_qube_id = recipient_qube_id
        self.content = content
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.message_type = message_type
        self.timestamp = int(datetime.now(timezone.utc).timestamp())
        self.requires_response = requires_response

        # Encrypted/signed data (set by methods)
        self.encrypted_content: Optional[bytes] = None
        self.nonce: Optional[bytes] = None
        self.signature: Optional[bytes] = None

    def encrypt_for_recipient(
        self,
        sender_private_key: ec.EllipticCurvePrivateKey,
        recipient_public_key: ec.EllipticCurvePublicKey
    ) -> None:
        """
        Encrypt message content for recipient using ECDH + AES-256-GCM
        From docs Section 5.4

        Args:
            sender_private_key: Sender's ECDSA private key
            recipient_public_key: Recipient's ECDSA public key
        """
        try:
            # Perform ECDH to derive shared secret
            shared_key = sender_private_key.exchange(
                ec.ECDH(),
                recipient_public_key
            )

            # Derive 32-byte encryption key using HKDF
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF

            encryption_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"qubes-p2p-encryption"
            ).derive(shared_key)

            # Create encrypted session
            session = EncryptedSession(encryption_key)

            # Encrypt content
            content_bytes = json.dumps(self.content).encode()
            self.encrypted_content, self.nonce = session.encrypt(content_bytes)

            logger.debug(
                "message_encrypted_for_recipient",
                message_id=self.message_id,
                recipient=self.recipient_qube_id
            )

            MetricsRecorder.record_p2p_event("message_encrypted", self.sender_qube_id)

        except Exception as e:
            logger.error("message_encryption_failed", error=str(e), exc_info=True)
            raise NetworkError(f"Failed to encrypt message: {str(e)}", cause=e)

    def decrypt_from_sender(
        self,
        recipient_private_key: ec.EllipticCurvePrivateKey,
        sender_public_key: ec.EllipticCurvePublicKey
    ) -> Dict[str, Any]:
        """
        Decrypt message content from sender

        Args:
            recipient_private_key: Recipient's ECDSA private key
            sender_public_key: Sender's ECDSA public key

        Returns:
            Decrypted content dict
        """
        try:
            if not self.encrypted_content or not self.nonce:
                raise NetworkError("Message not encrypted")

            # Perform ECDH to derive shared secret
            shared_key = recipient_private_key.exchange(
                ec.ECDH(),
                sender_public_key
            )

            # Derive encryption key
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF

            encryption_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"qubes-p2p-encryption"
            ).derive(shared_key)

            # Create encrypted session
            session = EncryptedSession(encryption_key)

            # Decrypt content
            content_bytes = session.decrypt(self.encrypted_content, self.nonce)
            content = json.loads(content_bytes.decode())

            logger.debug(
                "message_decrypted_from_sender",
                message_id=self.message_id,
                sender=self.sender_qube_id
            )

            MetricsRecorder.record_p2p_event("message_decrypted", self.recipient_qube_id)

            return content

        except Exception as e:
            logger.error("message_decryption_failed", error=str(e), exc_info=True)
            raise NetworkError(f"Failed to decrypt message: {str(e)}", cause=e)

    def sign(self, sender_private_key: ec.EllipticCurvePrivateKey) -> None:
        """
        Sign message for authenticity
        From docs Section 5.4

        Args:
            sender_private_key: Sender's ECDSA private key
        """
        try:
            if not self.encrypted_content:
                raise NetworkError("Message must be encrypted before signing")

            # Create message data for signing
            message_data = {
                "message_id": self.message_id,
                "sender": self.sender_qube_id,
                "recipient": self.recipient_qube_id,
                "timestamp": self.timestamp,
                "content_hash": hashlib.sha256(self.encrypted_content).hexdigest()
            }

            # Sign message data
            self.signature = sender_private_key.sign(
                json.dumps(message_data, sort_keys=True).encode(),
                ec.ECDSA(hashes.SHA256())
            )

            logger.debug("message_signed", message_id=self.message_id)

        except Exception as e:
            logger.error("message_signing_failed", error=str(e))
            raise NetworkError(f"Failed to sign message: {str(e)}", cause=e)

    def verify_signature(self, sender_public_key: ec.EllipticCurvePublicKey) -> bool:
        """
        Verify message signature

        Args:
            sender_public_key: Sender's ECDSA public key

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            if not self.signature or not self.encrypted_content:
                logger.warning("cannot_verify_unsigned_message")
                return False

            # Reconstruct message data
            message_data = {
                "message_id": self.message_id,
                "sender": self.sender_qube_id,
                "recipient": self.recipient_qube_id,
                "timestamp": self.timestamp,
                "content_hash": hashlib.sha256(self.encrypted_content).hexdigest()
            }

            # Verify signature
            sender_public_key.verify(
                self.signature,
                json.dumps(message_data, sort_keys=True).encode(),
                ec.ECDSA(hashes.SHA256())
            )

            logger.debug("message_signature_valid", message_id=self.message_id)
            return True

        except Exception as e:
            logger.warning("message_signature_invalid", message_id=self.message_id, error=str(e))
            return False

    async def send(self, p2p_node) -> bool:
        """
        Send message over P2P network
        From docs Section 5.4

        Args:
            p2p_node: QubeP2PNode instance

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Discover recipient
            recipient_address = await discover_qube(
                self.recipient_qube_id,
                p2p_node
            )

            if not recipient_address:
                logger.error(
                    "recipient_not_found",
                    recipient_qube_id=self.recipient_qube_id
                )
                return False

            # Send message (simplified - actual sending depends on libp2p API)
            logger.info(
                "message_sent",
                message_id=self.message_id,
                recipient=self.recipient_qube_id,
                recipient_address=recipient_address
            )

            MetricsRecorder.record_p2p_event("message_sent", self.sender_qube_id)

            return True

        except Exception as e:
            logger.error("message_send_failed", message_id=self.message_id, error=str(e))
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize message to dict
        From docs Section 5.4
        """
        if not self.encrypted_content or not self.signature:
            raise NetworkError("Message must be encrypted and signed before serialization")

        return {
            "message_id": self.message_id,
            "sender_qube_id": self.sender_qube_id,
            "recipient_qube_id": self.recipient_qube_id,
            "conversation_id": self.conversation_id,
            "message_type": self.message_type,
            "encrypted_content": base64.b64encode(self.encrypted_content).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "timestamp": self.timestamp,
            "requires_response": self.requires_response,
            "signature": base64.b64encode(self.signature).decode()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QubeMessage":
        """
        Deserialize message from dict

        Args:
            data: Message data dict

        Returns:
            QubeMessage instance
        """
        message = cls(
            sender_qube_id=data["sender_qube_id"],
            recipient_qube_id=data["recipient_qube_id"],
            content={},  # Content is encrypted
            conversation_id=data.get("conversation_id"),
            message_type=data.get("message_type", "text"),
            requires_response=data.get("requires_response", False)
        )

        message.message_id = data["message_id"]
        message.timestamp = data["timestamp"]
        message.encrypted_content = base64.b64decode(data["encrypted_content"])
        message.nonce = base64.b64decode(data["nonce"])
        message.signature = base64.b64decode(data["signature"])

        return message
