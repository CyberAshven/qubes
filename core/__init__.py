"""
Core Qube system components

Exports:
    - Block, BlockType, create_* functions
    - MemoryChain
    - Session
    - Custom exceptions

Note: Qube is not exported from __init__ to avoid circular imports with shared_memory.
Import Qube directly: from core.qube import Qube
"""

from core.block import (
    Block,
    BlockType,
    create_genesis_block,
    create_thought_block,
    create_action_block,
    # create_observation_block,  # Deprecated - results now included in ACTION blocks
    create_message_block,
    create_decision_block,
    create_memory_anchor_block,
    create_collaborative_memory_block,
    create_summary_block
)
from core.memory_chain import MemoryChain
from core.session import Session
# from core.qube import Qube  # Commented out to avoid circular import
from core.exceptions import (
    QubesError,
    CryptoError,
    StorageError,
    InvalidBlockError,
    ChainIntegrityError,
    BlockNotFoundError
)

__all__ = [
    "Block",
    "BlockType",
    "create_genesis_block",
    "create_thought_block",
    "create_action_block",
    # "create_observation_block",  # Deprecated - results now included in ACTION blocks
    "create_message_block",
    "create_decision_block",
    "create_memory_anchor_block",
    "create_collaborative_memory_block",
    "create_summary_block",
    "MemoryChain",
    "Session",
    # "Qube",  # Commented out - import directly from core.qube
    "QubesError",
    "CryptoError",
    "StorageError",
    "InvalidBlockError",
    "ChainIntegrityError",
    "BlockNotFoundError",
]
