# Phase 5: Memory & Recall - Implementation Blueprint

## Executive Summary

**Theme: Remember (Master Your Personal History)**

Memory & Recall is the **"librarian" Sun** - it manages ALL knowledge in the Qube's memory chain, regardless of which Sun created it. While other Suns (AI Reasoning, Social Intelligence, Board Games) create LEARNING blocks through their tools, Memory & Recall specializes in:

- **Searching**: Finding knowledge across all LEARNING blocks
- **Organizing**: Tagging and linking related knowledge
- **Synthesizing**: Combining knowledge to generate new insights
- **Documenting**: Exporting knowledge for external use

This phase heavily integrates with the existing Memory Chain infrastructure (FAISS semantic search, BM25 full-text search, temporal decay, relationship boosting) while adding new LEARNING block capabilities.

### Tool Summary

| Level | Count | Tools |
|-------|-------|-------|
| Sun | 1 | `store_knowledge` |
| Planet | 5 | `recall`, `store_fact`, `tag_memory`, `synthesize_knowledge`, `create_summary` |
| Moon | 10 | `keyword_search`, `semantic_search`, `search_memory`, `record_skill`, `add_tags`, `link_memories`, `find_patterns`, `generate_insight`, `write_summary`, `export_knowledge` |
| **Total** | **16** | |

### XP Model

