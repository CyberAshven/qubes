"""
Tests for core Block data structure

Tests the fundamental memory block system that powers all Qube memories.
Covers 9 block types, cryptographic integrity, session management, and serialization.

Phase 2: Core System Tests
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from core.block import (
    Block,
    BlockType,
    create_genesis_block,
    create_thought_block,
    create_action_block,
    create_observation_block,
    create_message_block,
    create_decision_block,
    create_memory_anchor_block,
    create_collaborative_memory_block,
    create_summary_block,
    create_learning_block,
    VALID_LEARNING_TYPES,
)


# ==============================================================================
# BLOCK CLASS TESTS
# ==============================================================================

class TestBlockCreation:
    """Test basic Block creation and initialization"""

    @pytest.mark.unit
    def test_create_block_with_minimal_fields(self):
        """Should create block with only required fields"""
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="ABCD1234"
        )

        assert block.block_type == BlockType.THOUGHT
        assert block.block_number == 1
        assert block.qube_id == "ABCD1234"
        assert block.timestamp is not None  # Auto-set
        assert block.encrypted is True  # Default
        assert block.temporary is False  # Default

    @pytest.mark.unit
    def test_block_auto_sets_timestamp(self):
        """Should automatically set timestamp if not provided"""
        before = int(datetime.now(timezone.utc).timestamp())

        block = Block(
            block_type=BlockType.MESSAGE,
            block_number=5,
            qube_id="TEST1234"
        )

        after = int(datetime.now(timezone.utc).timestamp())

        assert before <= block.timestamp <= after

    @pytest.mark.unit
    def test_block_respects_provided_timestamp(self):
        """Should use provided timestamp if given"""
        custom_timestamp = 1609459200  # 2021-01-01

        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="TEST1234",
            timestamp=custom_timestamp
        )

        assert block.timestamp == custom_timestamp

    @pytest.mark.unit
    def test_block_with_all_fields(self):
        """Should create block with all optional fields populated"""
        block = Block(
            block_type=BlockType.ACTION,
            block_number=10,
            qube_id="FULL1234",
            timestamp=1234567890,
            content={"action": "test", "result": "success"},
            encrypted=False,
            temporary=True,
            session_id="session_abc",
            original_session_index=5,
            previous_block_number=9,
            previous_hash="abc123",
            block_hash="def456",
            signature="sig789",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model_used="gpt-4",
            estimated_cost_usd=0.01
        )

        assert block.qube_id == "FULL1234"
        assert block.content["action"] == "test"
        assert block.temporary is True
        assert block.session_id == "session_abc"
        assert block.total_tokens == 150


# ==============================================================================
# BLOCK HASH TESTS
# ==============================================================================

class TestBlockHashing:
    """Test block hash computation and integrity"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_compute_hash_returns_string(self):
        """compute_hash() should return a hex string"""
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="HASH1234"
        )

        hash_value = block.compute_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64

    @pytest.mark.unit
    @pytest.mark.security
    def test_compute_hash_deterministic(self):
        """Same block content should produce same hash"""
        block1 = Block(
            block_type=BlockType.MESSAGE,
            block_number=5,
            qube_id="DET12345",
            timestamp=1234567890,
            content={"text": "Hello"}
        )

        block2 = Block(
            block_type=BlockType.MESSAGE,
            block_number=5,
            qube_id="DET12345",
            timestamp=1234567890,
            content={"text": "Hello"}
        )

        assert block1.compute_hash() == block2.compute_hash()

    @pytest.mark.unit
    @pytest.mark.security
    def test_compute_hash_changes_with_content(self):
        """Different content should produce different hashes"""
        block1 = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="DIFF1234",
            content={"text": "Original"}
        )

        block2 = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="DIFF1234",
            content={"text": "Modified"}
        )

        assert block1.compute_hash() != block2.compute_hash()

    @pytest.mark.unit
    @pytest.mark.security
    def test_compute_hash_excludes_hash_and_signature(self):
        """Hash computation should exclude block_hash and signature fields"""
        block = Block(
            block_type=BlockType.ACTION,
            block_number=3,
            qube_id="EXCL1234",
            block_hash="old_hash",
            signature="old_sig"
        )

        # Changing block_hash/signature shouldn't change computed hash
        hash1 = block.compute_hash()

        block.block_hash = "new_hash"
        block.signature = "new_sig"

        hash2 = block.compute_hash()

        assert hash1 == hash2  # Hash unchanged


