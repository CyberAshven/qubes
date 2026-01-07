"""
Qube NFT Registry

Maps Qube IDs to Bitcoin Cash CashToken Category IDs.
From docs/10_Blockchain_Integration.md Section 7.6
"""

import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


class QubeNFTRegistry:
    """
    Registry mapping Qube IDs to CashToken Category IDs

    Maintains a local database of all minted Qube NFTs.
    """

    def __init__(self, registry_path: str = "data/blockchain/nft_registry.json"):
        """
        Initialize NFT registry

        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        self.registry = self._load_registry()

        logger.info(
            "nft_registry_initialized",
            path=str(self.registry_path),
            entries=len(self.registry)
        )

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load registry from disk"""
        if not self.registry_path.exists():
            logger.debug("registry_not_found_creating_new")
            return {}

        try:
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)

            logger.debug("registry_loaded", entries=len(registry))

            return registry

        except Exception as e:
            logger.error("registry_load_failed", error=str(e))
            return {}

    def _save_registry(self) -> None:
        """Save registry to disk"""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)

            logger.debug("registry_saved", entries=len(self.registry))

        except Exception as e:
            logger.error("registry_save_failed", error=str(e))

    def register_nft(
        self,
        qube_id: str,
        category_id: str,
        mint_txid: str,
        recipient_address: str,
        commitment: str,
        network: str = "mainnet",
        multiaddr: Optional[str] = None
    ) -> None:
        """
        Register a newly minted Qube NFT

        Args:
            qube_id: Qube ID (8-character hex)
            category_id: CashToken category ID
            mint_txid: Minting transaction ID
            recipient_address: Recipient's BCH address
            commitment: NFT commitment hex
            network: "mainnet" or "chipnet"
            multiaddr: Optional P2P multiaddr for peer discovery
        """
        logger.info(
            "registering_nft",
            qube_id=qube_id,
            category_id=category_id[:16] + "...",
            has_multiaddr=bool(multiaddr)
        )

        # Validate official Qubes category before registering
        from core.official_category import validate_official_qube
        validate_official_qube(category_id, context="NFT registration")

        entry = {
            "qube_id": qube_id,
            "category_id": category_id,
            "mint_txid": mint_txid,
            "recipient_address": recipient_address,
            "commitment": commitment,
            "network": network,
            "minted_at": datetime.now(timezone.utc).isoformat()
        }

        # Add multiaddr if provided
        if multiaddr:
            entry["multiaddr"] = multiaddr

        self.registry[qube_id] = entry
        self._save_registry()

        logger.info(
            "nft_registered",
            qube_id=qube_id,
            category_id=category_id[:16] + "...",
            has_multiaddr=bool(multiaddr)
        )

    def get_category_id(self, qube_id: str) -> Optional[str]:
        """
        Get category ID for a Qube

        Args:
            qube_id: Qube ID

        Returns:
            Category ID or None if not registered
        """
        entry = self.registry.get(qube_id)

        if entry:
            return entry["category_id"]

        logger.debug("qube_not_registered", qube_id=qube_id)
        return None

    def get_nft_info(self, qube_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full NFT information for a Qube

        Args:
            qube_id: Qube ID

        Returns:
            NFT info dict or None if not registered
        """
        return self.registry.get(qube_id)

    def find_by_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Find Qube by category ID

        Args:
            category_id: CashToken category ID

        Returns:
            NFT info dict or None if not found
        """
        for qube_id, entry in self.registry.items():
            if entry["category_id"] == category_id:
                return entry

        logger.debug("category_not_found", category_id=category_id[:16] + "...")
        return None

    def list_all_nfts(self) -> List[Dict[str, Any]]:
        """
        List all registered NFTs

        Returns:
            List of NFT info dicts
        """
        return list(self.registry.values())

    def is_registered(self, qube_id: str) -> bool:
        """
        Check if Qube has a registered NFT

        Args:
            qube_id: Qube ID

        Returns:
            True if registered
        """
        return qube_id in self.registry

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics

        Returns:
            Stats dict
        """
        nfts_by_network = {}

        for entry in self.registry.values():
            network = entry.get("network", "unknown")
            nfts_by_network[network] = nfts_by_network.get(network, 0) + 1

        return {
            "total_nfts": len(self.registry),
            "by_network": nfts_by_network
        }

    def update_multiaddr(self, qube_id: str, multiaddr: str) -> bool:
        """
        Update P2P multiaddr for a registered Qube NFT

        Args:
            qube_id: Qube ID
            multiaddr: P2P multiaddr

        Returns:
            True if updated successfully, False if Qube not registered
        """
        if qube_id not in self.registry:
            logger.warning("update_multiaddr_failed_not_registered", qube_id=qube_id)
            return False

        self.registry[qube_id]["multiaddr"] = multiaddr
        self.registry[qube_id]["multiaddr_updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_registry()

        logger.info("multiaddr_updated", qube_id=qube_id)
        return True

    def get_multiaddr(self, qube_id: str) -> Optional[str]:
        """
        Get P2P multiaddr for a Qube

        Args:
            qube_id: Qube ID

        Returns:
            Multiaddr or None if not registered or no multiaddr set
        """
        entry = self.registry.get(qube_id)

        if not entry:
            return None

        return entry.get("multiaddr")

    def export_registry(self, output_path: str) -> None:
        """
        Export registry to file

        Args:
            output_path: Export file path
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(self.registry, f, indent=2)

            logger.info("registry_exported", path=output_path)

        except Exception as e:
            logger.error("registry_export_failed", error=str(e))
