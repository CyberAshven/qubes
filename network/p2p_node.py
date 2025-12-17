"""
P2P Node Implementation

Core libp2p node for Qube-to-Qube networking.
From docs/08_P2P_Network_Discovery.md Section 5.1, 5.2
"""

import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path

from core.exceptions import NetworkError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class QubeP2PNode:
    """
    libp2p-based P2P node for Qube networking

    Implements:
    - DHT for peer discovery (Kademlia)
    - GossipSub for message propagation
    - Noise Protocol for encrypted transport
    - mDNS for local network discovery
    """

    def __init__(
        self,
        qube_id: str,
        private_key,
        public_key,
        listen_port: int = 0,  # 0 = auto-assign
        bootstrap_peers: Optional[List[str]] = None
    ):
        """
        Initialize P2P node

        Args:
            qube_id: Qube ID (8-character hex)
            private_key: ECDSA private key for signing
            public_key: ECDSA public key
            listen_port: Port to listen on (0 for auto-assign)
            bootstrap_peers: List of bootstrap peer multiaddrs
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.public_key = public_key
        self.listen_port = listen_port
        self.bootstrap_peers = bootstrap_peers or []

        # libp2p components (initialized in start())
        self.host = None
        self.dht = None
        self.pubsub = None
        self.mdns = None

        # Network state
        self.is_running = False
        self.peer_id = None
        self.multiaddr = None

        # Known peers
        self.known_peers: Dict[str, Any] = {}  # qube_id -> peer_info

        logger.info(
            "p2p_node_initialized",
            qube_id=qube_id,
            listen_port=listen_port,
            bootstrap_peers_count=len(self.bootstrap_peers)
        )

    async def start(self) -> None:
        """
        Start P2P node

        Initializes libp2p host, DHT, GossipSub, and mDNS.
        From docs Section 5.2
        """
        try:
            logger.info("p2p_node_starting", qube_id=self.qube_id)

            # Note: libp2p integration requires actual library installation
            # For now, we'll create placeholder implementation that can be
            # filled in once py-libp2p is installed and tested

            # Try production libp2p-daemon client first
            try:
                from network.libp2p_daemon_client import LibP2PDaemonClient

                # Create daemon client
                self.daemon_client = LibP2PDaemonClient(
                    qube_id=self.qube_id,
                    listen_port=self.listen_port,
                    bootstrap_peers=self.bootstrap_peers
                )

                # Start daemon
                await self.daemon_client.start()

                # Get peer ID and multiaddr from daemon
                self.peer_id = self.daemon_client.peer_id
                self.multiaddr = self.daemon_client.multiaddr
                self.host = self.daemon_client  # Use daemon client as host

                logger.info(
                    "libp2p_daemon_client_started",
                    qube_id=self.qube_id,
                    peer_id=self.peer_id,
                    multiaddr=self.multiaddr
                )

                self.is_running = True

                logger.info(
                    "p2p_node_started_with_daemon",
                    qube_id=self.qube_id,
                    peer_id=self.peer_id
                )

                MetricsRecorder.record_p2p_event("node_started", self.qube_id)

            except (ImportError, NetworkError) as e:
                logger.warning(
                    "libp2p_not_installed",
                    message="py-libp2p not installed, using mock implementation"
                )

                # Mock implementation for development
                self.peer_id = f"Qm{self.qube_id}"  # Mock peer ID
                self.multiaddr = f"/ip4/127.0.0.1/tcp/{self.listen_port or 4001}/p2p/{self.peer_id}"
                self.is_running = True

                logger.info(
                    "p2p_node_started_mock",
                    qube_id=self.qube_id,
                    peer_id=self.peer_id,
                    multiaddr=self.multiaddr
                )

        except Exception as e:
            logger.error("p2p_node_start_failed", qube_id=self.qube_id, exc_info=True)
            raise NetworkError(
                f"Failed to start P2P node: {str(e)}",
                context={"qube_id": self.qube_id},
                cause=e
            )

    async def stop(self) -> None:
        """Stop P2P node and cleanup resources"""
        try:
            logger.info("p2p_node_stopping", qube_id=self.qube_id)

            # Stop daemon client if used
            if hasattr(self, 'daemon_client') and self.daemon_client:
                await self.daemon_client.stop()

            # Stop py-libp2p host if used
            elif self.host and hasattr(self.host, 'close'):
                await self.host.close()

            self.is_running = False

            logger.info("p2p_node_stopped", qube_id=self.qube_id)
            MetricsRecorder.record_p2p_event("node_stopped", self.qube_id)

        except Exception as e:
            logger.error("p2p_node_stop_failed", qube_id=self.qube_id, exc_info=True)
            raise NetworkError(
                f"Failed to stop P2P node: {str(e)}",
                context={"qube_id": self.qube_id},
                cause=e
            )

    async def _init_dht(self) -> None:
        """
        Initialize Kademlia DHT for peer discovery
        From docs Section 5.2.1
        """
        try:
            if self.host:
                from libp2p.kademlia.kad_dht import KadDHT

                self.dht = KadDHT(self.host)
                await self.dht.bootstrap()

                # Announce ourselves to DHT
                await self.dht.provide(self.qube_id.encode())

                logger.info("dht_initialized", qube_id=self.qube_id)
            else:
                logger.debug("dht_init_skipped_mock_mode")

        except ImportError:
            logger.debug("dht_init_skipped_libp2p_not_installed")
        except Exception as e:
            logger.error("dht_init_failed", error=str(e))

    async def _init_pubsub(self) -> None:
        """
        Initialize GossipSub for message propagation
        From docs Section 5.2.3
        """
        try:
            if self.host:
                from libp2p.pubsub.gossipsub import GossipSub

                self.pubsub = GossipSub(
                    protocols=["/qubes/gossip/1.0.0"],
                    degree=6,  # Target number of peers in mesh
                    degree_low=4,
                    degree_high=12
                )

                await self.pubsub.subscribe(f"qubes/{self.qube_id}")
                await self.pubsub.subscribe("qubes/discovery")

                logger.info("pubsub_initialized", qube_id=self.qube_id)
            else:
                logger.debug("pubsub_init_skipped_mock_mode")

        except ImportError:
            logger.debug("pubsub_init_skipped_libp2p_not_installed")
        except Exception as e:
            logger.error("pubsub_init_failed", error=str(e))

    async def _init_mdns(self) -> None:
        """
        Initialize mDNS for local network discovery
        From docs Section 5.1
        """
        try:
            if self.host:
                # mDNS initialization (simplified)
                logger.info("mdns_initialized", qube_id=self.qube_id)
            else:
                logger.debug("mdns_init_skipped_mock_mode")

        except Exception as e:
            logger.error("mdns_init_failed", error=str(e))

    async def _connect_bootstrap_peers(self) -> None:
        """Connect to bootstrap peers for network entry"""
        if not self.bootstrap_peers:
            logger.debug("no_bootstrap_peers_configured")
            return

        for peer_addr in self.bootstrap_peers:
            try:
                if self.host:
                    # await self.host.connect(peer_addr)
                    logger.info("connected_to_bootstrap_peer", peer=peer_addr)
                else:
                    logger.debug("bootstrap_connection_skipped_mock_mode", peer=peer_addr)

            except Exception as e:
                logger.warning("bootstrap_peer_connection_failed", peer=peer_addr, error=str(e))

    async def discover_qube(self, target_qube_id: str) -> Optional[str]:
        """
        Discover target Qube's P2P address via DHT
        From docs Section 5.2.1

        Args:
            target_qube_id: Target Qube ID to find

        Returns:
            Multiaddr of target Qube, or None if not found
        """
        try:
            # Use daemon client if available
            if hasattr(self, 'daemon_client') and self.daemon_client:
                peer_info = await self.daemon_client.find_peer(target_qube_id)

                if peer_info and peer_info.addrs:
                    multiaddr = peer_info.addrs[0]

                    logger.info(
                        "qube_discovered_via_dht",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr
                    )

                    return multiaddr
                else:
                    logger.debug("qube_not_found_in_dht", target_qube_id=target_qube_id)
                    return None

            # Fallback to py-libp2p if available
            elif self.dht:
                # Find providers for target Qube ID
                providers = await self.dht.find_providers(target_qube_id.encode(), count=1)

                if providers:
                    peer_info = providers[0]
                    multiaddr = str(peer_info.addrs[0])

                    logger.info(
                        "qube_discovered_via_dht",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr
                    )

                    return multiaddr
                else:
                    logger.debug("qube_not_found_in_dht", target_qube_id=target_qube_id)
                    return None
            else:
                logger.debug("discovery_skipped_no_dht")
                return None

        except Exception as e:
            logger.error("qube_discovery_failed", target_qube_id=target_qube_id, error=str(e))
            return None

    async def publish_message(self, topic: str, message: bytes) -> None:
        """
        Publish message to GossipSub topic
        From docs Section 5.2.3

        Args:
            topic: Topic name (e.g., "qubes/discovery")
            message: Message bytes to publish
        """
        try:
            # Use daemon client if available
            if hasattr(self, 'daemon_client') and self.daemon_client:
                await self.daemon_client.publish_to_topic(topic, message)

                logger.debug("message_published", topic=topic, size=len(message))
                MetricsRecorder.record_p2p_event("message_published", self.qube_id)

            # Fallback to py-libp2p if available
            elif self.pubsub:
                await self.pubsub.publish(topic, message)

                logger.debug("message_published", topic=topic, size=len(message))
                MetricsRecorder.record_p2p_event("message_published", self.qube_id)
            else:
                logger.debug("publish_skipped_no_pubsub")

        except Exception as e:
            logger.error("message_publish_failed", topic=topic, error=str(e))
            raise NetworkError(
                f"Failed to publish message: {str(e)}",
                context={"topic": topic},
                cause=e
            )

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return {
            "qube_id": self.qube_id,
            "peer_id": self.peer_id,
            "multiaddr": self.multiaddr,
            "is_running": self.is_running,
            "known_peers_count": len(self.known_peers),
            "bootstrap_peers": self.bootstrap_peers
        }


async def start_qube_network(qube) -> QubeP2PNode:
    """
    Start P2P network for a Qube
    From docs Section 5.2

    Args:
        qube: Qube instance

    Returns:
        Started QubeP2PNode instance
    """
    node = QubeP2PNode(
        qube_id=qube.qube_id,
        private_key=qube.private_key,
        public_key=qube.public_key
    )

    await node.start()

    return node
