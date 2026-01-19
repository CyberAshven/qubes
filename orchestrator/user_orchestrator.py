"""
User Orchestrator

Manages all Qubes owned by a single user.
From docs/11_Orchestrator_User_Interface.md Section 8.1
"""

import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple, Union
from datetime import datetime
from dataclasses import dataclass

from core.qube import Qube
from core.multi_qube_conversation import MultiQubeConversation
from crypto.keys import generate_key_pair, derive_qube_id, serialize_public_key, serialize_private_key, deserialize_private_key
from blockchain.manager import BlockchainManager
from blockchain.minting_api import MintingAPIClient, MintingAPIError, RegistrationResult, MintingResult
from config import SecureSettingsManager, APIKeys
from config.user_preferences import UserPreferencesManager, UserPreferences, BlockPreferences
from utils.logging import get_logger
from utils.input_validation import validate_user_id, validate_qube_id, validate_qube_name
from utils.paths import get_user_data_dir
from core.exceptions import QubesError

logger = get_logger(__name__)


@dataclass
class PendingQubeCreation:
    """Result of preparing a Qube for fee-based minting"""
    qube: "Qube"
    qube_id: str
    registration_id: str
    payment_address: str
    payment_amount_bch: float
    payment_amount_satoshis: int
    payment_uri: str
    qr_data: str
    websocket_url: str
    expires_at: datetime
    expires_in_seconds: int
    op_return_data: str = ""
    op_return_hex: str = ""
    qube_wallet_address: str = ""  # P2SH wallet address for Qube earnings


