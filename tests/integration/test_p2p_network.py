"""
Test P2P Network Implementation

Tests all Phase 3 components:
- Message encryption (ECDH + AES-256-GCM)
- Handshake protocol
- Qube messaging
- GossipSub
- Rate limiting

NOTE: These tests use mock P2P mode (no actual libp2p-daemon).
For integration tests with real DHT:
1. Install libp2p-daemon (see LIBP2P_SETUP.md)
2. Install p2pclient: pip install p2pclient
3. Run integration tests: pytest tests/integration/test_p2p_real.py

Mock mode tests verify the interface and logic are correct.
Integration tests verify actual DHT discovery and GossipSub messaging.
"""

import pytest
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from network.messaging import EncryptedSession, QubeMessage
from network.handshake import QubeHandshake
from network.qube_messenger import QubeMessenger
from network.discovery.gossip import GossipProtocol
from network.rate_limiter import RateLimiter, SlidingWindowRateLimiter, NetworkRateLimiter
from network.p2p_node import QubeP2PNode


class TestEncryptedSession:
    """Test encrypted session functionality"""

    def test_session_initialization(self):
        """Test creating encrypted session"""
        shared_secret = b"a" * 32  # 32-byte secret
        session = EncryptedSession(shared_secret)

        assert session.shared_secret == shared_secret
        assert session.messages_encrypted == 0
        assert session.messages_decrypted == 0

    def test_session_invalid_secret_length(self):
        """Test that invalid secret length raises error"""
        with pytest.raises(ValueError, match="must be 32 bytes"):
            EncryptedSession(b"too_short")

    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        shared_secret = b"a" * 32
        session = EncryptedSession(shared_secret)

        plaintext = b"Hello, Qube!"
        ciphertext, nonce = session.encrypt(plaintext)

        # Verify ciphertext is different from plaintext
        assert ciphertext != plaintext
        assert len(nonce) == 12  # GCM nonce is 12 bytes

        # Decrypt
        decrypted = session.decrypt(ciphertext, nonce)
        assert decrypted == plaintext

        # Verify stats
        assert session.messages_encrypted == 1
        assert session.messages_decrypted == 1

    def test_decrypt_with_wrong_nonce_fails(self):
        """Test that decryption with wrong nonce fails"""
        shared_secret = b"a" * 32
        session = EncryptedSession(shared_secret)

        plaintext = b"Hello, Qube!"
        ciphertext, _ = session.encrypt(plaintext)

        # Try to decrypt with wrong nonce
        wrong_nonce = b"0" * 12

        from core.exceptions import NetworkError
        with pytest.raises(NetworkError, match="Decryption failed"):
            session.decrypt(ciphertext, wrong_nonce)


class TestQubeMessage:
    """Test Qube message functionality"""

    @pytest.fixture
    def sender_keys(self):
        """Generate sender key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    @pytest.fixture
    def recipient_keys(self):
        """Generate recipient key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    def test_message_creation(self):
        """Test creating a message"""
        message = QubeMessage(
            sender_qube_id="AAAA1111",
            recipient_qube_id="BBBB2222",
            content={"text": "Hello!"},
            message_type="text"
        )

        assert message.sender_qube_id == "AAAA1111"
        assert message.recipient_qube_id == "BBBB2222"
        assert message.content == {"text": "Hello!"}
        assert message.message_type == "text"
        assert message.message_id is not None
        assert message.conversation_id is not None

    def test_message_encryption_and_signing(self, sender_keys, recipient_keys):
        """Test message encryption and signing"""
        sender_private, sender_public = sender_keys
        recipient_private, recipient_public = recipient_keys

        message = QubeMessage(
            sender_qube_id="AAAA1111",
            recipient_qube_id="BBBB2222",
            content={"text": "Secret message!"},
            message_type="text"
        )

        # Encrypt for recipient
        message.encrypt_for_recipient(sender_private, recipient_public)

        assert message.encrypted_content is not None
        assert message.nonce is not None

        # Sign message
        message.sign(sender_private)

        assert message.signature is not None

    def test_message_decryption(self, sender_keys, recipient_keys):
        """Test message decryption"""
        sender_private, sender_public = sender_keys
        recipient_private, recipient_public = recipient_keys

        original_content = {"text": "Secret message!", "data": [1, 2, 3]}

        message = QubeMessage(
            sender_qube_id="AAAA1111",
            recipient_qube_id="BBBB2222",
            content=original_content,
            message_type="text"
        )

        # Encrypt and sign
        message.encrypt_for_recipient(sender_private, recipient_public)
        message.sign(sender_private)

        # Decrypt
        decrypted_content = message.decrypt_from_sender(recipient_private, sender_public)

        assert decrypted_content == original_content

    def test_message_signature_verification(self, sender_keys, recipient_keys):
        """Test signature verification"""
        sender_private, sender_public = sender_keys
        recipient_private, recipient_public = recipient_keys

        message = QubeMessage(
            sender_qube_id="AAAA1111",
            recipient_qube_id="BBBB2222",
            content={"text": "Test"},
            message_type="text"
        )

        message.encrypt_for_recipient(sender_private, recipient_public)
        message.sign(sender_private)

        # Verify with correct key
        assert message.verify_signature(sender_public) is True

        # Verify with wrong key
        wrong_private = ec.generate_private_key(ec.SECP256R1())
        wrong_public = wrong_private.public_key()
        assert message.verify_signature(wrong_public) is False

    def test_message_serialization(self, sender_keys, recipient_keys):
        """Test message serialization and deserialization"""
        sender_private, sender_public = sender_keys
        recipient_private, recipient_public = recipient_keys

        message = QubeMessage(
            sender_qube_id="AAAA1111",
            recipient_qube_id="BBBB2222",
            content={"text": "Hello!"},
            message_type="text",
            conversation_id="conv_123"
        )

        message.encrypt_for_recipient(sender_private, recipient_public)
        message.sign(sender_private)

        # Serialize
        message_dict = message.to_dict()

        assert message_dict["message_id"] == message.message_id
        assert message_dict["sender_qube_id"] == "AAAA1111"
        assert message_dict["recipient_qube_id"] == "BBBB2222"
        assert message_dict["conversation_id"] == "conv_123"

        # Deserialize
        restored_message = QubeMessage.from_dict(message_dict)

        assert restored_message.message_id == message.message_id
        assert restored_message.sender_qube_id == message.sender_qube_id
        assert restored_message.encrypted_content == message.encrypted_content
        assert restored_message.signature == message.signature


