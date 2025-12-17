"""
Intelligent Memory Search - 5-Layer Hybrid System

Multi-layer memory recall combining:
- Layer 1: Semantic Search (FAISS embeddings)
- Layer 2: Metadata Filtering (fast pre-filter)
- Layer 3: Full-Text Search (keyword matching)
- Layer 4: Temporal Relevance (recency bias)
- Layer 5: Relationship-Aware Search (social context)

From docs/05_Data_Structures.md Section 2.2 (lines 358-682)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from ai.embeddings import merge_results, SearchResult
from utils.logging import get_logger

logger = get_logger(__name__)


def parse_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse query and extract search parameters

    Args:
        query: User query string
        context: Optional context dict with hints

    Returns:
        Parsed query dict with:
            - semantic_query: Query for semantic search
            - keyword_query: Query for keyword search
            - block_types: List of block types to filter (None = all)
            - date_range: Tuple of (start_timestamp, end_timestamp) or None
            - participants: List of participant IDs to filter (None = all)
            - query_type: "recent_events", "historical", "expertise_required", or None
    """
    if context is None:
        context = {}

    parsed = {
        "semantic_query": query,
        "keyword_query": query,
        "block_types": context.get("block_types"),
        "date_range": context.get("date_range"),
        "participants": context.get("participants"),
        "query_type": None
    }

    # Detect query type from query text
    query_lower = query.lower()

    # Check for historical queries first (more specific)
    if any(word in query_lower for word in ["history", "past", "ago", "remember when", "last month", "last year"]):
        parsed["query_type"] = "historical"

    # Then check for recent queries
    elif any(word in query_lower for word in ["recent", "recently", "latest", "last week", "last day"]):
        parsed["query_type"] = "recent_events"

    # Then check for expertise queries
    elif any(word in query_lower for word in ["expert", "specialist", "best at", "good at"]):
        parsed["query_type"] = "expertise_required"

    # Extract time references
    if "last week" in query_lower or "past week" in query_lower:
        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = end_time - (7 * 86400)  # 7 days
        parsed["date_range"] = (start_time, end_time)

    elif "last month" in query_lower or "past month" in query_lower:
        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = end_time - (30 * 86400)  # 30 days
        parsed["date_range"] = (start_time, end_time)

    logger.debug("query_parsed", query_type=parsed["query_type"], has_date_range=parsed["date_range"] is not None)

    return parsed


async def intelligent_memory_search(
    qube,
    query: str,
    context: Optional[Dict[str, Any]] = None,
    top_k: int = 10
) -> List[SearchResult]:
    """
    Multi-layer memory recall with hybrid ranking

    Combines RAG, vector search, and semantic recall to find the most
    relevant blocks for injecting into the system prompt.

    From docs Section 2.2 (lines 358-406)

    Args:
        qube: Qube instance with memory chain and semantic search
        query: Search query
        context: Optional context dict:
            - block_types: Filter by block types
            - date_range: Filter by date range
            - participants: Filter by participants
            - decay_rate: Custom temporal decay rate
        top_k: Number of results to return (default: 10)

    Returns:
        List of SearchResult objects, sorted by relevance (highest first)

    Process:
        1. Parse query and context
        2. Layer 2: Metadata filtering (fast elimination)
        3. Layer 1: Semantic search on candidates (FAISS)
        4. Layer 3: Full-text search on candidates (parallel)
        5. Merge and re-rank results
        6. Layer 4: Apply temporal decay
        7. Layer 5: Apply relationship boost
        8. Re-rank and return top-K
    """
    if context is None:
        context = {}

    logger.info("intelligent_memory_search_started", query=query[:50], top_k=top_k)

    # Step 1: Parse query and context
    parsed = parse_query(query, context)

    # Step 2: Metadata filtering (Layer 2 - fast pre-filter)
    candidate_blocks = await filter_by_metadata(
        qube=qube,
        block_types=parsed["block_types"],
        date_range=parsed["date_range"],
        participants=parsed["participants"]
    )

    if not candidate_blocks:
        logger.warning("no_candidates_after_metadata_filter", query=query[:50])
        return []

    logger.debug(
        "metadata_filter_complete",
        candidates=len(candidate_blocks),
        original_chain_length=qube.memory_chain.get_chain_length()
    )

    # Step 3: Semantic search (Layer 1)
    semantic_results = await semantic_search(
        qube=qube,
        query=parsed["semantic_query"],
        candidates=candidate_blocks,
        top_k=top_k * 3  # Get 3x candidates for re-ranking
    )

    # Step 4: Full-text search (Layer 3 - parallel)
    keyword_results = await fulltext_search(
        qube=qube,
        query=parsed["keyword_query"],
        candidates=candidate_blocks,
        top_k=top_k * 3
    )

    # Step 5: Merge and re-rank
    query_context = {
        "qube": qube,
        "query_type": parsed["query_type"],
        "decay_rate": context.get("decay_rate", 0.1)
    }

    merged = merge_results(semantic_results, keyword_results, query_context)

    # Steps 6-7: Temporal decay and relationship boost
    # (Already applied in calculate_final_score during merge_results)

    # Step 8: Return top-K
    top_results = merged[:top_k]

    logger.info(
        "intelligent_memory_search_complete",
        query=query[:50],
        results=len(top_results),
        top_score=top_results[0].score if top_results else 0
    )

    return top_results


