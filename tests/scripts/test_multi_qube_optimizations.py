"""
Test Multi-Qube Conversation Optimizations

Tests the Phase 1 and Phase 2 optimizations:
- Parallel block distribution
- Progress indicators
- Background speaker preparation
- Error handling and retry logic
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from core.multi_qube_conversation import MultiQubeConversation
from core.qube import Qube
from core.session import Session
from core.block import Block


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data"""
    temp_dir = Path(tempfile.mkdtemp(prefix="qubes_opt_test_"))
    yield temp_dir
    # Cleanup
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_qubes(temp_data_dir):
    """Create 3 mock Qubes for testing"""
    qubes = []

    for i, name in enumerate(["Alice", "Bob", "Charlie"]):
        # Create mock Qube
        qube = Mock(spec=Qube)
        qube.qube_id = f"qube_{name.lower()}_{'0' * 54}{i}"
        qube.name = name
        qube.data_dir = temp_data_dir / f"qube_{name.lower()}"
        qube.data_dir.mkdir(parents=True, exist_ok=True)

        # Mock private key for signing
        qube.private_key = f"private_key_{name.lower()}"

        # Mock genesis block with voice model
        qube.genesis_block = Mock()
        qube.genesis_block.voice_model = f"openai:{name.lower()}"

        # Mock session
        qube.current_session = Mock(spec=Session)
        qube.current_session.session_blocks = []
        qube.current_session.create_block = Mock()

        # Mock reasoner
        qube.reasoner = Mock()
        qube.reasoner.process_input = AsyncMock(
            return_value=f"This is {name}'s response to the conversation."
        )

        qubes.append(qube)

    return qubes


@pytest.mark.asyncio
async def test_parallel_block_distribution(mock_qubes):
    """Test that block distribution is parallelized"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="open_discussion"
    )

    # Create a test block
    test_block = Block(
        block_type="MESSAGE",
        block_number=-1,
        previous_block_hash="0" * 64,
        qube_id=mock_qubes[0].qube_id,
        content={
            "message_type": "qube_to_group",
            "sender_id": mock_qubes[0].qube_id,
            "message_body": "Test message",
            "conversation_id": conversation.conversation_id
        }
    )

    # Mock the sign_block function
    with patch('core.multi_qube_conversation.sign_block') as mock_sign:
        mock_sign.return_value = "test_signature"

        # Distribute block
        await conversation._distribute_block_to_participants(test_block)

    # Verify all Qubes received the block
    for qube in mock_qubes:
        qube.current_session.create_block.assert_called_once()

        # Verify the block has all signatures
        call_args = qube.current_session.create_block.call_args[0][0]
        assert "participant_signatures" in call_args.content
        assert len(call_args.content["participant_signatures"]) == len(mock_qubes)

    print("✓ Parallel block distribution test passed")


@pytest.mark.asyncio
async def test_progress_indicators(mock_qubes):
    """Test that continue_conversation returns progress indicators"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="open_discussion"
    )

    # Mock distribution
    with patch.object(conversation, '_distribute_block_to_participants', new_callable=AsyncMock):
        with patch.object(conversation, '_create_qube_message_block', new_callable=AsyncMock) as mock_create:
            # Mock block creation
            mock_block = Mock(spec=Block)
            mock_block.timestamp = "2025-10-15T00:00:00Z"
            mock_create.return_value = mock_block

            # Continue conversation
            result = await conversation.continue_conversation()

    # Verify response structure
    assert "status" in result
    assert result["status"] == "complete"

    assert "timing" in result
    assert "total_ms" in result["timing"]
    assert "ai_generation_ms" in result["timing"]
    assert "distribution_ms" in result["timing"]

    # Verify timing values are present and non-negative
    assert result["timing"]["total_ms"] >= 0
    assert result["timing"]["ai_generation_ms"] >= 0  # Can be 0 for mocked AI
    assert result["timing"]["distribution_ms"] >= 0

    print("✓ Progress indicators test passed")