# ==============================================================================
# SERIALIZATION TESTS
# ==============================================================================

class TestBlockSerialization:
    """Test block serialization and deserialization"""

    @pytest.mark.unit
    def test_to_dict_returns_dictionary(self):
        """to_dict() should return a dictionary"""
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="DICT1234",
            content={"thought": "test"}
        )

        result = block.to_dict()

        assert isinstance(result, dict)
        assert result["block_type"] == "THOUGHT"
        assert result["qube_id"] == "DICT1234"
        assert result["content"]["thought"] == "test"

    @pytest.mark.unit
    def test_to_dict_excludes_none_values(self):
        """to_dict() should exclude None values"""
        block = Block(
            block_type=BlockType.MESSAGE,
            block_number=1,
            qube_id="NONE1234"
            # Many optional fields not set (will be None)
        )

        result = block.to_dict()

        # Should not include fields that are None
        assert "signature" not in result
        assert "previous_hash" not in result
        assert "session_id" not in result

    @pytest.mark.unit
    def test_from_dict_creates_block(self):
        """from_dict() should create Block from dictionary"""
        data = {
            "block_type": "OBSERVATION",
            "block_number": 7,
            "qube_id": "FROM1234",
            "content": {"observation": "test"},
            "timestamp": 1234567890
        }

        block = Block.from_dict(data)

        assert isinstance(block, Block)
        assert block.block_type == BlockType.OBSERVATION
        assert block.block_number == 7
        assert block.qube_id == "FROM1234"

    @pytest.mark.unit
    def test_round_trip_serialization(self):
        """Block should survive to_dict() -> from_dict() round trip"""
        original = Block(
            block_type=BlockType.DECISION,
            block_number=15,
            qube_id="ROUND123",
            content={"decision": "approve", "reasoning": "looks good"},
            temporary=True,
            session_id="session_xyz"
        )

        # Round trip
        dict_form = original.to_dict()
        restored = Block.from_dict(dict_form)

        assert restored.block_type == original.block_type
        assert restored.block_number == original.block_number
        assert restored.qube_id == original.qube_id
        assert restored.content == original.content
        assert restored.temporary == original.temporary
        assert restored.session_id == original.session_id


# ==============================================================================
# GENESIS BLOCK TESTS
# ==============================================================================

class TestGenesisBlock:
    """Test GENESIS block creation (block 0, Qube birth)"""

    @pytest.mark.unit
    def test_create_genesis_block(self):
        """Should create valid GENESIS block"""
        block = create_genesis_block(
            qube_id="GEN12345",
            qube_name="Alice",
            creator="user_bob",
            public_key="pubkey_abc123",
            genesis_prompt="You are Alice, a helpful AI assistant",
            ai_model="gpt-4o-mini",
            voice_model="alloy",
            avatar={"style": "abstract", "colors": ["blue", "purple"]},
            favorite_color="#4A90E2"
        )

        assert block.block_type == BlockType.GENESIS
        assert block.block_number == 0
        assert block.qube_id == "GEN12345"
        assert block.qube_name == "Alice"
        assert block.creator == "user_bob"
        assert block.genesis_prompt == "You are Alice, a helpful AI assistant"
        assert block.ai_model == "gpt-4o-mini"
        assert block.previous_hash == "0" * 64  # Genesis convention
        assert block.encrypted is False  # Genesis not encrypted
        assert block.temporary is False  # Genesis is permanent

    @pytest.mark.unit
    def test_genesis_block_has_hash(self):
        """GENESIS block should have hash computed"""
        block = create_genesis_block(
            qube_id="HASH_GEN",
            qube_name="Bob",
            creator="user_alice",
            public_key="pubkey_xyz",
            genesis_prompt="Test prompt",
            ai_model="gpt-4o-mini",
            voice_model="test",
            avatar={}
        )

        assert block.block_hash is not None
        assert len(block.block_hash) == 64

# ==============================================================================
# THOUGHT BLOCK TESTS
# ==============================================================================

class TestThoughtBlock:
    """Test THOUGHT block creation (internal reasoning)"""

    @pytest.mark.unit
    def test_create_thought_block(self):
        """Should create valid THOUGHT block"""
        block = create_thought_block(
            qube_id="THT12345",
            block_number=5,
            internal_monologue="I should analyze this data carefully",
            previous_hash="prev_hash_abc"
        )

        assert block.block_type == BlockType.THOUGHT
        assert block.block_number == 5
        assert block.content["internal_monologue"] == "I should analyze this data carefully"
        assert block.previous_hash == "prev_hash_abc"

    @pytest.mark.unit
    def test_thought_block_temporary(self):
        """THOUGHT blocks can be temporary (session)"""
        block = create_thought_block(
            qube_id="TEMP_THT",
            block_number=1,
            internal_monologue="Session thought",
            temporary=True,
            session_id="session_123"
        )

        assert block.temporary is True
        assert block.session_id == "session_123"


