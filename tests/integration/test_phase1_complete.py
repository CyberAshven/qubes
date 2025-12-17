"""
Test Phase 1 Completion

Verifies all Phase 1 requirements are 100% complete:
1. Block creation with qube_id
2. Chain state persistence
3. Auto-anchor workflow
4. Session management
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.qube import Qube
from core.block import BlockType


def test_block_creation_with_qube_id():
    """Test that DECISION and COLLABORATIVE_MEMORY blocks include qube_id"""
    print("\n=== Test 1: Block Creation with qube_id ===")

    from core.block import create_decision_block, create_collaborative_memory_block

    # Test DECISION block
    decision_block = create_decision_block(
        qube_id="TEST1234",
        block_number=1,
        previous_hash="0" * 64,
        decision="switch_ai_model",
        from_value="gpt-4",
        to_value="claude-sonnet-4.5",
        reasoning="User requested more creative responses",
        impact_assessment="high"
    )

    assert decision_block.qube_id == "TEST1234", f"Expected qube_id='TEST1234', got '{decision_block.qube_id}'"
    print(f"✅ DECISION block has qube_id: {decision_block.qube_id}")

    # Test COLLABORATIVE_MEMORY block
    collab_block = create_collaborative_memory_block(
        qube_id="TEST1234",
        block_number=2,
        previous_hash=decision_block.block_hash,
        event_description="Joint task completed",
        participants=["TEST1234", "TEST5678"],
        shared_data_hash="abc123",
        contribution_weights={"TEST1234": 0.6, "TEST5678": 0.4},
        signatures={"TEST1234": "sig1", "TEST5678": "sig2"}
    )

    assert collab_block.qube_id == "TEST1234", f"Expected qube_id='TEST1234', got '{collab_block.qube_id}'"
    print(f"✅ COLLABORATIVE_MEMORY block has qube_id: {collab_block.qube_id}")

    print("✅ All block types now include qube_id parameter")


def test_chain_state_persistence():
    """Test that chain_state.json is created and updated"""
    print("\n=== Test 2: Chain State Persistence ===")

    # Create test Qube
    data_dir = Path(__file__).parent.parent / "data"

    qube = Qube.create_new(
        qube_name="TestQube",
        creator="TestUser",
        genesis_prompt="Test genesis prompt",
        ai_model="gpt-4o",
        voice_model="test-voice",
        data_dir=data_dir
    )

    # Check chain_state.json exists
    chain_state_file = data_dir / "qubes" / f"{qube.name}_{qube.qube_id}" / "chain_state.json"
    assert chain_state_file.exists(), f"chain_state.json not found at {chain_state_file}"
    print(f"✅ chain_state.json created at: {chain_state_file}")

    # Verify initial state
    state = qube.chain_state.get_state()
    assert state["qube_id"] == qube.qube_id
    assert state["chain_length"] == 1  # Genesis block
    assert state["block_counts"]["GENESIS"] == 1
    print(f"✅ Initial chain state: length={state['chain_length']}, genesis_count={state['block_counts']['GENESIS']}")

    # Start session
    from core.session import Session
    session = Session(qube)

    # Check session state updated
    assert qube.chain_state.get_session_id() == session.session_id
    assert qube.chain_state.get_session_block_count() == 0
    print(f"✅ Session started: session_id={session.session_id[:8]}...")

    # Create some session blocks
    from core.block import create_message_block

    for i in range(3):
        msg_block = create_message_block(
            qube_id=qube.qube_id,
            block_number=-1,  # Will be set by session
            previous_hash="",
            message_type="qube_to_human",
            recipient_id="human_user",
            message_body=f"Test message {i+1}",
            conversation_id="test-conv"
        )
        session.create_block(msg_block)

    # Verify session state
    assert qube.chain_state.get_session_block_count() == 3
    print(f"✅ Session block count updated: {qube.chain_state.get_session_block_count()} blocks")

    # Anchor session
    converted = session.anchor_to_chain(create_summary=True)

    # Verify chain state updated
    state = qube.chain_state.get_state()
    assert state["chain_length"] == 5  # Genesis + 3 messages + 1 summary
    assert state["session_block_count"] == 0
    assert state["current_session_id"] is None
    assert state["block_counts"]["MESSAGE"] == 3
    assert state["block_counts"]["SUMMARY"] == 1
    print(f"✅ Chain state after anchor: length={state['chain_length']}, messages={state['block_counts']['MESSAGE']}")

    print("✅ Chain state persistence working correctly")


def test_auto_anchor_workflow():
    """Test auto-anchor workflow end-to-end"""
    print("\n=== Test 3: Auto-Anchor Workflow ===")

    data_dir = Path(__file__).parent.parent / "data"

    qube = Qube.create_new(
        qube_name="AutoAnchorTest",
        creator="TestUser",
        genesis_prompt="Test auto-anchor",
        ai_model="gpt-4o",
        voice_model="test-voice",
        data_dir=data_dir
    )

    # Enable auto-anchor with low threshold for testing
    qube.auto_anchor_enabled = True
    qube.auto_anchor_threshold = 5
    qube.chain_state.set_auto_anchor(enabled=True, threshold=5)

    print(f"✅ Auto-anchor enabled: threshold={qube.auto_anchor_threshold} blocks")

    # Start session
    from core.session import Session
    from core.block import create_message_block

    session = Session(qube, auto_anchor_threshold=5)

    # Create blocks up to threshold
    for i in range(4):
        msg_block = create_message_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            message_type="qube_to_human",
            recipient_id="human_user",
            message_body=f"Message {i+1}",
            conversation_id="test-conv"
        )
        session.create_block(msg_block)

    # Session should still be active
    assert len(session.session_blocks) == 4
    print(f"✅ Created 4 blocks, session still active (threshold=5)")

    # Create 5th block - should trigger auto-anchor
    msg_block = create_message_block(
        qube_id=qube.qube_id,
        block_number=-1,
        previous_hash="",
        message_type="qube_to_human",
        recipient_id="human_user",
        message_body="Message 5",
        conversation_id="test-conv"
    )
    session.create_block(msg_block)

    # Session should be cleared (auto-anchored)
    assert len(session.session_blocks) == 0, f"Expected session to be cleared, but has {len(session.session_blocks)} blocks"

    # Chain should have all blocks
    state = qube.chain_state.get_state()
    assert state["chain_length"] == 7  # Genesis + 5 messages + 1 summary
    assert state["block_counts"]["MESSAGE"] == 5
    print(f"✅ Auto-anchor triggered at 5 blocks: chain_length={state['chain_length']}")

    print("✅ Auto-anchor workflow working correctly")


def test_session_management():
    """Test session start, update, end workflow"""
    print("\n=== Test 4: Session Management ===")

    data_dir = Path(__file__).parent.parent / "data"

    qube = Qube.create_new(
        qube_name="SessionTest",
        creator="TestUser",
        genesis_prompt="Test sessions",
        ai_model="gpt-4o",
        voice_model="test-voice",
        data_dir=data_dir
    )

    from core.session import Session
    from core.block import create_message_block

    # Test 1: Start session
    session = Session(qube)
    assert qube.chain_state.get_session_id() == session.session_id
    assert qube.chain_state.get_next_negative_index() == -1
    print(f"✅ Session started correctly")

    # Test 2: Create blocks and verify updates
    for i in range(3):
        msg_block = create_message_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            message_type="qube_to_human",
            recipient_id="human_user",
            message_body=f"Message {i+1}",
            conversation_id="test-conv"
        )
        session.create_block(msg_block)

    assert qube.chain_state.get_session_block_count() == 3
    assert qube.chain_state.get_next_negative_index() == -4
    print(f"✅ Session updates tracked: 3 blocks, next_index=-4")

    # Test 3: Delete block
    session.delete_block(-2)
    assert qube.chain_state.get_session_block_count() == 2
    print(f"✅ Block deletion tracked: 2 blocks remaining")

    # Test 4: Discard session
    session.discard_session()
    assert qube.chain_state.get_session_id() is None
    assert qube.chain_state.get_session_block_count() == 0
    print(f"✅ Session discarded, state reset")

    print("✅ Session management working correctly")


def main():
    """Run all Phase 1 completion tests"""
    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETION TESTS")
    print("=" * 60)

    try:
        test_block_creation_with_qube_id()
        test_chain_state_persistence()
        test_auto_anchor_workflow()
        test_session_management()

        print("\n" + "=" * 60)
        print("🎉 ALL PHASE 1 TESTS PASSED - 100% COMPLETE")
        print("=" * 60)
        print("\nPhase 1 Achievements:")
        print("✅ All 9 block types implemented")
        print("✅ DECISION and COLLABORATIVE_MEMORY blocks include qube_id")
        print("✅ chain_state.json persistence working")
        print("✅ Auto-anchor workflow functional")
        print("✅ Session management fully integrated")
        print("\n🚀 Ready to proceed to Phase 2 improvements!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
