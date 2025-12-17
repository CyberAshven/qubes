"""
Test Block Storage Architecture

Tests the complete flow:
1. Session blocks saved as individual unencrypted files
2. Anchoring converts to encrypted permanent blocks
3. Memory search decrypts blocks correctly
4. File structure is correct
"""

import pytest
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization

from core.qube import Qube
from core.block import create_message_block, create_thought_block, create_action_block
from crypto.keys import generate_key_pair, derive_qube_id


@pytest.fixture
def test_qube(tmp_path):
    """Create a test Qube instance with mock"""
    from core.memory_chain import MemoryChain
    from core.chain_state import ChainState

    # Generate keys
    private_key, public_key = generate_key_pair()
    qube_id = derive_qube_id(public_key)

    # Create data directory
    data_dir = tmp_path / "test_user" / "qubes" / f"TestQube_{qube_id}"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create memory chain
    memory_chain = MemoryChain(
        qube_id=qube_id,
        private_key=private_key,
        public_key=public_key,
        data_dir=data_dir,
        anchor_interval=100
    )

    # Create chain state
    chain_state = ChainState(qube_id, data_dir / "chain")

    # Create mock Qube object with necessary methods
    class MockQube:
        def __init__(self):
            self.qube_id = qube_id
            self.private_key = private_key
            self.public_key = public_key
            self.memory_chain = memory_chain
            self.chain_state = chain_state
            self.data_dir = str(data_dir)
            self.auto_anchor_enabled = False
            self.current_session = None

        def encrypt_block_content(self, content):
            from crypto.encryption import encrypt_block_data
            from crypto.keys import serialize_private_key
            import hashlib

            # Derive encryption key from private key
            private_key_bytes = serialize_private_key(self.private_key)
            encryption_key = hashlib.sha256(private_key_bytes).digest()

            return encrypt_block_data(content, encryption_key)

        def decrypt_block_content(self, encrypted_content):
            from crypto.encryption import decrypt_block_data
            from crypto.keys import serialize_private_key
            import hashlib

            # Derive encryption key from private key
            private_key_bytes = serialize_private_key(self.private_key)
            encryption_key = hashlib.sha256(private_key_bytes).digest()

            return decrypt_block_data(encrypted_content, encryption_key)

    qube = MockQube()

    # Create a session for the qube
    from core.session import Session
    qube.current_session = Session(qube)

    yield qube

    # Cleanup
    if data_dir.exists():
        shutil.rmtree(data_dir.parent.parent)


def test_session_block_storage(test_qube):
    """Test that session blocks are saved as individual unencrypted files"""
    from core.block import Block, BlockType

    # Start a session
    session = test_qube.current_session
    assert session is not None

    # Create some session blocks using simple Block constructor
    msg_block = Block(
        block_type=BlockType.MESSAGE,
        block_number=-1,
        qube_id=test_qube.qube_id,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        content={
            "message_type": "human_to_qube",
            "recipient_id": test_qube.qube_id,
            "message_body": "Hello, test qube!",
            "conversation_id": "test-conv-1"
        },
        encrypted=False,
        temporary=True
    )

    thought_block = Block(
        block_type=BlockType.THOUGHT,
        block_number=-2,
        qube_id=test_qube.qube_id,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        content={
            "thought_content": "I should respond to the greeting.",
            "reasoning_chain": ["User greeted me", "I should be polite"],
            "confidence": 0.95
        },
        encrypted=False,
        temporary=True
    )

    action_block = Block(
        block_type=BlockType.ACTION,
        block_number=-3,
        qube_id=test_qube.qube_id,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        content={
            "action_type": "respond",
            "parameters": {"response": "Hello, test user!"},
            "initiated_by": "self"
        },
        encrypted=False,
        temporary=True
    )

    # Add blocks to session
    session.create_block(msg_block)
    session.create_block(thought_block)
    session.create_block(action_block)

    # Verify session directory exists
    session_dir = Path(test_qube.data_dir) / "blocks" / "session" / session.session_id
    assert session_dir.exists()

    # Verify individual block files exist
    block_files = list(session_dir.glob("*.json"))
    assert len(block_files) == 3

    # Verify filename format
    for block_file in block_files:
        # Format: {block_number}_{type}_{timestamp}.json
        name = block_file.stem
        parts = name.split("_")
        assert len(parts) >= 3
        assert parts[0].startswith("-")  # Negative block number

    # Verify blocks are unencrypted
    for block_file in block_files:
        with open(block_file, 'r') as f:
            block_data = json.load(f)

        assert block_data.get("encrypted") == False
        assert block_data.get("temporary") == True

        # Content should be plain dict, not encrypted
        content = block_data.get("content", {})
        assert isinstance(content, dict)
        assert "nonce" not in content  # Not encrypted
        assert "ciphertext" not in content

        # Should have message_body, thought_content, or action_type
        if block_data["block_type"] == "MESSAGE":
            assert "message_body" in content
            assert content["message_body"] == "Hello, test qube!"
        elif block_data["block_type"] == "THOUGHT":
            assert "thought_content" in content
        elif block_data["block_type"] == "ACTION":
            assert "action_type" in content

    print(f"✅ Session blocks saved correctly: {len(block_files)} unencrypted files")