class TestQubeHandshake:
    """Test handshake protocol"""

    @pytest.fixture
    def qube_a_keys(self):
        """Generate Qube A key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    @pytest.fixture
    def qube_b_keys(self):
        """Generate Qube B key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    def test_handshake_initialization(self, qube_a_keys):
        """Test creating handshake handler"""
        private_key, public_key = qube_a_keys

        handshake = QubeHandshake(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key
        )

        assert handshake.qube_id == "AAAA1111"
        assert handshake.private_key == private_key
        assert handshake.public_key == public_key
        assert len(handshake.active_sessions) == 0

    def test_nft_proof_generation(self, qube_a_keys):
        """Test NFT proof generation"""
        private_key, public_key = qube_a_keys

        handshake = QubeHandshake(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key,
            nft_contract="0x123...",
            nft_token_id=42
        )

        # Generate proof (mock for now)
        import asyncio
        proof = asyncio.run(handshake.get_nft_proof())

        assert proof is not None
        assert proof["chain"] == "ethereum"
        assert proof["contract"] == "0x123..."
        assert proof["token_id"] == 42

    def test_session_management(self, qube_a_keys):
        """Test session get/close"""
        private_key, public_key = qube_a_keys

        handshake = QubeHandshake(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key
        )

        # Create session manually
        shared_secret = b"a" * 32
        session = EncryptedSession(shared_secret)
        handshake.active_sessions["BBBB2222"] = session

        # Get session
        retrieved = handshake.get_session("BBBB2222")
        assert retrieved == session

        # Close session
        handshake.close_session("BBBB2222")
        assert handshake.get_session("BBBB2222") is None