Standard XP model (5/2.5/0) for all tools:
- **Success**: 5 XP
- **Completed**: 2.5 XP
- **Failed**: 0 XP

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Task 5.1: Add LEARNING Block Type](#task-51-add-learning-block-type)
3. [Task 5.2: Update Skill Definitions](#task-52-update-skill-definitions)
4. [Task 5.3: Implement Sun Tool](#task-53-implement-sun-tool)
5. [Task 5.4: Implement Planet Tools](#task-54-implement-planet-tools)
6. [Task 5.5: Implement Moon Tools](#task-55-implement-moon-tools)
7. [Task 5.6: Memory Chain Enhancements](#task-56-memory-chain-enhancements)
8. [Task 5.7: Universal Search Integration](#task-57-universal-search-integration)
9. [Task 5.8: Update XP Routing](#task-58-update-xp-routing)
10. [Task 5.9: Frontend Integration](#task-59-frontend-integration)
11. [Task 5.10: Testing & Validation](#task-510-testing--validation)
12. [Files Modified Summary](#files-modified-summary)

---

## Prerequisites

### From Phase 0 (Foundation)

1. **LEARNING Block Type** (Task 0.4 in Phase 0)
   - File: `core/block.py`
   - Adds `LEARNING = "LEARNING"` to BlockType enum
   - Adds `create_learning_block()` function

2. **Qube Locker** (Task 0.12 in Phase 0)
   - File: `core/locker.py`
   - Required for `create_summary`, `write_summary`, `export_knowledge` tools

3. **XP Trickle-Up System** (Task 0.6 in Phase 0)
   - File: `core/xp_router.py`
   - Required for routing XP from tools to skills

### Existing Infrastructure Leveraged

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| MemoryChain | `core/memory_chain.py` | 28-564 | Block storage, retrieval, integrity |
| SemanticSearch | `ai/semantic_search.py` | 21-321 | FAISS embeddings, similarity search |
| BM25Scorer | `ai/tools/memory_search.py` | 68-165 | Full-text search ranking |
| intelligent_memory_search | `ai/tools/memory_search.py` | 385-519 | 5-layer hybrid search |
| ChainState | `core/chain_state.py` | 248-500+ | State management |
| Qube Profile | `core/chain_state.py` | 2468-2730 | Self-identity data |
| Owner Info | `core/chain_state.py` | 81-245 | Owner data |

### Current Codebase State (as of Jan 2026)

#### Category Naming
- **Current ID**: `knowledge_domains`
- **Current Name**: "Knowledge Domains"
- **Target ID**: `memory_recall`
- **Target Name**: "Memory & Recall"
- **Action**: Rename category in both Python and TypeScript

#### Existing Skills (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current Sun tool**: `search_memory` (existing tool, works)
- **Current Planets**: science, history, philosophy, mathematics, languages
- **Action**: Replace entire skill tree with new memory-centric structure

#### Tool Mappings (`ai/skill_scanner.py:71-74`)
- **Current mappings** (to be replaced):
  ```python
  "deep_research": "science"
  "synthesize_knowledge": "philosophy"
  "explain_like_im_five": "philosophy"
  ```
- **Target mappings** (new tools):
  ```python
  "store_knowledge": "memory_recall"  # Sun
  "universal_search": "retrieval_mastery"
  "recall_memories": "retrieval_mastery"
  # ... 13 more new tool mappings
  ```

#### Memory Search (`ai/tools/memory_search.py`)
- **Current**: `intelligent_memory_search()` with 5-layer hybrid search
- **Status**: ✅ Fully implemented and working
- **Action**: New tools will wrap/extend this infrastructure

---

## Task 5.1: Add LEARNING Block Type

> **Note**: This task is implemented in Phase 0 (Task 0.4). The following documents what should already exist.

### File: `core/block.py`

**Location**: Lines 17-29 (BlockType enum)

```python
class BlockType(str, Enum):
    """Memory block types - exactly as documented"""
    GENESIS = "GENESIS"
    THOUGHT = "THOUGHT"
    ACTION = "ACTION"
    OBSERVATION = "OBSERVATION"
    MESSAGE = "MESSAGE"
    DECISION = "DECISION"
    MEMORY_ANCHOR = "MEMORY_ANCHOR"
    COLLABORATIVE_MEMORY = "COLLABORATIVE_MEMORY"
    SUMMARY = "SUMMARY"
    GAME = "GAME"
    LEARNING = "LEARNING"  # NEW - Added in Phase 0
```

### LEARNING Block Schema

**Location**: Add after line 835 in `core/block.py`

```python
# =============================================================================
# LEARNING BLOCK
# =============================================================================

def create_learning_block(
    qube_id: str,
    block_number: int,
    previous_hash: str,
    learning_type: str,
    content: Dict[str, Any],
    source_block: Optional[int] = None,
    source_category: Optional[str] = None,
    confidence: int = 80,
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create a LEARNING block for storing knowledge.

    LEARNING blocks are cross-cutting - they can be created by any Sun
    but are managed by the Memory & Recall Sun.

    Args:
        qube_id: 8-character Qube ID
        block_number: Block number in chain
        previous_hash: Hash of previous block
        learning_type: Type of learning (fact, procedure, synthesis, insight, pattern)
        content: Learning content (type-specific fields)
        source_block: Block number that triggered this learning
        source_category: Which Sun/context created this (ai_reasoning, social_intelligence, etc.)
        confidence: Confidence level 0-100
        temporary: Whether this is a session block
        session_id: Session ID if temporary

    Returns:
        Block: LEARNING block

    Learning Types:
        - fact: General facts ("BCH uses 8MB blocks")
        - procedure: How to do something (steps list)
        - synthesis: Combined knowledge from multiple sources
        - insight: Patterns or realizations discovered
        - pattern: Recurring patterns identified
    """
    learning_content = {
        "learning_type": learning_type,
        "source_block": source_block,
        "source_category": source_category,
        "confidence": confidence,
        **content
    }

    return Block(
        block_type=BlockType.LEARNING,
        block_number=block_number,
        qube_id=qube_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=block_number - 1 if temporary else None,
        content=learning_content,
        temporary=temporary,
        session_id=session_id
    )
```

---

## Task 5.2: Update Skill Definitions

### File: `ai/tools/handlers.py`

**Location**: Lines 28-100 (SKILL_CATEGORIES and SKILL_TREE)

#### 5.2.1: Update SKILL_CATEGORIES

Replace `knowledge_domains` with `memory_recall`:

```python
SKILL_CATEGORIES = [
    {"id": "ai_reasoning", "name": "AI Reasoning", "color": "#4A90E2", "icon": "brain", "description": "Master AI reasoning and problem-solving capabilities"},
    {"id": "social_intelligence", "name": "Social Intelligence", "color": "#FF69B4", "icon": "handshake", "description": "Master social dynamics and interpersonal skills"},
    {"id": "coding", "name": "Coding", "color": "#00FF88", "icon": "code", "description": "Ship working code that solves real problems"},
    {"id": "creative_expression", "name": "Creative Expression", "color": "#FFB347", "icon": "palette", "description": "Express your unique self through creative works"},
    {"id": "memory_recall", "name": "Memory & Recall", "color": "#9B59B6", "icon": "brain-cog", "description": "Master your personal history and accumulated wisdom"},
    {"id": "security_privacy", "name": "Security & Privacy", "color": "#E74C3C", "icon": "shield", "description": "Protect self, owner, and network"},
    {"id": "board_games", "name": "Board Games", "color": "#F39C12", "icon": "chess", "description": "Master strategic games"},
    {"id": "finance", "name": "Finance", "color": "#27AE60", "icon": "wallet", "description": "Master financial operations"},
]
```

#### 5.2.2: Add memory_recall to SKILL_TREE

**Location**: Add after `creative_expression` section in SKILL_TREE

```python
    "memory_recall": [
        # Sun
        {
            "id": "memory_recall",
            "name": "Memory & Recall",
            "node_type": "sun",
            "xp_required": 1000,
            "tool_unlock": "store_knowledge",
            "icon": "brain-cog",
            "description": "Master your personal history and accumulated wisdom"
        },
        # Planet 1: Memory Search
        {
            "id": "memory_search",
            "name": "Memory Search",
            "node_type": "planet",
            "parent": "memory_recall",
            "xp_required": 500,
            "tool_unlock": "recall",
            "icon": "search",
            "description": "Search across all storage systems to find information"
        },
        # Planet 2: Knowledge Storage
        {
            "id": "knowledge_storage",
            "name": "Knowledge Storage",
            "node_type": "planet",
            "parent": "memory_recall",
            "xp_required": 500,
            "tool_unlock": "store_fact",
            "icon": "database",
            "description": "Store specific types of knowledge with precision"
        },
        # Planet 3: Memory Organization
        {
            "id": "memory_organization",
            "name": "Memory Organization",
            "node_type": "planet",
            "parent": "memory_recall",
            "xp_required": 500,
            "tool_unlock": "tag_memory",
            "icon": "tags",
            "description": "Organize and categorize memories"
        },
        # Planet 4: Knowledge Synthesis
        {
            "id": "knowledge_synthesis",
            "name": "Knowledge Synthesis",
            "node_type": "planet",
            "parent": "memory_recall",
            "xp_required": 500,
            "tool_unlock": "synthesize_knowledge",
            "icon": "sparkles",
            "description": "Combine information to generate new insights"
        },
        # Planet 5: Documentation
        {
            "id": "documentation",
            "name": "Documentation",
            "node_type": "planet",
            "parent": "memory_recall",
            "xp_required": 500,
            "tool_unlock": "create_summary",
            "icon": "file-text",
            "description": "Document and export knowledge"
        },
        # Moon 1.1: Keyword Search
        {
            "id": "keyword_search_skill",
            "name": "Keyword Search",
            "node_type": "moon",
            "parent": "memory_search",
            "xp_required": 250,
            "tool_unlock": "keyword_search",
            "icon": "text-search",
            "description": "Find memories by exact keywords"
        },
        # Moon 1.2: Semantic Search
        {
            "id": "semantic_search_skill",
            "name": "Semantic Search",
            "node_type": "moon",
            "parent": "memory_search",
            "xp_required": 250,
            "tool_unlock": "semantic_search",
            "icon": "brain",
            "description": "Find memories by meaning, not just keywords"
        },
        # Moon 1.3: Filtered Search
        {
            "id": "filtered_search",
            "name": "Filtered Search",
            "node_type": "moon",
            "parent": "memory_search",
            "xp_required": 250,
            "tool_unlock": "search_memory",
            "icon": "filter",
            "description": "Advanced search with source and type filters"
        },
        # Moon 2.1: Procedures
        {
            "id": "procedures",
            "name": "Procedures",
            "node_type": "moon",
            "parent": "knowledge_storage",
            "xp_required": 250,
            "tool_unlock": "record_skill",
            "icon": "list-ordered",
            "description": "Record procedural knowledge - how to do things"
        },
        # Moon 3.1: Topic Tagging
        {
            "id": "topic_tagging",
            "name": "Topic Tagging",
            "node_type": "moon",
            "parent": "memory_organization",
            "xp_required": 250,
            "tool_unlock": "add_tags",
            "icon": "tag",
            "description": "Auto-tag memories by topic"
        },
        # Moon 3.2: Memory Linking
        {
            "id": "memory_linking",
            "name": "Memory Linking",
            "node_type": "moon",
            "parent": "memory_organization",
            "xp_required": 250,
            "tool_unlock": "link_memories",
            "icon": "link",
            "description": "Create connections between related memories"
        },
        # Moon 4.1: Pattern Recognition
        {
            "id": "pattern_recognition",
            "name": "Pattern Recognition",
            "node_type": "moon",
            "parent": "knowledge_synthesis",
            "xp_required": 250,
            "tool_unlock": "find_patterns",
            "icon": "scan",
            "description": "Find patterns across memories"
        },
        # Moon 4.2: Insight Generation
        {
            "id": "insight_generation",
            "name": "Insight Generation",
            "node_type": "moon",
            "parent": "knowledge_synthesis",
            "xp_required": 250,
            "tool_unlock": "generate_insight",
            "icon": "lightbulb",
            "description": "Generate new insights from existing knowledge"
        },
        # Moon 5.1: Summary Writing
        {
            "id": "summary_writing",
            "name": "Summary Writing",
            "node_type": "moon",
            "parent": "documentation",
            "xp_required": 250,
            "tool_unlock": "write_summary",
            "icon": "scroll-text",
            "description": "Write detailed summaries"
        },
        # Moon 5.2: Knowledge Export
        {
            "id": "knowledge_export",
            "name": "Knowledge Export",
            "node_type": "moon",
            "parent": "documentation",
            "xp_required": 250,
            "tool_unlock": "export_knowledge",
            "icon": "download",
            "description": "Export knowledge for external use"
        },
    ],
```

---

## Task 5.3: Implement Sun Tool

### File: `ai/tools/memory_tools.py` (NEW FILE)

Create new file for Memory & Recall tools:

```python
"""
Memory & Recall Tools - Phase 5 Implementation

The "librarian" Sun - manages ALL knowledge in the Qube's memory chain.
Searches, organizes, synthesizes, and documents knowledge.

Theme: Remember (Master Your Personal History)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from core.block import Block, BlockType, create_learning_block
from core.exceptions import AIError
from ai.tools.registry import ToolDefinition
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_owner_fact(knowledge: str) -> bool:
    """
    Detect if knowledge is about the owner (should go to Owner Info).

    Patterns:
    - "Owner's name is..."
    - "My owner..."
    - "{owner_name}'s birthday..."
    - "The owner prefers..."
    """
    owner_patterns = [
        "owner's", "owner is", "my owner", "the owner",
        "user's", "user is", "my user", "the user"
    ]
    knowledge_lower = knowledge.lower()
    return any(pattern in knowledge_lower for pattern in owner_patterns)


def is_self_fact(knowledge: str) -> bool:
    """
    Detect if knowledge is about the Qube itself (should go to Qube Profile).

    Patterns:
    - "My favorite color is..."
    - "I prefer..."
    - "My name is..."
    - "I am..."
    """
    self_patterns = [
        "my favorite", "my name", "i prefer", "i am", "i like",
        "my personality", "my style", "my voice", "my goal"
    ]
    knowledge_lower = knowledge.lower()
    return any(pattern in knowledge_lower for pattern in self_patterns)


async def redirect_to_owner_info(qube, knowledge: str) -> Dict[str, Any]:
    """
    Redirect owner-related knowledge to Owner Info system.

    Uses update_system_state tool internally.
    """
    from ai.tools.handlers import update_system_state

    # Parse the knowledge to extract field and value
    # This is a simplified parser - production would use LLM
    result = await update_system_state(qube, {
        "section": "owner_info",
        "updates": {"note": knowledge}  # Store as note for now
    })

    return {
        "success": True,
        "redirected_to": "owner_info",
        "message": f"Stored in Owner Info: {knowledge[:50]}...",
        "original_knowledge": knowledge
    }


async def redirect_to_qube_profile(qube, knowledge: str) -> Dict[str, Any]:
    """
    Redirect self-related knowledge to Qube Profile system.

    Uses update_system_state tool internally.
    """
    from ai.tools.handlers import update_system_state

    result = await update_system_state(qube, {
        "section": "qube_profile",
        "updates": {"note": knowledge}  # Store as note for now
    })

    return {
        "success": True,
        "redirected_to": "qube_profile",
        "message": f"Stored in Qube Profile: {knowledge[:50]}...",
        "original_knowledge": knowledge
    }


def extract_topics(text: str) -> List[str]:
    """
    Extract topic tags from text using keyword extraction.

    Uses simple TF-IDF-like approach for topic extraction.
    """
    from ai.tools.memory_search import tokenize

    tokens = tokenize(text)

    # Count token frequency
    from collections import Counter
    freq = Counter(tokens)

    # Return top 5 most frequent meaningful tokens as topics
    return [token for token, _ in freq.most_common(5)]


def extract_entities(text: str) -> List[str]:
    """
    Extract named entities from text.

    Simple pattern-based extraction for names, places, organizations.
    """
    import re

    # Capitalize words that might be entities
    entities = []

    # Find capitalized words (potential proper nouns)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    entities.extend(capitalized[:5])

    return list(set(entities))


# =============================================================================
# SUN TOOL: store_knowledge
# =============================================================================

STORE_KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "knowledge": {
            "type": "string",
            "description": "The knowledge to store"
        },
        "category": {
            "type": "string",
            "enum": ["fact", "procedure", "insight"],
            "description": "Type of knowledge: fact (general truth), procedure (how-to), insight (realization)"
        },
        "source": {
            "type": "string",
            "enum": ["self", "owner", "conversation", "research"],
            "description": "Source of the knowledge"
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Confidence level 0-100 (default: 80)"
        }
    },
    "required": ["knowledge"]
}

STORE_KNOWLEDGE_DEFINITION = ToolDefinition(
    name="store_knowledge",
    description="Store knowledge explicitly in the memory chain. The foundational act - capture knowledge before you can recall it. Auto-redirects owner/self data to appropriate systems.",
    input_schema=STORE_KNOWLEDGE_SCHEMA,
    category="memory_recall"
)


async def store_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store knowledge explicitly in the memory chain.

    The Sun tool for Memory & Recall - the foundational act of capturing knowledge.
    Includes auto-redirect for owner/self data to appropriate storage.

    Args:
        qube: Qube instance
        params: {
            knowledge: str - The knowledge to store
            category: str - fact, procedure, or insight (default: fact)
            source: str - self, owner, conversation, research (default: self)
            confidence: int - 0-100 (default: 80 for self, 100 for owner)
        }

    Returns:
        Dict with success status, stored knowledge, block_id
    """
    knowledge = params.get("knowledge")
    if not knowledge:
        return {"success": False, "error": "Knowledge content is required"}

    category = params.get("category", "fact")
    source = params.get("source", "self")
    confidence = params.get("confidence", 100 if source == "owner" else 80)

    # Auto-redirect: Owner facts go to Owner Info
    if is_owner_fact(knowledge):
        logger.info("store_knowledge_redirect_owner", knowledge=knowledge[:50])
        return await redirect_to_owner_info(qube, knowledge)

    # Auto-redirect: Self facts go to Qube Profile
    if is_self_fact(knowledge):
        logger.info("store_knowledge_redirect_self", knowledge=knowledge[:50])
        return await redirect_to_qube_profile(qube, knowledge)

    # Get chain info for block creation
    try:
        chain_length = qube.memory_chain.get_chain_length()
        latest_block = qube.memory_chain.get_latest_block()
        previous_hash = latest_block.block_hash if latest_block else "0" * 64

        # Create LEARNING block content based on category
        if category == "fact":
            content = {
                "fact": knowledge,
                "subject": extract_entities(knowledge)[0] if extract_entities(knowledge) else "general",
                "source": source
            }
        elif category == "procedure":
            # Parse steps if provided as list
            steps = params.get("steps", [knowledge])
            content = {
                "skill_name": params.get("skill_name", "Unnamed procedure"),
                "steps": steps if isinstance(steps, list) else [steps],
                "tips": params.get("tips", [])
            }
        elif category == "insight":
            content = {
                "insight": knowledge,
                "evidence": params.get("evidence", [])
            }
        else:
            content = {"knowledge": knowledge}

        # Create LEARNING block
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=chain_length,
            previous_hash=previous_hash,
            learning_type=category,
            content=content,
            source_category="memory_recall",
            confidence=confidence,
            temporary=True,  # Start as session block
            session_id=qube.current_session.session_id if hasattr(qube, 'current_session') else None
        )

        # Add to session (will be anchored later)
        if hasattr(qube, 'current_session'):
            await qube.current_session.add_block(block)

        # Index for semantic search (before encryption)
        topics = extract_topics(knowledge)
        entities = extract_entities(knowledge)

        if hasattr(qube, 'semantic_search') and qube.semantic_search:
            qube.semantic_search.add_block(block)

        logger.info(
            "knowledge_stored",
            category=category,
            topics=topics,
            confidence=confidence
        )

        return {
            "success": True,
            "stored": knowledge[:100] + "..." if len(knowledge) > 100 else knowledge,
            "category": category,
            "source": source,
            "confidence": confidence,
            "topics": topics,
            "entities": entities,
            "block_number": block.block_number,
            "message": f"I'll remember: {knowledge[:100]}..."
        }

    except Exception as e:
        logger.error("store_knowledge_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Failed to store knowledge: {str(e)}"
        }
```

---

## Task 5.4: Implement Planet Tools

### Continue in `ai/tools/memory_tools.py`

```python
# =============================================================================
# PLANET 1: recall (Memory Search)
# =============================================================================

RECALL_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "What to search for"
        },
        "context": {
            "type": "string",
            "description": "Additional context to refine search"
        },
        "time_range": {
            "type": "string",
            "description": "Time filter: 'today', 'yesterday', 'last week', 'last month', or date range"
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "description": "Maximum results to return (default: 10)"
        }
    },
    "required": ["query"]
}

RECALL_DEFINITION = ToolDefinition(
    name="recall",
    description="Universal memory recall - searches ALL storage systems including LEARNING blocks, memory chain, Qube Profile, Owner Info, and Qube Locker.",
    input_schema=RECALL_SCHEMA,
    category="memory_recall"
)


async def recall(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Universal memory recall - searches ALL storage systems.

    The primary "find anything" operation. Searches across:
    1. LEARNING blocks (explicit knowledge)
    2. Memory Chain (conversations, actions, summaries)
    3. Qube Profile (self-identity)
    4. Owner Info (owner data - respects sensitivity)
    5. Qube Locker (creative works)

    Args:
        qube: Qube instance
        params: {
            query: str - What to search for
            context: str - Additional context (optional)
            time_range: str - Time filter (optional)
            limit: int - Max results (default: 10)
        }

    Returns:
        Dict with results from all systems, scored and ranked
    """
    from ai.tools.memory_search import intelligent_memory_search, parse_temporal_reference

    query = params.get("query")
    if not query:
        return {"success": False, "error": "Query is required"}

    context = params.get("context", "")
    time_range = params.get("time_range")
    limit = params.get("limit", 10)

    all_results = []
    sources_searched = []

    try:
        # 1. Search LEARNING blocks (using existing memory search)
        learning_results = await intelligent_memory_search(
            qube=qube,
            query=query,
            block_types=["LEARNING"],
            limit=limit
        )
        for r in learning_results:
            r["source"] = "learning"
        all_results.extend(learning_results)
        sources_searched.append("learning")

        # 2. Search Memory Chain (other block types)
        chain_results = await intelligent_memory_search(
            qube=qube,
            query=query,
            block_types=["MESSAGE", "ACTION", "SUMMARY", "GAME"],
            time_filter=parse_temporal_reference(time_range) if time_range else None,
            limit=limit
        )
        for r in chain_results:
            r["source"] = "memory_chain"
        all_results.extend(chain_results)
        sources_searched.append("memory_chain")

        # 3. Search Qube Profile
        profile_results = search_qube_profile(qube, query)
        all_results.extend(profile_results)
        sources_searched.append("qube_profile")

        # 4. Search Owner Info (respects sensitivity)
        owner_results = search_owner_info(qube, query)
        all_results.extend(owner_results)
        sources_searched.append("owner_info")

        # 5. Search Qube Locker
        if hasattr(qube, 'locker') and qube.locker:
            locker_results = await qube.locker.search(query)
            for r in locker_results:
                r["source"] = "qube_locker"
            all_results.extend(locker_results)
            sources_searched.append("qube_locker")

        # Score and rank all results
        scored_results = score_relevance(all_results, query, context)

        # Take top results
        top_results = scored_results[:limit]

        logger.info(
            "recall_completed",
            query=query[:50],
            total_found=len(all_results),
            returned=len(top_results)
        )

        return {
            "success": True,
            "query": query,
            "results": top_results,
            "total_found": len(all_results),
            "sources_searched": sources_searched,
            "time_range": time_range or "all time"
        }

    except Exception as e:
        logger.error("recall_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Recall failed: {str(e)}"
        }


def search_qube_profile(qube, query: str) -> List[Dict[str, Any]]:
    """
    Search Qube Profile for matching content.

    Searches across: preferences, traits, opinions, goals, style, interests
    """
    results = []
    query_lower = query.lower()

    try:
        # Get profile from chain state
        chain_state = qube.chain_state if hasattr(qube, 'chain_state') else {}
        profile = chain_state.get("qube_profile", {})

        # Search each section
        for section in ["preferences", "traits", "opinions", "goals", "style", "interests"]:
            section_data = profile.get(section, {})
            for key, value in section_data.items():
                value_str = str(value).lower()
                if query_lower in key.lower() or query_lower in value_str:
                    results.append({
                        "source": "qube_profile",
                        "section": section,
                        "key": key,
                        "value": value,
                        "relevance": 0.8,
                        "content": f"{section}/{key}: {value}"
                    })

    except Exception as e:
        logger.warning("qube_profile_search_failed", error=str(e))

    return results


def search_owner_info(qube, query: str) -> List[Dict[str, Any]]:
    """
    Search Owner Info for matching content.

    Respects sensitivity levels - only returns non-sensitive data.
    """
    results = []
    query_lower = query.lower()

    try:
        chain_state = qube.chain_state if hasattr(qube, 'chain_state') else {}
        owner_info = chain_state.get("owner_info", {})

        # Only search non-sensitive fields
        safe_fields = ["name", "nickname", "location", "timezone", "interests"]

        for field in safe_fields:
            if field in owner_info:
                value = owner_info[field]
                value_str = str(value).lower()
                if query_lower in field.lower() or query_lower in value_str:
                    results.append({
                        "source": "owner_info",
                        "field": field,
                        "value": value,
                        "relevance": 0.7,
                        "content": f"Owner {field}: {value}"
                    })

    except Exception as e:
        logger.warning("owner_info_search_failed", error=str(e))

    return results


def score_relevance(results: List[Dict[str, Any]], query: str, context: str = "") -> List[Dict[str, Any]]:
    """
    Score and rank results by relevance.

    Combines:
    - Keyword matching
    - Source priority (LEARNING > memory_chain > profile > locker)
    - Existing relevance scores
    """
    from ai.tools.memory_search import tokenize

    query_tokens = set(tokenize(query + " " + context))

    for result in results:
        # Base score from existing relevance
        base_score = result.get("relevance", 0.5)

        # Source priority multiplier
        source_weights = {
            "learning": 1.3,
            "memory_chain": 1.0,
            "qube_profile": 0.9,
            "owner_info": 0.8,
            "qube_locker": 0.7
        }
        source = result.get("source", "memory_chain")
        source_mult = source_weights.get(source, 1.0)

        # Keyword matching boost
        content = str(result.get("content", "")).lower()
        content_tokens = set(tokenize(content))
        overlap = len(query_tokens & content_tokens)
        keyword_boost = min(overlap * 0.1, 0.3)

        # Final score
        result["score"] = base_score * source_mult + keyword_boost

    # Sort by score descending
    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return results


# =============================================================================
# PLANET 2: store_fact (Knowledge Storage)
# =============================================================================

STORE_FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "fact": {
            "type": "string",
            "description": "The fact to store"
        },
        "subject": {
            "type": "string",
            "description": "What or who the fact is about"
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Confidence level 0-100 (default: 100)"
        }
    },
    "required": ["fact", "subject"]
}

STORE_FACT_DEFINITION = ToolDefinition(
    name="store_fact",
    description="Store a specific fact about a subject. More structured than general store_knowledge. Auto-redirects owner facts to Owner Info.",
    input_schema=STORE_FACT_SCHEMA,
    category="memory_recall"
)


async def store_fact(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store a specific fact about a subject.

    More structured than general store_knowledge - includes subject tagging
    and entity indexing.

    Args:
        qube: Qube instance
        params: {
            fact: str - The fact to store
            subject: str - What/who it's about
            confidence: int - 0-100 (default: 100)
        }

    Returns:
        Dict with success status, stored fact, block_id
    """
    fact = params.get("fact")
    subject = params.get("subject")

    if not fact or not subject:
        return {"success": False, "error": "Both fact and subject are required"}

    confidence = params.get("confidence", 100)

    # Auto-redirect: Owner facts go to Owner Info
    if is_owner_fact(subject) or is_owner_fact(fact):
        return await redirect_to_owner_info(qube, f"{subject}: {fact}")

    try:
        # Use store_knowledge with fact category
        result = await store_knowledge(qube, {
            "knowledge": f"{subject}: {fact}",
            "category": "fact",
            "source": "owner",
            "confidence": confidence
        })

        if result.get("success"):
            # Add subject to entity index
            result["subject"] = subject
            result["fact"] = fact

        return result

    except Exception as e:
        logger.error("store_fact_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Failed to store fact: {str(e)}"}


# =============================================================================
# PLANET 3: tag_memory (Memory Organization)
# =============================================================================

TAG_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id": {
            "type": "integer",
            "description": "Block number of the memory to tag"
        },
        "query": {
            "type": "string",
            "description": "Search query to find the memory (if memory_id not provided)"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags to add to the memory"
        }
    },
    "required": ["tags"]
}

TAG_MEMORY_DEFINITION = ToolDefinition(
    name="tag_memory",
    description="Add tags to a memory for better organization. Tags enable topic-based retrieval.",
    input_schema=TAG_MEMORY_SCHEMA,
    category="memory_recall"
)


async def tag_memory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add tags to a memory for better organization.

    Tags enable topic-based retrieval and organization.

    Args:
        qube: Qube instance
        params: {
            memory_id: int - Block number (optional if query provided)
            query: str - Search to find memory (optional if memory_id provided)
            tags: List[str] - Tags to add
        }

    Returns:
        Dict with success status, tagged memory, applied tags
    """
    memory_id = params.get("memory_id")
    query = params.get("query")
    tags = params.get("tags", [])

    if not tags:
        return {"success": False, "error": "Tags list is required"}

    # Find memory if query provided
    if query and not memory_id:
        try:
            from ai.tools.memory_search import intelligent_memory_search
            results = await intelligent_memory_search(qube=qube, query=query, limit=1)
            if results:
                memory_id = results[0].get("block_number")
            else:
                return {"success": False, "error": "Memory not found for query"}
        except Exception as e:
            return {"success": False, "error": f"Search failed: {str(e)}"}

    if not memory_id:
        return {"success": False, "error": "Either memory_id or query is required"}

    try:
        # Get the memory block
        block = qube.memory_chain.get_block(memory_id)

        # Add tags to block metadata
        # Tags are stored in a separate index for efficiency
        if not hasattr(qube, '_tag_index'):
            qube._tag_index = {}

        # Update tag index
        for tag in tags:
            if tag not in qube._tag_index:
                qube._tag_index[tag] = set()
            qube._tag_index[tag].add(memory_id)

        logger.info(
            "memory_tagged",
            memory_id=memory_id,
            tags=tags
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "tags_added": tags,
            "message": f"Tagged memory with: {', '.join(tags)}"
        }

    except Exception as e:
        logger.error("tag_memory_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Failed to tag memory: {str(e)}"}


# =============================================================================
# PLANET 4: synthesize_knowledge (Knowledge Synthesis)
# =============================================================================

SYNTHESIZE_KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic to synthesize knowledge about"
        },
        "memory_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Specific memory block numbers to synthesize (optional)"
        },
        "depth": {
            "type": "string",
            "enum": ["shallow", "deep"],
            "description": "Analysis depth: shallow (5 memories) or deep (20 memories)"
        }
    },
    "required": ["topic"]
}

SYNTHESIZE_KNOWLEDGE_DEFINITION = ToolDefinition(
    name="synthesize_knowledge",
    description="Synthesize knowledge from multiple memories on a topic. Combines information to generate new understanding.",
    input_schema=SYNTHESIZE_KNOWLEDGE_SCHEMA,
    category="memory_recall"
)


async def synthesize_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize knowledge from multiple memories.

    Combines information to generate new understanding. Creates a new
    LEARNING block with type 'synthesis'.

    Args:
        qube: Qube instance
        params: {
            topic: str - Topic to synthesize about
            memory_ids: List[int] - Specific memories (optional)
            depth: str - shallow or deep (default: shallow)
        }

    Returns:
        Dict with synthesis, source memories, new block_id
    """
    from ai.tools.memory_search import intelligent_memory_search

    topic = params.get("topic")
    if not topic:
        return {"success": False, "error": "Topic is required"}

    memory_ids = params.get("memory_ids", [])
    depth = params.get("depth", "shallow")
    limit = 20 if depth == "deep" else 5

    try:
        # Gather relevant memories
        if memory_ids:
            memories = []
            for mid in memory_ids:
                try:
                    block = qube.memory_chain.get_block(mid)
                    memories.append(block.to_dict())
                except:
                    pass
        else:
            memories = await intelligent_memory_search(
                qube=qube,
                query=topic,
                limit=limit
            )

        if not memories:
            return {
                "success": False,
                "error": f"No memories found for topic: {topic}"
            }

        # Generate synthesis using AI
        synthesis = await generate_synthesis(qube, memories, topic, depth)

        # Store the synthesis as new LEARNING block
        result = await store_knowledge(qube, {
            "knowledge": synthesis,
            "category": "insight",
            "source": "self",
            "confidence": 85
        })

        if result.get("success"):
            result["topic"] = topic
            result["synthesis"] = synthesis
            result["sources_used"] = len(memories)
            result["source_ids"] = [m.get("block_number") for m in memories if "block_number" in m]

        return result

    except Exception as e:
        logger.error("synthesize_knowledge_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Synthesis failed: {str(e)}"}


async def generate_synthesis(qube, memories: List[Dict], topic: str, depth: str) -> str:
    """
    Generate a synthesis from multiple memories using AI.

    Uses the Qube's current AI model to combine and analyze memories.
    """
    # Build context from memories
    memory_texts = []
    for i, mem in enumerate(memories[:10]):  # Limit context size
        content = mem.get("content", {})
        if isinstance(content, dict):
            text = content.get("knowledge", content.get("fact", content.get("message", str(content))))
        else:
            text = str(content)
        memory_texts.append(f"{i+1}. {text[:200]}")

    context = "\n".join(memory_texts)

    # Generate synthesis (simple version - production would use full AI call)
    synthesis = f"Synthesis of {len(memories)} memories about '{topic}':\n"
    synthesis += f"Based on the available information, the key points are:\n"

    # Extract key themes
    all_text = " ".join(memory_texts)
    topics = extract_topics(all_text)
    synthesis += f"- Key themes: {', '.join(topics)}\n"
    synthesis += f"- Analysis depth: {depth}\n"
    synthesis += f"- Sources analyzed: {len(memories)}"

    return synthesis


# =============================================================================
# PLANET 5: create_summary (Documentation)
# =============================================================================

CREATE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic to summarize"
        },
        "time_range": {
            "type": "string",
            "description": "Time filter: 'today', 'last week', 'last month', etc."
        },
        "format": {
            "type": "string",
            "enum": ["brief", "detailed"],
            "description": "Summary format: brief (1 paragraph) or detailed (sections)"
        }
    },
    "required": ["topic"]
}

CREATE_SUMMARY_DEFINITION = ToolDefinition(
    name="create_summary",
    description="Create a summary of memories on a topic. Stores the summary in Qube Locker for future reference.",
    input_schema=CREATE_SUMMARY_SCHEMA,
    category="memory_recall"
)


async def create_summary(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of memories on a topic.

    Compresses knowledge into digestible form and stores in Qube Locker.

    Args:
        qube: Qube instance
        params: {
            topic: str - Topic to summarize
            time_range: str - Time filter (optional)
            format: str - brief or detailed (default: brief)
        }

    Returns:
        Dict with summary content, memories used, storage location
    """
    from ai.tools.memory_search import intelligent_memory_search, parse_temporal_reference

    topic = params.get("topic")
    if not topic:
        return {"success": False, "error": "Topic is required"}

    time_range = params.get("time_range")
    format_type = params.get("format", "brief")

    try:
        # Gather relevant memories
        time_filter = parse_temporal_reference(time_range) if time_range else None
        memories = await intelligent_memory_search(
            qube=qube,
            query=topic,
            time_filter=time_filter,
            limit=20
        )

        if not memories:
            return {
                "success": False,
                "error": f"No memories found for topic: {topic}"
            }

        # Generate summary
        summary = await generate_summary(qube, memories, topic, format_type)

        # Store in Qube Locker
        stored_path = None
        if hasattr(qube, 'locker') and qube.locker:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            stored_path = await qube.locker.store(
                category="personal/summaries",
                name=f"summary_{topic.replace(' ', '_')}_{timestamp}",
                content=summary,
                metadata={"topic": topic, "memories_used": len(memories)}
            )

        return {
            "success": True,
            "topic": topic,
            "summary": summary,
            "memories_used": len(memories),
            "format": format_type,
            "stored_in_locker": stored_path is not None,
            "locker_path": stored_path
        }

    except Exception as e:
        logger.error("create_summary_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Summary creation failed: {str(e)}"}


async def generate_summary(qube, memories: List[Dict], topic: str, format_type: str) -> str:
    """
    Generate a summary from memories.

    Brief: Single paragraph
    Detailed: Multiple sections
    """
    # Extract content from memories
    contents = []
    for mem in memories:
        content = mem.get("content", {})
        if isinstance(content, dict):
            text = content.get("knowledge", content.get("fact", content.get("message", "")))
        else:
            text = str(content)
        if text:
            contents.append(text[:300])

    if format_type == "brief":
        summary = f"Summary of '{topic}':\n\n"
        summary += f"Based on {len(memories)} related memories, "
        summary += "the key information includes: "
        summary += "; ".join(contents[:3]) + "..."
    else:
        summary = f"# Summary: {topic}\n\n"
        summary += f"## Overview\n"
        summary += f"This summary covers {len(memories)} memories related to '{topic}'.\n\n"
        summary += f"## Key Points\n"
        for i, content in enumerate(contents[:5], 1):
            summary += f"{i}. {content}\n"
        summary += f"\n## Insights\n"
        topics = extract_topics(" ".join(contents))
        summary += f"Key themes: {', '.join(topics)}\n"

    return summary
```

---

## Task 5.5: Implement Moon Tools

### Continue in `ai/tools/memory_tools.py`

```python
# =============================================================================
# MOON TOOLS
# =============================================================================

# -----------------------------------------------------------------------------
# Moon 1.1: keyword_search
# -----------------------------------------------------------------------------

KEYWORD_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Keywords to search for"
        },
        "match_all": {
            "type": "boolean",
            "description": "Require all keywords (AND) or any keyword (OR)"
        }
    },
    "required": ["keywords"]
}

KEYWORD_SEARCH_DEFINITION = ToolDefinition(
    name="keyword_search",
    description="Search for exact keyword matches across all storage systems. Fast, precise lookup.",
    input_schema=KEYWORD_SEARCH_SCHEMA,
    category="memory_recall"
)


async def keyword_search(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for exact keyword matches.

    Args:
        qube: Qube instance
        params: {
            keywords: List[str] - Keywords to search
            match_all: bool - AND mode (default: False = OR mode)
        }

    Returns:
        Dict with matching results
    """
    from ai.tools.memory_search import tokenize

    keywords = params.get("keywords", [])
    if not keywords:
        return {"success": False, "error": "Keywords list is required"}

    match_all = params.get("match_all", False)

    try:
        results = []
        keywords_lower = [k.lower() for k in keywords]

        # Search all permanent blocks
        for block_num in qube.memory_chain.block_index.keys():
            try:
                block = qube.memory_chain.get_block(block_num)
                content = block.content or {}

                # Convert content to searchable text
                text = json.dumps(content).lower()
                tokens = set(tokenize(text))

                # Check keyword matches
                if match_all:
                    matches = all(any(k in token for token in tokens) for k in keywords_lower)
                else:
                    matches = any(any(k in token for token in tokens) for k in keywords_lower)

                if matches:
                    results.append({
                        "block_number": block.block_number,
                        "block_type": block.block_type,
                        "content_preview": str(content)[:200],
                        "timestamp": block.timestamp
                    })

            except Exception:
                continue

        return {
            "success": True,
            "keywords": keywords,
            "match_all": match_all,
            "results": results[:20],
            "count": len(results)
        }

    except Exception as e:
        logger.error("keyword_search_failed", error=str(e))
        return {"success": False, "error": f"Keyword search failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 1.2: semantic_search
# -----------------------------------------------------------------------------

SEMANTIC_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "concept": {
            "type": "string",
            "description": "The concept or meaning to search for"
        },
        "similarity_threshold": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Minimum similarity score 0-1 (default: 0.7)"
        }
    },
    "required": ["concept"]
}

SEMANTIC_SEARCH_DEFINITION = ToolDefinition(
    name="semantic_search",
    description="Search by meaning using vector embeddings. Finds conceptually related items even without keyword matches.",
    input_schema=SEMANTIC_SEARCH_SCHEMA,
    category="memory_recall"
)


async def semantic_search(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search by meaning using vector embeddings.

    Uses FAISS similarity search to find conceptually related memories.

    Args:
        qube: Qube instance
        params: {
            concept: str - The concept to search for
            similarity_threshold: float - Min similarity 0-1 (default: 0.7)
        }

    Returns:
        Dict with semantically similar results
    """
    concept = params.get("concept")
    if not concept:
        return {"success": False, "error": "Concept is required"}

    threshold = params.get("similarity_threshold", 0.7)

    try:
        if not hasattr(qube, 'semantic_search') or not qube.semantic_search:
            return {
                "success": False,
                "error": "Semantic search not initialized"
            }

        # Use FAISS semantic search
        raw_results = qube.semantic_search.search(
            query=concept,
            top_k=20
        )

        # Filter by threshold and enrich results
        results = []
        for block_num, similarity in raw_results:
            if similarity >= threshold:
                try:
                    block = qube.memory_chain.get_block(block_num)
                    results.append({
                        "block_number": block_num,
                        "similarity": round(similarity, 3),
                        "block_type": block.block_type,
                        "content_preview": str(block.content)[:200] if block.content else "",
                        "timestamp": block.timestamp
                    })
                except:
                    continue

        return {
            "success": True,
            "concept": concept,
            "threshold": threshold,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error("semantic_search_failed", error=str(e))
        return {"success": False, "error": f"Semantic search failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 1.3: search_memory (Filtered Search)
# -----------------------------------------------------------------------------

SEARCH_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query"
        },
        "filters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sources to search: learning, memory_chain, qube_profile, owner_info, qube_locker"
                },
                "block_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Block types to include: MESSAGE, ACTION, LEARNING, etc."
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date (ISO format or natural language)"
                },
                "date_to": {
                    "type": "string",
                    "description": "End date (ISO format or natural language)"
                },
                "topic": {
                    "type": "string",
                    "description": "Filter by topic tag"
                }
            },
            "description": "Filters to apply"
        }
    },
    "required": ["query"]
}

SEARCH_MEMORY_DEFINITION = ToolDefinition(
    name="search_memory",
    description="Advanced search with filters for source, type, date, and topic. More control than universal recall.",
    input_schema=SEARCH_MEMORY_SCHEMA,
    category="memory_recall"
)


async def search_memory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced filtered search.

    Args:
        qube: Qube instance
        params: {
            query: str - Search query
            filters: {
                source: List[str] - Sources to search
                block_types: List[str] - Block types to include
                date_from: str - Start date
                date_to: str - End date
                topic: str - Topic tag filter
            }
        }

    Returns:
        Dict with filtered results
    """
    from ai.tools.memory_search import intelligent_memory_search, parse_temporal_reference

    query = params.get("query")
    if not query:
        return {"success": False, "error": "Query is required"}

    filters = params.get("filters", {})
    sources = filters.get("source", ["all"])
    block_types = filters.get("block_types")
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    topic = filters.get("topic")

    try:
        # Build time filter
        time_filter = None
        if date_from:
            start = parse_temporal_reference(date_from)
            end = parse_temporal_reference(date_to) if date_to else None
            if start:
                time_filter = (start[0], end[1] if end else None)

        # Search with filters
        results = await intelligent_memory_search(
            qube=qube,
            query=query,
            block_types=block_types,
            time_filter=time_filter,
            limit=30
        )

        # Filter by topic if specified
        if topic and hasattr(qube, '_tag_index'):
            tagged_blocks = qube._tag_index.get(topic, set())
            results = [r for r in results if r.get("block_number") in tagged_blocks]

        # Filter by sources if not "all"
        if sources != ["all"]:
            # Apply source filtering based on block type mapping
            source_block_types = {
                "learning": ["LEARNING"],
                "memory_chain": ["MESSAGE", "ACTION", "SUMMARY", "GAME"],
                "qube_profile": [],  # Handled separately
                "owner_info": [],
                "qube_locker": []
            }
            allowed_types = set()
            for src in sources:
                allowed_types.update(source_block_types.get(src, []))
            if allowed_types:
                results = [r for r in results if r.get("block_type") in allowed_types]

        return {
            "success": True,
            "query": query,
            "filters": filters,
            "sources_searched": sources,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error("search_memory_failed", error=str(e))
        return {"success": False, "error": f"Filtered search failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 2.1: record_skill (Procedures)
# -----------------------------------------------------------------------------

RECORD_SKILL_SCHEMA = {
    "type": "object",
    "properties": {
        "skill_name": {
            "type": "string",
            "description": "Name of the skill/procedure"
        },
        "steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Step-by-step instructions"
        },
        "tips": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Additional tips or notes"
        }
    },
    "required": ["skill_name", "steps"]
}

RECORD_SKILL_DEFINITION = ToolDefinition(
    name="record_skill",
    description="Record procedural knowledge - how to do something. Stores step-by-step instructions for future reference.",
    input_schema=RECORD_SKILL_SCHEMA,
    category="memory_recall"
)


async def record_skill(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record procedural knowledge.

    Args:
        qube: Qube instance
        params: {
            skill_name: str - Name of the procedure
            steps: List[str] - Step-by-step instructions
            tips: List[str] - Additional tips (optional)
        }

    Returns:
        Dict with stored procedure details
    """
    skill_name = params.get("skill_name")
    steps = params.get("steps", [])
    tips = params.get("tips", [])

    if not skill_name or not steps:
        return {"success": False, "error": "Skill name and steps are required"}

    try:
        # Store as procedure type
        result = await store_knowledge(qube, {
            "knowledge": f"How to: {skill_name}",
            "category": "procedure",
            "source": "self",
            "steps": steps,
            "tips": tips,
            "skill_name": skill_name
        })

        if result.get("success"):
            result["skill_name"] = skill_name
            result["steps_count"] = len(steps)
            result["message"] = f"I now know how to: {skill_name}"

        return result

    except Exception as e:
        logger.error("record_skill_failed", error=str(e))
        return {"success": False, "error": f"Failed to record skill: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 3.1: add_tags (Topic Tagging)
# -----------------------------------------------------------------------------

ADD_TAGS_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id": {
            "type": "integer",
            "description": "Block number of the memory"
        },
        "auto_generate": {
            "type": "boolean",
            "description": "Auto-generate tags using AI (default: true)"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Manual tags to add (if not auto-generating)"
        }
    },
    "required": ["memory_id"]
}

ADD_TAGS_DEFINITION = ToolDefinition(
    name="add_tags",
    description="Auto-generate and add topic tags to a memory. Uses AI to identify relevant topics.",
    input_schema=ADD_TAGS_SCHEMA,
    category="memory_recall"
)


async def add_tags(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-generate or add tags to a memory.

    Args:
        qube: Qube instance
        params: {
            memory_id: int - Block number
            auto_generate: bool - Use AI to generate tags (default: True)
            tags: List[str] - Manual tags if not auto-generating
        }

    Returns:
        Dict with applied tags
    """
    memory_id = params.get("memory_id")
    if memory_id is None:
        return {"success": False, "error": "Memory ID is required"}

    auto_generate = params.get("auto_generate", True)
    manual_tags = params.get("tags", [])

    try:
        # Get memory content
        block = qube.memory_chain.get_block(memory_id)
        content = block.content or {}

        # Generate or use provided tags
        if auto_generate:
            text = json.dumps(content)
            tags = extract_topics(text)
        else:
            tags = manual_tags

        if not tags:
            return {"success": False, "error": "No tags generated or provided"}

        # Apply tags using tag_memory
        result = await tag_memory(qube, {
            "memory_id": memory_id,
            "tags": tags
        })

        if result.get("success"):
            result["auto_generated"] = auto_generate

        return result

    except Exception as e:
        logger.error("add_tags_failed", error=str(e))
        return {"success": False, "error": f"Failed to add tags: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 3.2: link_memories
# -----------------------------------------------------------------------------

LINK_MEMORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id_1": {
            "type": "integer",
            "description": "First memory block number"
        },
        "memory_id_2": {
            "type": "integer",
            "description": "Second memory block number"
        },
        "relationship": {
            "type": "string",
            "description": "Type of relationship: related_to, follows, contradicts, supports, etc."
        }
    },
    "required": ["memory_id_1", "memory_id_2"]
}

LINK_MEMORIES_DEFINITION = ToolDefinition(
    name="link_memories",
    description="Create a link between two related memories. Enables graph-based memory traversal.",
    input_schema=LINK_MEMORIES_SCHEMA,
    category="memory_recall"
)


async def link_memories(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a link between related memories.

    Args:
        qube: Qube instance
        params: {
            memory_id_1: int - First block number
            memory_id_2: int - Second block number
            relationship: str - Relationship type (default: related_to)
        }

    Returns:
        Dict with link confirmation
    """
    memory_id_1 = params.get("memory_id_1")
    memory_id_2 = params.get("memory_id_2")
    relationship = params.get("relationship", "related_to")

    if memory_id_1 is None or memory_id_2 is None:
        return {"success": False, "error": "Both memory IDs are required"}

    try:
        # Verify both memories exist
        block1 = qube.memory_chain.get_block(memory_id_1)
        block2 = qube.memory_chain.get_block(memory_id_2)

        # Create link in memory graph
        if not hasattr(qube, '_memory_links'):
            qube._memory_links = {}

        # Bidirectional links
        if memory_id_1 not in qube._memory_links:
            qube._memory_links[memory_id_1] = []
        if memory_id_2 not in qube._memory_links:
            qube._memory_links[memory_id_2] = []

        qube._memory_links[memory_id_1].append({
            "target": memory_id_2,
            "relationship": relationship
        })
        qube._memory_links[memory_id_2].append({
            "target": memory_id_1,
            "relationship": f"inverse_{relationship}"
        })

        logger.info(
            "memories_linked",
            id1=memory_id_1,
            id2=memory_id_2,
            relationship=relationship
        )

        return {
            "success": True,
            "linked": [memory_id_1, memory_id_2],
            "relationship": relationship,
            "message": f"Memories linked as '{relationship}'"
        }

    except Exception as e:
        logger.error("link_memories_failed", error=str(e))
        return {"success": False, "error": f"Failed to link memories: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 4.1: find_patterns
# -----------------------------------------------------------------------------

FIND_PATTERNS_SCHEMA = {
    "type": "object",
    "properties": {
        "scope": {
            "type": "string",
            "description": "Scope: topic name, time range like 'last week', or 'all'"
        },
        "pattern_type": {
            "type": "string",
            "enum": ["behavioral", "topical", "temporal", "all"],
            "description": "Type of patterns to look for"
        }
    }
}

FIND_PATTERNS_DEFINITION = ToolDefinition(
    name="find_patterns",
    description="Find recurring patterns across memories. Identifies trends, habits, and recurring themes.",
    input_schema=FIND_PATTERNS_SCHEMA,
    category="memory_recall"
)


async def find_patterns(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find recurring patterns in memories.

    Args:
        qube: Qube instance
        params: {
            scope: str - Topic, time range, or 'all'
            pattern_type: str - behavioral, topical, temporal, all
        }

    Returns:
        Dict with discovered patterns
    """
    from ai.tools.memory_search import intelligent_memory_search
    from collections import Counter

    scope = params.get("scope", "all")
    pattern_type = params.get("pattern_type", "all")

    try:
        # Gather memories based on scope
        if scope == "all":
            # Get recent memories
            memories = []
            block_nums = sorted(qube.memory_chain.block_index.keys(), reverse=True)[:100]
            for bn in block_nums:
                try:
                    block = qube.memory_chain.get_block(bn)
                    memories.append(block.to_dict())
                except:
                    continue
        else:
            memories = await intelligent_memory_search(
                qube=qube,
                query=scope,
                limit=50
            )

        patterns = []

        # Topical patterns - recurring themes
        if pattern_type in ["topical", "all"]:
            all_text = " ".join([str(m.get("content", "")) for m in memories])
            topics = extract_topics(all_text)
            topic_counts = Counter(topics)
            for topic, count in topic_counts.most_common(5):
                if count >= 2:
                    patterns.append({
                        "type": "topical",
                        "pattern": f"Recurring topic: {topic}",
                        "occurrences": count,
                        "confidence": min(count * 10, 100)
                    })

        # Temporal patterns - time-based trends
        if pattern_type in ["temporal", "all"]:
            # Group by hour of day
            hours = Counter()
            for m in memories:
                ts = m.get("timestamp")
                if ts:
                    hour = datetime.fromtimestamp(ts).hour
                    hours[hour] += 1

            if hours:
                peak_hour = hours.most_common(1)[0]
                patterns.append({
                    "type": "temporal",
                    "pattern": f"Most active at hour {peak_hour[0]:02d}:00",
                    "occurrences": peak_hour[1],
                    "confidence": 70
                })

        # Behavioral patterns - action types
        if pattern_type in ["behavioral", "all"]:
            actions = Counter()
            for m in memories:
                if m.get("block_type") == "ACTION":
                    content = m.get("content", {})
                    action_type = content.get("action_type", "unknown")
                    actions[action_type] += 1

            for action, count in actions.most_common(3):
                if count >= 2:
                    patterns.append({
                        "type": "behavioral",
                        "pattern": f"Frequent action: {action}",
                        "occurrences": count,
                        "confidence": min(count * 15, 95)
                    })

        return {
            "success": True,
            "scope": scope,
            "pattern_type": pattern_type,
            "patterns": patterns,
            "pattern_count": len(patterns),
            "memories_analyzed": len(memories)
        }

    except Exception as e:
        logger.error("find_patterns_failed", error=str(e))
        return {"success": False, "error": f"Pattern finding failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 4.2: generate_insight
# -----------------------------------------------------------------------------

GENERATE_INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "focus_area": {
            "type": "string",
            "description": "Area to generate insights about"
        },
        "creativity": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Creativity level affects diversity of connections made"
        }
    },
    "required": ["focus_area"]
}

GENERATE_INSIGHT_DEFINITION = ToolDefinition(
    name="generate_insight",
    description="Generate novel insights by connecting disparate memories. Creative knowledge synthesis.",
    input_schema=GENERATE_INSIGHT_SCHEMA,
    category="memory_recall"
)


async def generate_insight(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate insights by connecting memories.

    Args:
        qube: Qube instance
        params: {
            focus_area: str - Topic to focus on
            creativity: str - low, medium, high
        }

    Returns:
        Dict with generated insights
    """
    from ai.tools.memory_search import intelligent_memory_search

    focus_area = params.get("focus_area")
    if not focus_area:
        return {"success": False, "error": "Focus area is required"}

    creativity = params.get("creativity", "medium")
    diversity_weight = {"low": 0.3, "medium": 0.6, "high": 0.9}[creativity]

    try:
        # Get diverse sample of memories
        memories = await intelligent_memory_search(
            qube=qube,
            query=focus_area,
            limit=int(20 * (1 + diversity_weight))
        )

        if not memories:
            return {
                "success": False,
                "error": f"No memories found for: {focus_area}"
            }

        insights = []

        # Generate insights by finding connections
        all_topics = []
        for m in memories:
            content = m.get("content", {})
            text = str(content)
            topics = extract_topics(text)
            all_topics.extend(topics)

        # Find unexpected connections
        topic_counts = Counter(all_topics)
        common_topics = [t for t, c in topic_counts.most_common(3)]

        insight = {
            "insight": f"Analysis of '{focus_area}' reveals connections to: {', '.join(common_topics)}",
            "focus_area": focus_area,
            "connections": common_topics,
            "confidence": 0.75 if creativity == "medium" else 0.6,
            "creativity_level": creativity
        }
        insights.append(insight)

        # Store high-confidence insights
        stored_count = 0
        for ins in insights:
            if ins["confidence"] > 0.7:
                await store_knowledge(qube, {
                    "knowledge": ins["insight"],
                    "category": "insight",
                    "source": "self",
                    "confidence": int(ins["confidence"] * 100)
                })
                stored_count += 1

        return {
            "success": True,
            "focus_area": focus_area,
            "insights": insights,
            "stored_count": stored_count,
            "memories_analyzed": len(memories)
        }

    except Exception as e:
        logger.error("generate_insight_failed", error=str(e))
        return {"success": False, "error": f"Insight generation failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 5.1: write_summary
# -----------------------------------------------------------------------------

WRITE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic to summarize"
        },
        "sections": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sections to include: overview, key_points, timeline, insights"
        }
    },
    "required": ["topic"]
}

WRITE_SUMMARY_DEFINITION = ToolDefinition(
    name="write_summary",
    description="Write a detailed, structured summary with multiple sections. More comprehensive than create_summary.",
    input_schema=WRITE_SUMMARY_SCHEMA,
    category="memory_recall"
)


async def write_summary(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write a detailed structured summary.

    Args:
        qube: Qube instance
        params: {
            topic: str - Topic to summarize
            sections: List[str] - Sections to include
        }

    Returns:
        Dict with structured document
    """
    from ai.tools.memory_search import intelligent_memory_search

    topic = params.get("topic")
    if not topic:
        return {"success": False, "error": "Topic is required"}

    sections = params.get("sections", ["overview", "key_points", "timeline", "insights"])

    try:
        # Gather memories
        memories = await intelligent_memory_search(
            qube=qube,
            query=topic,
            limit=50
        )

        if not memories:
            return {
                "success": False,
                "error": f"No memories found for: {topic}"
            }

        # Generate each section
        document = f"# Detailed Summary: {topic}\n\n"
        generated_sections = {}

        for section in sections:
            if section == "overview":
                generated_sections["overview"] = f"This document covers {len(memories)} memories related to '{topic}'."
            elif section == "key_points":
                points = []
                for m in memories[:5]:
                    content = m.get("content", {})
                    if isinstance(content, dict):
                        text = content.get("knowledge", content.get("message", str(content)[:100]))
                    else:
                        text = str(content)[:100]
                    points.append(f"- {text}")
                generated_sections["key_points"] = "\n".join(points)
            elif section == "timeline":
                timeline = []
                sorted_mems = sorted(memories, key=lambda x: x.get("timestamp", 0))
                for m in sorted_mems[:5]:
                    ts = m.get("timestamp")
                    if ts:
                        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                        timeline.append(f"- {dt}: {m.get('block_type', 'Event')}")
                generated_sections["timeline"] = "\n".join(timeline) if timeline else "No timeline data"
            elif section == "insights":
                topics = extract_topics(" ".join([str(m.get("content", "")) for m in memories]))
                generated_sections["insights"] = f"Key themes: {', '.join(topics)}"

        # Build document
        for section_name, content in generated_sections.items():
            document += f"## {section_name.replace('_', ' ').title()}\n{content}\n\n"

        # Store in locker
        stored_path = None
        if hasattr(qube, 'locker') and qube.locker:
            stored_path = await qube.locker.store(
                category="personal/summaries",
                name=f"detailed_{topic.replace(' ', '_')}",
                content=document
            )

        return {
            "success": True,
            "topic": topic,
            "sections": list(generated_sections.keys()),
            "document": document,
            "stored_path": stored_path
        }

    except Exception as e:
        logger.error("write_summary_failed", error=str(e))
        return {"success": False, "error": f"Summary writing failed: {str(e)}"}


# -----------------------------------------------------------------------------
# Moon 5.2: export_knowledge
# -----------------------------------------------------------------------------

EXPORT_KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic to export knowledge about"
        },
        "format": {
            "type": "string",
            "enum": ["markdown", "json", "text"],
            "description": "Export format"
        },
        "include_sources": {
            "type": "boolean",
            "description": "Include source memory references"
        }
    },
    "required": ["topic"]
}

EXPORT_KNOWLEDGE_DEFINITION = ToolDefinition(
    name="export_knowledge",
    description="Export knowledge in portable formats (markdown, JSON, text). Enables sharing and backup.",
    input_schema=EXPORT_KNOWLEDGE_SCHEMA,
    category="memory_recall"
)


async def export_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Export knowledge in portable formats.

    Args:
        qube: Qube instance
        params: {
            topic: str - Topic to export
            format: str - markdown, json, text
            include_sources: bool - Include memory references
        }

    Returns:
        Dict with export file path and content
    """
    from ai.tools.memory_search import intelligent_memory_search

    topic = params.get("topic")
    if not topic:
        return {"success": False, "error": "Topic is required"}

    export_format = params.get("format", "markdown")
    include_sources = params.get("include_sources", True)

    try:
        # Gather all relevant knowledge
        memories = await intelligent_memory_search(
            qube=qube,
            query=topic,
            limit=100
        )

        # Filter for LEARNING blocks (facts, procedures, insights)
        learnings = [m for m in memories if m.get("block_type") == "LEARNING"]

        # Build export data
        export_data = {
            "topic": topic,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(learnings) + len(memories),
            "learnings": [],
            "memories": [] if include_sources else None
        }

        for m in learnings:
            content = m.get("content", {})
            export_data["learnings"].append({
                "type": content.get("learning_type", "unknown"),
                "content": content,
                "block_number": m.get("block_number"),
                "timestamp": m.get("timestamp")
            })

        if include_sources:
            for m in memories[:20]:  # Limit source references
                export_data["memories"].append({
                    "block_type": m.get("block_type"),
                    "block_number": m.get("block_number"),
                    "preview": str(m.get("content", ""))[:200]
                })

        # Format output
        if export_format == "json":
            output = json.dumps(export_data, indent=2)
            ext = "json"
        elif export_format == "markdown":
            output = f"# Knowledge Export: {topic}\n\n"
            output += f"Exported: {export_data['exported_at']}\n\n"
            output += f"## Learnings ({len(export_data['learnings'])})\n\n"
            for l in export_data["learnings"]:
                output += f"### {l['type'].title()}\n"
                output += f"{json.dumps(l['content'], indent=2)}\n\n"
            if include_sources and export_data.get("memories"):
                output += f"## Source Memories\n\n"
                for m in export_data["memories"]:
                    output += f"- Block {m['block_number']}: {m['preview'][:100]}...\n"
            ext = "md"
        else:  # text
            output = f"Knowledge Export: {topic}\n"
            output += "=" * 40 + "\n\n"
            for l in export_data["learnings"]:
                output += f"[{l['type']}] {l['content']}\n\n"
            ext = "txt"

        # Store export
        export_path = None
        if hasattr(qube, 'locker') and qube.locker:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            export_path = await qube.locker.store(
                category="exports",
                name=f"export_{topic.replace(' ', '_')}_{timestamp}.{ext}",
                content=output
            )

        return {
            "success": True,
            "topic": topic,
            "format": export_format,
            "export_path": export_path,
            "items_exported": len(export_data["learnings"]) + len(memories),
            "output_preview": output[:500] + "..." if len(output) > 500 else output
        }

    except Exception as e:
        logger.error("export_knowledge_failed", error=str(e))
        return {"success": False, "error": f"Export failed: {str(e)}"}
```

---

## Task 5.6: Memory Chain Enhancements

### File: `core/memory_chain.py`

Add these methods to the MemoryChain class (after line 438):

```python
    # ==========================================================================
    # PHASE 5: MEMORY & RECALL ENHANCEMENTS
    # ==========================================================================

    def get_blocks_by_type(
        self,
        block_type: str,
        limit: int = 50
    ) -> List[Block]:
        """
        Get blocks of a specific type.

        Args:
            block_type: BlockType value (e.g., "LEARNING", "MESSAGE")
            limit: Maximum blocks to return

        Returns:
            List of matching blocks, most recent first
        """
        results = []
        block_nums = sorted(self.block_index.keys(), reverse=True)

        for block_num in block_nums:
            if len(results) >= limit:
                break
            try:
                block = self.get_block(block_num)
                if block.block_type == block_type:
                    results.append(block)
            except Exception:
                continue

        return results

    def get_learning_blocks(
        self,
        learning_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Block]:
        """
        Get LEARNING blocks, optionally filtered by learning_type.

        Args:
            learning_type: Filter by type (fact, procedure, synthesis, insight)
            limit: Maximum blocks to return

        Returns:
            List of LEARNING blocks
        """
        learning_blocks = self.get_blocks_by_type("LEARNING", limit * 2)

        if learning_type:
            learning_blocks = [
                b for b in learning_blocks
                if b.content and b.content.get("learning_type") == learning_type
            ]

        return learning_blocks[:limit]

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> List[int]:
        """
        Search for block numbers by tags.

        Requires tag index to be maintained externally.

        Args:
            tags: Tags to search for
            match_all: Require all tags (AND) or any tag (OR)

        Returns:
            List of block numbers
        """
        # This method works with external tag index
        # Implementation delegates to the tag_index maintained by Qube
        raise NotImplementedError("Tag search requires external tag index")

    def get_recent_blocks(
        self,
        limit: int = 100,
        block_types: Optional[List[str]] = None
    ) -> List[Block]:
        """
        Get most recent blocks.

        Args:
            limit: Maximum blocks to return
            block_types: Filter by types (optional)

        Returns:
            List of blocks, most recent first
        """
        results = []
        block_nums = sorted(self.block_index.keys(), reverse=True)

        for block_num in block_nums:
            if len(results) >= limit:
                break
            try:
                block = self.get_block(block_num)
                if block_types is None or block.block_type in block_types:
                    results.append(block)
            except Exception:
                continue

        return results
```

---

## Task 5.7: Universal Search Integration

### File: `ai/tools/memory_search.py`

Add LEARNING to searchable block types (around line 400):

```python
# Add LEARNING to the default block types for intelligent_memory_search
SEARCHABLE_BLOCK_TYPES = ["MESSAGE", "ACTION", "SUMMARY", "GAME", "LEARNING"]
```

Update the `intelligent_memory_search` function to include LEARNING blocks (lines 385-519):

```python
async def intelligent_memory_search(
    qube,
    query: str,
    block_types: Optional[List[str]] = None,
    time_filter: Optional[Tuple[int, int]] = None,
    limit: int = 10,
    include_learning: bool = True  # NEW parameter
) -> List[Dict[str, Any]]:
    """
    5-layer hybrid memory search.

    Args:
        qube: Qube instance
        query: Search query
        block_types: Block types to search (default: all searchable)
        time_filter: (start_timestamp, end_timestamp) tuple
        limit: Max results
        include_learning: Include LEARNING blocks (default: True)

    Returns:
        List of matching blocks with scores
    """
    # Use default block types if not specified
    if block_types is None:
        block_types = SEARCHABLE_BLOCK_TYPES.copy()
        if not include_learning:
            block_types.remove("LEARNING")

    # ... rest of implementation unchanged
```

---

## Task 5.8: Update XP Routing

### File: `core/xp_router.py`

Add Memory & Recall tools to TOOL_TO_SKILL_MAPPING (add after existing mappings):

```python
# =============================================================================
# MEMORY & RECALL TOOL MAPPINGS
# =============================================================================

MEMORY_RECALL_TOOLS = {
    # Sun tool
    "store_knowledge": {
        "skill_id": "memory_recall",
        "xp_model": "standard",  # 5/2.5/0
        "category": "memory_recall"
    },

    # Planet tools
    "recall": {
        "skill_id": "memory_search",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "store_fact": {
        "skill_id": "knowledge_storage",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "tag_memory": {
        "skill_id": "memory_organization",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "synthesize_knowledge": {
        "skill_id": "knowledge_synthesis",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "create_summary": {
        "skill_id": "documentation",
        "xp_model": "standard",
        "category": "memory_recall"
    },

    # Moon tools
    "keyword_search": {
        "skill_id": "keyword_search_skill",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "semantic_search": {
        "skill_id": "semantic_search_skill",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "search_memory": {
        "skill_id": "filtered_search",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "record_skill": {
        "skill_id": "procedures",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "add_tags": {
        "skill_id": "topic_tagging",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "link_memories": {
        "skill_id": "memory_linking",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "find_patterns": {
        "skill_id": "pattern_recognition",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "generate_insight": {
        "skill_id": "insight_generation",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "write_summary": {
        "skill_id": "summary_writing",
        "xp_model": "standard",
        "category": "memory_recall"
    },
    "export_knowledge": {
        "skill_id": "knowledge_export",
        "xp_model": "standard",
        "category": "memory_recall"
    },
}

# Add to main mapping
TOOL_TO_SKILL_MAPPING.update(MEMORY_RECALL_TOOLS)
```

---

## Task 5.9: Frontend Integration

### File: `src/types/skills.ts`

Add Memory & Recall type definitions:

```typescript
// =============================================================================
// MEMORY & RECALL TYPES
// =============================================================================

export interface StoreKnowledgeParams {
  knowledge: string;
  category?: 'fact' | 'procedure' | 'insight';
  source?: 'self' | 'owner' | 'conversation' | 'research';
  confidence?: number;
}

export interface RecallParams {
  query: string;
  context?: string;
  time_range?: string;
  limit?: number;
}

export interface RecallResult {
  success: boolean;
  query: string;
  results: Array<{
    source: string;
    content: string;
    block_number?: number;
    relevance: number;
    score: number;
  }>;
  total_found: number;
  sources_searched: string[];
}

export interface StoreFactParams {
  fact: string;
  subject: string;
  confidence?: number;
}

export interface TagMemoryParams {
  memory_id?: number;
  query?: string;
  tags: string[];
}

export interface SynthesizeKnowledgeParams {
  topic: string;
  memory_ids?: number[];
  depth?: 'shallow' | 'deep';
}

export interface CreateSummaryParams {
  topic: string;
  time_range?: string;
  format?: 'brief' | 'detailed';
}

export interface KeywordSearchParams {
  keywords: string[];
  match_all?: boolean;
}

export interface SemanticSearchParams {
  concept: string;
  similarity_threshold?: number;
}

export interface SearchMemoryParams {
  query: string;
  filters?: {
    source?: string[];
    block_types?: string[];
    date_from?: string;
    date_to?: string;
    topic?: string;
  };
}

export interface RecordSkillParams {
  skill_name: string;
  steps: string[];
  tips?: string[];
}

export interface AddTagsParams {
  memory_id: number;
  auto_generate?: boolean;
  tags?: string[];
}

export interface LinkMemoriesParams {
  memory_id_1: number;
  memory_id_2: number;
  relationship?: string;
}

export interface FindPatternsParams {
  scope?: string;
  pattern_type?: 'behavioral' | 'topical' | 'temporal' | 'all';
}

export interface GenerateInsightParams {
  focus_area: string;
  creativity?: 'low' | 'medium' | 'high';
}

export interface WriteSummaryParams {
  topic: string;
  sections?: string[];
}

export interface ExportKnowledgeParams {
  topic: string;
  format?: 'markdown' | 'json' | 'text';
  include_sources?: boolean;
}

// Memory & Recall skill node IDs
export type MemoryRecallSkillId =
  | 'memory_recall'           // Sun
  | 'memory_search'           // Planet 1
  | 'knowledge_storage'       // Planet 2
  | 'memory_organization'     // Planet 3
  | 'knowledge_synthesis'     // Planet 4
  | 'documentation'           // Planet 5
  | 'keyword_search_skill'    // Moon 1.1
  | 'semantic_search_skill'   // Moon 1.2
  | 'filtered_search'         // Moon 1.3
  | 'procedures'              // Moon 2.1
  | 'topic_tagging'           // Moon 3.1
  | 'memory_linking'          // Moon 3.2
  | 'pattern_recognition'     // Moon 4.1
  | 'insight_generation'      // Moon 4.2
  | 'summary_writing'         // Moon 5.1
  | 'knowledge_export';       // Moon 5.2
```

---

## Task 5.10: Testing & Validation

### Test Checklist

```markdown
## Memory & Recall Testing Checklist

### 5.10.1 Block Type Tests
- [ ] LEARNING block can be created with `create_learning_block()`
- [ ] LEARNING block includes all required fields (learning_type, source_block, confidence)
- [ ] LEARNING blocks are properly indexed in semantic search
- [ ] LEARNING blocks appear in memory chain queries

### 5.10.2 Sun Tool Tests
- [ ] `store_knowledge` creates LEARNING block with correct type
- [ ] `store_knowledge` auto-redirects owner facts to Owner Info
- [ ] `store_knowledge` auto-redirects self facts to Qube Profile
- [ ] `store_knowledge` extracts topics and entities correctly
- [ ] `store_knowledge` awards 5 XP on success

### 5.10.3 Planet Tool Tests
- [ ] `recall` searches all 5 storage systems
- [ ] `recall` respects time_range filter
- [ ] `recall` scores and ranks results correctly
- [ ] `store_fact` creates structured fact LEARNING block
- [ ] `store_fact` updates entity index
- [ ] `tag_memory` adds tags to existing memories
- [ ] `tag_memory` can find memories by query
- [ ] `synthesize_knowledge` combines multiple memories
- [ ] `synthesize_knowledge` stores synthesis as new LEARNING block
- [ ] `create_summary` generates summary content
- [ ] `create_summary` stores in Qube Locker

### 5.10.4 Moon Tool Tests
- [ ] `keyword_search` finds exact matches
- [ ] `keyword_search` supports AND/OR modes
- [ ] `semantic_search` uses FAISS embeddings
- [ ] `semantic_search` respects similarity threshold
- [ ] `search_memory` applies all filter types
- [ ] `record_skill` stores procedural knowledge
- [ ] `add_tags` auto-generates topics
- [ ] `link_memories` creates bidirectional links
- [ ] `find_patterns` detects topical patterns
- [ ] `find_patterns` detects temporal patterns
- [ ] `generate_insight` creates novel connections
- [ ] `write_summary` generates structured documents
- [ ] `export_knowledge` supports all formats (md, json, txt)

### 5.10.5 Integration Tests
- [ ] XP trickle-up works: Moon → Planet → Sun
- [ ] All tools registered in ToolRegistry
- [ ] All tools appear in TOOL_TO_SKILL_MAPPING
- [ ] Qube Locker integration works for summaries/exports
- [ ] Semantic search indexes new LEARNING blocks
- [ ] Tag index persists across sessions
- [ ] Memory links persist across sessions

### 5.10.6 Edge Cases
- [ ] Empty query returns appropriate error
- [ ] Missing memory_id handled gracefully
- [ ] Large knowledge content truncated appropriately
- [ ] Circular memory links handled
- [ ] Duplicate tags deduplicated
- [ ] Export with no results returns error
```

---

## Files Modified Summary

| File | Action | Description |
|------|--------|-------------|
| `core/block.py` | MODIFY | Add LEARNING to BlockType enum (Phase 0), add `create_learning_block()` |
| `ai/tools/memory_tools.py` | CREATE | New file with all 16 Memory & Recall tool handlers |
| `ai/tools/handlers.py` | MODIFY | Update SKILL_CATEGORIES and SKILL_TREE with memory_recall |
| `core/memory_chain.py` | MODIFY | Add `get_blocks_by_type()`, `get_learning_blocks()`, `get_recent_blocks()` |
| `ai/tools/memory_search.py` | MODIFY | Add LEARNING to SEARCHABLE_BLOCK_TYPES |
| `core/xp_router.py` | MODIFY | Add MEMORY_RECALL_TOOLS mapping |
| `src/types/skills.ts` | MODIFY | Add TypeScript interfaces for all tools |

---

## Estimated Effort

| Task | Complexity | Estimated Hours |
|------|------------|-----------------|
| 5.1 Add LEARNING Block Type | Low | 1 (done in Phase 0) |
| 5.2 Update Skill Definitions | Medium | 2 |
| 5.3 Implement Sun Tool | Medium | 3 |
| 5.4 Implement Planet Tools | High | 8 |
| 5.5 Implement Moon Tools | High | 10 |
| 5.6 Memory Chain Enhancements | Medium | 3 |
| 5.7 Universal Search Integration | Low | 1 |
| 5.8 Update XP Routing | Low | 1 |
| 5.9 Frontend Integration | Medium | 3 |
| 5.10 Testing & Validation | Medium | 4 |
| **Total** | | **36 hours** |

---

## Dependencies

```
Phase 0 (Foundation)
├── Task 0.4: LEARNING Block Type
├── Task 0.6: XP Trickle-Up System
└── Task 0.12: Qube Locker

Phase 5 (Memory & Recall)
├── Task 5.1: Uses LEARNING from Phase 0
├── Task 5.3-5.5: All tool implementations
├── Task 5.6: Memory Chain enhancements
├── Task 5.7: Search integration
├── Task 5.8: XP routing
└── Task 5.9: Frontend types
```

---

## Notes

1. **Universal Search Priority**: Memory & Recall tools search in this priority order:
   - LEARNING blocks (explicit knowledge)
   - Memory Chain (MESSAGE, ACTION, SUMMARY, GAME)
   - Qube Profile (self-identity)
   - Owner Info (owner data, respects sensitivity)
   - Qube Locker (creative works)

2. **Auto-Redirect**: `store_knowledge` includes safety net for misplaced data:
   - Owner facts → Owner Info
   - Self facts → Qube Profile
   - General knowledge → LEARNING block

3. **Tag & Link Indices**: Tags and memory links are stored in memory (`_tag_index`, `_memory_links`) for the session. Consider persisting these to chain state for cross-session durability.

4. **Synthesis Quality**: The `synthesize_knowledge` and `generate_insight` tools use simplified synthesis logic. Production implementation should use full AI generation for higher quality output.
