"""
Chain State Management

Persistent tracking of memory chain state, session state, and usage metrics.
From docs/05_Data_Structures.md Section 2.3 (lines 1120-1173)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from utils.logging import get_logger
from utils.file_lock import FileLock

logger = get_logger(__name__)


class ChainState:
    """
    Manages chain_state.json persistence

    Tracks:
    - Chain state (length, last block, merkle root)
    - Session state (current session, block count, indexes)
    - Block type counts
    - Usage tracking (tokens, API costs)
    - Health metrics

    From docs Section 2.3
    """

    def __init__(self, qube_id: str, data_dir: Path):
        """
        Initialize chain state

        Args:
            qube_id: Qube ID
            data_dir: Path to Qube's data directory (e.g., data/qubes/Athena_A1B2C3D4/)
        """
        self.qube_id = qube_id
        self.state_file = data_dir / "chain_state.json"
        self.lock_file = data_dir / ".chain_state.lock"

        # Load existing state or create new
        if self.state_file.exists():
            self._load()
        else:
            self._initialize_new_state()

        logger.info("chain_state_loaded", qube_id=qube_id, state_file=str(self.state_file))

    def _initialize_new_state(self) -> None:
        """Initialize new chain state with defaults"""
        self.state = {
            "qube_id": self.qube_id,

            # Chain state
            "chain_length": 0,
            "last_block_number": -1,
            "last_block_hash": "0" * 64,
            "last_merkle_root": None,
            "last_anchor_block": None,

            # Current session state
            "current_session_id": None,
            "session_block_count": 0,
            "next_negative_index": -1,
            "session_start_timestamp": None,
            "auto_anchor_enabled": False,
            "auto_anchor_threshold": 50,

            # Block type counts
            "block_counts": {
                "GENESIS": 0,
                "THOUGHT": 0,
                "ACTION": 0,
                "OBSERVATION": 0,
                "MESSAGE": 0,
                "DECISION": 0,
                "MEMORY_ANCHOR": 0,
                "COLLABORATIVE_MEMORY": 0,
                "SUMMARY": 0
            },

            # Usage tracking
            "total_tokens_used": 0,
            "total_api_cost": 0.0,
            "tokens_by_model": {},
            "api_calls_by_tool": {},

            # Health metrics
            "last_updated": int(datetime.now(timezone.utc).timestamp()),
            "last_backup": None,
            "integrity_verified": True,
            "merkle_tree_valid": True,

            # Avatar description (cached vision analysis)
            "avatar_description": None,
            "avatar_description_generated_at": None,

            # Model preferences and switching
            "model_preferences": {},  # task_type -> {model, reason, set_at}
            "current_model_override": None,  # Persists model switch across sessions
            "model_locked": True,  # Manual mode is the default
            "model_locked_to": None,  # When locked, forced to this model
            "revolver_mode_enabled": False,  # Privacy mode - rotate providers
            "revolver_last_index": 0,  # Track rotation position
            "revolver_providers": [],  # Providers to include in revolver mode (empty = all)
            "revolver_models": [],  # Specific models to include (empty = all from providers)
            "revolver_first_response_done": False,  # Track if first response has been made
            "revolver_enabled_at": 0,  # Timestamp when revolver mode was enabled
            "revolver_last_response_at": 0,  # Timestamp of last revolver response

            # Autonomous mode settings
            "free_mode": False,  # Autonomous mode - off by default (Manual is default)
            "free_mode_models": [],  # Models available in free mode (empty = all configured)
        }

        self._save()

    def _load(self) -> None:
        """Load state from disk with file locking"""
        lock = FileLock(self.lock_file, timeout=5.0)

        try:
            with lock:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)

                logger.debug("chain_state_loaded_from_disk", qube_id=self.qube_id)

        except Exception as e:
            logger.error("chain_state_load_failed", error=str(e), exc_info=True)
            # Initialize new state on failure
            self._initialize_new_state()

    def reload(self) -> None:
        """
        Reload state from disk, picking up any external changes.

        This is useful when other processes (like the GUI) may have modified
        the chain_state.json file directly.
        """
        if self.state_file.exists():
            self._load()
            logger.debug("chain_state_reloaded", qube_id=self.qube_id)

    def _save(self) -> None:
        """Save state to disk with file locking to prevent concurrent write conflicts.

        IMPORTANT: This method merges with disk state to preserve GUI-managed settings.
        The GUI writes directly to chain_state.json for settings like model mode,
        so we must not overwrite those fields with stale in-memory values.
        """
        import time

        # Fields that the GUI manages directly - always prefer disk values
        GUI_MANAGED_FIELDS = {
            "model_locked",
            "model_locked_to",
            "revolver_mode_enabled",
            "revolver_providers",
            "revolver_models",
            "revolver_first_response_done",
            "revolver_enabled_at",
            "revolver_last_response_at",
            "free_mode",
            "free_mode_models",
            "auto_anchor_enabled",
            "auto_anchor_threshold",
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                lock = FileLock(self.lock_file, timeout=5.0)

                with lock:
                    # Load current disk state to merge with
                    disk_state = {}
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                disk_state = json.load(f)
                        except Exception:
                            pass  # Will use in-memory state if disk read fails

                    # Start with in-memory state
                    merged_state = self.state.copy()

                    # Preserve GUI-managed fields from disk state
                    for field in GUI_MANAGED_FIELDS:
                        if field in disk_state:
                            merged_state[field] = disk_state[field]

                    # Update last_updated timestamp
                    merged_state["last_updated"] = int(datetime.now(timezone.utc).timestamp())

                    # Ensure parent directory exists
                    self.state_file.parent.mkdir(parents=True, exist_ok=True)

                    # Write atomically (write to temp, then rename)
                    temp_file = self.state_file.with_suffix('.json.tmp')
                    with open(temp_file, 'w') as f:
                        json.dump(merged_state, f, indent=2)
                        f.flush()  # Ensure data is written
                        import os
                        os.fsync(f.fileno())  # Force OS to flush to disk

                    temp_file.replace(self.state_file)

                    # Update in-memory state to match what was saved
                    self.state = merged_state

                    logger.debug("chain_state_saved", qube_id=self.qube_id)
                    return  # Success

            except Exception as e:
                last_error = e
                logger.warning(
                    "chain_state_save_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # All retries failed
        logger.error(
            "chain_state_save_failed_all_retries",
            error=str(last_error),
            qube_id=self.qube_id,
            exc_info=True
        )

    # =============================================================================
    # Chain State Updates
    # =============================================================================

    def update_chain(
        self,
        chain_length: Optional[int] = None,
        last_block_number: Optional[int] = None,
        last_block_hash: Optional[str] = None,
        last_merkle_root: Optional[str] = None,
        last_anchor_block: Optional[int] = None
    ) -> None:
        """Update chain state fields"""
        if chain_length is not None:
            self.state["chain_length"] = chain_length
        if last_block_number is not None:
            self.state["last_block_number"] = last_block_number
        if last_block_hash is not None:
            self.state["last_block_hash"] = last_block_hash
        if last_merkle_root is not None:
            self.state["last_merkle_root"] = last_merkle_root
        if last_anchor_block is not None:
            self.state["last_anchor_block"] = last_anchor_block

        self._save()

    def increment_block_count(self, block_type: str) -> None:
        """Increment count for a block type"""
        if block_type in self.state["block_counts"]:
            self.state["block_counts"][block_type] += 1
        else:
            self.state["block_counts"][block_type] = 1

        self._save()

    # =============================================================================
    # Session State Updates
    # =============================================================================

    def start_session(self, session_id: str) -> None:
        """Start new session"""
        # Only reset values if there's no active session
        # In multi-qube conversations, sessions may be started multiple times
        # but we don't want to reset chain_state if session is already in progress
        if self.state.get("current_session_id") is None:
            self.state["session_block_count"] = 0
            self.state["next_negative_index"] = -1

        self.state["current_session_id"] = session_id
        self.state["session_start_timestamp"] = int(datetime.now(timezone.utc).timestamp())

        self._save()

        logger.info("session_started_in_state", session_id=session_id)

    def update_session(
        self,
        session_block_count: Optional[int] = None,
        next_negative_index: Optional[int] = None
    ) -> None:
        """Update session state"""
        if session_block_count is not None:
            self.state["session_block_count"] = session_block_count
        if next_negative_index is not None:
            self.state["next_negative_index"] = next_negative_index

        self._save()

    def end_session(self) -> None:
        """End current session"""
        self.state["current_session_id"] = None
        self.state["session_block_count"] = 0
        self.state["next_negative_index"] = -1
        self.state["session_start_timestamp"] = None

        self._save()

        logger.info("session_ended_in_state", qube_id=self.qube_id)

    def set_auto_anchor(self, enabled: bool, threshold: int = 50) -> None:
        """Configure auto-anchor settings"""
        self.state["auto_anchor_enabled"] = enabled
        self.state["auto_anchor_threshold"] = threshold

        self._save()

        logger.info("auto_anchor_configured", enabled=enabled, threshold=threshold)

    # =============================================================================
    # Usage Tracking
    # =============================================================================

    def add_tokens(self, model: str, tokens: int, cost: float = 0.0) -> None:
        """Track token usage and costs"""
        self.state["total_tokens_used"] += tokens
        self.state["total_api_cost"] += cost

        # Track by model
        if model not in self.state["tokens_by_model"]:
            self.state["tokens_by_model"][model] = 0
        self.state["tokens_by_model"][model] += tokens

        self._save()

    def increment_tool_call(self, tool_name: str) -> None:
        """Track tool/API calls"""
        if tool_name not in self.state["api_calls_by_tool"]:
            self.state["api_calls_by_tool"][tool_name] = 0
        self.state["api_calls_by_tool"][tool_name] += 1

        self._save()

    # =============================================================================
    # Health Metrics
    # =============================================================================

    def update_health(
        self,
        last_backup: Optional[int] = None,
        integrity_verified: Optional[bool] = None,
        merkle_tree_valid: Optional[bool] = None
    ) -> None:
        """Update health metrics"""
        if last_backup is not None:
            self.state["last_backup"] = last_backup
        if integrity_verified is not None:
            self.state["integrity_verified"] = integrity_verified
        if merkle_tree_valid is not None:
            self.state["merkle_tree_valid"] = merkle_tree_valid

        self._save()

    # =============================================================================
    # Getters
    # =============================================================================

    def get_chain_length(self) -> int:
        """Get current chain length"""
        return self.state["chain_length"]

    def get_last_block_hash(self) -> str:
        """Get last block hash"""
        return self.state["last_block_hash"]

    def get_session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self.state["current_session_id"]

    def get_session_block_count(self) -> int:
        """Get current session block count"""
        return self.state["session_block_count"]

    def get_next_negative_index(self) -> int:
        """Get next negative index for session blocks"""
        return self.state["next_negative_index"]

    def is_auto_anchor_enabled(self) -> bool:
        """Check if auto-anchor is enabled"""
        return self.state["auto_anchor_enabled"]

    def get_auto_anchor_threshold(self) -> int:
        """Get auto-anchor threshold"""
        return self.state["auto_anchor_threshold"]

    def get_state(self) -> Dict[str, Any]:
        """Get full state dict (for debugging/inspection)"""
        return self.state.copy()

    def get_block_counts(self) -> Dict[str, int]:
        """Get block type counts"""
        return self.state["block_counts"].copy()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_tokens": self.state["total_tokens_used"],
            "total_cost": self.state["total_api_cost"],
            "tokens_by_model": self.state["tokens_by_model"].copy(),
            "api_calls_by_tool": self.state["api_calls_by_tool"].copy()
        }

    # =============================================================================
    # Avatar Description Management
    # =============================================================================

    def set_avatar_description(self, description: str) -> None:
        """
        Store avatar description (cached from vision analysis)

        Args:
            description: First-person avatar description from vision AI
        """
        self.state["avatar_description"] = description
        self.state["avatar_description_generated_at"] = int(datetime.now(timezone.utc).timestamp())

        self._save()

        logger.info("avatar_description_cached", qube_id=self.qube_id, length=len(description))

    def get_avatar_description(self) -> Optional[str]:
        """
        Get cached avatar description

        Returns:
            Avatar description string or None if not set
        """
        return self.state.get("avatar_description")

    def clear_avatar_description(self) -> None:
        """Clear cached avatar description (force regeneration on next request)"""
        self.state["avatar_description"] = None
        self.state["avatar_description_generated_at"] = None

        self._save()

        logger.info("avatar_description_cleared", qube_id=self.qube_id)

    # =============================================================================
    # Model Preferences
    # =============================================================================

    def set_model_preference(self, task_type: str, model_name: str, reason: str = None) -> None:
        """
        Save a model preference for a task type.

        Args:
            task_type: Category of task (e.g., 'coding', 'creative_writing', 'research')
            model_name: Model to use for this task type
            reason: Optional reason for this preference
        """
        # Initialize if missing (backward compatibility)
        if "model_preferences" not in self.state:
            self.state["model_preferences"] = {}

        self.state["model_preferences"][task_type] = {
            "model": model_name,
            "reason": reason,
            "set_at": int(datetime.now(timezone.utc).timestamp())
        }

        self._save()

        logger.info(
            "model_preference_set",
            qube_id=self.qube_id,
            task_type=task_type,
            model=model_name
        )

    def get_model_preference(self, task_type: str) -> Optional[Dict[str, Any]]:
        """
        Get model preference for a task type.

        Args:
            task_type: Category of task

        Returns:
            Dict with model, reason, set_at or None if not set
        """
        preferences = self.state.get("model_preferences", {})
        return preferences.get(task_type)

    def get_all_model_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored model preferences."""
        return self.state.get("model_preferences", {}).copy()

    def clear_model_preference(self, task_type: str) -> None:
        """Clear preference for a specific task type."""
        preferences = self.state.get("model_preferences", {})
        if task_type in preferences:
            del preferences[task_type]
            self.state["model_preferences"] = preferences
            self._save()

            logger.info("model_preference_cleared", qube_id=self.qube_id, task_type=task_type)

    def clear_all_model_preferences(self) -> None:
        """Clear all model preferences."""
        self.state["model_preferences"] = {}
        self._save()

        logger.info("all_model_preferences_cleared", qube_id=self.qube_id)

    # =============================================================================
    # Model Override
    # =============================================================================

    def set_current_model_override(self, model_name: str) -> None:
        """
        Set model override (persists across sessions).

        Args:
            model_name: Model to use as override
        """
        self.state["current_model_override"] = model_name
        self._save()

        logger.info("model_override_set", qube_id=self.qube_id, model=model_name)

    def get_current_model_override(self) -> Optional[str]:
        """Get current model override, if any."""
        return self.state.get("current_model_override")

    def clear_current_model_override(self) -> None:
        """Clear model override (return to genesis model)."""
        self.state["current_model_override"] = None
        self._save()

        logger.info("model_override_cleared", qube_id=self.qube_id)

    # =============================================================================
    # Model Lock (User Control)
    # =============================================================================

    def set_model_lock(self, locked: bool, model_name: str = None) -> None:
        """
        Lock or unlock the Qube's ability to switch models.

        Args:
            locked: True to lock, False to unlock
            model_name: When locking, optionally force a specific model
        """
        self.state["model_locked"] = locked
        self.state["model_locked_to"] = model_name if locked else None
        self._save()

        logger.info(
            "model_lock_changed",
            qube_id=self.qube_id,
            locked=locked,
            model=model_name
        )

    def is_model_locked(self) -> bool:
        """Check if model switching is locked by user."""
        return self.state.get("model_locked", False)

    def get_locked_model(self) -> Optional[str]:
        """Get the model that switching is locked to, if any."""
        return self.state.get("model_locked_to")

    # =============================================================================
    # Revolver Mode
    # =============================================================================

    def set_revolver_mode(self, enabled: bool) -> None:
        """
        Enable or disable revolver mode (privacy feature).

        When enabled, rotates providers for each response.
        """
        self.state["revolver_mode_enabled"] = enabled
        if enabled:
            # Reset index and first response flag when enabling
            self.state["revolver_last_index"] = 0
            self.state["revolver_first_response_done"] = False
            # Record timestamp for first-response detection
            import time
            self.state["revolver_enabled_at"] = int(time.time())
        self._save()

        logger.info("revolver_mode_changed", qube_id=self.qube_id, enabled=enabled)

    def is_revolver_mode_enabled(self) -> bool:
        """Check if revolver mode is enabled."""
        return self.state.get("revolver_mode_enabled", False)

    def get_next_revolver_index(self, num_providers: int) -> int:
        """
        Get the next provider index for revolver mode.

        Args:
            num_providers: Total number of available providers

        Returns:
            Index of next provider to use
        """
        if num_providers <= 0:
            return 0
        current = self.state.get("revolver_last_index", 0)
        return current % num_providers

    def increment_revolver_index(self, num_providers: int) -> None:
        """
        Increment revolver index for next rotation.

        Args:
            num_providers: Total number of available providers
        """
        if num_providers <= 0:
            return
        current = self.state.get("revolver_last_index", 0)
        self.state["revolver_last_index"] = (current + 1) % num_providers
        self._save()

    def is_revolver_first_response_done(self) -> bool:
        """
        Check if first response has been made since enabling revolver mode.

        Uses both flag AND timestamp for reliability. First response is NOT done if:
        - Flag is False, OR
        - Last response timestamp is before/equal to enabled timestamp (or 0)
        """
        flag = self.state.get("revolver_first_response_done", False)
        enabled_at = self.state.get("revolver_enabled_at", 0)
        last_response_at = self.state.get("revolver_last_response_at", 0)

        # First response is done only if flag is True AND last_response is after enabled_at
        if not flag:
            return False
        if enabled_at > 0 and last_response_at <= enabled_at:
            return False
        return True

    def set_revolver_first_response_done(self) -> None:
        """Mark that the first response has been made since enabling revolver mode."""
        import time
        self.state["revolver_first_response_done"] = True
        self.state["revolver_last_response_at"] = int(time.time())
        self._save()

    def set_revolver_providers(self, providers: list[str]) -> None:
        """
        Set the list of providers to include in revolver mode rotation.

        Args:
            providers: List of provider names (e.g., ['venice', 'google', 'openai']).
                      Empty list means use all configured providers.
        """
        self.state["revolver_providers"] = providers
        logger.info("revolver_providers_set", qube_id=self.qube_id, providers=providers)
        self._save()

    def get_revolver_providers(self) -> list[str]:
        """
        Get the list of providers to include in revolver mode rotation.

        Returns:
            List of provider names, or empty list if all providers should be used.
        """
        return self.state.get("revolver_providers", [])

    def set_revolver_models(self, models: list[str]) -> None:
        """
        Set the list of specific models to include in revolver mode rotation.

        Args:
            models: List of model IDs (e.g., ['gpt-5.2', 'claude-sonnet-4.5']).
                   Empty list means use all models from selected providers.
        """
        self.state["revolver_models"] = models
        logger.info("revolver_models_set", qube_id=self.qube_id, model_count=len(models))
        self._save()

    def get_revolver_models(self) -> list[str]:
        """
        Get the list of specific models to include in revolver mode rotation.

        Returns:
            List of model IDs, or empty list if all models should be used.
        """
        return self.state.get("revolver_models", [])

    def set_free_mode_models(self, models: list[str]) -> None:
        """
        Set the list of models available in free mode (autonomous selection).

        Args:
            models: List of model IDs (e.g., ['gpt-5.2', 'claude-sonnet-4.5']).
                   Empty list means all configured models are available.
        """
        self.state["free_mode_models"] = models
        logger.info("free_mode_models_set", qube_id=self.qube_id, model_count=len(models))
        self._save()

    def get_free_mode_models(self) -> list[str]:
        """
        Get the list of models available in free mode.

        Returns:
            List of model IDs, or empty list if all models are available.
        """
        return self.state.get("free_mode_models", [])

    def set_free_mode(self, enabled: bool) -> None:
        """
        Enable or disable free mode (autonomous model selection).

        Args:
            enabled: True to enable free mode, False to disable
        """
        self.state["free_mode"] = enabled
        logger.info("free_mode_set", qube_id=self.qube_id, enabled=enabled)
        self._save()

    def is_free_mode_enabled(self) -> bool:
        """
        Check if free mode is enabled.

        Returns:
            True if free mode is enabled, False otherwise.
            Defaults to False (model_locked is the default mode).
        """
        return self.state.get("free_mode", False)
