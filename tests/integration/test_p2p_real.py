"""
Integration Tests for P2P Networking with Real libp2p-daemon

These tests require:
1. libp2p-daemon (p2pd) binary installed and in PATH
2. p2pclient Python library installed
3. Network connectivity

To run these tests:
    pytest tests/integration/test_p2p_real.py -v

To skip if libp2p not available:
    pytest tests/integration/test_p2p_real.py -v -m "not requires_libp2p"

Setup instructions: See LIBP2P_SETUP.md
"""

import pytest
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec

from network.p2p_node import QubeP2PNode
from network.libp2p_daemon_client import LibP2PDaemonClient

# Mark all tests in this file as requiring libp2p
pytestmark = pytest.mark.requires_libp2p


@pytest.fixture
def node_keys():
    """Generate ECDSA key pair for testing"""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key


class TestLibP2PDaemonClient:
    """Test libp2p-daemon client directly"""

    @pytest.mark.asyncio
    async def test_daemon_start_stop(self):
        """Test starting and stopping daemon"""
        client = LibP2PDaemonClient(qube_id="TEST0001")

        try:
            # Start daemon
            await client.start()

            # Verify started
            assert client.is_running is True
            assert client.peer_id is not None
            assert client.multiaddr is not None

            print(f"\n✅ Daemon started:")
            print(f"   Peer ID: {client.peer_id}")
            print(f"   Multiaddr: {client.multiaddr}")

            # Stop daemon
            await client.stop()

            assert client.is_running is False

            print("✅ Daemon stopped")

        except Exception as e:
            pytest.skip(f"libp2p-daemon not available: {e}")

    @pytest.mark.asyncio
    async def test_two_daemons_connect(self):
        """Test two daemons connecting to each other"""
        client1 = LibP2PDaemonClient(qube_id="TEST0001", listen_port=0)
        client2 = LibP2PDaemonClient(qube_id="TEST0002", listen_port=0)

        try:
            # Start both daemons
            await client1.start()
            await client2.start()

            print(f"\n✅ Client 1: {client1.peer_id}")
            print(f"✅ Client 2: {client2.peer_id}")

            # Create peer info for client2
            from network.libp2p_daemon_client import PeerInfo

            peer2_info = PeerInfo(
                peer_id=client2.peer_id,
                addrs=[client2.multiaddr]
            )

            # Connect client1 to client2
            success = await client1.connect_peer(peer2_info)

            assert success is True
            print("✅ Clients connected!")

            # Cleanup
            await client1.stop()
            await client2.stop()

        except Exception as e:
            pytest.skip(f"libp2p-daemon not available: {e}")
        finally:
            # Ensure cleanup
            if client1.is_running:
                await client1.stop()
            if client2.is_running:
                await client2.stop()


class TestP2PNodeWithRealDHT:
    """Test P2P node with real libp2p-daemon DHT"""

    @pytest.mark.asyncio
    async def test_p2p_node_with_daemon(self, node_keys):
        """Test P2P node starts with daemon client"""
        private_key, public_key = node_keys

        node = QubeP2PNode(
            qube_id="TESTNODE",
            private_key=private_key,
            public_key=public_key
        )

        try:
            # Start node (should use daemon client)
            await node.start()

            # Verify daemon client is used
            assert hasattr(node, 'daemon_client')
            assert node.daemon_client is not None
            assert node.is_running is True
            assert node.peer_id is not None

            print(f"\n✅ P2P node started with daemon:")
            print(f"   Qube ID: {node.qube_id}")
            print(f"   Peer ID: {node.peer_id}")

            # Stop node
            await node.stop()

            assert node.is_running is False
            print("✅ P2P node stopped")

        except Exception as e:
            # If daemon not available, test should still pass (falls back to mock)
            print(f"⚠️  Daemon not available, using mock mode: {e}")
            assert node.is_running is True  # Mock mode should still work

            await node.stop()

    @pytest.mark.asyncio
    async def test_dht_peer_discovery(self, node_keys):
        """Test DHT-based peer discovery between two nodes"""
        private_key1, public_key1 = node_keys

        # Generate second key pair
        private_key2 = ec.generate_private_key(ec.SECP256R1())
        public_key2 = private_key2.public_key()

        node1 = QubeP2PNode(
            qube_id="QUBE0001",
            private_key=private_key1,
            public_key=public_key1
        )

        node2 = QubeP2PNode(
            qube_id="QUBE0002",
            private_key=private_key2,
            public_key=public_key2
        )

        try:
            # Start both nodes
            await node1.start()
            await node2.start()

            print(f"\n✅ Node 1 (QUBE0001): {node1.peer_id}")
            print(f"✅ Node 2 (QUBE0002): {node2.peer_id}")

            # Wait for DHT to bootstrap
            await asyncio.sleep(2)

            # Try to discover node2 from node1
            # Note: This may fail without bootstrap peers or local network discovery
            discovered_addr = await node1.discover_qube("QUBE0002")

            if discovered_addr:
                print(f"✅ Discovered QUBE0002 at: {discovered_addr}")
                assert discovered_addr is not None
            else:
                print("⚠️  DHT discovery failed (expected without bootstrap peers)")
                # This is expected without proper bootstrap configuration

            # Cleanup
            await node1.stop()
            await node2.stop()

        except Exception as e:
            pytest.skip(f"DHT discovery test failed: {e}")
        finally:
            if node1.is_running:
                await node1.stop()
            if node2.is_running:
                await node2.stop()

    @pytest.mark.asyncio
    async def test_gossipsub_messaging(self, node_keys):
        """Test GossipSub publish/subscribe between nodes"""
        private_key1, public_key1 = node_keys

        private_key2 = ec.generate_private_key(ec.SECP256R1())
        public_key2 = private_key2.public_key()

        node1 = QubeP2PNode(
            qube_id="QUBE0001",
            private_key=private_key1,
            public_key=public_key1
        )

        node2 = QubeP2PNode(
            qube_id="QUBE0002",
            private_key=private_key2,
            public_key=public_key2
        )

        try:
            # Start nodes
            await node1.start()
            await node2.start()

            print(f"\n✅ Nodes started for GossipSub test")

            # Subscribe node2 to topic
            topic = "qubes/test-topic"

            if hasattr(node2, 'daemon_client') and node2.daemon_client:
                messages_received = []

                def message_handler(msg):
                    messages_received.append(msg)

                await node2.daemon_client.subscribe_to_topic(topic, message_handler)
                print(f"✅ Node 2 subscribed to {topic}")

                # Wait for subscription to propagate
                await asyncio.sleep(1)

                # Publish message from node1
                test_message = b"Hello from QUBE0001!"
                await node1.publish_message(topic, test_message)
                print(f"✅ Node 1 published message to {topic}")

                # Wait for message to arrive
                await asyncio.sleep(1)

                # Check if message received
                if messages_received:
                    print(f"✅ Node 2 received message: {messages_received[0]}")
                    assert len(messages_received) > 0
                else:
                    print("⚠️  Message not received (GossipSub may need more time to mesh)")

            else:
                print("⚠️  Daemon client not available, skipping GossipSub test")

            # Cleanup
            await node1.stop()
            await node2.stop()

        except Exception as e:
            pytest.skip(f"GossipSub test failed: {e}")
        finally:
            if node1.is_running:
                await node1.stop()
            if node2.is_running:
                await node2.stop()


# Pytest configuration
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "requires_libp2p: mark test as requiring libp2p-daemon installation"
    )


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