# ==============================================================================
# MESSAGE BLOCK TESTS
# ==============================================================================

class TestMessageBlock:
    """Test MESSAGE block creation (communication)"""

    @pytest.mark.unit
    def test_create_message_block(self):
        """Should create valid MESSAGE block"""
        block = create_message_block(
            qube_id="MSG12345",
            block_number=10,
            message_body="Hello, how are you?",
            sender_id="SENDER01",
            recipient_id="RECV0001",
            previous_hash="prev_msg_hash"
        )

        assert block.block_type == BlockType.MESSAGE
        assert block.content["message_body"] == "Hello, how are you?"
        assert block.content["sender_id"] == "SENDER01"
        assert block.content["recipient_id"] == "RECV0001"

    @pytest.mark.unit
    def test_message_block_multiple_participants(self):
        """MESSAGE can include multiple participants"""
        participants = ["QUBE_A", "QUBE_B", "QUBE_C"]

        block = create_message_block(
            qube_id="MSG_PART",
            block_number=1,
            message_body="Group conversation",
            participants=participants,
            conversation_id="conv_123"
        )

        assert block.content["participants"] == participants
        assert block.content["conversation_id"] == "conv_123"


# ==============================================================================
# ACTION & OBSERVATION TESTS
# ==============================================================================

class TestActionBlock:
    """Test ACTION block creation (external actions)"""

    @pytest.mark.unit
    def test_create_action_block(self):
        """Should create valid ACTION block"""
        block = create_action_block(
            qube_id="ACT12345",
            block_number=3,
            action_type="web_search",
            parameters={"query": "Python testing", "engine": "google"},
            previous_hash="prev_action_hash"
        )

        assert block.block_type == BlockType.ACTION
        assert block.content["action_type"] == "web_search"
        assert block.content["parameters"]["query"] == "Python testing"


class TestObservationBlock:
    """Test OBSERVATION block creation (perceived data)"""

    @pytest.mark.unit
    def test_create_observation_block(self):
        """Should create valid OBSERVATION block"""
        block = create_observation_block(
            qube_id="OBS12345",
            block_number=4,
            observation_source="user_feedback",
            observation_data="User seems satisfied",
            previous_hash="prev_obs_hash"
        )

        assert block.block_type == BlockType.OBSERVATION
        assert block.content["observation_data"] == "User seems satisfied"
        assert block.content["observation_source"] == "user_feedback"


# ==============================================================================
# DECISION BLOCK TESTS
# ==============================================================================

class TestDecisionBlock:
    """Test DECISION block creation (choices made)"""

    @pytest.mark.unit
    def test_create_decision_block(self):
        """Should create valid DECISION block"""
        block = create_decision_block(
            qube_id="DEC12345",
            block_number=8,
            decision="use_web_search",
            from_value="analysis",
            previous_hash="prev_dec_hash"
        )

        assert block.block_type == BlockType.DECISION
        assert block.content["decision"] == "use_web_search"
        assert block.content["from_value"] == "analysis"


# ==============================================================================
# MEMORY ANCHOR TESTS
# ==============================================================================

class TestMemoryAnchorBlock:
    """Test MEMORY_ANCHOR block (session to permanent conversion)"""

    @pytest.mark.unit
    def test_create_memory_anchor_block(self):
        """Should create valid MEMORY_ANCHOR block"""
        block = create_memory_anchor_block(
            qube_id="ANCHOR01",
            block_number=20,
            previous_hash="prev_anchor_hash",
            merkle_root="merkle_abc123",
            block_range=(5, 19),
            total_blocks=15
        )

        assert block.block_type == BlockType.MEMORY_ANCHOR
        assert block.content["merkle_root"] == "merkle_abc123"
        assert block.content["block_range"] == (5, 19)
        assert block.content["total_blocks"] == 15


# ==============================================================================
# COLLABORATIVE MEMORY TESTS
# ==============================================================================

