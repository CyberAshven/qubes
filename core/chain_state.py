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
            "avatar_description_generated_at": None
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

    def _save(self) -> None:
        """Save state to disk with file locking to prevent concurrent write conflicts"""
        lock = FileLock(self.lock_file, timeout=5.0)

        try:
            with lock:
                # Update last_updated timestamp
                self.state["last_updated"] = int(datetime.now(timezone.utc).timestamp())

                # Ensure parent directory exists
                self.state_file.parent.mkdir(parents=True, exist_ok=True)

                # Write atomically (write to temp, then rename)
                temp_file = self.state_file.with_suffix('.json.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.state, f, indent=2)

                temp_file.replace(self.state_file)

                logger.debug("chain_state_saved", qube_id=self.qube_id)

        except Exception as e:
            logger.error("chain_state_save_failed", error=str(e), exc_info=True)

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