class UserOrchestrator:
    """
    Manages all Qubes owned by a single user

    Responsibilities:
    - Qube lifecycle (create, load, save, delete)
    - Global settings management
    - Master key encryption for private keys
    - Inter-Qube message routing
    - Qube discovery and listing
    """

    def __init__(self, user_id: str, data_dir: Optional[Path] = None):
        """
        Initialize user orchestrator

        Args:
            user_id: Unique identifier for the user
            data_dir: Optional custom data directory (uses platform-aware default)

        Raises:
            QubesError: If user_id validation fails
        """
        # SECURITY: Validate user_id to prevent path traversal
        validated_user_id = validate_user_id(user_id)

        self.user_id = validated_user_id
        # Use platform-aware data directory (critical for Linux AppImage)
        self.data_dir = data_dir or get_user_data_dir(validated_user_id)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.qubes: Dict[str, Qube] = {}  # qube_id -> Qube instance
        self.global_settings = self._load_global_settings()
        self.master_key: Optional[bytes] = None
        self.active_conversations: Dict[str, MultiQubeConversation] = {}  # conversation_id -> conversation
        self.pending_minting: Dict[str, PendingQubeCreation] = {}  # registration_id -> pending creation

        # Initialize secure settings manager (password will be set via set_master_key)
        self.secure_settings = SecureSettingsManager(self.data_dir)

        # Initialize user preferences manager (for non-sensitive settings)
        self.preferences_manager = UserPreferencesManager(self.data_dir)

        logger.info(
            "orchestrator_initialized",
            user_id=user_id,
            data_dir=str(self.data_dir)
        )

    def set_master_key(self, password: str):
        """
        Set master key derived from user password (backward compatible)

        Args:
            password: User password (will be hashed to derive key)
        """
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend

        # Load or generate salt
        salt_file = self.data_dir / "salt.bin"
        iterations_file = self.data_dir / "pbkdf2_iterations.txt"

        if salt_file.exists():
            salt = salt_file.read_bytes()

            # Check for iteration count file (backward compatibility)
            if iterations_file.exists():
                iterations = int(iterations_file.read_text().strip())
                logger.debug("using_stored_iterations", iterations=iterations)
            else:
                # Old user - was using 100K iterations before the security fix
                iterations = 100000
                logger.debug("backward_compat_using_old_iterations", iterations=iterations)
        else:
            # New user - use OWASP 2025 minimum
            import os
            salt = os.urandom(32)
            salt_file.write_bytes(salt)
            iterations = 600000
            iterations_file.write_text(str(iterations))
            logger.debug("new_user_using_new_iterations", iterations=iterations)

        # Derive master key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )

        self.master_key = kdf.derive(password.encode())

        # Also set master password for secure settings (encrypted API keys)
        self.secure_settings.set_master_password(password)

        logger.info("master_key_set", user_id=self.user_id, iterations=iterations)

    async def create_qube(self, config: Dict[str, Any]) -> Qube:
        """
        Create a new Qube

        Args:
            config: Qube configuration with required fields:
                - name: str
                - genesis_prompt: str
                - ai_model: str
                - wallet_address: str (for NFT minting)
                - voice_model: str (optional, defaults based on ai_model)
                - avatar_file: Path (optional, uploaded avatar)
                - generate_avatar: bool (optional, default False - generate with AI)
                - avatar_style: str (optional, default "cyberpunk" - style for generation)
                - favorite_color: str (optional, default #4A90E2)
                - encrypt_genesis: bool (optional, default False)
                - capabilities: dict (optional)
                - default_trust_level: int (optional, default 50)

        Returns:
            Created Qube instance

        Raises:
            QubesError: If required fields missing or creation fails
        """
        try:
            logger.info("creating_qube", name=config.get("name"))

            # Validate required fields
            required_fields = ["name", "genesis_prompt", "ai_model", "owner_pubkey"]
            for field in required_fields:
                if field not in config:
                    raise QubesError(
                        f"Missing required field: {field}. All qubes must have a blockchain identity (NFT) and wallet.",
                        context={"config": config}
                    )

            # Validate owner_pubkey format (compressed secp256k1 public key)
            owner_pubkey = config["owner_pubkey"]
            if not owner_pubkey.startswith(('02', '03')) or len(owner_pubkey) != 66:
                raise QubesError(
                    "Invalid owner_pubkey format. Must be compressed public key (02.../03... + 64 hex chars)",
                    context={"owner_pubkey": owner_pubkey[:20] + "..."}
                )

            # Derive token-aware 'z' address from owner's public key (for NFT recipient)
            from crypto.bch_script import pubkey_to_token_address
            config["wallet_address"] = pubkey_to_token_address(owner_pubkey, network="mainnet")

            # Generate cryptographic keys
            private_key, public_key = generate_key_pair()
            qube_id = derive_qube_id(public_key)

            logger.debug("qube_keys_generated", qube_id=qube_id[:16] + "...")

            # Handle avatar (upload or generate)
            avatar_data = await self._handle_avatar_creation(config, qube_id)

            # Determine voice model
            voice_model = config.get("voice_model") or self._default_voice_for_model(config["ai_model"])

            # Create genesis block
            creator_name = config.get("creator", self.user_id)

            genesis_block = {
                "block_type": "GENESIS",
                "block_number": 0,
                "qube_id": qube_id,
                "qube_name": config["name"],
                "creator": creator_name,
                "public_key": serialize_public_key(public_key),
                "birth_timestamp": int(datetime.now().timestamp()),
                "genesis_prompt": config["genesis_prompt"],
                "genesis_prompt_encrypted": config.get("encrypt_genesis", False),
                "ai_provider": config.get("ai_provider", "openai"),
                "ai_model": config["ai_model"],
                "voice_model": voice_model,
                "avatar": avatar_data,
                "favorite_color": config.get("favorite_color", "#4A90E2"),
                "home_blockchain": config.get("home_blockchain", "bitcoincash"),
                "default_trust_level": config.get("default_trust_level", 50),
                "temporary": False,  # Genesis blocks are always permanent
                "merkle_root": None,  # Will be computed
                "previous_hash": "0" * 64
            }

            # Optionally encrypt genesis prompt
            if genesis_block["genesis_prompt_encrypted"]:
                from crypto.encryption import encrypt_data
                import hashlib

                # Derive 32-byte key from private key (encrypt_data expects bytes, not EC object)
                private_key_bytes = serialize_private_key(private_key)
                encryption_key = hashlib.sha256(private_key_bytes).digest()

                encrypted_prompt = encrypt_data(
                    genesis_block["genesis_prompt"].encode(),
                    encryption_key
                )
                genesis_block["genesis_prompt"] = encrypted_prompt.hex()

            # Create Qube instance (this initializes memory chain and adds genesis block)
            # Pass qubes subdirectory to avoid duplicate nesting
            qubes_dir = self.data_dir / "qubes"
            qubes_dir.mkdir(parents=True, exist_ok=True)

            qube = Qube(
                qube_id=qube_id,
                private_key=private_key,
                public_key=public_key,
                genesis_block=genesis_block,
                data_dir=qubes_dir,
                user_name=self.user_id
            )

            # Mint NFT on Bitcoin Cash (REQUIRED - every qube needs blockchain identity)
            wallet_address = config["wallet_address"]  # Now required field

            logger.info("minting_nft", qube_id=qube_id[:16] + "...", wallet=wallet_address[:20] + "...")

            try:
                blockchain_manager = BlockchainManager(network="mainnet")

                # Mint NFT
                mint_result = await blockchain_manager.mint_qube_nft(
                    qube=qube,
                    recipient_address=wallet_address,
                    upload_to_ipfs=True
                )

                # Update genesis block with NFT info
                qube.genesis_block.nft_category_id = mint_result["category_id"]
                qube.genesis_block.mint_txid = mint_result["mint_txid"]
                qube.genesis_block.bcmr_uri = mint_result.get("ipfs_uri", "")
                # Also update the underlying dict
                genesis_dict = qube.genesis_block.to_dict()
                genesis_dict["nft_category_id"] = mint_result["category_id"]
                genesis_dict["mint_txid"] = mint_result["mint_txid"]
                genesis_dict["bcmr_uri"] = mint_result.get("ipfs_uri", "")

                logger.info("nft_minted_successfully", category_id=mint_result["category_id"][:16] + "...")
            except Exception as e:
                logger.error("nft_minting_failed", error=str(e))
                # NFT minting is now mandatory - fail qube creation
                raise QubesError(
                    f"Failed to mint NFT for qube. NFT is required for blockchain identity: {str(e)}",
                    context={"qube_id": qube_id, "wallet": wallet_address},
                    cause=e
                )

            # Start P2P network node (optional)
            try:
                logger.info("starting_p2p_network", qube_id=qube_id[:16] + "...")
                await qube.start_network()
                logger.info("p2p_network_started", qube_id=qube_id[:16] + "...")
            except Exception as e:
                logger.warning("p2p_network_start_failed", error=str(e))
                # Continue without P2P - can start later

            # Register in orchestrator
            self.qubes[qube_id] = qube
            qube._orchestrator = self  # Store reference for auto-approval

            # Save Qube to storage
            await self._save_qube(qube, private_key)

            # Initialize skills for the new Qube
            self._initialize_qube_skills(qube)

            # Get NFT category from genesis block (might be "not_minted")
            nft_category = qube.genesis_block.to_dict().get("nft_category_id", "not_minted")

            # Apply user's auto-anchor preferences to newly created qube
            prefs = self.preferences_manager.get_block_preferences()
            qube.chain_state.set_auto_anchor(
                enabled=prefs.individual_auto_anchor,
                threshold=prefs.individual_anchor_threshold
            )
            qube.auto_anchor_enabled = prefs.individual_auto_anchor
            qube.auto_anchor_threshold = prefs.individual_anchor_threshold

            logger.info(
                "qube_created_successfully",
                qube_id=qube_id[:16] + "...",
                name=config["name"],
                nft_category=nft_category[:16] + "..." if nft_category != "not_minted" else nft_category,
                auto_anchor_threshold=prefs.individual_anchor_threshold
            )

            return qube

        except Exception as e:
            logger.error("qube_creation_failed", error=str(e), exc_info=True)
            raise QubesError(
                f"Failed to create Qube: {str(e)}",
                context={"config": config},
                cause=e
            )

    async def prepare_qube_for_minting(self, config: Dict[str, Any]) -> PendingQubeCreation:
        """
        Prepare a Qube for fee-based minting via the qube.cash API

        This method creates the Qube locally and registers it with the minting
        service, returning payment details. The Qube is saved but marked as
        pending until payment is confirmed and NFT is minted.

        Args:
            config: Qube configuration (same as create_qube)

        Returns:
            PendingQubeCreation with payment details

        Raises:
            QubesError: If preparation fails
        """
        import os

        try:
            logger.info("preparing_qube_for_minting", name=config.get("name"))

            # Validate required fields
            required_fields = ["name", "genesis_prompt", "ai_model", "owner_pubkey"]
            for field in required_fields:
                if field not in config:
                    raise QubesError(
                        f"Missing required field: {field}",
                        context={"config": config}
                    )

            # Validate owner_pubkey format (compressed secp256k1 public key)
            owner_pubkey = config["owner_pubkey"]
            if not owner_pubkey.startswith(('02', '03')) or len(owner_pubkey) != 66:
                raise QubesError(
                    "Invalid owner_pubkey format. Must be compressed public key (02.../03... + 64 hex chars)",
                    context={"owner_pubkey": owner_pubkey[:20] + "..."}
                )

            # Derive token-aware 'z' address from owner's public key (for NFT recipient)
            from crypto.bch_script import pubkey_to_token_address
            token_address = pubkey_to_token_address(owner_pubkey, network="mainnet")
            config["wallet_address"] = token_address

            logger.info(
                "nft_recipient_derived",
                owner_pubkey=owner_pubkey[:16] + "...",
                token_address=token_address
            )

            # Generate cryptographic keys
            private_key, public_key = generate_key_pair()
            qube_id = derive_qube_id(public_key)

            logger.debug("qube_keys_generated", qube_id=qube_id[:16] + "...")

            # Extract raw 32-byte private key for wallet (not PEM format)
            from crypto.keys import get_raw_private_key_bytes
            raw_private_key = get_raw_private_key_bytes(private_key)

            # Create P2SH wallet with owner's public key (mandatory)
            from crypto.wallet import QubeWallet
            qube_wallet = QubeWallet(
                qube_private_key=raw_private_key,
                owner_pubkey_hex=owner_pubkey,
                network="mainnet"
            )

            logger.info(
                "qube_wallet_created",
                qube_id=qube_id[:8],
                p2sh_address=qube_wallet.p2sh_address
            )

            # Handle avatar (upload or generate)
            avatar_data = await self._handle_avatar_creation(config, qube_id)

            # Get avatar base64 for API if we have a local file
            avatar_base64 = None
            avatar_format = "png"
            avatar_source = avatar_data.get("source", "generated") if avatar_data else "default"
            avatar_ipfs_cid = avatar_data.get("ipfs_cid") if avatar_data else None

            if avatar_data and avatar_data.get("local_path"):
                avatar_path = Path(avatar_data["local_path"])
                if avatar_path.exists():
                    with open(avatar_path, "rb") as f:
                        import base64
                        avatar_base64 = base64.b64encode(f.read()).decode("utf-8")
                    avatar_format = avatar_path.suffix.lstrip(".").lower()
                    if avatar_format == "jpg":
                        avatar_format = "jpeg"

            # Determine voice model
            voice_model = config.get("voice_model") or self._default_voice_for_model(config["ai_model"])

            # Create genesis block
            creator_name = config.get("creator", self.user_id)
            birth_timestamp = int(datetime.now().timestamp())

            genesis_block = {
                "block_type": "GENESIS",
                "block_number": 0,
                "qube_id": qube_id,
                "qube_name": config["name"],
                "creator": creator_name,
                "public_key": serialize_public_key(public_key),
                "birth_timestamp": birth_timestamp,
                "genesis_prompt": config["genesis_prompt"],
                "genesis_prompt_encrypted": config.get("encrypt_genesis", False),
                "ai_provider": config.get("ai_provider", "openai"),
                "ai_model": config["ai_model"],
                "voice_model": voice_model,
                "avatar": avatar_data,
                "favorite_color": config.get("favorite_color", "#4A90E2"),
                "home_blockchain": config.get("home_blockchain", "bitcoincash"),
                "default_trust_level": config.get("default_trust_level", 50),
                "temporary": False,
                "merkle_root": None,
                "previous_hash": "0" * 64,
                # Qube wallet (P2SH multi-sig with asymmetric control)
                "wallet": {
                    "owner_pubkey": owner_pubkey,
                    "p2sh_address": qube_wallet.p2sh_address,
                    "redeem_script_hash": qube_wallet.script_hash,
                    "qube_pubkey": qube_wallet.qube_pubkey_hex
                },
                # Mark as pending minting
                "nft_category_id": "pending_minting",
                "mint_txid": None,
                "bcmr_uri": None
            }

            # Optionally encrypt genesis prompt
            if genesis_block["genesis_prompt_encrypted"]:
                from crypto.encryption import encrypt_data
                import hashlib
                private_key_bytes = serialize_private_key(private_key)
                encryption_key = hashlib.sha256(private_key_bytes).digest()
                encrypted_prompt = encrypt_data(
                    genesis_block["genesis_prompt"].encode(),
                    encryption_key
                )
                genesis_block["genesis_prompt"] = encrypted_prompt.hex()

            # Create Qube instance
            qubes_dir = self.data_dir / "qubes"
            qubes_dir.mkdir(parents=True, exist_ok=True)

            qube = Qube(
                qube_id=qube_id,
                private_key=private_key,
                public_key=public_key,
                genesis_block=genesis_block,
                data_dir=qubes_dir,
                user_name=self.user_id
            )

            # Get genesis block hash for API registration
            # Use the block_hash attribute (set during Qube initialization)
            genesis_block_hash = qube.genesis_block.block_hash

            # Register with minting API
            logger.info("registering_with_minting_api", qube_id=qube_id[:16] + "...")

            async with MintingAPIClient() as api_client:
                registration = await api_client.register_qube(
                    qube_id=qube_id,
                    qube_name=config["name"],
                    genesis_block_hash=genesis_block_hash,
                    public_key=serialize_public_key(public_key),
                    recipient_address=config["wallet_address"],
                    creator=creator_name,
                    birth_timestamp=birth_timestamp,
                    genesis_prompt=config["genesis_prompt"] if not genesis_block["genesis_prompt_encrypted"] else None,
                    ai_model=config["ai_model"],
                    avatar_base64=avatar_base64,
                    avatar_format=avatar_format,
                    avatar_source=avatar_source,
                    avatar_ipfs_cid=avatar_ipfs_cid,  # Pass the IPFS CID from client upload
                    favorite_color=config.get("favorite_color")
                )

            # Save Qube to storage (marked as pending)
            await self._save_qube(qube, private_key)

            # Initialize skills for the new Qube
            self._initialize_qube_skills(qube)

            # Create pending creation result
            pending = PendingQubeCreation(
                qube=qube,
                qube_id=qube_id,
                registration_id=registration.registration_id,
                payment_address=registration.payment.address,
                payment_amount_bch=registration.payment.amount_bch,
                payment_amount_satoshis=registration.payment.amount_satoshis,
                payment_uri=registration.payment.payment_uri,
                qr_data=registration.payment.qr_data,
                websocket_url=registration.websocket_url,
                expires_at=registration.expires_at,
                expires_in_seconds=registration.expires_in_seconds,
                op_return_data=registration.payment.op_return_data,
                op_return_hex=registration.payment.op_return_hex,
                qube_wallet_address=qube_wallet.p2sh_address
            )

            # Track pending minting
            self.pending_minting[registration.registration_id] = pending

            # Also save registration info to disk for recovery
            await self._save_pending_registration(pending, private_key)

            logger.info(
                "qube_prepared_for_minting",
                qube_id=qube_id[:16] + "...",
                registration_id=registration.registration_id,
                payment_address=registration.payment.address,
                amount_bch=registration.payment.amount_bch
            )

            return pending

        except MintingAPIError as e:
            logger.error("minting_api_error", error=str(e), status_code=e.status_code)
            raise QubesError(
                f"Minting API error: {str(e)}",
                context={"config": config, "status_code": e.status_code},
                cause=e
            )
        except Exception as e:
            logger.error("prepare_qube_failed", error=str(e), exc_info=True)
            raise QubesError(
                f"Failed to prepare Qube for minting: {str(e)}",
                context={"config": config},
                cause=e
            )

    async def check_minting_status(self, registration_id: str) -> Dict[str, Any]:
        """
        Check the minting status for a pending registration

        Args:
            registration_id: Registration ID from prepare_qube_for_minting

        Returns:
            Status dict with fields like:
            - status: pending, paid, minting, complete, failed, expired
            - category_id (if complete)
            - mint_txid (if complete)
            - error_message (if failed)
        """
        logger.info("checking_minting_status", registration_id=registration_id)

        async with MintingAPIClient() as api_client:
            status = await api_client.get_status(registration_id)

        # If complete, finalize the qube
        if status.get("status") == "complete":
            await self._finalize_minted_qube(registration_id, status)

        return status

    async def wait_for_minting_completion(
        self,
        registration_id: str,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
        on_status_change: Optional[callable] = None
    ) -> Qube:
        """
        Wait for minting to complete (blocking with polling)

        Args:
            registration_id: Registration ID from prepare_qube_for_minting
            poll_interval: Seconds between polls
            timeout: Maximum time to wait
            on_status_change: Optional callback for status updates

        Returns:
            Finalized Qube with NFT info

        Raises:
            QubesError: On failure, timeout, or expiration
        """
        logger.info(
            "waiting_for_minting",
            registration_id=registration_id,
            timeout=timeout
        )

        async with MintingAPIClient() as api_client:
            result = await api_client.wait_for_completion(
                registration_id=registration_id,
                poll_interval=poll_interval,
                timeout=timeout,
                on_status_change=on_status_change
            )

        # Finalize the qube with NFT info
        qube = await self._finalize_minted_qube(registration_id, {
            "category_id": result.category_id,
            "mint_txid": result.mint_txid,
            "bcmr_ipfs_cid": result.bcmr_ipfs_cid,
            "avatar_ipfs_cid": result.avatar_ipfs_cid,
            "commitment": result.commitment
        })

        return qube

    async def cancel_pending_minting(self, registration_id: str) -> bool:
        """
        Cancel a pending minting registration

        Only works if payment hasn't been received yet.

        Args:
            registration_id: Registration ID to cancel

        Returns:
            True if cancelled successfully
        """
        logger.info("cancelling_pending_minting", registration_id=registration_id)

        try:
            async with MintingAPIClient() as api_client:
                await api_client.cancel_registration(registration_id)

            # Remove from pending
            if registration_id in self.pending_minting:
                pending = self.pending_minting.pop(registration_id)
                # Optionally delete the pending qube files
                await self._cleanup_pending_qube(pending.qube_id)

            # Remove saved registration
            await self._remove_pending_registration(registration_id)

            logger.info("pending_minting_cancelled", registration_id=registration_id)
            return True

        except MintingAPIError as e:
            logger.error("cancel_minting_failed", error=str(e))
            return False

    async def _finalize_minted_qube(
        self,
        registration_id: str,
        mint_info: Dict[str, Any]
    ) -> Qube:
        """
        Finalize a Qube after successful minting

        Updates the genesis block with NFT info and registers the qube.
        """
        logger.info(
            "finalizing_minted_qube",
            registration_id=registration_id,
            category_id=mint_info.get("category_id", "")[:16] + "..."
        )

        # Get pending creation
        pending = self.pending_minting.get(registration_id)

        if not pending:
            # Try to load from disk
            pending = await self._load_pending_registration(registration_id)

        if not pending:
            raise QubesError(
                f"No pending registration found for {registration_id}",
                context={"registration_id": registration_id}
            )

        qube = pending.qube

        # Update genesis block with NFT info
        qube.genesis_block.nft_category_id = mint_info.get("category_id")
        qube.genesis_block.mint_txid = mint_info.get("mint_txid")

        bcmr_cid = mint_info.get("bcmr_ipfs_cid")
        if bcmr_cid:
            qube.genesis_block.bcmr_uri = f"ipfs://{bcmr_cid}"

        # Set commitment on genesis block
        commitment = mint_info.get("commitment")
        if commitment:
            qube.genesis_block.commitment = commitment

        # Create nft_metadata.json with additional blockchain fields
        nft_metadata = {
            "qube_id": qube.qube_id,
            "category_id": mint_info.get("category_id"),
            "mint_txid": mint_info.get("mint_txid"),
            "recipient_address": mint_info.get("recipient_address"),
            "bcmr_ipfs_cid": bcmr_cid,
            "avatar_ipfs_cid": mint_info.get("avatar_ipfs_cid"),
            "commitment": mint_info.get("commitment", qube.qube_id),  # SHA-256 hash commitment from minter
            "network": os.getenv("BCH_NETWORK", "mainnet")
        }

        # Save nft_metadata.json
        qube_dir = self.data_dir / "qubes" / f"{qube.name}_{qube.qube_id}"
        nft_metadata_path = qube_dir / "chain" / "nft_metadata.json"
        with open(nft_metadata_path, "w", encoding="utf-8") as f:
            json.dump(nft_metadata, f, indent=2)
        logger.info("nft_metadata_saved", path=str(nft_metadata_path))

        # Re-save the qube with updated NFT info
        # Need to get private key from storage
        qube_data = await self._load_qube_data(qube.qube_id)
        if self.master_key:
            private_key = self._decrypt_private_key(
                qube_data["encrypted_private_key"],
                self.master_key
            )
            await self._save_qube(qube, private_key)

        # Register in orchestrator
        self.qubes[qube.qube_id] = qube

        # Start P2P network (optional)
        try:
            await qube.start_network()
            logger.info("p2p_network_started", qube_id=qube.qube_id[:16] + "...")
        except Exception as e:
            logger.warning("p2p_network_start_failed", error=str(e))

        # Apply user preferences
        prefs = self.preferences_manager.get_block_preferences()
        qube.chain_state.set_auto_anchor(
            enabled=prefs.individual_auto_anchor,
            threshold=prefs.individual_anchor_threshold
        )
        qube.auto_anchor_enabled = prefs.individual_auto_anchor
        qube.auto_anchor_threshold = prefs.individual_anchor_threshold

        # Clean up pending
        if registration_id in self.pending_minting:
            del self.pending_minting[registration_id]
        await self._remove_pending_registration(registration_id)

        logger.info(
            "qube_minting_finalized",
            qube_id=qube.qube_id[:16] + "...",
            category_id=mint_info.get("category_id", "")[:16] + "..."
        )

        return qube

    async def _save_pending_registration(
        self,
        pending: PendingQubeCreation,
        private_key
    ) -> None:
        """Save pending registration info to disk for recovery"""
        pending_dir = self.data_dir / "pending_minting"
        pending_dir.mkdir(parents=True, exist_ok=True)

        pending_file = pending_dir / f"{pending.registration_id}.json"

        data = {
            "qube_id": pending.qube_id,
            "registration_id": pending.registration_id,
            "payment_address": pending.payment_address,
            "payment_amount_bch": pending.payment_amount_bch,
            "payment_amount_satoshis": pending.payment_amount_satoshis,
            "payment_uri": pending.payment_uri,
            "qr_data": pending.qr_data,
            "websocket_url": pending.websocket_url,
            "expires_at": pending.expires_at.isoformat(),
            "expires_in_seconds": pending.expires_in_seconds,
            "op_return_data": pending.op_return_data,
            "op_return_hex": pending.op_return_hex,
            "created_at": datetime.now().isoformat()
        }

        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug("pending_registration_saved", registration_id=pending.registration_id)

    async def _load_pending_registration(
        self,
        registration_id: str
    ) -> Optional[PendingQubeCreation]:
        """Load pending registration from disk"""
        pending_file = self.data_dir / "pending_minting" / f"{registration_id}.json"

        logger.debug("loading_pending_registration", path=str(pending_file), exists=pending_file.exists())

        if not pending_file.exists():
            logger.warning("pending_file_not_found", path=str(pending_file))
            return None

        with open(pending_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.debug("pending_data_loaded", qube_id=data.get("qube_id"))

        # Load the associated qube (skip NFT validation since it's still pending_minting)
        try:
            qube = await self.load_qube(data["qube_id"], skip_nft_validation=True)
        except Exception as e:
            import traceback
            logger.error("failed_to_load_pending_qube", error=str(e), traceback=traceback.format_exc())
            return None

        # Parse expires_at
        expires_at = datetime.fromisoformat(data["expires_at"])

        return PendingQubeCreation(
            qube=qube,
            qube_id=data["qube_id"],
            registration_id=registration_id,
            payment_address=data["payment_address"],
            payment_amount_bch=data["payment_amount_bch"],
            payment_amount_satoshis=data["payment_amount_satoshis"],
            payment_uri=data["payment_uri"],
            qr_data=data["qr_data"],
            websocket_url=data["websocket_url"],
            expires_at=expires_at,
            expires_in_seconds=data["expires_in_seconds"],
            op_return_data=data.get("op_return_data", ""),
            op_return_hex=data.get("op_return_hex", "")
        )

    async def _remove_pending_registration(self, registration_id: str) -> None:
        """Remove pending registration file"""
        pending_file = self.data_dir / "pending_minting" / f"{registration_id}.json"
        if pending_file.exists():
            pending_file.unlink()
            logger.debug("pending_registration_removed", registration_id=registration_id)

    async def _cleanup_pending_qube(self, qube_id: str) -> None:
        """Clean up a cancelled pending qube's files"""
        # This is a soft cleanup - we don't delete, just mark
        # The user might want to retry
        logger.debug("cleanup_pending_qube", qube_id=qube_id[:16] + "...")

    async def list_pending_registrations(self) -> List[Dict[str, Any]]:
        """List all pending minting registrations"""
        pending_dir = self.data_dir / "pending_minting"
        if not pending_dir.exists():
            return []

        registrations = []
        for pending_file in pending_dir.glob("*.json"):
            try:
                with open(pending_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                registrations.append(data)
            except Exception as e:
                logger.warning("failed_to_load_pending", file=str(pending_file), error=str(e))

        return registrations

    async def load_qube(self, qube_id: str, force_reload: bool = False, skip_nft_validation: bool = False) -> Qube:
        """
        Load existing Qube from storage

        Args:
            qube_id: Qube ID to load
            force_reload: If True, reload qube even if already in memory (refreshes API keys)
            skip_nft_validation: If True, skip NFT category validation (used during finalization)

        Returns:
            Loaded Qube instance

        Raises:
            QubesError: If Qube not found or load fails
        """
        try:
            logger.info("loading_qube", qube_id=qube_id[:16] + "...", force_reload=force_reload, skip_nft_validation=skip_nft_validation)

            if qube_id in self.qubes and not force_reload:
                logger.debug("qube_already_loaded", qube_id=qube_id[:16] + "...")
                return self.qubes[qube_id]
            elif qube_id in self.qubes and force_reload:
                logger.info("force_reloading_qube", qube_id=qube_id[:16] + "...")
                # Remove from cache to force fresh load
                del self.qubes[qube_id]

            # Load Qube data
            qube_data = await self._load_qube_data(qube_id)

            # Decrypt private key with master key
            if not self.master_key:
                raise QubesError(
                    "Master key not set. Call set_master_key() first.",
                    context={"qube_id": qube_id}
                )

            private_key = self._decrypt_private_key(
                qube_data["encrypted_private_key"],
                self.master_key
            )

            # Get qube_dir from memory_chain_path
            # memory_chain_path is like: data/users/{user}/qubes/{name_id}/memory
            memory_chain_path = Path(qube_data["memory_chain_path"])
            qube_dir = memory_chain_path.parent  # Go up one level: memory -> {name_id}

            # Get encryption key for chain_state
            encryption_key = self._get_encryption_key(qube_dir)

            # If encryption_key.enc doesn't exist yet (legacy qube), save it now
            # This ensures existing qubes get their encryption_key.enc file
            key_file = qube_dir / "chain" / "encryption_key.enc"
            if not key_file.exists() and encryption_key:
                self._save_encryption_key(qube_dir, encryption_key)

            # Create Qube from storage
            qube = Qube.from_storage(
                qube_data=qube_data,
                private_key=private_key,
                user_name=self.user_id,
                encryption_key=encryption_key,
                orchestrator=self
            )

            # Defense-in-depth: Validate official Qubes category
            # This should never trigger since minting is mandatory at creation,
            # but protects against corrupted data or tampering
            # Skip validation during finalization (when qube still has pending_minting status)
            if not skip_nft_validation:
                from core.official_category import is_official_qube
                nft_category_id = qube.genesis_block.nft_category_id if hasattr(qube.genesis_block, 'nft_category_id') else None
                if not nft_category_id:
                    raise QubesError(
                        f"Qube {qube_id} is not minted. Minting is required.",
                        context={"qube_id": qube_id}
                    )
                if not is_official_qube(nft_category_id):
                    raise QubesError(
                        f"Qube {qube_id} has invalid category ID. Not an official Qube.",
                        context={"qube_id": qube_id, "category_id": nft_category_id[:16] + "..."}
                    )
            else:
                logger.debug("skipping_nft_validation_for_finalization", qube_id=qube_id[:16] + "...")

            # Initialize AI with API keys from secure settings
            api_keys = self._get_api_keys()

            if api_keys:
                qube.init_ai(api_keys)
                logger.info("ai_initialized_on_load", qube_id=qube_id[:16] + "...", providers=list(api_keys.keys()))

                # Initialize audio after AI (requires API keys)
                qube.init_audio()
                logger.info("audio_initialized_on_load", qube_id=qube_id[:16] + "...")
            else:
                logger.warning("no_api_keys_available", qube_id=qube_id[:16] + "...")

            # Start network (P2P networking - not yet implemented)
            # TODO: Implement start_network() method when P2P is ready
            # await qube.start_network()

            # Register in orchestrator
            self.qubes[qube_id] = qube
            qube._orchestrator = self  # Store reference for auto-approval

            # Apply user preferences for auto-anchor settings
            prefs = self.preferences_manager.get_block_preferences()
            qube.chain_state.set_auto_anchor(
                enabled=prefs.individual_auto_anchor,
                threshold=prefs.individual_anchor_threshold
            )
            qube.auto_anchor_enabled = prefs.individual_auto_anchor
            qube.auto_anchor_threshold = prefs.individual_anchor_threshold
            logger.debug("auto_anchor_prefs_applied",
                        enabled=prefs.individual_auto_anchor,
                        threshold=prefs.individual_anchor_threshold)

            # Background sync wallet balances to chain_state (non-blocking)
            try:
                import asyncio
                genesis = qube.genesis_block
                wallet_info = None
                if hasattr(genesis, 'wallet'):
                    wallet_info = genesis.wallet
                    if hasattr(wallet_info, '__dict__') and not isinstance(wallet_info, dict):
                        wallet_info = vars(wallet_info)
                owner_pubkey = wallet_info.get("owner_pubkey") if wallet_info else None

                asyncio.create_task(
                    qube.wallet_manager.sync_balances_to_chain_state(owner_pubkey)
                )
            except Exception as sync_err:
                logger.debug(f"Could not start balance sync: {sync_err}")

            logger.info("qube_loaded_successfully", qube_id=qube_id[:16] + "...")

            return qube

        except Exception as e:
            logger.error("qube_load_failed", qube_id=qube_id, error=str(e), exc_info=True)
            raise QubesError(
                f"Failed to load Qube: {str(e)}",
                context={"qube_id": qube_id},
                cause=e
            )

    async def list_qubes(self) -> List[Dict[str, Any]]:
        """
        List all Qubes owned by this user

        Returns:
            List of Qube metadata dictionaries
        """
        qube_list = []

        qubes_dir = self.data_dir / "qubes"
        if not qubes_dir.exists():
            return []

        for qube_dir in qubes_dir.iterdir():
            if qube_dir.is_dir():
                # Try new location first (chain/qube_metadata.json)
                qube_metadata = qube_dir / "chain" / "qube_metadata.json"
                if not qube_metadata.exists():
                    # Fallback to old location for backwards compatibility
                    qube_metadata = qube_dir / "qube.json"

                if qube_metadata.exists():
                    with open(qube_metadata, "r") as f:
                        qube_data = json.load(f)
                        genesis = qube_data["genesis_block"]

                        # Get avatar info
                        avatar_info = genesis.get("avatar", {})
                        avatar_ipfs_cid = avatar_info.get("ipfs_cid")
                        avatar_local_path = avatar_info.get("local_path")

                        # Construct avatar URL (IPFS only - file:// URLs don't work in Tauri WebView)
                        # Frontend will handle local files via convertFileSrc()
                        avatar_url = None
                        if avatar_ipfs_cid:
                            avatar_url = f"https://ipfs.io/ipfs/{avatar_ipfs_cid}"
                        # Note: We pass avatar_local_path separately for frontend to handle

                        # Load chain state for block counts using ChainState with encryption
                        total_blocks = 1  # At least genesis
                        block_breakdown = {}
                        try:
                            encryption_key = self._get_encryption_key(qube_dir)
                            if encryption_key:
                                from core.chain_state import ChainState
                                chain_dir = qube_dir / "chain"
                                cs = ChainState(chain_dir, encryption_key, qube_data["qube_id"])
                                chain_data = cs.state.get("chain", {})
                                total_blocks = chain_data.get("total_blocks", 1)
                                block_breakdown = cs.state.get("block_counts", {})
                            else:
                                # Fallback: try legacy plain JSON (for qubes not yet migrated)
                                chain_state_path = qube_dir / "chain" / "chain_state.json"
                                if chain_state_path.exists():
                                    with open(chain_state_path, "r") as cs_f:
                                        chain_state = json.load(cs_f)
                                        # Handle both legacy and v2 formats
                                        if "chain" in chain_state:
                                            total_blocks = chain_state["chain"].get("total_blocks", 1)
                                        else:
                                            total_blocks = chain_state.get("chain_length", 1)
                                        block_breakdown = chain_state.get("block_counts", {})
                        except Exception as cs_err:
                            logger.debug(f"Could not load chain_state for {qube_dir.name}: {cs_err}")

                        # Load relationship stats
                        relationships_file = qube_dir / "relationships" / "relationships.json"
                        relationship_stats = {
                            "total_relationships": 0,
                            "friends": 0,
                            "close_friends": 0,
                            "acquaintances": 0,
                            "strangers": 0,
                            "best_friend": None,
                            "avg_trust_score": 0.0,
                            "highest_trust": 0,
                            "lowest_trust": 100,
                            "total_messages_sent": 0,
                            "total_messages_received": 0,
                            "total_collaborations": 0,
                            "successful_joint_tasks": 0,
                            "failed_joint_tasks": 0,
                            "avg_reliability": 0.0,
                            "avg_honesty": 0.0,
                            "avg_responsiveness": 0.0,
                            "avg_compatibility": 0.0,
                        }
                        if relationships_file.exists():
                            with open(relationships_file, "r") as rel_f:
                                relationships_data = json.load(rel_f)
                                relationship_stats["total_relationships"] = len(relationships_data)

                                # Count relationship types and calculate trust stats
                                friends_count = 0
                                close_friends_count = 0
                                acquaintances_count = 0
                                strangers_count = 0
                                trust_scores = []
                                reliability_scores = []
                                honesty_scores = []
                                responsiveness_scores = []
                                compatibility_scores = []

                                for entity_id, rel in relationships_data.items():
                                    status = rel.get("relationship_status", "stranger")

                                    if status == "close_friend":
                                        close_friends_count += 1
                                        friends_count += 1
                                    elif status == "friend":
                                        friends_count += 1
                                    elif status == "acquaintance":
                                        acquaintances_count += 1
                                    elif status == "stranger":
                                        strangers_count += 1

                                    if rel.get("is_best_friend"):
                                        relationship_stats["best_friend"] = entity_id

                                    # Collect various stats
                                    trust_score = rel.get("overall_trust_score", 50)
                                    trust_scores.append(trust_score)

                                    relationship_stats["total_messages_sent"] += rel.get("total_messages_sent", 0)
                                    relationship_stats["total_messages_received"] += rel.get("total_messages_received", 0)
                                    relationship_stats["total_collaborations"] += rel.get("total_collaborations", 0)
                                    relationship_stats["successful_joint_tasks"] += rel.get("successful_joint_tasks", 0)
                                    relationship_stats["failed_joint_tasks"] += rel.get("failed_joint_tasks", 0)

                                    reliability_scores.append(rel.get("reliability_score", 50))
                                    honesty_scores.append(rel.get("honesty_score", 50))
                                    responsiveness_scores.append(rel.get("responsiveness_score", 50))
                                    compatibility_scores.append(rel.get("compatibility_score", 50))

                                relationship_stats["friends"] = friends_count
                                relationship_stats["close_friends"] = close_friends_count
                                relationship_stats["acquaintances"] = acquaintances_count
                                relationship_stats["strangers"] = strangers_count

                                if trust_scores:
                                    relationship_stats["avg_trust_score"] = sum(trust_scores) / len(trust_scores)
                                    relationship_stats["highest_trust"] = max(trust_scores)
                                    relationship_stats["lowest_trust"] = min(trust_scores)

                                if reliability_scores:
                                    relationship_stats["avg_reliability"] = sum(reliability_scores) / len(reliability_scores)
                                if honesty_scores:
                                    relationship_stats["avg_honesty"] = sum(honesty_scores) / len(honesty_scores)
                                if responsiveness_scores:
                                    relationship_stats["avg_responsiveness"] = sum(responsiveness_scores) / len(responsiveness_scores)
                                if compatibility_scores:
                                    relationship_stats["avg_compatibility"] = sum(compatibility_scores) / len(compatibility_scores)

                        # Load NFT metadata for additional blockchain fields
                        nft_metadata_path = qube_dir / "chain" / "nft_metadata.json"
                        nft_metadata = {}
                        if nft_metadata_path.exists():
                            with open(nft_metadata_path, "r") as nft_f:
                                nft_metadata = json.load(nft_f)

                        # Load BCMR metadata from blockchain folder
                        blockchain_dir = qube_dir / "blockchain"
                        bcmr_data = {}
                        if blockchain_dir.exists():
                            # Look for BCMR JSON file (format: {QubeName}_bcmr.json)
                            bcmr_files = list(blockchain_dir.glob("*_bcmr.json"))
                            if bcmr_files:
                                with open(bcmr_files[0], "r") as bcmr_f:
                                    bcmr_full = json.load(bcmr_f)
                                    # Extract data from BCMR structure
                                    identities = bcmr_full.get("identities", {})
                                    if identities:
                                        # Get the first (and usually only) identity
                                        category_id = list(identities.keys())[0]
                                        identity_data = identities[category_id]
                                        # Get the latest revision
                                        latest_revision_key = list(identity_data.keys())[0]
                                        latest_data = identity_data[latest_revision_key]

                                        # Extract token category
                                        token_data = latest_data.get("token", {})
                                        bcmr_data["nft_category_id"] = token_data.get("category", category_id)

                                        # Extract commitment data
                                        extensions = latest_data.get("extensions", {})
                                        commitment_data = extensions.get("commitment_data", {})
                                        bcmr_data["genesis_block_hash"] = commitment_data.get("genesis_block_hash")
                                        bcmr_data["creator_public_key"] = commitment_data.get("creator_public_key")

                                        # Extract URIs
                                        uris = latest_data.get("uris", {})
                                        bcmr_data["avatar_ipfs_uri"] = uris.get("icon") or uris.get("image")
                                        bcmr_data["web_uri"] = uris.get("web")

                        qube_list.append({
                            "qube_id": qube_data["qube_id"],
                            "name": genesis["qube_name"],
                            "ai_model": genesis["ai_model"],
                            "ai_provider": genesis.get("ai_provider", "unknown"),
                            "birth_timestamp": genesis["birth_timestamp"],
                            "creator": genesis.get("creator"),
                            "voice_model": genesis.get("voice_model"),
                            "tts_enabled": genesis.get("tts_enabled"),
                            "favorite_color": genesis.get("favorite_color", "#00ff88"),
                            "home_blockchain": genesis.get("home_blockchain", "bitcoincash"),
                            "genesis_prompt": genesis.get("genesis_prompt", ""),
                            "nft_category_id": bcmr_data.get("nft_category_id") or genesis.get("nft_category_id"),
                            "mint_txid": genesis.get("mint_txid"),
                            # Construct avatar_url from IPFS CID (prefer nft_metadata over genesis)
                            "avatar_url": f"https://ipfs.io/ipfs/{nft_metadata.get('avatar_ipfs_cid') or avatar_info.get('ipfs_cid')}" if (nft_metadata.get('avatar_ipfs_cid') or avatar_info.get('ipfs_cid')) else None,
                            "total_blocks": total_blocks,
                            "block_breakdown": block_breakdown,
                            "relationship_stats": relationship_stats,
                            "loaded": qube_data["qube_id"] in self.qubes,
                            # Additional blockchain metadata from nft_metadata.json and BCMR
                            "recipient_address": nft_metadata.get("recipient_address"),
                            "commitment": nft_metadata.get("commitment"),
                            "network": nft_metadata.get("network"),
                            # Additional fields from qube_metadata.json genesis block and BCMR
                            "public_key": genesis.get("public_key"),
                            "genesis_block_hash": bcmr_data.get("genesis_block_hash") or genesis.get("block_hash"),
                            "bcmr_uri": genesis.get("bcmr_uri"),
                            "avatar_ipfs_cid": nft_metadata.get("avatar_ipfs_cid") or avatar_info.get("ipfs_cid"),
                            "avatar_local_path": avatar_local_path,  # For frontend to use with convertFileSrc()
                            # Wallet fields (from genesis block wallet object)
                            "wallet_address": genesis.get("wallet", {}).get("p2sh_address"),
                            "wallet_owner_pubkey": genesis.get("wallet", {}).get("owner_pubkey"),
                            "wallet_qube_pubkey": genesis.get("wallet", {}).get("qube_pubkey"),
                            # Derive owner's 'q' address from pubkey
                            "wallet_owner_q_address": self._derive_q_address(genesis.get("wallet", {}).get("owner_pubkey")),
                        })

        logger.debug("qubes_listed", count=len(qube_list))

        return qube_list

    async def delete_qube(self, qube_id: str) -> bool:
        """
        Delete a Qube and all its data

        Args:
            qube_id: Qube ID to delete

        Returns:
            True if successfully deleted

        Raises:
            QubesError: If deletion fails
        """
        try:
            logger.info("deleting_qube", qube_id=qube_id[:16] + "...")

            # Remove from memory if loaded
            if qube_id in self.qubes:
                del self.qubes[qube_id]

            # Find and delete qube directory
            qubes_dir = self.data_dir / "qubes"
            qube_dir = None

            for d in qubes_dir.iterdir():
                if d.is_dir():
                    # Check if this is the qube we're looking for
                    metadata_path = d / "chain" / "qube_metadata.json"
                    if not metadata_path.exists():
                        metadata_path = d / "qube.json"

                    if metadata_path.exists():
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data["qube_id"] == qube_id:
                                qube_dir = d
                                break

            if not qube_dir:
                raise QubesError(
                    f"Qube not found: {qube_id}",
                    context={"qube_id": qube_id}
                )

            # Delete the entire qube directory
            import shutil
            shutil.rmtree(qube_dir)

            # Delete debug prompt cache (prevents stale data in Debug Inspector)
            try:
                import tempfile
                debug_prompt_dir = Path(tempfile.gettempdir()) / "qubes_debug_prompts"
                debug_prompt_file = debug_prompt_dir / f"{qube_id}.json"
                if debug_prompt_file.exists():
                    debug_prompt_file.unlink()
                    logger.debug("deleted_debug_prompt_cache")
            except Exception as e:
                logger.debug(f"Could not delete debug prompt cache: {e}")

            # Remove from BCMR registry via minting API
            try:
                async with MintingAPIClient() as client:
                    await client.unregister_qube(qube_id)
                    logger.info("qube_unregistered_from_bcmr", qube_id=qube_id[:16] + "...")
            except Exception as bcmr_error:
                # Don't fail deletion if BCMR removal fails
                logger.warning("bcmr_unregister_failed", qube_id=qube_id[:16] + "...", error=str(bcmr_error))

            logger.info("qube_deleted_successfully", qube_id=qube_id[:16] + "...")

            return True

        except Exception as e:
            logger.error("qube_deletion_failed", qube_id=qube_id, error=str(e), exc_info=True)
            raise QubesError(
                f"Failed to delete Qube: {str(e)}",
                context={"qube_id": qube_id},
                cause=e
            )

    async def reset_qube(self, qube_id: str) -> bool:
        """
        Reset a Qube to fresh state while preserving identity.

        This resets all accumulated state (blocks, relationships, skills progress,
        snapshots, semantic index) while keeping the genesis block, NFT info,
        and cryptographic identity intact.

        WARNING: This is a destructive operation intended for development only.

        Args:
            qube_id: Qube ID to reset

        Returns:
            True if successfully reset

        Raises:
            QubesError: If reset fails
        """
        import shutil

        try:
            logger.info("resetting_qube", qube_id=qube_id[:16] + "...")

            # Find qube directory
            qubes_dir = self.data_dir / "qubes"
            qube_dir = None

            for d in qubes_dir.iterdir():
                if d.is_dir():
                    metadata_path = d / "chain" / "qube_metadata.json"
                    if not metadata_path.exists():
                        metadata_path = d / "qube.json"

                    if metadata_path.exists():
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data["qube_id"] == qube_id:
                                qube_dir = d
                                break

            if not qube_dir:
                raise QubesError(
                    f"Qube not found: {qube_id}",
                    context={"qube_id": qube_id}
                )

            # Remove from memory if loaded
            if qube_id in self.qubes:
                del self.qubes[qube_id]

            # === DELETE accumulated state files ===

            # 1. Delete all blocks except genesis (block 0)
            blocks_dir = qube_dir / "blocks" / "permanent"
            if blocks_dir.exists():
                for block_file in blocks_dir.glob("*.json"):
                    # Keep genesis block (starts with 0_GENESIS_)
                    if not block_file.name.startswith("0_GENESIS_"):
                        block_file.unlink()
                        logger.debug("deleted_block", file=block_file.name)

            # 1b. Delete all session blocks
            session_blocks_dir = qube_dir / "blocks" / "session"
            if session_blocks_dir.exists():
                shutil.rmtree(session_blocks_dir)
                session_blocks_dir.mkdir(parents=True, exist_ok=True)  # Recreate empty
                logger.debug("deleted_session_blocks")

            # 2. Delete relationships folder
            relationships_dir = qube_dir / "relationships"
            if relationships_dir.exists():
                shutil.rmtree(relationships_dir)
                logger.debug("deleted_relationships_dir")

            # 3. Delete owner_info folder (learned info about owner - now in chain_state)
            owner_info_dir = qube_dir / "owner_info"
            if owner_info_dir.exists():
                shutil.rmtree(owner_info_dir)
                logger.debug("deleted_owner_info_dir")

            # 3b. Delete clearance folder (clearance settings now in chain_state.relationships)
            clearance_dir = qube_dir / "clearance"
            if clearance_dir.exists():
                shutil.rmtree(clearance_dir)
                logger.debug("deleted_clearance_dir")

            # 4. Delete snapshots folder
            snapshots_dir = qube_dir / "snapshots"
            if snapshots_dir.exists():
                shutil.rmtree(snapshots_dir)
                logger.debug("deleted_snapshots_dir")

            # 5. Delete semantic index files
            chain_dir = qube_dir / "chain"
            semantic_index = chain_dir / "semantic_index.faiss"
            semantic_mapping = chain_dir / "semantic_mapping.npy"
            if semantic_index.exists():
                semantic_index.unlink()
                logger.debug("deleted_semantic_index")
            if semantic_mapping.exists():
                semantic_mapping.unlink()
                logger.debug("deleted_semantic_mapping")

            # 6. Delete audio cache
            audio_dir = qube_dir / "audio"
            if audio_dir.exists():
                shutil.rmtree(audio_dir)
                logger.debug("deleted_audio_dir")

            # 7. Delete visualizer settings
            visualizer_settings = qube_dir / "visualizer_settings.json"
            if visualizer_settings.exists():
                visualizer_settings.unlink()
                logger.debug("deleted_visualizer_settings")

            # 8. Delete session lock files (skip if locked by another process)
            for lock_file in qube_dir.glob("*.lock"):
                try:
                    lock_file.unlink()
                    logger.debug("deleted_lock_file", file=lock_file.name)
                except OSError:
                    logger.debug("skipped_locked_file", file=lock_file.name)
            for lock_file in chain_dir.glob("*.lock"):
                try:
                    lock_file.unlink()
                    logger.debug("deleted_chain_lock_file", file=lock_file.name)
                except OSError:
                    logger.debug("skipped_locked_chain_file", file=lock_file.name)

            # 9. Delete root-level chain_state.json if exists (duplicate)
            root_chain_state = qube_dir / "chain_state.json"
            if root_chain_state.exists():
                root_chain_state.unlink()
                logger.debug("deleted_root_chain_state")

            # 10. Delete chain_state backup file (prevents old data restoration)
            chain_state_backup = chain_dir / ".chain_state.backup.json"
            if chain_state_backup.exists():
                chain_state_backup.unlink()
                logger.debug("deleted_chain_state_backup")

            # 11. Delete debug prompt cache (prevents stale data in Debug Inspector)
            try:
                import tempfile
                debug_prompt_dir = Path(tempfile.gettempdir()) / "qubes_debug_prompts"
                debug_prompt_file = debug_prompt_dir / f"{qube_id}.json"
                if debug_prompt_file.exists():
                    debug_prompt_file.unlink()
                    logger.debug("deleted_debug_prompt_cache")
            except Exception as e:
                logger.debug(f"Could not delete debug prompt cache: {e}")

            # === RESET state files to fresh values ===

            # Get encryption key for this qube (required for ChainState)
            encryption_key = self._get_encryption_key(qube_dir)
            if not encryption_key:
                raise QubesError(
                    f"Cannot reset qube - encryption key not available. Is master key set?",
                    context={"qube_id": qube_id}
                )

            # Load genesis block data (source of truth for qube-specific values)
            genesis_path = chain_dir / "genesis.json"
            if not genesis_path.exists():
                raise QubesError(
                    f"Genesis block not found for qube {qube_id}",
                    context={"qube_id": qube_id, "genesis_path": str(genesis_path)}
                )

            with open(genesis_path, "r", encoding="utf-8") as f:
                genesis_data = json.load(f)

            # Use centralized function to create default chain_state
            from core.chain_state import create_default_chain_state
            reset_state = create_default_chain_state(genesis_data, qube_id)

            # Preserve financial data from existing chain_state (wallet/transactions are blockchain data)
            try:
                from core.chain_state import ChainState
                existing_cs = ChainState(chain_dir, encryption_key, qube_id)
                existing_financial = existing_cs.state.get("financial", {})
                if existing_financial and existing_financial.get("wallet", {}).get("address"):
                    reset_state["financial"] = existing_financial
                    logger.debug("preserved_financial_data_during_reset")
            except Exception as e:
                logger.debug(f"Could not preserve financial data: {e}")

            logger.debug(
                "reset_state_created",
                qube_id=qube_id,
                tts_enabled=reset_state["settings"]["tts_enabled"],
                voice_model=reset_state["settings"]["voice_model"],
                model_locked=reset_state["settings"]["model_locked"],
                ai_model=reset_state["runtime"]["current_model"]
            )

            # Write encrypted chain_state directly (bypassing ChainState class to avoid lock conflicts)
            # This is safe because reset is a destructive operation that replaces all state
            from crypto.encryption import encrypt_block_data, derive_chain_state_key

            chain_state_path = chain_dir / "chain_state.json"
            chain_state_key = derive_chain_state_key(encryption_key)
            encrypted_data = encrypt_block_data(reset_state, chain_state_key)  # Pass dict, not string
            encrypted_data["encrypted"] = True  # CRITICAL: Mark as encrypted so ChainState doesn't "migrate" it

            # Atomic write: temp file then rename
            temp_path = chain_state_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f)
            temp_path.replace(chain_state_path)
            logger.debug("reset_chain_state_encrypted")

            # Also delete legacy skills directory if it exists (data now in chain_state)
            skills_dir = qube_dir / "skills"
            if skills_dir.exists():
                shutil.rmtree(skills_dir)
                logger.debug("deleted_legacy_skills_dir")

            logger.info(
                "qube_reset_successfully",
                qube_id=qube_id[:16] + "...",
                preserved=["genesis.json", "qube_metadata.json", "nft_metadata.json", "avatar"]
            )

            return True

        except Exception as e:
            logger.error("qube_reset_failed", qube_id=qube_id, error=str(e), exc_info=True)
            raise QubesError(
                f"Failed to reset Qube: {str(e)}",
                context={"qube_id": qube_id},
                cause=e
            )

    async def get_qube_stats(self, qube_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a qube including block breakdown

        Args:
            qube_id: Qube ID to get stats for

        Returns:
            Dictionary with detailed stats including block counts by type
        """
        try:
            # Load qube metadata
            qubes_dir = self.data_dir / "qubes"
            qube_dir = None

            # Find the qube directory
            for d in qubes_dir.iterdir():
                if d.is_dir() and qube_id in d.name:
                    qube_dir = d
                    break

            if not qube_dir:
                raise QubesError(f"Qube {qube_id} not found")

            # Load qube metadata
            qube_metadata_path = qube_dir / "chain" / "qube_metadata.json"
            if not qube_metadata_path.exists():
                qube_metadata_path = qube_dir / "qube.json"  # Fallback

            with open(qube_metadata_path, "r") as f:
                qube_data = json.load(f)

            genesis = qube_data["genesis_block"]

            # Load chain state to get block counts using ChainState with encryption
            block_breakdown = {}
            total_blocks = 0

            try:
                encryption_key = self._get_encryption_key(qube_dir)
                if encryption_key:
                    from core.chain_state import ChainState
                    chain_dir = qube_dir / "chain"
                    cs = ChainState(chain_dir, encryption_key, qube_id)
                    chain_data = cs.state.get("chain", {})
                    total_blocks = chain_data.get("total_blocks", 0)
                    block_breakdown = cs.state.get("block_counts", {})
                else:
                    # Fallback: try legacy plain JSON
                    chain_state_path = qube_dir / "chain" / "chain_state.json"
                    if chain_state_path.exists():
                        with open(chain_state_path, "r") as f:
                            chain_state = json.load(f)
                            if "chain" in chain_state:
                                total_blocks = chain_state["chain"].get("total_blocks", 0)
                            else:
                                total_blocks = chain_state.get("chain_length", 0)
                            block_breakdown = chain_state.get("block_counts", {})
            except Exception as cs_err:
                logger.debug(f"Could not load chain_state for {qube_id}: {cs_err}")

            # Get avatar info
            avatar_info = genesis.get("avatar", {})
            avatar_ipfs_cid = avatar_info.get("ipfs_cid")
            avatar_local_path = avatar_info.get("local_path")

            # Construct avatar URL (IPFS only - file:// URLs don't work in Tauri WebView)
            # Frontend will handle local files via convertFileSrc()
            avatar_url = None
            if avatar_ipfs_cid:
                avatar_url = f"https://ipfs.io/ipfs/{avatar_ipfs_cid}"
            # Note: We pass avatar_local_path separately for frontend to handle

            stats = {
                "qube_id": qube_data["qube_id"],
                "name": genesis["qube_name"],
                "ai_model": genesis["ai_model"],
                "ai_provider": genesis.get("ai_provider", "unknown"),
                "voice_model": genesis.get("voice_model"),
                "creator": genesis.get("creator"),
                "birth_timestamp": genesis["birth_timestamp"],
                "favorite_color": genesis.get("favorite_color", "#00ff88"),
                "home_blockchain": genesis.get("home_blockchain", "bitcoincash"),
                "genesis_prompt": genesis.get("genesis_prompt", ""),
                "nft_category_id": genesis.get("nft_category_id"),
                "mint_txid": genesis.get("mint_txid"),
                "total_blocks": total_blocks,
                "block_breakdown": block_breakdown,
                "avatar_url": avatar_url,
                "avatar_local_path": avatar_local_path,  # For frontend to use with convertFileSrc()
                "loaded": qube_data["qube_id"] in self.qubes
            }

            return stats

        except Exception as e:
            logger.error("get_qube_stats_failed", qube_id=qube_id, error=str(e))
            raise QubesError(
                f"Failed to get qube stats: {str(e)}",
                context={"qube_id": qube_id},
                cause=e
            )

    def reload_ai_keys(self, qube_id: str) -> None:
        """
        Reload AI API keys for an already-loaded qube

        This is useful when API keys change or new providers are added.

        Args:
            qube_id: Qube ID to reload keys for
        """
        if qube_id not in self.qubes:
            logger.warning("qube_not_loaded_cannot_reload_keys", qube_id=qube_id[:16] + "...")
            return

        qube = self.qubes[qube_id]

        # Load API keys from secure settings
        api_keys = self._get_api_keys()

        if api_keys:
            qube.init_ai(api_keys)
            logger.info("ai_keys_reloaded", qube_id=qube_id[:16] + "...", providers=list(api_keys.keys()))
        else:
            logger.warning("no_api_keys_found_for_reload", qube_id=qube_id[:16] + "...")

    async def send_message_between_qubes(
        self,
        from_qube_id: str,
        to_qube_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send message from one Qube to another

        Args:
            from_qube_id: Sender Qube ID
            to_qube_id: Recipient Qube ID
            message: Message content

        Returns:
            Result dictionary with status and response

        Raises:
            QubesError: If sender Qube not loaded
        """
        if from_qube_id not in self.qubes:
            raise QubesError(
                f"Qube {from_qube_id} not loaded",
                context={"from_qube_id": from_qube_id}
            )

        from_qube = self.qubes[from_qube_id]

        logger.info(
            "routing_message",
            from_qube=from_qube_id[:16] + "...",
            to_qube=to_qube_id[:16] + "..."
        )

        result = await from_qube.send_message(to_qube_id, message)

        return result

    async def _handle_avatar_creation(
        self,
        config: Dict[str, Any],
        qube_id: str
    ) -> Dict[str, Any]:
        """
        Handle avatar creation - upload or generate

        Args:
            config: Qube configuration with optional fields:
                - avatar_file: Path (uploaded avatar)
                - generate_avatar: bool (whether to generate)
                - avatar_style: str (cyberpunk, realistic, cartoon, etc.)

        Returns:
            Avatar data dictionary with IPFS CID and metadata
        """
        # Priority 1: User uploaded an avatar
        if "avatar_file" in config:
            from blockchain.ipfs import IPFSUploader
            from pathlib import Path
            import shutil

            avatar_file = Path(config["avatar_file"])

            # Determine qube-specific chain directory for avatar
            # SECURITY: Validate qube_name to prevent path traversal
            qube_name = validate_qube_name(config["name"])
            validated_qube_id = validate_qube_id(qube_id)
            # Use original name (with spaces) to match qube.py directory creation
            qube_dir_name = f"{qube_name}_{validated_qube_id[:8]}"
            chain_dir = self.data_dir / "qubes" / qube_dir_name / "chain"

            # Create chain directory
            chain_dir.mkdir(parents=True, exist_ok=True)

            # Copy avatar to chain directory with local filename
            local_avatar_filename = f"{qube_id[:8]}_avatar{avatar_file.suffix}"
            local_avatar_path = chain_dir / local_avatar_filename

            shutil.copy2(avatar_file, local_avatar_path)

            logger.info("uploading_avatar", path=str(local_avatar_path))

            # Create custom IPFS filename: avatar_<qube_name>_<qube_id>.<ext>
            safe_name = "".join(c for c in qube_name if c.isalnum() or c in ('-', '_'))
            ipfs_filename = f"avatar_{safe_name}_{qube_id}{avatar_file.suffix}"

            # Load Pinata API key from secure storage and set in environment
            api_keys = self.get_api_keys()
            if not api_keys.pinata_jwt:
                raise QubesError(
                    "Pinata IPFS API key not configured. Please set PINATA_API_KEY in Settings.",
                    context={"qube_id": qube_id}
                )
            os.environ["PINATA_API_KEY"] = api_keys.pinata_jwt

            # Use Pinata for uploaded avatars with custom filename
            uploader = IPFSUploader(use_pinata=True)

            # Check if Pinata is properly configured
            if not uploader.use_pinata:
                raise QubesError(
                    "Pinata IPFS API key not configured. Please set PINATA_API_KEY in Settings.",
                    context={"qube_id": qube_id}
                )

            ipfs_uri = await uploader.upload_file(
                str(local_avatar_path),
                pin=True,
                custom_filename=ipfs_filename
            )

            # Ensure IPFS upload succeeded
            if not ipfs_uri:
                error_detail = uploader.last_error or "Unknown error"
                raise QubesError(
                    f"Failed to upload avatar to IPFS: {error_detail}",
                    context={"qube_id": qube_id, "avatar_path": str(local_avatar_path)}
                )

            # Extract CID from URI
            ipfs_cid = ipfs_uri.replace("ipfs://", "")

            logger.info("avatar_uploaded_to_ipfs", qube_id=qube_id[:16] + "...", ipfs_cid=ipfs_cid[:20] + "...")

            return {
                "source": "uploaded",
                "ipfs_cid": ipfs_cid,
                "local_path": str(local_avatar_path),
                "file_format": avatar_file.suffix[1:],  # Remove dot
                "dimensions": "unknown"
            }

        # Priority 2: Generate avatar using AI
        elif config.get("generate_avatar", False):
            from ai.avatar_generator import AvatarGenerator
            from pathlib import Path

            logger.info("generating_avatar", qube_id=qube_id[:16] + "...")

            # Determine qube-specific chain directory for avatar
            # SECURITY: Validate qube_name to prevent path traversal
            qube_name = validate_qube_name(config["name"])
            validated_qube_id = validate_qube_id(qube_id)
            # Use original name (with spaces) to match qube.py directory creation
            qube_dir_name = f"{qube_name}_{validated_qube_id[:8]}"
            chain_dir = self.data_dir / "qubes" / qube_dir_name / "chain"

            # Create chain directory
            chain_dir.mkdir(parents=True, exist_ok=True)

            # Load Pinata API key from secure storage and set in environment
            api_keys = self.get_api_keys()
            if not api_keys.pinata_jwt:
                raise QubesError(
                    "Pinata IPFS API key not configured. Please set PINATA_API_KEY in Settings.",
                    context={"qube_id": qube_id}
                )
            os.environ["PINATA_API_KEY"] = api_keys.pinata_jwt

            # Initialize IPFS uploader with Pinata enabled
            from blockchain.ipfs import IPFSUploader
            ipfs_uploader = IPFSUploader(use_pinata=True)

            # Check if Pinata is properly configured
            if not ipfs_uploader.use_pinata:
                raise QubesError(
                    "Pinata IPFS API key not configured. Please set PINATA_API_KEY in Settings.",
                    context={"qube_id": qube_id}
                )

            # Initialize generator with qube-specific chain directory and Pinata uploader
            generator = AvatarGenerator(images_dir=chain_dir, ipfs_uploader=ipfs_uploader)

            # Get generation parameters
            avatar_style = config.get("avatar_style", "cyberpunk")
            favorite_color = config.get("favorite_color", "#4A90E2")

            # Generate avatar
            avatar_data = await generator.generate_avatar(
                qube_id=qube_id,
                qube_name=config["name"],
                genesis_prompt=config["genesis_prompt"],
                favorite_color=favorite_color,
                style=avatar_style
            )

            # Ensure IPFS upload succeeded
            if not avatar_data.get("ipfs_cid"):
                error_detail = ipfs_uploader.last_error or "Unknown error"
                raise QubesError(
                    f"Failed to upload generated avatar to IPFS: {error_detail}",
                    context={"qube_id": qube_id, "avatar_path": avatar_data.get("local_path")}
                )

            logger.info(
                "avatar_generated_and_uploaded",
                qube_id=qube_id[:16] + "...",
                style=avatar_style,
                ipfs_cid=avatar_data.get("ipfs_cid", "")[:20] + "..."
            )

            return avatar_data

        # Priority 3: No avatar specified - this is now an error
        else:
            raise QubesError(
                "Avatar is required. Please upload an image or enable AI avatar generation.",
                context={"qube_id": qube_id}
            )

    # =============================================================================
    # API Key Management
    # =============================================================================

    def get_api_keys(self) -> APIKeys:
        """
        Get all stored API keys

        Returns:
            APIKeys instance with all configured keys
        """
        return self.secure_settings.load_api_keys()

    def update_api_key(self, provider: str, api_key: str):
        """
        Update a single API key

        Args:
            provider: Provider name (openai, anthropic, google, etc.)
            api_key: API key value
        """
        self.secure_settings.update_api_key(provider, api_key)
        logger.info("api_key_updated_via_orchestrator", provider=provider, user=self.user_id)

    def delete_api_key(self, provider: str):
        """
        Delete a single API key

        Args:
            provider: Provider name
        """
        self.secure_settings.delete_api_key(provider)
        logger.info("api_key_deleted_via_orchestrator", provider=provider, user=self.user_id)

    def save_api_keys(self, api_keys: APIKeys):
        """
        Save all API keys at once

        Args:
            api_keys: APIKeys instance with credentials
        """
        self.secure_settings.save_api_keys(api_keys)
        logger.info("api_keys_saved_via_orchestrator", user=self.user_id, num_keys=len(api_keys.to_dict()))

    def list_configured_providers(self) -> list[str]:
        """
        Get list of providers with configured API keys

        Returns:
            List of provider names (e.g., ['openai', 'anthropic'])
        """
        return self.secure_settings.list_configured_providers()

    async def validate_api_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key by making a test request

        Args:
            provider: Provider name (openai, anthropic, google, etc.)
            api_key: API key to validate

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "message": str,
                "details": Optional[dict]
            }
        """
        return await self.secure_settings.validate_api_key(provider, api_key)

    def has_api_keys_configured(self) -> bool:
        """
        Check if any API keys are configured

        Returns:
            True if at least one API key is stored
        """
        return self.secure_settings.has_api_keys()

    # =============================================================================
    # User Preferences Management
    # =============================================================================

    def get_preferences(self) -> UserPreferences:
        """
        Get all user preferences

        Returns:
            UserPreferences instance with all settings
        """
        return self.preferences_manager.load_preferences()

    def get_block_preferences(self) -> BlockPreferences:
        """
        Get block-related preferences (auto-anchor settings)

        Returns:
            BlockPreferences instance
        """
        return self.preferences_manager.get_block_preferences()

    def update_block_preferences(
        self,
        individual_auto_anchor: Optional[bool] = None,
        individual_anchor_threshold: Optional[int] = None,
        group_auto_anchor: Optional[bool] = None,
        group_anchor_threshold: Optional[int] = None
    ) -> BlockPreferences:
        """
        Update block-related preferences

        Args:
            individual_auto_anchor: Enable/disable auto-anchor for individual chats
            individual_anchor_threshold: Blocks between anchors for individual chats
            group_auto_anchor: Enable/disable auto-anchor for group chats
            group_anchor_threshold: Blocks between anchors for group chats

        Returns:
            Updated BlockPreferences
        """
        prefs = self.preferences_manager.update_block_preferences(
            individual_auto_anchor=individual_auto_anchor,
            individual_anchor_threshold=individual_anchor_threshold,
            group_auto_anchor=group_auto_anchor,
            group_anchor_threshold=group_anchor_threshold
        )
        logger.info(
            "block_preferences_updated",
            user=self.user_id,
            individual_auto=individual_auto_anchor,
            individual_threshold=individual_anchor_threshold,
            group_auto=group_auto_anchor,
            group_threshold=group_anchor_threshold
        )

        # Sync preferences to all existing qubes' chain_state
        # Pass both individual and group settings
        if any([individual_anchor_threshold, individual_auto_anchor, group_auto_anchor, group_anchor_threshold]):
            from core.chain_state import ChainState

            # Update loaded qubes
            for qube_id, qube in self.qubes.items():
                # Update chain_state with all settings
                qube.chain_state.set_auto_anchor(
                    individual_enabled=individual_auto_anchor,
                    individual_threshold=individual_anchor_threshold,
                    group_enabled=group_auto_anchor,
                    group_threshold=group_anchor_threshold
                )

                # Update in-memory Qube instance (use individual settings for legacy fields)
                if individual_auto_anchor is not None:
                    qube.auto_anchor_enabled = individual_auto_anchor
                if individual_anchor_threshold is not None:
                    qube.auto_anchor_threshold = individual_anchor_threshold

                # If qube has an active session, update session threshold too
                if qube.current_session and individual_anchor_threshold is not None:
                    qube.current_session.auto_anchor_threshold = individual_anchor_threshold

                logger.debug(
                    "qube_anchor_settings_updated",
                    qube_id=qube_id[:8],
                    individual_enabled=individual_auto_anchor,
                    individual_threshold=individual_anchor_threshold,
                    group_enabled=group_auto_anchor,
                    group_threshold=group_anchor_threshold
                )

            # Also update chain_state for qubes not currently loaded
            qubes_dir = self.data_dir / "qubes"
            if qubes_dir.exists():
                for qube_dir in qubes_dir.iterdir():
                    if qube_dir.is_dir():
                        qube_id_from_dir = qube_dir.name.split('_')[-1]

                        # Skip if already updated above
                        if qube_id_from_dir in self.qubes:
                            continue

                        chain_state_file = qube_dir / "chain" / "chain_state.json"
                        if chain_state_file.exists():
                            try:
                                # Load chain_state for this qube with encryption
                                encryption_key = self._get_encryption_key(qube_dir)
                                if not encryption_key:
                                    logger.debug(f"Skipping unloaded qube {qube_id_from_dir} - no encryption key")
                                    continue

                                chain_dir = qube_dir / "chain"
                                chain_state = ChainState(chain_dir, encryption_key, qube_id_from_dir)

                                # Update with all anchor settings
                                chain_state.set_auto_anchor(
                                    individual_enabled=individual_auto_anchor,
                                    individual_threshold=individual_anchor_threshold,
                                    group_enabled=group_auto_anchor,
                                    group_threshold=group_anchor_threshold
                                )

                                logger.debug(
                                    "unloaded_qube_anchor_settings_updated",
                                    qube_id=qube_id_from_dir[:8],
                                    individual_enabled=individual_auto_anchor,
                                    individual_threshold=individual_anchor_threshold,
                                    group_enabled=group_auto_anchor,
                                    group_threshold=group_anchor_threshold
                                )
                            except Exception as e:
                                logger.warning(
                                    "failed_to_update_unloaded_qube",
                                    qube_dir=qube_dir.name,
                                    error=str(e)
                                )

        return prefs.blocks

    def reset_preferences(self) -> UserPreferences:
        """
        Reset all preferences to defaults

        Returns:
            Default UserPreferences
        """
        prefs = self.preferences_manager.reset_to_defaults()
        logger.info("preferences_reset", user=self.user_id)
        return prefs

    # =============================================================================
    # Private Helper Methods
    # =============================================================================

    def _derive_q_address(self, owner_pubkey: Optional[str]) -> Optional[str]:
        """
        Derive the owner's 'q' address (standard P2PKH) from their public key.

        Args:
            owner_pubkey: Compressed public key hex string (66 chars)

        Returns:
            BCH address with 'q' prefix, or None if pubkey is invalid
        """
        if not owner_pubkey:
            return None
        try:
            from crypto.bch_script import pubkey_to_p2pkh_address
            return pubkey_to_p2pkh_address(owner_pubkey, "mainnet", token_aware=False)
        except Exception:
            return None

    def _default_voice_for_model(self, ai_model: str) -> str:
        """
        Get default voice model for AI model

        Args:
            ai_model: AI model name

        Returns:
            Voice model ID
        """
        # OpenAI models default to OpenAI TTS
        if "gpt" in ai_model.lower() or "o1" in ai_model.lower() or "o3" in ai_model.lower() or "o4" in ai_model.lower():
            return "openai:alloy"

        # Anthropic models default to OpenAI TTS (no native TTS)
        if "claude" in ai_model.lower():
            return "openai:nova"

        # Google models default to OpenAI TTS (no native TTS)
        if "gemini" in ai_model.lower():
            return "openai:shimmer"

        # Ollama models default to Piper (local)
        if "llama" in ai_model.lower() or "qwen" in ai_model.lower() or "deepseek" in ai_model.lower():
            return "piper:en_US-lessac-medium"

        # Default
        return "openai:alloy"

    def _get_api_keys(self) -> Dict[str, str]:
        """
        Get API keys from secure settings merged with environment variables

        Priority: Secure settings > Environment variables

        Returns:
            Dictionary of provider -> api_key
        """
        api_keys = {}

        # First, load from environment variables as a fallback base
        import os

        if os.getenv("OPENAI_API_KEY"):
            api_keys["openai"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("ANTHROPIC_API_KEY"):
            api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
        if os.getenv("GOOGLE_API_KEY"):
            api_keys["google"] = os.getenv("GOOGLE_API_KEY")
        if os.getenv("DEEPSEEK_API_KEY"):
            api_keys["deepseek"] = os.getenv("DEEPSEEK_API_KEY")
        if os.getenv("PERPLEXITY_API_KEY"):
            api_keys["perplexity"] = os.getenv("PERPLEXITY_API_KEY")

        if api_keys:
            logger.debug("api_keys_loaded_from_environment", providers=list(api_keys.keys()))

        # Then, load from secure settings and override with saved keys
        if self.secure_settings.has_api_keys():
            try:
                stored_keys = self.secure_settings.load_api_keys()
                stored_dict = stored_keys.to_dict()

                # Merge: secure settings override environment variables
                api_keys.update(stored_dict)

                logger.info("api_keys_loaded_from_secure_settings", providers=list(stored_dict.keys()))

            except Exception as e:
                logger.warning("failed_to_load_secure_settings", error=str(e))
                # Continue with env vars only

        if api_keys:
            logger.info("final_api_keys_available", providers=list(api_keys.keys()))
        else:
            logger.debug("no_api_keys_available")

        return api_keys

    def _load_global_settings(self) -> Dict[str, Any]:
        """Load global user settings"""
        settings_file = self.data_dir / "settings.json"

        # Default settings
        default_settings = {
            "default_ai_model": "claude-sonnet-4.5",
            "default_voice": "openai:alloy",
            "max_session_blocks": 50,
            "auto_anchor_threshold": 100,
            "network_mode": "p2p",  # p2p or relay
            "log_level": "INFO"
        }

        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    content = f.read().strip()
                    if content:  # Only parse if file has content
                        return json.loads(content)
                    else:
                        # File is empty, write defaults
                        logger.warning("Settings file is empty, using defaults")
                        with open(settings_file, "w") as f:
                            json.dump(default_settings, f, indent=2)
                        return default_settings
            except json.JSONDecodeError as e:
                # Corrupted JSON, recreate with defaults
                logger.error(f"Corrupted settings file, recreating: {e}")
                with open(settings_file, "w") as f:
                    json.dump(default_settings, f, indent=2)
                return default_settings
        else:
            # Create new settings file
            with open(settings_file, "w") as f:
                json.dump(default_settings, f, indent=2)

            return default_settings

    async def _save_qube(self, qube: Qube, private_key: Any):
        """
        Persist Qube to storage

        Args:
            qube: Qube instance to save
            private_key: Private key to encrypt and save
        """
        qube_dir = self.data_dir / "qubes" / qube.storage_dir_name
        qube_dir.mkdir(parents=True, exist_ok=True)

        # Encrypt private key with master key
        encrypted_private_key = self._encrypt_private_key(private_key, self.master_key)

        # Prepare Qube data
        qube_data = {
            "qube_id": qube.qube_id,
            "encrypted_private_key": encrypted_private_key.hex(),
            "public_key": serialize_public_key(qube.public_key),
            "genesis_block": qube.genesis_block.to_dict(),
            "memory_chain_path": str(qube_dir / "memory"),
            "relationships_path": str(qube_dir / "relationships.json"),
            "settings": {}
        }

        # Save to disk (in chain/ folder to keep root clean)
        qube_metadata = qube_dir / "chain" / "qube_metadata.json"
        with open(qube_metadata, "w", encoding="utf-8") as f:
            json.dump(qube_data, f, indent=2)

        # Save encryption key encrypted by master key (for gui_bridge access)
        # This allows gui_bridge to access chain_state without loading full Qube
        self._save_encryption_key(qube_dir, qube.encryption_key)

        logger.debug("qube_saved", qube_id=qube.qube_id[:16] + "...")

    def _initialize_qube_skills(self, qube: Qube):
        """
        Initialize skills for a newly created Qube

        Skills are now stored in chain_state and initialized in Qube.__init__.
        This method just logs the initialization status.

        Args:
            qube: Qube instance to initialize skills for
        """
        try:
            # Qube already has skills_manager initialized in __init__
            # Just ensure skills data is loaded and get count for logging
            skills_data = qube.skills_manager.load_skills()

            logger.info(
                "qube_skills_initialized",
                qube_id=qube.qube_id[:16] + "...",
                skills_count=len(skills_data.get("skills", []))
            )
        except Exception as e:
            logger.warning(f"Failed to verify skills initialization for qube: {e}")
            # Don't fail qube creation if skills verification fails

    async def _load_qube_data(self, qube_id: str) -> Dict[str, Any]:
        """
        Load Qube data from storage

        Args:
            qube_id: Qube ID to load

        Returns:
            Qube data dictionary

        Raises:
            QubesError: If Qube not found
        """
        # Find Qube directory
        qubes_dir = self.data_dir / "qubes"

        for qube_dir in qubes_dir.iterdir():
            if qube_dir.is_dir():
                # Try new location first (chain/qube_metadata.json)
                qube_metadata = qube_dir / "chain" / "qube_metadata.json"
                if not qube_metadata.exists():
                    # Fallback to old location for backwards compatibility
                    qube_metadata = qube_dir / "qube.json"

                if qube_metadata.exists():
                    with open(qube_metadata, "r", encoding="utf-8") as f:
                        qube_data = json.load(f)
                        if qube_data["qube_id"] == qube_id:
                            return qube_data

        raise QubesError(
            f"Qube not found: {qube_id}",
            context={"qube_id": qube_id}
        )

    def _encrypt_private_key(self, private_key: Any, master_key: bytes) -> bytes:
        """Encrypt private key with master key"""
        from crypto.encryption import encrypt_data

        # Serialize private key
        private_key_bytes = serialize_private_key(private_key)

        # Encrypt with master key
        encrypted = encrypt_data(private_key_bytes, master_key)

        return encrypted

    def _decrypt_private_key(self, encrypted_key_hex: str, master_key: bytes) -> Any:
        """Decrypt private key with master key"""
        from crypto.encryption import decrypt_data

        # Decrypt
        encrypted_key = bytes.fromhex(encrypted_key_hex)
        decrypted = decrypt_data(encrypted_key, master_key)

        # Deserialize private key
        private_key = deserialize_private_key(decrypted)

        return private_key

    def _save_encryption_key(self, qube_dir: Path, encryption_key: bytes) -> None:
        """
        Save qube encryption key encrypted by master key.

        This allows gui_bridge to access chain_state without loading the full Qube.
        The key file is stored at {qube_dir}/chain/encryption_key.enc

        Args:
            qube_dir: Qube data directory
            encryption_key: 32-byte encryption key to save
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets as crypto_secrets

        if not self.master_key:
            logger.warning("Cannot save encryption key - master key not set")
            return

        chain_dir = qube_dir / "chain"
        chain_dir.mkdir(parents=True, exist_ok=True)
        key_file = chain_dir / "encryption_key.enc"

        try:
            aesgcm = AESGCM(self.master_key)
            nonce = crypto_secrets.token_bytes(12)
            ciphertext = aesgcm.encrypt(nonce, encryption_key, None)

            with open(key_file, 'w') as f:
                json.dump({
                    "nonce": nonce.hex(),
                    "ciphertext": ciphertext.hex(),
                    "algorithm": "AES-256-GCM",
                    "version": "1.0"
                }, f, indent=2)

            logger.debug("encryption_key_saved", key_file=str(key_file))

        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")
            raise

    def _get_encryption_key(self, qube_dir: Path) -> Optional[bytes]:
        """
        Get the encryption key for a qube.

        The qube's encryption key is stored encrypted by the master key in:
        {qube_dir}/chain/encryption_key.enc

        Args:
            qube_dir: Qube data directory

        Returns:
            Encryption key bytes, or None if not available
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not self.master_key:
            logger.warning("Cannot get qube encryption key - master key not set")
            return None

        key_file = qube_dir / "chain" / "encryption_key.enc"
        if not key_file.exists():
            # Legacy qube without encrypted key file - use master key directly
            # (for backward compatibility during migration)
            logger.debug("No encryption_key.enc found, using master key fallback")
            return self.master_key

        try:
            with open(key_file, 'r') as f:
                enc_data = json.load(f)

            nonce = bytes.fromhex(enc_data["nonce"])
            ciphertext = bytes.fromhex(enc_data["ciphertext"])

            aesgcm = AESGCM(self.master_key)
            qube_key = aesgcm.decrypt(nonce, ciphertext, None)
            return qube_key

        except Exception as e:
            logger.error(f"Failed to decrypt qube encryption key: {e}")
            return None

    # =============================================================================
    # Multi-Qube Conversation Management
    # =============================================================================

    async def start_multi_qube_conversation(
        self,
        qube_ids: List[str],
        initial_prompt: str,
        conversation_mode: str = "open_discussion"
    ) -> Dict[str, Any]:
        """
        Start a multi-Qube conversation

        Args:
            qube_ids: List of Qube IDs to include in conversation
            initial_prompt: User's initial message to start the conversation
            conversation_mode: "open_discussion", "round_robin", or "debate"

        Returns:
            Conversation info with first response

        Raises:
            QubesError: If any Qubes not loaded or conversation start fails
        """
        logger.info(
            "starting_multi_qube_conversation",
            qube_count=len(qube_ids),
            mode=conversation_mode
        )

        # Validate all Qubes are loaded
        missing_qubes = [qid for qid in qube_ids if qid not in self.qubes]
        if missing_qubes:
            raise QubesError(
                f"Cannot start conversation - {len(missing_qubes)} Qube(s) not loaded",
                context={"missing_qubes": missing_qubes}
            )

        # Get Qube instances
        participating_qubes = [self.qubes[qid] for qid in qube_ids]

        # Create conversation
        conversation = MultiQubeConversation(
            participating_qubes=participating_qubes,
            user_id=self.user_id,
            conversation_mode=conversation_mode
        )

        # Store conversation
        self.active_conversations[conversation.conversation_id] = conversation

        # Start conversation with user's prompt
        first_response = await conversation.start_conversation(initial_prompt)

        logger.info(
            "multi_qube_conversation_started",
            conversation_id=conversation.conversation_id,
            first_speaker=first_response["speaker_name"]
        )

        return {
            "conversation_id": conversation.conversation_id,
            "participants": [
                {
                    "qube_id": q.qube_id,
                    "name": q.name,
                    "voice_model": getattr(q.genesis_block, 'voice_model', 'openai:alloy')
                }
                for q in participating_qubes
            ],
            "mode": conversation_mode,
            "first_response": first_response
        }

    async def get_next_speaker(
        self,
        conversation_id: str
    ) -> Dict[str, str]:
        """
        Get the next speaker info before processing the response

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with speaker_id and speaker_name

        Raises:
            QubesError: If conversation not found
        """
        if conversation_id not in self.active_conversations:
            raise QubesError(
                f"Conversation not found: {conversation_id}",
                context={"conversation_id": conversation_id}
            )

        conversation = self.active_conversations[conversation_id]

        logger.info(
            "getting_next_speaker",
            conversation_id=conversation_id
        )

        speaker_info = await conversation.get_next_speaker_info()

        logger.info(
            "next_speaker_determined",
            conversation_id=conversation_id,
            speaker_id=speaker_info["speaker_id"],
            speaker_name=speaker_info["speaker_name"]
        )

        return speaker_info

    async def continue_multi_qube_conversation(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Continue a multi-Qube conversation (get next turn)

        Args:
            conversation_id: Conversation ID to continue

        Returns:
            Next response dict with speaker info and message

        Raises:
            QubesError: If conversation not found
        """
        if conversation_id not in self.active_conversations:
            raise QubesError(
                f"Conversation not found: {conversation_id}",
                context={"conversation_id": conversation_id}
            )

        conversation = self.active_conversations[conversation_id]

        logger.info(
            "continuing_conversation",
            conversation_id=conversation_id,
            turn_number=conversation.turn_number + 1
        )

        response = await conversation.continue_conversation()

        return response

    async def inject_user_message_to_conversation(
        self,
        conversation_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Inject a user message into an active multi-Qube conversation

        This allows the user to participate in the conversation at any time,
        taking precedence over the scheduled Qube responses.

        Args:
            conversation_id: Conversation ID to inject message into
            user_message: The user's message

        Returns:
            Dict with user message info and Qube response

        Raises:
            QubesError: If conversation not found
        """
        if conversation_id not in self.active_conversations:
            raise QubesError(
                f"Conversation not found: {conversation_id}",
                context={"conversation_id": conversation_id}
            )

        conversation = self.active_conversations[conversation_id]

        logger.info(
            "injecting_user_message_to_conversation",
            conversation_id=conversation_id,
            message_length=len(user_message)
        )

        result = await conversation.inject_user_message(user_message)

        logger.info(
            "user_message_injected_to_conversation",
            conversation_id=conversation_id,
            user_turn=result["user_message"]["turn_number"],
            response_turn=result["qube_response"]["turn_number"]
        )

        return result

    async def end_multi_qube_conversation(
        self,
        conversation_id: str,
        anchor: bool = True
    ) -> Dict[str, Any]:
        """
        End a multi-Qube conversation

        Args:
            conversation_id: Conversation ID to end
            anchor: Whether to anchor session blocks to permanent chains

        Returns:
            Conversation summary

        Raises:
            QubesError: If conversation not found
        """
        if conversation_id not in self.active_conversations:
            raise QubesError(
                f"Conversation not found: {conversation_id}",
                context={"conversation_id": conversation_id}
            )

        conversation = self.active_conversations[conversation_id]

        logger.info(
            "ending_conversation",
            conversation_id=conversation_id,
            anchor=anchor
        )

        summary = await conversation.end_conversation(anchor=anchor)

        # Remove from active conversations
        del self.active_conversations[conversation_id]

        logger.info(
            "conversation_ended",
            conversation_id=conversation_id,
            total_turns=summary["total_turns"]
        )

        return summary

    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get statistics for an active conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            Participation statistics

        Raises:
            QubesError: If conversation not found
        """
        if conversation_id not in self.active_conversations:
            raise QubesError(
                f"Conversation not found: {conversation_id}",
                context={"conversation_id": conversation_id}
            )

        conversation = self.active_conversations[conversation_id]
        return conversation.get_participation_stats()

    # ===== Wallet Security Methods =====

    def save_owner_key(self, nft_address: str, owner_wif: str) -> bool:
        """
        Save encrypted owner WIF for an NFT address.
        Works for all qubes at that address since they share the same owner key.

        Args:
            nft_address: The NFT/CashTokens address
            owner_wif: Owner's private key in WIF format

        Returns:
            True on success
        """
        config = self.secure_settings.load_wallet_security()
        config.owner_keys[nft_address] = owner_wif
        self.secure_settings.save_wallet_security(config)
        logger.info("owner_key_saved", nft_address=nft_address[:20] + "...")
        return True

    def delete_owner_key(self, nft_address: str) -> bool:
        """
        Delete stored owner WIF for an NFT address.

        Args:
            nft_address: The NFT/CashTokens address

        Returns:
            True on success
        """
        config = self.secure_settings.load_wallet_security()
        if nft_address in config.owner_keys:
            del config.owner_keys[nft_address]
            self.secure_settings.save_wallet_security(config)
            logger.info("owner_key_deleted", nft_address=nft_address[:20] + "...")
        return True

    def get_wallet_security(self) -> Dict[str, Any]:
        """
        Get wallet security config (WIFs redacted, shows which addresses have keys).

        Returns:
            Dictionary with addresses_with_keys and whitelists
        """
        config = self.secure_settings.load_wallet_security()
        return {
            'addresses_with_keys': list(config.owner_keys.keys()),  # Just addresses, not WIFs
            'whitelists': config.whitelists  # qube_id -> [addresses]
        }

    def get_owner_wif_for_qube(self, qube_id: str) -> Optional[str]:
        """
        Get stored owner WIF for a Qube by looking up its NFT address (internal use).

        Args:
            qube_id: The Qube ID

        Returns:
            WIF string if found, None otherwise
        """
        # Get qube's NFT address (z address) from nft_metadata.json
        if qube_id not in self.qubes:
            return None
        qube = self.qubes[qube_id]

        # The NFT address (z address) is stored in nft_metadata.json as recipient_address
        nft_metadata_path = Path(qube.data_dir) / "chain" / "nft_metadata.json"
        nft_address = None

        if nft_metadata_path.exists():
            try:
                import json
                with open(nft_metadata_path, 'r') as f:
                    nft_metadata = json.load(f)
                nft_address = nft_metadata.get("recipient_address")
            except Exception as e:
                logger.warning("failed_to_read_nft_metadata", error=str(e))

        if not nft_address:
            return None

        config = self.secure_settings.load_wallet_security()
        return config.get_key_for_address(nft_address)

    def update_whitelist(self, qube_id: str, whitelist: List[str]) -> bool:
        """
        Update auto-send whitelist for a Qube.

        Args:
            qube_id: The Qube ID
            whitelist: List of addresses that can receive auto-approved sends

        Returns:
            True on success
        """
        config = self.secure_settings.load_wallet_security()
        config.whitelists[qube_id] = whitelist
        self.secure_settings.save_wallet_security(config)
        logger.info("whitelist_updated", qube_id=qube_id[:16] + "...", count=len(whitelist))
        return True

    def is_address_whitelisted(self, qube_id: str, address: str) -> bool:
        """
        Check if address is whitelisted for auto-send from a Qube.

        Args:
            qube_id: The Qube ID
            address: Address to check

        Returns:
            True if whitelisted
        """
        config = self.secure_settings.load_wallet_security()
        return config.is_whitelisted(qube_id, address)
