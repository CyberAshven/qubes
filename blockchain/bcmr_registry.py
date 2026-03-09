"""
Master BCMR Registry Manager

Manages the master Bitcoin Cash Metadata Registry for all Qubes.
Implements the parsable NFT format with automatic sync to web server.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


class BCMRRegistryManager:
    """
    Manage master BCMR registry for all Qubes

    Features:
    - Single registry with all Qubes under one category_id
    - Parsable NFT format (nfts.parse.types)
    - Dual hosting (IPFS + HTTPS)
    - Auto-sync to web server via SCP
    - Paytaca indexer integration
    """

    def __init__(
        self,
        category_id: str,
        web_dir: Optional[Path] = None,
        registry_url: str = "https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json"
    ):
        """
        Initialize BCMR registry manager

        Args:
            category_id: Platform minting token category ID
            web_dir: Local web directory (default: data/web)
            registry_url: Public URL for registry
        """
        self.category_id = category_id
        self.registry_url = registry_url

        # Setup directories
        if web_dir is None:
            from utils.paths import get_app_data_dir
            web_dir = get_app_data_dir() / "web"
        self.web_dir = web_dir
        self.wellknown_dir = self.web_dir / ".well-known"
        self.wellknown_dir.mkdir(parents=True, exist_ok=True)

        self.registry_file = self.wellknown_dir / "bitcoin-cash-metadata-registry.json"

        logger.info(
            "bcmr_registry_manager_initialized",
            category_id=category_id[:16] + "...",
            registry_file=str(self.registry_file)
        )

    def create_or_update_registry(self, qubes: List[Any]) -> Dict[str, Any]:
        """
        Create or update the master BCMR registry with all Qubes

        Args:
            qubes: List of Qube instances

        Returns:
            Complete BCMR registry dictionary
        """
        logger.info("updating_master_registry", qube_count=len(qubes))

        # Create revision timestamp
        revision_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Build nfts.parse.types with all Qubes
        nft_types = {}

        for qube in qubes:
            qube_entry = self._create_qube_entry(qube)
            # Use qube_id as the key in parse.types
            nft_types[qube.qube_id] = qube_entry

        # Build complete registry
        registry = {
            "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            },
            "latestRevision": revision_timestamp,
            "registryIdentity": {
                "name": "Qubes Network",
                "description": "Sovereign AI Agent NFT Registry",
                "uris": {
                    "web": "https://qube.cash",
                    "registry": self.registry_url,
                    "support": "https://qube.cash/support"
                }
            },
            "identities": {
                self.category_id: {
                    revision_timestamp: {
                        "name": "Qubes",
                        "description": "Sovereign AI Agents with cryptographic identity and persistent memory. Each Qube is a unique self-sovereign digital entity.",
                        "token": {
                            "category": self.category_id,
                            "symbol": "QUBE",
                            "decimals": 0
                        },
                        "uris": {
                            "icon": "ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7",
                            "image": "ipfs://QmNiPRSUMLdAgCWxZ777Cs5idvtipdWuSrim21cm57JDL7",
                            "web": "https://qube.cash",
                            "support": "https://qube.cash/support"
                        },
                        "nfts": {
                            "description": "Each Qube is a unique sovereign AI entity with its own personality, memory, and cryptographic identity. Qubes can form relationships, earn reputation, and participate in the decentralized AI economy.",
                            "parse": {
                                "types": nft_types
                            }
                        }
                    }
                }
            }
        }

        # Save to local file
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

        logger.info(
            "master_registry_updated",
            qube_count=len(qubes),
            file=str(self.registry_file),
            revision=revision_timestamp
        )

        return registry

    def _create_qube_entry(self, qube) -> Dict[str, Any]:
        """
        Create BCMR entry for a single Qube

        Args:
            qube: Qube instance

        Returns:
            BCMR entry dict for nfts.parse.types
        """
        # Get avatar IPFS CID
        avatar_cid = getattr(qube, 'avatar_ipfs_cid', '')

        # Build icon/image URIs
        if avatar_cid:
            icon_uri = f"ipfs://{avatar_cid}"
            image_uri = f"ipfs://{avatar_cid}"
        else:
            # Fallback to empty (wallet will show placeholder)
            icon_uri = ""
            image_uri = ""

        # Extract qube metadata
        qube_name = getattr(qube, 'name', f"Qube {qube.qube_id}")

        # Get genesis block for description
        if hasattr(qube, 'genesis_block'):
            genesis_prompt = getattr(qube.genesis_block, 'genesis_prompt', '')
            # Truncate to 500 chars for description
            description = genesis_prompt[:500] if genesis_prompt else f"Sovereign AI agent {qube_name}"
        else:
            description = f"Sovereign AI agent {qube_name}"

        # Build attributes
        attributes = self._extract_attributes(qube)

        return {
            "name": qube_name,
            "description": description,
            "uris": {
                "icon": icon_uri,
                "image": image_uri,
                "web": f"https://qube.cash/qube/{qube.qube_id}"
            },
            "extensions": {
                "attributes": attributes
            }
        }

    def _extract_attributes(self, qube) -> List[Dict[str, str]]:
        """
        Extract attributes for a Qube in BCMR array format.

        Returns:
            List of {"trait_type": ..., "value": ...} dicts
            (matches server BCMRService format and registry.html expectations)
        """
        attributes = [
            {"trait_type": "Qube ID", "value": qube.qube_id},
            {"trait_type": "Category", "value": "AI Agent"},
        ]

        if hasattr(qube, 'genesis_block'):
            creator = getattr(qube.genesis_block, 'creator', None)
            if creator:
                attributes.append({"trait_type": "Creator", "value": creator})

            birth_timestamp = getattr(qube.genesis_block, 'birth_timestamp', None)
            if birth_timestamp:
                attributes.append({"trait_type": "Birth", "value": str(birth_timestamp)})

            genesis_hash = getattr(qube.genesis_block, 'block_hash', None)
            if genesis_hash:
                attributes.append({"trait_type": "Genesis Hash", "value": genesis_hash[:16] + "..."})

        return attributes

    def add_qube_to_registry(self, qube) -> Dict[str, Any]:
        """
        Add a single Qube to the existing registry

        Args:
            qube: Qube instance to add

        Returns:
            Updated registry
        """
        logger.info("adding_qube_to_registry", qube_id=qube.qube_id)

        # Load existing registry or create new
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                registry = json.load(f)
        else:
            logger.warning("registry_not_found_creating_new")
            # Create empty registry
            registry = self.create_or_update_registry([])

        # Get latest revision
        identities = registry.get("identities", {})
        category_data = identities.get(self.category_id, {})

        # Get latest timestamp
        if category_data:
            latest_timestamp = max(category_data.keys())
            latest_revision = category_data[latest_timestamp]
        else:
            # Create new revision
            latest_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            latest_revision = {
                "name": "Qubes",
                "description": "Sovereign AI Agent NFT Registry",
                "token": {
                    "category": self.category_id,
                    "symbol": "QUBE",
                    "decimals": 0
                },
                "uris": {
                    "icon": "ipfs://QmQubesLogoPlaceholder",
                    "web": "https://qube.cash"
                },
                "nfts": {
                    "description": "Sovereign AI Agents",
                    "parse": {
                        "types": {}
                    }
                }
            }

        # Add qube to parse.types
        qube_entry = self._create_qube_entry(qube)
        latest_revision["nfts"]["parse"]["types"][qube.qube_id] = qube_entry

        # Update registry
        registry["identities"][self.category_id] = {latest_timestamp: latest_revision}
        registry["latestRevision"] = latest_timestamp

        # Save
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

        logger.info("qube_added_to_registry", qube_id=qube.qube_id)

        return registry

    def remove_qube_from_registry(self, qube_id: str) -> bool:
        """
        Remove a Qube from the BCMR registry

        Args:
            qube_id: The qube_id to remove (can be short or full form)

        Returns:
            True if removed successfully, False if not found or error
        """
        logger.info("removing_qube_from_registry", qube_id=qube_id[:16] + "...")

        # Load existing registry
        if not self.registry_file.exists():
            logger.warning("registry_not_found_cannot_remove")
            return False

        try:
            with open(self.registry_file, 'r') as f:
                registry = json.load(f)
        except Exception as e:
            logger.error("failed_to_load_registry", error=str(e))
            return False

        # Navigate to identities.category_id
        identities = registry.get("identities", {})
        category_data = identities.get(self.category_id, {})

        if not category_data:
            logger.warning("category_not_found_in_registry")
            return False

        # Get latest timestamp revision
        latest_timestamp = max(category_data.keys())
        latest_revision = category_data[latest_timestamp]

        # Get parse.types
        nft_types = latest_revision.get("nfts", {}).get("parse", {}).get("types", {})

        if not nft_types:
            logger.warning("no_nft_types_in_registry")
            return False

        # Find and remove the qube entry
        # The key could be the full qube_id or a commitment hash
        removed = False
        keys_to_remove = []

        for key in nft_types:
            # Check if key matches qube_id (full or partial)
            if key == qube_id or key.upper().startswith(qube_id.upper()[:8]):
                keys_to_remove.append(key)
                removed = True
                logger.info("found_qube_to_remove", key=key[:16] + "...")

        for key in keys_to_remove:
            del nft_types[key]

        if not removed:
            logger.warning("qube_not_found_in_registry", qube_id=qube_id[:16] + "...")
            return False

        # Update latestRevision timestamp
        new_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        registry["latestRevision"] = new_timestamp

        # Save updated registry
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(registry, f, indent=2)
            logger.info("qube_removed_from_registry", qube_id=qube_id[:16] + "...")
            return True
        except Exception as e:
            logger.error("failed_to_save_registry", error=str(e))
            return False

    def add_qube_to_server(self, qube) -> bool:
        """
        Add a Qube to the server's BCMR registry via HTTPS API.

        Args:
            qube: Qube instance to add

        Returns:
            True if added successfully, False otherwise
        """
        import requests

        api_url = self.registry_url.replace(
            "/.well-known/bitcoin-cash-metadata-registry.json",
            "/api/v2/bcmr/registry/add"
        )

        api_key = self._get_api_key()
        if not api_key:
            logger.error("bcmr_api_key_not_configured")
            return False

        # Extract qube data
        qube_name = getattr(qube, 'name', f"Qube {qube.qube_id}")
        avatar_cid = getattr(qube, 'avatar_ipfs_cid', '')

        description = ""
        creator = None
        birth_timestamp = None
        genesis_block_hash = None

        if hasattr(qube, 'genesis_block'):
            description = getattr(qube.genesis_block, 'genesis_prompt', '') or f"Sovereign AI agent {qube_name}"
            creator = getattr(qube.genesis_block, 'creator', None)
            birth_timestamp = getattr(qube.genesis_block, 'birth_timestamp', None)
            genesis_block_hash = getattr(qube.genesis_block, 'block_hash', None)

        # Derive commitment from qube's public key
        from crypto.keys import derive_commitment
        commitment = derive_commitment(qube.public_key)

        payload = {
            "commitment": commitment,
            "qube_id": qube.qube_id,
            "qube_name": qube_name,
            "description": description[:1000],
            "avatar_ipfs_cid": avatar_cid or None,
            "creator": creator,
            "birth_timestamp": birth_timestamp,
            "genesis_block_hash": genesis_block_hash[:16] + "..." if genesis_block_hash else None,
        }

        try:
            logger.info("adding_qube_to_server_registry", qube_id=qube.qube_id)
            response = requests.post(
                api_url,
                json=payload,
                headers={"X-API-Key": api_key},
                timeout=15
            )

            if response.status_code == 200:
                logger.info("qube_added_to_server_registry", qube_id=qube.qube_id)
                return True
            else:
                logger.error(
                    "server_registry_add_failed",
                    status=response.status_code,
                    response=response.text[:200]
                )
                return False

        except Exception as e:
            logger.error("server_registry_add_error", error=str(e))
            return False

    def remove_qube_from_server(self, qube_id: str, commitment: str) -> bool:
        """
        Remove a Qube from the server's BCMR registry via HTTPS API.

        Args:
            qube_id: Qube ID (for logging)
            commitment: NFT commitment hex to remove

        Returns:
            True if removed successfully, False otherwise
        """
        import requests

        api_url = self.registry_url.replace(
            "/.well-known/bitcoin-cash-metadata-registry.json",
            "/api/v2/bcmr/registry/remove"
        )

        api_key = self._get_api_key()
        if not api_key:
            logger.error("bcmr_api_key_not_configured")
            return False

        try:
            logger.info("removing_qube_from_server_registry", qube_id=qube_id)
            response = requests.post(
                api_url,
                json={"commitment": commitment},
                headers={"X-API-Key": api_key},
                timeout=15
            )

            if response.status_code == 200:
                logger.info("qube_removed_from_server_registry", qube_id=qube_id)
                return True
            elif response.status_code == 404:
                logger.warning("qube_not_found_on_server_registry", qube_id=qube_id)
                return True  # Not on server = already removed
            else:
                logger.error(
                    "server_registry_remove_failed",
                    status=response.status_code,
                    response=response.text[:200]
                )
                return False

        except Exception as e:
            logger.error("server_registry_remove_error", error=str(e))
            return False

    def _get_api_key(self) -> Optional[str]:
        """Get BCMR API key for server registry updates."""
        return os.environ.get(
            "BCMR_API_KEY",
            "599e00be12c692a0122ad90da805edb935d1acce3d7b235ca153854ef83f463a"
        )

    async def upload_to_ipfs(self) -> Optional[str]:
        """
        Upload BCMR registry to IPFS via Pinata

        Returns:
            IPFS CID or None if upload fails
        """
        if not self.registry_file.exists():
            logger.error("cannot_upload_registry_not_found")
            return None

        try:
            from blockchain.ipfs import IPFSUploader

            # Use Pinata for registry uploads
            uploader = IPFSUploader(use_pinata=True)
            ipfs_uri = await uploader.upload_file(str(self.registry_file), pin=True)

            if ipfs_uri:
                cid = ipfs_uri.replace("ipfs://", "")
                logger.info("registry_uploaded_to_ipfs", cid=cid)
                return cid
            else:
                logger.warning("ipfs_upload_failed")
                return None

        except Exception as e:
            logger.error("ipfs_upload_error", error=str(e))
            return None

    def trigger_paytaca_reindex(self) -> bool:
        """
        Trigger Paytaca BCMR indexer to reindex this category

        Returns:
            True if reindex triggered successfully
        """
        try:
            import requests

            url = f"https://bcmr.paytaca.com/api/bcmr/{self.category_id}/reindex/"

            logger.info("triggering_paytaca_reindex", category_id=self.category_id[:16] + "...")

            response = requests.post(url, timeout=10)

            if response.status_code == 200:
                logger.info("paytaca_reindex_triggered")
                return True
            else:
                logger.warning(
                    "paytaca_reindex_failed",
                    status=response.status_code,
                    response=response.text
                )
                return False

        except Exception as e:
            logger.error("paytaca_reindex_error", error=str(e))
            return False

    def get_registry(self) -> Optional[Dict[str, Any]]:
        """
        Load current registry from disk

        Returns:
            Registry dict or None if not found
        """
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return None
