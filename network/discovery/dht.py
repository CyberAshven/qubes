"""
DHT-Based Discovery

Implements Kademlia DHT for peer discovery.
From docs/08_P2P_Network_Discovery.md Section 5.2.1
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.exceptions import NetworkError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class DHTDiscovery:
    """
    Kademlia DHT for Qube discovery

    Provides:
    - Announce self to DHT
    - Find other Qubes by ID
    - Maintain routing table
    """

    def __init__(self, p2p_node):
        """
        Initialize DHT discovery

        Args:
            p2p_node: QubeP2PNode instance
        """
        self.p2p_node = p2p_node
        self.dht = p2p_node.dht
        self.qube_id = p2p_node.qube_id

        # Discovery cache
        self.discovery_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("dht_discovery_initialized", qube_id=self.qube_id)

    async def announce(self) -> None:
        """
        Announce this Qube to the DHT
        From docs Section 5.2.1

        Makes this Qube discoverable by other peers.
        """
        try:
            if not self.dht:
                logger.debug("announce_skipped_no_dht")
                return

            # Provide our Qube ID to the DHT
            await self.dht.provide(self.qube_id.encode())

            logger.info("qube_announced_to_dht", qube_id=self.qube_id)
            MetricsRecorder.record_p2p_event("dht_announce", self.qube_id)

        except Exception as e:
            logger.error("dht_announce_failed", qube_id=self.qube_id, error=str(e))
            raise NetworkError(
                f"Failed to announce to DHT: {str(e)}",
                context={"qube_id": self.qube_id},
                cause=e
            )

    async def find_qube(self, target_qube_id: str) -> Optional[str]:
        """
        Find a Qube by ID using DHT
        From docs Section 5.2.1

        Args:
            target_qube_id: Qube ID to find

        Returns:
            Multiaddr of target Qube, or None if not found
        """
        try:
            # Check cache first
            cached = self._get_from_cache(target_qube_id)
            if cached:
                logger.debug("qube_found_in_cache", target_qube_id=target_qube_id)
                return cached["multiaddr"]

            if not self.dht:
                logger.debug("find_qube_skipped_no_dht")
                return None

            # Query DHT for providers
            logger.debug("querying_dht_for_qube", target_qube_id=target_qube_id)

            providers = await self.dht.find_providers(
                target_qube_id.encode(),
                count=5  # Get up to 5 providers
            )

            if providers:
                # Take first provider
                peer_info = providers[0]
                multiaddr = str(peer_info.addrs[0]) if peer_info.addrs else None

                if multiaddr:
                    # Cache result
                    self._add_to_cache(target_qube_id, {
                        "multiaddr": multiaddr,
                        "peer_info": peer_info,
                        "discovered_at": datetime.now(timezone.utc).timestamp()
                    })

                    logger.info(
                        "qube_found_via_dht",
                        target_qube_id=target_qube_id,
                        multiaddr=multiaddr,
                        providers_count=len(providers)
                    )

                    MetricsRecorder.record_p2p_event("dht_discovery_success", self.qube_id)

                    return multiaddr
                else:
                    logger.warning("provider_has_no_addrs", target_qube_id=target_qube_id)
                    return None
            else:
                logger.info("qube_not_found_in_dht", target_qube_id=target_qube_id)
                MetricsRecorder.record_p2p_event("dht_discovery_miss", self.qube_id)
                return None

        except Exception as e:
            logger.error(
                "dht_find_qube_failed",
                target_qube_id=target_qube_id,
                error=str(e),
                exc_info=True
            )
            MetricsRecorder.record_p2p_event("dht_discovery_error", self.qube_id)
            return None

    async def find_multiple_qubes(self, qube_ids: List[str]) -> Dict[str, Optional[str]]:
        """
        Find multiple Qubes in parallel

        Args:
            qube_ids: List of Qube IDs to find

        Returns:
            Dict mapping qube_id -> multiaddr (or None if not found)
        """
        try:
            tasks = [self.find_qube(qube_id) for qube_id in qube_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            discoveries = {}
            for qube_id, result in zip(qube_ids, results):
                if isinstance(result, Exception):
                    logger.error("find_qube_exception", qube_id=qube_id, error=str(result))
                    discoveries[qube_id] = None
                else:
                    discoveries[qube_id] = result

            logger.info(
                "multiple_qubes_discovery_complete",
                total=len(qube_ids),
                found=sum(1 for v in discoveries.values() if v is not None)
            )

            return discoveries

        except Exception as e:
            logger.error("find_multiple_qubes_failed", error=str(e))
            return {qube_id: None for qube_id in qube_ids}

    async def get_routing_table(self) -> List[Dict[str, Any]]:
        """
        Get DHT routing table

        Returns:
            List of peer information from routing table
        """
        try:
            if not self.dht:
                return []

            # Get routing table peers
            # (Simplified - actual implementation depends on DHT API)
            routing_table = []

            logger.debug("routing_table_retrieved", peers_count=len(routing_table))

            return routing_table

        except Exception as e:
            logger.error("get_routing_table_failed", error=str(e))
            return []

    def _add_to_cache(self, qube_id: str, info: Dict[str, Any]) -> None:
        """Add discovery result to cache"""
        self.discovery_cache[qube_id] = info

    def _get_from_cache(self, qube_id: str) -> Optional[Dict[str, Any]]:
        """Get discovery result from cache if not expired"""
        if qube_id not in self.discovery_cache:
            return None

        cached = self.discovery_cache[qube_id]
        discovered_at = cached.get("discovered_at", 0)
        current_time = datetime.now(timezone.utc).timestamp()

        if current_time - discovered_at > self.cache_ttl:
            # Cache expired
            del self.discovery_cache[qube_id]
            return None

        return cached

    def clear_cache(self) -> None:
        """Clear discovery cache"""
        self.discovery_cache.clear()
        logger.debug("discovery_cache_cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_qubes": len(self.discovery_cache),
            "ttl_seconds": self.cache_ttl
        }
