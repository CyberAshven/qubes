"""
Chain State Management - v2.0

Consolidated, encrypted state management for Qubes.
All Qube state (settings, relationships, skills, financial) lives here.

Architecture:
- Encrypted at rest using AES-256-GCM
- Namespaced sections for organization
- Atomic writes with backup
- Bidirectional merge on save prevents data loss:
  - Backend saves preserve GUI-managed settings from disk
  - GUI saves preserve backend-managed sections (stats, skills, etc.) from disk
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from utils.logging import get_logger
from utils.file_lock import FileLock
from crypto.encryption import encrypt_block_data, decrypt_block_data, derive_chain_state_key

if TYPE_CHECKING:
    from core.events import ChainStateEventBus

logger = get_logger(__name__)


def create_default_chain_state(genesis_block: Dict[str, Any], qube_id: str = None) -> Dict[str, Any]:
    """
    Create a default chain_state from genesis block data.

    This is the SINGLE SOURCE OF TRUTH for what a fresh chain_state looks like.
    Used when:
    - Creating a new qube (initial chain_state)
    - Resetting a qube (restore to default)

    Args:
        genesis_block: Genesis block data (from genesis.json or metadata)
        qube_id: Qube ID (extracted from genesis if not provided)

    Returns:
        Complete chain_state dict ready to be saved
    """
    now = int(datetime.now(timezone.utc).timestamp())

    # Extract qube-specific values from genesis
    qube_id = qube_id or genesis_block.get("qube_id", "unknown")
    ai_model = genesis_block.get("ai_model", "claude-sonnet-4-20250514")
    voice_model = genesis_block.get("voice_model", "openai:alloy")
    genesis_hash = genesis_block.get("block_hash", "0" * 64)
    birth_timestamp = genesis_block.get("birth_timestamp") or genesis_block.get("timestamp") or now

    # TTS enabled: check explicit field, then capabilities, then default based on voice_model
    tts_enabled = genesis_block.get("tts_enabled")
    if tts_enabled is None:
        capabilities = genesis_block.get("capabilities", {})
        tts_enabled = capabilities.get("tts", bool(voice_model))

    # Determine provider from model name
    ai_model_lower = ai_model.lower()
    if "claude" in ai_model_lower:
        provider = "anthropic"
    elif "gpt" in ai_model_lower:
        provider = "openai"
    elif "gemini" in ai_model_lower:
        provider = "google"
    elif "sonar" in ai_model_lower:
        provider = "perplexity"
    elif "venice" in ai_model_lower:
        provider = "venice"
    elif any(x in ai_model_lower for x in ["llama", "mistral", "qwen"]):
        provider = "ollama"
    else:
        provider = genesis_block.get("ai_provider", "anthropic")

    return {
        "version": "2.0",
        "qube_id": qube_id,
        "last_updated": now,

        # Chain section - blockchain tracking
        "chain": {
            "length": 1,
            "latest_block_number": 0,
            "latest_block_hash": genesis_hash,
            "genesis_hash": genesis_hash,
            "genesis_timestamp": birth_timestamp,
            "total_blocks": 1,
            "permanent_blocks": 1,
            "session_blocks": 0,
            "last_anchor_block": None,
            "last_merkle_root": None,
        },

        # Session section - current conversation (ephemeral)
        "session": {
            "session_id": None,
            "started_at": None,
            "messages_this_session": 0,
            "context_window_used": 0,
            "last_message_at": None,
            "next_negative_index": -1,
        },

        # Settings section - qube-specific from genesis
        "settings": {
            "model_locked": True,  # Default to Manual Mode (locked)
            "model_locked_to": ai_model,
            "revolver_mode_enabled": False,
            "revolver_mode_pool": [],  # Populated with all models on first load
            "autonomous_mode_enabled": False,
            "autonomous_mode_pool": [],  # Populated with all models on first load
            "individual_auto_anchor_enabled": True,
            "individual_auto_anchor_threshold": 20,
            "group_auto_anchor_enabled": True,
            "group_auto_anchor_threshold": 20,
            "tts_enabled": tts_enabled,
            "voice_model": voice_model,
            "visualizer_enabled": False,
            "visualizer_settings": None,
        },

        # Runtime section - active state (updated during conversation)
        "runtime": {
            "is_online": False,
            "current_model": ai_model,
            "current_provider": provider,
            "last_api_call": None,
            "pending_tool_calls": [],
            "active_conversation_id": None,
        },

        # Stats section - usage metrics (all zeroed)
        "stats": {
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_tokens_used": 0,
            "total_api_cost": 0.0,
            "tokens_by_model": {},
            "api_calls_by_tool": {},
            "total_tool_calls": 0,
            "total_sessions": 0,
            "total_anchors": 0,
            "created_at": now,
            "first_interaction": None,
            "last_interaction": None,
        },

        # Block counts - fresh start
        "block_counts": {
            "GENESIS": 1,
            "MESSAGE": 0,
            "ACTION": 0,
            "SUMMARY": 0,
            "GAME": 0,
        },

        # Skills section - compact format (only stores skills with XP)
        "skills": {
            "skill_xp": {},  # {skill_id: {xp: int, level: int}} - only skills with XP > 0
            "extra_unlocked": [],  # Skills unlocked beyond defaults (suns are default unlocked)
            "total_xp": 0,
            "last_xp_gain": None,
            "history": [],
        },

        # Relationships section - empty (no relationships)
        "relationships": {
            "entities": {},
            "total_entities_known": 0,
            "best_friend": None,
            "owner": None,
            "clearance_settings": None,
        },

        # Financial section - empty wallet
        "financial": {
            "wallet": {
                "address": None,
                "balance_satoshis": 0,
                "balance_bch": 0.0,
                "last_sync": None,
                "utxo_count": 0,
            },
            "transactions": {
                "history": [],
                "total_count": 0,
                "archived_count": 0,
            },
            "pending": [],
        },

        # Mood section - neutral
        "mood": {
            "current": "neutral",
            "intensity": 0.5,
            "last_updated": None,
            "history": [],
        },

        # Owner info section - empty (learned during conversation)
        "owner_info": {},

        # Health section - integrity and system status
        "health": {
            "overall_status": "healthy",
            "last_health_check": None,
            "integrity_verified": None,
            "last_integrity_check": None,
            "issues": [],
        },

        # Attestation section - blockchain attestation tracking
        "attestation": {
            "last_attestation": None,
            "attestation_hash": None,
            "signed_by": None,
            "verified": False,
        },
    }


class ChainState:
    """
    Manages chain_state.json persistence with encryption.

    v2.0 Features:
    - Encrypted at rest (AES-256-GCM)
    - Namespaced sections (chain, session, settings, runtime, stats, skills, relationships, financial, mood, health, attestation)
    - Atomic writes (temp file + rename)
    - Backup on every save
    - Bidirectional merge prevents GUI/backend from overwriting each other's data
    """

    # Version for migration detection
    VERSION = "2.0"

    # Fields managed by GUI (always prefer disk values on backend save)
    GUI_MANAGED_FIELDS = {
        "model_locked",
        "model_locked_to",
        "revolver_mode_enabled",
        "revolver_mode_pool",
        "autonomous_mode_enabled",
        "autonomous_mode_pool",
        "individual_auto_anchor_enabled",
        "individual_auto_anchor_threshold",
        "group_auto_anchor_enabled",
        "group_auto_anchor_threshold",
        "tts_enabled",
        "voice_model",
        "visualizer_enabled",
        "visualizer_settings",
    }

    # Sections excluded from IPFS anchors (ephemeral data)
    IPFS_EXCLUDED_SECTIONS = {"session", "runtime", "attestation"}

    # Array caps to prevent unbounded growth
    MAX_TRANSACTION_HISTORY = 50
    MAX_SKILL_HISTORY = 100
    MAX_RELATIONSHIP_EVALUATIONS = 50
    MAX_MOOD_HISTORY = 20

    def __init__(self, data_dir: Path, encryption_key: bytes, qube_id: str = None, genesis_block: Dict[str, Any] = None):
        """
        Initialize chain state.

        Args:
            data_dir: Path to chain directory (e.g., data/qubes/Athena_A1B2C3D4/chain/)
            encryption_key: 32-byte qube encryption key
            qube_id: Qube ID (optional, read from state if not provided)
            genesis_block: Genesis block data (optional, used to create initial state with correct values)
        """
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "chain_state.json"
        self.backup_file = self.data_dir / ".chain_state.backup.json"
        self.lock_file = self.data_dir / ".chain_state.lock"

        # Derive chain_state-specific key
        self.encryption_key = encryption_key
        self.chain_state_key = derive_chain_state_key(encryption_key)

        self.qube_id = qube_id
        self._genesis_block = genesis_block  # Store for use in _initialize_new_state

        # Event bus for event-driven state management (lazy initialization)
        self._event_bus: Optional["ChainStateEventBus"] = None

        # Staged session tracking - session-scoped sections stay in memory until anchor
        # When active, _save() excludes staged sections from disk writes
        self._staged_session_active: bool = False
        self._staged_stats_baseline: Dict[str, Any] = {}  # Baseline for session-scoped stats

        # Load existing state or create new
        if self.state_file.exists():
            self._load()
        else:
            self._initialize_new_state()

        # Update qube_id if provided and different
        if qube_id and self.state.get("qube_id") != qube_id:
            self.state["qube_id"] = qube_id

        logger.info("chain_state_loaded", qube_id=self.qube_id, version=self.state.get("version"))

    @property
    def events(self) -> "ChainStateEventBus":
        """
        Get the event bus for event-driven state management.

        The event bus is lazily initialized on first access.
        Use this to emit events that update chain_state:

            chain_state.events.emit(Events.TRANSACTION_SENT, {...})

        Returns:
            ChainStateEventBus instance
        """
        if self._event_bus is None:
            from core.events import ChainStateEventBus
            self._event_bus = ChainStateEventBus(self)
        return self._event_bus

    def _initialize_new_state(self) -> None:
        """Initialize new v2.0 chain state with all sections."""
        # Use create_default_chain_state if genesis_block is available (preferred)
        if self._genesis_block is not None:
            self.state = create_default_chain_state(self._genesis_block, self.qube_id)
            self._save()
            logger.info("chain_state_initialized_from_genesis", qube_id=self.qube_id)
            return

        # Fallback: hardcoded defaults (for backward compatibility)
        now = int(datetime.now(timezone.utc).timestamp())

        self.state = {
            "version": self.VERSION,
            "qube_id": self.qube_id,
            "last_updated": now,

            # Chain section - blockchain tracking
            "chain": {
                "length": 0,
                "latest_block_number": -1,
                "latest_block_hash": "0" * 64,
                "genesis_hash": None,
                "genesis_timestamp": now,
                "total_blocks": 0,
                "permanent_blocks": 0,
                "session_blocks": 0,
                "last_anchor_block": None,
                "last_merkle_root": None,
            },

            # Session section - current conversation (ephemeral)
            "session": {
                "session_id": None,
                "started_at": None,
                "messages_this_session": 0,
                "context_window_used": 0,
                "last_message_at": None,
                "next_negative_index": -1,
            },

            # Settings section - GUI-managed settings
            "settings": {
                "model_locked": False,
                "model_locked_to": None,
                "revolver_mode_enabled": False,
                "revolver_mode_pool": [],  # Populated with all models on first load
                "autonomous_mode_enabled": False,
                "autonomous_mode_pool": [],  # Populated with all models on first load
                "individual_auto_anchor_enabled": True,
                "individual_auto_anchor_threshold": 20,
                "group_auto_anchor_enabled": True,
                "group_auto_anchor_threshold": 20,
                "tts_enabled": False,
                "voice_model": "openai:alloy",
                "visualizer_enabled": False,
                "visualizer_settings": None,
            },

            # Runtime section - active state (updated during conversation)
            "runtime": {
                "is_online": False,
                "current_model": "claude-sonnet-4-20250514",
                "current_provider": "anthropic",
                "last_api_call": None,
                "pending_tool_calls": [],
                "active_conversation_id": None,
            },

            # Stats section - usage metrics
            "stats": {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_tokens_used": 0,
                "total_api_cost": 0.0,
                "tokens_by_model": {},
                "api_calls_by_tool": {},
                "total_tool_calls": 0,
                "total_sessions": 0,
                "total_anchors": 0,
                "created_at": now,
                "first_interaction": None,
                "last_interaction": None,
            },

            # Block counts (active block types only)
            "block_counts": {
                "GENESIS": 0,
                "MESSAGE": 0,
                "ACTION": 0,
                "SUMMARY": 0,
                "GAME": 0,
            },

            # Skills section - compact format (only stores skills with XP)
            "skills": {
                "skill_xp": {},  # {skill_id: {xp: int, level: int}} - only skills with XP > 0
                "extra_unlocked": [],  # Skills unlocked beyond defaults
                "total_xp": 0,
                "last_xp_gain": None,
                "history": [],
            },

            # Relationships section
            "relationships": {
                "entities": {},
                "total_entities_known": 0,
                "best_friend": None,
                "owner": None,
            },

            # Financial section
            "financial": {
                "wallet": {
                    "address": None,
                    "balance_satoshis": 0,
                    "balance_bch": 0.0,
                    "last_sync": None,
                    "utxo_count": 0,
                },
                "transactions": {
                    "history": [],
                    "total_count": 0,
                    "archived_count": 0,
                },
                "pending": [],
            },

            # Mood section
            "mood": {
                "current_mood": "neutral",
                "energy_level": 50,
                "stress_level": 0,
                "last_mood_update": None,
                "mood_history": [],
            },

            # Health section
            "health": {
                "overall_status": "healthy",
                "last_health_check": None,
                "issues": [],
                "integrity_verified": True,
                "last_integrity_check": None,
            },

            # Attestation section (ephemeral)
            "attestation": {
                "last_attestation": None,
                "attestation_hash": None,
                "signed_by": None,
                "verified": False,
            },

            # Legacy fields for backward compatibility
            "avatar_description": None,
            "avatar_description_generated_at": None,
            "model_preferences": {},
            "current_model_override": None,
        }

        self._save()
        logger.info("chain_state_initialized", qube_id=self.qube_id)

    def _load(self) -> None:
        """Load and decrypt state from disk.

        Note: No lock needed for reads - atomic file writes in _save() protect against
        corruption, and multiple readers are safe. This avoids lock contention when
        multiple processes (GUI CLI commands) load the same qube simultaneously.
        """
        try:
            with open(self.state_file, 'r') as f:
                file_data = json.load(f)

            # Check if encrypted
            if file_data.get("encrypted"):
                try:
                    self.state = decrypt_block_data(file_data, self.chain_state_key)
                except Exception as e:
                    logger.error("chain_state_decryption_failed", error=str(e))
                    # Try to recover from backup
                    if self._recover_from_backup():
                        return
                    raise
            else:
                # Unencrypted legacy file - migrate to encrypted
                self.state = file_data
                logger.info("migrating_unencrypted_chain_state")
                self._save()  # Re-save encrypted

            # Check if migration needed (flat → namespaced)
            if "version" not in self.state:
                self._migrate_v1_to_v2()

            # Clean up deprecated fields (always run)
            self._cleanup_deprecated_fields()

            logger.debug("chain_state_loaded_from_disk", qube_id=self.state.get("qube_id"))

        except Exception as e:
            logger.error("chain_state_load_failed", error=str(e), exc_info=True)
            raise

    def _recover_from_backup(self) -> bool:
        """Attempt to recover from backup file."""
        if not self.backup_file.exists():
            logger.warning("no_backup_file_for_recovery")
            return False

        try:
            with open(self.backup_file, 'r') as f:
                backup_data = json.load(f)

            if backup_data.get("encrypted"):
                self.state = decrypt_block_data(backup_data, self.chain_state_key)
            else:
                self.state = backup_data

            logger.info("chain_state_recovered_from_backup")
            self._save()  # Re-save to main file
            return True

        except Exception as e:
            logger.error("backup_recovery_failed", error=str(e))
            return False

    def _migrate_v1_to_v2(self) -> None:
        """Migrate flat v1 state to namespaced v2 structure."""
        logger.info("migrating_chain_state_v1_to_v2")

        old = self.state
        now = int(datetime.now(timezone.utc).timestamp())

        # Build v2 structure preserving old values
        self.state = {
            "version": self.VERSION,
            "qube_id": old.get("qube_id"),
            "last_updated": now,

            "chain": {
                "length": old.get("chain_length", 0),
                "latest_block_number": old.get("chain_length", 1) - 1,
                "latest_block_hash": old.get("last_block_hash", "0" * 64),
                "genesis_hash": None,
                "genesis_timestamp": None,
                "total_blocks": old.get("chain_length", 0),
                "permanent_blocks": old.get("chain_length", 0),
                "session_blocks": old.get("session_block_count", 0),
                "last_anchor_block": old.get("last_anchor_block"),
                "last_merkle_root": old.get("last_merkle_root"),
            },

            "session": {
                "session_id": old.get("current_session_id"),
                "started_at": old.get("session_start_timestamp"),
                "messages_this_session": 0,
                "context_window_used": 0,
                "last_message_at": None,
                "next_negative_index": old.get("next_negative_index", -1),
            },

            "settings": {
                "model_locked": old.get("model_locked", False),
                "model_locked_to": old.get("model_locked_to"),
                "revolver_mode_enabled": old.get("revolver_mode_enabled", False),
                # Migrate: old revolver_models -> revolver_mode_pool
                "revolver_mode_pool": old.get("revolver_mode_pool", old.get("revolver_models", [])),
                "autonomous_mode_enabled": old.get("free_mode_enabled", old.get("autonomous_mode_enabled", False)),
                # Migrate: old autonomous_mode_pools (dict) -> autonomous_mode_pool (list)
                # If old was dict, flatten values; if already list, use directly
                "autonomous_mode_pool": (
                    old.get("autonomous_mode_pool", []) or
                    [m for models in old.get("autonomous_mode_pools", old.get("free_mode_models", {})).values() for m in models]
                    if isinstance(old.get("autonomous_mode_pools", old.get("free_mode_models", {})), dict)
                    else old.get("autonomous_mode_pools", [])
                ),
                "individual_auto_anchor_enabled": old.get("individual_auto_anchor_enabled", True),
                "individual_auto_anchor_threshold": old.get("individual_auto_anchor_threshold", 20),
                "group_auto_anchor_enabled": old.get("group_auto_anchor_enabled", True),
                "group_auto_anchor_threshold": old.get("group_auto_anchor_threshold", 20),
                "tts_enabled": old.get("tts_enabled", False),
                "voice_model": old.get("voice_model", "openai:alloy"),
                "visualizer_enabled": old.get("visualizer_enabled", False),
                "visualizer_settings": old.get("visualizer_settings"),
            },

            "runtime": {
                "is_online": old.get("is_online", False),
                "current_model": old.get("current_model_override", old.get("current_model", "claude-sonnet-4-20250514")),
                "current_provider": old.get("current_provider", "anthropic"),
                "last_api_call": old.get("last_api_call"),
                "pending_tool_calls": old.get("pending_tool_calls", []),
                "active_conversation_id": old.get("active_conversation_id"),
            },

            "stats": {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_tokens_used": old.get("total_tokens_used", 0),
                "total_api_cost": old.get("total_api_cost", 0.0),
                "tokens_by_model": old.get("tokens_by_model", {}),
                "api_calls_by_tool": old.get("api_calls_by_tool", {}),
                "total_tool_calls": sum(old.get("api_calls_by_tool", {}).values()) if old.get("api_calls_by_tool") else 0,
                "total_sessions": 0,
                "total_anchors": 0,
                "created_at": old.get("last_updated", now),
                "first_interaction": None,
                "last_interaction": old.get("last_updated"),
            },

            "block_counts": old.get("block_counts", {
                "GENESIS": 0, "MESSAGE": 0, "ACTION": 0, "SUMMARY": 0, "GAME": 0,
            }),

            "skills": {"skill_xp": {}, "extra_unlocked": [], "total_xp": 0, "last_xp_gain": None, "history": []},
            "relationships": {"entities": {}, "total_entities_known": 0, "best_friend": None, "owner": None},
            "financial": {
                "wallet": {"address": None, "balance_satoshis": 0, "balance_bch": 0.0, "last_sync": None, "utxo_count": 0},
                "transactions": {"history": [], "total_count": 0, "archived_count": 0},
                "pending": [],
            },
            "mood": {"current_mood": "neutral", "energy_level": 50, "stress_level": 0, "last_mood_update": None, "mood_history": []},
            "health": {
                "overall_status": "healthy",
                "last_health_check": None,
                "issues": [],
                "integrity_verified": old.get("integrity_verified", True),
                "last_integrity_check": None,
            },
            "attestation": {"last_attestation": None, "attestation_hash": None, "signed_by": None, "verified": False},

            # Preserve legacy fields
            "avatar_description": old.get("avatar_description"),
            "avatar_description_generated_at": old.get("avatar_description_generated_at"),
            "model_preferences": old.get("model_preferences", {}),
            "current_model_override": old.get("current_model_override"),
        }

        self._save()
        logger.info("chain_state_migrated_to_v2", qube_id=self.state.get("qube_id"))

    def _cleanup_deprecated_fields(self) -> None:
        """Remove deprecated fields, migrate to correct locations, and ensure defaults.

        This ensures old fields don't accumulate in settings section.
        """
        settings = self.state.get("settings", {})
        runtime = self.state.setdefault("runtime", {})
        changed = False

        # Deprecated/ephemeral runtime fields to remove
        # - revolver tracking: no longer used (revolver is pure random)
        # - session_snapshot: ephemeral, should not be persisted to disk
        deprecated_runtime_fields = [
            "revolver_enabled_at",
            "revolver_first_response_done",
            "revolver_last_index",
            "revolver_last_response_at",
            "session_snapshot",           # ephemeral - for rollback, not disk storage
            "session_snapshot_timestamp", # ephemeral - accompanies session_snapshot
        ]
        for field in deprecated_runtime_fields:
            if field in runtime:
                del runtime[field]
                changed = True
            if field in settings:
                del settings[field]
                changed = True

        # Deprecated settings fields to remove (replaced by new names)
        deprecated_fields = [
            "revolver_models",      # replaced by revolver_mode_pool
            "revolver_providers",   # replaced by revolver_mode_pool
            "autonomous_mode_pools", # replaced by autonomous_mode_pool
            "free_mode_enabled",    # replaced by autonomous_mode_enabled
            "free_mode_models",     # replaced by autonomous_mode_pool
            "auto_anchor_enabled",  # replaced by individual/group variants
            "auto_anchor_threshold", # replaced by individual/group variants
        ]
        for field in deprecated_fields:
            if field in settings:
                del settings[field]
                changed = True

        # Ensure individual and group auto-anchor settings exist (independent settings)
        if "individual_auto_anchor_enabled" not in settings:
            settings["individual_auto_anchor_enabled"] = True
            changed = True
        if "individual_auto_anchor_threshold" not in settings:
            settings["individual_auto_anchor_threshold"] = 20
            changed = True
        if "group_auto_anchor_enabled" not in settings:
            settings["group_auto_anchor_enabled"] = True
            changed = True
        if "group_auto_anchor_threshold" not in settings:
            settings["group_auto_anchor_threshold"] = 20
            changed = True

        # Populate model pools with all available models if empty
        # Model pools should ALWAYS have models, even when modes are disabled
        if not settings.get("revolver_mode_pool") or not settings.get("autonomous_mode_pool"):
            try:
                from ai.model_registry import ModelRegistry
                all_models = list(ModelRegistry.MODELS.keys())
                if not settings.get("revolver_mode_pool"):
                    settings["revolver_mode_pool"] = all_models
                    changed = True
                if not settings.get("autonomous_mode_pool"):
                    settings["autonomous_mode_pool"] = all_models
                    changed = True
                logger.info("populated_model_pools", count=len(all_models))
            except Exception as e:
                logger.warning("failed_to_populate_model_pools", error=str(e))

        if changed:
            logger.info("cleaned_up_deprecated_fields", qube_id=self.state.get("qube_id"))
            self._save(preserve_gui_fields=False)

    def _save(self, preserve_gui_fields: bool = True) -> None:
        """Encrypt and save state to disk with backup.

        Merge strategy prevents GUI and backend from overwriting each other's data:
        - If preserve_gui_fields=True (backend saving): preserves GUI_MANAGED_FIELDS
          in settings section from disk, so backend won't overwrite GUI settings.
        - If preserve_gui_fields=False (GUI saving): preserves ALL non-settings
          sections (stats, skills, relationships, etc.) from disk, so GUI won't
          overwrite backend-managed data like message counts.

        Args:
            preserve_gui_fields: If True, backend is saving - preserve GUI settings.
                                 If False, GUI is saving - preserve non-settings sections.
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                lock = FileLock(self.lock_file, timeout=5.0)

                with lock:
                    # Load current disk state to preserve fields from disk
                    # Both GUI and backend need to merge with disk state to avoid overwriting
                    disk_state = {}
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                file_data = json.load(f)
                            if file_data.get("encrypted"):
                                disk_state = decrypt_block_data(file_data, self.chain_state_key)
                            else:
                                disk_state = file_data
                        except Exception:
                            pass

                    # Merge: start with in-memory, preserve appropriate fields from disk
                    merged_state = self.state.copy()

                    if preserve_gui_fields:
                        # Backend saving: preserve GUI-managed fields in settings from disk
                        if "settings" in disk_state and "settings" in merged_state:
                            for field in self.GUI_MANAGED_FIELDS:
                                if field in disk_state.get("settings", {}):
                                    merged_state["settings"][field] = disk_state["settings"][field]
                    else:
                        # GUI saving: preserve ALL non-settings sections from disk
                        # because GUI only manages settings, not stats/skills/relationships/etc.
                        # This prevents GUI from overwriting backend stats with stale values
                        non_settings_sections = ["stats", "skills", "relationships", "mood", "chain", "financial", "health", "owner_info", "block_counts", "runtime", "session"]
                        for section in non_settings_sections:
                            if section in disk_state:
                                merged_state[section] = disk_state[section]

                    # Strip ephemeral runtime fields before saving
                    # These are in-memory only and should not be persisted to disk
                    EPHEMERAL_RUNTIME_FIELDS = ["session_snapshot", "session_snapshot_timestamp"]
                    if "runtime" in merged_state:
                        # Create a copy without ephemeral fields
                        runtime_copy = {k: v for k, v in merged_state["runtime"].items()
                                       if k not in EPHEMERAL_RUNTIME_FIELDS}
                        merged_state["runtime"] = runtime_copy

                    # Staged session: keep session-scoped sections on disk unchanged
                    # Changes to skills, relationships, mood, owner_info stay in memory
                    # until the session is anchored (committed)
                    if self._staged_session_active:
                        for section in self.SESSION_SCOPED_SECTIONS:
                            if section in disk_state:
                                merged_state[section] = disk_state[section]
                        # Also preserve session-scoped stats fields
                        # IMPORTANT: Must copy the stats dict first to avoid corrupting self.state
                        # (merged_state is a shallow copy, so merged_state["stats"] points to self.state["stats"])
                        if "stats" in disk_state and "stats" in merged_state:
                            merged_state["stats"] = merged_state["stats"].copy()
                            for field in self.SESSION_SCOPED_STATS:
                                if field in disk_state["stats"]:
                                    merged_state["stats"][field] = disk_state["stats"][field]

                    # Update timestamp
                    merged_state["last_updated"] = int(datetime.now(timezone.utc).timestamp())

                    # Create backup before writing
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                backup_data = f.read()
                            with open(self.backup_file, 'w') as f:
                                f.write(backup_data)
                        except Exception as e:
                            logger.warning("backup_creation_failed", error=str(e))

                    # Encrypt
                    encrypted_data = encrypt_block_data(merged_state, self.chain_state_key)
                    encrypted_data["encrypted"] = True

                    # Atomic write
                    self.data_dir.mkdir(parents=True, exist_ok=True)
                    temp_file = self.state_file.with_suffix('.json.tmp')

                    with open(temp_file, 'w') as f:
                        json.dump(encrypted_data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())

                    temp_file.replace(self.state_file)

                    # Update in-memory state
                    # BUT preserve session-scoped sections if staged session is active
                    # (we want disk to have old values, but memory to have new values)
                    if self._staged_session_active:
                        # Restore session-scoped sections from original self.state
                        for section in self.SESSION_SCOPED_SECTIONS:
                            if section in self.state:
                                merged_state[section] = self.state[section]
                        # Restore session-scoped stats fields
                        if "stats" in self.state:
                            for field in self.SESSION_SCOPED_STATS:
                                if field in self.state["stats"]:
                                    merged_state["stats"][field] = self.state["stats"][field]

                    self.state = merged_state

                    logger.debug("chain_state_saved", qube_id=self.state.get("qube_id"))
                    return

            except Exception as e:
                logger.warning("chain_state_save_retry", attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))

        logger.error("chain_state_save_failed_all_retries", qube_id=self.state.get("qube_id"))

    def reload(self) -> None:
        """Reload state from disk, picking up external changes.

        IMPORTANT: If a staged session is active, session-scoped sections
        (skills, relationships, mood, owner_info) and session-scoped stats
        are preserved from memory - they should NOT be overwritten by disk values.
        """
        if self.state_file.exists():
            # If staged session is active, preserve session-scoped sections before reload
            preserved_sections = {}
            preserved_stats = {}
            if self._staged_session_active:
                for section in self.SESSION_SCOPED_SECTIONS:
                    if section in self.state:
                        # Deep copy to avoid reference issues
                        preserved_sections[section] = json.loads(json.dumps(self.state[section]))
                # Also preserve session-scoped stats
                if "stats" in self.state:
                    for field in self.SESSION_SCOPED_STATS:
                        if field in self.state["stats"]:
                            preserved_stats[field] = self.state["stats"][field]

            self._load()

            # Restore preserved session-scoped data
            if self._staged_session_active:
                for section, data in preserved_sections.items():
                    self.state[section] = data
                if preserved_stats and "stats" in self.state:
                    for field, value in preserved_stats.items():
                        self.state["stats"][field] = value
                logger.debug(
                    "reload_preserved_session_data",
                    qube_id=self.state.get("qube_id"),
                    preserved_sections=list(preserved_sections.keys()),
                    preserved_stats=list(preserved_stats.keys())
                )

            logger.debug("chain_state_reloaded", qube_id=self.state.get("qube_id"))

    # =========================================================================
    # SETTINGS SECTION METHODS (GUI-managed)
    # =========================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.state.get("settings", {}).get(key, default)

    def update_settings(self, updates: Dict[str, Any], from_gui: bool = False) -> None:
        """Update multiple settings at once.

        Args:
            updates: Dictionary of settings to update
            from_gui: If True, this is a GUI update and we should NOT preserve
                      old GUI-managed field values from disk (we want to save the new values)
        """
        if "settings" not in self.state:
            self.state["settings"] = {}
        self.state["settings"].update(updates)
        self._save(preserve_gui_fields=not from_gui)

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self.state.get("settings", {}).copy()

    # =========================================================================
    # CHAIN SECTION METHODS
    # =========================================================================

    def update_chain(
        self,
        chain_length: Optional[int] = None,
        last_block_number: Optional[int] = None,
        last_block_hash: Optional[str] = None,
        last_merkle_root: Optional[str] = None,
        last_anchor_block: Optional[int] = None,
        latest_block_number: Optional[int] = None
    ) -> None:
        """Update chain state fields."""
        chain = self.state.setdefault("chain", {})

        if chain_length is not None:
            chain["length"] = chain_length
            chain["permanent_blocks"] = chain_length
            chain["total_blocks"] = chain_length
        if last_block_number is not None:
            chain["latest_block_number"] = last_block_number
            chain["length"] = last_block_number + 1
            chain["permanent_blocks"] = last_block_number + 1
        if latest_block_number is not None:
            chain["latest_block_number"] = latest_block_number
        if last_block_hash is not None:
            chain["latest_block_hash"] = last_block_hash
        if last_merkle_root is not None:
            chain["last_merkle_root"] = last_merkle_root
        if last_anchor_block is not None:
            chain["last_anchor_block"] = last_anchor_block

        self._save()

    def increment_block_count(self, block_type: str, is_session_block: bool = False) -> None:
        """
        Increment count for a block type.

        Args:
            block_type: Type of block (GENESIS, MESSAGE, ACTION, SUMMARY, GAME)
            is_session_block: True if this is a temporary session block (negative index)
        """
        counts = self.state.setdefault("block_counts", {})
        counts[block_type] = counts.get(block_type, 0) + 1

        # Update chain totals based on block permanence
        chain = self.state.setdefault("chain", {})
        if is_session_block:
            # Session blocks are temporary - only increment session_blocks
            chain["session_blocks"] = chain.get("session_blocks", 0) + 1
        else:
            # Permanent blocks increment total_blocks and permanent_blocks
            chain["total_blocks"] = chain.get("total_blocks", 0) + 1
            chain["permanent_blocks"] = chain.get("permanent_blocks", 0) + 1
            # Also update length (alias for total permanent blocks)
            chain["length"] = chain.get("permanent_blocks", 1)

        self._save()

    def get_chain_length(self) -> int:
        """Get current chain length (permanent blocks only)."""
        return self.state.get("chain", {}).get("length", 1)

    def get_last_block_hash(self) -> str:
        """Get last block hash."""
        return self.state.get("chain", {}).get("latest_block_hash", "0" * 64)

    def get_block_counts(self) -> Dict[str, int]:
        """Get block type counts."""
        return self.state.get("block_counts", {}).copy()

    def rebuild_block_counts(self, memory_chain) -> bool:
        """
        Rebuild block_counts from actual memory chain blocks.

        Called during qube loading when chain_state has stale/zero counts
        but memory chain has blocks.

        Args:
            memory_chain: MemoryChain instance with block_index

        Returns:
            True if counts were rebuilt, False if no rebuild needed
        """
        if not hasattr(memory_chain, 'block_index'):
            return False

        actual_count = len(memory_chain.block_index)
        current_total = sum(self.get_block_counts().values())

        # Only rebuild if chain_state shows 0 but blocks exist
        if current_total > 0 or actual_count == 0:
            return False

        logger.info("rebuilding_block_counts", actual_blocks=actual_count)

        # Count blocks by type
        rebuilt_counts = {
            "GENESIS": 0,
            "MESSAGE": 0,
            "ACTION": 0,
            "SUMMARY": 0,
            "GAME": 0,
        }

        for block_num in memory_chain.block_index.keys():
            try:
                block = memory_chain.get_block(block_num)
                block_type = block.block_type if hasattr(block, 'block_type') else "MESSAGE"
                if block_type in rebuilt_counts:
                    rebuilt_counts[block_type] += 1
                # Ignore deprecated block types
            except Exception as e:
                logger.debug(f"Could not read block {block_num}: {e}")

        # Update chain_state
        self.state["block_counts"] = rebuilt_counts

        # Update chain totals
        chain = self.state.setdefault("chain", {})
        total = sum(rebuilt_counts.values())
        chain["total_blocks"] = total
        chain["permanent_blocks"] = total

        self._save()
        logger.info("block_counts_rebuilt", counts=rebuilt_counts)
        return True

    # =========================================================================
    # SESSION SECTION METHODS
    # =========================================================================

    def start_session(self, session_id: str) -> None:
        """Start new session."""
        session = self.state.setdefault("session", {})

        if session.get("session_id") is None:
            session["messages_this_session"] = 0
            session["next_negative_index"] = -1
            session["context_window_used"] = 0  # Reset for new session

        session["session_id"] = session_id
        session["started_at"] = int(datetime.now(timezone.utc).timestamp())

        # Update runtime with active conversation
        runtime = self.state.setdefault("runtime", {})
        runtime["active_conversation_id"] = session_id
        runtime["is_online"] = True

        # Note: total_sessions removed - sessions are implementation details,
        # not meaningful metrics. Qubes use anchors for persistent state.

        self._save()

        # Create snapshot for transactional consistency
        # If session is discarded, session-scoped data can be rolled back
        self.snapshot_session_data()

        logger.info("session_started", session_id=session_id)

    def end_session(self) -> None:
        """End current session."""
        session = self.state.setdefault("session", {})
        session["session_id"] = None

        # Clear runtime active conversation
        runtime = self.state.setdefault("runtime", {})
        runtime["active_conversation_id"] = None
        session["started_at"] = None
        session["messages_this_session"] = 0
        session["context_window_used"] = 0  # Reset context usage when session ends
        # Note: next_negative_index no longer tracked - block indices computed from timestamps

        self._save()
        logger.info("session_ended", qube_id=self.state.get("qube_id"))

    def get_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.state.get("session", {}).get("session_id")

    def update_session(
        self,
        session_block_count: Optional[int] = None,
        next_negative_index: Optional[int] = None,
        context_window_used: Optional[int] = None,
        last_message_at: Optional[int] = None
    ) -> None:
        """Update session state."""
        session = self.state.setdefault("session", {})

        if session_block_count is not None:
            session["messages_this_session"] = session_block_count
            # Also update chain.session_blocks to keep in sync
            chain = self.state.setdefault("chain", {})
            chain["session_blocks"] = session_block_count
        if next_negative_index is not None:
            session["next_negative_index"] = next_negative_index
        if context_window_used is not None:
            session["context_window_used"] = context_window_used
        if last_message_at is not None:
            session["last_message_at"] = last_message_at

        self._save()

    def get_session_block_count(self) -> int:
        """Get current session block count."""
        return self.state.get("session", {}).get("messages_this_session", 0)

    # =========================================================================
    # STATS SECTION METHODS
    # =========================================================================

    def add_tokens(self, model: str, tokens: int, cost: float = 0.0) -> None:
        """Track token usage and costs."""
        stats = self.state.setdefault("stats", {})

        stats["total_tokens_used"] = stats.get("total_tokens_used", 0) + tokens
        stats["total_api_cost"] = stats.get("total_api_cost", 0.0) + cost

        tokens_by_model = stats.setdefault("tokens_by_model", {})
        tokens_by_model[model] = tokens_by_model.get(model, 0) + tokens

        self._save()

    def increment_tool_call(self, tool_name: str) -> None:
        """Track tool/API calls.

        During staged session, total_tool_calls is derived from session block files.
        api_calls_by_tool still increments (detailed breakdown, not session-scoped).
        """
        stats = self.state.setdefault("stats", {})

        # api_calls_by_tool always increments (detailed tracking, persists immediately)
        api_calls = stats.setdefault("api_calls_by_tool", {})
        api_calls[tool_name] = api_calls.get(tool_name, 0) + 1

        # During staged session, don't increment total_tool_calls in-memory
        # It's derived from session blocks to avoid double-counting
        if not self._staged_session_active:
            stats["total_tool_calls"] = stats.get("total_tool_calls", 0) + 1

        self._save()

    def increment_anchor(self) -> None:
        """Track anchor operations."""
        stats = self.state.setdefault("stats", {})
        stats["total_anchors"] = stats.get("total_anchors", 0) + 1
        self._save()

    def increment_message_sent(self) -> None:
        """Track outgoing messages.

        During staged session, counts are derived from session block files,
        not incremented in memory. This avoids double-counting and works
        with subprocess architecture.
        """
        stats = self.state.setdefault("stats", {})

        # During staged session, don't increment in-memory - counts are derived from blocks
        # This prevents double-counting when get_stats_with_pending() adds file-based counts
        if not self._staged_session_active:
            stats["total_messages_sent"] = stats.get("total_messages_sent", 0) + 1

        # Update last_interaction timestamp (always, not session-scoped)
        stats["last_interaction"] = int(datetime.now(timezone.utc).timestamp())
        if stats.get("first_interaction") is None:
            stats["first_interaction"] = stats["last_interaction"]

        self._save()

    def increment_message_received(self) -> None:
        """Track incoming messages.

        During staged session, counts are derived from session block files,
        not incremented in memory. This avoids double-counting and works
        with subprocess architecture.
        """
        stats = self.state.setdefault("stats", {})

        # During staged session, don't increment in-memory - counts are derived from blocks
        # This prevents double-counting when get_stats_with_pending() adds file-based counts
        if not self._staged_session_active:
            stats["total_messages_received"] = stats.get("total_messages_received", 0) + 1

        # Update last_interaction timestamp (always, not session-scoped)
        stats["last_interaction"] = int(datetime.now(timezone.utc).timestamp())
        if stats.get("first_interaction") is None:
            stats["first_interaction"] = stats["last_interaction"]

        self._save()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        stats = self.state.get("stats", {})
        return {
            "total_tokens": stats.get("total_tokens_used", 0),
            "total_cost": stats.get("total_api_cost", 0.0),
            "tokens_by_model": stats.get("tokens_by_model", {}).copy(),
            "api_calls_by_tool": stats.get("api_calls_by_tool", {}).copy(),
        }

    def get_pending_session_stats(self) -> Dict[str, int]:
        """
        Calculate pending message/tool counts from session block files.

        This allows displaying real-time counts during a session while preserving
        rollback semantics (discard deletes session blocks, pending counts go to 0).
        Works with subprocess architecture since it reads from disk.

        Returns:
            Dict with pending_messages_sent, pending_messages_received, pending_tool_calls
        """
        import json
        from pathlib import Path

        pending = {
            "pending_messages_sent": 0,
            "pending_messages_received": 0,
            "pending_tool_calls": 0
        }

        # Session blocks are in blocks/session/ folder (sibling to chain/ folder)
        session_dir = self.data_dir.parent / "blocks" / "session"
        if not session_dir.exists():
            return pending

        try:
            for block_file in session_dir.glob("*.json"):
                try:
                    with open(block_file, 'r') as f:
                        block_data = json.load(f)

                    block_type = block_data.get("block_type", "")
                    content = block_data.get("content", {})

                    if block_type == "MESSAGE":
                        message_type = content.get("message_type", "")
                        # From qube's perspective:
                        # - human_to_qube = qube RECEIVES the message
                        # - qube_to_human = qube SENDS the message
                        if message_type in ["human_to_qube", "human_to_group", "qube_to_qube_response"]:
                            pending["pending_messages_received"] += 1
                        elif message_type in ["qube_to_human", "qube_to_group", "qube_to_qube"]:
                            pending["pending_messages_sent"] += 1
                    elif block_type == "ACTION":
                        pending["pending_tool_calls"] += 1

                except Exception as e:
                    logger.debug(f"Failed to read session block {block_file}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to scan session blocks: {e}")

        return pending

    def get_stats_with_pending(self) -> Dict[str, Any]:
        """
        Get stats with pending session counts added.

        Returns committed stats + pending counts from session blocks.
        This gives real-time visibility while preserving rollback semantics.
        """
        stats = self.state.get("stats", {}).copy()
        pending = self.get_pending_session_stats()

        # Add pending to committed values
        stats["total_messages_sent"] = stats.get("total_messages_sent", 0) + pending["pending_messages_sent"]
        stats["total_messages_received"] = stats.get("total_messages_received", 0) + pending["pending_messages_received"]
        stats["total_tool_calls"] = stats.get("total_tool_calls", 0) + pending["pending_tool_calls"]

        # Include pending counts separately for transparency
        stats["_pending_messages_sent"] = pending["pending_messages_sent"]
        stats["_pending_messages_received"] = pending["pending_messages_received"]
        stats["_pending_tool_calls"] = pending["pending_tool_calls"]

        return stats

    # =========================================================================
    # SKILLS SECTION METHODS
    # =========================================================================

    def get_unlocked_skills(self) -> List[Dict[str, Any]]:
        """Get list of unlocked skills."""
        return self.state.get("skills", {}).get("unlocked", [])

    def unlock_skill(self, skill_id: str, xp: int = 0) -> None:
        """Add a skill to unlocked list."""
        skills = self.state.setdefault("skills", {"unlocked": [], "total_xp": 0, "history": []})
        now = int(datetime.now(timezone.utc).timestamp())

        # Check if already unlocked
        for skill in skills["unlocked"]:
            if skill["id"] == skill_id:
                return  # Already unlocked

        skills["unlocked"].append({
            "id": skill_id,
            "xp": xp,
            "level": 1,
            "unlocked_at": now,
            "last_updated": now,
        })

        self._save()
        logger.info("skill_unlocked", skill_id=skill_id)

    def add_skill_xp(self, skill_id: str, xp_amount: int, reason: str = None, block_id: str = None) -> None:
        """Add XP to a skill."""
        skills = self.state.setdefault("skills", {"unlocked": [], "total_xp": 0, "history": []})
        now = int(datetime.now(timezone.utc).timestamp())

        # Find and update skill
        for skill in skills["unlocked"]:
            if skill["id"] == skill_id:
                skill["xp"] = skill.get("xp", 0) + xp_amount
                skill["last_updated"] = now
                # Calculate level (simple: 100 XP per level)
                skill["level"] = min(100, 1 + skill["xp"] // 100)
                break
        else:
            # Skill not unlocked yet - unlock it
            self.unlock_skill(skill_id, xp_amount)

        # Update totals
        skills["total_xp"] = skills.get("total_xp", 0) + xp_amount
        skills["last_xp_gain"] = now

        # Add to history (capped)
        history = skills.setdefault("history", [])
        history.append({
            "timestamp": now,
            "skill_id": skill_id,
            "xp_gained": xp_amount,
            "reason": reason,
            "block_id": block_id,
        })

        # Cap history
        if len(history) > self.MAX_SKILL_HISTORY:
            skills["history"] = history[-self.MAX_SKILL_HISTORY:]

        self._save()

    def get_skill_progress(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific skill."""
        for skill in self.get_unlocked_skills():
            if skill["id"] == skill_id:
                return skill
        return None

    # =========================================================================
    # RELATIONSHIPS SECTION METHODS
    # =========================================================================

    def get_relationship(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get relationship data for an entity."""
        return self.state.get("relationships", {}).get("entities", {}).get(entity_id)

    def get_all_relationships(self) -> Dict[str, Dict[str, Any]]:
        """Get all relationships."""
        return self.state.get("relationships", {}).get("entities", {}).copy()

    def get_relationships(self) -> Dict[str, Dict[str, Any]]:
        """Alias for get_all_relationships - returns all relationships."""
        return self.get_all_relationships()

    def update_relationship(self, entity_id: str, data: Dict[str, Any]) -> None:
        """Update or create a relationship."""
        relationships = self.state.setdefault("relationships", {"entities": {}, "total_entities_known": 0})
        entities = relationships.setdefault("entities", {})

        is_new = entity_id not in entities
        entities[entity_id] = data

        if is_new:
            relationships["total_entities_known"] = len(entities)

        # Update owner/best_friend tracking
        if data.get("entity_type") == "human":
            relationships["owner"] = entity_id
        if data.get("is_best_friend"):
            relationships["best_friend"] = entity_id

        self._save()

    def delete_relationship(self, entity_id: str) -> bool:
        """Delete a relationship."""
        entities = self.state.get("relationships", {}).get("entities", {})
        if entity_id in entities:
            del entities[entity_id]
            self.state["relationships"]["total_entities_known"] = len(entities)
            self._save()
            return True
        return False

    def update_relationships(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Bulk update all relationships (replaces entire entities dict).

        Args:
            data: Dict mapping entity_id -> relationship data
        """
        relationships = self.state.setdefault("relationships", {"entities": {}, "total_entities_known": 0})
        relationships["entities"] = data
        relationships["total_entities_known"] = len(data)

        # Update owner/best_friend tracking
        for entity_id, rel_data in data.items():
            if rel_data.get("entity_type") == "human":
                relationships["owner"] = entity_id
            if rel_data.get("is_best_friend"):
                relationships["best_friend"] = entity_id

        self._save()

    def get_best_friend(self) -> Optional[str]:
        """Get best friend entity ID."""
        return self.state.get("relationships", {}).get("best_friend")

    def get_owner(self) -> Optional[str]:
        """Get owner entity ID."""
        return self.state.get("relationships", {}).get("owner")

    # =========================================================================
    # FINANCIAL SECTION METHODS
    # =========================================================================

    def get_wallet_info(self) -> Dict[str, Any]:
        """Get wallet information."""
        return self.state.get("financial", {}).get("wallet", {}).copy()

    def update_wallet(self, **kwargs) -> None:
        """Update wallet information."""
        wallet = self.state.setdefault("financial", {}).setdefault("wallet", {})
        wallet.update(kwargs)
        self._save()

    def add_transaction(self, tx: Dict[str, Any]) -> None:
        """Add a transaction to history."""
        financial = self.state.setdefault("financial", {})
        transactions = financial.setdefault("transactions", {"history": [], "total_count": 0, "archived_count": 0})
        history = transactions.setdefault("history", [])

        history.append(tx)
        transactions["total_count"] = transactions.get("total_count", 0) + 1

        # Cap history
        if len(history) > self.MAX_TRANSACTION_HISTORY:
            overflow = len(history) - self.MAX_TRANSACTION_HISTORY
            transactions["archived_count"] = transactions.get("archived_count", 0) + overflow
            transactions["history"] = history[-self.MAX_TRANSACTION_HISTORY:]

        self._save()

    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history."""
        history = self.state.get("financial", {}).get("transactions", {}).get("history", [])
        return history[-limit:] if limit else history

    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get pending transactions."""
        return self.state.get("financial", {}).get("pending", [])

    def add_pending_transaction(self, tx: Dict[str, Any]) -> None:
        """Add a pending transaction."""
        pending = self.state.setdefault("financial", {}).setdefault("pending", [])
        pending.append(tx)
        self._save()

    def remove_pending_transaction(self, tx_id: str) -> bool:
        """Remove a pending transaction by ID."""
        pending = self.state.get("financial", {}).get("pending", [])
        for i, tx in enumerate(pending):
            if tx.get("tx_id") == tx_id:
                pending.pop(i)
                self._save()
                return True
        return False

    # =========================================================================
    # MOOD SECTION METHODS
    # =========================================================================

    def update_mood(
        self,
        mood: Optional[str] = None,
        energy_level: Optional[int] = None,
        stress_level: Optional[int] = None
    ) -> None:
        """
        Update emotional state.

        Args:
            mood: Current mood (e.g., "neutral", "happy", "focused", "tired")
            energy_level: Energy level 0-100
            stress_level: Stress level 0-100
        """
        mood_section = self.state.setdefault("mood", {
            "current_mood": "neutral",
            "energy_level": 50,
            "stress_level": 0,
            "last_mood_update": None,
            "mood_history": []
        })
        now = int(datetime.now(timezone.utc).timestamp())

        old_mood = mood_section.get("current_mood")

        if mood is not None:
            mood_section["current_mood"] = mood
        if energy_level is not None:
            mood_section["energy_level"] = max(0, min(100, energy_level))
        if stress_level is not None:
            mood_section["stress_level"] = max(0, min(100, stress_level))

        mood_section["last_mood_update"] = now

        # Add to history if mood changed
        if mood is not None and old_mood != mood:
            history = mood_section.setdefault("mood_history", [])
            history.append({
                "mood": mood,
                "energy": mood_section.get("energy_level", 50),
                "stress": mood_section.get("stress_level", 0),
                "timestamp": now
            })
            # Cap history
            if len(history) > self.MAX_MOOD_HISTORY:
                mood_section["mood_history"] = history[-self.MAX_MOOD_HISTORY:]

        self._save()

    def get_mood(self) -> Dict[str, Any]:
        """Get current mood state."""
        return self.state.get("mood", {}).copy()

    def adjust_energy(self, delta: int) -> int:
        """
        Adjust energy level by delta.

        Args:
            delta: Amount to adjust (+/-)

        Returns:
            New energy level
        """
        mood = self.state.setdefault("mood", {"energy_level": 50})
        current = mood.get("energy_level", 50)
        new_level = max(0, min(100, current + delta))
        mood["energy_level"] = new_level
        mood["last_mood_update"] = int(datetime.now(timezone.utc).timestamp())
        self._save()
        return new_level

    def adjust_stress(self, delta: int) -> int:
        """
        Adjust stress level by delta.

        Args:
            delta: Amount to adjust (+/-)

        Returns:
            New stress level
        """
        mood = self.state.setdefault("mood", {"stress_level": 0})
        current = mood.get("stress_level", 0)
        new_level = max(0, min(100, current + delta))
        mood["stress_level"] = new_level
        mood["last_mood_update"] = int(datetime.now(timezone.utc).timestamp())
        self._save()
        return new_level

    # =========================================================================
    # HEALTH SECTION METHODS
    # =========================================================================

    def update_health(
        self,
        overall_status: Optional[str] = None,
        integrity_verified: Optional[bool] = None,
        issues: Optional[List[str]] = None
    ) -> None:
        """Update health metrics."""
        health = self.state.setdefault("health", {})
        now = int(datetime.now(timezone.utc).timestamp())

        if overall_status is not None:
            health["overall_status"] = overall_status
        if integrity_verified is not None:
            health["integrity_verified"] = integrity_verified
            health["last_integrity_check"] = now
        if issues is not None:
            health["issues"] = issues

        health["last_health_check"] = now
        self._save()

    def get_health(self) -> Dict[str, Any]:
        """Get health information."""
        return self.state.get("health", {}).copy()

    # =========================================================================
    # OWNER INFO SECTION METHODS
    # =========================================================================

    # Predefined categories for owner info
    OWNER_INFO_CATEGORIES = {"standard", "physical", "preferences", "people", "dates", "dynamic"}

    # Default sensitivity levels for common fields
    OWNER_INFO_DEFAULT_SENSITIVITIES = {
        # Standard fields
        "name": "public",
        "nickname": "public",
        "birthday": "private",
        "location_city": "private",
        "location_country": "private",
        "occupation": "public",
        "timezone": "public",
        # Physical fields
        "eye_color": "public",
        "hair_color": "public",
        "height": "public",
        "distinguishing_features": "public",
        # Preference fields
        "favorite_color": "public",
        "favorite_food": "public",
        "favorite_music": "public",
        "favorite_movie": "public",
        "hobbies": "public",
        "dislikes": "public",
        # People fields
        "family_members": "private",
        "pets": "private",
        "significant_other": "private",
        # Date fields
        "anniversary": "private",
        "important_dates": "private",
    }

    # Limits
    MAX_FIELD_VALUE_LENGTH = 1000
    MAX_DYNAMIC_FIELDS = 50
    MAX_CUSTOM_SECTIONS = 20
    MAX_FIELDS_PER_CUSTOM_SECTION = 30

    def _initialize_owner_info(self) -> Dict[str, Any]:
        """Initialize empty owner info structure."""
        now = datetime.now(timezone.utc).isoformat() + "Z"
        return {
            "created_at": now,
            "last_updated": now,
            "standard": {},
            "physical": {},
            "preferences": {},
            "people": {},
            "dates": {},
            "dynamic": [],
            "custom_sections": {}
        }

    def _create_owner_field(
        self,
        key: str,
        value: str,
        sensitivity: str = "private",
        source: str = "explicit",
        confidence: int = 100,
        block_id: str = None
    ) -> Dict[str, Any]:
        """Create a new owner info field dictionary."""
        # Truncate value if too long
        if len(value) > self.MAX_FIELD_VALUE_LENGTH:
            value = value[:self.MAX_FIELD_VALUE_LENGTH]
            logger.warning("owner_field_truncated", key=key, max_length=self.MAX_FIELD_VALUE_LENGTH)

        # Validate sensitivity
        if sensitivity not in ("public", "private", "secret"):
            sensitivity = "private"

        now = datetime.now(timezone.utc).isoformat() + "Z"
        return {
            "key": key,
            "value": value,
            "sensitivity": sensitivity,
            "source": source,
            "confidence": min(100, max(0, confidence)),
            "learned_at": now,
            "block_id": block_id,
            "last_confirmed": None
        }

    def get_owner_info(self) -> Dict[str, Any]:
        """Get all owner info."""
        owner_info = self.state.get("owner_info")
        if not owner_info:
            return self._initialize_owner_info()
        return owner_info.copy()

    def set_owner_field(
        self,
        category: str,
        key: str,
        value: str,
        sensitivity: str = None,
        source: str = "explicit",
        confidence: int = 100,
        block_id: str = None
    ) -> bool:
        """
        Set or update an owner info field.

        Args:
            category: Field category (standard, physical, preferences, people, dates, dynamic)
                      OR a custom section name
            key: Field key
            value: Field value
            sensitivity: Sensitivity level (public/private/secret), uses default if None
            source: How info was obtained (explicit/inferred)
            confidence: Confidence level 0-100
            block_id: Evidence block ID

        Returns:
            True if successful
        """
        owner_info = self.state.setdefault("owner_info", self._initialize_owner_info())

        # Normalize key
        key = key.lower().replace(" ", "_").replace("-", "_")

        # Use default sensitivity if not provided
        if sensitivity is None:
            sensitivity = self.OWNER_INFO_DEFAULT_SENSITIVITIES.get(key, "private")

        field = self._create_owner_field(key, value, sensitivity, source, confidence, block_id)

        if category == "dynamic":
            # Dynamic is a list of misc fields
            dynamic_fields = owner_info.setdefault("dynamic", [])

            if len(dynamic_fields) >= self.MAX_DYNAMIC_FIELDS:
                # Check if updating existing
                existing_idx = None
                for idx, f in enumerate(dynamic_fields):
                    if f.get("key") == key:
                        existing_idx = idx
                        break

                if existing_idx is None:
                    logger.warning("owner_info_max_dynamic_fields", max=self.MAX_DYNAMIC_FIELDS)
                    return False

                dynamic_fields[existing_idx] = field
            else:
                # Update existing or add new
                found = False
                for idx, f in enumerate(dynamic_fields):
                    if f.get("key") == key:
                        dynamic_fields[idx] = field
                        found = True
                        break
                if not found:
                    dynamic_fields.append(field)

        elif category in self.OWNER_INFO_CATEGORIES:
            # Standard category
            if category not in owner_info:
                owner_info[category] = {}
            owner_info[category][key] = field

        else:
            # Custom section
            custom_sections = owner_info.setdefault("custom_sections", {})

            # Check custom section limits
            if category not in custom_sections:
                if len(custom_sections) >= self.MAX_CUSTOM_SECTIONS:
                    logger.warning("owner_info_max_custom_sections", max=self.MAX_CUSTOM_SECTIONS)
                    return False
                custom_sections[category] = {}

            section = custom_sections[category]
            if len(section) >= self.MAX_FIELDS_PER_CUSTOM_SECTION and key not in section:
                logger.warning("owner_info_max_fields_in_section", section=category, max=self.MAX_FIELDS_PER_CUSTOM_SECTION)
                return False

            section[key] = field

        owner_info["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"
        logger.info("owner_field_set", category=category, key=key, sensitivity=sensitivity)
        self._save()
        return True

    def get_owner_field(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific owner info field.

        Args:
            category: Field category or custom section name
            key: Field key

        Returns:
            Field dictionary or None if not found
        """
        owner_info = self.state.get("owner_info", {})

        if category == "dynamic":
            for field in owner_info.get("dynamic", []):
                if field.get("key") == key:
                    return field.copy()
            return None
        elif category in self.OWNER_INFO_CATEGORIES:
            field = owner_info.get(category, {}).get(key)
            return field.copy() if field else None
        else:
            # Custom section
            section = owner_info.get("custom_sections", {}).get(category, {})
            field = section.get(key)
            return field.copy() if field else None

    def delete_owner_field(self, category: str, key: str) -> bool:
        """
        Delete an owner info field.

        Args:
            category: Field category or custom section name
            key: Field key

        Returns:
            True if deleted, False if not found
        """
        owner_info = self.state.get("owner_info", {})

        if category == "dynamic":
            dynamic_fields = owner_info.get("dynamic", [])
            original_len = len(dynamic_fields)
            owner_info["dynamic"] = [f for f in dynamic_fields if f.get("key") != key]
            if len(owner_info["dynamic"]) == original_len:
                return False
        elif category in self.OWNER_INFO_CATEGORIES:
            if category not in owner_info or key not in owner_info.get(category, {}):
                return False
            del owner_info[category][key]
        else:
            # Custom section
            section = owner_info.get("custom_sections", {}).get(category, {})
            if key not in section:
                return False
            del section[key]
            # Remove empty custom section
            if not section:
                del owner_info["custom_sections"][category]

        owner_info["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"
        logger.info("owner_field_deleted", category=category, key=key)
        self._save()
        return True

    def create_custom_section(self, section_name: str) -> bool:
        """
        Create a custom owner info section.

        Args:
            section_name: Name for the new section

        Returns:
            True if created, False if limit reached or already exists
        """
        owner_info = self.state.setdefault("owner_info", self._initialize_owner_info())
        custom_sections = owner_info.setdefault("custom_sections", {})

        # Check if already exists
        if section_name in custom_sections:
            return True  # Already exists, that's fine

        # Check limit
        if len(custom_sections) >= self.MAX_CUSTOM_SECTIONS:
            logger.warning("owner_info_max_custom_sections", max=self.MAX_CUSTOM_SECTIONS)
            return False

        # Normalize section name
        section_name = section_name.lower().replace(" ", "_").replace("-", "_")

        # Don't allow overriding predefined categories
        if section_name in self.OWNER_INFO_CATEGORIES:
            logger.warning("owner_info_section_reserved", section=section_name)
            return False

        custom_sections[section_name] = {}
        owner_info["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"
        logger.info("owner_custom_section_created", section=section_name)
        self._save()
        return True

    def delete_custom_section(self, section_name: str) -> bool:
        """
        Delete a custom owner info section and all its fields.

        Args:
            section_name: Name of the section to delete

        Returns:
            True if deleted, False if not found
        """
        owner_info = self.state.get("owner_info", {})
        custom_sections = owner_info.get("custom_sections", {})

        if section_name not in custom_sections:
            return False

        del custom_sections[section_name]
        owner_info["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"
        logger.info("owner_custom_section_deleted", section=section_name)
        self._save()
        return True

    def get_all_owner_fields(self) -> List[Dict[str, Any]]:
        """
        Get all owner info fields as a flat list with category attached.

        Returns:
            List of field dictionaries with category attached
        """
        owner_info = self.state.get("owner_info", {})
        fields = []

        # Standard categories
        for category in ["standard", "physical", "preferences", "people", "dates"]:
            for key, field in owner_info.get(category, {}).items():
                field_copy = field.copy()
                field_copy["category"] = category
                fields.append(field_copy)

        # Dynamic fields
        for field in owner_info.get("dynamic", []):
            field_copy = field.copy()
            field_copy["category"] = "dynamic"
            fields.append(field_copy)

        # Custom sections
        for section_name, section in owner_info.get("custom_sections", {}).items():
            for key, field in section.items():
                field_copy = field.copy()
                field_copy["category"] = section_name
                field_copy["is_custom_section"] = True
                fields.append(field_copy)

        return fields

    def get_injectable_owner_fields(self, is_public_chat: bool = False) -> List[Dict[str, Any]]:
        """
        Get owner fields appropriate for injection into AI context.

        Args:
            is_public_chat: If True, only return public fields.
                           If False, return public + private fields.
                           Secret fields are NEVER returned.

        Returns:
            List of field dictionaries
        """
        all_fields = self.get_all_owner_fields()

        if is_public_chat:
            filtered = [f for f in all_fields if f.get("sensitivity") == "public"]
        else:
            filtered = [f for f in all_fields if f.get("sensitivity") in ("public", "private")]

        # Sort by confidence (highest first)
        filtered.sort(key=lambda f: f.get("confidence", 0), reverse=True)
        return filtered

    def get_owner_info_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for Active Context display.

        Returns:
            Dictionary with counts and field list
        """
        all_fields = self.get_all_owner_fields()
        owner_info = self.state.get("owner_info", {})

        public_count = len([f for f in all_fields if f.get("sensitivity") == "public"])
        private_count = len([f for f in all_fields if f.get("sensitivity") == "private"])
        secret_count = len([f for f in all_fields if f.get("sensitivity") == "secret"])

        # Count populated categories
        categories_populated = 0
        for category in ["standard", "physical", "preferences", "people", "dates"]:
            if owner_info.get(category):
                categories_populated += 1
        if owner_info.get("dynamic"):
            categories_populated += 1

        # Count custom sections
        custom_section_count = len(owner_info.get("custom_sections", {}))

        # Get all fields with category info for display
        top_fields = [
            {
                "key": f["key"],
                "value": f["value"][:200],
                "sensitivity": f["sensitivity"],
                "category": f.get("category", "dynamic"),
                "is_custom": f.get("is_custom_section", False)
            }
            for f in sorted(
                all_fields,
                key=lambda x: (
                    0 if x.get("sensitivity") == "private" else
                    1 if x.get("sensitivity") == "public" else 2,
                    -x.get("confidence", 0)
                )
            )
        ]

        return {
            "total_fields": len(all_fields),
            "public_fields": public_count,
            "private_fields": private_count,
            "secret_fields": secret_count,
            "categories_populated": categories_populated,
            "custom_sections": custom_section_count,
            "last_updated": owner_info.get("last_updated"),
            "fields": top_fields
        }

    def migrate_owner_info_from_file(self, legacy_data: Dict[str, Any]) -> bool:
        """
        Migrate owner info from legacy OwnerInfoManager format.

        Args:
            legacy_data: Data from old owner_info.json file

        Returns:
            True if migration successful
        """
        try:
            owner_info = self.state.setdefault("owner_info", self._initialize_owner_info())

            # Migrate standard categories
            for category in ["standard", "physical", "preferences", "people", "dates"]:
                if category in legacy_data:
                    owner_info[category] = legacy_data[category]

            # Migrate dynamic fields
            if "dynamic" in legacy_data:
                owner_info["dynamic"] = legacy_data["dynamic"]

            # Preserve timestamps
            if "created_at" in legacy_data:
                owner_info["created_at"] = legacy_data["created_at"]

            owner_info["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"

            logger.info("owner_info_migrated_from_file")
            self._save()
            return True
        except Exception as e:
            logger.error("owner_info_migration_failed", error=str(e))
            return False

    # =========================================================================
    # CLEARANCE SETTINGS METHODS (stored under relationships.clearance_settings)
    # =========================================================================

    def _initialize_clearance_settings(self) -> Dict[str, Any]:
        """Initialize empty clearance settings."""
        return {
            "custom_profiles": {},
            "custom_tags": {},
            "auto_suggest_enabled": True
        }

    def _get_clearance_settings(self) -> Dict[str, Any]:
        """Get clearance settings from relationships section."""
        relationships = self.state.setdefault("relationships", {})
        return relationships.setdefault("clearance_settings", self._initialize_clearance_settings())

    def get_clearance_config(self) -> Dict[str, Any]:
        """Get full clearance configuration from relationships.clearance_settings."""
        relationships = self.state.get("relationships", {})
        settings = relationships.get("clearance_settings")
        if not settings:
            return self._initialize_clearance_settings()
        return settings.copy()

    def get_custom_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get a custom profile override by name."""
        settings = self._get_clearance_settings()
        return settings.get("custom_profiles", {}).get(profile_name)

    def set_custom_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> None:
        """
        Set or update a custom clearance profile.

        Args:
            profile_name: Name of the profile (e.g., 'trusted', 'inner_circle')
            profile_data: Profile configuration with keys:
                - name, level, description, categories, fields, excluded_fields, icon, color
        """
        settings = self._get_clearance_settings()
        custom_profiles = settings.setdefault("custom_profiles", {})
        custom_profiles[profile_name] = profile_data
        logger.info("clearance_profile_updated", profile=profile_name)
        self._save()

    def delete_custom_profile(self, profile_name: str) -> bool:
        """Delete a custom profile (reverts to default)."""
        settings = self._get_clearance_settings()
        custom_profiles = settings.get("custom_profiles", {})
        if profile_name in custom_profiles:
            del custom_profiles[profile_name]
            logger.info("clearance_profile_deleted", profile=profile_name)
            self._save()
            return True
        return False

    def get_all_custom_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all custom profile overrides."""
        settings = self._get_clearance_settings()
        return settings.get("custom_profiles", {}).copy()

    def get_custom_tag(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get a custom tag definition by name."""
        settings = self._get_clearance_settings()
        return settings.get("custom_tags", {}).get(tag_name)

    def set_custom_tag(self, tag_name: str, tag_data: Dict[str, Any]) -> None:
        """
        Set or update a custom tag definition.

        Args:
            tag_name: Name of the tag
            tag_data: Tag configuration with keys:
                - name, description, icon, color, implies_clearance
        """
        settings = self._get_clearance_settings()
        custom_tags = settings.setdefault("custom_tags", {})
        custom_tags[tag_name] = tag_data
        logger.info("clearance_tag_updated", tag=tag_name)
        self._save()

    def delete_custom_tag(self, tag_name: str) -> bool:
        """Delete a custom tag definition."""
        settings = self._get_clearance_settings()
        custom_tags = settings.get("custom_tags", {})
        if tag_name in custom_tags:
            del custom_tags[tag_name]
            logger.info("clearance_tag_deleted", tag=tag_name)
            self._save()
            return True
        return False

    def get_all_custom_tags(self) -> Dict[str, Dict[str, Any]]:
        """Get all custom tag definitions."""
        settings = self._get_clearance_settings()
        return settings.get("custom_tags", {}).copy()

    def is_clearance_auto_suggest_enabled(self) -> bool:
        """Check if clearance auto-suggest is enabled."""
        settings = self._get_clearance_settings()
        return settings.get("auto_suggest_enabled", True)

    def set_clearance_auto_suggest(self, enabled: bool) -> None:
        """Enable or disable clearance auto-suggest."""
        settings = self._get_clearance_settings()
        settings["auto_suggest_enabled"] = enabled
        self._save()

    def migrate_clearance_from_file(self, legacy_data: Dict[str, Any]) -> bool:
        """
        Migrate clearance config from legacy clearance/config.json file.

        Args:
            legacy_data: Data from old config.json file

        Returns:
            True if migration successful
        """
        try:
            settings = self._get_clearance_settings()

            if "profiles" in legacy_data:
                settings["custom_profiles"] = legacy_data["profiles"]

            if "custom_tags" in legacy_data:
                settings["custom_tags"] = legacy_data["custom_tags"]

            if "auto_suggest_enabled" in legacy_data:
                settings["auto_suggest_enabled"] = legacy_data["auto_suggest_enabled"]

            logger.info("clearance_config_migrated_to_relationships")
            self._save()
            return True
        except Exception as e:
            logger.error("clearance_migration_failed", error=str(e))
            return False

    # =========================================================================
    # AUTO-ANCHOR METHODS
    # =========================================================================

    def is_auto_anchor_enabled(self, group_chat: bool = False) -> bool:
        """Check if auto-anchor is enabled for the given context.

        Args:
            group_chat: If True, check group chat setting; otherwise individual
        """
        settings = self.state.get("settings", {})
        if group_chat:
            return settings.get("group_auto_anchor_enabled", True)
        return settings.get("individual_auto_anchor_enabled", True)

    def get_auto_anchor_threshold(self, group_chat: bool = False) -> int:
        """Get auto-anchor threshold for the given context.

        Args:
            group_chat: If True, get group chat threshold; otherwise individual
        """
        settings = self.state.get("settings", {})
        if group_chat:
            return settings.get("group_auto_anchor_threshold", 20)
        return settings.get("individual_auto_anchor_threshold", 20)

    def set_auto_anchor(
        self,
        individual_enabled: bool = None,
        individual_threshold: int = None,
        group_enabled: bool = None,
        group_threshold: int = None
    ) -> None:
        """Configure auto-anchor settings for individual and group chats."""
        settings = self.state.setdefault("settings", {})

        # Individual chat settings
        if individual_enabled is not None:
            settings["individual_auto_anchor_enabled"] = individual_enabled
        if individual_threshold is not None:
            settings["individual_auto_anchor_threshold"] = individual_threshold

        # Group chat settings
        if group_enabled is not None:
            settings["group_auto_anchor_enabled"] = group_enabled
        if group_threshold is not None:
            settings["group_auto_anchor_threshold"] = group_threshold

        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    # =========================================================================
    # MODEL MODE METHODS (backward compatible)
    # =========================================================================

    def is_model_locked(self) -> bool:
        """Check if model switching is locked."""
        return self.state.get("settings", {}).get("model_locked", True)

    def get_locked_model(self) -> Optional[str]:
        """Get locked model name."""
        return self.state.get("settings", {}).get("model_locked_to")

    def set_model_lock(self, locked: bool, model_name: str = None) -> None:
        """Lock or unlock model selection."""
        settings = self.state.setdefault("settings", {})
        settings["model_locked"] = locked
        settings["model_locked_to"] = model_name if locked else None
        if locked:
            settings["revolver_mode_enabled"] = False
            settings["autonomous_mode_enabled"] = False
        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    def is_revolver_mode_enabled(self) -> bool:
        """Check if revolver mode is enabled."""
        return self.state.get("settings", {}).get("revolver_mode_enabled", False)

    def set_revolver_mode(self, enabled: bool) -> None:
        """Enable or disable revolver mode."""
        settings = self.state.setdefault("settings", {})
        settings["revolver_mode_enabled"] = enabled
        if enabled:
            # Revolver mode uses random selection from pool - disable conflicting modes
            settings["model_locked"] = False
            settings["autonomous_mode_enabled"] = False
        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    def get_revolver_mode_pool(self) -> List[str]:
        """Get revolver mode model pool."""
        return self.state.get("settings", {}).get("revolver_mode_pool", [])

    def set_revolver_mode_pool(self, models: List[str]) -> None:
        """Set revolver mode model pool."""
        self.state.setdefault("settings", {})["revolver_mode_pool"] = models
        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    # Deprecated: Use get_revolver_mode_pool instead
    def get_revolver_providers(self) -> List[str]:
        """Deprecated: Use get_revolver_mode_pool instead."""
        return self.get_revolver_mode_pool()

    # Deprecated: Use set_revolver_mode_pool instead
    def set_revolver_providers(self, providers: List[str]) -> None:
        """Deprecated: Use set_revolver_mode_pool instead."""
        self.set_revolver_mode_pool(providers)

    # Deprecated: Use get_revolver_mode_pool instead
    def get_revolver_models(self) -> List[str]:
        """Deprecated: Use get_revolver_mode_pool instead."""
        return self.get_revolver_mode_pool()

    # Deprecated: Use set_revolver_mode_pool instead
    def set_revolver_models(self, models: List[str]) -> None:
        """Deprecated: Use set_revolver_mode_pool instead."""
        self.set_revolver_mode_pool(models)

    def is_autonomous_mode_enabled(self) -> bool:
        """Check if autonomous mode is enabled."""
        return self.state.get("settings", {}).get("autonomous_mode_enabled", False)

    def set_autonomous_mode(self, enabled: bool) -> None:
        """Enable or disable autonomous mode."""
        settings = self.state.setdefault("settings", {})
        settings["autonomous_mode_enabled"] = enabled
        if enabled:
            settings["model_locked"] = False
            settings["revolver_mode_enabled"] = False
        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    def get_autonomous_mode_pool(self) -> List[str]:
        """Get autonomous mode model pool."""
        return self.state.get("settings", {}).get("autonomous_mode_pool", [])

    def set_autonomous_mode_pool(self, models: List[str]) -> None:
        """Set autonomous mode model pool."""
        self.state.setdefault("settings", {})["autonomous_mode_pool"] = models
        # Use preserve_gui_fields=False since we're intentionally updating GUI-managed settings
        self._save(preserve_gui_fields=False)

    # Deprecated: Use get_autonomous_mode_pool instead
    def get_autonomous_mode_pools(self) -> Dict[str, List[str]]:
        """Deprecated: Use get_autonomous_mode_pool instead."""
        pool = self.get_autonomous_mode_pool()
        return {"default": pool} if pool else {}

    # Deprecated: Use set_autonomous_mode_pool instead
    def set_autonomous_mode_pools(self, pools: Dict[str, List[str]]) -> None:
        """Deprecated: Use set_autonomous_mode_pool instead."""
        # Flatten all pools into a single list
        all_models = [m for models in pools.values() for m in models]
        self.set_autonomous_mode_pool(all_models)

    # =========================================================================
    # TTS/VOICE SETTINGS METHODS
    # =========================================================================

    def is_tts_enabled(self) -> bool:
        """Check if TTS is enabled."""
        return self.state.get("settings", {}).get("tts_enabled", False)

    def set_tts_enabled(self, enabled: bool) -> None:
        """Enable or disable TTS."""
        settings = self.state.setdefault("settings", {})
        settings["tts_enabled"] = enabled
        self._save(preserve_gui_fields=False)

    def get_voice_model(self) -> str:
        """Get the voice model to use for TTS."""
        return self.state.get("settings", {}).get("voice_model", "openai:alloy")

    def set_voice_model(self, voice_model: str) -> None:
        """Set the voice model for TTS."""
        settings = self.state.setdefault("settings", {})
        settings["voice_model"] = voice_model
        self._save(preserve_gui_fields=False)

    def is_visualizer_enabled(self) -> bool:
        """Check if visualizer is enabled."""
        return self.state.get("settings", {}).get("visualizer_enabled", False)

    def set_visualizer_enabled(self, enabled: bool) -> None:
        """Enable or disable visualizer."""
        settings = self.state.setdefault("settings", {})
        settings["visualizer_enabled"] = enabled
        self._save(preserve_gui_fields=False)

    def get_visualizer_settings(self) -> Optional[Dict[str, Any]]:
        """Get visualizer settings."""
        return self.state.get("settings", {}).get("visualizer_settings")

    def set_visualizer_settings(self, settings_data: Dict[str, Any]) -> None:
        """Set visualizer settings."""
        settings = self.state.setdefault("settings", {})
        settings["visualizer_settings"] = settings_data
        self._save(preserve_gui_fields=False)

    def get_current_model(self) -> str:
        """Get the current AI model (from runtime, falls back to settings)."""
        runtime = self.state.get("runtime", {})
        if runtime.get("current_model"):
            return runtime["current_model"]
        # Fall back to locked model if set
        settings = self.state.get("settings", {})
        if settings.get("model_locked_to"):
            return settings["model_locked_to"]
        return "claude-sonnet-4-20250514"

    def get_current_provider(self) -> str:
        """Get the current AI provider (from runtime)."""
        return self.state.get("runtime", {}).get("current_provider", "anthropic")

    # Backward compatibility aliases
    def is_free_mode_enabled(self) -> bool:
        """Deprecated: Use is_autonomous_mode_enabled instead."""
        return self.is_autonomous_mode_enabled()

    def set_free_mode(self, enabled: bool) -> None:
        """Deprecated: Use set_autonomous_mode instead."""
        self.set_autonomous_mode(enabled)

    # =========================================================================
    # LEGACY METHODS (backward compatibility)
    # =========================================================================

    def set_avatar_description(self, description: str) -> None:
        """Store avatar description."""
        self.state["avatar_description"] = description
        self.state["avatar_description_generated_at"] = int(datetime.now(timezone.utc).timestamp())
        self._save()

    def get_avatar_description(self) -> Optional[str]:
        """Get cached avatar description."""
        return self.state.get("avatar_description")

    def clear_avatar_description(self) -> None:
        """Clear cached avatar description."""
        self.state["avatar_description"] = None
        self.state["avatar_description_generated_at"] = None
        self._save()

    def set_current_model_override(self, model_name: str) -> None:
        """Set model override and update runtime with model and provider."""
        self.state["current_model_override"] = model_name
        runtime = self.state.setdefault("runtime", {})
        runtime["current_model"] = model_name

        # Derive provider from model name
        try:
            from ai.model_registry import ModelRegistry
            model_info = ModelRegistry.get_model_info(model_name)
            if model_info:
                runtime["current_provider"] = model_info["provider"]
        except Exception:
            # Fallback: infer provider from model name
            model_lower = model_name.lower()
            if "claude" in model_lower:
                runtime["current_provider"] = "anthropic"
            elif "gpt" in model_lower:
                runtime["current_provider"] = "openai"
            elif "gemini" in model_lower:
                runtime["current_provider"] = "google"
            elif "sonar" in model_lower:
                runtime["current_provider"] = "perplexity"
            elif "grok" in model_lower:
                runtime["current_provider"] = "xai"
            elif "venice" in model_lower:
                runtime["current_provider"] = "venice"
            elif any(x in model_lower for x in ["llama", "mistral", "qwen"]):
                runtime["current_provider"] = "ollama"

        self._save()

    def get_current_model_override(self) -> Optional[str]:
        """Get current model override."""
        return self.state.get("current_model_override")

    def clear_current_model_override(self) -> None:
        """Clear model override."""
        self.state["current_model_override"] = None
        self._save()

    # =========================================================================
    # RUNTIME STATE METHODS
    # =========================================================================

    def update_runtime(
        self,
        current_model: str = None,
        current_provider: str = None,
        is_online: bool = None,
        last_api_call: int = None,
        active_conversation_id: str = None
    ) -> None:
        """
        Update runtime state. Only updates provided fields.

        Args:
            current_model: Currently active AI model
            current_provider: Current provider (anthropic, openai, etc.)
            is_online: Whether the Qube is online/active
            last_api_call: Timestamp of last API call
            active_conversation_id: Current conversation/session ID
        """
        runtime = self.state.setdefault("runtime", {})

        if current_model is not None:
            runtime["current_model"] = current_model
        if current_provider is not None:
            runtime["current_provider"] = current_provider
        if is_online is not None:
            runtime["is_online"] = is_online
        if last_api_call is not None:
            runtime["last_api_call"] = last_api_call
        if active_conversation_id is not None:
            runtime["active_conversation_id"] = active_conversation_id

        self._save()

    def record_api_call(self, model: str, provider: str) -> None:
        """Record an API call - updates runtime with model, provider, and timestamp."""
        now = int(datetime.now(timezone.utc).timestamp())
        runtime = self.state.setdefault("runtime", {})
        runtime["current_model"] = model
        runtime["current_provider"] = provider
        runtime["last_api_call"] = now
        runtime["is_online"] = True
        self._save()

    def get_runtime(self) -> Dict[str, Any]:
        """Get current runtime state."""
        return self.state.get("runtime", {}).copy()

    def set_online(self, is_online: bool) -> None:
        """Set online status."""
        runtime = self.state.setdefault("runtime", {})
        runtime["is_online"] = is_online
        self._save()

    def get_state(self) -> Dict[str, Any]:
        """Get full state dict (for debugging)."""
        return self.state.copy()

    def get_ipfs_state(self) -> Dict[str, Any]:
        """Get state for IPFS anchoring (excludes ephemeral sections)."""
        state = self.state.copy()
        for section in self.IPFS_EXCLUDED_SECTIONS:
            state.pop(section, None)
        return state

    # =========================================================================
    # STAGED SESSION (Transactional Consistency)
    # =========================================================================
    #
    # Session-scoped data stays in memory until the session is anchored.
    # This eliminates the need for snapshots and rollback - changes simply
    # aren't persisted until commit.
    #
    # Flow:
    # 1. begin_staged_session() - Start staging (changes stay in memory)
    # 2. During session - _save() excludes staged sections from disk
    # 3. commit_staged_session() - Write staged changes to disk (on anchor)
    # 4. discard_staged_session() - Reload from disk, discarding memory changes
    #
    # On crash: staged changes are lost, disk has pre-session state (same as discard)

    # Sections that are session-scoped (staged until anchor)
    # These represent changes made during conversation
    SESSION_SCOPED_SECTIONS = {"skills", "relationships", "mood", "owner_info"}

    # Specific stats fields that are session-scoped (committed at anchor, rolled back on discard)
    # These are derived from session blocks at anchor time, not tracked incrementally.
    # During session, display logic adds pending counts from session block files.
    # This works with subprocess architecture (no in-memory state needed).
    SESSION_SCOPED_STATS = {"total_messages_sent", "total_messages_received", "total_tool_calls"}

    # Sections that persist immediately (even during staged session)
    # - settings: GUI-managed, user explicitly changed
    # - financial: Blockchain transactions are irrevocable
    # - chain: Block tracking is canonical state
    # Note: Some stats (tokens, costs) persist because real money was spent
    IMMEDIATELY_PERSISTENT_SECTIONS = {"settings", "financial", "chain", "block_counts"}

    def begin_staged_session(self) -> None:
        """
        Begin a staged session.

        While staged, session-scoped sections (skills, relationships, mood, owner_info)
        and session-scoped stats are kept in memory only. They won't be written to disk
        until commit_staged_session() is called.

        Call this when starting a new conversation session.
        """
        if self._staged_session_active:
            logger.warning("staged_session_already_active", qube_id=self.state.get("qube_id"))
            return

        # Record baseline for session-scoped stats (for reference, not rollback)
        stats = self.state.get("stats", {})
        self._staged_stats_baseline = {
            field: stats.get(field, 0)
            for field in self.SESSION_SCOPED_STATS
        }

        self._staged_session_active = True

        logger.info(
            "staged_session_started",
            sections=list(self.SESSION_SCOPED_SECTIONS),
            stats_fields=list(self.SESSION_SCOPED_STATS),
            qube_id=self.state.get("qube_id")
        )

    def commit_staged_session(self, pending_stats: Dict[str, int] = None) -> None:
        """
        Commit staged session data to disk.

        Called when session is successfully anchored. Writes all in-memory
        session-scoped changes to disk.

        Args:
            pending_stats: Pre-calculated pending stats from session blocks.
                           If provided, uses these instead of reading from disk.
                           Required when session block files are deleted before commit.
                           Expected keys: messages_sent, messages_received, tool_calls
        """
        if not self._staged_session_active:
            logger.debug("commit_staged_session_not_active", qube_id=self.state.get("qube_id"))
            return

        # Get message/tool counts - prefer pre-calculated if provided (session blocks may be deleted)
        if pending_stats:
            # Use pre-calculated counts passed from anchor_to_chain
            pending_sent = pending_stats.get("messages_sent", 0)
            pending_received = pending_stats.get("messages_received", 0)
            pending_tool_calls = pending_stats.get("tool_calls", 0)
        else:
            # Fall back to reading from session block files (for backward compatibility)
            pending = self.get_pending_session_stats()
            pending_sent = pending["pending_messages_sent"]
            pending_received = pending["pending_messages_received"]
            pending_tool_calls = pending["pending_tool_calls"]

        stats = self.state.setdefault("stats", {})
        stats["total_messages_sent"] = stats.get("total_messages_sent", 0) + pending_sent
        stats["total_messages_received"] = stats.get("total_messages_received", 0) + pending_received
        stats["total_tool_calls"] = stats.get("total_tool_calls", 0) + pending_tool_calls

        # Clear staged flag BEFORE saving so changes are written to disk
        self._staged_session_active = False
        self._staged_stats_baseline = {}

        # Reset session_blocks counter (session blocks are now permanent)
        chain = self.state.get("chain", {})
        chain["session_blocks"] = 0

        # Save everything (including previously staged sections)
        self._save()

        logger.info(
            "staged_session_committed",
            qube_id=self.state.get("qube_id")
        )

    def discard_staged_session(self) -> bool:
        """
        Discard staged session changes by reloading from disk.

        Called when session is discarded without anchoring. Reloads session-scoped
        sections from disk, effectively discarding all in-memory changes.

        Returns:
            True if discard was performed, False if no staged session was active
        """
        if not self._staged_session_active:
            logger.debug("discard_staged_session_not_active", qube_id=self.state.get("qube_id"))
            return False

        # Clear staged flag
        self._staged_session_active = False
        self._staged_stats_baseline = {}

        # Reload from disk to get the pre-session state
        # This will overwrite in-memory changes with disk values
        self._load()

        logger.info(
            "staged_session_discarded",
            qube_id=self.state.get("qube_id")
        )

        return True

    def is_staged_session_active(self) -> bool:
        """Check if a staged session is currently active."""
        return self._staged_session_active

    # Legacy method aliases for compatibility during transition
    def snapshot_session_data(self) -> None:
        """Legacy alias for begin_staged_session()."""
        self.begin_staged_session()

    def commit_session_data(self, pending_stats: Dict[str, int] = None) -> None:
        """Legacy alias for commit_staged_session()."""
        self.commit_staged_session(pending_stats=pending_stats)

    def rollback_session_data(self) -> bool:
        """Legacy alias for discard_staged_session()."""
        return self.discard_staged_session()

    def has_session_snapshot(self) -> bool:
        """Legacy alias for is_staged_session_active()."""
        return self.is_staged_session_active()

    # =========================================================================
    # UNIFIED ACCESS METHODS (for AI tools)
    # =========================================================================

    # Available sections for unified access
    ACCESSIBLE_SECTIONS = {
        "chain", "session", "settings", "runtime", "stats",
        "skills", "relationships", "financial", "mood", "health",
        "owner_info", "block_counts"
    }

    def get_sections(self, sections: List[str] = None) -> Dict[str, Any]:
        """
        Get chain_state data for specific sections or all sections.

        Args:
            sections: List of section names to retrieve.
                     If None or empty, returns all accessible sections.
                     Valid sections: chain, session, settings, runtime, stats,
                                    skills, relationships, financial, mood,
                                    health, owner_info, block_counts

        Returns:
            Dictionary with requested sections
        """
        # If no sections specified, return all accessible
        if not sections:
            sections = list(self.ACCESSIBLE_SECTIONS)

        result = {}
        for section in sections:
            if section not in self.ACCESSIBLE_SECTIONS:
                continue

            if section == "owner_info":
                # Special handling for owner_info summary
                result["owner_info"] = self.get_owner_info_summary()
            elif section == "relationships":
                # Include clearance_settings with relationships
                rel_data = self.state.get("relationships", {}).copy()
                result["relationships"] = rel_data
            else:
                data = self.state.get(section)
                if data is not None:
                    result[section] = data.copy() if isinstance(data, dict) else data

        return result

    def update_section(
        self,
        section: str,
        path: str = None,
        value: Any = None,
        operation: str = "set"
    ) -> Dict[str, Any]:
        """
        Update a specific part of chain_state.

        Args:
            section: Section name (e.g., 'owner_info', 'relationships', 'mood')
            path: Dot-notation path within section (e.g., 'standard.name' for owner_info)
            value: Value to set/add
            operation: 'set' (replace), 'delete' (remove), 'append' (add to list)

        Returns:
            {"success": bool, "message": str}
        """
        if section not in self.ACCESSIBLE_SECTIONS:
            return {"success": False, "message": f"Invalid section: {section}"}

        try:
            # Special handling for specific sections
            if section == "owner_info":
                return self._update_owner_info_section(path, value, operation)
            elif section == "relationships":
                return self._update_relationships_section(path, value, operation)
            elif section == "mood":
                return self._update_mood_section(path, value, operation)
            elif section == "skills":
                return self._update_skills_section(path, value, operation)
            elif section == "settings":
                return self._update_settings_section(path, value, operation)
            else:
                return {"success": False, "message": f"Section '{section}' is read-only via this method"}

        except Exception as e:
            logger.error("update_section_failed", section=section, path=path, error=str(e))
            return {"success": False, "message": str(e)}

    def _update_owner_info_section(self, path: str, value: Any, operation: str) -> Dict[str, Any]:
        """Handle owner_info updates via unified interface."""
        if not path:
            return {"success": False, "message": "Path required for owner_info updates"}

        parts = path.split(".")
        if len(parts) < 2:
            return {"success": False, "message": "Path must be 'category.key' format"}

        category = parts[0]
        key = parts[1]

        if operation == "set":
            # value should be the field value, or a dict with value/sensitivity
            if isinstance(value, dict):
                success = self.set_owner_field(
                    category=category,
                    key=key,
                    value=value.get("value", ""),
                    sensitivity=value.get("sensitivity"),
                    source=value.get("source", "explicit"),
                    confidence=value.get("confidence", 100)
                )
            else:
                success = self.set_owner_field(category=category, key=key, value=str(value))

            if success:
                return {"success": True, "message": f"Set owner_info.{category}.{key}"}
            else:
                return {"success": False, "message": "Failed to set field (may have hit limits)"}

        elif operation == "delete":
            success = self.delete_owner_field(category, key)
            if success:
                return {"success": True, "message": f"Deleted owner_info.{category}.{key}"}
            else:
                return {"success": False, "message": "Field not found"}

        return {"success": False, "message": f"Unknown operation: {operation}"}

    def _update_relationships_section(self, path: str, value: Any, operation: str) -> Dict[str, Any]:
        """Handle relationships updates via unified interface."""
        if not path:
            return {"success": False, "message": "Path required for relationships updates"}

        parts = path.split(".")

        # Handle clearance_settings
        if parts[0] == "clearance_settings":
            if len(parts) < 3:
                return {"success": False, "message": "Path must be 'clearance_settings.type.name'"}

            setting_type = parts[1]  # custom_profiles or custom_tags
            name = parts[2]

            if setting_type == "custom_profiles":
                if operation == "set":
                    self.set_custom_profile(name, value)
                    return {"success": True, "message": f"Set custom profile '{name}'"}
                elif operation == "delete":
                    if self.delete_custom_profile(name):
                        return {"success": True, "message": f"Deleted custom profile '{name}'"}
                    return {"success": False, "message": "Profile not found"}

            elif setting_type == "custom_tags":
                if operation == "set":
                    self.set_custom_tag(name, value)
                    return {"success": True, "message": f"Set custom tag '{name}'"}
                elif operation == "delete":
                    if self.delete_custom_tag(name):
                        return {"success": True, "message": f"Deleted custom tag '{name}'"}
                    return {"success": False, "message": "Tag not found"}

        # Handle entity relationships
        elif parts[0] == "entities" and len(parts) >= 2:
            entity_id = parts[1]
            if operation == "set":
                self.update_relationship(entity_id, value)
                return {"success": True, "message": f"Updated relationship with '{entity_id}'"}
            elif operation == "delete":
                if self.delete_relationship(entity_id):
                    return {"success": True, "message": f"Deleted relationship with '{entity_id}'"}
                return {"success": False, "message": "Relationship not found"}

        return {"success": False, "message": f"Invalid path for relationships: {path}"}

    def _update_mood_section(self, path: str, value: Any, operation: str) -> Dict[str, Any]:
        """Handle mood updates via unified interface."""
        if operation != "set":
            return {"success": False, "message": "Mood only supports 'set' operation"}

        if path == "current_mood":
            self.update_mood(mood=value)
            return {"success": True, "message": f"Set mood to '{value}'"}
        elif path == "energy_level":
            self.update_mood(energy_level=int(value))
            return {"success": True, "message": f"Set energy level to {value}"}
        elif path == "stress_level":
            self.update_mood(stress_level=int(value))
            return {"success": True, "message": f"Set stress level to {value}"}

        return {"success": False, "message": f"Invalid mood path: {path}"}

    def _update_skills_section(self, path: str, value: Any, operation: str) -> Dict[str, Any]:
        """Handle skills updates via unified interface."""
        if not path:
            return {"success": False, "message": "Path required (skill_id)"}

        skill_id = path.split(".")[0]

        if operation == "set":
            # Unlock skill or add XP
            if isinstance(value, dict) and "xp" in value:
                self.add_skill_xp(skill_id, value["xp"], value.get("reason"))
                return {"success": True, "message": f"Added {value['xp']} XP to skill '{skill_id}'"}
            else:
                self.unlock_skill(skill_id, xp=int(value) if value else 0)
                return {"success": True, "message": f"Unlocked skill '{skill_id}'"}

        return {"success": False, "message": f"Skills only supports 'set' operation"}

    def _update_settings_section(self, path: str, value: Any, operation: str) -> Dict[str, Any]:
        """Handle settings updates via unified interface."""
        if not path:
            return {"success": False, "message": "Path (setting key) required"}

        if operation == "set":
            self.update_settings({path: value})
            return {"success": True, "message": f"Set setting '{path}'"}

        return {"success": False, "message": f"Settings only supports 'set' operation"}
