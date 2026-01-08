"""
Embedding and Scoring Functions for Intelligent Memory Search

From docs/05_Data_Structures.md Section 2.2 (lines 411-682)
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


def temporal_decay(timestamp: int, decay_rate: float = 0.1) -> float:
    """
    Apply temporal decay to relevance score

    More recent blocks are weighted higher. Decay rate determines how
    quickly older blocks lose relevance.

    From docs Section 2.2 (lines 411-427)

    Args:
        timestamp: Block creation timestamp (Unix epoch seconds)
        decay_rate: How quickly relevance decays (0.1 = slow, 1.0 = fast)
                   0.1 = memories decay slowly (good for long-term recall)
                   1.0 = memories decay quickly (focus on recent events)

    Returns:
        Multiplier between 0 and 1 (1.0 = very recent, approaches 0 for old)

    Examples:
        >>> temporal_decay(int(time.time()), 0.1)  # Now
        1.0
        >>> temporal_decay(int(time.time()) - 86400, 0.1)  # 1 day ago
        ~0.91
        >>> temporal_decay(int(time.time()) - 86400 * 30, 0.1)  # 30 days ago
        ~0.25
    """
    current_time = int(datetime.now(timezone.utc).timestamp())
    age_seconds = current_time - timestamp

    # Convert to days for more intuitive decay rates
    age_days = age_seconds / 86400.0

    # Decay formula: 1 / (1 + age_days * decay_rate)
    decay = 1.0 / (1.0 + (age_days * decay_rate))

    return max(0.0, min(1.0, decay))  # Clamp to [0, 1]


def relationship_boost(relationship: Optional[Dict[str, Any]]) -> float:
    """
    Boost blocks based on relationship strength with participants

    Blocks involving trusted friends or important contacts are weighted higher.

    From docs Section 2.2 (lines 430-478)

    Args:
        relationship: Relationship dict from relationships schema (Section 2.4)
                     Can be None if no relationship exists

    Returns:
        Multiplier >= 1.0 (1.0 = no boost, higher = stronger boost)

    Boost Levels:
        - No relationship: 1.0 (no boost)
        - Low trust (<30): 0.8 (penalty)
        - Enemy: 0.7 (penalty)
        - Moderate trust (60-79): 1.2
        - High trust (80+): 1.3
        - Close friend: 1.25
        - Dating/partner/married: 1.4
        - Best friend: 1.5 (highest boost)
        - Collaborative history (10+ tasks): +0.1
    """
    if not relationship:
        return 1.0  # No boost for unknown entities

    boost = 1.0

    # Enemy - significant penalty (check first to override trust score)
    if relationship.get("relationship_status") == "enemy":
        boost = 0.7

    # Best friend gets highest boost
    elif relationship.get("is_best_friend", False):
        boost = 1.5

    # Dating/partnership gets high boost
    elif relationship.get("relationship_status") in ["dating", "partner", "married"]:
        boost = 1.4

    # High trust relationships
    elif relationship.get("overall_trust_score", 0) >= 80:
        boost = 1.3

    # Close friend
    elif relationship.get("relationship_status") == "close_friend":
        boost = 1.25

    # Moderate trust relationships
    elif relationship.get("overall_trust_score", 0) >= 60:
        boost = 1.2

    # Low trust - reduce importance
    elif relationship.get("overall_trust_score", 0) < 30:
        boost = 0.8

    # Collaborative history boost (but not for enemies)
    if relationship.get("successful_joint_tasks", 0) > 10 and relationship.get("relationship_status") != "enemy":
        boost += 0.1

    return boost


def calculate_final_score(
    block: Dict[str, Any],
    semantic_score: float,
    keyword_score: float,
    query_context: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate final relevance score using weighted combination of factors

    Combines semantic similarity, keyword matching, temporal relevance,
    relationship importance, and contextual factors.

    From docs Section 2.2 (lines 481-559)

    Args:
        block: Memory block dict
        semantic_score: Semantic similarity score (0-1) from FAISS
        keyword_score: Keyword match score (0-1) from full-text search
        query_context: Optional context about the query:
            - query_type: "recent_events", "historical", "expertise_required"
            - qube: Qube instance for relationship lookups
            - decay_rate: Custom temporal decay rate (default: 0.1)

    Returns:
        Final relevance score (0-100+, higher = more relevant)

    Scoring Weights:
        - Semantic similarity: 40%
        - Keyword matching: 30%
        - Temporal relevance: 15%
        - Relationship strength: 10%
        - Block type importance: 5%
    """
    if query_context is None:
        query_context = {}

    # Base weights for each component (can be overridden via query_context)
    weights = {
        "semantic": query_context.get("semantic_weight", 0.4),      # Semantic similarity
        "keyword": query_context.get("keyword_weight", 0.3),        # Exact keyword matches
        "temporal": query_context.get("temporal_weight", 0.15),     # Recent blocks preference
        "relationship": query_context.get("relationship_weight", 0.1),  # Relationship strength
        "block_type": 0.05    # Some block types more important (not configurable)
    }

    # Base score from semantic + keyword
    base_score = (semantic_score * weights["semantic"]) + (keyword_score * weights["keyword"])

    # Layer 4: Temporal decay
    decay_rate = query_context.get("decay_rate", 0.1)
    # Handle different timestamp field names (genesis blocks use birth_timestamp)
    timestamp = block.get("timestamp") or block.get("birth_timestamp") or block.get("created_at")
    if timestamp:
        temporal_multiplier = temporal_decay(timestamp, decay_rate=decay_rate)
        base_score *= (1 + (temporal_multiplier - 1) * weights["temporal"])

    # Layer 5: Relationship boost
    if "content" in block and "participants" in block.get("content", {}):
        qube = query_context.get("qube")
        if qube:
            participants = block["content"]["participants"]
            max_boost = 1.0

            # Find highest relationship boost among participants
            for participant_id in participants:
                # Note: This will work once Phase 5 (relationships) is implemented
                # For now, we'll use a placeholder
                try:
                    rel = qube.get_relationship(participant_id)
                    boost = relationship_boost(rel)
                    max_boost = max(max_boost, boost)
                except AttributeError:
                    # Qube.get_relationship() doesn't exist yet (Phase 5)
                    pass

            base_score *= (1 + (max_boost - 1) * weights["relationship"])

    # Block type importance weights
    block_type_weights = {
        "COLLABORATIVE_MEMORY": 1.2,  # Collaborative work is important
        "DECISION": 1.15,             # Decisions are significant
        "SUMMARY": 1.3,               # Summaries are highly condensed info
        "ACTION": 1.05,               # Actions show what was done
        "OBSERVATION": 1.05,          # Results are useful
        "MESSAGE": 1.0,               # Messages are baseline
        "THOUGHT": 0.9,               # Thoughts less critical for recall
        "MEMORY_ANCHOR": 0.5,         # Anchors not content-rich
        "GENESIS": 0.8,               # Genesis is metadata, not content
    }

    block_type = block.get("block_type", "MESSAGE")
    block_type_weight = block_type_weights.get(block_type, 1.0)
    base_score *= block_type_weight

    # Context-aware adjustments
    query_type = query_context.get("query_type")

    if query_type == "recent_events":
        # Boost recent blocks more for "what happened recently" queries
        if temporal_multiplier > 0.8:
            base_score *= 1.2

    elif query_type == "historical":
        # Reduce temporal penalty for historical queries
        # Recalculate with very slow decay
        if timestamp:
            historical_temporal = temporal_decay(timestamp, decay_rate=0.01)
            base_score *= (historical_temporal / max(temporal_multiplier, 0.01))

    elif query_type == "expertise_required":
        # Boost blocks with high-trust expert participants
        # (Already handled in relationship boost, could be enhanced)
        pass

    # Normalize to 0-100+ scale
    final_score = base_score * 100

    return final_score


