"""
BCMR (Bitcoin Cash Metadata Registry) Generation

Creates standardized metadata for Qube CashTokens NFTs.
From docs/10_Blockchain_Integration.md Section 7.5
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from utils.logging import get_logger

logger = get_logger(__name__)


class BCMRGenerator:
    """
    Generate BCMR-compliant metadata for Qube NFTs

    BCMR Specification: https://cashtokens.org/docs/bcmr/chip/

    Features:
    - Versioned metadata with timestamps
    - Rich content (images, descriptions, links)
    - Wallet integration (Paytaca, Cashonize, Zapit)
    - NFT attributes and traits
    """

    def __init__(self, registry_url: str = "https://qubes.network/bcmr.json", qube_dir: Optional[Path] = None, qube_name: Optional[str] = None):
        """
        Initialize BCMR generator

        Args:
            registry_url: Public URL for BCMR registry
            qube_dir: Optional qube directory for qube-specific BCMR (e.g., data/users/bit_faced/qubes/Alph_26286A30/)
                     If provided, BCMR will be saved to {qube_dir}/blockchain/{qube_name}_bcmr.json
                     If None, uses legacy shared directory data/blockchain/bcmr/
            qube_name: Qube name for filename (e.g., "Alph" -> "Alph_bcmr.json")
        """
        self.registry_url = registry_url
        self.qube_dir = qube_dir
        self.qube_name = qube_name

        if qube_dir:
            # Qube-specific BCMR storage (for mobility)
            self.bcmr_dir = qube_dir / "blockchain"

            # Use qube name in filename if provided, otherwise use generic name
            if qube_name:
                self.bcmr_file = self.bcmr_dir / f"{qube_name}_bcmr.json"
            else:
                self.bcmr_file = self.bcmr_dir / "bcmr.json"

            self.use_qube_storage = True
        else:
            # Legacy shared BCMR storage
            self.bcmr_dir = Path("data/blockchain/bcmr")
            self.bcmr_file = None  # Will use category_id as filename
            self.use_qube_storage = False

        self.bcmr_dir.mkdir(parents=True, exist_ok=True)

        logger.info("bcmr_generator_initialized", registry_url=registry_url, qube_specific=self.use_qube_storage, qube_name=qube_name)

    def generate_bcmr_metadata(
        self,
        category_id: str,
        qube,
        commitment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate BCMR metadata for a Qube NFT
        From docs Section 7.5

        Args:
            category_id: CashToken category ID
            qube: Qube instance
            commitment_data: Data that was hashed into commitment

        Returns:
            BCMR-compliant metadata dict
        """
        logger.info(
            "generating_bcmr_metadata",
            category_id=category_id[:16] + "...",
            qube_id=qube.qube_id
        )

        # Current timestamp for this revision
        revision_timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        # Get Qube attributes
        qube_name = getattr(qube, 'name', f"Qube {qube.qube_id}")
        qube_description = getattr(
            qube.genesis_block,
            "genesis_prompt",
            f"Sovereign AI agent {qube.qube_id}"
        )[:500]  # First 500 chars

        # Create BCMR-compliant metadata
        bcmr_metadata = {
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
                    "web": "https://qubes.network",
                    "registry": self.registry_url,
                    "support": "https://qubes.network/support"
                }
            },
            "identities": {
                category_id: {
                    revision_timestamp: self._create_identity_snapshot(
                        category_id,
                        qube,
                        qube_name,
                        qube_description,
                        commitment_data
                    )
                }
            }
        }

        logger.debug(
            "bcmr_metadata_generated",
            category_id=category_id[:16] + "...",
            revision=revision_timestamp
        )

        return bcmr_metadata

    def _create_identity_snapshot(
        self,
        category_id: str,
        qube,
        name: str,
        description: str,
        commitment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create identity snapshot for BCMR revision

        Args:
            category_id: CashToken category ID
            qube: Qube instance
            name: Qube name
            description: Qube description
            commitment_data: Commitment data

        Returns:
            Identity snapshot dict
        """
        # Extract attributes from Qube
        attributes = [
            {"trait_type": "Qube ID", "value": qube.qube_id},
            {"trait_type": "Genesis Block Hash", "value": qube.genesis_block.block_hash},
            {"trait_type": "Creator", "value": getattr(qube.genesis_block, "creator", "Unknown")},
            {"trait_type": "Birth Date", "value": qube.genesis_block.birth_timestamp},
            {"trait_type": "Home Blockchain", "value": "Bitcoin Cash"}
        ]

        # Add AI model if available
        if hasattr(qube.genesis_block, "ai_model"):
            attributes.append({
                "trait_type": "AI Model",
                "value": qube.genesis_block.ai_model
            })

        # Add memory block count if available
        if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'get_block_count'):
            try:
                block_count = qube.memory_chain.get_block_count()
                attributes.append({
                    "trait_type": "Memory Blocks",
                    "value": str(block_count)
                })
            except:
                pass

        return {
            "name": name,
            "description": description,
            "token": {
                "category": category_id,
                "symbol": "QUBE",
                "decimals": 0  # NFTs have 0 decimals
            },
            "uris": {
                "icon": f"ipfs://{getattr(qube, 'avatar_ipfs_cid', '')}" if getattr(qube, 'avatar_ipfs_cid', '') else "",
                "image": f"ipfs://{getattr(qube, 'avatar_ipfs_cid', '')}" if getattr(qube, 'avatar_ipfs_cid', '') else "",
                "web": f"https://qubes.network/qube/{qube.qube_id}",
                "support": "https://qubes.network/support"
            },
            "extensions": {
                "commitment_data": commitment_data,  # Original data before hashing
                "attributes": attributes
            }
        }

    def save_bcmr_locally(
        self,
        category_id: str,
        bcmr_metadata: Dict[str, Any]
    ) -> str:
        """
        Save BCMR metadata to local file

        Args:
            category_id: CashToken category ID
            bcmr_metadata: BCMR metadata dict

        Returns:
            Local file path
        """
        if self.use_qube_storage:
            # Qube-specific: save as blockchain/bcmr.json
            bcmr_path = self.bcmr_file
        else:
            # Legacy: save as bcmr/{category_id}.json
            bcmr_path = self.bcmr_dir / f"{category_id}.json"

        with open(bcmr_path, 'w') as f:
            json.dump(bcmr_metadata, f, indent=2)

        logger.info(
            "bcmr_saved_locally",
            category_id=category_id[:16] + "...",
            path=str(bcmr_path),
            qube_specific=self.use_qube_storage
        )

        return str(bcmr_path)

    def add_revision(
        self,
        category_id: str,
        updated_metadata: Dict[str, Any]
    ) -> str:
        """
        Add new revision to existing BCMR metadata

        This is the preferred way to update Qube metadata:
        - No blockchain transaction required
        - Instant updates
        - Lower cost
        - Full version history

        Args:
            category_id: CashToken category ID
            updated_metadata: Updated metadata dict

        Returns:
            Local file path
        """
        logger.info(
            "adding_bcmr_revision",
            category_id=category_id[:16] + "..."
        )

        bcmr_path = self.bcmr_dir / f"{category_id}.json"

        # Load existing BCMR or create new
        if bcmr_path.exists():
            with open(bcmr_path, 'r') as f:
                bcmr_metadata = json.load(f)
        else:
            logger.warning(
                "bcmr_not_found_creating_new",
                category_id=category_id[:16] + "..."
            )
            bcmr_metadata = self._create_empty_bcmr_template(category_id)

        # Create new revision timestamp
        revision_timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        # Add new revision
        bcmr_metadata["identities"][category_id][revision_timestamp] = {
            "name": updated_metadata.get("name", "Qube"),
            "description": updated_metadata.get("description", ""),
            "token": {
                "category": category_id,
                "symbol": "QUBE",
                "decimals": 0
            },
            "extensions": {
                "updated_metadata": updated_metadata,
                "revision": revision_timestamp
            }
        }

        bcmr_metadata["latestRevision"] = revision_timestamp

        # Save updated BCMR
        with open(bcmr_path, 'w') as f:
            json.dump(bcmr_metadata, f, indent=2)

        logger.info(
            "bcmr_revision_added",
            category_id=category_id[:16] + "...",
            revision=revision_timestamp
        )

        return str(bcmr_path)

    def _create_empty_bcmr_template(self, category_id: str) -> Dict[str, Any]:
        """Create empty BCMR template"""
        return {
            "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "latestRevision": datetime.now(timezone.utc).isoformat() + "Z",
            "registryIdentity": {
                "name": "Qubes Network",
                "description": "Sovereign AI Agent NFT Registry",
                "uris": {
                    "web": "https://qubes.network",
                    "registry": self.registry_url
                }
            },
            "identities": {
                category_id: {}
            }
        }

    def load_bcmr(self, category_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Load BCMR metadata from local file

        Args:
            category_id: CashToken category ID (only needed for legacy storage)

        Returns:
            BCMR metadata dict or None if not found
        """
        if self.use_qube_storage:
            # Qube-specific: load from blockchain/bcmr.json
            bcmr_path = self.bcmr_file
        else:
            # Legacy: load from bcmr/{category_id}.json
            if not category_id:
                raise ValueError("category_id required for legacy BCMR storage")
            bcmr_path = self.bcmr_dir / f"{category_id}.json"

        if not bcmr_path.exists():
            logger.debug(
                "bcmr_not_found",
                category_id=category_id[:16] + "..." if category_id else "N/A",
                path=str(bcmr_path)
            )
            return None

        with open(bcmr_path, 'r') as f:
            return json.load(f)
