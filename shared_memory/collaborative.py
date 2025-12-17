"""
Collaborative Memory System

Multi-signature collaborative memory blocks for shared experiences.
From docs/07_Shared_Memory_Architecture.md Section 4.2
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from enum import Enum

from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class CollaborativeStatus(Enum):
    """Status of collaborative memory"""
    DRAFT = "draft"                    # Initial draft, collecting signatures
    PARTIALLY_SIGNED = "partially_signed"  # Some but not all signatures
    COMPLETE = "complete"              # All signatures collected
    REJECTED = "rejected"              # One or more participants rejected


class CollaborativeMemoryBlock:
    """Multi-signature collaborative memory block"""

    def __init__(
        self,
        participants: List[str],
        content: Dict[str, Any],
        initiator: str,
        block_id: Optional[str] = None
    ):
        """
        Initialize collaborative memory block

        Args:
            participants: List of Qube IDs participating
            content: Memory content (shared experience data)
            initiator: Qube ID who initiated the collaborative memory
            block_id: Optional block ID (generated if not provided)
        """
        self.block_id = block_id or str(uuid.uuid4())
        self.block_type = "COLLABORATIVE_MEMORY"
        self.participants = list(set(participants))  # Remove duplicates
        self.content = content
        self.initiator = initiator
        self.signatures: Dict[str, str] = {}  # qube_id → signature
        self.rejections: List[str] = []  # List of Qube IDs who rejected
        self.threshold = len(self.participants)  # All must sign
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.status = CollaborativeStatus.DRAFT

        logger.info(
            "collaborative_memory_created",
            block_id=self.block_id,
            participants=len(self.participants),
            initiator=initiator
        )

    def add_signature(self, qube_id: str, signature: str) -> bool:
        """
        Add signature from participant

        Args:
            qube_id: Qube ID signing
            signature: Cryptographic signature

        Returns:
            True if signature was added, False if qube_id not a participant
        """
        if qube_id not in self.participants:
            logger.warning(
                "signature_rejected_not_participant",
                block_id=self.block_id,
                qube_id=qube_id
            )
            return False

        self.signatures[qube_id] = signature
        self._update_status()

        logger.info(
            "signature_added",
            block_id=self.block_id,
            qube_id=qube_id,
            signatures_count=len(self.signatures),
            threshold=self.threshold
        )

        return True

    def reject(self, qube_id: str, reason: Optional[str] = None):
        """
        Reject participation in collaborative memory

        Args:
            qube_id: Qube ID rejecting
            reason: Optional rejection reason
        """
        if qube_id not in self.participants:
            logger.warning(
                "rejection_ignored_not_participant",
                block_id=self.block_id,
                qube_id=qube_id
            )
            return

        self.rejections.append(qube_id)
        self.status = CollaborativeStatus.REJECTED

        logger.info(
            "collaborative_memory_rejected",
            block_id=self.block_id,
            qube_id=qube_id,
            reason=reason
        )

    def _update_status(self):
        """Update status based on signatures"""
        signatures_count = len(self.signatures)

        if signatures_count == 0:
            self.status = CollaborativeStatus.DRAFT
        elif signatures_count < self.threshold:
            self.status = CollaborativeStatus.PARTIALLY_SIGNED
        elif signatures_count == self.threshold:
            self.status = CollaborativeStatus.COMPLETE
            self.completed_at = datetime.now()

    def is_valid(self) -> bool:
        """
        Check if all participants have signed

        Returns:
            True if all signatures collected, False otherwise
        """
        return len(self.signatures) == self.threshold

    def is_complete(self) -> bool:
        """Check if collaborative memory is complete"""
        return self.status == CollaborativeStatus.COMPLETE

    def get_missing_signatures(self) -> List[str]:
        """
        Get list of participants who haven't signed yet

        Returns:
            List of Qube IDs
        """
        return [
            qube_id for qube_id in self.participants
            if qube_id not in self.signatures
        ]

    def verify_signature(self, qube_id: str, public_key: bytes) -> bool:
        """
        Verify a participant's signature

        Args:
            qube_id: Qube ID to verify
            public_key: Public key of the Qube

        Returns:
            True if signature is valid, False otherwise
        """
        from crypto.signing import verify_signature

        if qube_id not in self.signatures:
            return False

        # Create canonical data representation
        data_to_sign = self._get_canonical_data()
        signature = self.signatures[qube_id]

        is_valid = verify_signature(data_to_sign.encode(), signature, public_key)

        logger.debug(
            "signature_verified",
            block_id=self.block_id,
            qube_id=qube_id,
            is_valid=is_valid
        )

        return is_valid

    def _get_canonical_data(self) -> str:
        """Get canonical data representation for signing"""
        data = {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "participants": sorted(self.participants),  # Sorted for consistency
            "content": self.content,
            "initiator": self.initiator,
            "created_at": self.created_at.isoformat()
        }
        return json.dumps(data, sort_keys=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "participants": self.participants,
            "content": self.content,
            "initiator": self.initiator,
            "signatures": self.signatures,
            "rejections": self.rejections,
            "threshold": self.threshold,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborativeMemoryBlock":
        """Deserialize from dictionary"""
        block = cls(
            participants=data["participants"],
            content=data["content"],
            initiator=data["initiator"],
            block_id=data["block_id"]
        )

        block.signatures = data["signatures"]
        block.rejections = data["rejections"]
        block.threshold = data["threshold"]
        block.status = CollaborativeStatus(data["status"])
        block.created_at = datetime.fromisoformat(data["created_at"])

        if data.get("completed_at"):
            block.completed_at = datetime.fromisoformat(data["completed_at"])

        return block


class CollaborativeSession:
    """Manages collaborative memory creation workflow"""

    def __init__(self, session_dir: Path):
        """
        Initialize collaborative session manager

        Args:
            session_dir: Directory to store collaborative sessions
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.active_sessions: Dict[str, CollaborativeMemoryBlock] = {}
        self.load_sessions()

        logger.info(
            "collaborative_session_initialized",
            session_dir=str(session_dir),
            active_sessions=len(self.active_sessions)
        )

    def create_session(
        self,
        participants: List[str],
        content: Dict[str, Any],
        initiator: str
    ) -> CollaborativeMemoryBlock:
        """
        Create new collaborative memory session

        Args:
            participants: List of participating Qube IDs
            content: Memory content
            initiator: Qube ID initiating

        Returns:
            CollaborativeMemoryBlock
        """
        block = CollaborativeMemoryBlock(
            participants=participants,
            content=content,
            initiator=initiator
        )

        self.active_sessions[block.block_id] = block
        self.save_session(block)

        logger.info(
            "collaborative_session_created",
            block_id=block.block_id,
            participants=len(participants)
        )

        return block

    def get_session(self, block_id: str) -> Optional[CollaborativeMemoryBlock]:
        """Get collaborative session by ID"""
        return self.active_sessions.get(block_id)

    def add_signature(
        self,
        block_id: str,
        qube_id: str,
        signature: str
    ) -> bool:
        """
        Add signature to collaborative memory

        Args:
            block_id: Collaborative block ID
            qube_id: Qube ID signing
            signature: Cryptographic signature

        Returns:
            True if signature added successfully
        """
        block = self.active_sessions.get(block_id)
        if not block:
            logger.warning("collaborative_block_not_found", block_id=block_id)
            return False

        success = block.add_signature(qube_id, signature)

        if success:
            self.save_session(block)

            # If complete, move to completed
            if block.is_complete():
                self._complete_session(block)

        return success

    def reject_session(
        self,
        block_id: str,
        qube_id: str,
        reason: Optional[str] = None
    ):
        """
        Reject collaborative memory session

        Args:
            block_id: Collaborative block ID
            qube_id: Qube ID rejecting
            reason: Optional rejection reason
        """
        block = self.active_sessions.get(block_id)
        if not block:
            logger.warning("collaborative_block_not_found", block_id=block_id)
            return

        block.reject(qube_id, reason)
        self.save_session(block)

    def _complete_session(self, block: CollaborativeMemoryBlock):
        """Mark session as complete"""
        logger.info(
            "collaborative_session_completed",
            block_id=block.block_id,
            participants=len(block.participants)
        )

        # Session remains in active_sessions for retrieval
        # Qubes can query and add to their chains

    def get_pending_sessions_for_qube(self, qube_id: str) -> List[CollaborativeMemoryBlock]:
        """
        Get collaborative sessions pending signature from a Qube

        Args:
            qube_id: Qube ID

        Returns:
            List of CollaborativeMemoryBlock objects
        """
        pending = []

        for block in self.active_sessions.values():
            if (qube_id in block.participants and
                qube_id not in block.signatures and
                block.status not in [CollaborativeStatus.COMPLETE, CollaborativeStatus.REJECTED]):
                pending.append(block)

        return pending

    def get_completed_sessions_for_qube(self, qube_id: str) -> List[CollaborativeMemoryBlock]:
        """
        Get completed collaborative sessions for a Qube

        Args:
            qube_id: Qube ID

        Returns:
            List of completed CollaborativeMemoryBlock objects
        """
        completed = []

        for block in self.active_sessions.values():
            if (qube_id in block.participants and
                block.status == CollaborativeStatus.COMPLETE):
                completed.append(block)

        return completed

    def save_session(self, block: CollaborativeMemoryBlock):
        """Save collaborative session to disk"""
        try:
            session_file = self.session_dir / f"{block.block_id}.json"

            with open(session_file, "w") as f:
                json.dump(block.to_dict(), f, indent=2)

            logger.debug(
                "collaborative_session_saved",
                block_id=block.block_id,
                file=str(session_file)
            )

        except Exception as e:
            logger.error(
                "collaborative_session_save_failed",
                block_id=block.block_id,
                error=str(e),
                exc_info=True
            )
            raise QubesError(f"Failed to save collaborative session: {e}", cause=e)

    def load_sessions(self):
        """Load all collaborative sessions from disk"""
        try:
            for session_file in self.session_dir.glob("*.json"):
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)

                    block = CollaborativeMemoryBlock.from_dict(data)
                    self.active_sessions[block.block_id] = block

                except Exception as e:
                    logger.error(
                        "collaborative_session_load_failed",
                        file=str(session_file),
                        error=str(e)
                    )

            logger.info(
                "collaborative_sessions_loaded",
                count=len(self.active_sessions)
            )

        except Exception as e:
            logger.error("collaborative_sessions_load_failed", error=str(e), exc_info=True)
            self.active_sessions = {}

    def cleanup_old_sessions(self, days: int = 30):
        """
        Remove old rejected or stale draft sessions

        Args:
            days: Remove sessions older than this many days
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        removed = 0

        to_remove = []
        for block_id, block in self.active_sessions.items():
            if block.created_at < cutoff_date:
                if block.status in [CollaborativeStatus.REJECTED, CollaborativeStatus.DRAFT]:
                    to_remove.append(block_id)
                    removed += 1

        for block_id in to_remove:
            del self.active_sessions[block_id]
            session_file = self.session_dir / f"{block_id}.json"
            if session_file.exists():
                session_file.unlink()

        if removed > 0:
            logger.info("old_sessions_cleaned", removed=removed)

    def get_stats(self) -> Dict[str, Any]:
        """Get collaborative session statistics"""
        total = len(self.active_sessions)
        by_status = {
            status.value: len([
                b for b in self.active_sessions.values()
                if b.status == status
            ])
            for status in CollaborativeStatus
        }

        return {
            "total_sessions": total,
            "by_status": by_status,
            "avg_participants": sum(len(b.participants) for b in self.active_sessions.values()) / total if total > 0 else 0
        }


from datetime import timedelta  # Add this import at the top
