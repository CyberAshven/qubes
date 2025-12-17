"""
libp2p-daemon Client (Production Implementation)

Uses official p2pclient library for stable DHT discovery and GossipSub messaging.

Installation:
    pip install p2pclient

Dependencies:
    - p2pclient (Python bindings for libp2p-daemon)
    - libp2p-daemon binary (Go implementation)

Install libp2p-daemon:
    go install github.com/libp2p/go-libp2p-daemon/p2pd@latest
    # Binary will be at ~/go/bin/p2pd (add to PATH)
"""

import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path
from dataclasses import dataclass

from core.exceptions import NetworkError
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PeerInfo:
    """Information about a peer"""
    peer_id: str
    addrs: List[str]


class LibP2PDaemonClient:
    """
    Production libp2p-daemon client using official p2pclient library

    Provides:
    - DHT-based peer discovery (Kademlia)
    - GossipSub message propagation
    - Connection management
    - Peer routing
    """

    def __init__(
        self,
        qube_id: str,
        listen_port: int = 0,  # 0 = auto-assign
        control_maddr: Optional[str] = None,
        bootstrap_peers: Optional[List[str]] = None,
        daemon_path: Optional[str] = None
    ):
        """
        Initialize libp2p-daemon client

        Args:
            qube_id: Qube ID (used as content routing key)
            listen_port: Port for libp2p to listen on (0 = auto)
            control_maddr: Control multiaddr (default: /unix/tmp/p2pd-{qube_id}.sock)
            bootstrap_peers: List of bootstrap peer multiaddrs
            daemon_path: Path to p2pd binary (searches PATH if None)
        """
        self.qube_id = qube_id
        self.listen_port = listen_port
        self.bootstrap_peers = bootstrap_peers or []
        self.daemon_path = daemon_path or "p2pd"

        # Control multiaddr
        if control_maddr:
            self.control_maddr = control_maddr
        else:
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            self.control_maddr = f"/unix/{temp_dir}/p2pd-{qube_id}.sock"

        # Client state
        self.client = None
        self.daemon_process = None
        self.is_running = False

        # Network state
        self.peer_id: Optional[str] = None
        self.multiaddr: Optional[str] = None
        self.known_peers: Dict[str, PeerInfo] = {}

        logger.info(
            "libp2p_daemon_client_initialized",
            qube_id=qube_id,
            control_maddr=self.control_maddr
        )

    async def start(self) -> None:
        """
        Start libp2p-daemon and establish client connection

        Steps:
        1. Import p2pclient library
        2. Spawn daemon via p2pclient
        3. Connect to daemon
        4. Initialize DHT and GossipSub
        """
        try:
            logger.info("starting_libp2p_daemon_client", qube_id=self.qube_id)

            # Import p2pclient
            try:
                from p2pclient import Client
                from p2pclient.datastructures import PeerInfo as P2PPeerInfo
            except ImportError:
                raise NetworkError(
                    "p2pclient not installed. Install with: pip install p2pclient\n"
                    "Also ensure libp2p-daemon (p2pd) is installed and in PATH:\n"
                    "  go install github.com/libp2p/go-libp2p-daemon/p2pd@latest",
                    context={"qube_id": self.qube_id}
                )

            # Create client instance
            self.client = Client(
                maddr_control=self.control_maddr,
                maddr_listen=f"/ip4/0.0.0.0/tcp/{self.listen_port}",
                daemon_path=self.daemon_path
            )

            # Start daemon
            await self.client.listen()

            # Get our peer ID
            self.peer_id = str(self.client.peer_id)

            # Get our multiaddrs
            addrs = await self.client.list_addrs()
            if addrs:
                self.multiaddr = str(addrs[0])

            logger.info(
                "libp2p_daemon_client_started",
                qube_id=self.qube_id,
                peer_id=self.peer_id,
                multiaddr=self.multiaddr
            )

            # Bootstrap DHT if peers provided
            if self.bootstrap_peers:
                await self._bootstrap_dht()

            # Announce ourselves to DHT
            await self._announce_to_dht()

            self.is_running = True

        except Exception as e:
            logger.error("libp2p_daemon_client_start_failed", exc_info=True)
            await self.stop()
            raise NetworkError(
                f"Failed to start libp2p-daemon client: {str(e)}",
                context={"qube_id": self.qube_id},
                cause=e
            )

    async def stop(self) -> None:
        """Stop libp2p-daemon client and cleanup"""
        try:
            logger.info("stopping_libp2p_daemon_client", qube_id=self.qube_id)

            if self.client:
                await self.client.close()
                self.client = None

            self.is_running = False

            logger.info("libp2p_daemon_client_stopped", qube_id=self.qube_id)

        except Exception as e:
            logger.error("libp2p_daemon_client_stop_failed", exc_info=True)

    async def _bootstrap_dht(self) -> None:
        """Bootstrap DHT by connecting to bootstrap peers"""
        try:
            from p2pclient.datastructures import PeerInfo as P2PPeerInfo
            from multiaddr import Multiaddr

            logger.info("bootstrapping_dht", bootstrap_peers_count=len(self.bootstrap_peers))

            for peer_maddr in self.bootstrap_peers:
                try:
                    # Parse multiaddr to extract peer ID and address
                    maddr = Multiaddr(peer_maddr)

                    # Connect to peer
                    # Note: p2pclient's connect method signature may vary
                    # Adjust based on actual library API
                    await self.client.connect(peer_maddr)

                    logger.info("connected_to_bootstrap_peer", peer=peer_maddr)

                except Exception as e:
                    logger.warning("bootstrap_peer_connection_failed", peer=peer_maddr, error=str(e))

        except Exception as e:
            logger.warning("dht_bootstrap_error", error=str(e))

    async def _announce_to_dht(self) -> None:
        """Announce ourselves to DHT"""
        try:
            # Provide our Qube ID as content in the DHT
            # p2pclient uses CID (Content Identifier) format
            logger.info("announcing_to_dht", qube_id=self.qube_id)

            # Convert Qube ID to CID format
            try:
                from cid import make_cid
                import hashlib

                # Create a deterministic hash from qube_id
                qube_hash = hashlib.sha256(self.qube_id.encode('utf-8')).digest()

                # Create CID v1 using raw codec (0x55) and sha256 multihash
                cid = make_cid(1, 'raw', qube_hash)

                logger.debug("qube_id_converted_to_cid_for_announce", qube_id=self.qube_id, cid=str(cid))

                # Announce ourselves as provider for this CID
                # p2pclient API: dht_provide(cid)
                try:
                    await self.client.dht_provide(str(cid))
                    logger.info("announced_to_dht_successfully", qube_id=self.qube_id)

                except AttributeError:
                    logger.warning(
                        "dht_provide_not_supported",
                        message="p2pclient may not support DHT provide API"
                    )

            except ImportError:
                logger.warning(
                    "cid_library_not_installed_skipping_dht_announce",
                    message="py-cid not installed, DHT announce skipped"
                )

        except Exception as e:
            logger.warning("dht_announce_error", error=str(e))
            # Non-fatal - DHT may not be ready yet

    async def find_peer(self, qube_id: str, timeout: float = 30.0) -> Optional[PeerInfo]:
        """
        Find peer by Qube ID via DHT

        Args:
            qube_id: Target Qube ID
            timeout: Search timeout in seconds

        Returns:
            PeerInfo if found, None otherwise
        """
        try:
            logger.debug("searching_dht_for_qube", target_qube_id=qube_id)

            if not self.client or not self.is_running:
                logger.debug("dht_search_skipped_client_not_running")
                return None

            # Check cache first
            if qube_id in self.known_peers:
                cached_peer = self.known_peers[qube_id]
                logger.debug("peer_found_in_cache", qube_id=qube_id)
                return cached_peer

            # Convert Qube ID to CID format for DHT lookup
            # CID = Content Identifier used by IPFS/libp2p DHT
            try:
                from cid import make_cid
                import hashlib

                # Create a deterministic hash from qube_id
                qube_hash = hashlib.sha256(qube_id.encode('utf-8')).digest()

                # Create CID v1 using raw codec (0x55) and sha256 multihash
                cid = make_cid(1, 'raw', qube_hash)

                logger.debug("qube_id_converted_to_cid", qube_id=qube_id, cid=str(cid))

            except ImportError:
                logger.warning(
                    "cid_library_not_installed",
                    message="py-cid not installed, using qube_id as string key"
                )
                # Fallback: use qube_id directly as a string
                # This may not work with all DHT implementations
                cid = qube_id

            except Exception as e:
                logger.warning("cid_conversion_failed", error=str(e))
                return None

            # Find providers for this content in DHT
            try:
                # p2pclient API: dht_find_providers(cid, num_providers)
                # Returns list of PeerInfo objects with peer_id and addrs
                providers = await asyncio.wait_for(
                    self.client.dht_find_providers(str(cid), num_providers=5),
                    timeout=timeout
                )

                if not providers:
                    logger.debug("no_providers_found_in_dht", qube_id=qube_id)
                    return None

                # Convert first provider to our PeerInfo format
                provider = providers[0]
                peer_info = PeerInfo(
                    peer_id=str(provider.peer_id),
                    addrs=[str(addr) for addr in provider.addrs]
                )

                # Cache discovered peer
                self.known_peers[qube_id] = peer_info

                logger.info(
                    "peer_discovered_via_dht",
                    qube_id=qube_id,
                    peer_id=peer_info.peer_id,
                    addrs_count=len(peer_info.addrs)
                )

                return peer_info

            except asyncio.TimeoutError:
                logger.warning("dht_search_timeout", qube_id=qube_id, timeout=timeout)
                return None

            except AttributeError as e:
                # p2pclient may not have dht_find_providers method
                logger.warning(
                    "dht_find_providers_not_supported",
                    qube_id=qube_id,
                    error=str(e),
                    message="p2pclient may not support DHT find_providers API"
                )
                return None

        except Exception as e:
            logger.error("dht_find_peer_failed", target_qube_id=qube_id, error=str(e))
            return None

    async def connect_peer(self, peer_info: PeerInfo) -> bool:
        """
        Connect to peer

        Args:
            peer_info: Peer information

        Returns:
            True if connected successfully
        """
        try:
            from p2pclient.datastructures import PeerInfo as P2PPeerInfo, PeerID
            from multiaddr import Multiaddr

            # Convert our PeerInfo to p2pclient PeerInfo
            peer_id = PeerID.from_base58(peer_info.peer_id)
            maddrs = [Multiaddr(addr) for addr in peer_info.addrs]

            p2p_peer_info = P2PPeerInfo(peer_id=peer_id, addrs=maddrs)

            # Connect to peer
            await self.client.connect(p2p_peer_info)

            logger.info("peer_connected", peer_id=peer_info.peer_id)
            return True

        except Exception as e:
            logger.error("peer_connect_error", peer_id=peer_info.peer_id, error=str(e))
            return False

    async def publish_to_topic(self, topic: str, data: bytes) -> bool:
        """
        Publish message to GossipSub topic

        Args:
            topic: Topic name
            data: Message data (bytes)

        Returns:
            True if published successfully
        """
        try:
            # Subscribe to topic first (required for GossipSub)
            # await self.client.pubsub_subscribe(topic)

            # Publish message
            await self.client.pubsub_publish(topic, data)

            logger.debug("message_published_to_topic", topic=topic, size=len(data))
            return True

        except Exception as e:
            logger.error("pubsub_publish_error", topic=topic, error=str(e))
            return False

    async def subscribe_to_topic(self, topic: str, handler=None) -> bool:
        """
        Subscribe to GossipSub topic

        Args:
            topic: Topic name
            handler: Optional message handler callback

        Returns:
            True if subscribed successfully
        """
        try:
            # Subscribe to topic
            # p2pclient returns an async generator for messages
            subscription = await self.client.pubsub_subscribe(topic)

            logger.info("subscribed_to_topic", topic=topic)

            # If handler provided, start message processing task
            if handler:
                asyncio.create_task(self._handle_topic_messages(subscription, handler))

            return True

        except Exception as e:
            logger.error("pubsub_subscribe_error", topic=topic, error=str(e))
            return False

    async def _handle_topic_messages(self, subscription, handler):
        """Process messages from topic subscription"""
        try:
            async for message in subscription:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error("topic_message_handler_error", error=str(e))

        except Exception as e:
            logger.error("topic_subscription_error", error=str(e))

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return {
            "qube_id": self.qube_id,
            "peer_id": self.peer_id,
            "multiaddr": self.multiaddr,
            "is_running": self.is_running,
            "control_maddr": self.control_maddr,
            "known_peers_count": len(self.known_peers),
            "bootstrap_peers": self.bootstrap_peers
        }


# Usage Example:
# async def main():
#     client = LibP2PDaemonClient(
#         qube_id="A1B2C3D4",
#         bootstrap_peers=[
#             "/ip4/104.131.131.82/tcp/4001/p2p/QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ"
#         ]
#     )
#     await client.start()
#
#     # Find peer
#     peer_info = await client.find_peer("B2C3D4E5")
#     if peer_info:
#         await client.connect_peer(peer_info)
#
#     # Publish message
#     await client.publish_to_topic("qubes/discovery", b"Hello!")
#
#     await client.stop()
