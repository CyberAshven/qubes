"""
Tests for Qube Locker

Tests the creative works storage system.

Phase 0: Foundation Tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from core.locker import QubeLocker, LockerItem


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def locker(temp_dir):
    """Create a QubeLocker instance for testing."""
    return QubeLocker(temp_dir)


# ==============================================================================
# INITIALIZATION TESTS
# ==============================================================================

class TestLockerInitialization:
    """Test QubeLocker initialization and directory structure."""

    @pytest.mark.unit
    def test_creates_locker_directory(self, locker, temp_dir):
        """Verify locker base directory is created."""
        assert (Path(temp_dir) / "locker").exists()

    @pytest.mark.unit
    def test_creates_category_directories(self, locker, temp_dir):
        """Verify all category directories are created."""
        locker_path = Path(temp_dir) / "locker"

        for category, subcategories in QubeLocker.CATEGORIES.items():
            for sub in subcategories:
                assert (locker_path / category / sub).exists()

    @pytest.mark.unit
    def test_index_file_created_on_first_store(self, locker, temp_dir):
        """Verify index file is created when storing first item."""
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            locker.store(
                category="writing/poems",
                name="test_poem",
                content="Test poem content"
            )
        )

        assert (Path(temp_dir) / "locker" / "index.json").exists()


# ==============================================================================
# STORE TESTS
# ==============================================================================

class TestLockerStore:
    """Test storing items in the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_text_content(self, locker):
        """Verify storing text content."""
        result = await locker.store(
            category="writing/poems",
            name="sunset_haiku",
            content="Crimson sun descends",
            metadata={"form": "haiku"},
            tags=["nature", "sunset"]
        )

        assert result["success"] is True
        assert result["category"] == "writing/poems"
        assert result["name"] == "sunset_haiku"
        assert "id" in result
        assert "path" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_json_content(self, locker):
        """Verify storing JSON content."""
        result = await locker.store(
            category="stories/characters",
            name="hero",
            content='{"name": "Alex", "class": "warrior"}',
            content_type="json",
            tags=["rpg"]
        )

        assert result["success"] is True
        assert result["category"] == "stories/characters"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_invalid_category(self, locker):
        """Verify storing to invalid category fails."""
        result = await locker.store(
            category="invalid/category",
            name="test",
            content="test content"
        )

        assert result["success"] is False
        assert "Invalid category" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_all_categories(self, locker):
        """Verify storing to all valid categories."""
        for category, subcategories in QubeLocker.CATEGORIES.items():
            for sub in subcategories:
                full_category = f"{category}/{sub}"
                result = await locker.store(
                    category=full_category,
                    name=f"test_{sub}",
                    content=f"Test content for {full_category}"
                )

                assert result["success"] is True, f"Failed for {full_category}"


# ==============================================================================
# GET TESTS
# ==============================================================================

class TestLockerGet:
    """Test retrieving items from the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stored_item(self, locker):
        """Verify retrieving a stored item."""
        await locker.store(
            category="writing/poems",
            name="test_poem",
            content="Test poem content",
            metadata={"author": "test"},
            tags=["test"]
        )

        item = await locker.get("writing/poems", "test_poem")

        assert item is not None
        assert item["name"] == "test_poem"
        assert item["content"] == "Test poem content"
        assert item["metadata"]["author"] == "test"
        assert "test" in item["tags"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_nonexistent_item(self, locker):
        """Verify getting nonexistent item returns None."""
        item = await locker.get("writing/poems", "nonexistent")
        assert item is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_json_content(self, locker):
        """Verify JSON content is parsed on retrieval."""
        await locker.store(
            category="stories/characters",
            name="hero",
            content='{"name": "Alex", "class": "warrior"}',
            content_type="json"
        )

        item = await locker.get("stories/characters", "hero")

        assert item is not None
        assert isinstance(item["content"], dict)
        assert item["content"]["name"] == "Alex"


# ==============================================================================
# LIST TESTS
# ==============================================================================

class TestLockerList:
    """Test listing items in the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_all_items(self, locker):
        """Verify listing all items."""
        await locker.store(category="writing/poems", name="poem1", content="content1")
        await locker.store(category="writing/poems", name="poem2", content="content2")
        await locker.store(category="art/images", name="image1", content="content3")

        items = await locker.list()

        assert len(items) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_by_category(self, locker):
        """Verify listing by category."""
        await locker.store(category="writing/poems", name="poem1", content="content1")
        await locker.store(category="writing/poems", name="poem2", content="content2")
        await locker.store(category="art/images", name="image1", content="content3")

        items = await locker.list(category="writing/poems")

        assert len(items) == 2
        for item in items:
            assert item["category"] == "writing/poems"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_by_tags(self, locker):
        """Verify listing by tags."""
        await locker.store(category="writing/poems", name="poem1", content="content1", tags=["nature"])
        await locker.store(category="writing/poems", name="poem2", content="content2", tags=["love"])
        await locker.store(category="writing/poems", name="poem3", content="content3", tags=["nature", "sunset"])

        items = await locker.list(tags=["nature"])

        assert len(items) == 2


