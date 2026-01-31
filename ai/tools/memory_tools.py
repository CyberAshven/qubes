"""
Memory & Recall Tools - Phase 5 Implementation

The "librarian" Sun - manages ALL knowledge in the Qube's memory chain.
Searches, organizes, synthesizes, and documents knowledge.

Theme: Remember (Master Your Personal History)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from collections import Counter
import json
import re

from core.block import Block, BlockType, create_learning_block
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
    freq = Counter(tokens)

    # Return top 5 most frequent meaningful tokens as topics
    return [token for token, _ in freq.most_common(5)]


def extract_entities(text: str) -> List[str]:
    """
    Extract named entities from text.

    Simple pattern-based extraction for names, places, organizations.
    """
    # Find capitalized words (potential proper nouns)
    entities = []
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
        if qube.locker:
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
        profile = chain_state.get("qube_profile", {}) if hasattr(chain_state, 'get') else {}

        # Search each section
        for section in ["preferences", "traits", "opinions", "goals", "style", "interests"]:
            section_data = profile.get(section, {}) if profile else {}
            if isinstance(section_data, dict):
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
        owner_info = chain_state.get("owner_info", {}) if hasattr(chain_state, 'get') else {}

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

        # Generate synthesis
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
        if qube.locker:
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
        if qube.locker:
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
        if qube.locker:
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


# =============================================================================
# TOOL HANDLERS - exported for registration in handlers.py
# =============================================================================

MEMORY_TOOL_HANDLERS = {
    # Sun
    "store_knowledge": store_knowledge,
    # Planets
    "recall": recall,
    "store_fact": store_fact,
    "tag_memory": tag_memory,
    "synthesize_knowledge": synthesize_knowledge,
    "create_summary": create_summary,
    # Moons
    "keyword_search": keyword_search,
    "semantic_search": semantic_search,
    "search_memory": search_memory,
    "record_skill": record_skill,
    "add_tags": add_tags,
    "link_memories": link_memories,
    "find_patterns": find_patterns,
    "generate_insight": generate_insight,
    "write_summary": write_summary,
    "export_knowledge": export_knowledge,
}
