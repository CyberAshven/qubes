"""
Manual Qube Introduction

Allows users to explicitly connect two Qubes.
From docs/08_P2P_Network_Discovery.md Section 5.2.4
"""

import json
from typing import Dict, Any
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from core.exceptions import NetworkError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


async def introduce_qubes(
    qube_a,
    qube_b,
    introduction_message: str = "Hello, I'd like to connect!"
) -> bool:
    """
    Manually introduce two Qubes to each other
    From docs Section 5.2.4

    User explicitly connects Qube A to Qube B. This bypasses discovery
    and creates a direct introduction.

    Args:
        qube_a: First Qube instance
        qube_b: Second Qube instance (or Qube ID + address)
        introduction_message: Optional introduction message

    Returns:
        True if introduction successful
    """
    try:
        logger.info(
            "introducing_qubes",
            qube_a_id=qube_a.qube_id,
            qube_b_id=qube_b.qube_id if hasattr(qube_b, 'qube_id') else str(qube_b)
        )

        # Extract Qube B information
        if hasattr(qube_b, 'qube_id'):
            qube_b_id = qube_b.qube_id
            qube_b_address = qube_b.p2p_node.multiaddr if hasattr(qube_b, 'p2p_node') else None
            qube_b_public_key = qube_b.public_key
        else:
            # Assume qube_b is a dict with info
            qube_b_id = qube_b.get('qube_id')
            qube_b_address = qube_b.get('p2p_address')
            qube_b_public_key = qube_b.get('public_key')

        if not qube_b_id or not qube_b_address:
            raise NetworkError("Invalid Qube B information")

        # Create introduction message from A to B
        intro_message = {
            "type": "INTRODUCTION",
            "from_qube": qube_a.qube_id,
            "to_qube": qube_b_id,
            "public_key": _serialize_public_key(qube_a.public_key),
            "p2p_address": qube_a.p2p_node.multiaddr if hasattr(qube_a, 'p2p_node') else None,
            "message": introduction_message,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }

        # Sign introduction
        intro_message["signature"] = _sign_introduction(intro_message, qube_a.private_key)

        # Send introduction to Qube B
        # (Simplified - actual sending depends on libp2p API)
        logger.info(
            "introduction_sent",
            from_qube=qube_a.qube_id,
            to_qube=qube_b_id,
            address=qube_b_address
        )

        MetricsRecorder.record_p2p_event("introduction_sent", qube_a.qube_id)

        return True

    except Exception as e:
        logger.error("introduction_failed", error=str(e), exc_info=True)
        return False


async def handle_introduction(
    qube,
    intro_message: Dict[str, Any],
    sender_public_key: ec.EllipticCurvePublicKey
) -> bool:
    """
    Handle incoming introduction request

    Args:
        qube: This Qube instance
        intro_message: Introduction message data
        sender_public_key: Sender's public key

    Returns:
        True if introduction accepted
    """
    try:
        from_qube = intro_message.get("from_qube")
        message_text = intro_message.get("message")

        logger.info(
            "introduction_received",
            qube_id=qube.qube_id,
            from_qube=from_qube,
            message=message_text
        )

        # Verify signature
        if not _verify_introduction_signature(intro_message, sender_public_key):
            logger.error("introduction_signature_invalid", from_qube=from_qube)
            return False

        # Store introduced Qube information
        # (This would integrate with the Qube's known peers)
        introduced_qube_info = {
            "qube_id": from_qube,
            "public_key": intro_message.get("public_key"),
            "p2p_address": intro_message.get("p2p_address"),
            "introduced_at": intro_message.get("timestamp"),
            "introduction_message": message_text
        }

        logger.info(
            "introduction_accepted",
            qube_id=qube.qube_id,
            from_qube=from_qube
        )

        MetricsRecorder.record_p2p_event("introduction_accepted", qube.qube_id)

        return True

    except Exception as e:
        logger.error("introduction_handling_failed", error=str(e))
        return False


def _serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> str:
    """Serialize public key to string"""
    from cryptography.hazmat.primitives import serialization
    import base64

    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(pem).decode()


def _sign_introduction(
    intro_message: Dict[str, Any],
    private_key: ec.EllipticCurvePrivateKey
) -> str:
    """Sign introduction message"""
    import base64

    # Remove signature field
    message_copy = {k: v for k, v in intro_message.items() if k != "signature"}

    # Serialize and sign
    message_data = json.dumps(message_copy, sort_keys=True).encode()
    signature = private_key.sign(
        message_data,
        ec.ECDSA(hashes.SHA256())
    )

    return base64.b64encode(signature).decode()


def _verify_introduction_signature(
    intro_message: Dict[str, Any],
    public_key: ec.EllipticCurvePublicKey
) -> bool:
    """Verify introduction message signature"""
    try:
        import base64

        signature = intro_message.get("signature")
        if not signature:
            return False

        signature_bytes = base64.b64decode(signature)

        # Reconstruct signed data
        message_copy = {k: v for k, v in intro_message.items() if k != "signature"}
        message_data = json.dumps(message_copy, sort_keys=True).encode()

        # Verify
        public_key.verify(
            signature_bytes,
            message_data,
            ec.ECDSA(hashes.SHA256())
        )

        return True

    except Exception:
        return False