class TestCollaborativeMemoryBlock:
    """Test COLLABORATIVE_MEMORY block (shared memories)"""

    @pytest.mark.unit
    def test_create_collaborative_memory_block(self):
        """Should create valid COLLABORATIVE_MEMORY block"""
        block = create_collaborative_memory_block(
            qube_id="COLLAB01",
            block_number=12,
            event_description="Project discussion: Building test suite",
            participants=["QUBE_A", "QUBE_B", "QUBE_C"],
            shared_data_hash="hash_xyz789",
            contribution_weights={"QUBE_A": 0.4, "QUBE_B": 0.3, "QUBE_C": 0.3},
            signatures={"QUBE_A": "sig_a", "QUBE_B": "sig_b", "QUBE_C": "sig_c"},
            previous_hash="prev_collab_hash"
        )

        assert block.block_type == BlockType.COLLABORATIVE_MEMORY
        assert block.content["event_description"] == "Project discussion: Building test suite"
        assert len(block.content["participants"]) == 3


# ==============================================================================
# SUMMARY BLOCK TESTS
# ==============================================================================

class TestSummaryBlock:
    """Test SUMMARY block (condensed memory)"""

    @pytest.mark.unit
    def test_create_summary_block(self):
        """Should create valid SUMMARY block"""
        block = create_summary_block(
            qube_id="SUM12345",
            block_number=100,
            summarized_blocks=[50, 55, 60, 65, 70],
            block_count=5,
            time_period="2024-01-01 to 2024-01-07",
            summary_text="Week summary: 50 conversations completed",
            previous_hash="prev_sum_hash"
        )

        assert block.block_type == BlockType.SUMMARY
        assert block.content["block_count"] == 5
        assert block.content["summary_text"] == "Week summary: 50 conversations completed"


# ==============================================================================
# BLOCK LINKING TESTS
# ==============================================================================

