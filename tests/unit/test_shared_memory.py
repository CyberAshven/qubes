"""
Tests for Shared Memory Module (Phase 6)

Tests permissions, collaborative memory, memory market, and caching.
From docs/07_Shared_Memory_Architecture.md
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

from shared_memory import (
    MemoryPermission,
    PermissionManager,
    PermissionLevel,
    CollaborativeMemoryBlock,
    CollaborativeSession,
    CollaborativeStatus,
    MemoryMarketListing,
    MemoryMarket,
    ListingStatus,
    SharedMemoryCache
)


class TestMemoryPermission:
    """Test memory permission system"""

    def test_create_permission(self):
        """Test creating a basic permission"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        assert permission.granted_by == "qube_a"
        assert permission.granted_to == "qube_b"
        assert permission.permission_id is not None
        assert len(permission.granted_blocks) == 0
        assert permission.permission_level == PermissionLevel.READ
        assert permission.revoked is False

    def test_grant_access(self):
        """Test granting access to blocks"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        permission.grant_access([1, 2, 3], PermissionLevel.READ_WRITE, expiry_days=30)

        assert len(permission.granted_blocks) == 3
        assert permission.permission_level == PermissionLevel.READ_WRITE
        assert permission.expiry_timestamp is not None

    def test_revoke_access(self):
        """Test revoking permission"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        permission.grant_access([1, 2, 3])
        assert permission.is_valid()

        permission.revoke_access()
        assert not permission.is_valid()
        assert permission.revoked is True

    def test_expiry(self):
        """Test permission expiry"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        # Set expiry in the past
        permission.grant_access([1, 2, 3], expiry_days=-1)

        assert permission.is_expired()
        assert not permission.is_valid()

    def test_can_access_block(self):
        """Test block access checking"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        permission.grant_access([1, 2, 3])

        assert permission.can_access_block(1)
        assert permission.can_access_block(2)
        assert not permission.can_access_block(4)

    def test_serialization(self):
        """Test permission serialization"""
        permission = MemoryPermission(
            granted_by="qube_a",
            granted_to="qube_b"
        )

        permission.grant_access([1, 2, 3], PermissionLevel.READ_WRITE)

        # Serialize
        data = permission.to_dict()
        assert data["granted_by"] == "qube_a"
        assert data["granted_to"] == "qube_b"
        assert data["granted_blocks"] == [1, 2, 3]

        # Deserialize
        restored = MemoryPermission.from_dict(data)
        assert restored.granted_by == permission.granted_by
        assert restored.granted_to == permission.granted_to
        assert restored.granted_blocks == permission.granted_blocks


class TestPermissionManager:
    """Test permission manager"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def test_create_permission(self):
        """Test creating permission via manager"""
        manager = PermissionManager(self.temp_dir)

        permission = manager.create_permission(
            granted_to="qube_b",
            block_numbers=[1, 2, 3],
            granted_by="qube_a"
        )

        assert permission.permission_id in manager.permissions
        assert len(manager.permissions) == 1

    def test_get_permissions_for_qube(self):
        """Test retrieving permissions for a Qube"""
        manager = PermissionManager(self.temp_dir)

        manager.create_permission("qube_b", [1, 2], "qube_a")
        manager.create_permission("qube_c", [3, 4], "qube_a")
        manager.create_permission("qube_b", [5, 6], "qube_d")

        qube_b_permissions = manager.get_permissions_for_qube("qube_b")
        assert len(qube_b_permissions) == 2

    def test_can_access_block(self):
        """Test checking block access"""
        manager = PermissionManager(self.temp_dir)

        manager.create_permission("qube_b", [1, 2, 3], "qube_a")

        assert manager.can_access_block("qube_b", 1)
        assert manager.can_access_block("qube_b", 2)
        assert not manager.can_access_block("qube_b", 4)
        assert not manager.can_access_block("qube_c", 1)

    def test_persistence(self):
        """Test permission persistence"""
        manager1 = PermissionManager(self.temp_dir)
        manager1.create_permission("qube_b", [1, 2, 3], "qube_a")

        # Create new manager with same directory
        manager2 = PermissionManager(self.temp_dir)
        assert len(manager2.permissions) == 1
        assert manager2.can_access_block("qube_b", 1)

    def test_get_stats(self):
        """Test permission statistics"""
        manager = PermissionManager(self.temp_dir)

        manager.create_permission("qube_b", [1, 2], "qube_a", PermissionLevel.READ)
        manager.create_permission("qube_c", [3, 4], "qube_a", PermissionLevel.READ_WRITE)

        p = manager.create_permission("qube_d", [5], "qube_a")
        p.revoke_access()
        manager.save_permissions()

        stats = manager.get_stats()
        assert stats["total_permissions"] == 3
        assert stats["valid_permissions"] == 2
        assert stats["revoked_permissions"] == 1


class TestCollaborativeMemory:
    """Test collaborative memory blocks"""

    def test_create_collaborative_block(self):
        """Test creating collaborative memory"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b", "qube_c"],
            content={"event": "meeting", "notes": "Discussed project"},
            initiator="qube_a"
        )

        assert len(block.participants) == 3
        assert block.threshold == 3
        assert block.status == CollaborativeStatus.DRAFT

    def test_add_signature(self):
        """Test adding participant signatures"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b"],
            content={"event": "collaboration"},
            initiator="qube_a"
        )

        assert block.add_signature("qube_a", "sig_a")
        assert block.status == CollaborativeStatus.PARTIALLY_SIGNED

        assert block.add_signature("qube_b", "sig_b")
        assert block.status == CollaborativeStatus.COMPLETE
        assert block.is_valid()

    def test_reject_collaboration(self):
        """Test rejecting collaborative memory"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b"],
            content={"event": "collaboration"},
            initiator="qube_a"
        )

        block.reject("qube_b", "Not accurate")
        assert block.status == CollaborativeStatus.REJECTED
        assert "qube_b" in block.rejections

    def test_get_missing_signatures(self):
        """Test tracking missing signatures"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b", "qube_c"],
            content={"event": "meeting"},
            initiator="qube_a"
        )

        block.add_signature("qube_a", "sig_a")

        missing = block.get_missing_signatures()
        assert len(missing) == 2
        assert "qube_b" in missing
        assert "qube_c" in missing

    def test_non_participant_signature(self):
        """Test rejecting signature from non-participant"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b"],
            content={"event": "meeting"},
            initiator="qube_a"
        )

        assert not block.add_signature("qube_c", "sig_c")
        assert len(block.signatures) == 0

    def test_serialization(self):
        """Test collaborative block serialization"""
        block = CollaborativeMemoryBlock(
            participants=["qube_a", "qube_b"],
            content={"event": "meeting"},
            initiator="qube_a"
        )

        block.add_signature("qube_a", "sig_a")

        data = block.to_dict()
        restored = CollaborativeMemoryBlock.from_dict(data)

        assert restored.participants == block.participants
        assert restored.content == block.content
        assert restored.signatures == block.signatures


