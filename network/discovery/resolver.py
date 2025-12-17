"""
Qube Resolver

Resolves Qube IDs to P2P addresses using multiple discovery mechanisms.
From docs/08_P2P_Network_Discovery.md Section 5.2
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from utils.logging import get_logger

logger = get_logger(__name__)


class QubeResolver:
    """
    Resolves Qube IDs to P2P addresses using multiple discovery methods

    Discovery Methods (in order of precedence):
    1. Local cache (fastest)
    2. DHT discovery (Kademlia)
    3. Blockchain registry (NFT metadata)
    4. GossipSub protocol (peer announcements)
    """

    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize Qube resolver

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

        logger.info("qube_resolver_initialized", cache_ttl_seconds=cache_ttl_seconds)

    def _get_from_cache(self, qube_id: str) -> Optional[str]:
        """
        Get multiaddr from cache if not expired

        Args:
            qube_id: Qube ID to look up

        Returns:
            Cached multiaddr or None
        """
        if qube_id not in self.cache:
            return None

        entry = self.cache[qube_id]
        cached_at = entry.get("cached_at")

        if not cached_at:
            return None

        # Check if cache entry is expired
        age = datetime.now(timezone.utc) - cached_at
        if age > self.cache_ttl:
            logger.debug("cache_entry_expired", qube_id=qube_id, age_seconds=age.total_seconds())
            del self.cache[qube_id]
            return None

        logger.debug("cache_hit", qube_id=qube_id)
        return entry.get("multiaddr")

    def _add_to_cache(self, qube_id: str, multiaddr: str, source: str) -> None:
        """
        Add multiaddr to cache

        Args:
            qube_id: Qube ID
            multiaddr: P2P multiaddr
            source: Discovery source (dht, blockchain, gossip)
        """
        self.cache[qube_id] = {
            "multiaddr": multiaddr,
            "cached_at": datetime.now(timezone.utc),
            "source": source
        }

        logger.debug("cache_entry_added", qube_id=qube_id, source=source)

    async def discover_qube(
        self,
        target_qube_id: str,
        p2p_node=None,
        nft_registry=None,
        gossip_protocol=None
    ) -> Optional[str]:
        """
        Discover target Qube's P2P address
        From docs Section 5.2

        Uses multiple discovery mechanisms in order:
        1. Local cache
        2. DHT (Kademlia)
        3. Blockchain registry (Phase 4)
        4. Gossip protocol

        Args:
            target_qube_id: Target Qube ID to find
            p2p_node: Optional QubeP2PNode instance for DHT discovery
            nft_registry: Optional QubeNFTRegistry for blockchain discovery
            gossip_protocol: Optional GossipProtocol for gossip discovery

        Returns:
            Multiaddr of target Qube, or None if not found
        """
        try:
            logger.debug("discovering_qube", target_qube_id=target_qube_id)

            # Method 1: Check local cache
            cached_multiaddr = self._get_from_cache(target_qube_id)
            if cached_multiaddr:
                logger.info(
                    "qube_discovered_via_cache",
                    target_qube_id=target_qube_id,
                    multiaddr=cached_multiaddr
                )
                return cached_multiaddr

            # Method 2: DHT discovery
            if p2p_node:
                multiaddr = await self._discover_via_dht(target_qube_id, p2p_node)
                if multiaddr:
                    self._add_to_cache(target_qube_id, multiaddr, "dht")
                    logger.info(
                        "qube_discovered_via_dht",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr
                    )
                    return multiaddr

            # Method 3: Blockchain registry discovery
            if nft_registry:
                multiaddr = await self._discover_via_blockchain(target_qube_id, nft_registry)
                if multiaddr:
                    self._add_to_cache(target_qube_id, multiaddr, "blockchain")
                    logger.info(
                        "qube_discovered_via_blockchain",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr
                    )
                    return multiaddr

            # Method 4: GossipSub discovery
            if gossip_protocol:
                multiaddr = await self._discover_via_gossip(target_qube_id, gossip_protocol)
                if multiaddr:
                    self._add_to_cache(target_qube_id, multiaddr, "gossip")
                    logger.info(
                        "qube_discovered_via_gossip",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr
                    )
                    return multiaddr

            logger.info("qube_not_found", target_qube_id=target_qube_id)
            logger.debug(
                "discovery_methods_used",
                dht=bool(p2p_node),
                blockchain_discovery=bool(nft_registry),
                gossip_discovery=bool(gossip_protocol)
            )
            return None

        except Exception as e:
            logger.error(
                "qube_discovery_failed",
                target_qube_id=target_qube_id,
                error=str(e)
            )
            return None

    async def _discover_via_dht(self, target_qube_id: str, p2p_node) -> Optional[str]:
        """
        Discover Qube via DHT (Kademlia)

        Args:
            target_qube_id: Target Qube ID
            p2p_node: QubeP2PNode instance

        Returns:
            Multiaddr or None
        """
        try:
            logger.debug("attempting_dht_discovery", target_qube_id=target_qube_id)

            # Use p2p_node's discover_qube method which calls libp2p_daemon_client
            multiaddr = await p2p_node.discover_qube(target_qube_id)

            if multiaddr:
                logger.debug("dht_discovery_successful", target_qube_id=target_qube_id)
                return multiaddr

            logger.debug("dht_discovery_no_result", target_qube_id=target_qube_id)
            return None

        except Exception as e:
            logger.warning("dht_discovery_error", target_qube_id=target_qube_id, error=str(e))
            return None

    async def _discover_via_blockchain(
        self,
        target_qube_id: str,
        nft_registry
    ) -> Optional[str]:
        """
        Discover Qube via blockchain NFT registry

        Queries the blockchain registry for Qube → MultiAddr mapping.
        The multiaddr can be stored in NFT metadata or an on-chain registry.

        Args:
            target_qube_id: Target Qube ID
            nft_registry: QubeNFTRegistry instance

        Returns:
            Multiaddr or None
        """
        try:
            logger.debug("attempting_blockchain_discovery", target_qube_id=target_qube_id)

            # Get NFT info from registry
            nft_info = nft_registry.get_nft_info(target_qube_id)

            if not nft_info:
                logger.debug("qube_not_registered_in_blockchain", target_qube_id=target_qube_id)
                return None

            # Check if multiaddr is stored in NFT metadata
            multiaddr = nft_info.get("multiaddr") or nft_info.get("p2p_address")

            if multiaddr:
                logger.debug("blockchain_discovery_successful", target_qube_id=target_qube_id)
                return multiaddr

            # Future enhancement: Query on-chain registry contract
            # For now, we only support metadata stored in local registry
            logger.debug(
                "no_multiaddr_in_nft_metadata",
                target_qube_id=target_qube_id,
                message="NFT exists but no multiaddr in metadata"
            )

            return None

        except Exception as e:
            logger.warning("blockchain_discovery_error", target_qube_id=target_qube_id, error=str(e))
            return None

    async def _discover_via_gossip(
        self,
        target_qube_id: str,
        gossip_protocol
    ) -> Optional[str]:
        """
        Discover Qube via GossipSub announcements

        Queries the gossip protocol's known_qubes cache for peer information.

        Args:
            target_qube_id: Target Qube ID
            gossip_protocol: GossipProtocol instance

        Returns:
            Multiaddr or None
        """
        try:
            logger.debug("attempting_gossip_discovery", target_qube_id=target_qube_id)

            # Query known_qubes cache from gossip announcements
            qube_info = gossip_protocol.get_known_qube(target_qube_id)

            if not qube_info:
                logger.debug("qube_not_in_gossip_cache", target_qube_id=target_qube_id)
                return None

            # Extract multiaddr from qube info
            multiaddr = qube_info.get("p2p_address")

            if multiaddr:
                logger.debug("gossip_discovery_successful", target_qube_id=target_qube_id)
                return multiaddr

            logger.debug("no_multiaddr_in_gossip_info", target_qube_id=target_qube_id)
            return None

        except Exception as e:
            logger.warning("gossip_discovery_error", target_qube_id=target_qube_id, error=str(e))
            return None

    def clear_cache(self) -> None:
        """Clear all cached entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info("cache_cleared", entries_removed=count)

    def remove_from_cache(self, qube_id: str) -> bool:
        """
        Remove specific Qube from cache

        Args:
            qube_id: Qube ID to remove

        Returns:
            True if removed, False if not in cache
        """
        if qube_id in self.cache:
            del self.cache[qube_id]
            logger.debug("cache_entry_removed", qube_id=qube_id)
            return True
        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now(timezone.utc)
        sources = {}

        for qube_id, entry in self.cache.items():
            source = entry.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        return {
            "total_entries": len(self.cache),
            "by_source": sources,
            "cache_ttl_seconds": self.cache_ttl.total_seconds()
        }


# Legacy function for backward compatibility
async def discover_qube(target_qube_id: str, p2p_node=None) -> Optional[str]:
    """
    Discover target Qube's P2P address (legacy function)

    Args:
        target_qube_id: Target Qube ID to find
        p2p_node: Optional QubeP2PNode instance for discovery

    Returns:
        Multiaddr of target Qube, or None if not found
    """
    resolver = QubeResolver()
    return await resolver.discover_qube(target_qube_id, p2p_node=p2p_node)
