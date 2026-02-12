"""
Semantic Search with FAISS

Hybrid semantic search combining embeddings and keyword matching.
From docs/09_AI_Integration_Tool_Calling.md Section 6.4
"""

import os
import numpy as np
import faiss
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from core.block import Block
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)


class SemanticSearch:
    """
    FAISS-based semantic search for memory blocks

    Uses sentence-transformers for embeddings and FAISS for
    efficient similarity search across large memory chains.
    """

    def __init__(self, qube_id: str, storage_dir: Path, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic search

        Args:
            qube_id: Qube ID
            storage_dir: Path to Qube's storage directory
            model_name: Sentence transformer model name
        """
        self.qube_id = qube_id
        self.storage_dir = Path(storage_dir)
        self.model_name = model_name

        # Initialize sentence transformer model
        # NOTE: SentenceTransformer uses accelerate's init_empty_weights() which
        # monkey-patches torch.nn.Module.__init__ GLOBALLY (not thread-locally).
        # While this context is active, ANY nn.Module creation in ANY thread gets
        # meta tensors instead of real ones. We acquire _model_init_lock to prevent
        # overlap with Kokoro TTS model construction (see audio/kokoro_tts.py).
        try:
            from sentence_transformers import SentenceTransformer
            from ai._model_init_lock import model_init_lock

            with model_init_lock:
                self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                "semantic_search_initialized",
                qube_id=qube_id,
                model=model_name,
                embedding_dim=self.embedding_dim
            )

        except Exception as e:
            logger.error("semantic_search_init_failed", error=str(e), exc_info=True)
            raise AIError(
                f"Failed to initialize semantic search: {str(e)}",
                context={"model": model_name},
                cause=e
            )

        # Initialize FAISS index
        self.index: Optional[faiss.IndexFlatL2] = None
        self.block_ids: List[int] = []  # Maps FAISS index to block numbers

        # Index file path
        self.index_file = self.storage_dir / "semantic_index.faiss"
        self.mapping_file = self.storage_dir / "semantic_mapping.npy"

        # Load existing index if available
        self._load_index()

    def _load_index(self) -> None:
        """Load FAISS index from disk if it exists"""
        if self.index_file.exists() and self.mapping_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                self.block_ids = np.load(str(self.mapping_file)).tolist()

                logger.info(
                    "semantic_index_loaded",
                    qube_id=self.qube_id,
                    vectors=len(self.block_ids)
                )

            except Exception as e:
                logger.error("semantic_index_load_failed", error=str(e))
                self.index = None
                self.block_ids = []

    def _save_index(self) -> None:
        """Save FAISS index to disk"""
        if self.index is not None:
            try:
                faiss.write_index(self.index, str(self.index_file))
                np.save(str(self.mapping_file), np.array(self.block_ids))

                logger.debug("semantic_index_saved", vectors=len(self.block_ids))

            except Exception as e:
                logger.error("semantic_index_save_failed", error=str(e))

    def add_block(self, block: Block) -> None:
        """
        Add block to semantic index

        Args:
            block: Block to index
        """
        try:
            # Extract text from block for embedding
            text = self._extract_text_from_block(block)

            if not text:
                logger.debug("block_has_no_text", block_number=block.block_number)
                return

            # Generate embedding
            embedding = self.model.encode([text], show_progress_bar=False)[0]

            # Initialize index if needed
            if self.index is None:
                self.index = faiss.IndexFlatL2(self.embedding_dim)

            # Add to index
            self.index.add(np.array([embedding], dtype=np.float32))
            self.block_ids.append(block.block_number)

            # Save index
            self._save_index()

            logger.debug(
                "block_added_to_semantic_index",
                block_number=block.block_number,
                text_length=len(text)
            )

        except Exception as e:
            logger.error(
                "semantic_index_add_failed",
                block_number=block.block_number,
                error=str(e)
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
        block_type_filter: Optional[List[str]] = None
    ) -> List[Tuple[int, float]]:
        """
        Search for similar blocks using semantic similarity

        Args:
            query: Search query text
            top_k: Number of results to return
            block_type_filter: Optional list of block types to filter by

        Returns:
            List of (block_number, similarity_score) tuples
        """
        if self.index is None or len(self.block_ids) == 0:
            logger.warning("semantic_search_empty_index")
            return []

        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], show_progress_bar=False)[0]

            # Search FAISS index
            distances, indices = self.index.search(
                np.array([query_embedding], dtype=np.float32),
                min(top_k, len(self.block_ids))
            )

            # Map indices to block numbers
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx >= 0 and idx < len(self.block_ids):
                    block_number = self.block_ids[idx]
                    similarity = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    results.append((block_number, similarity))

            logger.info(
                "semantic_search_complete",
                query_length=len(query),
                results_found=len(results)
            )

            return results

        except Exception as e:
            logger.error("semantic_search_failed", error=str(e), exc_info=True)
            return []

    def hybrid_search(
        self,
        query: str,
        blocks: List[Block],
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Tuple[Block, float]]:
        """
        Hybrid search combining semantic similarity and keyword matching

        Args:
            query: Search query
            blocks: List of blocks to search (from storage)
            top_k: Number of results to return
            semantic_weight: Weight for semantic similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)

        Returns:
            List of (block, combined_score) tuples
        """
        # Get semantic search results
        semantic_results = self.search(query, top_k=top_k * 2)  # Get more for hybrid ranking

        # Create block lookup
        block_lookup = {b.block_number: b for b in blocks}

        # Score each block
        scored_blocks = []

        for block_number, semantic_score in semantic_results:
            if block_number not in block_lookup:
                continue

            block = block_lookup[block_number]

            # Calculate keyword score
            keyword_score = self._keyword_score(query, block)

            # Combine scores
            combined_score = (semantic_weight * semantic_score) + (keyword_weight * keyword_score)

            scored_blocks.append((block, combined_score))

        # Sort by combined score
        scored_blocks.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "hybrid_search_complete",
            query=query,
            results=len(scored_blocks[:top_k])
        )

        return scored_blocks[:top_k]

    def _extract_text_from_block(self, block: Block) -> str:
        """Extract searchable text from block"""
        text_parts = []

        # Block type as context
        block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
        text_parts.append(block_type_str)

        # Extract content based on block type
        if block_type_str == "MESSAGE":
            text_parts.append(block.content.get("message_body", block.content.get("content", "")))

        elif block_type_str == "THOUGHT":
            text_parts.append(block.content.get("thought", ""))

        elif block_type_str == "OBSERVATION":
            observation = block.content.get("observation", "")
            if isinstance(observation, str):
                text_parts.append(observation)
            else:
                text_parts.append(str(observation))

        elif block_type_str == "SUMMARY":
            text_parts.append(block.content.get("summary_text", ""))

        else:
            # Generic: convert content to string
            text_parts.append(str(block.content))

        return " ".join(filter(None, text_parts))

    def _keyword_score(self, query: str, block: Block) -> float:
        """Calculate keyword matching score"""
        query_lower = query.lower()
        block_text = self._extract_text_from_block(block).lower()

        if not block_text:
            return 0.0

        # Count query words found in block
        query_words = set(query_lower.split())
        block_words = set(block_text.split())

        matches = query_words.intersection(block_words)

        if not query_words:
            return 0.0

        return len(matches) / len(query_words)

    def rebuild_index(self, blocks: List[Block]) -> None:
        """
        Rebuild entire semantic index from blocks

        Args:
            blocks: All blocks to index
        """
        logger.info("rebuilding_semantic_index", total_blocks=len(blocks))

        # Reset index
        self.index = None
        self.block_ids = []

        # Add all blocks
        for block in blocks:
            self.add_block(block)

        logger.info("semantic_index_rebuilt", vectors=len(self.block_ids))