class TestCollaborativeSession:
    """Test collaborative session manager"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def test_create_session(self):
        """Test creating collaborative session"""
        session = CollaborativeSession(self.temp_dir)

        block = session.create_session(
            participants=["qube_a", "qube_b"],
            content={"event": "meeting"},
            initiator="qube_a"
        )

        assert block.block_id in session.active_sessions

    def test_add_signature_to_session(self):
        """Test adding signatures to session"""
        session = CollaborativeSession(self.temp_dir)

        block = session.create_session(
            participants=["qube_a", "qube_b"],
            content={"event": "meeting"},
            initiator="qube_a"
        )

        assert session.add_signature(block.block_id, "qube_a", "sig_a")
        assert session.add_signature(block.block_id, "qube_b", "sig_b")

        retrieved = session.get_session(block.block_id)
        assert retrieved.is_complete()

    def test_get_pending_sessions(self):
        """Test retrieving pending sessions for Qube"""
        session = CollaborativeSession(self.temp_dir)

        session.create_session(["qube_a", "qube_b"], {"event": "meeting1"}, "qube_a")
        session.create_session(["qube_a", "qube_c"], {"event": "meeting2"}, "qube_c")

        pending = session.get_pending_sessions_for_qube("qube_a")
        assert len(pending) == 2

    def test_persistence(self):
        """Test session persistence"""
        session1 = CollaborativeSession(self.temp_dir)
        block = session1.create_session(["qube_a", "qube_b"], {"event": "meeting"}, "qube_a")

        session2 = CollaborativeSession(self.temp_dir)
        assert len(session2.active_sessions) == 1
        assert session2.get_session(block.block_id) is not None


class TestMemoryMarket:
    """Test memory market system"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def test_create_listing(self):
        """Test creating marketplace listing"""
        market = MemoryMarket(self.temp_dir)

        listing = market.create_listing(
            seller_qube_id="qube_a",
            memory_block_hashes=["hash1", "hash2", "hash3"],
            block_numbers=[1, 2, 3],
            description="Quantum computing research",
            price=5.0,
            expertise_domain="quantum_computing"
        )

        assert listing.listing_id in market.listings
        assert listing.is_available()

    def test_search_listings(self):
        """Test searching marketplace"""
        market = MemoryMarket(self.temp_dir)

        market.create_listing("qube_a", ["h1"], [1], "Quantum research", 5.0, "quantum_computing")
        market.create_listing("qube_b", ["h2"], [1], "ML research", 3.0, "machine_learning")
        market.create_listing("qube_c", ["h3"], [1], "Quantum algorithms", 10.0, "quantum_computing")

        quantum_listings = market.search_listings(expertise_domain="quantum_computing")
        assert len(quantum_listings) == 2

        affordable_listings = market.search_listings(max_price=5.0)
        assert len(affordable_listings) == 2

    def test_listing_expiry(self):
        """Test listing expiration"""
        market = MemoryMarket(self.temp_dir)

        listing = market.create_listing(
            seller_qube_id="qube_a",
            memory_block_hashes=["hash1"],
            block_numbers=[1],
            description="Research",
            price=5.0,
            expertise_domain="test",
            expiry_days=-1  # Already expired
        )

        assert not listing.is_available()
        assert listing.status == ListingStatus.EXPIRED

    def test_max_sales(self):
        """Test maximum sales limit"""
        market = MemoryMarket(self.temp_dir)

        listing = market.create_listing(
            seller_qube_id="qube_a",
            memory_block_hashes=["hash1"],
            block_numbers=[1],
            description="Research",
            price=1.0,
            expertise_domain="test",
            max_sales=1
        )

        # Simulate first purchase
        listing.buyers.append({"buyer_id": "qube_b"})

        assert listing.is_available() is False  # Should be sold out
        listing._update_status() if hasattr(listing, '_update_status') else None

    def test_market_stats(self):
        """Test marketplace statistics"""
        market = MemoryMarket(self.temp_dir)

        listing1 = market.create_listing("qube_a", ["h1"], [1], "Research1", 5.0, "quantum")
        listing2 = market.create_listing("qube_b", ["h2"], [1], "Research2", 3.0, "ml")

        # Simulate purchase
        listing1.buyers.append({"buyer_id": "qube_c", "amount_paid": 5.0})

        stats = market.get_market_stats()
        assert stats["total_listings"] == 2
        assert stats["active_listings"] == 2
        assert stats["total_sales"] == 1

    def test_get_purchases_by_buyer(self):
        """Test retrieving buyer's purchase history"""
        market = MemoryMarket(self.temp_dir)

        listing = market.create_listing("qube_a", ["h1"], [1], "Research", 5.0, "quantum")
        listing.buyers.append({
            "buyer_id": "qube_b",
            "amount_paid": 5.0,
            "purchased_at": datetime.now().isoformat(),
            "tx_hash": "tx123",
            "permission_id": "perm123"
        })
        market.save_listing(listing)

        purchases = market.get_purchases_by_buyer("qube_b")
        assert len(purchases) == 1
        assert purchases[0]["seller_id"] == "qube_a"


