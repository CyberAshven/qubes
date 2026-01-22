"""
Memory Chain - Blockchain-like structure for Qube memories

Updated to match documentation exactly
Loads blocks from individual JSON files on demand
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from core.block import Block, BlockType, create_memory_anchor_block
from core.exceptions import (
    InvalidBlockError,
    ChainIntegrityError,
    BlockNotFoundError
)
from crypto.merkle import compute_merkle_root
# Import signing functions in methods to avoid circular import
from cryptography.hazmat.primitives.asymmetric import ec
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class MemoryChain:
    """
    Qube memory chain with cryptographic integrity

    Handles permanent blocks only (temporary=False)
    Session blocks managed by Session class
    """

    def __init__(
        self,
        qube_id: str,
        private_key: ec.EllipticCurvePrivateKey,
        public_key: ec.EllipticCurvePublicKey,
        data_dir: Path,
        anchor_interval: int = 100
    ):
        """
        Initialize memory chain

        Args:
            qube_id: 8-character Qube ID
            private_key: ECDSA private key for signing
            public_key: ECDSA public key for verification
            data_dir: Path to qube data directory
            anchor_interval: Create anchor block every N blocks
        """
        self.qube_id = qube_id
        self.private_key = private_key
        self.public_key = public_key
        self.data_dir = data_dir
        self.anchor_interval = anchor_interval

        # Directory for permanent blocks
        self.permanent_dir = Path(data_dir) / "blocks" / "permanent"
        self.permanent_dir.mkdir(parents=True, exist_ok=True)

        # Directory for relationship snapshots (new unified structure)
        self.snapshots_dir = Path(data_dir) / "snapshots" / "relationships"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # In-memory index: block_number -> filename
        self.block_index: Dict[int, str] = {}

        # Snapshot index: block_number -> has_snapshot
        self.snapshot_index: Dict[int, bool] = {}

        # Load block index from directory
        self._load_block_index()
        self._load_snapshot_index()

        logger.info("memory_chain_initialized", qube_id=qube_id, blocks=len(self.block_index), snapshots=len(self.snapshot_index))

    def reload(self) -> None:
        """
        Reload block index from disk.

        Call this when the memory chain may have been modified externally
        (e.g., after anchoring session blocks) to refresh the in-memory index.
        """
        self.block_index.clear()
        self.snapshot_index.clear()
        self._load_block_index()
        self._load_snapshot_index()
        logger.debug("memory_chain_reloaded", blocks=len(self.block_index), snapshots=len(self.snapshot_index))

    def add_block(self, block: Block, skip_signature: bool = False) -> None:
        """
        Add permanent block to chain with validation
        Block is NOT saved here - caller is responsible for saving

        Args:
            block: Block to add (must have temporary=False)
            skip_signature: Skip signature for genesis block

        Raises:
            InvalidBlockError: If block validation fails
            ChainIntegrityError: If chain integrity compromised
        """
        from crypto.signing import sign_block

        # Only accept permanent blocks
        # Support both dict and object blocks
        is_temporary = block.get("temporary", False) if isinstance(block, dict) else block.temporary
        if is_temporary:
            block_num = block.get("block_number") if isinstance(block, dict) else block.block_number
            raise InvalidBlockError(
                "Cannot add temporary block to memory chain",
                context={"block_number": block_num}
            )

        # Validate block
        self._validate_block(block, skip_signature)

        # Sign block if not already signed
        if not block.signature and not skip_signature:
            block.signature = sign_block(block.to_dict(), self.private_key)

        # Create filename for this block
        block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
        filename = f"{block.block_number}_{block_type_str}_{block.timestamp}.json"

        # Add to index (block will be saved by caller)
        self.block_index[block.block_number] = filename

        # Record metrics
        MetricsRecorder.record_memory_block_created(self.qube_id, block_type_str)

        # Check if anchor needed (skip for genesis block and until we have at least 2 blocks)
        if block.block_number > 0 and len(self.block_index) >= 2 and self._should_create_anchor():
            self._create_anchor()

        logger.debug(
            "block_added",
            qube_id=self.qube_id,
            block_number=block.block_number,
            block_type=block.block_type,
            block_hash=block.block_hash[:16] if block.block_hash else None
        )

    def get_block(self, block_number: int) -> Block:
        """
        Get block by number (loads from file)

        Args:
            block_number: Block number (must be >= 0 for permanent blocks)

        Returns:
            Block

        Raises:
            BlockNotFoundError: If block not found
        """
        if block_number not in self.block_index:
            raise BlockNotFoundError(
                f"Block {block_number} not found",
                context={"block_number": block_number}
            )

        filename = self.block_index[block_number]
        block_file = self.permanent_dir / filename

        # Check if file exists - if not, clean up orphaned index entry
        if not block_file.exists():
            logger.warning(
                "orphaned_block_index_entry",
                block_number=block_number,
                filename=filename,
                action="removing from index"
            )
            del self.block_index[block_number]
            raise BlockNotFoundError(
                f"Block {block_number} file missing (orphaned index entry cleaned)",
                context={"block_number": block_number, "filename": filename}
            )

        try:
            with open(block_file, 'r') as f:
                block_data = json.load(f)
            return Block.from_dict(block_data)
        except Exception as e:
            raise BlockNotFoundError(
                f"Failed to load block {block_number}",
                context={"block_number": block_number, "filename": filename},
                cause=e
            )

    def get_latest_block(self) -> Optional[Block]:
        """Get most recent block"""
        if not self.block_index:
            return None

        latest_block_num = max(self.block_index.keys())
        return self.get_block(latest_block_num)

    def get_chain_length(self) -> int:
        """Get number of blocks in chain"""
        return len(self.block_index)

    def verify_chain_integrity(self) -> bool:
        """
        Verify entire chain integrity (loads all blocks from disk)

        Returns:
            True if all blocks valid

        Raises:
            ChainIntegrityError: If integrity compromised
        """
        from crypto.signing import verify_block_signature

        # Get all block numbers in order
        block_numbers = sorted(self.block_index.keys())

        prev_block = None
        for block_num in block_numbers:
            block = self.get_block(block_num)

            # Verify hash
            computed_hash = block.compute_hash()
            if block.block_hash != computed_hash:
                raise ChainIntegrityError(
                    f"Block {block.block_number} hash mismatch",
                    context={
                        "block_number": block.block_number,
                        "stored_hash": block.block_hash[:16] if block.block_hash else None,
                        "computed_hash": computed_hash[:16]
                    }
                )

            # Verify signature
            if block.signature:
                try:
                    verify_block_signature(
                        block.to_dict(),
                        block.signature,
                        self.public_key
                    )
                except Exception as e:
                    raise ChainIntegrityError(
                        f"Block {block.block_number} signature invalid",
                        context={"block_number": block.block_number},
                        cause=e
                    )

            # Verify chain linkage
            if prev_block:
                if block.previous_hash != prev_block.block_hash:
                    raise ChainIntegrityError(
                        f"Block {block.block_number} chain link broken",
                        context={
                            "block_number": block.block_number,
                            "expected_prev": prev_block.block_hash[:16] if prev_block.block_hash else None,
                            "actual_prev": block.previous_hash[:16]
                        }
                    )

            prev_block = block

        logger.info("chain_integrity_verified", qube_id=self.qube_id, blocks=len(self.block_index))
        return True

    def _validate_block(self, block: Block, skip_signature: bool = False) -> None:
        """Validate block before adding"""
        # Validate block number sequence
        expected_number = len(self.block_index)
        if block.block_number != expected_number:
            raise InvalidBlockError(
                "Block number sequence error",
                context={"expected": expected_number, "actual": block.block_number}
            )

        # Validate previous hash linkage
        if len(self.block_index) > 0:
            latest = self.get_latest_block()
            if block.previous_hash != latest.block_hash:
                raise InvalidBlockError(
                    "Previous hash mismatch",
                    context={
                        "expected": latest.block_hash[:16] if latest.block_hash else None,
                        "actual": block.previous_hash[:16]
                    }
                )

    def _should_create_anchor(self) -> bool:
        """Check if anchor block should be created"""
        if not self.block_index:
            return False

        latest = self.get_latest_block()
        return (
            latest.block_type != BlockType.MEMORY_ANCHOR and
            len(self.block_index) % self.anchor_interval == 0
        )

    def _create_anchor(self) -> None:
        """Create memory anchor block with Merkle root"""
        from crypto.signing import sign_block

        # Load all blocks to get hashes
        block_numbers = sorted(self.block_index.keys())
        block_hashes = []
        for block_num in block_numbers:
            block = self.get_block(block_num)
            if block.block_hash:
                block_hashes.append(block.block_hash)

        merkle_root = compute_merkle_root(block_hashes)

        # SAFEGUARD: Determine next available block number
        next_block_number = len(self.block_index)

        # Check if this block number already exists (collision prevention)
        existing_files = list(self.permanent_dir.glob(f"{next_block_number}_*.json"))
        if existing_files:
            logger.warning(
                "memory_anchor_collision_avoided",
                intended_block_number=next_block_number,
                existing_files=[f.name for f in existing_files],
                qube_id=self.qube_id
            )
            # Skip anchor creation - block number already in use
            return

        latest = self.get_latest_block()
        anchor_block = create_memory_anchor_block(
            qube_id=self.qube_id,
            block_number=next_block_number,
            previous_hash=latest.block_hash,
            merkle_root=merkle_root,
            block_range=[0, next_block_number - 1],
            total_blocks=next_block_number,
            anchor_type="periodic"
        )

        anchor_block.signature = sign_block(anchor_block.to_dict(), self.private_key)

        # Save anchor block to file
        block_type_str = anchor_block.block_type if isinstance(anchor_block.block_type, str) else anchor_block.block_type.value
        filename = f"{anchor_block.block_number}_{block_type_str}_{anchor_block.timestamp}.json"
        block_file = self.permanent_dir / filename

        with open(block_file, 'w') as f:
            json.dump(anchor_block.to_dict(), f, indent=2)

        # Add to index
        self.block_index[anchor_block.block_number] = filename

    def _load_block_index(self) -> None:
        """Load block index from permanent directory"""
        if not self.permanent_dir.exists():
            return

        for block_file in self.permanent_dir.glob("*.json"):
            try:
                # Parse filename: {block_number}_{type}_{timestamp}.json
                filename = block_file.name
                parts = filename.replace(".json", "").split("_")
                if len(parts) >= 3:
                    block_number = int(parts[0])
                    self.block_index[block_number] = filename
            except Exception as e:
                logger.warning("failed_to_parse_block_filename", filename=block_file.name, error=str(e))

        logger.debug("block_index_loaded", blocks=len(self.block_index))

    def filter_blocks(
        self,
        block_types: Optional[List[str]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        participants: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter blocks by metadata (for memory search)

        Loads blocks from JSON files and filters based on criteria.

        Args:
            block_types: Filter by block types (None = all)
            start_time: Start timestamp (None = no lower bound)
            end_time: End timestamp (None = no upper bound)
            participants: Filter by participants (None = all)

        Returns:
            List of matching block dicts
        """
        matching_blocks = []

        # Iterate through all blocks in index
        for block_number in sorted(self.block_index.keys()):
            try:
                block = self.get_block(block_number)
                block_dict = block.to_dict()

                # Filter by block type
                block_type = block_dict.get("block_type")
                if block_types and block_type not in block_types:
                    continue

                # Filter by timestamp
                block_time = block_dict.get("timestamp", 0)
                if start_time and block_time < start_time:
                    continue
                if end_time and block_time > end_time:
                    continue

                # Filter by participants (check content for participant IDs)
                if participants:
                    content = block_dict.get("content", {})
                    # Check if this is a MESSAGE block with participant info
                    if block_type == "MESSAGE":
                        recipient = content.get("recipient_id", "")
                        if not any(p in recipient for p in participants):
                            continue
                    # For other block types, skip if participants filter specified
                    else:
                        continue

                matching_blocks.append(block_dict)

            except Exception as e:
                logger.warning("block_filter_error", block_number=block_number, error=str(e))
                continue

        logger.debug("blocks_filtered", total=len(self.block_index), matched=len(matching_blocks))
        return matching_blocks

    def _load_snapshot_index(self) -> None:
        """Load relationship snapshot index from snapshots directory"""
        if not self.snapshots_dir.exists():
            return

        for snapshot_file in self.snapshots_dir.glob("snapshot_*.json"):
            try:
                # Parse filename: snapshot_{block_number}.json
                filename = snapshot_file.name
                block_number_str = filename.replace("snapshot_", "").replace(".json", "")
                block_number = int(block_number_str)
                self.snapshot_index[block_number] = True
            except Exception as e:
                logger.warning("failed_to_parse_snapshot_filename", filename=snapshot_file.name, error=str(e))

        logger.debug("snapshot_index_loaded", snapshots=len(self.snapshot_index))

    def save_relationship_snapshot(
        self,
        block_number: int,
        relationships: Dict[str, Any]
    ) -> None:
        """
        Save relationship snapshot at specific block number

        Args:
            block_number: Block number where snapshot is taken
            relationships: Dictionary of entity_id -> relationship state
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())
        snapshot_file = self.snapshots_dir / f"relationship_snapshot_{block_number}_{timestamp}.json"

        try:
            with open(snapshot_file, 'w') as f:
                json.dump({
                    "block_number": block_number,
                    "timestamp": timestamp,
                    "relationships": relationships
                }, f, indent=2)

            self.snapshot_index[block_number] = True

            logger.info(
                "relationship_snapshot_saved",
                qube_id=self.qube_id,
                block_number=block_number,
                relationship_count=len(relationships)
            )
        except Exception as e:
            logger.error(
                "relationship_snapshot_save_failed",
                block_number=block_number,
                error=str(e),
                exc_info=True
            )
            raise

    def load_relationship_snapshot(self, block_number: int) -> Optional[Dict[str, Any]]:
        """
        Load relationship snapshot from specific block number

        Args:
            block_number: Block number to load snapshot from

        Returns:
            Dictionary with snapshot data or None if not found
        """
        if block_number not in self.snapshot_index:
            return None

        snapshot_file = self.snapshots_dir / f"snapshot_{block_number}.json"

        try:
            with open(snapshot_file, 'r') as f:
                snapshot_data = json.load(f)

            logger.debug(
                "relationship_snapshot_loaded",
                block_number=block_number,
                relationship_count=len(snapshot_data.get("relationships", {}))
            )

            return snapshot_data
        except Exception as e:
            logger.error(
                "relationship_snapshot_load_failed",
                block_number=block_number,
                error=str(e),
                exc_info=True
            )
            return None

    def get_nearest_snapshot(self, target_block_number: int) -> Optional[int]:
        """
        Find nearest snapshot at or before target block number

        Args:
            target_block_number: Target block number

        Returns:
            Block number of nearest snapshot, or None if no snapshots exist
        """
        if not self.snapshot_index:
            return None

        # Get all snapshot block numbers at or before target
        candidates = [
            block_num for block_num in self.snapshot_index.keys()
            if block_num <= target_block_number
        ]

        if not candidates:
            return None

        return max(candidates)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize chain metadata to dictionary"""
        return {
            "qube_id": self.qube_id,
            "chain_length": len(self.block_index),
            "anchor_interval": self.anchor_interval,
            "snapshot_count": len(self.snapshot_index)
        }