# ==============================================================================
# SEARCH TESTS
# ==============================================================================

class TestLockerSearch:
    """Test searching items in the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_by_name(self, locker):
        """Verify searching by name."""
        await locker.store(category="writing/poems", name="sunset_haiku", content="content1")
        await locker.store(category="writing/poems", name="morning_verse", content="content2")

        results = await locker.search("sunset")

        assert len(results) == 1
        assert results[0]["name"] == "sunset_haiku"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_by_tag(self, locker):
        """Verify searching by tag."""
        await locker.store(category="writing/poems", name="poem1", content="content1", tags=["nature", "sunset"])
        await locker.store(category="writing/poems", name="poem2", content="content2", tags=["love"])

        results = await locker.search("nature")

        assert len(results) == 1
        assert "nature" in results[0]["tags"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, locker):
        """Verify search respects category filter."""
        await locker.store(category="writing/poems", name="sunset", content="content1")
        await locker.store(category="art/images", name="sunset", content="content2")

        results = await locker.search("sunset", category="writing")

        assert len(results) == 1
        assert results[0]["category"] == "writing/poems"


# ==============================================================================
# DELETE TESTS
# ==============================================================================

class TestLockerDelete:
    """Test deleting items from the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_item(self, locker):
        """Verify deleting an item."""
        await locker.store(category="writing/poems", name="to_delete", content="content")

        result = await locker.delete("writing/poems", "to_delete")
        assert result is True

        item = await locker.get("writing/poems", "to_delete")
        assert item is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_nonexistent_item(self, locker):
        """Verify deleting nonexistent item returns False."""
        result = await locker.delete("writing/poems", "nonexistent")
        assert result is False


# ==============================================================================
# UPDATE TESTS
# ==============================================================================

class TestLockerUpdate:
    """Test updating items in the locker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_content(self, locker):
        """Verify updating content."""
        await locker.store(category="writing/poems", name="poem", content="original content")

        result = await locker.update("writing/poems", "poem", content="updated content")
        assert result["success"] is True

        item = await locker.get("writing/poems", "poem")
        assert item["content"] == "updated content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_metadata(self, locker):
        """Verify updating metadata."""
        await locker.store(
            category="writing/poems",
            name="poem",
            content="content",
            metadata={"author": "original"}
        )

        result = await locker.update(
            "writing/poems",
            "poem",
            metadata={"author": "updated", "version": 2}
        )
        assert result["success"] is True

        item = await locker.get("writing/poems", "poem")
        assert item["metadata"]["author"] == "updated"
        assert item["metadata"]["version"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_nonexistent_item(self, locker):
        """Verify updating nonexistent item fails."""
        result = await locker.update("writing/poems", "nonexistent", content="new")
        assert result["success"] is False


# ==============================================================================
# STATS TESTS
# ==============================================================================

class TestLockerStats:
    """Test locker statistics."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats(self, locker):
        """Verify getting locker stats."""
        await locker.store(category="writing/poems", name="poem1", content="content1")
        await locker.store(category="writing/poems", name="poem2", content="content2")
        await locker.store(category="art/images", name="image1", content="content3")

        stats = locker.get_stats()

        assert stats["total_items"] == 3
        assert stats["categories"]["writing"] == 2
        assert stats["categories"]["art"] == 1