def test_permanent_block_storage(test_qube):
    """Test that permanent blocks are saved as individual encrypted files"""

    # Start a session and create blocks
    session = test_qube.current_session

    msg_block = create_message_block(
        qube_id=test_qube.qube_id,
        block_number=-1,
        previous_hash="",
        message_type="human_to_qube",
        sender_id="test_user",
        recipient_id=test_qube.qube_id,
        message_body="This will be encrypted!"
    )

    session.create_block(msg_block)

    # Anchor to chain
    converted_blocks = session.anchor_to_chain(create_summary=False)

    # Verify permanent directory exists
    permanent_dir = Path(test_qube.data_dir) / "blocks" / "permanent"
    assert permanent_dir.exists()

    # Verify genesis block (0) + converted block (1) exist
    block_files = list(permanent_dir.glob("*.json"))
    assert len(block_files) >= 2

    # Find the message block file (should be block 1)
    message_file = None
    for block_file in block_files:
        with open(block_file, 'r') as f:
            block_data = json.load(f)
        if block_data.get("block_number") == 1:
            message_file = block_file
            break

    assert message_file is not None

    # Verify filename format
    name = message_file.stem
    parts = name.split("_")
    assert len(parts) >= 3
    assert parts[0] == "1"  # Positive block number
    assert parts[1] == "MESSAGE"

    # Verify block is encrypted
    with open(message_file, 'r') as f:
        block_data = json.load(f)

    assert block_data.get("encrypted") == True
    assert block_data.get("temporary") == False

    # Content should be encrypted
    content = block_data.get("content", {})
    assert isinstance(content, dict)
    assert "nonce" in content  # Encrypted
    assert "ciphertext" in content
    assert "tag" in content

    # Should NOT have plain message_body
    assert "message_body" not in content

    # Verify block has hash and signature
    assert block_data.get("block_hash") is not None
    assert block_data.get("signature") is not None

    # Verify previous_block_number is NOT in permanent block
    assert "previous_block_number" not in block_data

    # Verify previous_hash IS in permanent block
    assert "previous_hash" in block_data

    # Verify session directory was cleaned up
    session_dir = Path(test_qube.data_dir) / "blocks" / "session" / session.session_id
    assert not session_dir.exists()

    print(f"✅ Permanent block encrypted correctly: {message_file.name}")
    print(f"   - Content encrypted: ✓")
    print(f"   - Hash: {block_data['block_hash'][:16]}...")
    print(f"   - Signature: {block_data['signature'][:16]}...")


def test_memory_chain_loads_from_files(test_qube):
    """Test that MemoryChain loads blocks from individual files"""

    # Create and anchor some blocks
    session = test_qube.current_session

    for i in range(3):
        msg_block = create_message_block(
            qube_id=test_qube.qube_id,
            block_number=-(i+1),
            previous_hash="",
            message_type="human_to_qube",
            sender_id="test_user",
            recipient_id=test_qube.qube_id,
            message_body=f"Message {i+1}"
        )
        session.create_block(msg_block)

    session.anchor_to_chain(create_summary=False)

    # Verify memory chain has correct length
    # Genesis (0) + 3 messages (1, 2, 3) = 4 blocks
    assert test_qube.memory_chain.get_chain_length() == 4

    # Verify we can load each block
    for i in range(4):
        block = test_qube.memory_chain.get_block(i)
        assert block is not None
        assert block.block_number == i

        # Verify permanent blocks have encrypted content
        if i > 0:  # Skip genesis
            assert block.encrypted == True
            assert isinstance(block.content, dict)
            assert "nonce" in block.content

    # Verify latest block
    latest = test_qube.memory_chain.get_latest_block()
    assert latest is not None
    assert latest.block_number == 3

    print(f"✅ Memory chain loads correctly: {test_qube.memory_chain.get_chain_length()} blocks")


def test_memory_search_decryption(test_qube):
    """Test that memory search properly decrypts recalled blocks"""

    # Create and anchor a block with specific content
    session = test_qube.current_session

    msg_block = create_message_block(
        qube_id=test_qube.qube_id,
        block_number=-1,
        previous_hash="",
        message_type="human_to_qube",
        sender_id="test_user",
        recipient_id=test_qube.qube_id,
        message_body="This is a secret message about quantum computing!"
    )

    session.create_block(msg_block)
    session.anchor_to_chain(create_summary=False)

    # Get the block from chain (should be encrypted)
    block = test_qube.memory_chain.get_block(1)
    assert block.encrypted == True

    # Test decryption
    decrypted_content = test_qube.decrypt_block_content(block.content)
    assert isinstance(decrypted_content, dict)
    assert "message_body" in decrypted_content
    assert decrypted_content["message_body"] == "This is a secret message about quantum computing!"

    # Test _summarize_block_content (used by memory search)
    from ai.reasoner import Reasoner

    # Create reasoner
    reasoner = Reasoner(test_qube)

    # Get block as dict
    block_dict = block.to_dict()

    # Summarize (should decrypt automatically)
    summary = reasoner._summarize_block_content(block_dict)

    # Should contain the decrypted message
    assert "secret message" in summary.lower() or "quantum computing" in summary.lower()

    print(f"✅ Memory search decryption works correctly")
    print(f"   - Encrypted content: {block.content['ciphertext'][:20]}...")
    print(f"   - Decrypted summary: {summary}")


