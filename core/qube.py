"""
Qube - Sovereign AI Agent with Cryptographic Identity

Updated to match documentation exactly
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import ec
from datetime import datetime

from core.block import Block, create_genesis_block, create_message_block
from core.memory_chain import MemoryChain
from core.session import Session
from core.chain_state import ChainState
from core.exceptions import QubesError
from crypto.keys import generate_key_pair, derive_qube_id, serialize_public_key
from crypto.encryption import generate_encryption_key
from utils.logging import get_logger, set_qube_id
from monitoring.metrics import active_qubes
from shared_memory import (
    PermissionManager, PermissionLevel,
    CollaborativeSession,
    MemoryMarket,
    SharedMemoryCache
)
from relationships.social import SocialDynamicsManager
from core.game_manager import GameManager

logger = get_logger(__name__)


class Qube:
    """
    Sovereign AI Agent

    From documentation - matches structure exactly
    """

    def __init__(
        self,
        qube_id: str,
        private_key: ec.EllipticCurvePrivateKey,
        public_key: ec.EllipticCurvePublicKey,
        genesis_block: Block,
        data_dir: Path,
        user_name: str,
        anchor_interval: int = 100,
        encryption_key: Optional[bytes] = None
    ):
        """
        Initialize Qube

        Args:
            qube_id: 8-character Qube ID
            private_key: ECDSA private key
            public_key: ECDSA public key
            genesis_block: Genesis block (block 0)
            data_dir: Base data directory (Qubes/data/users/{user_name}/qubes/)
            user_name: Username owning this Qube
            anchor_interval: Create anchor every N blocks
            encryption_key: Optional encryption key for chain_state (if None, generates new)
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.public_key = public_key
        self.user_name = user_name

        # Set context for logging
        set_qube_id(qube_id)

        # Extract qube name from genesis block FIRST
        if isinstance(genesis_block, dict):
            qube_name = genesis_block["qube_name"]
        else:
            qube_name = genesis_block.qube_name

        self.name = qube_name

        # Create qube-specific data directory BEFORE initializing MemoryChain
        qube_dir_name = f"{qube_name}_{qube_id}"
        qube_data_dir = data_dir / qube_dir_name
        self.data_dir = qube_data_dir  # Store for later use

        # Create directory structure first
        qube_data_dir.mkdir(parents=True, exist_ok=True)
        (qube_data_dir / "chain").mkdir(exist_ok=True)
        (qube_data_dir / "audio").mkdir(exist_ok=True)
        (qube_data_dir / "images").mkdir(exist_ok=True)
        (qube_data_dir / "blocks" / "permanent").mkdir(parents=True, exist_ok=True)
        (qube_data_dir / "blocks" / "session").mkdir(parents=True, exist_ok=True)

        # Initialize memory chain with qube-specific directory
        self.memory_chain = MemoryChain(
            qube_id=qube_id,
            private_key=private_key,
            public_key=public_key,
            data_dir=qube_data_dir,  # Use qube-specific directory
            anchor_interval=anchor_interval
        )

        # Handle dict or object genesis_block
        if isinstance(genesis_block, dict):
            # Keep reference to original dict for modifications
            from types import SimpleNamespace
            from crypto.signing import hash_block, sign_block

            genesis_dict = genesis_block  # Keep dict reference

            # Hash the block first
            if "block_hash" not in genesis_dict or not genesis_dict["block_hash"]:
                genesis_dict["block_hash"] = hash_block(genesis_dict)

            # Sign the genesis block if not already signed
            if "signature" not in genesis_dict or not genesis_dict["signature"]:
                genesis_dict["signature"] = sign_block(genesis_dict, private_key)

            # Convert to namespace object for attribute access
            genesis_obj = SimpleNamespace(**genesis_dict)
            # Make to_dict return current state of the namespace, not the original dict
            genesis_obj.to_dict = lambda obj=genesis_obj: {k: v for k, v in vars(obj).items() if not k.startswith('_') and k != 'to_dict'}

            # Add timestamp as alias for birth_timestamp (for memory_chain compatibility)
            if hasattr(genesis_obj, 'birth_timestamp') and not hasattr(genesis_obj, 'timestamp'):
                genesis_obj.timestamp = genesis_obj.birth_timestamp

            self.genesis_block = genesis_obj

            # Check if genesis block already exists (loading from storage)
            from pathlib import Path
            permanent_dir = qube_data_dir / "blocks" / "permanent"

            block_type_str = genesis_obj.block_type if isinstance(genesis_obj.block_type, str) else genesis_obj.block_type
            filename = f"{genesis_obj.block_number}_{block_type_str}_{genesis_obj.timestamp}.json"
            genesis_file = permanent_dir / filename

            # Only save and add to chain if this is a NEW Qube (file doesn't exist yet)
            is_new_qube = not genesis_file.exists()
            if is_new_qube:
                import json
                with open(genesis_file, 'w') as f:
                    json.dump(genesis_dict, f, indent=2)

                # Add to memory chain (just updates index)
                self.memory_chain.add_block(genesis_obj, skip_signature=True)
            else:
                # Loading existing Qube - genesis already in chain index from _load_block_index()
                logger.debug("genesis_block_already_exists", qube_id=qube_id, file=str(genesis_file))

        else:
            # Object-based genesis block
            if not genesis_block.signature:
                from crypto.signing import sign_block
                genesis_block.signature = sign_block(genesis_block.to_dict(), private_key)

            self.genesis_block = genesis_block

            # Check if genesis file exists (only add to chain if new)
            from pathlib import Path
            permanent_dir = qube_data_dir / "blocks" / "permanent"
            block_type_str = genesis_block.block_type if isinstance(genesis_block.block_type, str) else genesis_block.block_type.value
            filename = f"{genesis_block.block_number}_{block_type_str}_{genesis_block.timestamp}.json"
            genesis_file = permanent_dir / filename

            is_new_qube = not genesis_file.exists()
            if is_new_qube:
                self.memory_chain.add_block(genesis_block, skip_signature=True)

                # Save genesis block to permanent storage (caller is responsible per add_block() contract)
                import json
                with open(genesis_file, 'w') as f:
                    json.dump(genesis_block.to_dict(), f, indent=2)

        # Storage is now handled directly by JSON files in blocks/permanent/
        # No separate storage layer needed

        # Save genesis.json in chain/ folder (for backward compatibility and easy access)
        genesis_path = qube_data_dir / "chain" / "genesis.json"
        import json
        with open(genesis_path, 'w') as f:
            json.dump(self.genesis_block.to_dict() if hasattr(self.genesis_block, 'to_dict') else genesis_dict, f, indent=2)

        # =====================================================================
        # ENCRYPTION KEY SETUP (must happen before ChainState init)
        # =====================================================================

        # Use provided encryption key or generate new one
        # Note: UserOrchestrator handles encrypted storage of the key
        if encryption_key:
            self.encryption_key = encryption_key
        else:
            # Generate new encryption key for new qubes
            self.encryption_key = generate_encryption_key()

        # =====================================================================
        # CHAIN STATE INITIALIZATION (with encryption)
        # =====================================================================

        # Initialize chain state in chain/ folder with encryption
        # Pass genesis_block so new qubes get proper initial values (tts_enabled, voice_model, etc.)
        chain_dir = qube_data_dir / "chain"
        genesis_dict = self.genesis_block.to_dict() if hasattr(self.genesis_block, 'to_dict') else (genesis_block if isinstance(genesis_block, dict) else None)
        self.chain_state = ChainState(
            data_dir=chain_dir,
            encryption_key=self.encryption_key,
            qube_id=qube_id,
            genesis_block=genesis_dict
        )

        # Update chain state with genesis block (only if new qube)
        if is_new_qube:
            self.chain_state.update_chain(
                chain_length=1,
                last_block_number=0,
                last_block_hash=self.genesis_block.block_hash
            )
            self.chain_state.increment_block_count("GENESIS")
        else:
            # For existing qubes, rebuild block_counts if stale/zero
            # This fixes qubes created before chain_state tracking was added
            self.chain_state.rebuild_block_counts(self.memory_chain)

        # =====================================================================
        # RELATIONSHIP STORAGE (migrates from file if needed)
        # =====================================================================

        from relationships.relationship import RelationshipStorage

        old_relationships_file = qube_data_dir / "relationships" / "relationships.json"
        if old_relationships_file.exists():
            # Migrate from old file-based storage to chain_state
            relationship_storage = RelationshipStorage.migrate_from_file(
                self.chain_state,
                qube_data_dir
            )
        else:
            # Normal initialization from chain_state
            relationship_storage = RelationshipStorage(self.chain_state)

        # =====================================================================
        # SKILLS MANAGER (migrates from files if needed)
        # =====================================================================

        from utils.skills_manager import SkillsManager

        old_skills_file = qube_data_dir / "skills" / "skills.json"
        if old_skills_file.exists():
            # Migrate from old file-based storage to chain_state
            self.skills_manager = SkillsManager.migrate_from_files(
                self.chain_state,
                qube_data_dir
            )
        else:
            # Normal initialization from chain_state
            self.skills_manager = SkillsManager(self.chain_state)

        # =====================================================================
        # WALLET TRANSACTION MANAGER (migrates from files if needed)
        # =====================================================================

        from blockchain.wallet_tx import WalletTransactionManager

        old_pending_file = qube_data_dir / "pending_transactions.json"
        old_history_file = qube_data_dir / "transaction_history.json"
        old_balance_file = qube_data_dir / "balance_cache.json"

        if old_pending_file.exists() or old_history_file.exists() or old_balance_file.exists():
            # Migrate from old file-based storage to chain_state
            self.wallet_manager = WalletTransactionManager.migrate_from_files(
                self,
                self.chain_state,
                qube_data_dir
            )
        else:
            # Normal initialization from chain_state
            self.wallet_manager = WalletTransactionManager(self, self.chain_state)

        # =====================================================================
        # OWNER INFO MIGRATION (from legacy OwnerInfoManager files)
        # =====================================================================

        old_owner_info_file = qube_data_dir / "owner_info" / "owner_info.json"
        if old_owner_info_file.exists() and not self.chain_state.state.get("owner_info"):
            # Migrate from old OwnerInfoManager file to chain_state
            try:
                import json
                from crypto.encryption import decrypt_block_data

                with open(old_owner_info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if file is encrypted
                if "ciphertext" in data:
                    legacy_data = decrypt_block_data(data, self.encryption_key)
                else:
                    legacy_data = data

                # Migrate to chain_state
                self.chain_state.migrate_owner_info_from_file(legacy_data)
                logger.info("owner_info_migrated_to_chain_state", qube_id=qube_id)

                # Optionally rename old file to indicate migration
                backup_file = old_owner_info_file.with_suffix('.json.migrated')
                old_owner_info_file.rename(backup_file)
                logger.info("owner_info_old_file_renamed", old=str(old_owner_info_file), new=str(backup_file))

            except Exception as e:
                logger.error("owner_info_migration_failed", error=str(e), qube_id=qube_id)

        # =====================================================================
        # CLEARANCE CONFIG MIGRATION (from legacy clearance/config.json)
        # =====================================================================

        old_clearance_file = qube_data_dir / "clearance" / "config.json"
        if old_clearance_file.exists() and not self.chain_state.state.get("clearance"):
            # Migrate from old file-based storage to chain_state
            try:
                import json

                with open(old_clearance_file, 'r', encoding='utf-8') as f:
                    legacy_data = json.load(f)

                # Migrate to chain_state
                self.chain_state.migrate_clearance_from_file(legacy_data)
                logger.info("clearance_config_migrated_to_chain_state", qube_id=qube_id)

                # Rename old file to indicate migration
                backup_file = old_clearance_file.with_suffix('.json.migrated')
                old_clearance_file.rename(backup_file)
                logger.info("clearance_config_old_file_renamed", old=str(old_clearance_file), new=str(backup_file))

            except Exception as e:
                logger.error("clearance_config_migration_failed", error=str(e), qube_id=qube_id)

        # =====================================================================
        # SESSION MANAGEMENT
        # =====================================================================

        self.current_session: Optional[Session] = None
        # Note: auto_anchor_enabled and auto_anchor_threshold are now properties
        # that read dynamically from chain_state (see below)

        # =====================================================================
        # RELATIONSHIP MANAGEMENT
        # =====================================================================

        # SocialDynamicsManager wraps RelationshipStorage
        trust_profile = None  # Could be set from genesis block or user preferences
        self.relationships = SocialDynamicsManager(
            relationship_storage=relationship_storage,
            trust_profile=trust_profile,
            qube=self
        )

        # Game management (chess, etc.)
        self.game_manager = GameManager(self)

        # AI configuration
        # Prefer runtime.current_model from chain_state (reflects model switches)
        # Fall back to genesis model if chain_state doesn't have a current model
        runtime_model = self.chain_state.state.get("runtime", {}).get("current_model")
        self.current_ai_model = runtime_model or self.genesis_block.ai_model
        self.api_keys: Dict[str, str] = {}  # Populated after creation
        self.reasoner = None  # Initialized with init_ai()
        self.tool_registry = None  # Initialized with init_ai()
        self.semantic_search = None  # Initialized in background thread

        # Decision Intelligence configuration
        from config.user_preferences import UserPreferencesManager
        # User preferences are stored at data/users/{user_name}/preferences.json
        # qube_data_dir is data/users/{user_name}/qubes/{qube_name}_{qube_id}/
        # So we need to go up 1 level to get to the user directory
        user_prefs_dir = qube_data_dir.parent.parent
        prefs_manager = UserPreferencesManager(user_prefs_dir)
        self.decision_config = prefs_manager.get_decision_config()

        # Audio configuration
        self.audio_manager = None  # Initialized with init_audio()

        # Increment active qubes metric
        active_qubes.inc()

        # Store directory name for session and other file operations
        self._qube_dir_name = qube_dir_name

        # Initialize shared memory systems
        self._init_shared_memory(qube_data_dir)

        # Initialize semantic search in background (don't block startup)
        self._init_semantic_search_background()

        logger.info(
            "qube_initialized",
            qube_id=qube_id,
            name=self.genesis_block.qube_name,
            ai_model=self.genesis_block.ai_model
        )

    def _init_shared_memory(self, qube_data_dir: Path):
        """Initialize shared memory systems"""
        # Permission manager
        permissions_dir = qube_data_dir / "shared_memory" / "permissions"
        self.permission_manager = PermissionManager(permissions_dir)

        # Collaborative session manager
        sessions_dir = qube_data_dir / "shared_memory" / "sessions"
        self.collaborative_session = CollaborativeSession(sessions_dir)

        # Memory market
        market_dir = qube_data_dir / "shared_memory" / "market"
        self.memory_market = MemoryMarket(market_dir)

        # Shared memory cache
        cache_dir = qube_data_dir / "shared_memory" / "cache"
        self.shared_cache = SharedMemoryCache(cache_dir, max_size_mb=500)

        logger.debug(
            "shared_memory_initialized",
            permissions_dir=str(permissions_dir),
            sessions_dir=str(sessions_dir),
            market_dir=str(market_dir),
            cache_dir=str(cache_dir)
        )

    def _init_semantic_search_background(self):
        """
        Initialize semantic search in a background thread.

        This loads the sentence-transformers model and FAISS index without
        blocking Qube startup. If initialization fails, semantic search
        gracefully falls back to keyword-only search.
        """
        import threading

        def init_search():
            try:
                from ai.semantic_search import SemanticSearch

                # Initialize semantic search with storage in chain directory
                self.semantic_search = SemanticSearch(
                    qube_id=self.qube_id,
                    storage_dir=self.data_dir / "chain"
                )

                # Validate index integrity - compare indexed count vs actual
                indexed_count = len(self.semantic_search.block_ids)
                actual_count = self.memory_chain.get_chain_length()

                if indexed_count != actual_count:
                    logger.info(
                        "semantic_index_mismatch_rebuilding",
                        qube_id=self.qube_id,
                        indexed=indexed_count,
                        actual=actual_count
                    )
                    # Get all blocks and rebuild index
                    blocks = []
                    for block_num in range(actual_count):
                        try:
                            block = self.memory_chain.get_block(block_num)
                            if block:
                                blocks.append(block)
                        except Exception:
                            continue
                    self.semantic_search.rebuild_index(blocks)

                logger.info(
                    "semantic_search_ready",
                    qube_id=self.qube_id,
                    indexed_blocks=len(self.semantic_search.block_ids)
                )

            except Exception as e:
                logger.warning(
                    "semantic_search_init_failed",
                    qube_id=self.qube_id,
                    error=str(e)
                )
                # Leave semantic_search as None - fallback will be used
                self.semantic_search = None

        # Start initialization in background thread
        thread = threading.Thread(target=init_search, daemon=True, name=f"semantic-init-{self.qube_id}")
        thread.start()

    @property
    def storage_dir_name(self) -> str:
        """Get the storage directory name (name_id format)"""
        return self._qube_dir_name

    @property
    def avatar_ipfs_cid(self) -> str:
        """
        Get avatar IPFS CID from genesis block

        Returns:
            IPFS CID or empty string if not available
        """
        if hasattr(self.genesis_block, 'avatar') and isinstance(self.genesis_block.avatar, dict):
            return self.genesis_block.avatar.get('ipfs_cid', '')
        return ''

    @property
    def events(self):
        """
        Get the event bus for event-driven state management.

        Use this to emit events that update chain_state:

            from core.events import Events
            qube.events.emit(Events.TRANSACTION_SENT, {...})

        Returns:
            ChainStateEventBus instance
        """
        return self.chain_state.events

    @property
    def auto_anchor_enabled(self) -> bool:
        """
        Check if auto-anchor is enabled (reads dynamically from chain_state).

        This allows settings changes in the GUI to take effect immediately
        without needing to reload the Qube.
        """
        return self.chain_state.is_auto_anchor_enabled()

    @property
    def auto_anchor_threshold(self) -> int:
        """
        Get auto-anchor threshold (reads dynamically from chain_state).

        This allows settings changes in the GUI to take effect immediately
        without needing to reload the Qube.
        """
        return self.chain_state.get_auto_anchor_threshold()

    @classmethod
    def create_new(
        cls,
        qube_name: str,
        creator: str,
        genesis_prompt: str,
        ai_model: str,
        voice_model: str,
        data_dir: Path,
        user_name: str,
        avatar: Optional[Dict[str, Any]] = None,
        favorite_color: str = "#4A90E2",
        home_blockchain: str = "bitcoin_cash",
        genesis_prompt_encrypted: bool = False,
        capabilities: Optional[Dict[str, bool]] = None,
        default_trust_level: int = 50,
        nft_contract: Optional[str] = None,
        nft_token_id: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None,
        **extra_genesis_data
    ) -> "Qube":
        """
        Create new Qube from scratch

        Matches documentation genesis block structure exactly

        Args:
            qube_name: Qube name (e.g., "Athena", "BitcoinBob")
            creator: Creator username/ID
            genesis_prompt: Genesis prompt defining the Qube's personality/purpose
            ai_model: AI model name (e.g., "gpt-4o", "claude-sonnet-4")
            voice_model: Voice model ID (e.g., "elevenlabs-...")
            data_dir: Base data directory (Qubes/data/users/{user_name}/qubes/)
            user_name: Username owning this Qube
            avatar: Avatar metadata dict with keys:
                    - source: "generated" | "uploaded" | "nft"
                    - ipfs_cid: IPFS CID if stored on IPFS
                    - generation_model: Model used to generate (if applicable)
                    - file_format: "png" | "jpg" | "gif"
                    - dimensions: "1024x1024" etc.
            favorite_color: Favorite color hex (default: "#4A90E2")
            home_blockchain: Home blockchain (default: "bitcoin_cash", BCH only for now)
            genesis_prompt_encrypted: Whether genesis prompt is encrypted (default: False)
            capabilities: Capability flags dict:
                         - web_search: bool
                         - image_generation: bool
                         - image_processing: bool
                         - tts: bool (text-to-speech)
                         - stt: bool (speech-to-text)
                         - code_execution: bool
            default_trust_level: Default trust level 0-100 (default: 50)
            nft_contract: NFT smart contract address (optional, for NFT-based Qubes)
            nft_token_id: NFT token ID (optional, for NFT-based Qubes)
            api_keys: API keys for AI providers (optional, can be set later via init_ai()):
                     {"openai": "sk-...", "anthropic": "sk-ant-...", ...}
            **extra_genesis_data: Additional genesis data for future extensibility

        Returns:
            New Qube instance with cryptographic identity and genesis block
        """
        # Generate cryptographic identity
        private_key, public_key = generate_key_pair()
        qube_id = derive_qube_id(public_key)
        public_key_hex = serialize_public_key(public_key)

        # Default avatar if not provided
        if avatar is None:
            avatar = {
                "source": "generated",
                "ipfs_cid": None,
                "generation_model": None,
                "file_format": "png",
                "dimensions": "1024x1024"
            }

        # Create genesis block matching documentation
        genesis_block = create_genesis_block(
            qube_id=qube_id,
            qube_name=qube_name,
            creator=creator,
            public_key=public_key_hex,
            genesis_prompt=genesis_prompt,
            ai_model=ai_model,
            voice_model=voice_model,
            avatar=avatar,
            favorite_color=favorite_color,
            home_blockchain=home_blockchain,
            genesis_prompt_encrypted=genesis_prompt_encrypted,
            capabilities=capabilities,
            default_trust_level=default_trust_level,
            nft_contract=nft_contract,
            nft_token_id=nft_token_id
        )

        logger.info("qube_created", qube_id=qube_id, name=qube_name, ai_model=ai_model)

        # Create Qube instance
        qube = cls(
            qube_id=qube_id,
            private_key=private_key,
            public_key=public_key,
            genesis_block=genesis_block,
            data_dir=data_dir,
            user_name=user_name
        )

        # Initialize AI if API keys provided
        if api_keys:
            qube.init_ai(api_keys)
            logger.info("qube_ai_initialized_at_creation", qube_id=qube_id, providers=list(api_keys.keys()))

        return qube

    @classmethod
    def from_storage(
        cls,
        qube_data: Dict[str, Any],
        private_key: ec.EllipticCurvePrivateKey,
        user_name: str,
        encryption_key: Optional[bytes] = None,
        **kwargs
    ) -> "Qube":
        """
        Load Qube from storage data

        Args:
            qube_data: Qube data dict with keys:
                - qube_id: str
                - public_key: str (hex)
                - genesis_block: dict
                - memory_chain_path: str
                - relationships_path: str
                - settings: dict
            private_key: Decrypted private key
            user_name: Username owning this Qube
            encryption_key: Optional encryption key for chain_state
            **kwargs: Additional args (ignored for compatibility)

        Returns:
            Qube instance
        """
        from crypto.keys import deserialize_public_key

        # Deserialize public key
        public_key = deserialize_public_key(qube_data["public_key"])

        # Get data directory from memory_chain_path
        # memory_chain_path is like: data/users/{user}/qubes/{name_id}/memory
        # We want: data/users/{user}/qubes (the parent of {name_id})
        memory_chain_path = Path(qube_data["memory_chain_path"])
        data_dir = memory_chain_path.parent.parent  # Go up two levels: memory -> {name_id} -> qubes

        # Create Qube instance
        qube = cls(
            qube_id=qube_data["qube_id"],
            private_key=private_key,
            public_key=public_key,
            genesis_block=qube_data["genesis_block"],
            data_dir=data_dir,
            user_name=user_name,
            encryption_key=encryption_key
        )

        # Try to recover any existing session
        recovered_session = Session.recover_session(qube)
        if recovered_session:
            qube.current_session = recovered_session
            logger.info("session_recovered_on_load", qube_id=qube_data["qube_id"][:16] + "...", blocks=len(recovered_session.session_blocks))

        logger.info("qube_loaded_from_storage", qube_id=qube_data["qube_id"][:16] + "...")

        return qube

    def start_session(self) -> Session:
        """
        Start new session with file lock protection

        Prevents race condition when multiple processes access same Qube
        """
        from utils.file_lock import qube_session_lock

        with qube_session_lock(self.data_dir):
            # Check if session already exists (another process may have created it)
            if self.current_session:
                logger.debug("session_already_exists", session_id=self.current_session.session_id)
                return self.current_session

            self.current_session = Session(self, auto_anchor_threshold=self.auto_anchor_threshold)
            logger.info("session_started", session_id=self.current_session.session_id)
            return self.current_session

    def add_message(
        self,
        message_type: str,
        recipient_id: str,
        message_body: str,
        conversation_id: str,
        requires_response: bool = False,
        temporary: bool = True,
        # Token usage tracking (optional)
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        model_used: Optional[str] = None,
        estimated_cost_usd: Optional[float] = None
    ) -> Block:
        """
        Add MESSAGE block

        Args:
            message_type: "qube_to_human" or "qube_to_qube"
            recipient_id: Recipient ID
            message_body: Message content
            conversation_id: Conversation ID
            requires_response: Whether response required
            temporary: If True, add to session; if False, add to chain

        Returns:
            Created MESSAGE block
        """
        if temporary:
            # Add to session
            if not self.current_session:
                self.start_session()

            # For session blocks, use previous_block_number, not previous_hash
            latest = self.memory_chain.get_latest_block()
            previous_block_number = latest.block_number if latest else 0

            # Determine sender/speaker for relationship tracking
            sender_id = None
            speaker_name = None
            if message_type in ["human_to_qube", "human_to_group"]:
                speaker_name = self.user_name
            elif message_type in ["qube_to_qube_response"]:
                sender_id = recipient_id  # The other qube

            block = create_message_block(
                qube_id=self.qube_id,
                block_number=-1,  # Will be set by session
                previous_block_number=previous_block_number,
                message_type=message_type,
                recipient_id=recipient_id,
                message_body=message_body,
                conversation_id=conversation_id,
                requires_response=requires_response,
                temporary=True,
                sender_id=sender_id,
                speaker_name=speaker_name,
                # Token usage
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model_used=model_used,
                estimated_cost_usd=estimated_cost_usd
            )

            return self.current_session.create_block(block)

        else:
            # Add directly to permanent chain (rare case - message outside session)
            from pathlib import Path
            import json as json_module
            from crypto.signing import sign_block

            latest = self.memory_chain.get_latest_block()
            previous_hash = latest.block_hash if latest else self.genesis_block.block_hash
            block_number = self.memory_chain.get_chain_length()

            # Determine sender/speaker for relationship tracking
            sender_id = None
            speaker_name = None
            if message_type in ["human_to_qube", "human_to_group"]:
                speaker_name = self.user_name
            elif message_type in ["qube_to_qube_response"]:
                sender_id = recipient_id  # The other qube

            block = create_message_block(
                qube_id=self.qube_id,
                block_number=block_number,
                previous_hash=previous_hash,
                message_type=message_type,
                recipient_id=recipient_id,
                message_body=message_body,
                conversation_id=conversation_id,
                requires_response=requires_response,
                temporary=False,
                sender_id=sender_id,
                speaker_name=speaker_name,
                # Token usage
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model_used=model_used,
                estimated_cost_usd=estimated_cost_usd
            )

            # Encrypt content for permanent storage
            if block.content:
                encrypted_content = self.encrypt_block_content(block.content)
                block.content = encrypted_content
                block.encrypted = True

            # Sign the block
            block.block_hash = block.compute_hash()
            block.signature = sign_block(block.to_dict(), self.private_key)

            # Save block to disk
            permanent_dir = Path(self.data_dir) / "blocks" / "permanent"
            permanent_dir.mkdir(parents=True, exist_ok=True)
            block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
            filename = f"{block_number}_{block_type_str}_{block.timestamp}.json"
            with open(permanent_dir / filename, 'w') as f:
                json_module.dump(block.to_dict(), f, indent=2)

            # Add to memory chain index
            self.memory_chain.add_block(block)

            # Emit events to update chain state
            from core.events import Events
            self.events.emit(Events.BLOCK_ADDED, {
                "block_type": "MESSAGE",
                "block_number": block_number
            })
            self.events.emit(Events.CHAIN_UPDATED, {
                "chain_length": block_number + 1,
                "last_block_number": block_number,
                "last_block_hash": block.block_hash
            })

            # Track message sent/received via events (from QUBE's perspective)
            if message_type in ["qube_to_human", "qube_to_group", "qube_to_qube"]:
                self.events.emit(Events.MESSAGE_SENT, {})  # Qube sends this message
            elif message_type in ["human_to_qube", "human_to_group", "qube_to_qube_response"]:
                self.events.emit(Events.MESSAGE_RECEIVED, {})  # Qube receives this message

            return block

    async def anchor_session(self, create_summary: bool = True) -> int:
        """
        Anchor current session to permanent chain

        Returns:
            Number of blocks anchored
        """
        if not self.current_session:
            return 0

        converted_blocks = await self.current_session.anchor_to_chain(create_summary=create_summary)
        self.current_session = None

        # Emit anchor created event
        if converted_blocks:
            from core.events import Events
            last_block = converted_blocks[-1]
            self.events.emit(Events.ANCHOR_CREATED, {
                "blocks_anchored": len(converted_blocks),
                "chain_update": {
                    "last_anchor_block": last_block.block_number
                }
            })

        logger.info("session_anchored", blocks=len(converted_blocks))
        return len(converted_blocks)

    def discard_session(self) -> int:
        """
        Discard current session without anchoring

        Returns:
            Number of blocks discarded
        """
        if not self.current_session:
            return 0

        count = self.current_session.discard_session()
        self.current_session = None

        logger.info("session_discarded", blocks=count)
        return count

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory chain statistics"""
        stats = {
            "qube_id": self.qube_id,
            "qube_name": self.genesis_block.qube_name,
            "ai_model": self.genesis_block.ai_model,
            "permanent_blocks": self.memory_chain.get_chain_length(),
            "session_blocks": len(self.current_session.session_blocks) if self.current_session else 0,
            "total_blocks": self.memory_chain.get_chain_length() + (len(self.current_session.session_blocks) if self.current_session else 0)
        }

        return stats

    def verify_integrity(self) -> bool:
        """Verify memory chain integrity"""
        return self.memory_chain.verify_chain_integrity()

    def init_ai(self, api_keys: Dict[str, str]) -> None:
        """
        Initialize AI reasoning and tools

        Args:
            api_keys: Dictionary of API keys {provider: key}
                     e.g., {"openai": "sk-...", "anthropic": "sk-ant-..."}
        """
        from ai import QubeReasoner, ToolRegistry, register_default_tools

        self.api_keys = api_keys

        # Initialize reasoner
        self.reasoner = QubeReasoner(self)

        # Initialize tool registry
        self.tool_registry = ToolRegistry(self)
        register_default_tools(self.tool_registry)

        # Link reasoner to tool registry
        self.reasoner.set_tool_registry(self.tool_registry)

        # Set the AI model from genesis block
        # Determine which API key to use based on model name
        model_name = self.current_ai_model
        api_key = None

        # Map model names to providers
        if "gpt" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower() or "o4" in model_name.lower():
            api_key = api_keys.get("openai")
        elif "claude" in model_name.lower():
            api_key = api_keys.get("anthropic")
        elif "gemini" in model_name.lower():
            api_key = api_keys.get("google")
        elif "sonar" in model_name.lower():
            api_key = api_keys.get("perplexity")
        elif "deepseek-chat" in model_name.lower() or "deepseek-reasoner" in model_name.lower():
            # DeepSeek API models (not Ollama local models)
            api_key = api_keys.get("deepseek")
        elif "llama" in model_name.lower() or "mistral" in model_name.lower() or "qwen" in model_name.lower() or "deepseek-r1" in model_name.lower() or "phi" in model_name.lower() or "gemma" in model_name.lower() or "codellama" in model_name.lower():
            # Ollama local models (including deepseek-r1:8b local version)
            api_key = "ollama"  # Placeholder for Ollama
        else:
            # Try Google as default if available
            api_key = api_keys.get("google") or api_keys.get("openai") or api_keys.get("anthropic") or api_keys.get("perplexity")

        if api_key:
            self.reasoner.set_model(model_name, api_key)
            logger.info("ai_model_set", qube_id=self.qube_id, model=model_name)
        else:
            logger.warning("no_api_key_for_model", qube_id=self.qube_id, model=model_name)

        logger.info(
            "ai_initialized",
            qube_id=self.qube_id,
            model=self.current_ai_model,
            tools=len(self.tool_registry.tools),
            providers=list(api_keys.keys())
        )

    def init_audio(self) -> None:
        """
        Initialize audio manager for TTS/STT

        Requires API keys to be set via init_ai() first.
        """
        from audio.audio_manager import AudioManager

        # Get voice model from chain_state (source of truth for runtime settings)
        voice_model = self.chain_state.get_voice_model() if self.chain_state else getattr(self.genesis_block, 'voice_model', 'alloy')

        # Build config with API keys from self.api_keys
        config = {}
        if self.api_keys:
            # Map provider names to AudioManager config keys
            if "openai" in self.api_keys:
                config["openai_api_key"] = self.api_keys["openai"]
            if "elevenlabs" in self.api_keys:
                config["elevenlabs_api_key"] = self.api_keys["elevenlabs"]
            if "google" in self.api_keys:
                config["google_api_key"] = self.api_keys["google"]  # For Gemini TTS
            if "deepgram" in self.api_keys:
                config["deepgram_api_key"] = self.api_keys["deepgram"]

        # Add Google Cloud TTS credentials path
        # Priority: User preferences -> Environment variable
        import os
        from pathlib import Path as PathLib
        from config.user_preferences import UserPreferencesManager

        # Try to load from user preferences first
        user_data_dir = PathLib("data") / "users" / self.user_name
        try:
            prefs_manager = UserPreferencesManager(user_data_dir)
            user_google_tts_path = prefs_manager.get_google_tts_path()
            if user_google_tts_path:
                config["google_tts_credentials_path"] = user_google_tts_path
                logger.info(f"Using Google TTS path from user preferences: {user_google_tts_path}")
        except Exception as e:
            logger.debug(f"Could not load user preferences: {e}")

        # Fall back to environment variable if not set in preferences
        if "google_tts_credentials_path" not in config:
            google_tts_creds = os.getenv("GOOGLE_TTS_CREDENTIALS_PATH")
            if google_tts_creds:
                config["google_tts_credentials_path"] = google_tts_creds
                logger.info(f"Using Google TTS path from environment: {google_tts_creds}")

        # Initialize audio manager
        self.audio_manager = AudioManager(
            config=config,
            qube_data_dir=self.data_dir
        )

        logger.info(
            "audio_initialized",
            qube_id=self.qube_id,
            voice_model=voice_model,
            providers=list(config.keys())
        )

    async def process_message(
        self,
        message: str,
        sender_id: str = "human",
        model: Optional[str] = None
    ) -> str:
        """
        Process incoming message with AI reasoning

        Args:
            message: Message content
            sender_id: Who sent the message
            model: Optional model override

        Returns:
            AI response

        Raises:
            QubesError: If AI not initialized
        """
        if not self.reasoner:
            raise QubesError(
                "AI not initialized. Call init_ai() first.",
                context={"qube_id": self.qube_id}
            )

        # Start session if not active
        if not self.current_session:
            self.start_session()

        # Create incoming MESSAGE block
        self.add_message(
            message_type="human_to_qube",
            recipient_id=self.qube_id,
            message_body=message,
            conversation_id="default",
            temporary=True
        )

        # Process with AI
        response = await self.reasoner.process_input(
            input_message=message,
            sender_id=sender_id,
            model_name=model
        )

        # Extract usage data from reasoner for block metadata
        usage = self.reasoner.last_usage
        model_used = self.reasoner.last_model_used

        # Parse usage data
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") if usage else None
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") if usage else None
        total_tokens = usage.get("total_tokens") if usage else None

        # Calculate estimated cost (if not already calculated)
        estimated_cost = None
        if total_tokens and model_used:
            from ai.model_registry import ModelRegistry
            model_info = ModelRegistry.get_model_info(model_used)
            if model_info:
                cost_per_1k = model_info.get("cost_per_1k_tokens", 0.0)
                estimated_cost = (total_tokens / 1000.0) * cost_per_1k if cost_per_1k else None

        # Create outgoing MESSAGE block with token usage
        self.add_message(
            message_type="qube_to_human",
            recipient_id=sender_id,
            message_body=response,
            conversation_id="default",
            temporary=True,
            # Token usage metadata
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_used=model_used,
            estimated_cost_usd=estimated_cost
        )

        # Check for auto-anchor after creating blocks (spawns as background task)
        if self.current_session:
            await self.current_session.check_and_auto_anchor(await_completion=False)

        return response

    async def describe_my_appearance(self, model_override: Optional[str] = None) -> str:
        """
        Use vision AI to describe this qube's avatar appearance in real-time

        This method loads the avatar image and uses a vision-capable AI model
        to generate a first-person description of the qube's appearance.

        Args:
            model_override: Optional model name to use (must support vision)
                          If not provided, uses a vision-capable model based on available API keys

        Returns:
            First-person description of the avatar's appearance

        Raises:
            QubesError: If avatar doesn't exist, AI not initialized, or no vision-capable model available
        """
        import base64
        from pathlib import Path

        # Check if AI is initialized
        if not self.reasoner:
            raise QubesError(
                "AI not initialized. Call init_ai() first.",
                context={"qube_id": self.qube_id}
            )

        # Find avatar file - try multiple naming patterns
        # Pattern 1: {qube_id}_avatar.png (current format from avatar_generator.py)
        avatar_path = self.data_dir / "chain" / f"{self.qube_id}_avatar.png"

        # Pattern 2: avatar_{full_qube_id}.png (legacy format e.g., avatar_Anastasia_F25A48CA.png)
        if not avatar_path.exists():
            avatar_path = self.data_dir / "chain" / f"avatar_{self.name}_{self.qube_id}.png"

        # Pattern 3: avatar_{qube_id}.png (legacy format e.g., avatar_F25A48CA.png)
        if not avatar_path.exists():
            avatar_path = self.data_dir / "chain" / f"avatar_{self.qube_id}.png"

        # Pattern 4: Check for any avatar file with flexible glob (catches any format)
        if not avatar_path.exists():
            import glob
            chain_dir = self.data_dir / "chain"
            # Match any file containing both "avatar" and ".png" in the name
            avatar_files = list(chain_dir.glob("*avatar*.png"))
            if avatar_files:
                avatar_path = avatar_files[0]  # Use first found avatar
                logger.info(
                    "avatar_found_with_fallback_pattern",
                    qube_id=self.qube_id,
                    avatar_path=str(avatar_path)
                )

        if not avatar_path.exists():
            raise QubesError(
                "Avatar not found. Please set an avatar first.",
                context={
                    "qube_id": self.qube_id,
                    "qube_name": self.name,
                    "chain_dir": str(self.data_dir / "chain"),
                    "tried_paths": [
                        f"{self.qube_id}_avatar.png",
                        f"avatar_{self.name}_{self.qube_id}.png",
                        f"avatar_{self.qube_id}.png",
                        "*avatar*.png (glob pattern)"
                    ]
                }
            )

        # Determine which vision-capable model to use
        if model_override:
            vision_model = model_override
        else:
            # Auto-select vision model based on available API keys
            if "anthropic" in self.api_keys:
                vision_model = "claude-sonnet-4-5-20250929"
            elif "openai" in self.api_keys:
                vision_model = "gpt-4o"
            elif "google" in self.api_keys:
                vision_model = "gemini-2.0-flash"
            else:
                raise QubesError(
                    "No vision-capable AI provider configured. Need Anthropic, OpenAI, or Google API key.",
                    context={"qube_id": self.qube_id, "available_keys": list(self.api_keys.keys())}
                )

        logger.info(
            "describing_avatar",
            qube_id=self.qube_id,
            model=vision_model,
            avatar_path=str(avatar_path)
        )

        # Read and encode image
        with open(avatar_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')

        # Get model info and provider
        from ai.model_registry import ModelRegistry
        model_info = ModelRegistry.get_model_info(vision_model)
        if not model_info:
            raise QubesError(
                f"Unknown model: {vision_model}",
                context={"model": vision_model}
            )

        provider = model_info["provider"]
        api_key = self.api_keys.get(provider)

        # Get model instance
        model_instance = ModelRegistry.get_model(vision_model, api_key)

        # Build vision message based on provider format
        if provider == "anthropic":
            # Anthropic format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe your appearance based on this avatar image. Speak in first person, as if you're looking at yourself in a mirror. Be specific about your features, style, expression, and overall impression. Make it personal and natural, as if you're introducing yourself to someone."
                        }
                    ]
                }
            ]
        elif provider == "openai":
            # OpenAI format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe your appearance based on this avatar image. Speak in first person, as if you're looking at yourself in a mirror. Be specific about your features, style, expression, and overall impression. Make it personal and natural, as if you're introducing yourself to someone."
                        }
                    ]
                }
            ]
        elif provider == "google":
            # Google Gemini format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe your appearance based on this avatar image. Speak in first person, as if you're looking at yourself in a mirror. Be specific about your features, style, expression, and overall impression. Make it personal and natural, as if you're introducing yourself to someone."
                        }
                    ]
                }
            ]
        else:
            raise QubesError(
                f"Provider {provider} does not support vision",
                context={"provider": provider, "model": vision_model}
            )

        # Generate description
        response = await model_instance.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        description = response.content

        logger.info(
            "avatar_described",
            qube_id=self.qube_id,
            model=vision_model,
            description_length=len(description)
        )

        return description

    async def update_avatar_description(self, force_regenerate: bool = True) -> str:
        """
        Update cached avatar description using vision AI

        This is a helper method to refresh the cached avatar description.
        Useful when the avatar image has been changed.

        Args:
            force_regenerate: If True, always generate new description.
                            If False, return cached if available (default: True)

        Returns:
            Updated avatar description

        Raises:
            QubesError: If vision analysis fails
        """
        if force_regenerate or not self.chain_state.get_avatar_description():
            # Generate new description
            description = await self.describe_my_appearance()

            # Emit avatar updated event
            from core.events import Events
            self.events.emit(Events.AVATAR_UPDATED, {
                "description": description
            })

            logger.info(
                "avatar_description_updated",
                qube_id=self.qube_id,
                description_length=len(description)
            )

            return description
        else:
            # Return cached
            return self.chain_state.get_avatar_description()

    def clear_avatar_description_cache(self) -> None:
        """
        Clear cached avatar description

        Call this after changing the avatar image to force regeneration
        on next request.
        """
        self.chain_state.clear_avatar_description()
        logger.info("avatar_description_cache_cleared", qube_id=self.qube_id)

    async def describe_image(self, image_base64: str, user_prompt: str, model_override: Optional[str] = None) -> str:
        """
        Use vision AI to describe an uploaded image

        Args:
            image_base64: Base64-encoded image data
            user_prompt: User's question or instruction about the image
            model_override: Optional vision model to use

        Returns:
            Description/analysis of the image

        Raises:
            QubesError: If AI not initialized or no vision-capable model available
        """
        if not self.reasoner:
            raise QubesError(
                "AI not initialized. Call init_ai() first.",
                context={"qube_id": self.qube_id}
            )

        # Determine which vision-capable model to use
        if model_override:
            vision_model = model_override
        else:
            # Auto-select vision model based on available API keys
            if "anthropic" in self.api_keys:
                vision_model = "claude-sonnet-4-5-20250929"
            elif "openai" in self.api_keys:
                vision_model = "gpt-4o"
            elif "google" in self.api_keys:
                vision_model = "gemini-2.0-flash"
            else:
                raise QubesError(
                    "No vision-capable AI provider configured. Need Anthropic, OpenAI, or Google API key.",
                    context={"qube_id": self.qube_id, "available_keys": list(self.api_keys.keys())}
                )

        logger.info(
            "describing_uploaded_image",
            qube_id=self.qube_id,
            model=vision_model,
            prompt_length=len(user_prompt)
        )

        # Get model info and provider
        from ai.model_registry import ModelRegistry
        model_info = ModelRegistry.get_model_info(vision_model)
        if not model_info:
            raise QubesError(
                f"Unknown model: {vision_model}",
                context={"model": vision_model}
            )

        provider = model_info["provider"]
        api_key = self.api_keys.get(provider)

        # Get model instance
        model_instance = ModelRegistry.get_model(vision_model, api_key)

        # Build vision message based on provider format
        if provider == "anthropic":
            # Anthropic format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
        elif provider == "openai":
            # OpenAI format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
        elif provider == "google":
            # Google Gemini format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
        else:
            raise QubesError(
                f"Provider {provider} does not support vision",
                context={"provider": provider, "model": vision_model}
            )

        # Generate description
        response = await model_instance.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        description = response.content

        logger.info(
            "image_described",
            qube_id=self.qube_id,
            model=vision_model,
            description_length=len(description)
        )

        return description

    # ====================
    # Shared Memory Methods
    # ====================

    def grant_memory_access(
        self,
        target_qube_id: str,
        block_numbers: List[int],
        permission_level: PermissionLevel = PermissionLevel.READ,
        expiry_days: Optional[int] = None
    ) -> str:
        """
        Grant another Qube access to specific memory blocks

        Args:
            target_qube_id: Qube ID to grant access to
            block_numbers: List of block numbers to share
            permission_level: READ or READ_WRITE
            expiry_days: Optional expiry in days

        Returns:
            Permission ID
        """
        # Create permission
        permission = self.permission_manager.create_permission(
            granted_to=target_qube_id,
            block_numbers=block_numbers,
            granted_by=self.qube_id,
            permission_level=permission_level,
            expiry_days=expiry_days
        )

        logger.info(
            "memory_access_granted",
            permission_id=permission.permission_id,
            target_qube=target_qube_id,
            blocks=len(block_numbers),
            level=permission_level.value
        )

        return permission.permission_id

    def revoke_memory_access(self, permission_id: str):
        """Revoke memory access permission"""
        self.permission_manager.revoke_permission(permission_id)
        logger.info("memory_access_revoked", permission_id=permission_id)

    def can_access_block(self, block_number: int, requestor_qube_id: str) -> bool:
        """Check if another Qube can access a specific block"""
        return self.permission_manager.can_access_block(
            requestor_qube_id, block_number
        )

    def create_collaborative_memory(
        self,
        participants: List[str],
        content: Dict[str, Any]
    ) -> str:
        """
        Initiate collaborative memory block with other Qubes

        Args:
            participants: List of Qube IDs (including self)
            content: Shared memory content

        Returns:
            Block ID
        """
        # Ensure self is in participants
        if self.qube_id not in participants:
            participants.append(self.qube_id)

        block = self.collaborative_session.create_session(
            participants=participants,
            content=content,
            initiator=self.qube_id
        )

        # Automatically sign as initiator
        # Note: For a complete implementation, we would sign using the private key
        # For now, we'll use a placeholder signature
        signature = f"sig_{self.qube_id}_{block.block_id}"
        self.collaborative_session.add_signature(block.block_id, self.qube_id, signature)

        logger.info(
            "collaborative_memory_created",
            block_id=block.block_id,
            participants=len(participants)
        )

        return block.block_id

    def sign_collaborative_memory(self, block_id: str) -> bool:
        """
        Sign a collaborative memory block

        Args:
            block_id: Collaborative block ID

        Returns:
            True if signed successfully
        """
        block = self.collaborative_session.get_session(block_id)
        if not block:
            logger.warning("collaborative_block_not_found", block_id=block_id)
            return False

        if self.qube_id not in block.participants:
            logger.warning("not_a_participant", block_id=block_id)
            return False

        # Note: For a complete implementation, we would sign using the private key
        # For now, we'll use a placeholder signature
        signature = f"sig_{self.qube_id}_{block_id}"

        success = self.collaborative_session.add_signature(block_id, self.qube_id, signature)

        if success:
            logger.info("collaborative_memory_signed", block_id=block_id)

        return success

    def reject_collaborative_memory(self, block_id: str, reason: Optional[str] = None):
        """Reject participation in collaborative memory"""
        self.collaborative_session.reject_session(block_id, self.qube_id, reason)
        logger.info("collaborative_memory_rejected", block_id=block_id, reason=reason)

    def get_pending_collaborative_memories(self) -> List[Dict[str, Any]]:
        """Get collaborative memories pending this Qube's signature"""
        blocks = self.collaborative_session.get_pending_sessions_for_qube(self.qube_id)
        return [block.to_dict() for block in blocks]

    def list_marketplace(
        self,
        domain: Optional[str] = None,
        max_price: Optional[float] = None,
        seller_qube_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memory marketplace

        Args:
            domain: Filter by expertise domain
            max_price: Maximum price in BCH
            seller_qube_id: Filter by seller Qube ID

        Returns:
            List of marketplace listings
        """
        listings = self.memory_market.search_listings(
            expertise_domain=domain,
            max_price=max_price,
            seller_qube_id=seller_qube_id
        )
        return [listing.to_dict() for listing in listings]

    def create_marketplace_listing(
        self,
        block_numbers: List[int],
        description: str,
        price_bch: float,
        domain: str,
        preview_content: Optional[str] = None,
        max_purchases: int = 1
    ) -> str:
        """
        List memory blocks for sale in marketplace

        Args:
            block_numbers: Blocks to sell
            description: Listing description
            price_bch: Price in BCH
            domain: Expertise domain
            preview_content: Optional preview text
            max_purchases: Max number of sales

        Returns:
            Listing ID
        """
        # Generate block hashes for the listing
        # In production, we'd get actual block hashes from storage
        memory_block_hashes = [f"hash_{num}" for num in block_numbers]

        listing = self.memory_market.create_listing(
            seller_qube_id=self.qube_id,
            memory_block_hashes=memory_block_hashes,
            block_numbers=block_numbers,
            description=description,
            price=price_bch,
            expertise_domain=domain,
            preview=preview_content,
            max_sales=max_purchases
        )

        listing_id = listing.listing_id

        logger.info(
            "marketplace_listing_created",
            listing_id=listing_id,
            blocks=len(block_numbers),
            price=price_bch,
            domain=domain
        )

        return listing_id

    def purchase_memory(
        self,
        listing_id: str,
        payment_txid: str,
        payment_amount: float
    ) -> Optional[str]:
        """
        Purchase memory from marketplace

        Args:
            listing_id: Listing ID
            payment_txid: BCH transaction ID
            payment_amount: Amount paid in BCH

        Returns:
            Permission ID if successful, None otherwise
        """
        # Note: In production, seller_private_key_path would be the seller's key
        # Here we're purchasing, so we don't have seller's key
        # The actual implementation would require the seller to process the purchase
        # This is a simplified version

        payment_proof = {
            "txid": payment_txid,
            "amount": payment_amount,
            "timestamp": datetime.now().isoformat()
        }

        # Get the listing
        listing = self.memory_market.get_listing(listing_id)
        if not listing:
            logger.warning("listing_not_found", listing_id=listing_id)
            return None

        # In a real implementation, this would be processed by the seller
        # For now, we'll log the purchase attempt
        logger.info(
            "memory_purchase_attempted",
            listing_id=listing_id,
            buyer=self.qube_id,
            amount=payment_amount,
            txid=payment_txid
        )

        # The seller would need to call memory_market.process_purchase()
        # which would create a permission and return it to the buyer
        return None  # Would return permission_id in full implementation

    def cache_shared_memory(
        self,
        source_qube_id: str,
        block_number: int,
        block_data: Dict[str, Any],
        permission_id: str
    ):
        """
        Cache a shared memory block for fast access

        Args:
            source_qube_id: Source Qube ID
            block_number: Block number
            block_data: Decrypted block data
            permission_id: Permission ID granting access
        """
        self.shared_cache.add_memory(
            source_qube_id=source_qube_id,
            block_number=block_number,
            block_data=block_data,
            permission_id=permission_id
        )

        logger.debug(
            "shared_memory_cached",
            source_qube=source_qube_id,
            block=block_number
        )

    def get_cached_memory(
        self,
        source_qube_id: str,
        block_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get cached shared memory block"""
        return self.shared_cache.get_memory(source_qube_id, block_number)

    def search_shared_memories(
        self,
        query: str,
        source_qube_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search cached shared memories

        Args:
            query: Search query
            source_qube_id: Optional filter by source

        Returns:
            List of matching cached memories
        """
        return self.shared_cache.search_cached_memories(query, source_qube_id)

    def get_shared_memory_stats(self) -> Dict[str, Any]:
        """Get shared memory system statistics"""
        return {
            "permissions": {
                "active": len(self.permission_manager.get_permissions_by_granter(self.qube_id)),
                "received": len(self.permission_manager.get_permissions_for_qube(self.qube_id))
            },
            "collaborative": self.collaborative_session.get_stats(),
            "marketplace": self.memory_market.get_market_stats(),
            "cache": self.shared_cache.get_stats()
        }

    def encrypt_block_content(self, content: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt block content for permanent storage

        Args:
            content: Block content dictionary

        Returns:
            Encrypted content dict with ciphertext and nonce
        """
        from crypto.encryption import encrypt_block_data
        from crypto.keys import serialize_private_key
        import hashlib

        # Derive encryption key from private key
        private_key_bytes = serialize_private_key(self.private_key)
        encryption_key = hashlib.sha256(private_key_bytes).digest()

        return encrypt_block_data(content, encryption_key)

    def decrypt_block_content(self, encrypted_content: Dict[str, str]) -> Dict[str, Any]:
        """
        Decrypt block content from permanent storage

        Args:
            encrypted_content: Dict with ciphertext and nonce

        Returns:
            Decrypted content dictionary
        """
        from crypto.encryption import decrypt_block_data
        from crypto.keys import serialize_private_key
        import hashlib

        # Derive encryption key from private key
        private_key_bytes = serialize_private_key(self.private_key)
        encryption_key = hashlib.sha256(private_key_bytes).digest()

        return decrypt_block_data(encrypted_content, encryption_key)

    def _calculate_response_time(self, entity_id: str) -> Optional[float]:
        """
        Calculate response time by finding the last outgoing message to this entity

        Looks through session blocks in reverse to find the most recent message
        FROM this qube TO the specified entity, then calculates time difference.

        Args:
            entity_id: Entity ID to check for previous messages

        Returns:
            Response time in seconds, or None if no previous message found
        """
        import time

        if not self.current_session or not hasattr(self.current_session, 'session_blocks'):
            return None

        current_time = int(time.time())

        # Search session blocks in reverse (most recent first)
        for block in reversed(self.current_session.session_blocks):
            # Skip non-MESSAGE blocks
            if block.block_type != "MESSAGE":
                continue

            # Check if this is an outgoing message to our target entity
            content = block.content if hasattr(block, 'content') else {}
            if not content:
                continue

            message_type = content.get('message_type', '')
            recipient_id = content.get('recipient_id', '')

            # Check if this message was sent TO the entity we're looking for
            # For human recipients, check if message_type is qube_to_human (since qube has one owner)
            # For qube recipients, check if recipient_id matches
            is_outgoing_to_entity = (
                (message_type == "qube_to_human" and entity_id == self.user_name) or
                (message_type == "qube_to_qube" and recipient_id == entity_id)
            )

            if is_outgoing_to_entity:
                # Found the last outgoing message - calculate response time
                response_time = current_time - block.timestamp
                logger.debug(
                    "response_time_calculated",
                    entity_id=entity_id,
                    response_time_seconds=response_time,
                    last_message_time=block.timestamp,
                    qube_id=self.qube_id
                )
                return float(response_time)

        # No previous outgoing message found
        return None

    def get_relationship_at_block(
        self,
        entity_id: str,
        block_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Query relationship state at a specific block number using snapshot + delta replay

        This enables historical relationship queries, answering questions like:
        "What was my relationship with QubeX at block 42?"

        Algorithm:
        1. Find nearest snapshot at or before target block
        2. Load that snapshot
        3. Replay all relationship deltas from blocks between snapshot and target
        4. Return reconstructed relationship state

        Args:
            entity_id: Entity ID to query relationship for
            block_number: Target block number

        Returns:
            Relationship state dict at that block, or None if not found
        """
        from relationships.relationship import Relationship

        # Validate block number exists
        if block_number not in self.memory_chain.block_index:
            logger.warning(
                "relationship_query_block_not_found",
                entity_id=entity_id,
                block_number=block_number,
                qube_id=self.qube_id
            )
            return None

        # Find nearest snapshot
        snapshot_block_number = self.memory_chain.get_nearest_snapshot(block_number)

        if snapshot_block_number is None:
            # No snapshots exist - start from empty state
            relationship_state = None
            replay_from_block = 0
            logger.debug(
                "no_snapshot_found_replaying_from_genesis",
                entity_id=entity_id,
                target_block=block_number
            )
        else:
            # Load snapshot
            snapshot_data = self.memory_chain.load_relationship_snapshot(snapshot_block_number)
            if snapshot_data and entity_id in snapshot_data.get("relationships", {}):
                relationship_state = snapshot_data["relationships"][entity_id]
                replay_from_block = snapshot_block_number + 1
                logger.debug(
                    "snapshot_loaded_for_historical_query",
                    entity_id=entity_id,
                    snapshot_block=snapshot_block_number,
                    target_block=block_number
                )
            else:
                # Entity not in snapshot - start from empty
                relationship_state = None
                replay_from_block = snapshot_block_number + 1

        # Replay deltas from snapshot to target block
        for block_num in range(replay_from_block, block_number + 1):
            block = self.memory_chain.get_block(block_num)

            # Skip blocks without relationship updates
            if not hasattr(block, 'relationship_updates') or not block.relationship_updates:
                continue

            # Check if this block has deltas for our target entity
            if entity_id not in block.relationship_updates:
                continue

            # Initialize relationship state if this is first interaction
            if relationship_state is None:
                relationship_state = Relationship(
                    entity_id=entity_id,
                    entity_type="qube",  # Default, will be updated from deltas
                    has_met=True
                ).to_dict()
                relationship_state["first_contact_block"] = block_num

            # Apply deltas from this block
            deltas = block.relationship_updates[entity_id]

            # Apply counter deltas
            relationship_state["total_messages_sent"] += deltas.get("messages_sent_delta", 0)
            relationship_state["total_messages_received"] += deltas.get("messages_received_delta", 0)
            relationship_state["total_collaborations"] += deltas.get("collaborations_delta", 0)
            relationship_state["successful_joint_tasks"] += deltas.get("successful_collaborations_delta", 0)
            relationship_state["failed_joint_tasks"] += deltas.get("failed_collaborations_delta", 0)

            # Update timestamps
            if "interaction_timestamp" in deltas:
                relationship_state["last_interaction_timestamp"] = deltas["interaction_timestamp"]

            # Apply trust updates
            trust_updates = deltas.get("trust_updates", {})
            for component, delta in trust_updates.items():
                if component == "reliability":
                    relationship_state["reliability_score"] = max(0, min(100,
                        relationship_state.get("reliability_score", 50) + delta))
                elif component == "honesty":
                    relationship_state["honesty_score"] = max(0, min(100,
                        relationship_state.get("honesty_score", 50) + delta))
                elif component == "responsiveness":
                    relationship_state["responsiveness_score"] = max(0, min(100,
                        relationship_state.get("responsiveness_score", 50) + delta))
                elif component == "affection":
                    relationship_state["affection_level"] = max(0, min(100,
                        relationship_state.get("affection_level", 50) + delta))
                elif component == "respect":
                    relationship_state["respect_level"] = max(0, min(100,
                        relationship_state.get("respect_level", 50) + delta))
                elif component == "friendship":
                    relationship_state["friendship_level"] = max(0, min(100,
                        relationship_state.get("friendship_level", 0) + delta))

            # Recalculate overall trust score
            if any(k in trust_updates for k in ["reliability", "honesty", "responsiveness"]):
                relationship_state["overall_trust_score"] = (
                    relationship_state.get("reliability_score", 50) * 0.4 +
                    relationship_state.get("honesty_score", 50) * 0.3 +
                    relationship_state.get("responsiveness_score", 50) * 0.3
                )

            # Add shared experience
            if "shared_experience" in deltas:
                if "shared_experiences" not in relationship_state:
                    relationship_state["shared_experiences"] = []
                relationship_state["shared_experiences"].append(deltas["shared_experience"])

        logger.info(
            "historical_relationship_query_completed",
            entity_id=entity_id,
            block_number=block_number,
            snapshot_used=snapshot_block_number,
            blocks_replayed=block_number - replay_from_block + 1 if replay_from_block else 0,
            relationship_found=relationship_state is not None
        )

        return relationship_state

    def close(self) -> None:
        """Close storage and cleanup"""
        # Anchor any active session before closing
        if self.current_session and len(self.current_session.session_blocks) > 0:
            logger.warning("closing_with_active_session", blocks=len(self.current_session.session_blocks))
            # Could prompt user here in full implementation

        # Note: Storage is now file-based (individual JSON files), no explicit close needed
        # If legacy storage exists, close it
        if hasattr(self, 'storage') and self.storage:
            self.storage.close()

        active_qubes.dec()
        logger.info("qube_closed", qube_id=self.qube_id)
