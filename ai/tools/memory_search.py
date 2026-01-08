"""
Intelligent Memory Search - 5-Layer Hybrid System

Multi-layer memory recall combining:
- Layer 1: Semantic Search (FAISS embeddings)
- Layer 2: Metadata Filtering (fast pre-filter)
- Layer 3: Full-Text Search (BM25 ranking)
- Layer 4: Temporal Relevance (recency bias)
- Layer 5: Relationship-Aware Search (social context)

From docs/05_Data_Structures.md Section 2.2 (lines 358-682)
"""

import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from ai.embeddings import merge_results, SearchResult
from utils.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# BM25 FULL-TEXT SEARCH
# =============================================================================

# Common English stopwords to filter out
STOPWORDS = frozenset([
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "her", "our", "their", "mine", "yours", "hers", "ours", "theirs",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "also", "now", "here", "there",
    "then", "once", "if", "because", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "while", "any", "am", "being", "get", "got",
    "said", "say", "says", "like", "okay", "ok", "yes", "no", "yeah",
    "well", "really", "actually", "basically", "simply", "going", "went"
])


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words, removing stopwords and short tokens.

    Args:
        text: Input text

    Returns:
        List of tokens (lowercase, filtered)
    """
    # Lowercase and extract words (letters and numbers)
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())

    # Filter stopwords and very short tokens
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class BM25Scorer:
    """
    BM25 (Best Matching 25) ranking algorithm for full-text search.

    BM25 improves on simple TF-IDF by:
    - Saturating term frequency (diminishing returns for repeated terms)
    - Normalizing by document length
    - Using probabilistic IDF
    """

    # BM25 parameters (standard values)
    K1 = 1.5   # Term frequency saturation (1.2-2.0 typical)
    B = 0.75   # Length normalization (0.75 standard)

    def __init__(self, documents: List[List[str]]):
        """
        Initialize BM25 scorer with a corpus of documents.

        Args:
            documents: List of tokenized documents (each doc is list of tokens)
        """
        self.corpus_size = len(documents)
        self.doc_lengths = [len(doc) for doc in documents]
        self.avgdl = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 1

        # Document frequency: how many docs contain each term
        self.doc_freqs: Dict[str, int] = Counter()
        for doc in documents:
            unique_terms = set(doc)
            for term in unique_terms:
                self.doc_freqs[term] += 1

        # Pre-compute IDF for all terms
        self.idf: Dict[str, float] = {}
        for term, df in self.doc_freqs.items():
            # BM25 IDF formula (with smoothing to avoid negative values)
            self.idf[term] = math.log(
                (self.corpus_size - df + 0.5) / (df + 0.5) + 1
            )

        # Store term frequencies per document
        self.doc_term_freqs: List[Counter] = [Counter(doc) for doc in documents]

    def score(self, query_tokens: List[str], doc_index: int) -> float:
        """
        Calculate BM25 score for a query against a specific document.

        Args:
            query_tokens: Tokenized query
            doc_index: Index of document in corpus

        Returns:
            BM25 relevance score
        """
        if doc_index >= self.corpus_size:
            return 0.0

        score = 0.0
        doc_len = self.doc_lengths[doc_index]
        term_freqs = self.doc_term_freqs[doc_index]

        for term in query_tokens:
            if term not in self.idf:
                continue

            tf = term_freqs.get(term, 0)
            if tf == 0:
                continue

            idf = self.idf[term]

            # BM25 term score formula
            numerator = tf * (self.K1 + 1)
            denominator = tf + self.K1 * (1 - self.B + self.B * doc_len / self.avgdl)

            score += idf * (numerator / denominator)

        return score

    def score_all(self, query_tokens: List[str]) -> List[Tuple[int, float]]:
        """
        Score all documents against a query.

        Args:
            query_tokens: Tokenized query

        Returns:
            List of (doc_index, score) tuples, sorted by score descending
        """
        scores = []
        for i in range(self.corpus_size):
            s = self.score(query_tokens, i)
            if s > 0:
                scores.append((i, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# =============================================================================
# TEMPORAL PARSING
# =============================================================================

# Days of the week for "last Monday" style queries
WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def parse_temporal_reference(query: str) -> Optional[Tuple[int, int]]:
    """
    Parse temporal references from a query string.

    Handles various natural language time expressions:
    - "today", "yesterday"
    - "X days/weeks/months ago"
    - "last week", "last month", "last year"
    - "this week", "this month"
    - "last Monday", "last Tuesday", etc.

    Args:
        query: Query string to parse

    Returns:
        Tuple of (start_timestamp, end_timestamp) or None if no temporal reference found
    """
    query_lower = query.lower()
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp())

    # === Today / Yesterday ===
    if "today" in query_lower:
        # Start of today (midnight UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return (int(start_of_day.timestamp()), end_time)

    if "yesterday" in query_lower:
        # Yesterday: from start of yesterday to start of today
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_yesterday = int(start_of_today.timestamp()) - 86400
        end_of_yesterday = int(start_of_today.timestamp())
        return (start_of_yesterday, end_of_yesterday)

    # === X days/weeks/months/years ago ===
    # Match patterns like "3 days ago", "2 weeks ago", "1 month ago"
    ago_pattern = re.search(r'(\d+)\s*(day|week|month|year)s?\s*ago', query_lower)
    if ago_pattern:
        amount = int(ago_pattern.group(1))
        unit = ago_pattern.group(2)

        if unit == "day":
            seconds = amount * 86400
        elif unit == "week":
            seconds = amount * 7 * 86400
        elif unit == "month":
            seconds = amount * 30 * 86400  # Approximate
        elif unit == "year":
            seconds = amount * 365 * 86400  # Approximate
        else:
            seconds = 0

        start_time = end_time - seconds
        return (start_time, end_time)

    # === Last week / month / year ===
    if "last week" in query_lower or "past week" in query_lower:
        start_time = end_time - (7 * 86400)
        return (start_time, end_time)

    if "last month" in query_lower or "past month" in query_lower:
        start_time = end_time - (30 * 86400)
        return (start_time, end_time)

    if "last year" in query_lower or "past year" in query_lower:
        start_time = end_time - (365 * 86400)
        return (start_time, end_time)

    # === This week / month ===
    if "this week" in query_lower:
        # Start of this week (Monday)
        days_since_monday = now.weekday()
        start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = int(start_of_week.timestamp()) - (days_since_monday * 86400)
        return (start_of_week, end_time)

    if "this month" in query_lower:
        # Start of this month
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (int(start_of_month.timestamp()), end_time)

    # === Last [weekday] (e.g., "last Monday", "last Tuesday") ===
    for day_name, day_num in WEEKDAYS.items():
        if f"last {day_name}" in query_lower:
            # Find the most recent occurrence of this weekday
            current_weekday = now.weekday()
            days_ago = (current_weekday - day_num) % 7
            if days_ago == 0:
                days_ago = 7  # "last Monday" when today is Monday means 7 days ago

            target_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_target = int(target_day.timestamp()) - (days_ago * 86400)
            end_of_target = start_of_target + 86400  # End of that day

            return (start_of_target, end_of_target)

    # === Relative expressions ===
    if "few days" in query_lower or "couple days" in query_lower or "couple of days" in query_lower:
        start_time = end_time - (3 * 86400)  # ~3 days
        return (start_time, end_time)

    if "few weeks" in query_lower or "couple weeks" in query_lower or "couple of weeks" in query_lower:
        start_time = end_time - (14 * 86400)  # ~2 weeks
        return (start_time, end_time)

    # No temporal reference found
    return None


def get_user_memory_config(qube) -> Optional[Dict[str, Any]]:
    """
    Load user's memory recall configuration from preferences.

    Args:
        qube: Qube instance with user_name and data_dir

    Returns:
        MemoryConfig as dict or None if not available
    """
    try:
        if not hasattr(qube, 'data_dir') or not hasattr(qube, 'user_name'):
            return None

        # User preferences are in data/users/{user_name}/preferences.json
        # data_dir is data/users/{user_name}/qubes/
        user_data_dir = qube.data_dir.parent

        from config.user_preferences import UserPreferencesManager
        prefs_manager = UserPreferencesManager(user_data_dir)
        memory_config = prefs_manager.get_memory_config()

        # Convert to dict
        from dataclasses import asdict
        return asdict(memory_config)

    except Exception as e:
        logger.warning("failed_to_load_memory_config", error=str(e))
        return None


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
    elif any(word in query_lower for word in ["recent", "recently", "latest", "last week", "last day", "today", "yesterday"]):
        parsed["query_type"] = "recent_events"

    # Then check for expertise queries
    elif any(word in query_lower for word in ["expert", "specialist", "best at", "good at"]):
        parsed["query_type"] = "expertise_required"

    # Extract time references using the comprehensive temporal parser
    # Only parse if not already provided in context
    if parsed["date_range"] is None:
        temporal_range = parse_temporal_reference(query)
        if temporal_range:
            parsed["date_range"] = temporal_range
            logger.debug(
                "temporal_reference_parsed",
                query=query[:50],
                start=datetime.fromtimestamp(temporal_range[0], tz=timezone.utc).isoformat(),
                end=datetime.fromtimestamp(temporal_range[1], tz=timezone.utc).isoformat()
            )

    logger.debug("query_parsed", query_type=parsed["query_type"], has_date_range=parsed["date_range"] is not None)

    return parsed


async def intelligent_memory_search(
    qube,
    query: str,
    context: Optional[Dict[str, Any]] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None
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
            - semantic_weight, keyword_weight, temporal_weight, relationship_weight:
              Custom scoring weights (override user preferences)
        top_k: Maximum number of results (default: from user config or 5)
        min_score: Minimum relevance score threshold (default: from user config or 15.0)

    Returns:
        List of SearchResult objects above threshold, sorted by relevance (highest first)

    Process:
        1. Load user config and merge with context
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

    # Step 0: Load user's memory config and apply defaults
    user_config = get_user_memory_config(qube) or {}

    # Apply config values (context overrides user config, which overrides defaults)
    effective_min_score = min_score if min_score is not None else context.get("recall_threshold", user_config.get("recall_threshold", 15.0))
    effective_top_k = top_k if top_k is not None else context.get("max_recalls", user_config.get("max_recalls", 5))
    effective_decay_rate = context.get("decay_rate", user_config.get("decay_rate", 0.1))

    # Scoring weights (context overrides user config)
    effective_semantic_weight = context.get("semantic_weight", user_config.get("semantic_weight", 0.4))
    effective_keyword_weight = context.get("keyword_weight", user_config.get("keyword_weight", 0.3))
    effective_temporal_weight = context.get("temporal_weight", user_config.get("temporal_weight", 0.15))
    effective_relationship_weight = context.get("relationship_weight", user_config.get("relationship_weight", 0.1))

    logger.info(
        "intelligent_memory_search_started",
        query=query[:50],
        top_k=effective_top_k,
        min_score=effective_min_score,
        decay_rate=effective_decay_rate
    )

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
        top_k=effective_top_k * 3  # Get 3x candidates for re-ranking
    )

    # Step 4: Full-text search (Layer 3 - parallel)
    keyword_results = await fulltext_search(
        qube=qube,
        query=parsed["keyword_query"],
        candidates=candidate_blocks,
        top_k=effective_top_k * 3
    )

    # Step 5: Merge and re-rank with user-configured weights
    query_context = {
        "qube": qube,
        "query_type": parsed["query_type"],
        "decay_rate": effective_decay_rate,
        "semantic_weight": effective_semantic_weight,
        "keyword_weight": effective_keyword_weight,
        "temporal_weight": effective_temporal_weight,
        "relationship_weight": effective_relationship_weight,
    }

    merged = merge_results(semantic_results, keyword_results, query_context)

    # Steps 6-7: Temporal decay and relationship boost
    # (Already applied in calculate_final_score during merge_results)

    # Step 8: Filter by threshold and return top-K
    # Only include results that meet minimum relevance threshold
    filtered_results = [r for r in merged if r.score >= effective_min_score]
    top_results = filtered_results[:effective_top_k]

    logger.info(
        "intelligent_memory_search_complete",
        query=query[:50],
        total_merged=len(merged),
        above_threshold=len(filtered_results),
        returned=len(top_results),
        min_score_threshold=effective_min_score,
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
            # SemanticSearch.search() returns List[Tuple[block_number, score]]
            results = qube.semantic_search.search(
                query=query,
                top_k=top_k
            )

            # Create lookup from candidates by block_number
            candidate_lookup = {b.get("block_number"): b for b in candidates}

            # Convert (block_number, score) to (block_dict, score)
            # Only include blocks that are in our candidate set
            matched_results = []
            for block_num, score in results:
                if block_num in candidate_lookup:
                    matched_results.append((candidate_lookup[block_num], score))

            logger.debug(
                "semantic_search_layer_complete",
                query_length=len(query),
                faiss_results=len(results),
                matched_candidates=len(matched_results)
            )

            return matched_results

    except Exception as e:
        logger.error("semantic_search_failed", error=str(e), exc_info=True)

    # Fallback: return candidates with default score
    return [(block, 0.5) for block in candidates[:top_k]]


async def fulltext_search(
    qube,
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 30
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Layer 3: Full-text search using BM25 ranking

    Uses the BM25 algorithm for better relevance ranking compared to
    simple keyword matching. Includes stopword removal and proper
    term frequency / inverse document frequency scoring.

    Args:
        qube: Qube instance
        query: Search query
        candidates: Pre-filtered candidate blocks
        top_k: Number of results

    Returns:
        List of (block, score) tuples, sorted by BM25 relevance score
    """
    if not candidates:
        return []

    # Tokenize query
    query_tokens = tokenize(query)

    if not query_tokens:
        # If query is all stopwords, fall back to simple matching
        logger.debug("fulltext_query_all_stopwords", query=query[:50])
        return _fallback_simple_search(query, candidates, top_k)

    # Extract and tokenize text from all candidate blocks
    doc_texts = []
    for block in candidates:
        text = extract_text_from_block(block)
        tokens = tokenize(text)
        doc_texts.append(tokens)

    # Build BM25 index
    bm25 = BM25Scorer(doc_texts)

    # Score all documents
    scored_indices = bm25.score_all(query_tokens)

    # Convert indices back to (block, score) tuples
    # Normalize scores to 0-1 range for consistency with other layers
    max_score = scored_indices[0][1] if scored_indices else 1.0
    max_score = max(max_score, 0.001)  # Avoid division by zero

    results = []
    for doc_idx, score in scored_indices[:top_k]:
        normalized_score = score / max_score
        results.append((candidates[doc_idx], normalized_score))

    logger.debug(
        "fulltext_bm25_search_complete",
        query_tokens=len(query_tokens),
        candidates=len(candidates),
        results_found=len(results),
        top_score=results[0][1] if results else 0
    )

    return results


def _fallback_simple_search(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Fallback simple search when query has no meaningful tokens.

    Used when query is entirely stopwords (e.g., "what is the").

    Args:
        query: Original query string
        candidates: Candidate blocks
        top_k: Number of results

    Returns:
        List of (block, score) tuples
    """
    query_words = set(query.lower().split())
    scored_blocks = []

    for block in candidates:
        text = extract_text_from_block(block).lower()
        words = set(text.split())
        matches = query_words.intersection(words)

        if matches:
            score = len(matches) / len(query_words) if query_words else 0
            scored_blocks.append((block, score))

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