async def filter_by_metadata(
    qube,
    block_types: Optional[List[str]] = None,
    date_range: Optional[Tuple[int, int]] = None,
    participants: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Layer 2: Fast metadata filtering

    Quickly eliminate blocks that don't match basic criteria.

    Args:
        qube: Qube instance
        block_types: Filter by block types (None = all types)
        date_range: Tuple of (start_timestamp, end_timestamp) or None
        participants: List of participant IDs (None = all)

    Returns:
        List of candidate blocks after filtering
    """
    # Use memory chain's filter_blocks (reads from JSON files)
    # Already filters by block_types, date_range, and participants
    candidates = qube.memory_chain.filter_blocks(
        block_types=block_types,
        start_time=date_range[0] if date_range else None,
        end_time=date_range[1] if date_range else None,
        participants=participants
    )

    return candidates


async def semantic_search(
    qube,
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 30
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Layer 1: Semantic search using FAISS

    Args:
        qube: Qube instance with semantic_search
        query: Search query
        candidates: Pre-filtered candidate blocks
        top_k: Number of results

    Returns:
        List of (block, score) tuples, sorted by semantic similarity
    """
    try:
        # Use Qube's semantic search if available
        if hasattr(qube, 'semantic_search') and qube.semantic_search:
            results = qube.semantic_search.search(
                query=query,
                top_k=top_k,
                candidate_blocks=candidates
            )
            return [(r["block"], r["score"]) for r in results]

    except Exception as e:
        logger.error("semantic_search_failed", error=str(e))

    # Fallback: return candidates with default score
    return [(block, 0.5) for block in candidates[:top_k]]


async def fulltext_search(
    qube,
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 30
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Layer 3: Full-text keyword search

    Args:
        qube: Qube instance
        query: Search query
        candidates: Pre-filtered candidate blocks
        top_k: Number of results

    Returns:
        List of (block, score) tuples, sorted by keyword match score
    """
    query_words = set(query.lower().split())

    scored_blocks = []

    for block in candidates:
        # Extract text from block content
        text = extract_text_from_block(block).lower()

        # Simple keyword matching score
        words = set(text.split())
        matches = query_words.intersection(words)

        if matches:
            # Score based on percentage of query words matched
            score = len(matches) / len(query_words)
            scored_blocks.append((block, score))

    # Sort by score descending
    scored_blocks.sort(key=lambda x: x[1], reverse=True)

    return scored_blocks[:top_k]


def extract_text_from_block(block: Dict[str, Any]) -> str:
    """
    Extract searchable text from block content

    Args:
        block: Block dict

    Returns:
        Concatenated text from block
    """
    parts = []

    content = block.get("content", {})

    # Add all string values from content
    for key, value in content.items():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend([str(v) for v in value if isinstance(v, str)])

    # Add block type (helps with queries like "my decisions")
    block_type = block.get("block_type", "")
    if block_type:
        parts.append(block_type.lower())

    return " ".join(parts)
