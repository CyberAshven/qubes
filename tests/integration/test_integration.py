"""
Integration Test for Core Qube System - Updated for Documentation Compliance

Tests match documentation structure exactly
"""

import asyncio
import json
import pytest
from pathlib import Path
import shutil

from core.qube import Qube
from core.block import BlockType
from core.exceptions import ChainIntegrityError
from utils.logging import configure_logging


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary data directory"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    yield data_dir
    if data_dir.exists():
        shutil.rmtree(data_dir)


@pytest.fixture
def qube(test_data_dir):
    """Create test Qube"""
    configure_logging(log_level="INFO", console_output=False)

    qube = Qube.create_new(
        qube_name="TestQube",
        creator="alice",
        genesis_prompt="A test AI agent for integration testing",
        ai_model="gpt-4",
        voice_model="elevenlabs-test",
        data_dir=test_data_dir,
        favorite_color="#FF0000"
    )

    yield qube
    qube.close()


def test_qube_creation(qube):
    """Test Qube creation matches documentation"""
    assert qube.qube_id is not None
    assert len(qube.qube_id) == 8
    assert qube.genesis_block.block_number == 0
    assert qube.genesis_block.block_type == BlockType.GENESIS
    assert qube.genesis_block.qube_name == "TestQube"
    assert qube.genesis_block.creator == "alice"
    assert qube.genesis_block.ai_model == "gpt-4"
    assert qube.genesis_block.voice_model == "elevenlabs-test"
    assert qube.genesis_block.favorite_color == "#FF0000"
    assert qube.genesis_block.home_blockchain == "bitcoin_cash"
    assert qube.genesis_block.temporary == False
    assert qube.genesis_block.encrypted == False  # Genesis not encrypted


def test_session_blocks(qube):
    """Test session blocks with negative indexing"""
    # Start session
    session = qube.start_session()
    assert session.session_id is not None

    # Add messages to session (temporary blocks)
    msg1 = qube.add_message(
        message_type="qube_to_human",
        recipient_id="alice",
        message_body="Hello!",
        conversation_id="conv-123",
        temporary=True
    )

    assert msg1.block_number == -1
    assert msg1.temporary == True
    assert msg1.session_id == session.session_id
    assert msg1.block_type == BlockType.MESSAGE

    msg2 = qube.add_message(
        message_type="qube_to_human",
        recipient_id="alice",
        message_body="How are you?",
        conversation_id="conv-123",
        temporary=True
    )

    assert msg2.block_number == -2
    assert msg2.temporary == True

    # Verify session has 2 blocks
    assert len(session.session_blocks) == 2

    # Anchor session
    count = qube.anchor_session(create_summary=False)
    assert count == 2

    # Verify blocks are now permanent
    block1 = qube.memory_chain.get_block(1)  # Genesis is 0
    assert block1.block_number == 1
    assert block1.temporary == False
    assert block1.original_session_index == -1

    block2 = qube.memory_chain.get_block(2)
    assert block2.block_number == 2
    assert block2.temporary == False
    assert block2.original_session_index == -2


def test_permanent_message_block(qube):
    """Test adding message directly to chain"""
    msg = qube.add_message(
        message_type="qube_to_human",
        recipient_id="alice",
        message_body="Permanent message",
        conversation_id="conv-456",
        temporary=False
    )

    assert msg.block_number == 1  # After genesis
    assert msg.temporary == False
    assert msg.block_type == BlockType.MESSAGE
    assert msg.content["message_body"] == "Permanent message"


def test_memory_chain_integrity(qube):
    """Test memory chain integrity verification"""
    # Add blocks
    for i in range(10):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Message {i}",
            conversation_id="conv-789",
            temporary=False
        )

    # Verify integrity
    assert qube.verify_integrity() == True