class TestSharedMemoryCache:
    """Test shared memory cache"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def test_add_and_get_memory(self):
        """Test adding and retrieving cached memory"""
        cache = SharedMemoryCache(self.temp_dir)

        block_data = {"content": "test memory", "timestamp": "2025-10-04"}

        cache.add_memory(
            source_qube_id="qube_a",
            block_number=1,
            block_data=block_data,
            permission_id="perm123"
        )

        retrieved = cache.get_memory("qube_a", 1)
        assert retrieved == block_data

    def test_cache_miss(self):
        """Test cache miss"""
        cache = SharedMemoryCache(self.temp_dir)

        result = cache.get_memory("qube_a", 999)
        assert result is None

    def test_get_memories_from_qube(self):
        """Test retrieving all memories from a Qube"""
        cache = SharedMemoryCache(self.temp_dir)

        cache.add_memory("qube_a", 1, {"content": "mem1"}, "perm1")
        cache.add_memory("qube_a", 2, {"content": "mem2"}, "perm2")
        cache.add_memory("qube_b", 1, {"content": "mem3"}, "perm3")

        qube_a_memories = cache.get_memories_from_qube("qube_a")
        assert len(qube_a_memories) == 2

    def test_search_cached_memories(self):
        """Test searching cached memories"""
        cache = SharedMemoryCache(self.temp_dir)

        cache.add_memory("qube_a", 1, {"content": "quantum computing"}, "perm1")
        cache.add_memory("qube_a", 2, {"content": "machine learning"}, "perm2")

        results = cache.search_cached_memories("quantum")
        assert len(results) == 1
        assert results[0]["block_data"]["content"] == "quantum computing"

    def test_remove_memory(self):
        """Test removing cached memory"""
        cache = SharedMemoryCache(self.temp_dir)

        cache.add_memory("qube_a", 1, {"content": "test"}, "perm1")
        assert cache.get_memory("qube_a", 1) is not None

        cache.remove_memory("qube_a", 1)
        assert cache.get_memory("qube_a", 1) is None

    def test_clear_cache(self):
        """Test clearing entire cache"""
        cache = SharedMemoryCache(self.temp_dir)

        cache.add_memory("qube_a", 1, {"content": "mem1"}, "perm1")
        cache.add_memory("qube_b", 1, {"content": "mem2"}, "perm2")

        cache.clear_cache()
        assert len(cache.cached_memories) == 0

    def test_persistence(self):
        """Test cache persistence"""
        cache1 = SharedMemoryCache(self.temp_dir)
        cache1.add_memory("qube_a", 1, {"content": "test"}, "perm1")

        cache2 = SharedMemoryCache(self.temp_dir)
        assert cache2.get_memory("qube_a", 1) is not None

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = SharedMemoryCache(self.temp_dir)

        cache.add_memory("qube_a", 1, {"content": "mem1"}, "perm1")
        cache.add_memory("qube_b", 1, {"content": "mem2"}, "perm2")

        stats = cache.get_stats()
        assert stats["total_cached"] == 2
        assert stats["unique_sources"] == 2