class TestRateLimiter:
    """Test rate limiting"""

    def test_token_bucket_limiter(self):
        """Test token bucket rate limiter"""
        limiter = RateLimiter(
            rate=10.0,  # 10 tokens per second
            capacity=10,
            name="test"
        )

        # Should allow initial requests
        assert limiter.allow(5) is True
        assert limiter.allow(5) is True

        # Should deny when out of tokens
        assert limiter.allow(1) is False

        # Wait and tokens should refill
        import time
        time.sleep(0.5)  # 0.5 seconds = 5 tokens

        assert limiter.allow(5) is True

    def test_sliding_window_limiter(self):
        """Test sliding window rate limiter"""
        limiter = SlidingWindowRateLimiter(
            max_requests=5,
            window_seconds=60,
            name="test"
        )

        # Allow first 5 requests
        for i in range(5):
            assert limiter.allow() is True

        # Deny 6th request
        assert limiter.allow() is False

        stats = limiter.get_stats()
        assert stats["requests_in_window"] == 5

    def test_network_rate_limiter(self):
        """Test network-wide rate limiting"""
        limiter = NetworkRateLimiter(
            messages_per_qube_per_minute=10,
            handshakes_per_qube_per_hour=5
        )

        # Test message limiting
        for i in range(10):
            allowed, reason = limiter.allow_message("AAAA1111")
            assert allowed is True

        # 11th message should be denied
        allowed, reason = limiter.allow_message("AAAA1111")
        assert allowed is False
        assert reason == "rate_limit_exceeded"

        # Different Qube should still be allowed
        allowed, reason = limiter.allow_message("BBBB2222")
        assert allowed is True

    def test_network_blocklist(self):
        """Test Qube blocking"""
        limiter = NetworkRateLimiter()

        # Block Qube
        limiter.block_qube("AAAA1111", duration_seconds=3600)

        # Should deny all operations
        allowed, reason = limiter.allow_message("AAAA1111")
        assert allowed is False
        assert reason == "qube_blocked"

        allowed, reason = limiter.allow_handshake("AAAA1111")
        assert allowed is False
        assert reason == "qube_blocked"

        # Unblock
        limiter.unblock_qube("AAAA1111")

        # Should allow now
        allowed, reason = limiter.allow_message("AAAA1111")
        assert allowed is True

    def test_connection_limiting(self):
        """Test connection limiting"""
        limiter = NetworkRateLimiter(max_concurrent_connections=3)

        # Allow first 3 connections
        for i in range(3):
            qube_id = f"QUBE_{i}"
            allowed, reason = limiter.allow_connection(qube_id)
            assert allowed is True
            limiter.register_connection(qube_id)

        # 4th connection should be denied
        allowed, reason = limiter.allow_connection("QUBE_4")
        assert allowed is False
        assert reason == "max_connections_reached"

        # Unregister connection
        limiter.unregister_connection("QUBE_0")

        # Now 4th should be allowed
        allowed, reason = limiter.allow_connection("QUBE_4")
        assert allowed is True


class TestP2PNode:
    """Test P2P node"""

    @pytest.fixture
    def node_keys(self):
        """Generate node key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    def test_node_initialization(self, node_keys):
        """Test P2P node initialization"""
        private_key, public_key = node_keys

        node = QubeP2PNode(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key,
            listen_port=4001
        )

        assert node.qube_id == "AAAA1111"
        assert node.listen_port == 4001
        assert node.is_running is False

    @pytest.mark.asyncio
    async def test_node_start_mock_mode(self, node_keys):
        """Test P2P node start (mock mode without libp2p)"""
        private_key, public_key = node_keys

        node = QubeP2PNode(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key
        )

        # Start node (will use mock mode since libp2p not installed)
        await node.start()

        assert node.is_running is True
        assert node.peer_id is not None
        assert node.multiaddr is not None

        # Stop node
        await node.stop()

        assert node.is_running is False


class TestGossipProtocol:
    """Test gossip protocol"""

    @pytest.fixture
    def gossip_keys(self):
        """Generate gossip protocol keys"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    @pytest.mark.asyncio
    async def test_gossip_initialization(self, gossip_keys):
        """Test gossip protocol initialization"""
        private_key, public_key = gossip_keys

        # Create mock p2p node
        node = QubeP2PNode(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key
        )

        gossip = GossipProtocol(
            qube_id="AAAA1111",
            private_key=private_key,
            p2p_node=node
        )

        assert gossip.qube_id == "AAAA1111"
        assert gossip.discovery_topic == "qubes/discovery"
        assert len(gossip.known_qubes) == 0

    @pytest.mark.asyncio
    async def test_gossip_message_handling(self, gossip_keys):
        """Test handling gossip messages"""
        private_key, public_key = gossip_keys

        node = QubeP2PNode(
            qube_id="AAAA1111",
            private_key=private_key,
            public_key=public_key
        )

        gossip = GossipProtocol(
            qube_id="AAAA1111",
            private_key=private_key,
            p2p_node=node
        )

        # Simulate discovery message
        discovery_message = {
            "type": "QUBE_DISCOVERY",
            "from_qube": "BBBB2222",
            "known_qubes": [
                {
                    "qube_id": "CCCC3333",
                    "p2p_address": "/ip4/127.0.0.1/tcp/4001",
                    "last_seen": 1234567890
                }
            ],
            "timestamp": 1234567890
        }

        await gossip.handle_discovery_message(discovery_message)

        # Should have stored the discovered Qube
        assert "CCCC3333" in gossip.known_qubes
        assert gossip.known_qubes["CCCC3333"]["p2p_address"] == "/ip4/127.0.0.1/tcp/4001"


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("TESTING PHASE 3: P2P NETWORK IMPLEMENTATION")
    print("=" * 80)
    print()

    # Run pytest
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])


if __name__ == "__main__":
    run_tests()
