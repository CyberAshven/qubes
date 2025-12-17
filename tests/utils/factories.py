"""
Test data factories for creating test objects.

Provides reusable factory functions to create test Qubes, blocks,
relationships, and other domain objects with sensible defaults.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from core.qube import Qube
from core.block import (
    create_message_block,
    create_thought_block,
    create_decision_block,
    create_summary_block,
    Block
)


# =============================================================================
# QUBE FACTORIES
# =============================================================================

def create_test_qube(
    name: str = "TestQube",
    creator: str = "test_user",
    ai_model: str = "gpt-4o-mini",
    data_dir: Optional[Path] = None,
    **kwargs
) -> Qube:
    """
    Factory for creating test Qubes with sensible defaults.

    Args:
        name: Qube name
        creator: Creator name
        ai_model: AI model to use
        data_dir: Data directory (uses temp if not provided)
        **kwargs: Additional arguments passed to Qube.create_new()

    Returns:
        Qube instance ready for testing

    Example:
        qube = create_test_qube(name="Alice", favorite_color="#FF0000")
    """
    defaults = {
        "qube_name": name,
        "creator": creator,
        "genesis_prompt": f"Test AI agent named {name}",
        "ai_model": ai_model,
        "voice_model": "test",
        "favorite_color": "#4A90E2",
    }

    if data_dir:
        defaults["data_dir"] = data_dir

    defaults.update(kwargs)

    return Qube.create_new(**defaults)


def create_test_qube_with_blocks(
    num_blocks: int = 10,
    data_dir: Optional[Path] = None,
    **qube_kwargs
) -> Qube:
    """
    Create test Qube with specified number of message blocks.

    Args:
        num_blocks: Number of message blocks to create
        data_dir: Data directory
        **qube_kwargs: Arguments for Qube creation

    Returns:
        Qube with populated memory chain
    """
    qube = create_test_qube(data_dir=data_dir, **qube_kwargs)

    for i in range(num_blocks):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="test_user",
            message_body=f"Test message {i}",
            conversation_id="test_conv",
            temporary=False
        )

    return qube


# =============================================================================
# BLOCK FACTORIES
# =============================================================================

def create_test_message(
    qube_id: str = "TEST0001",
    message_body: str = "Test message",
    block_number: int = 1,
    **kwargs
) -> Block:
    """
    Factory for creating test message blocks.

    Args:
        qube_id: Qube ID
        message_body: Message content
        block_number: Block number
        **kwargs: Additional block properties

    Returns:
        Message block
    """
    defaults = {
        "qube_id": qube_id,
        "block_number": block_number,
        "previous_hash": "0" * 64,
        "message_type": "qube_to_human",
        "recipient_id": "test_user",
        "message_body": message_body,
        "conversation_id": "test_conv",
    }
    defaults.update(kwargs)

    return create_message_block(**defaults)


def create_test_thought(
    qube_id: str = "TEST0001",
    internal_monologue: str = "Test thought",
    block_number: int = 1,
    **kwargs
) -> Block:
    """Factory for creating test thought blocks."""
    defaults = {
        "qube_id": qube_id,
        "block_number": block_number,
        "previous_hash": "0" * 64,
        "internal_monologue": internal_monologue,
        "reasoning_chain": ["Step 1", "Step 2"],
        "confidence": 0.9,
    }
    defaults.update(kwargs)

    return create_thought_block(**defaults)


def create_test_decision(
    qube_id: str = "TEST0001",
    decision: str = "Test decision",
    block_number: int = 1,
    **kwargs
) -> Block:
    """Factory for creating test decision blocks."""
    defaults = {
        "qube_id": qube_id,
        "block_number": block_number,
        "previous_hash": "0" * 64,
        "decision": decision,
        "reasoning": "Test reasoning",
        "confidence": 0.85,
        "alternatives_considered": ["Alternative 1", "Alternative 2"],
    }
    defaults.update(kwargs)

    return create_decision_block(**defaults)


def create_test_summary(
    qube_id: str = "TEST0001",
    summary_text: str = "Test summary",
    block_number: int = 1,
    **kwargs
) -> Block:
    """Factory for creating test summary blocks."""
    defaults = {
        "qube_id": qube_id,
        "block_number": block_number,
        "previous_hash": "0" * 64,
        "summary_text": summary_text,
        "summarized_blocks": list(range(1, 10)),
        "key_points": ["Point 1", "Point 2"],
    }
    defaults.update(kwargs)

    return create_summary_block(**defaults)


# =============================================================================
# RELATIONSHIP FACTORIES
# =============================================================================

def create_test_relationship(
    entity_id: str = "OTHER001",
    trust_score: int = 50,
    status: str = "acquaintance",
    **kwargs
):
    """
    Factory for creating test relationships.

    Args:
        entity_id: Other entity's ID
        trust_score: Overall trust score (0-100)
        status: Relationship status
        **kwargs: Additional relationship properties

    Returns:
        Relationship instance
    """
    from relationships import Relationship

    rel = Relationship(entity_id=entity_id)
    rel.overall_trust_score = trust_score
    rel.relationship_status = status

    for key, value in kwargs.items():
        setattr(rel, key, value)

    return rel


# =============================================================================
# PERMISSION FACTORIES
# =============================================================================

def create_test_permission(
    granted_to: str = "QUBE0002",
    granted_by: str = "QUBE0001",
    block_numbers: Optional[List[int]] = None,
    **kwargs
):
    """Factory for creating test memory permissions."""
    from shared_memory import MemoryPermission, PermissionLevel

    permission = MemoryPermission(
        granted_by=granted_by,
        granted_to=granted_to
    )

    if block_numbers:
        permission.grant_access(
            block_numbers=block_numbers,
            permission_level=kwargs.get("permission_level", PermissionLevel.READ)
        )

    return permission