class TestBlockLinking:
    """Test block chain linking with previous_hash"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_blocks_link_via_previous_hash(self):
        """Blocks should link via previous_hash forming a chain"""
        block1 = create_thought_block(
            qube_id="LINK1234",
            block_number=1,
            internal_monologue="First thought",
            previous_hash="genesis_hash"
        )
        block1.block_hash = block1.compute_hash()

        block2 = create_thought_block(
            qube_id="LINK1234",
            block_number=2,
            internal_monologue="Second thought",
            previous_hash=block1.block_hash
        )

        assert block2.previous_hash == block1.block_hash
        assert block2.block_number == block1.block_number + 1

    @pytest.mark.unit
    @pytest.mark.security
    def test_hash_chain_integrity(self):
        """Modifying earlier block should break hash chain"""
        # Create chain of 2 blocks
        block1 = create_thought_block(
            qube_id="INTEGRITY",
            block_number=1,
            internal_monologue="Original",
            previous_hash="0" * 64
        )
        hash1 = block1.compute_hash()
        block1.block_hash = hash1

        block2 = create_thought_block(
            qube_id="INTEGRITY",
            block_number=2,
            internal_monologue="Second",
            previous_hash=hash1
        )

        # Verify link is correct
        assert block2.previous_hash == block1.block_hash

        # Modify block1's content
        block1.content["internal_monologue"] = "Modified"
        new_hash1 = block1.compute_hash()

        # Block2's previous_hash now points to invalid hash
        assert block2.previous_hash != new_hash1
        assert block2.previous_hash == hash1  # Still points to old hash


# ==============================================================================
# EDGE CASES
# ==============================================================================

class TestBlockEdgeCases:
    """Test edge cases and unusual scenarios"""

    @pytest.mark.unit
    def test_block_with_empty_content(self):
        """Block with empty content dictionary should be valid"""
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="EMPTY123",
            content={}
        )

        assert block.content == {}

    @pytest.mark.unit
    def test_block_with_large_content(self):
        """Block should handle large content"""
        large_text = "x" * 100000  # 100KB text

        block = Block(
            block_type=BlockType.MESSAGE,
            block_number=1,
            qube_id="LARGE123",
            content={"message_body": large_text}
        )

        assert len(block.content["message_body"]) == 100000

    @pytest.mark.unit
    def test_block_with_nested_content(self):
        """Block content can be deeply nested"""
        nested_content = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": "deep value"
                    }
                }
            }
        }

        block = Block(
            block_type=BlockType.OBSERVATION,
            block_number=1,
            qube_id="NESTED12",
            content=nested_content
        )

        assert block.content["level1"]["level2"]["level3"]["data"] == "deep value"

    @pytest.mark.unit
    def test_temporary_block_without_session_id(self):
        """Temporary block without session_id should still be valid"""
        # This might happen during creation before session_id is assigned
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=1,
            qube_id="TEMP1234",
            temporary=True
            # No session_id provided
        )

        assert block.temporary is True
        assert block.session_id is None

    @pytest.mark.unit
    def test_block_number_zero_for_non_genesis(self):
        """Non-GENESIS blocks can theoretically have block_number 0 (unusual but valid)"""
        block = Block(
            block_type=BlockType.THOUGHT,
            block_number=0,
            qube_id="ZERO1234"
        )

        assert block.block_number == 0
        assert block.block_type == BlockType.THOUGHT


# ==============================================================================
# LEARNING BLOCK TESTS (Phase 0)
# ==============================================================================

class TestLearningBlockType:
    """Test the LEARNING block type exists and works correctly"""

    @pytest.mark.unit
    def test_learning_block_type_exists(self):
        """Verify LEARNING block type is defined"""
        assert hasattr(BlockType, 'LEARNING')
        assert BlockType.LEARNING.value == "LEARNING"

    @pytest.mark.unit
    def test_valid_learning_types(self):
        """Verify all learning types are defined"""
        expected_types = {"fact", "procedure", "synthesis", "insight", "pattern", "relationship", "threat", "trust"}
        assert VALID_LEARNING_TYPES == expected_types

    @pytest.mark.unit
    def test_create_learning_block_fact(self):
        """Verify LEARNING block creation for fact type"""
        block = create_learning_block(
            qube_id="TEST1234",
            block_number=42,
            previous_hash="abc123",
            learning_type="fact",
            content_data={"fact": "The sky is blue"},
            confidence=95
        )

        assert block.block_type == BlockType.LEARNING
        assert block.block_number == 42
        assert block.qube_id == "TEST1234"
        assert block.previous_hash == "abc123"
        assert block.content["learning_type"] == "fact"
        assert block.content["fact"] == "The sky is blue"
        assert block.content["confidence"] == 95

    @pytest.mark.unit
    def test_create_learning_block_insight(self):
        """Verify LEARNING block creation for insight type"""
        block = create_learning_block(
            qube_id="TEST1234",
            block_number=43,
            previous_hash="def456",
            learning_type="insight",
            content_data={"insight": "Users prefer simplicity"},
            source_block=10,
            source_block_type="MESSAGE"
        )

        assert block.block_type == BlockType.LEARNING
        assert block.content["learning_type"] == "insight"
        assert block.content["insight"] == "Users prefer simplicity"
        assert block.content["source_block"] == 10
        assert block.content["source_block_type"] == "MESSAGE"

    @pytest.mark.unit
    def test_create_learning_block_threat(self):
        """Verify LEARNING block creation for threat type"""
        block = create_learning_block(
            qube_id="TEST1234",
            block_number=44,
            previous_hash="ghi789",
            learning_type="threat",
            content_data={
                "threat_type": "phishing",
                "threat_description": "Suspicious email pattern detected",
                "severity": "high"
            },
            confidence=80
        )

        assert block.block_type == BlockType.LEARNING
        assert block.content["learning_type"] == "threat"
        assert block.content["threat_type"] == "phishing"
        assert block.content["severity"] == "high"

    @pytest.mark.unit
    def test_create_learning_block_invalid_type(self):
        """Verify LEARNING block rejects invalid learning types"""
        with pytest.raises(ValueError) as exc_info:
            create_learning_block(
                qube_id="TEST1234",
                block_number=45,
                previous_hash="jkl012",
                learning_type="invalid_type",
                content_data={"data": "test"}
            )

        assert "Invalid learning_type" in str(exc_info.value)

    @pytest.mark.unit
    def test_create_learning_block_default_confidence(self):
        """Verify LEARNING block uses default confidence of 80"""
        block = create_learning_block(
            qube_id="TEST1234",
            block_number=46,
            previous_hash="mno345",
            learning_type="pattern",
            content_data={"pattern": "Users log in between 9-10 AM"}
        )

        assert block.content["confidence"] == 80

    @pytest.mark.unit
    def test_learning_block_all_types(self):
        """Verify all learning types can be used"""
        for learning_type in VALID_LEARNING_TYPES:
            block = create_learning_block(
                qube_id="TEST1234",
                block_number=50,
                previous_hash="test123",
                learning_type=learning_type,
                content_data={learning_type: f"Test {learning_type} content"}
            )

            assert block.content["learning_type"] == learning_type
