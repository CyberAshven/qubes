"""
Integration test for P2P discovery system

Tests the complete discovery flow without requiring actual libp2p-daemon
"""

import pytest
import asyncio
from network.discovery.resolver import QubeResolver
from blockchain.registry import QubeNFTRegistry
import tempfile
import os


@pytest.mark.asyncio
async def test_resolver_cache():
    """Test resolver caching functionality"""

    print("\n" + "="*70)
    print("🧪 TESTING QUBE RESOLVER CACHE")
    print("="*70 + "\n")

    # Create resolver
    resolver = QubeResolver(cache_ttl_seconds=60)

    # Test empty cache
    stats = resolver.get_cache_stats()
    assert stats['total_entries'] == 0
    print(f"✅ Empty cache verified: {stats}")

    # Add entry to cache
    resolver._add_to_cache("TEST123", "/ip4/127.0.0.1/tcp/4001", "test")

    # Verify cache
    cached = resolver._get_from_cache("TEST123")
    assert cached == "/ip4/127.0.0.1/tcp/4001"
    print(f"✅ Cache add/get working: {cached}")

    # Check stats
    stats = resolver.get_cache_stats()
    assert stats['total_entries'] == 1
    assert stats['by_source']['test'] == 1
    print(f"✅ Cache stats correct: {stats}")

    # Clear cache
    resolver.clear_cache()
    stats = resolver.get_cache_stats()
    assert stats['total_entries'] == 0
    print(f"✅ Cache cleared: {stats}")

    print("\n✅ All cache tests passed!\n")


@pytest.mark.asyncio
async def test_blockchain_registry_discovery():
    """Test blockchain registry integration"""

    print("\n" + "="*70)
    print("🧪 TESTING BLOCKCHAIN REGISTRY DISCOVERY")
    print("="*70 + "\n")

    # Create temporary registry
    temp_dir = tempfile.mkdtemp()
    registry_path = os.path.join(temp_dir, "test_registry.json")
    registry = QubeNFTRegistry(registry_path=registry_path)

    # Register NFT with multiaddr
    test_qube_id = "A1B2C3D4"
    test_multiaddr = "/ip4/192.168.1.100/tcp/5001"

    registry.register_nft(
        qube_id=test_qube_id,
        category_id="test_category_123",
        mint_txid="test_tx_456",
        recipient_address="test_address",
        commitment="test_commit",
        network="mainnet",
        multiaddr=test_multiaddr
    )

    print(f"✅ NFT registered with multiaddr")

    # Verify multiaddr retrieval
    retrieved = registry.get_multiaddr(test_qube_id)
    assert retrieved == test_multiaddr
    print(f"✅ MultiAddr retrieved: {retrieved}")

    # Test update
    new_multiaddr = "/ip4/10.0.0.1/tcp/6001"
    success = registry.update_multiaddr(test_qube_id, new_multiaddr)
    assert success

    retrieved = registry.get_multiaddr(test_qube_id)
    assert retrieved == new_multiaddr
    print(f"✅ MultiAddr updated: {retrieved}")

    # Create resolver and test blockchain discovery
    resolver = QubeResolver()

    # Mock blockchain discovery (without actual p2p node)
    multiaddr = await resolver._discover_via_blockchain(test_qube_id, registry)
    assert multiaddr == new_multiaddr
    print(f"✅ Blockchain discovery working: {multiaddr}")

    print("\n✅ All blockchain registry tests passed!\n")


@pytest.mark.asyncio
async def test_resolver_fallback_chain():
    """Test resolver fallback chain without actual network"""

    print("\n" + "="*70)
    print("🧪 TESTING RESOLVER FALLBACK CHAIN")
    print("="*70 + "\n")

    # Create temporary registry
    temp_dir = tempfile.mkdtemp()
    registry_path = os.path.join(temp_dir, "test_registry.json")
    registry = QubeNFTRegistry(registry_path=registry_path)

    # Register NFT with multiaddr
    test_qube_id = "FALLBACK1"
    test_multiaddr = "/ip4/172.16.0.1/tcp/7001"

    registry.register_nft(
        qube_id=test_qube_id,
        category_id="fallback_cat",
        mint_txid="fallback_tx",
        recipient_address="fallback_addr",
        commitment="fallback_commit",
        multiaddr=test_multiaddr
    )

    # Create resolver
    resolver = QubeResolver()

    # Test discovery with blockchain only (no DHT, no gossip)
    multiaddr = await resolver.discover_qube(
        target_qube_id=test_qube_id,
        p2p_node=None,           # No DHT
        nft_registry=registry,    # Blockchain available
        gossip_protocol=None      # No gossip
    )

    assert multiaddr == test_multiaddr
    print(f"✅ Fallback to blockchain working: {multiaddr}")

    # Verify cache was populated
    cached = resolver._get_from_cache(test_qube_id)
    assert cached == test_multiaddr
    print(f"✅ Cache populated after discovery: {cached}")

    # Test cache-first on second lookup
    multiaddr2 = await resolver.discover_qube(
        target_qube_id=test_qube_id,
        p2p_node=None,
        nft_registry=None,  # Even without registry, should use cache
        gossip_protocol=None
    )

    assert multiaddr2 == test_multiaddr
    print(f"✅ Cache-first retrieval working: {multiaddr2}")

    # Test not found scenario
    multiaddr_none = await resolver.discover_qube(
        target_qube_id="NONEXISTENT",
        p2p_node=None,
        nft_registry=registry,
        gossip_protocol=None
    )

    assert multiaddr_none is None
    print(f"✅ Not found returns None correctly")

    print("\n✅ All fallback chain tests passed!\n")


@pytest.mark.asyncio
async def test_avatar_imports():
    """Test avatar generation module imports"""

    print("\n" + "="*70)
    print("🧪 TESTING AVATAR GENERATION IMPORTS")
    print("="*70 + "\n")

    from ai.avatar_generator import AvatarGenerator

    # Test style listing
    styles = AvatarGenerator.list_styles()
    assert len(styles) == 5
    assert 'cyberpunk' in styles
    assert 'realistic' in styles
    print(f"✅ Avatar styles available: {list(styles.keys())}")

    # Test default avatar
    default = AvatarGenerator.get_default_avatar()
    assert default['source'] == 'default'
    assert default['local_path'] == 'images/qubes_logo.png'
    print(f"✅ Default avatar: {default['source']}")

    # Test generator initialization (without API key)
    generator = AvatarGenerator(api_key=None)
    assert generator.api_key is None
    print(f"✅ Generator initialized without API key")

    print("\n✅ All avatar import tests passed!\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 QUBES DISCOVERY & AVATAR INTEGRATION TESTS")
    print("="*70)

    # Run all tests
    asyncio.run(test_resolver_cache())
    asyncio.run(test_blockchain_registry_discovery())
    asyncio.run(test_resolver_fallback_chain())
    asyncio.run(test_avatar_imports())

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70 + "\n")