def test_storage_persistence(test_data_dir):
    """Test that blocks persist to JSON storage"""
    # Create Qube and add blocks
    qube1 = Qube.create_new(
        qube_name="PersistTest",
        creator="bob",
        genesis_prompt="Test persistence",
        ai_model="gpt-4",
        voice_model="elevenlabs-test",
        data_dir=test_data_dir
    )

    qube1.start_session()
    qube1.add_message(
        message_type="qube_to_human",
        recipient_id="bob",
        message_body="Test message",
        conversation_id="conv-persist",
        temporary=True
    )
    asyncio.run(qube1.anchor_session(create_summary=False))

    qube_id = qube1.qube_id
    qube1.close()

    qube_dir = test_data_dir / f"PersistTest_{qube_id}"
    blocks_dir = qube_dir / "blocks" / "permanent"
    assert blocks_dir.exists()

    def load_block(block_number: int) -> dict:
        matches = list(blocks_dir.glob(f"{block_number}_*.json"))
        assert matches, f"Block {block_number} not found"
        with open(matches[0], "r") as f:
            return json.load(f)

    genesis = load_block(0)
    assert genesis["block_number"] == 0
    assert genesis["qube_name"] == "PersistTest"
    assert genesis["creator"] == "bob"

    message = load_block(1)
    assert message["block_number"] == 1
    assert message["block_type"] == BlockType.MESSAGE.value


def test_memory_stats(qube):
    """Test memory statistics"""
    # Add some permanent blocks
    for i in range(5):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Permanent {i}",
            conversation_id="conv-stats",
            temporary=False
        )

    # Add some session blocks
    qube.start_session()
    for i in range(3):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Session {i}",
            conversation_id="conv-stats",
            temporary=True
        )

    stats = qube.get_memory_stats()
    assert stats["qube_id"] == qube.qube_id
    assert stats["qube_name"] == "TestQube"
    assert stats["ai_model"] == "gpt-4"
    assert stats["permanent_blocks"] == 6  # Genesis + 5 messages
    assert stats["session_blocks"] == 3
    assert stats["total_blocks"] == 9


def test_block_signatures(qube):
    """Test that all blocks are properly signed"""
    # Add blocks
    for i in range(5):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Test {i}",
            conversation_id="conv-sig",
            temporary=False
        )

    # Check all blocks have signatures
    for i in range(qube.memory_chain.get_chain_length()):
        block = qube.memory_chain.get_block(i)
        assert block.signature is not None
        assert len(block.signature) > 0


def test_merkle_root_anchors(qube):
    """Test that anchor blocks contain Merkle roots"""
    # Add enough blocks to trigger anchor (100 blocks)
    for i in range(100):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Test {i}",
            conversation_id="conv-anchor",
            temporary=False
        )

    # Find anchor block
    anchor_block = None
    for i in range(qube.memory_chain.get_chain_length()):
        block = qube.memory_chain.get_block(i)
        if block.block_type == BlockType.MEMORY_ANCHOR:
            anchor_block = block
            break

    assert anchor_block is not None
    assert anchor_block.merkle_root is not None
    assert len(anchor_block.merkle_root) == 64  # SHA-256 hex
    assert anchor_block.encrypted == False  # Anchors are public
    assert "merkle_root" in anchor_block.content
    assert "block_range" in anchor_block.content
    assert anchor_block.content["anchor_type"] == "periodic"


def test_session_discard(qube):
    """Test discarding session without anchoring"""
    # Start session and add blocks
    qube.start_session()
    for i in range(5):
        qube.add_message(
            message_type="qube_to_human",
            recipient_id="alice",
            message_body=f"Temp {i}",
            conversation_id="conv-discard",
            temporary=True
        )

    # Verify session has blocks
    assert len(qube.current_session.session_blocks) == 5

    # Discard session
    count = qube.discard_session()
    assert count == 5

    # Verify chain unchanged
    assert qube.memory_chain.get_chain_length() == 1  # Only genesis
    assert qube.current_session is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