def test_complete_flow(test_qube):
    """Test complete flow: create session → anchor → verify files → load → decrypt"""

    print("\n" + "="*60)
    print("COMPLETE BLOCK STORAGE FLOW TEST")
    print("="*60)

    # Step 1: Create session blocks
    print("\n📝 Step 1: Creating session blocks...")
    session = test_qube.current_session

    blocks_created = []
    for i in range(5):
        msg_block = create_message_block(
            qube_id=test_qube.qube_id,
            block_number=-(i+1),
            previous_hash="",
            message_type="human_to_qube",
            sender_id="test_user",
            recipient_id=test_qube.qube_id,
            message_body=f"Test message {i+1}"
        )
        session.create_block(msg_block)
        blocks_created.append(msg_block)

    # Verify session files
    session_dir = Path(test_qube.data_dir) / "blocks" / "session" / session.session_id
    session_files = list(session_dir.glob("*.json"))
    print(f"   ✓ Created {len(session_files)} session block files")

    # Step 2: Anchor to chain
    print("\n⚓ Step 2: Anchoring session to permanent chain...")
    converted_blocks = session.anchor_to_chain(create_summary=False)
    print(f"   ✓ Converted {len(converted_blocks)} blocks to permanent")

    # Step 3: Verify file structure
    print("\n📂 Step 3: Verifying file structure...")
    permanent_dir = Path(test_qube.data_dir) / "blocks" / "permanent"
    permanent_files = list(permanent_dir.glob("*.json"))
    print(f"   ✓ Found {len(permanent_files)} permanent block files")

    # Genesis (0) + 5 messages (1-5) = 6 blocks
    assert len(permanent_files) == 6

    # Session directory should be deleted
    assert not session_dir.exists()
    print(f"   ✓ Session directory cleaned up")

    # Step 4: Load and verify blocks
    print("\n📖 Step 4: Loading blocks from files...")
    for i in range(1, 6):  # Skip genesis, check converted blocks
        block = test_qube.memory_chain.get_block(i)
        assert block is not None

        # Verify encrypted
        assert block.encrypted == True
        assert "nonce" in block.content

        # Decrypt and verify
        decrypted = test_qube.decrypt_block_content(block.content)
        expected_message = f"Test message {i}"
        assert decrypted["message_body"] == expected_message

        print(f"   ✓ Block {i}: Loaded, encrypted, and decrypted successfully")

    # Step 5: Test integrity
    print("\n🔒 Step 5: Verifying chain integrity...")
    assert test_qube.memory_chain.verify_chain_integrity()
    print(f"   ✓ Chain integrity verified")

    print("\n" + "="*60)
    print("✅ COMPLETE FLOW TEST PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Allow running directly for manual testing
    from datetime import datetime, timezone
    from cryptography.hazmat.primitives import serialization
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test qube
        private_key, public_key = generate_key_pair()
        qube_id = derive_qube_id(public_key)

        data_dir = tmp_path / "test_user" / "qubes" / f"TestQube_{qube_id}"
        data_dir.mkdir(parents=True, exist_ok=True)

        genesis_block = {
            "block_type": "GENESIS",
            "block_number": 0,
            "qube_id": qube_id,
            "qube_name": "TestQube",
            "creator": "test_user",
            "public_key": public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode(),
            "birth_timestamp": int(datetime.now(timezone.utc).timestamp()),
            "genesis_prompt": "You are a test qube for validating block storage.",
            "ai_model": "gpt-4o-mini",
            "capabilities": {
                "web_search": False,
                "image_generation": False
            },
            "default_trust_level": 50,
            "merkle_root": None,
            "previous_hash": "0" * 64
        }

        qube = Qube(
            qube_id=qube_id,
            qube_name="TestQube",
            creator="test_user",
            genesis_block=genesis_block,
            private_key=private_key,
            public_key=public_key,
            data_dir=str(data_dir)
        )

        print("\nRunning tests...\n")

        test_session_block_storage(qube)
        print()

        # Create new qube for each test
        test_permanent_block_storage(qube)
        print()

        test_memory_chain_loads_from_files(qube)
        print()

        test_memory_search_decryption(qube)
        print()

        test_complete_flow(qube)