@pytest.mark.asyncio
async def test_background_preparation(mock_qubes):
    """Test that background speaker preparation works"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="open_discussion"
    )

    # Mock distribution and block creation
    with patch.object(conversation, '_distribute_block_to_participants', new_callable=AsyncMock):
        with patch.object(conversation, '_create_qube_message_block', new_callable=AsyncMock) as mock_create:
            mock_block = Mock(spec=Block)
            mock_block.timestamp = "2025-10-15T00:00:00Z"
            mock_create.return_value = mock_block

            # First turn - no preparation yet
            result1 = await conversation.continue_conversation()
            assert result1["turn_number"] == 1

            # Wait for background preparation to complete
            if conversation._preparation_task:
                await asyncio.sleep(0.1)  # Give it time to complete

            # Second turn - should use prepared speaker
            result2 = await conversation.continue_conversation()
            assert result2["turn_number"] == 2

            # Verify preparation task was created after first turn
            assert conversation._preparation_task is not None

    print("✓ Background preparation test passed")


@pytest.mark.asyncio
async def test_retry_logic_on_timeout(mock_qubes):
    """Test that AI generation retries on timeout"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="round_robin"  # Use round_robin to ensure deterministic speaker
    )

    # Make first reasoner call timeout, second succeed for Alice (first qube)
    call_count = 0
    async def mock_process_with_timeout(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call times out
            raise asyncio.TimeoutError("Simulated timeout")
        else:
            # Second call succeeds
            await asyncio.sleep(0.01)  # Small delay to ensure timeout doesn't trigger
            return "Success after retry"

    # Apply to all qubes so it doesn't matter which one is selected
    for qube in mock_qubes:
        qube.reasoner.process_input = mock_process_with_timeout

    # Mock distribution and block creation
    with patch.object(conversation, '_distribute_block_to_participants', new_callable=AsyncMock):
        with patch.object(conversation, '_create_qube_message_block', new_callable=AsyncMock) as mock_create:
            mock_block = Mock(spec=Block)
            mock_block.timestamp = "2025-10-15T00:00:00Z"
            mock_create.return_value = mock_block

            # Should succeed after retry
            result = await conversation.continue_conversation(
                max_retries=2,
                ai_timeout=0.5
            )

            assert result["message"] == "Success after retry"
            assert call_count == 2  # Verify it retried

    print("✓ Retry logic test passed")


@pytest.mark.asyncio
async def test_error_recovery(mock_qubes):
    """Test recover_from_stuck_state method"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="open_discussion"
    )

    # Simulate stuck state
    conversation._next_speaker_prepared = mock_qubes[0]
    conversation._next_context_prepared = "Some context"
    conversation._preparation_task = Mock()
    conversation._preparation_task.done = Mock(return_value=False)
    conversation._preparation_task.cancel = Mock()

    # Recover
    result = await conversation.recover_from_stuck_state()

    # Verify recovery actions
    assert result["status"] == "recovered"
    assert len(result["actions_taken"]) > 0
    assert "canceled_background_preparation_task" in result["actions_taken"]
    assert "cleared_prepared_speaker" in result["actions_taken"]

    # Verify state was cleared
    assert conversation._next_speaker_prepared is None
    assert conversation._next_context_prepared is None
    assert conversation._preparation_task is None

    print("✓ Error recovery test passed")


@pytest.mark.asyncio
async def test_session_validation(mock_qubes):
    """Test that missing sessions are automatically created"""
    conversation = MultiQubeConversation(
        participating_qubes=mock_qubes,
        user_id="test_user",
        conversation_mode="open_discussion"
    )

    # Simulate missing session
    mock_qubes[1].current_session = None
    mock_qubes[1].start_session = Mock()

    # Mock distribution and block creation
    with patch.object(conversation, '_distribute_block_to_participants', new_callable=AsyncMock):
        with patch.object(conversation, '_create_qube_message_block', new_callable=AsyncMock) as mock_create:
            mock_block = Mock(spec=Block)
            mock_block.timestamp = "2025-10-15T00:00:00Z"
            mock_create.return_value = mock_block

            # Should automatically create missing session
            await conversation.continue_conversation()

            # Verify start_session was called
            mock_qubes[1].start_session.assert_called_once()

    print("✓ Session validation test passed")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
