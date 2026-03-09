"""
Blockchain Manager

High-level interface for all blockchain operations.
Coordinates NFT minting, BCMR generation, IPFS uploads, and verification.
From docs/10_Blockchain_Integration.md Section 7
"""

from typing import Dict, Any, Optional

from blockchain.covenant_client import CovenantMinter
from blockchain.bcmr import BCMRGenerator
from blockchain.ipfs import IPFSUploader
from blockchain.verifier import NFTVerifier
from blockchain.registry import QubeNFTRegistry
from crypto.keys import derive_commitment
from utils.logging import get_logger

logger = get_logger(__name__)


class BlockchainManager:
    """
    Unified interface for all blockchain operations

    Provides:
    - Qube NFT minting (single transaction)
    - BCMR metadata generation
    - IPFS hosting
    - NFT ownership verification
    - Registry management
    """

    def __init__(self, network: str = "mainnet"):
        """
        Initialize blockchain manager

        Args:
            network: "mainnet" or "chipnet"
        """
        self.network = network
        import os

        # Check if we're in development/test mode (check DEV_MODE first!)
        dev_mode = os.getenv("QUBES_DEV_MODE", "false").lower() == "true"

        if dev_mode:
            # Developer mode: use mock blockchain regardless of token existence
            logger.warning(
                "platform_dev_mode_enabled",
                message="QUBES_DEV_MODE=true, using mock blockchain operations"
            )
            self.dev_mode = True
            self.minter = None
        else:
            # Production mode: use CashScript covenant for permissionless minting
            self.dev_mode = False
            self.minter = CovenantMinter(network=network)

        # Initialize other components (work in both dev and production modes)
        self.bcmr_generator = BCMRGenerator()

        # Auto-detect Pinata if API key is available
        import os
        use_pinata = bool(os.getenv("PINATA_API_KEY"))
        self.ipfs_uploader = IPFSUploader(use_pinata=use_pinata)

        self.verifier = NFTVerifier()
        self.registry = QubeNFTRegistry()

        if self.dev_mode:
            logger.info(
                "blockchain_manager_initialized",
                network=network,
                mode="development (mock blockchain)"
            )
        else:
            logger.info(
                "blockchain_manager_initialized",
                network=network,
                mode="covenant",
                category_id=self.minter.category_id[:16] + "..."
            )

    async def prepare_mint_transaction(
        self,
        qube,
        recipient_address: str,
        user_address: str,
        change_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build an unsigned WalletConnect transaction for minting.

        Returns the WC transaction object that the frontend sends to the
        user's wallet for signing. No Qube is created yet.

        Args:
            qube: Qube-like object with public_key (or temp key holder)
            recipient_address: BCH cashaddr (token-aware)
            user_address: User's BCH address from WalletConnect session
            change_address: Where to send change (defaults to user_address if None)

        Returns:
            {
                "wc_transaction": str,
                "category_id": str,
                "commitment": str,
                "covenant_address": str,
                "recipient_address": str
            }
        """
        if self.dev_mode:
            import hashlib
            mock_commitment = derive_commitment(qube.public_key)
            return {
                "wc_transaction": "{}",
                "category_id": hashlib.sha256(f"mock_{qube.qube_id}".encode()).hexdigest(),
                "commitment": mock_commitment,
                "covenant_address": "mock_covenant",
                "recipient_address": recipient_address
            }

        return await self.minter.prepare_mint_transaction(
            qube, recipient_address, user_address, change_address=change_address
        )

    async def finalize_qube_nft(
        self,
        qube,
        mint_txid: str,
        category_id: str,
        commitment: str,
        recipient_address: str,
        upload_to_ipfs: bool = True
    ) -> Dict[str, Any]:
        """
        Finalize a minted Qube NFT — BCMR, IPFS, registry.

        Called after the wallet has signed and broadcast the mint transaction.
        This does steps 2-5 of the full mint_qube_nft workflow.

        Args:
            qube: Qube instance
            mint_txid: Transaction ID from the wallet's broadcast
            category_id: NFT category ID
            commitment: NFT commitment hex
            recipient_address: BCH cashaddr
            upload_to_ipfs: Whether to upload BCMR to IPFS

        Returns:
            Same structure as mint_qube_nft
        """
        logger.info(
            "finalizing_qube_nft",
            qube_id=qube.qube_id,
            mint_txid=mint_txid
        )

        mint_result = {
            "category_id": category_id,
            "mint_txid": mint_txid,
            "commitment": commitment,
            "recipient_address": recipient_address,
            "network": self.network
        }

        # Step 2: Generate BCMR metadata
        commitment_data = {
            "qube_id": qube.qube_id,
            "genesis_block_hash": qube.genesis_block.block_hash,
            "creator_public_key": getattr(qube.genesis_block, "creator", ""),
            "birth_timestamp": qube.genesis_block.birth_timestamp,
            "name": getattr(qube, 'name', qube.qube_id),
            "version": "1.0"
        }

        qube_name = getattr(qube, 'name', qube.qube_id)
        qube_bcmr_generator = BCMRGenerator(qube_dir=qube.data_dir, qube_name=qube_name)

        bcmr_metadata = qube_bcmr_generator.generate_bcmr_metadata(
            category_id=category_id,
            qube=qube,
            commitment_data=commitment_data
        )

        bcmr_path = qube_bcmr_generator.save_bcmr_locally(
            category_id=category_id,
            bcmr_metadata=bcmr_metadata
        )

        result = {
            **mint_result,
            "bcmr_local_path": bcmr_path
        }

        # Step 3: Upload to IPFS
        if upload_to_ipfs:
            ipfs_uri = await self.ipfs_uploader.upload_bcmr(
                bcmr_metadata,
                qube_name=qube_name,
                qube_id=qube.qube_id
            )
            if ipfs_uri:
                result["ipfs_uri"] = ipfs_uri
                result["ipfs_gateway_url"] = self.ipfs_uploader.get_gateway_url(ipfs_uri)
            else:
                logger.warning("ipfs_upload_skipped")
                result["ipfs_uri"] = None

        # Step 4: Save NFT metadata to qube
        self._save_nft_metadata_to_qube(qube, mint_result)

        # Step 5: Register in local registry
        self.registry.register_nft(
            qube_id=qube.qube_id,
            category_id=category_id,
            mint_txid=mint_txid,
            recipient_address=recipient_address,
            commitment=commitment,
            network=self.network
        )

        logger.info(
            "qube_nft_finalized",
            qube_id=qube.qube_id,
            category_id=category_id[:16] + "..."
        )

        return result

    async def mint_qube_nft(
        self,
        qube,
        recipient_address: str,
        upload_to_ipfs: bool = True,
        wallet_wif: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mint a Qube as an NFT (complete workflow)

        Process:
        1. Mint NFT on-chain via CashScript covenant (1 transaction)
        2. Generate BCMR metadata (saved to qube's blockchain/ folder)
        3. Upload to IPFS (optional)
        4. Register in local registry
        5. Save NFT metadata to qube's chain/ folder
        6. Return complete NFT info

        Args:
            qube: Qube instance
            recipient_address: Recipient's BCH address (cashaddr)
            upload_to_ipfs: Whether to upload BCMR to IPFS
            wallet_wif: WIF private key for funding (defaults to PLATFORM_BCH_MINTING_KEY env)

        Returns:
            {
                "category_id": str,
                "mint_txid": str,
                "commitment": str,
                "recipient_address": str,
                "bcmr_uri": str,
                "ipfs_uri": str (optional),
                "network": str
            }
        """
        logger.info(
            "minting_qube_nft_workflow",
            qube_id=qube.qube_id,
            recipient=recipient_address
        )

        # Step 1: Mint NFT on-chain (or mock in dev mode)
        if self.dev_mode:
            import hashlib
            from datetime import datetime, timezone

            # Generate mock NFT data for development
            mock_category_id = hashlib.sha256(f"mock_{qube.qube_id}".encode()).hexdigest()
            mock_txid = hashlib.sha256(f"mock_tx_{qube.qube_id}_{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
            # Commitment is SHA256(public_key) - qube_id is first 8 chars of this
            mock_commitment = derive_commitment(qube.public_key)

            mint_result = {
                "category_id": mock_category_id,
                "mint_txid": mock_txid,
                "commitment": mock_commitment,
                "recipient_address": recipient_address,
                "network": "mock_" + self.network
            }

            logger.warning(
                "mock_nft_minted",
                qube_id=qube.qube_id,
                category_id=mock_category_id[:16] + "...",
                message="DEV MODE: Using mock blockchain data"
            )
        else:
            mint_result = await self.minter.mint_qube_nft(
                qube, recipient_address, wallet_wif=wallet_wif
            )

        # Step 2: Generate BCMR metadata (qube-specific storage)
        commitment_data = {
            "qube_id": qube.qube_id,
            "genesis_block_hash": qube.genesis_block.block_hash,
            "creator_public_key": getattr(qube.genesis_block, "creator", ""),
            "birth_timestamp": qube.genesis_block.birth_timestamp,
            "name": getattr(qube, 'name', qube.qube_id),
            "version": "1.0"
        }

        # Create qube-specific BCMR generator (saves to qube's blockchain/{qube_name}_bcmr.json)
        qube_name = getattr(qube, 'name', qube.qube_id)
        qube_bcmr_generator = BCMRGenerator(qube_dir=qube.data_dir, qube_name=qube_name)

        bcmr_metadata = qube_bcmr_generator.generate_bcmr_metadata(
            category_id=mint_result["category_id"],
            qube=qube,
            commitment_data=commitment_data
        )

        # Save BCMR locally (to qube's blockchain/bcmr.json)
        bcmr_path = qube_bcmr_generator.save_bcmr_locally(
            category_id=mint_result["category_id"],
            bcmr_metadata=bcmr_metadata
        )

        result = {
            **mint_result,
            "bcmr_local_path": bcmr_path
        }

        # Step 3: Upload to IPFS (optional)
        if upload_to_ipfs:
            ipfs_uri = await self.ipfs_uploader.upload_bcmr(
                bcmr_metadata,
                qube_name=qube_name,
                qube_id=qube.qube_id
            )

            if ipfs_uri:
                result["ipfs_uri"] = ipfs_uri
                result["ipfs_gateway_url"] = self.ipfs_uploader.get_gateway_url(ipfs_uri)
            else:
                logger.warning("ipfs_upload_skipped")
                result["ipfs_uri"] = None

        # Step 4: Save NFT metadata to qube's chain/ folder (for mobility)
        self._save_nft_metadata_to_qube(qube, mint_result)

        # Step 5: Register in local registry
        self.registry.register_nft(
            qube_id=qube.qube_id,
            category_id=mint_result["category_id"],
            mint_txid=mint_result["mint_txid"],
            recipient_address=recipient_address,
            commitment=mint_result["commitment"],
            network=self.network
        )

        logger.info(
            "qube_nft_minting_complete",
            qube_id=qube.qube_id,
            category_id=mint_result["category_id"][:16] + "..."
        )

        return result

    async def verify_qube_nft(
        self,
        qube_id: str,
        owner_address: str
    ) -> bool:
        """
        Verify Qube NFT ownership

        Args:
            qube_id: Qube ID
            owner_address: Expected owner's BCH address

        Returns:
            True if owner has the NFT
        """
        # Get category ID from registry
        category_id = self.registry.get_category_id(qube_id)

        if not category_id:
            logger.error("qube_not_registered", qube_id=qube_id)
            return False

        # Verify ownership via Chaingraph
        is_owned = await self.verifier.verify_ownership(category_id, owner_address)

        return is_owned

    async def get_qube_nft_details(
        self,
        qube_id: str,
        owner_address: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete NFT details for a Qube

        Args:
            qube_id: Qube ID
            owner_address: Optional owner address for on-chain verification

        Returns:
            Complete NFT info or None
        """
        # Get registry info
        registry_info = self.registry.get_nft_info(qube_id)

        if not registry_info:
            logger.debug("qube_not_in_registry", qube_id=qube_id)
            return None

        result = {
            "qube_id": qube_id,
            "category_id": registry_info["category_id"],
            "mint_txid": registry_info["mint_txid"],
            "recipient_address": registry_info["recipient_address"],
            "commitment": registry_info["commitment"],
            "network": registry_info["network"],
            "minted_at": registry_info["minted_at"]
        }

        # Get BCMR metadata
        bcmr_metadata = self.bcmr_generator.load_bcmr(registry_info["category_id"])

        if bcmr_metadata:
            result["bcmr_metadata"] = bcmr_metadata

        # Verify on-chain ownership (optional)
        if owner_address:
            is_owned = await self.verifier.verify_ownership(
                registry_info["category_id"],
                owner_address
            )
            result["ownership_verified"] = is_owned

        return result

    def _save_nft_metadata_to_qube(self, qube, mint_result: Dict[str, Any]) -> None:
        """
        Save NFT metadata to qube's chain/ folder (for mobility)

        Args:
            qube: Qube instance
            mint_result: Minting result dict

        Creates: {qube_dir}/chain/nft_metadata.json
        """
        import json
        from datetime import datetime, timezone

        # Get qube name for BCMR reference
        qube_name = getattr(qube, 'name', qube.qube_id)

        nft_metadata = {
            "qube_id": qube.qube_id,
            "category_id": mint_result["category_id"],
            "mint_txid": mint_result["mint_txid"],
            "recipient_address": mint_result["recipient_address"],
            "commitment": mint_result["commitment"],
            "network": self.network,
            "minted_at": datetime.now(timezone.utc).isoformat(),
            "bcmr_location": f"blockchain/{qube_name}_bcmr.json"  # Local path within qube folder
        }

        nft_metadata_path = qube.data_dir / "chain" / "nft_metadata.json"

        with open(nft_metadata_path, 'w') as f:
            json.dump(nft_metadata, f, indent=2)

        logger.info(
            "nft_metadata_saved_to_qube",
            qube_id=qube.qube_id,
            path=str(nft_metadata_path)
        )

    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get platform minting token information

        Returns:
            Platform info dict
        """
        if self.dev_mode:
            return {
                "mode": "development",
                "network": "mock_" + self.network,
                "message": "Using mock blockchain operations (QUBES_DEV_MODE=true)"
            }
        return self.minter.get_minting_stats()

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get NFT registry statistics

        Returns:
            Registry stats dict
        """
        return self.registry.get_stats()

    async def update_qube_metadata(
        self,
        qube_id: str,
        updated_metadata: Dict[str, Any],
        upload_to_ipfs: bool = True
    ) -> Dict[str, Any]:
        """
        Update Qube metadata via BCMR revision

        This is the PREFERRED way to update Qube metadata:
        - No blockchain transaction required
        - Instant updates
        - Lower cost
        - Full version history

        From docs Section 7.5 - BCMR Metadata Updates

        Args:
            qube_id: Qube ID
            updated_metadata: Updated metadata dict with:
                - name: str (optional)
                - description: str (optional)
                - uris: dict (optional)
                - attributes: list (optional)
            upload_to_ipfs: Whether to upload updated BCMR to IPFS

        Returns:
            {
                "qube_id": str,
                "category_id": str,
                "revision_timestamp": str,
                "bcmr_local_path": str,
                "ipfs_uri": str (optional)
            }
        """
        logger.info("updating_qube_metadata_via_bcmr", qube_id=qube_id)

        # Get category ID from registry
        category_id = self.registry.get_category_id(qube_id)

        if not category_id:
            raise ValueError(f"Qube {qube_id} not registered. Cannot update metadata.")

        # Add new BCMR revision
        bcmr_path = self.bcmr_generator.add_revision(
            category_id=category_id,
            updated_metadata=updated_metadata
        )

        result = {
            "qube_id": qube_id,
            "category_id": category_id,
            "bcmr_local_path": bcmr_path,
            "revision_timestamp": updated_metadata.get("revision")
        }

        # Upload to IPFS if requested
        if upload_to_ipfs:
            bcmr_metadata = self.bcmr_generator.load_bcmr(category_id)

            if bcmr_metadata:
                # Extract qube name from BCMR metadata for custom filename
                qube_name = None
                try:
                    # BCMR structure: {"$schema": ..., "identities": {category_id: {...}}}
                    identities = bcmr_metadata.get("identities", {})
                    if category_id in identities:
                        qube_name = identities[category_id].get("name")
                except Exception:
                    pass

                ipfs_uri = await self.ipfs_uploader.upload_bcmr(
                    bcmr_metadata,
                    qube_name=qube_name,
                    qube_id=qube_id
                )

                if ipfs_uri:
                    result["ipfs_uri"] = ipfs_uri
                    result["ipfs_gateway_url"] = self.ipfs_uploader.get_gateway_url(ipfs_uri)
                else:
                    logger.warning("ipfs_upload_skipped")
                    result["ipfs_uri"] = None

        logger.info(
            "qube_metadata_updated",
            qube_id=qube_id,
            category_id=category_id[:16] + "..."
        )

        return result

    async def update_mutable_nft_commitment(
        self,
        qube_id: str,
        owner_wif_key: str,
        new_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update NFT commitment by creating new NFT (requires 'mutable' capability)

        ⚠️ WARNING: This requires the NFT to have 'mutable' capability.
        Most Qubes use immutable NFTs for security.

        For standard metadata updates, use update_qube_metadata() instead
        (BCMR revision - no blockchain transaction required).

        From docs Section 7.4 - Mutable NFT Updates

        Args:
            qube_id: Qube ID
            owner_wif_key: Owner's private key (WIF format)
            new_metadata: New metadata to hash into commitment

        Returns:
            {
                "qube_id": str,
                "category_id": str,
                "update_txid": str,
                "new_commitment": str,
                "network": str
            }

        Raises:
            ValueError: If NFT doesn't have 'mutable' capability
        """
        logger.warning(
            "mutable_nft_update_requested",
            qube_id=qube_id,
            message="Most Qubes use immutable NFTs. Consider using update_qube_metadata() instead."
        )

        # Get category ID from registry
        category_id = self.registry.get_category_id(qube_id)

        if not category_id:
            raise ValueError(f"Qube {qube_id} not registered.")

        # Import bitcash for transaction creation
        try:
            from bitcash import Key
            import hashlib
            import json
        except ImportError:
            raise ImportError("bitcash library required for mutable NFT updates")

        # Create new commitment from metadata
        metadata_json = json.dumps(new_metadata, sort_keys=True)
        new_commitment = hashlib.sha256(metadata_json.encode()).digest()

        # Load owner's key
        key = Key(owner_wif_key)

        logger.info(
            "creating_mutable_nft_update_tx",
            category_id=category_id[:16] + "...",
            new_commitment=new_commitment.hex()[:16] + "..."
        )

        # Create transaction output with updated commitment
        # If current NFT has 'mutable' capability, it can create one new NFT
        tx_outputs = [
            (
                key.cashtoken_address,
                1000,  # 1000 satoshis
                "satoshi",
                category_id,
                None,  # New NFT becomes immutable ('none' capability)
                new_commitment.hex(),
                0  # No fungible tokens
            )
        ]

        try:
            # Broadcast transaction
            tx_hash = key.send(tx_outputs)

            logger.info(
                "mutable_nft_updated",
                txid=tx_hash,
                category_id=category_id[:16] + "..."
            )

            # Update BCMR with new revision
            await self.update_qube_metadata(qube_id, new_metadata, upload_to_ipfs=True)

            return {
                "qube_id": qube_id,
                "category_id": category_id,
                "update_txid": tx_hash,
                "new_commitment": new_commitment.hex(),
                "network": self.network
            }

        except Exception as e:
            logger.error(
                "mutable_nft_update_failed",
                error=str(e),
                message="NFT must have 'mutable' capability"
            )
            raise ValueError(
                f"Failed to update mutable NFT: {e}\n"
                f"Note: NFT must have 'mutable' capability. "
                f"For immutable NFTs, use update_qube_metadata() instead."
            )
