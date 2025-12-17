"""
Qube-to-Qube Messenger

High-level interface for secure Qube communication.
Integrates discovery, handshake, and encrypted messaging.
From docs/08_P2P_Network_Discovery.md
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec

from core.exceptions import NetworkError, AuthenticationError
from network.p2p_node import QubeP2PNode
from network.handshake import QubeHandshake
from network.messaging import QubeMessage, EncryptedSession
from network.discovery.resolver import discover_qube
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class QubeMessenger:
    """
    High-level Qube-to-Qube messaging interface

    Provides:
    - Automatic discovery and handshake
    - Encrypted message sending
    - Message receiving and handling
    - Conversation management
    - Session lifecycle management
    """

    def __init__(
        self,
        qube_id: str,
        private_key: ec.EllipticCurvePrivateKey,
        public_key: ec.EllipticCurvePublicKey,
        p2p_node: QubeP2PNode,
        nft_contract: Optional[str] = None,
        nft_token_id: Optional[int] = None
    ):
        """
        Initialize Qube messenger

        Args:
            qube_id: This Qube's ID
            private_key: ECDSA private key
            public_key: ECDSA public key
            p2p_node: P2P node instance
            nft_contract: NFT contract address (optional)
            nft_token_id: NFT token ID (optional)
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.public_key = public_key
        self.p2p_node = p2p_node

        # Initialize handshake handler
        self.handshake = QubeHandshake(
            qube_id=qube_id,
            private_key=private_key,
            public_key=public_key,
            nft_contract=nft_contract,
            nft_token_id=nft_token_id
        )

        # Conversations and messages
        self.conversations: Dict[str, List[QubeMessage]] = {}
        self.message_handlers: Dict[str, Callable] = {}

        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.handshakes_completed = 0

        logger.info("qube_messenger_initialized", qube_id=qube_id)

    async def send_message(
        self,
        recipient_qube_id: str,
        content: Dict[str, Any],
        recipient_public_key: ec.EllipticCurvePublicKey,
        message_type: str = "text",
        conversation_id: Optional[str] = None,
        requires_response: bool = False
    ) -> bool:
        """
        Send encrypted message to another Qube

        Automatically handles:
        - Qube discovery
        - Handshake (if needed)
        - Message encryption
        - Message signing
        - Message sending

        Args:
            recipient_qube_id: Target Qube ID
            content: Message content (will be encrypted)
            recipient_public_key: Recipient's public key
            message_type: Message type (text/task_request/etc)
            conversation_id: Optional conversation thread ID
            requires_response: Whether response is required

        Returns:
            True if message sent successfully
        """
        try:
            logger.info(
                "sending_message",
                recipient_qube_id=recipient_qube_id,
                message_type=message_type
            )

            # Ensure we have an active session (handshake if needed)
            session = self.handshake.get_session(recipient_qube_id)
            if not session:
                logger.debug(
                    "no_active_session_initiating_handshake",
                    recipient_qube_id=recipient_qube_id
                )

                handshake_result = await self.handshake.initiate(
                    target_qube_id=recipient_qube_id,
                    p2p_node=self.p2p_node,
                    target_public_key=recipient_public_key
                )

                self.handshakes_completed += 1

                logger.info(
                    "handshake_established",
                    recipient_qube_id=recipient_qube_id,
                    trust_score=handshake_result.get("trust_score")
                )

            # Create message
            message = QubeMessage(
                sender_qube_id=self.qube_id,
                recipient_qube_id=recipient_qube_id,
                content=content,
                conversation_id=conversation_id,
                message_type=message_type,
                requires_response=requires_response
            )

            # Encrypt message
            message.encrypt_for_recipient(
                sender_private_key=self.private_key,
                recipient_public_key=recipient_public_key
            )

            # Sign message
            message.sign(self.private_key)

            # Send message
            success = await message.send(self.p2p_node)

            if success:
                # Store in conversation history
                conv_id = message.conversation_id
                if conv_id not in self.conversations:
                    self.conversations[conv_id] = []
                self.conversations[conv_id].append(message)

                self.messages_sent += 1

                logger.info(
                    "message_sent_successfully",
                    message_id=message.message_id,
                    recipient_qube_id=recipient_qube_id,
                    conversation_id=conv_id
                )

                MetricsRecorder.record_p2p_event("message_sent", self.qube_id)

            return success

        except Exception as e:
            logger.error(
                "message_send_failed",
                recipient_qube_id=recipient_qube_id,
                error=str(e),
                exc_info=True
            )
            MetricsRecorder.record_p2p_event("message_send_failed", self.qube_id)
            return False

    async def receive_message(
        self,
        message_data: Dict[str, Any],
        sender_public_key: ec.EllipticCurvePublicKey
    ) -> Optional[Dict[str, Any]]:
        """
        Receive and process encrypted message from another Qube

        Args:
            message_data: Serialized message data
            sender_public_key: Sender's public key

        Returns:
            Decrypted message content
        """
        try:
            # Deserialize message
            message = QubeMessage.from_dict(message_data)

            logger.info(
                "receiving_message",
                message_id=message.message_id,
                sender_qube_id=message.sender_qube_id,
                message_type=message.message_type
            )

            # Verify signature
            if not message.verify_signature(sender_public_key):
                logger.error(
                    "message_signature_invalid",
                    message_id=message.message_id,
                    sender_qube_id=message.sender_qube_id
                )
                return None

            # Decrypt message
            content = message.decrypt_from_sender(
                recipient_private_key=self.private_key,
                sender_public_key=sender_public_key
            )

            # Store in conversation history
            conv_id = message.conversation_id
            if conv_id not in self.conversations:
                self.conversations[conv_id] = []
            self.conversations[conv_id].append(message)

            self.messages_received += 1

            logger.info(
                "message_received_successfully",
                message_id=message.message_id,
                sender_qube_id=message.sender_qube_id,
                conversation_id=conv_id
            )

            MetricsRecorder.record_p2p_event("message_received", self.qube_id)

            # Call message handler if registered
            handler = self.message_handlers.get(message.message_type)
            if handler:
                try:
                    await handler(message, content)
                except Exception as e:
                    logger.error(
                        "message_handler_failed",
                        message_type=message.message_type,
                        error=str(e)
                    )

            return content

        except Exception as e:
            logger.error(
                "message_receive_failed",
                error=str(e),
                exc_info=True
            )
            MetricsRecorder.record_p2p_event("message_receive_failed", self.qube_id)
            return None

    async def send_text_message(
        self,
        recipient_qube_id: str,
        text: str,
        recipient_public_key: ec.EllipticCurvePublicKey,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Send text message to another Qube

        Args:
            recipient_qube_id: Target Qube ID
            text: Text message content
            recipient_public_key: Recipient's public key
            conversation_id: Optional conversation ID

        Returns:
            True if sent successfully
        """
        content = {
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return await self.send_message(
            recipient_qube_id=recipient_qube_id,
            content=content,
            recipient_public_key=recipient_public_key,
            message_type="text",
            conversation_id=conversation_id
        )

    async def send_task_request(
        self,
        recipient_qube_id: str,
        task_description: str,
        task_data: Dict[str, Any],
        recipient_public_key: ec.EllipticCurvePublicKey,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Send task request to another Qube

        Args:
            recipient_qube_id: Target Qube ID
            task_description: Task description
            task_data: Task parameters
            recipient_public_key: Recipient's public key
            conversation_id: Optional conversation ID

        Returns:
            True if sent successfully
        """
        content = {
            "description": task_description,
            "data": task_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return await self.send_message(
            recipient_qube_id=recipient_qube_id,
            content=content,
            recipient_public_key=recipient_public_key,
            message_type="task_request",
            conversation_id=conversation_id,
            requires_response=True
        )

    async def send_collaboration_invite(
        self,
        recipient_qube_id: str,
        collaboration_type: str,
        details: Dict[str, Any],
        recipient_public_key: ec.EllipticCurvePublicKey,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Send collaboration invite to another Qube

        Args:
            recipient_qube_id: Target Qube ID
            collaboration_type: Type of collaboration
            details: Collaboration details
            recipient_public_key: Recipient's public key
            conversation_id: Optional conversation ID

        Returns:
            True if sent successfully
        """
        content = {
            "collaboration_type": collaboration_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return await self.send_message(
            recipient_qube_id=recipient_qube_id,
            content=content,
            recipient_public_key=recipient_public_key,
            message_type="collaboration_invite",
            conversation_id=conversation_id,
            requires_response=True
        )

    def register_message_handler(
        self,
        message_type: str,
        handler: Callable[[QubeMessage, Dict[str, Any]], None]
    ) -> None:
        """
        Register handler for specific message type

        Args:
            message_type: Message type to handle
            handler: Async handler function
        """
        self.message_handlers[message_type] = handler
        logger.info("message_handler_registered", message_type=message_type)

    def get_conversation(self, conversation_id: str) -> List[QubeMessage]:
        """
        Get messages from conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages in conversation
        """
        return self.conversations.get(conversation_id, [])

    def get_all_conversations(self) -> Dict[str, List[QubeMessage]]:
        """Get all conversations"""
        return self.conversations

    async def close_session(self, qube_id: str) -> None:
        """
        Close session with Qube

        Args:
            qube_id: Target Qube ID
        """
        self.handshake.close_session(qube_id)
        logger.info("session_closed", qube_id=qube_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get messenger statistics"""
        return {
            "qube_id": self.qube_id,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "handshakes_completed": self.handshakes_completed,
            "active_sessions": len(self.handshake.active_sessions),
            "active_conversations": len(self.conversations),
            "total_messages": sum(len(msgs) for msgs in self.conversations.values())
        }


async def create_qube_messenger(
    qube,
    p2p_node: QubeP2PNode,
    nft_contract: Optional[str] = None,
    nft_token_id: Optional[int] = None
) -> QubeMessenger:
    """
    Create QubeMessenger instance for a Qube

    Args:
        qube: Qube instance
        p2p_node: P2P node instance
        nft_contract: Optional NFT contract address
        nft_token_id: Optional NFT token ID

    Returns:
        QubeMessenger instance
    """
    messenger = QubeMessenger(
        qube_id=qube.qube_id,
        private_key=qube.private_key,
        public_key=qube.public_key,
        p2p_node=p2p_node,
        nft_contract=nft_contract,
        nft_token_id=nft_token_id
    )

    logger.info("qube_messenger_created", qube_id=qube.qube_id)

    return messenger
