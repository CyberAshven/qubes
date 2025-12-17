"""
Shared Memory Cache

Caches shared memories from other Qubes for fast access.
From docs/07_Shared_Memory_Architecture.md Section 4.4
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class SharedMemoryCache:
    """Cache for shared memories from other Qubes"""

    def __init__(self, cache_dir: Path, max_size_mb: int = 500):
        """
        Initialize shared memory cache

        Args:
            cache_dir: Directory to store cached shared memories
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cached_memories: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, datetime] = {}

        self.load_cache()

        logger.info(
            "shared_memory_cache_initialized",
            cache_dir=str(cache_dir),
            max_size_mb=max_size_mb,
            cached_count=len(self.cached_memories)
        )

    def add_memory(
        self,
        source_qube_id: str,
        block_number: int,
        block_data: Dict[str, Any],
        permission_id: str
    ):
        """
        Add shared memory to cache

        Args:
            source_qube_id: Qube ID who shared the memory
            block_number: Block number in source Qube's chain
            block_data: Decrypted block data
            permission_id: Permission ID granting access
        """
        cache_key = self._get_cache_key(source_qube_id, block_number)

        cached_entry = {
            "source_qube_id": source_qube_id,
            "block_number": block_number,
            "block_data": block_data,
            "permission_id": permission_id,
            "cached_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat(),
            "access_count": 0
        }

        self.cached_memories[cache_key] = cached_entry
        self.access_times[cache_key] = datetime.now()

        self.save_cache_entry(cache_key, cached_entry)
        self._enforce_size_limit()

        logger.info(
            "shared_memory_cached",
            source_qube=source_qube_id,
            block=block_number,
            cache_key=cache_key
        )

    def get_memory(
        self,
        source_qube_id: str,
        block_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get shared memory from cache

        Args:
            source_qube_id: Source Qube ID
            block_number: Block number

        Returns:
            Block data if found, None otherwise
        """
        cache_key = self._get_cache_key(source_qube_id, block_number)
        entry = self.cached_memories.get(cache_key)

        if entry:
            # Update access time and count
            entry["accessed_at"] = datetime.now().isoformat()
            entry["access_count"] += 1
            self.access_times[cache_key] = datetime.now()

            self.save_cache_entry(cache_key, entry)

            logger.debug(
                "shared_memory_cache_hit",
                source_qube=source_qube_id,
                block=block_number,
                access_count=entry["access_count"]
            )

            return entry["block_data"]

        logger.debug(
            "shared_memory_cache_miss",
            source_qube=source_qube_id,
            block=block_number
        )

        return None

    def get_memories_from_qube(self, source_qube_id: str) -> List[Dict[str, Any]]:
        """
        Get all cached memories from a specific Qube

        Args:
            source_qube_id: Source Qube ID

        Returns:
            List of cached memory entries
        """
        return [
            entry for entry in self.cached_memories.values()
            if entry["source_qube_id"] == source_qube_id
        ]

    def search_cached_memories(
        self,
        query: str,
        source_qube_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search cached memories by content

        Args:
            query: Search query
            source_qube_id: Optional filter by source Qube

        Returns:
            List of matching cached memories
        """
        query_lower = query.lower()
        results = []

        for entry in self.cached_memories.values():
            # Filter by source if specified
            if source_qube_id and entry["source_qube_id"] != source_qube_id:
                continue

            # Search in block content
            block_data = entry["block_data"]
            content_str = json.dumps(block_data).lower()

            if query_lower in content_str:
                results.append(entry)

        logger.debug(
            "cached_memories_searched",
            query=query[:50],
            source_qube=source_qube_id,
            results=len(results)
        )

        return results

    def remove_memory(self, source_qube_id: str, block_number: int):
        """
        Remove shared memory from cache

        Args:
            source_qube_id: Source Qube ID
            block_number: Block number
        """
        cache_key = self._get_cache_key(source_qube_id, block_number)

        if cache_key in self.cached_memories:
            del self.cached_memories[cache_key]
            del self.access_times[cache_key]

            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()

            logger.info(
                "shared_memory_removed_from_cache",
                source_qube=source_qube_id,
                block=block_number
            )

    def remove_memories_from_qube(self, source_qube_id: str):
        """
        Remove all cached memories from a specific Qube

        Args:
            source_qube_id: Source Qube ID
        """
        to_remove = [
            (entry["source_qube_id"], entry["block_number"])
            for entry in self.cached_memories.values()
            if entry["source_qube_id"] == source_qube_id
        ]

        for source_id, block_num in to_remove:
            self.remove_memory(source_id, block_num)

        logger.info(
            "qube_memories_removed_from_cache",
            source_qube=source_qube_id,
            removed=len(to_remove)
        )

    def clear_cache(self):
        """Clear entire cache"""
        count = len(self.cached_memories)

        self.cached_memories.clear()
        self.access_times.clear()

        # Remove all cache files
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

        logger.info("shared_memory_cache_cleared", removed=count)

    def _get_cache_key(self, source_qube_id: str, block_number: int) -> str:
        """Generate cache key"""
        return f"{source_qube_id}_{block_number}"

    def _enforce_size_limit(self):
        """Enforce maximum cache size using LRU eviction"""
        try:
            # Calculate current cache size
            total_size = sum(
                (self.cache_dir / f"{key}.json").stat().st_size
                for key in self.cached_memories.keys()
                if (self.cache_dir / f"{key}.json").exists()
            )

            if total_size <= self.max_size_bytes:
                return

            # Sort by access time (LRU)
            sorted_keys = sorted(
                self.access_times.keys(),
                key=lambda k: self.access_times[k]
            )

            # Remove oldest entries until under limit
            for cache_key in sorted_keys:
                if total_size <= self.max_size_bytes:
                    break

                entry = self.cached_memories[cache_key]
                self.remove_memory(entry["source_qube_id"], entry["block_number"])

                # Recalculate size
                total_size = sum(
                    (self.cache_dir / f"{key}.json").stat().st_size
                    for key in self.cached_memories.keys()
                    if (self.cache_dir / f"{key}.json").exists()
                )

            logger.info(
                "cache_size_limit_enforced",
                total_size_mb=round(total_size / (1024 * 1024), 2),
                max_size_mb=round(self.max_size_bytes / (1024 * 1024), 2)
            )

        except Exception as e:
            logger.error("cache_size_enforcement_failed", error=str(e), exc_info=True)

    def cleanup_old_entries(self, days: int = 30):
        """
        Remove old cache entries not accessed recently

        Args:
            days: Remove entries not accessed in this many days
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        to_remove = []

        for cache_key, access_time in self.access_times.items():
            if access_time < cutoff_date:
                entry = self.cached_memories[cache_key]
                to_remove.append((entry["source_qube_id"], entry["block_number"]))

        for source_id, block_num in to_remove:
            self.remove_memory(source_id, block_num)

        if to_remove:
            logger.info("old_cache_entries_removed", removed=len(to_remove), days=days)

    def save_cache_entry(self, cache_key: str, entry: Dict[str, Any]):
        """Save cache entry to disk"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"

            with open(cache_file, "w") as f:
                json.dump(entry, f, indent=2)

            logger.debug(
                "cache_entry_saved",
                cache_key=cache_key,
                file=str(cache_file)
            )

        except Exception as e:
            logger.error(
                "cache_entry_save_failed",
                cache_key=cache_key,
                error=str(e),
                exc_info=True
            )
            raise QubesError(f"Failed to save cache entry: {e}", cause=e)

    def load_cache(self):
        """Load cache from disk"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        entry = json.load(f)

                    cache_key = cache_file.stem
                    self.cached_memories[cache_key] = entry

                    # Restore access time
                    accessed_at = entry.get("accessed_at")
                    if accessed_at:
                        self.access_times[cache_key] = datetime.fromisoformat(accessed_at)
                    else:
                        self.access_times[cache_key] = datetime.now()

                except Exception as e:
                    logger.error(
                        "cache_entry_load_failed",
                        file=str(cache_file),
                        error=str(e)
                    )

            logger.info(
                "shared_memory_cache_loaded",
                entries=len(self.cached_memories)
            )

        except Exception as e:
            logger.error("cache_load_failed", error=str(e), exc_info=True)
            self.cached_memories = {}
            self.access_times = {}

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_size = sum(
                (self.cache_dir / f"{key}.json").stat().st_size
                for key in self.cached_memories.keys()
                if (self.cache_dir / f"{key}.json").exists()
            )
        except:
            total_size = 0

        total_accesses = sum(
            entry.get("access_count", 0)
            for entry in self.cached_memories.values()
        )

        sources = {}
        for entry in self.cached_memories.values():
            source_id = entry["source_qube_id"]
            sources[source_id] = sources.get(source_id, 0) + 1

        return {
            "total_cached": len(self.cached_memories),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "utilization_percent": round((total_size / self.max_size_bytes) * 100, 1) if self.max_size_bytes > 0 else 0,
            "total_accesses": total_accesses,
            "unique_sources": len(sources),
            "memories_by_source": sources
        }
