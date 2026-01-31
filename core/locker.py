"""
Qube Locker - Storage for Creative Works and Documents

The Qube Locker stores actual documents and creative artifacts:
- Writing: poems, stories, essays
- Art: images, concepts, compositions
- Music: melodies, lyrics, compositions
- Stories: narratives, characters, worlds
- Personal: reflections, journal entries
- Exports: knowledge documents

Storage is file-based within the qube's data directory,
with metadata indexed for search and retrieval.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LockerItem:
    """Metadata for an item stored in the Qube Locker."""
    id: str                      # Unique identifier (hash of content)
    name: str                    # Human-readable name
    category: str                # e.g., "writing/poems"
    content_type: str            # "text", "url", "json", "binary"
    created_at: str              # ISO timestamp
    updated_at: str              # ISO timestamp
    metadata: Dict[str, Any]     # Additional metadata (prompt, style, etc.)
    file_path: str               # Relative path to content file
    size_bytes: int              # Content size
    tags: List[str]              # Searchable tags


class QubeLocker:
    """
    Manages storage and retrieval of creative works.

    Usage:
        locker = QubeLocker(qube_data_dir)

        # Store a poem
        await locker.store(
            category="writing/poems",
            name="sunset_haiku",
            content="Crimson sun descends\\nSilhouettes dance on the waves\\nNight embraces day",
            metadata={"form": "haiku", "theme": "nature"}
        )

        # Retrieve
        item = await locker.get("writing/poems", "sunset_haiku")

        # List all poems
        poems = await locker.list("writing/poems")

        # Search across locker
        results = await locker.search("sunset")
    """

    # Valid top-level categories
    CATEGORIES = {
        "writing": ["poems", "stories", "essays"],
        "art": ["images", "concepts", "compositions"],
        "music": ["melodies", "lyrics", "compositions"],
        "stories": ["narratives", "characters", "worlds"],
        "personal": ["reflections", "journal"],
        "exports": ["knowledge"]
    }

    def __init__(self, qube_data_dir: str):
        """
        Initialize the Qube Locker.

        Args:
            qube_data_dir: Path to qube's data directory
        """
        self.base_dir = Path(qube_data_dir) / "locker"
        self.index_file = self.base_dir / "index.json"
        self._index: Dict[str, LockerItem] = {}
        self._ensure_directories()
        self._load_index()

    def _ensure_directories(self) -> None:
        """Create the locker directory structure."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

        for category, subcategories in self.CATEGORIES.items():
            for sub in subcategories:
                (self.base_dir / category / sub).mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Load the index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._index = {
                        k: LockerItem(**v) for k, v in data.items()
                    }
            except Exception as e:
                logger.error("locker_index_load_failed", error=str(e))
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """Save the index to disk."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                data = {k: asdict(v) for k, v in self._index.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("locker_index_save_failed", error=str(e))

    def _generate_id(self, content: str) -> str:
        """Generate unique ID from content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _validate_category(self, category: str) -> bool:
        """Validate category path."""
        parts = category.split('/')
        if len(parts) != 2:
            return False
        top, sub = parts
        return top in self.CATEGORIES and sub in self.CATEGORIES[top]

    async def store(
        self,
        category: str,
        name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        content_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Store an item in the locker.

        Args:
            category: Category path (e.g., "writing/poems")
            name: Human-readable name
            content: The actual content to store
            metadata: Additional metadata
            tags: Searchable tags
            content_type: "text", "url", "json", or "binary"

        Returns:
            Dict with id, path, and success status
        """
        if not self._validate_category(category):
            return {
                "success": False,
                "error": f"Invalid category: {category}. Valid: {self._get_valid_categories()}"
            }

        # Generate ID and paths
        item_id = self._generate_id(f"{category}/{name}/{content}")
        safe_name = self._sanitize_filename(name)
        file_ext = self._get_extension(content_type)
        relative_path = f"{category}/{safe_name}{file_ext}"
        full_path = self.base_dir / relative_path

        # Write content
        try:
            if content_type == "binary":
                with open(full_path, 'wb') as f:
                    f.write(content.encode() if isinstance(content, str) else content)
            else:
                with open(full_path, 'w', encoding='utf-8') as f:
                    if content_type == "json":
                        json.dump(content if isinstance(content, dict) else json.loads(content), f, indent=2)
                    else:
                        f.write(content)
        except Exception as e:
            logger.error("locker_write_failed", error=str(e), path=str(full_path))
            return {"success": False, "error": str(e)}

        # Create index entry
        now = datetime.utcnow().isoformat()
        item = LockerItem(
            id=item_id,
            name=name,
            category=category,
            content_type=content_type,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            file_path=relative_path,
            size_bytes=len(content.encode() if isinstance(content, str) else content),
            tags=tags or []
        )

        # Add to index
        index_key = f"{category}/{name}"
        self._index[index_key] = item
        self._save_index()

        logger.info("locker_item_stored", key=index_key, category=category)

        return {
            "success": True,
            "id": item_id,
            "path": relative_path,
            "category": category,
            "name": name
        }

    async def get(
        self,
        category: str,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the locker.

        Args:
            category: Category path
            name: Item name

        Returns:
            Dict with item metadata and content, or None if not found
        """
        index_key = f"{category}/{name}"
        item = self._index.get(index_key)

        if not item:
            return None

        # Read content
        full_path = self.base_dir / item.file_path
        try:
            if item.content_type == "binary":
                with open(full_path, 'rb') as f:
                    content = f.read()
            else:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if item.content_type == "json":
                        content = json.loads(content)
        except Exception as e:
            logger.error("locker_read_failed", error=str(e), path=str(full_path))
            return None

        return {
            **asdict(item),
            "content": content
        }

    async def list(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List items in the locker.

        Args:
            category: Filter by category (optional)
            tags: Filter by tags (optional, matches any)
            limit: Maximum items to return

        Returns:
            List of item metadata (without content)
        """
        results = []

        for key, item in self._index.items():
            # Category filter
            if category and not item.category.startswith(category):
                continue

            # Tag filter
            if tags and not any(t in item.tags for t in tags):
                continue

            results.append(asdict(item))

            if len(results) >= limit:
                break

        # Sort by updated_at descending
        results.sort(key=lambda x: x["updated_at"], reverse=True)

        return results

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search the locker for items matching query.

        Searches: name, tags, metadata values

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of matching items with relevance scores
        """
        query_lower = query.lower()
        results = []

        for key, item in self._index.items():
            # Category filter
            if category and not item.category.startswith(category):
                continue

            score = 0

            # Name match
            if query_lower in item.name.lower():
                score += 10

            # Tag match
            for tag in item.tags:
                if query_lower in tag.lower():
                    score += 5

            # Metadata match
            for k, v in item.metadata.items():
                if isinstance(v, str) and query_lower in v.lower():
                    score += 3

            if score > 0:
                results.append({
                    **asdict(item),
                    "relevance_score": score
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return results[:limit]

    async def delete(self, category: str, name: str) -> bool:
        """Delete an item from the locker."""
        index_key = f"{category}/{name}"
        item = self._index.get(index_key)

        if not item:
            return False

        # Delete file
        full_path = self.base_dir / item.file_path
        try:
            if full_path.exists():
                full_path.unlink()
        except Exception as e:
            logger.error("locker_delete_failed", error=str(e), path=str(full_path))

        # Remove from index
        del self._index[index_key]
        self._save_index()

        logger.info("locker_item_deleted", key=index_key)

        return True

    async def update(
        self,
        category: str,
        name: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing item."""
        index_key = f"{category}/{name}"
        item = self._index.get(index_key)

        if not item:
            return {"success": False, "error": "Item not found"}

        # Update content if provided
        if content is not None:
            full_path = self.base_dir / item.file_path
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                item.size_bytes = len(content.encode())
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Update metadata
        if metadata is not None:
            item.metadata.update(metadata)

        # Update tags
        if tags is not None:
            item.tags = tags

        # Update timestamp
        item.updated_at = datetime.utcnow().isoformat()

        # Save index
        self._index[index_key] = item
        self._save_index()

        logger.info("locker_item_updated", key=index_key)

        return {"success": True, "item": asdict(item)}

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize name for use as filename."""
        # Replace unsafe characters
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return safe[:100]  # Limit length

    def _get_extension(self, content_type: str) -> str:
        """Get file extension for content type."""
        extensions = {
            "text": ".txt",
            "url": ".url",
            "json": ".json",
            "binary": ".bin"
        }
        return extensions.get(content_type, ".txt")

    def _get_valid_categories(self) -> List[str]:
        """Get list of valid category paths."""
        return [
            f"{cat}/{sub}"
            for cat, subs in self.CATEGORIES.items()
            for sub in subs
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the locker."""
        category_counts = {}
        total_size = 0

        for item in self._index.values():
            cat = item.category.split('/')[0]
            category_counts[cat] = category_counts.get(cat, 0) + 1
            total_size += item.size_bytes

        return {
            "total_items": len(self._index),
            "total_size_bytes": total_size,
            "categories": category_counts
        }
