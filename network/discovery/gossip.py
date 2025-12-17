"""
Gossip Protocol for Qube Discovery

Implements GossipSub-based peer discovery and network announcements.
From docs/08_P2P_Network_Discovery.md Section 5.2.3
"""

import json
import asyncio
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from core.exceptions import NetworkError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class GossipProtocol:
    """
    GossipSub protocol for Qube discovery and announcements

    Provides:
    - Qube discovery announcements
    - Network-wide message propagation
    - Subscribe to discovery topics
    - Publish known Qubes to network
    """

    def __init__(
        self,
        qube_id: str,
        private_key: ec.EllipticCurvePrivateKey,
        p2p_node
    ):
        """
        Initialize gossip protocol

        Args:
            qube_id: This Qube's ID
            private_key: ECDSA private key for signing
            p2p_node: QubeP2PNode instance
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.p2p_node = p2p_node
        self.pubsub = p2p_node.pubsub if p2p_node else None

        # Known Qubes from gossip
        self.known_qubes: Dict[str, Dict[str, Any]] = {}

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

        # Topics
        self.discovery_topic = "qubes/discovery"
        self.announcement_topic = "qubes/announcement"

        logger.info("gossip_protocol_initialized", qube_id=qube_id)

    async def start(self) -> None:
        """
        Start gossip protocol

        Subscribes to discovery topics and begins listening for announcements.
        """
        try:
            if not self.pubsub:
                logger.warning("gossip_start_skipped_no_pubsub")
                return

            # Subscribe to discovery topic
            await self._subscribe_to_topic(self.discovery_topic)

            # Subscribe to announcement topic
            await self._subscribe_to_topic(self.announcement_topic)

            # Announce ourselves to the network
            await self.announce_presence()

            logger.info("gossip_protocol_started", qube_id=self.qube_id)

        except Exception as e:
            logger.error("gossip_start_failed", error=str(e))
            raise NetworkError(f"Failed to start gossip protocol: {str(e)}", cause=e)

    async def announce_presence(self) -> None:
        """
        Announce this Qube's presence to the network
        From docs Section 5.2.3
        """
        try:
            announcement = {
                "type": "QUBE_ANNOUNCEMENT",
                "qube_id": self.qube_id,
                "p2p_address": self.p2p_node.multiaddr if self.p2p_node else None,
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "capabilities": self._get_capabilities()
            }

            # Sign announcement
            announcement["signature"] = self._sign_message(announcement)

            # Publish to network
            await self._publish_message(self.announcement_topic, announcement)

            logger.info("presence_announced", qube_id=self.qube_id)
            MetricsRecorder.record_p2p_event("presence_announced", self.qube_id)

        except Exception as e:
            logger.error("presence_announcement_failed", error=str(e))

    async def gossip_known_qubes(self) -> None:
        """
        Gossip about known Qubes to the network
        From docs Section 5.2.3

        Shares knowledge of other Qubes to help with discovery.
        """
        try:
            if not self.known_qubes:
                logger.debug("no_qubes_to_gossip")
                return

            # Create gossip message with known Qubes
            known_qubes_list = [
                {
                    "qube_id": qube_id,
                    "p2p_address": info.get("p2p_address"),
                    "last_seen": info.get("timestamp")
                }
                for qube_id, info in list(self.known_qubes.items())[:20]  # Limit to 20
            ]

            gossip_message = {
                "type": "QUBE_DISCOVERY",
                "from_qube": self.qube_id,
                "known_qubes": known_qubes_list,
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }

            # Sign gossip message
            gossip_message["signature"] = self._sign_message(gossip_message)

            # Publish to discovery topic
            await self._publish_message(self.discovery_topic, gossip_message)

            logger.info(
                "qubes_gossiped",
                qube_id=self.qube_id,
                known_qubes_count=len(known_qubes_list)
            )

            MetricsRecorder.record_p2p_event("qubes_gossiped", self.qube_id)

        except Exception as e:
            logger.error("gossip_failed", error=str(e))

    async def handle_discovery_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming discovery message

        Args:
            message: Discovery message data
        """
        try:
            message_type = message.get("type")

            if message_type == "QUBE_DISCOVERY":
                await self._handle_qube_discovery(message)
            elif message_type == "QUBE_ANNOUNCEMENT":
                await self._handle_qube_announcement(message)
            else:
                logger.debug("unknown_message_type", message_type=message_type)

        except Exception as e:
            logger.error("discovery_message_handling_failed", error=str(e))

    async def _handle_qube_discovery(self, message: Dict[str, Any]) -> None:
        """Handle QUBE_DISCOVERY message"""
        try:
            from_qube = message.get("from_qube")
            known_qubes = message.get("known_qubes", [])

            logger.debug(
                "received_qube_discovery",
                from_qube=from_qube,
                known_qubes_count=len(known_qubes)
            )

            # Store known Qubes
            for qube_info in known_qubes:
                qube_id = qube_info.get("qube_id")
                if qube_id and qube_id != self.qube_id:
                    self.known_qubes[qube_id] = {
                        "p2p_address": qube_info.get("p2p_address"),
                        "timestamp": qube_info.get("last_seen"),
                        "discovered_via": from_qube
                    }

            logger.info(
                "known_qubes_updated",
                total_known=len(self.known_qubes)
            )

        except Exception as e:
            logger.error("qube_discovery_handling_failed", error=str(e))

    async def _handle_qube_announcement(self, message: Dict[str, Any]) -> None:
        """Handle QUBE_ANNOUNCEMENT message"""
        try:
            qube_id = message.get("qube_id")
            p2p_address = message.get("p2p_address")

            if not qube_id or qube_id == self.qube_id:
                return

            logger.debug("received_qube_announcement", qube_id=qube_id)

            # Store announced Qube
            self.known_qubes[qube_id] = {
                "p2p_address": p2p_address,
                "timestamp": message.get("timestamp"),
                "capabilities": message.get("capabilities", []),
                "discovered_via": "announcement"
            }

            logger.info(
                "qube_announced",
                qube_id=qube_id,
                p2p_address=p2p_address
            )

        except Exception as e:
            logger.error("announcement_handling_failed", error=str(e))

    async def _subscribe_to_topic(self, topic: str) -> None:
        """
        Subscribe to GossipSub topic

        Args:
            topic: Topic name to subscribe to
        """
        try:
            if not self.pubsub:
                logger.debug("subscribe_skipped_no_pubsub", topic=topic)
                return

            # Subscribe to topic
            # (Simplified - actual implementation depends on libp2p API)
            await self.pubsub.subscribe(topic)

            logger.info("subscribed_to_topic", topic=topic)

        except Exception as e:
            logger.error("topic_subscription_failed", topic=topic, error=str(e))

    async def _publish_message(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish message to GossipSub topic

        Args:
            topic: Topic name
            message: Message to publish
        """
        try:
            if not self.pubsub:
                logger.debug(
                    "publish_skipped_no_pubsub",
                    topic=topic,
                    message_type=message.get("type")
                )
                return

            # Serialize message
            message_bytes = json.dumps(message).encode()

            # Publish to topic
            await self.p2p_node.publish_message(topic, message_bytes)

            logger.debug(
                "message_published",
                topic=topic,
                message_type=message.get("type")
            )

        except Exception as e:
            logger.error("message_publish_failed", topic=topic, error=str(e))

    def _sign_message(self, message: Dict[str, Any]) -> str:
        """
        Sign message with private key

        Args:
            message: Message to sign (without signature field)

        Returns:
            Base64-encoded signature
        """
        try:
            import base64

            # Remove signature field if present
            message_copy = {k: v for k, v in message.items() if k != "signature"}

            # Serialize and sign
            message_data = json.dumps(message_copy, sort_keys=True).encode()
            signature = self.private_key.sign(
                message_data,
                ec.ECDSA(hashes.SHA256())
            )

            return base64.b64encode(signature).decode()

        except Exception as e:
            logger.error("message_signing_failed", error=str(e))
            return ""

    def _get_capabilities(self) -> List[str]:
        """
        Get this Qube's capabilities

        Returns:
            List of capability strings
        """
        return [
            "messaging",
            "task_execution",
            "collaboration"
        ]

    def get_known_qube(self, qube_id: str) -> Optional[Dict[str, Any]]:
        """
        Get known Qube information

        Args:
            qube_id: Qube ID to look up

        Returns:
            Qube information or None
        """
        return self.known_qubes.get(qube_id)

    def get_all_known_qubes(self) -> Dict[str, Dict[str, Any]]:
        """Get all known Qubes"""
        return self.known_qubes

    def register_message_handler(
        self,
        message_type: str,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register handler for specific message type

        Args:
            message_type: Message type to handle
            handler: Async handler function
        """
        self.message_handlers[message_type] = handler
        logger.info("gossip_handler_registered", message_type=message_type)

    def get_stats(self) -> Dict[str, Any]:
        """Get gossip protocol statistics"""
        return {
            "qube_id": self.qube_id,
            "known_qubes": len(self.known_qubes),
            "subscribed_topics": [self.discovery_topic, self.announcement_topic]
        }


async def gossip_known_qubes(qube_id: str, network, known_qubes: List[Dict[str, Any]]) -> None:
    """
    Utility function to gossip known Qubes
    From docs Section 5.2.3

    Args:
        qube_id: This Qube's ID
        network: Network/GossipProtocol instance
        known_qubes: List of known Qube information
    """
    try:
        message = {
            "type": "QUBE_DISCOVERY",
            "from_qube": qube_id,
            "known_qubes": known_qubes,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }

        await network.gossip.publish("qubes/discovery", json.dumps(message).encode())

        logger.info("qubes_gossiped_utility", qube_id=qube_id, count=len(known_qubes))

    except Exception as e:
        logger.error("gossip_utility_failed", error=str(e))