class SearchResult:
    """
    Container for search results with multiple scores

    From docs Section 2.2 (lines 617-627)
    """

    def __init__(
        self,
        block: Dict[str, Any],
        semantic_score: float = 0.0,
        keyword_score: float = 0.0,
        combined_score: float = 0.0
    ):
        """
        Initialize search result

        Args:
            block: Memory block dict
            semantic_score: Semantic similarity score (0-1)
            keyword_score: Keyword match score (0-1)
            combined_score: Final combined score (0-100+)
        """
        self.block = block
        self.semantic_score = semantic_score
        self.keyword_score = keyword_score
        self.combined_score = combined_score
        self.score = combined_score  # For sorting

    def __repr__(self) -> str:
        return (
            f"SearchResult(block={self.block.get('block_number', '?')}, "
            f"score={self.score:.2f}, "
            f"semantic={self.semantic_score:.2f}, "
            f"keyword={self.keyword_score:.2f})"
        )

    def __lt__(self, other: 'SearchResult') -> bool:
        """Enable sorting by score (descending)"""
        return self.score > other.score  # Reverse for descending order


def merge_results(
    semantic_results: list,
    keyword_results: list,
    query_context: Optional[Dict[str, Any]] = None
) -> list:
    """
    Merge semantic and keyword search results intelligently

    Combines results from both search methods, deduplicating and
    preserving the best score for each block.

    From docs Section 2.2 (lines 562-614)

    Args:
        semantic_results: List of (block, score) from semantic search
        keyword_results: List of (block, score) from keyword search
        query_context: Query context for final scoring

    Returns:
        List of SearchResult objects with combined scores, sorted by relevance
    """
    if query_context is None:
        query_context = {}

    # Create dict keyed by block number
    merged = {}

    # Add semantic results
    for block, score in semantic_results:
        block_num = block.get("block_number")
        if block_num is not None:
            merged[block_num] = SearchResult(
                block=block,
                semantic_score=score,
                keyword_score=0.0,
                combined_score=0.0  # Will calculate after merge
            )

    # Add/merge keyword results
    for block, score in keyword_results:
        block_num = block.get("block_number")
        if block_num is not None:
            if block_num in merged:
                # Block found in both - update keyword score
                merged[block_num].keyword_score = score
            else:
                # Only in keyword results
                merged[block_num] = SearchResult(
                    block=block,
                    semantic_score=0.0,
                    keyword_score=score,
                    combined_score=0.0
                )

    # Calculate combined scores
    results = []
    for result in merged.values():
        # Use calculate_final_score for combined scoring
        result.combined_score = calculate_final_score(
            result.block,
            result.semantic_score,
            result.keyword_score,
            query_context
        )
        result.score = result.combined_score
        results.append(result)

    # Sort by combined score (descending via __lt__ method)
    results.sort()

    return results
