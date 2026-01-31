# Phase 1: AI Reasoning - Implementation Blueprint

**Document Version:** 1.0
**Based on:** SKILL_TREE_MASTER.md
**Theme:** Learning From Experience
**Prerequisites:** Phase 0 (Foundation) completed

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Prerequisites & Dependencies](#2-prerequisites--dependencies)
3. [Task 1.1: Update Skill Definitions](#3-task-11-update-skill-definitions)
4. [Task 1.2: Update TOOL_TO_SKILL_MAPPING](#4-task-12-update-tool_to_skill_mapping)
5. [Task 1.3: Implement Sun Tool - recall_similar](#5-task-13-implement-sun-tool---recall_similar)
6. [Task 1.4: Implement Pattern Recognition Planet](#6-task-14-implement-pattern-recognition-planet)
7. [Task 1.5: Implement Learning from Failure Planet](#7-task-15-implement-learning-from-failure-planet)
8. [Task 1.6: Implement Building on Success Planet](#8-task-16-implement-building-on-success-planet)
9. [Task 1.7: Implement Self-Reflection Planet](#9-task-17-implement-self-reflection-planet)
10. [Task 1.8: Implement Knowledge Synthesis Planet](#10-task-18-implement-knowledge-synthesis-planet)
11. [Task 1.9: Register All Tools](#11-task-19-register-all-tools)
12. [Task 1.10: Move describe_my_avatar to Creative Expression](#12-task-110-move-describe_my_avatar-to-creative-expression)
13. [Task 1.11: Frontend Synchronization](#13-task-111-frontend-synchronization)
14. [Task 1.12: LEARNING Block Integration](#14-task-112-learning-block-integration)
15. [Task 1.13: Testing & Validation](#15-task-113-testing--validation)
16. [Appendix A: Tool Summary Table](#appendix-a-tool-summary-table)
17. [Appendix B: File Reference](#appendix-b-file-reference)
18. [Appendix C: Helper Functions](#appendix-c-helper-functions)

---

## 1. Executive Summary

### Purpose

Phase 1 transforms the AI Reasoning category from generic prompt engineering skills into a powerful "Learning From Experience" system. The Qube analyzes its own memory chain to find patterns, learn from mistakes, build on successes, and synthesize knowledge over time.

### Theme: Learning From Experience

This phase leverages the unique blockchain-based memory that differentiates Qubes from stateless AI:
- **Pattern Recognition**: Finding analogies in past experience
- **Learning from Failure**: Analyzing mistakes to avoid repeating them
- **Building on Success**: Replicating what worked before
- **Self-Reflection**: Understanding own patterns and biases
- **Knowledge Synthesis**: Connecting disparate learnings into insights

### Tool Count

| Type | Count | Tools |
|------|-------|-------|
| Sun | 1 | `recall_similar` |
| Planets | 5 | `find_analogy`, `analyze_mistake`, `replicate_success`, `self_reflect`, `synthesize_learnings` |
| Moons | 8 | `detect_trend`, `quick_insight`, `find_root_cause`, `extract_success_factors`, `track_growth`, `detect_bias`, `cross_pollinate`, `reflect_on_topic` |
| **Total** | **14** | |

### Scope

| Metric | Before Phase 1 | After Phase 1 |
|--------|----------------|---------------|
| AI Reasoning Skills | 16 (old structure) | 14 (new structure) |
| AI Reasoning Tools | 1 (`describe_my_avatar`) | 14 (new tools) |
| `describe_my_avatar` Location | AI Reasoning | Creative Expression |
| Memory-Chain Tools | 0 | 14 |

### Current Codebase State (as of Jan 2026)

#### Existing AI Reasoning Skills (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current Sun tool**: `describe_my_avatar` (needs to move to Creative Expression)
- **Current Planets**: prompt_engineering, chain_of_thought, code_generation, analysis_critique, multistep_planning
- **Current Moons**: 10 moons across planets
- **Action**: Replace entire AI Reasoning skill tree with new memory-centric structure

#### Tool Mappings (`ai/skill_scanner.py:44-85`)
- **Current mappings** (to be replaced):
  ```python
  "think_step_by_step": "chain_of_thought"
  "self_critique": "analysis_critique"
  "explore_alternatives": "multistep_planning"
  ```
- **Target mappings** (new tools):
  ```python
  "recall_similar": "ai_reasoning"  # Sun
  "find_analogy": "pattern_recognition"
  "analyze_mistake": "learning_from_failure"
  # ... 11 more new tool mappings
  ```
- **Action**: Replace old mappings with new memory-centric tools

#### Sun Tool Change
- **Current**: `describe_my_avatar` earns AI Reasoning XP
- **Target**: `recall_similar` earns AI Reasoning XP
- **Note**: `describe_my_avatar` moves to Creative Expression (visual_design planet)

### Files Modified

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Replace all AI Reasoning skills |
| `ai/skill_scanner.py` | Add 14 new tool mappings, update `describe_my_avatar` |
| `ai/tools/handlers.py` | Add 14 new handler functions + helper functions |
| `ai/tools/registry.py` | Register 14 new tools |
| `qubes-gui/src/data/skillDefinitions.ts` | Replace all AI Reasoning definitions |

### Estimated Effort

| Task | Effort | Complexity |
|------|--------|------------|
| 1.1 Skill Definitions | 2 hours | Low |
| 1.2 Tool Mappings | 30 min | Low |
| 1.3 Sun Tool (recall_similar) | 2-3 hours | Medium |
| 1.4 Pattern Recognition (2 tools) | 3-4 hours | Medium |
| 1.5 Learning from Failure (2 tools) | 3-4 hours | Medium |
| 1.6 Building on Success (2 tools) | 3-4 hours | Medium |
| 1.7 Self-Reflection (3 tools) | 4-5 hours | Medium |
| 1.8 Knowledge Synthesis (3 tools) | 4-5 hours | Medium |
| 1.9 Tool Registration | 2-3 hours | Low |
| 1.10 Move describe_my_avatar | 30 min | Low |
| 1.11 Frontend Sync | 2-3 hours | Medium |
| 1.12 LEARNING Block Integration | 2-3 hours | Medium |
| 1.13 Testing | 4-6 hours | Medium |
| **Total** | **~4-5 days** | **Medium** |

---

## 2. Prerequisites & Dependencies

### Phase 0 Requirements

These Phase 0 items MUST be completed before Phase 1:

- [x] XP values updated (5/2.5/0)
- [x] LEARNING block type added to `core/block.py`
- [x] Float XP support confirmed

### Existing Systems Leveraged

Phase 1 tools depend heavily on existing infrastructure:

#### 1. Intelligent Memory Search (5-Layer Hybrid)

**File:** `ai/tools/memory_search.py`
**Function:** `intelligent_memory_search(qube, query, context, top_k, min_score)`

```python
# Key parameters for Phase 1 tools
context = {
    "block_types": ["ACTION", "SUMMARY", "DECISION"],  # Filter by type
    "date_range": (start_timestamp, end_timestamp),     # Time filter
    "decay_rate": 0.05,                                  # Temporal decay (0.01-0.3)
    "semantic_weight": 0.6,                              # Layer 1 weight
    "keyword_weight": 0.3,                               # Layer 3 weight
    "temporal_weight": 0.15,                             # Layer 4 weight
    "relationship_weight": 0.1,                          # Layer 5 weight
}
```

#### 2. Self-Evaluation System

**File:** `relationships/self_evaluation.py`
**Class:** `SelfEvaluation`

```python
# Methods used by Phase 1 tools
qube.self_evaluation.get_summary()   # Returns current metrics, strengths, areas_for_improvement
qube.self_evaluation.get_timeline()  # Returns list of historical snapshots with metrics
```

**10 Core Metrics:**
- `self_awareness`, `confidence`, `consistency`, `growth_rate`, `goal_alignment`
- `critical_thinking`, `adaptability`, `emotional_intelligence`, `humility`, `curiosity`

#### 3. Block Types

Phase 1 tools analyze these block types:

| Block Type | Key Fields | Used By |
|------------|------------|---------|
| ACTION | `success` (bool), `action_type`, `result` | `analyze_mistake`, `replicate_success` |
| SUMMARY | `self_evaluation`, `key_insights` | `self_reflect`, `quick_insight` |
| DECISION | `decision`, `reasoning`, `participants` | `detect_bias`, `find_root_cause` |
| LEARNING | `learning_type`, `source_block`, `confidence` | Created by tools |

#### 4. BM25 Scorer

**File:** `ai/tools/memory_search.py`
**Class:** `BM25Scorer`

Used by `extract_success_factors` and `detect_trend` for frequency analysis.

---

## 3. Task 1.1: Update Skill Definitions

### Python Backend

**File:** `utils/skill_definitions.py`
**Lines:** 52-70 (replace entire AI Reasoning section)

#### Current State (Old)

```python
# ===== AI REASONING (16 skills) =====
skills.append(_create_skill("ai_reasoning", "AI Reasoning", "Master AI reasoning and problem-solving capabilities", "ai_reasoning", "sun", tool_reward="describe_my_avatar", icon="🧠"))
# Planets
skills.append(_create_skill("prompt_engineering", "Prompt Engineering", "Craft effective prompts to elicit desired AI responses", "ai_reasoning", "planet", "ai_reasoning", tool_reward="analyze_prompt_quality", icon="✍️"))
skills.append(_create_skill("chain_of_thought", "Chain of Thought", "Break down complex problems into logical steps", "ai_reasoning", "planet", "ai_reasoning", tool_reward="generate_reasoning_chain", icon="🔗"))
skills.append(_create_skill("code_generation", "Code Generation", "Generate high-quality code across multiple languages", "ai_reasoning", "planet", "ai_reasoning", tool_reward="advanced_code_gen", icon="⚙️"))
skills.append(_create_skill("analysis_critique", "Analysis & Critique", "Critically analyze and provide constructive feedback", "ai_reasoning", "planet", "ai_reasoning", tool_reward="deep_analysis", icon="🔍"))
skills.append(_create_skill("multistep_planning", "Multi-step Planning", "Plan and execute complex multi-step tasks", "ai_reasoning", "planet", "ai_reasoning", tool_reward="create_task_plan", icon="📋"))
# Moons (10 total - 2 per planet)
skills.append(_create_skill("prompt_eng_clarity", ...))
# ... etc
```

#### Target State (New)

```python
# ===== AI REASONING (14 skills) =====
# Theme: Learning From Experience - analyze memory chain to improve over time

# Sun
skills.append(_create_skill(
    "ai_reasoning",
    "AI Reasoning",
    "Master learning from experience through memory chain analysis",
    "ai_reasoning",
    "sun",
    tool_reward="recall_similar",  # NEW: was describe_my_avatar
    icon="🧠"
))

# Planet 1: Pattern Recognition
skills.append(_create_skill(
    "pattern_recognition",
    "Pattern Recognition",
    "Finding similar situations in past experience",
    "ai_reasoning",
    "planet",
    "ai_reasoning",
    tool_reward="find_analogy",
    icon="🔍"
))

# Moon 1.1: Trend Detection
skills.append(_create_skill(
    "trend_detection",
    "Trend Detection",
    "Spot patterns that repeat or evolve over time",
    "ai_reasoning",
    "moon",
    "pattern_recognition",
    "pattern_recognition",
    icon="📈"
))

# Moon 1.2: Quick Insight
skills.append(_create_skill(
    "quick_insight",
    "Quick Insight",
    "Pull one highly relevant insight from memory",
    "ai_reasoning",
    "moon",
    "pattern_recognition",
    "pattern_recognition",
    icon="💡"
))

# Planet 2: Learning from Failure
skills.append(_create_skill(
    "learning_from_failure",
    "Learning from Failure",
    "Analyzing past mistakes to avoid repeating them",
    "ai_reasoning",
    "planet",
    "ai_reasoning",
    tool_reward="analyze_mistake",
    icon="📉"
))

# Moon 2.1: Root Cause Analysis
skills.append(_create_skill(
    "root_cause_analysis",
    "Root Cause Analysis",
    "Dig past symptoms to find underlying issues",
    "ai_reasoning",
    "moon",
    "learning_from_failure",
    "learning_from_failure",
    icon="🔬"
))

# Planet 3: Building on Success
skills.append(_create_skill(
    "building_on_success",
    "Building on Success",
    "Finding what worked and replicating it",
    "ai_reasoning",
    "planet",
    "ai_reasoning",
    tool_reward="replicate_success",
    icon="🏆"
))

# Moon 3.1: Success Factors
skills.append(_create_skill(
    "success_factors",
    "Success Factors",
    "Identify WHY something worked, not just THAT it worked",
    "ai_reasoning",
    "moon",
    "building_on_success",
    "building_on_success",
    icon="🎯"
))

# Planet 4: Self-Reflection
skills.append(_create_skill(
    "self_reflection",
    "Self-Reflection",
    "Understanding own patterns, biases, and growth",
    "ai_reasoning",
    "planet",
    "ai_reasoning",
    tool_reward="self_reflect",
    icon="🪞"
))

# Moon 4.1: Growth Tracking
skills.append(_create_skill(
    "growth_tracking",
    "Growth Tracking",
    "Compare past vs present performance, see improvement",
    "ai_reasoning",
    "moon",
    "self_reflection",
    "self_reflection",
    icon="📊"
))

# Moon 4.2: Bias Detection
skills.append(_create_skill(
    "bias_detection",
    "Bias Detection",
    "Identify blind spots and tendencies in own reasoning",
    "ai_reasoning",
    "moon",
    "self_reflection",
    "self_reflection",
    icon="⚠️"
))

# Planet 5: Knowledge Synthesis
skills.append(_create_skill(
    "knowledge_synthesis",
    "Knowledge Synthesis",
    "Combining learnings from different experiences into new insights",
    "ai_reasoning",
    "planet",
    "ai_reasoning",
    tool_reward="synthesize_learnings",
    icon="🧩"
))

# Moon 5.1: Cross-Pollinate
skills.append(_create_skill(
    "cross_pollinate",
    "Cross-Pollinate",
    "Find unexpected links between different knowledge areas",
    "ai_reasoning",
    "moon",
    "knowledge_synthesis",
    "knowledge_synthesis",
    icon="🔀"
))

# Moon 5.2: Reflect on Topic
skills.append(_create_skill(
    "reflect_on_topic",
    "Reflect on Topic",
    "Get accumulated wisdom on any topic",
    "ai_reasoning",
    "moon",
    "knowledge_synthesis",
    "knowledge_synthesis",
    icon="💭"
))
```

### Verification

After updating, verify count:
```python
ai_reasoning_skills = [s for s in skills if s["category"] == "ai_reasoning"]
assert len(ai_reasoning_skills) == 14  # 1 sun + 5 planets + 8 moons
```

---

## 4. Task 1.2: Update TOOL_TO_SKILL_MAPPING

**File:** `ai/skill_scanner.py`
**Lines:** 44-85

### Current State

```python
TOOL_TO_SKILL_MAPPING = {
    # ...existing mappings...
    "describe_my_avatar": "analysis_critique",   # ai_reasoning → analysis_critique planet
    "think_step_by_step": "chain_of_thought",    # ai_reasoning → chain_of_thought planet
    "self_critique": "analysis_critique",        # ai_reasoning → analysis_critique planet
    "explore_alternatives": "multistep_planning",# ai_reasoning → multistep_planning planet
    # ...
}
```

### Target State

```python
TOOL_TO_SKILL_MAPPING = {
    # =========================================
    # AI REASONING - Learning From Experience
    # =========================================

    # Sun Tool
    "recall_similar": "ai_reasoning",

    # Planet 1: Pattern Recognition
    "find_analogy": "pattern_recognition",

    # Moon 1.1, 1.2
    "detect_trend": "trend_detection",
    "quick_insight": "quick_insight",

    # Planet 2: Learning from Failure
    "analyze_mistake": "learning_from_failure",

    # Moon 2.1
    "find_root_cause": "root_cause_analysis",

    # Planet 3: Building on Success
    "replicate_success": "building_on_success",

    # Moon 3.1
    "extract_success_factors": "success_factors",

    # Planet 4: Self-Reflection
    "self_reflect": "self_reflection",

    # Moon 4.1, 4.2
    "track_growth": "growth_tracking",
    "detect_bias": "bias_detection",

    # Planet 5: Knowledge Synthesis
    "synthesize_learnings": "knowledge_synthesis",

    # Moon 5.1, 5.2
    "cross_pollinate": "cross_pollinate",
    "reflect_on_topic": "reflect_on_topic",

    # =========================================
    # CREATIVE EXPRESSION (moved from AI Reasoning)
    # =========================================
    "describe_my_avatar": "visual_design",  # MOVED: was analysis_critique

    # ... rest of existing mappings ...
}
```

### Remove Old Mappings

Delete these obsolete mappings:
```python
# DELETE THESE:
"think_step_by_step": "chain_of_thought",
"self_critique": "analysis_critique",
"explore_alternatives": "multistep_planning",
```

---

## 5. Task 1.3: Implement Sun Tool - recall_similar

### Purpose

Quick "I've seen this before" lookup - the essence of learning from experience. This is the AI Reasoning Sun tool, available from birth.

### Handler Implementation

**File:** `ai/tools/handlers.py`
**Location:** Add after existing handlers

```python
# =============================================================================
# AI REASONING - LEARNING FROM EXPERIENCE TOOLS
# =============================================================================

from ai.tools.memory_search import intelligent_memory_search
from datetime import datetime, timezone


def format_relative_time(timestamp: int) -> str:
    """Format timestamp as relative time string (e.g., '2 days ago')"""
    now = int(datetime.now(timezone.utc).timestamp())
    diff = now - timestamp

    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = diff // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < 604800:
        days = diff // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < 2592000:
        weeks = diff // 604800
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff < 31536000:
        months = diff // 2592000
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff // 31536000
        return f"{years} year{'s' if years > 1 else ''} ago"


def extract_summary_from_block(block: dict) -> str:
    """Extract a brief summary from a block's content"""
    content = block.get("content", {})
    block_type = block.get("block_type", "")

    if block_type == "SUMMARY":
        # Use evaluation summary if available
        summary = content.get("evaluation_summary", "")
        if summary:
            return summary[:200]
        # Otherwise use key insights
        insights = content.get("key_insights", [])
        if insights:
            return insights[0][:200] if insights[0] else ""

    elif block_type == "ACTION":
        action_type = content.get("action_type", "action")
        result = content.get("result", {})
        if isinstance(result, dict):
            return f"{action_type}: {result.get('summary', str(result)[:100])}"
        return f"{action_type}: {str(result)[:100]}"

    elif block_type == "MESSAGE":
        text = content.get("text", content.get("content", ""))
        return text[:200] if text else ""

    elif block_type == "DECISION":
        decision = content.get("decision", "")
        return f"Decision: {decision[:180]}" if decision else ""

    return str(content)[:200]


async def recall_similar_handler(qube, params: dict) -> dict:
    """
    Quick pattern match against memory chain.
    Lightweight version of find_analogy for frequent use.

    The AI Reasoning Sun tool - always available.
    """
    try:
        situation = params.get("situation", "")

        if not situation:
            return {
                "success": False,
                "error": "Please provide a situation to recall similar experiences"
            }

        # Use semantic search with moderate settings
        results = await intelligent_memory_search(
            qube=qube,
            query=situation,
            context={
                "semantic_weight": 0.6,
                "temporal_weight": 0.2,
                "decay_rate": 0.05,  # Moderate decay - balance recent and historical
            },
            top_k=3
        )

        if not results:
            return {
                "success": True,
                "similar_situations": [],
                "message": "No similar situations found in memory"
            }

        similar_situations = []
        for r in results:
            block = r.block
            similar_situations.append({
                "summary": extract_summary_from_block(block),
                "when": format_relative_time(block.get("timestamp", 0)),
                "block_type": block.get("block_type", "UNKNOWN"),
                "relevance": round(r.combined_score, 2),
                "block_number": block.get("block_number", 0)
            })

        return {
            "success": True,
            "query": situation,
            "similar_situations": similar_situations,
            "count": len(similar_situations)
        }

    except Exception as e:
        logger.error(f"recall_similar_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Tool Registration

**File:** `ai/tools/registry.py` (in `register_default_tools` function)

```python
# AI Reasoning - Sun Tool: recall_similar
registry.register(ToolDefinition(
    name="recall_similar",
    description="Quick lookup for similar past situations in memory. Use this to check 'have I seen this before?' or find relevant past experiences for the current context.",
    parameters={
        "type": "object",
        "properties": {
            "situation": {
                "type": "string",
                "description": "Current situation or topic to find similar experiences for"
            }
        },
        "required": ["situation"]
    },
    handler=lambda params: recall_similar_handler(qube, params)
))
```

### ALWAYS_AVAILABLE_TOOLS Update

**File:** `ai/tools/registry.py`
**Line:** 19-41

Add `recall_similar` to the set (it's a Sun tool):

```python
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    # ... existing tools ...
    "recall_similar",  # AI Reasoning Sun tool
}
```

---

## 6. Task 1.4: Implement Pattern Recognition Planet

### Planet Tool: find_analogy

```python
async def find_analogy_handler(qube, params: dict) -> dict:
    """
    Deep search for analogous situations in memory chain.
    More thorough than recall_similar - used for deeper analysis.

    Optionally creates a LEARNING block with type='insight' if a strong
    analogy is found.
    """
    try:
        situation = params.get("situation", "")
        depth = params.get("depth", "deep")

        if not situation:
            return {
                "success": False,
                "error": "Please provide a situation to find analogies for"
            }

        # Use semantic search with historical bias
        results = await intelligent_memory_search(
            qube=qube,
            query=situation,
            context={
                "semantic_weight": 0.7,
                "temporal_weight": 0.1,  # Don't penalize old memories
                "decay_rate": 0.01,      # Very slow decay for patterns
                "block_types": ["MESSAGE", "DECISION", "ACTION", "SUMMARY"]
            },
            top_k=5 if depth == "deep" else 3
        )

        if not results:
            return {
                "success": True,
                "analogies_found": 0,
                "analogies": [],
                "message": "No analogous situations found in memory"
            }

        analogies = []
        for r in results:
            block = r.block
            content = block.get("content", {})

            # Extract outcome if available (for ACTION blocks)
            outcome = None
            if block.get("block_type") == "ACTION":
                outcome = "Success" if content.get("success") else "Failed/Unknown"

            # Check for covering SUMMARY block
            lesson_learned = None
            if hasattr(qube, 'memory_chain'):
                # Look for SUMMARY blocks after this one that might reference it
                for i in range(block.get("block_number", 0) + 1,
                               min(block.get("block_number", 0) + 20,
                                   qube.memory_chain.get_chain_length())):
                    try:
                        check_block = qube.memory_chain.get_block(i)
                        if check_block and check_block.get("block_type") == "SUMMARY":
                            insights = check_block.get("content", {}).get("key_insights", [])
                            if insights:
                                lesson_learned = insights[0]
                                break
                    except:
                        continue

            analogies.append({
                "situation": extract_summary_from_block(block),
                "outcome": outcome,
                "lesson_learned": lesson_learned,
                "similarity_score": round(r.combined_score, 2),
                "when": format_relative_time(block.get("timestamp", 0)),
                "block_number": block.get("block_number", 0),
                "block_type": block.get("block_type", "UNKNOWN")
            })

        return {
            "success": True,
            "query": situation,
            "search_depth": depth,
            "analogies_found": len(analogies),
            "analogies": analogies
        }

    except Exception as e:
        logger.error(f"find_analogy_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 1.1: detect_trend

```python
async def detect_trend_handler(qube, params: dict) -> dict:
    """
    Analyze how a topic/pattern has evolved over time.
    Divides history into windows and compares frequency/relevance.
    """
    try:
        topic = params.get("topic", "")
        num_windows = params.get("time_windows", 4)

        if not topic:
            return {
                "success": False,
                "error": "Please provide a topic to analyze trends for"
            }

        # Get chain time range
        if not hasattr(qube, 'memory_chain'):
            return {"success": False, "error": "Memory chain not available"}

        chain_length = qube.memory_chain.get_chain_length()
        if chain_length < 2:
            return {
                "success": True,
                "message": "Not enough history to detect trends",
                "blocks_in_chain": chain_length
            }

        # Get genesis block for start time
        genesis = qube.memory_chain.get_block(0)
        if not genesis:
            return {"success": False, "error": "Could not access genesis block"}

        genesis_time = genesis.get("timestamp", 0)
        now = int(datetime.now(timezone.utc).timestamp())
        total_time = now - genesis_time
        window_size = total_time / num_windows

        trends = []
        for i in range(num_windows):
            start_time = genesis_time + int(i * window_size)
            end_time = start_time + int(window_size)

            # Search within this time window
            results = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={
                    "date_range": (start_time, end_time),
                    "keyword_weight": 0.5,  # BM25 for frequency counting
                    "semantic_weight": 0.3
                },
                top_k=50  # Get more to count
            )

            avg_relevance = 0
            if results:
                avg_relevance = sum(r.combined_score for r in results) / len(results)

            trends.append({
                "period": f"Window {i+1}",
                "start": datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "end": datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "mention_count": len(results),
                "avg_relevance": round(avg_relevance, 2)
            })

        # Analyze trend direction
        counts = [t["mention_count"] for t in trends]

        if len(counts) >= 2:
            first_half = sum(counts[:len(counts)//2])
            second_half = sum(counts[len(counts)//2:])

            if second_half > first_half * 1.3:
                direction = "increasing"
            elif first_half > second_half * 1.3:
                direction = "decreasing"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"

        return {
            "success": True,
            "topic": topic,
            "trend_direction": direction,
            "windows": trends,
            "total_mentions": sum(counts),
            "analysis_period": {
                "start": datetime.fromtimestamp(genesis_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "end": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
            }
        }

    except Exception as e:
        logger.error(f"detect_trend_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 1.2: quick_insight

```python
async def quick_insight_handler(qube, params: dict) -> dict:
    """
    Retrieve the single most relevant insight for the current context.
    Optimized for speed - returns immediately with best match.
    """
    try:
        context = params.get("context", "")

        if not context:
            return {
                "success": False,
                "error": "Please provide context to find an insight for"
            }

        # Fast semantic search - just get the best match
        results = await intelligent_memory_search(
            qube=qube,
            query=context,
            context={
                "semantic_weight": 0.8,
                "block_types": ["SUMMARY", "DECISION", "LEARNING"]  # Focus on insight-rich blocks
            },
            top_k=1
        )

        if not results:
            return {
                "success": True,
                "insight": None,
                "message": "No relevant insights found in memory"
            }

        best = results[0]
        block = best.block
        content = block.get("content", {})

        # Extract the most relevant insight based on block type
        insight = None
        if block.get("block_type") == "SUMMARY":
            insights = content.get("key_insights", [])
            insight = insights[0] if insights else content.get("evaluation_summary", "")
        elif block.get("block_type") == "DECISION":
            insight = f"Decision made: {content.get('decision', '')} - {content.get('reasoning', '')}"
        elif block.get("block_type") == "LEARNING":
            insight = content.get("insight", content.get("content", ""))
        else:
            insight = extract_summary_from_block(block)

        return {
            "success": True,
            "insight": insight[:500] if insight else None,
            "source_block": block.get("block_number", 0),
            "block_type": block.get("block_type", "UNKNOWN"),
            "when": format_relative_time(block.get("timestamp", 0)),
            "relevance": round(best.combined_score, 2)
        }

    except Exception as e:
        logger.error(f"quick_insight_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 7. Task 1.5: Implement Learning from Failure Planet

### Planet Tool: analyze_mistake

```python
async def analyze_mistake_handler(qube, params: dict) -> dict:
    """
    Find and analyze past mistakes/failures in memory chain.
    Searches for ACTION blocks with success=false and low self-evaluation scores.

    Creates a LEARNING block with type='insight' or 'pattern'.
    """
    try:
        topic = params.get("topic")
        recent_only = params.get("recent_only", False)

        # Build search query
        query = topic if topic else "mistake error failed wrong problem issue"

        # Search with filters for failures
        results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context={
                "block_types": ["ACTION", "SUMMARY", "DECISION"],
                "decay_rate": 0.3 if recent_only else 0.05,
            },
            top_k=20  # Get more to filter
        )

        mistakes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            # Check if this is actually a failure
            is_failure = False
            failure_reason = None

            if block_type == "ACTION":
                if content.get("success") == False:
                    is_failure = True
                    result = content.get("result", {})
                    if isinstance(result, dict):
                        failure_reason = result.get("error", result.get("message", "Unknown error"))
                    else:
                        failure_reason = str(result)[:200]

            elif block_type == "SUMMARY":
                eval_data = content.get("self_evaluation", {})
                metrics = eval_data.get("metrics", {})
                # Low confidence or goal_alignment indicates issues
                if metrics.get("goal_alignment", 100) < 60 or metrics.get("confidence", 100) < 50:
                    is_failure = True
                    failure_reason = f"Low goal alignment ({metrics.get('goal_alignment', 'N/A')}%) or confidence ({metrics.get('confidence', 'N/A')}%)"

            if is_failure:
                mistakes.append({
                    "what_happened": extract_summary_from_block(block),
                    "what_went_wrong": failure_reason,
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_type": block_type,
                    "block_number": block.get("block_number", 0)
                })

        # Find common patterns in mistakes
        common_patterns = []
        if len(mistakes) >= 2:
            # Simple pattern detection: look for repeated words
            all_text = " ".join([m["what_happened"] + " " + (m["what_went_wrong"] or "") for m in mistakes])
            words = all_text.lower().split()
            from collections import Counter
            word_counts = Counter(words)
            # Filter common words
            stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "was", "are", "were"}
            common = [(w, c) for w, c in word_counts.most_common(10) if w not in stopwords and len(w) > 3]
            common_patterns = [w for w, c in common if c >= 2][:5]

        # Generate recommendation
        recommendation = None
        if common_patterns:
            recommendation = f"Consider reviewing patterns related to: {', '.join(common_patterns)}"
        elif mistakes:
            recommendation = "Review individual failures for specific improvements"

        return {
            "success": True,
            "topic": topic,
            "search_scope": "recent" if recent_only else "all time",
            "mistakes_found": len(mistakes),
            "mistakes": mistakes[:5],  # Top 5
            "common_patterns": common_patterns,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"analyze_mistake_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 2.1: find_root_cause

```python
async def find_root_cause_handler(qube, params: dict) -> dict:
    """
    Trace back through the block chain to find root causes of a failure.
    Uses block chain traversal to walk back through history.
    """
    try:
        failure_block = params.get("failure_block")
        failure_description = params.get("failure_description")

        # Find the failure block if description provided
        if failure_description and not failure_block:
            results = await intelligent_memory_search(
                qube=qube,
                query=failure_description,
                context={"block_types": ["ACTION"]},
                top_k=1
            )
            if results:
                failure_block = results[0].block.get("block_number")

        if failure_block is None:
            return {
                "success": False,
                "error": "Could not identify failure block. Provide failure_block number or failure_description."
            }

        if not hasattr(qube, 'memory_chain'):
            return {"success": False, "error": "Memory chain not available"}

        # Walk back through the chain
        chain = []
        depth = params.get("depth", 10)

        for i in range(failure_block, max(0, failure_block - depth), -1):
            try:
                block = qube.memory_chain.get_block(i)
                if not block:
                    continue

                is_decision = block.get("block_type") == "DECISION"

                chain.append({
                    "block_number": i,
                    "type": block.get("block_type", "UNKNOWN"),
                    "summary": extract_summary_from_block(block),
                    "is_decision_point": is_decision,
                    "when": format_relative_time(block.get("timestamp", 0))
                })

                # Stop if we hit a DECISION block (likely cause)
                if is_decision and i != failure_block:
                    break

            except Exception:
                continue

        # Analyze the chain
        decision_points = [c for c in chain if c["is_decision_point"]]

        likely_root_cause = None
        if decision_points:
            likely_root_cause = decision_points[-1]  # Earliest decision in the chain
        elif chain:
            likely_root_cause = chain[-1]  # Earliest block we found

        return {
            "success": True,
            "failure_block": failure_block,
            "chain_depth": len(chain),
            "causal_chain": chain,
            "decision_points_found": len(decision_points),
            "decision_points": decision_points,
            "likely_root_cause": likely_root_cause,
            "analysis": f"Traced back {len(chain)} blocks from failure. Found {len(decision_points)} decision points."
        }

    except Exception as e:
        logger.error(f"find_root_cause_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 8. Task 1.6: Implement Building on Success Planet

### Planet Tool: replicate_success

```python
async def replicate_success_handler(qube, params: dict) -> dict:
    """
    Find successful past approaches for a similar goal.
    Searches for ACTION blocks with success=true and high self-evaluation.
    """
    try:
        goal = params.get("goal", "")

        if not goal:
            return {
                "success": False,
                "error": "Please provide a goal to find successful approaches for"
            }

        results = await intelligent_memory_search(
            qube=qube,
            query=goal,
            context={
                "block_types": ["ACTION", "SUMMARY"],
                "semantic_weight": 0.6,
            },
            top_k=20
        )

        successes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            # Check if this is a success
            is_success = False
            confidence_boost = 1.0
            what_worked = None

            if block_type == "ACTION":
                if content.get("success") == True:
                    is_success = True
                    action_type = content.get("action_type", "action")
                    result = content.get("result", {})
                    what_worked = f"Used {action_type}"
                    if isinstance(result, dict) and result.get("summary"):
                        what_worked += f": {result['summary'][:100]}"

            elif block_type == "SUMMARY":
                eval_data = content.get("self_evaluation", {})
                metrics = eval_data.get("metrics", {})
                if metrics.get("goal_alignment", 0) >= 75:
                    is_success = True
                    confidence_boost = 1 + (metrics.get("confidence", 50) / 100)
                    what_worked = eval_data.get("evaluation_summary", "")[:200]

            if is_success and what_worked:
                successes.append({
                    "what_worked": what_worked,
                    "context": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "confidence": round(r.combined_score * confidence_boost, 2),
                    "block_type": block_type,
                    "block_number": block.get("block_number", 0)
                })

        # Sort by confidence
        successes.sort(key=lambda x: x["confidence"], reverse=True)

        recommended_approach = None
        if successes:
            recommended_approach = successes[0]["what_worked"]

        return {
            "success": True,
            "goal": goal,
            "successes_found": len(successes),
            "top_strategies": successes[:5],
            "recommended_approach": recommended_approach
        }

    except Exception as e:
        logger.error(f"replicate_success_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 3.1: extract_success_factors

```python
async def extract_success_factors_handler(qube, params: dict) -> dict:
    """
    Analyze multiple successes to find common factors.
    Uses BM25 to find frequently co-occurring terms and patterns.
    """
    try:
        domain = params.get("domain", "")

        if not domain:
            return {
                "success": False,
                "error": "Please provide a domain to analyze success factors for"
            }

        # First get successes using replicate_success logic
        results = await intelligent_memory_search(
            qube=qube,
            query=domain,
            context={
                "block_types": ["ACTION", "SUMMARY"],
                "semantic_weight": 0.6,
            },
            top_k=30
        )

        # Filter to only successes
        successes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            is_success = False
            if block_type == "ACTION" and content.get("success") == True:
                is_success = True
            elif block_type == "SUMMARY":
                metrics = content.get("self_evaluation", {}).get("metrics", {})
                if metrics.get("goal_alignment", 0) >= 75:
                    is_success = True

            if is_success:
                successes.append({
                    "text": extract_summary_from_block(block),
                    "block": block
                })

        if len(successes) < 2:
            return {
                "success": True,
                "message": "Not enough successes to analyze patterns (need at least 2)",
                "successes_found": len(successes)
            }

        # Analyze common terms
        from collections import Counter
        all_words = []
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                     "of", "with", "is", "was", "are", "were", "been", "be", "have", "has",
                     "had", "do", "does", "did", "will", "would", "could", "should", "may",
                     "might", "must", "shall", "can", "need", "it", "its", "this", "that"}

        for s in successes:
            words = s["text"].lower().split()
            words = [w.strip(".,!?;:") for w in words if len(w) > 3 and w not in stopwords]
            all_words.extend(words)

        word_counts = Counter(all_words)

        # Find words that appear in multiple successes
        common_factors = [word for word, count in word_counts.most_common(15) if count >= 2]

        # Try to identify approaches
        action_words = ["used", "applied", "created", "built", "implemented", "designed", "developed"]
        common_approaches = []
        for s in successes:
            text = s["text"].lower()
            for action in action_words:
                if action in text:
                    # Extract phrase around action word
                    idx = text.find(action)
                    phrase = text[max(0, idx-20):min(len(text), idx+50)]
                    common_approaches.append(phrase.strip())
                    break

        return {
            "success": True,
            "domain": domain,
            "successes_analyzed": len(successes),
            "common_factors": common_factors[:10],
            "common_approaches": list(set(common_approaches))[:5],
            "recommendation": f"When working on {domain}, focus on: {', '.join(common_factors[:3])}" if common_factors else None
        }

    except Exception as e:
        logger.error(f"extract_success_factors_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 9. Task 1.7: Implement Self-Reflection Planet

### Planet Tool: self_reflect

```python
async def self_reflect_handler(qube, params: dict) -> dict:
    """
    Analyze own behavior patterns using self_evaluation data.
    Uses SelfEvaluation class and SUMMARY blocks.
    """
    try:
        topic = params.get("topic")

        # Get current self-evaluation state
        if not hasattr(qube, 'self_evaluation'):
            return {
                "success": False,
                "error": "Self-evaluation system not available"
            }

        current_eval = qube.self_evaluation.get_summary()
        timeline = qube.self_evaluation.get_timeline()

        # Calculate overall trends if we have history
        improvements = {}
        declines = {}

        if len(timeline) >= 2:
            first = timeline[0].get("metrics", {})
            latest = timeline[-1].get("metrics", {})

            for metric in first.keys():
                diff = latest.get(metric, 50) - first.get(metric, 50)
                if diff > 5:
                    improvements[metric] = round(diff, 1)
                elif diff < -5:
                    declines[metric] = round(diff, 1)

        result = {
            "success": True,
            "current_state": {
                "overall_score": round(current_eval.get("overall_score", 50), 1),
                "strengths": current_eval.get("strengths", []),
                "areas_for_improvement": current_eval.get("areas_for_improvement", []),
                "metrics": current_eval.get("metrics", {})
            },
            "evaluation_count": current_eval.get("evaluation_count", 0),
            "improvements": improvements,
            "declines": declines
        }

        # If topic provided, analyze performance in that specific area
        if topic:
            topic_blocks = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={"block_types": ["ACTION", "SUMMARY"]},
                top_k=20
            )

            topic_successes = 0
            topic_failures = 0

            for r in topic_blocks:
                block = r.block
                content = block.get("content", {})
                if block.get("block_type") == "ACTION":
                    if content.get("success") == True:
                        topic_successes += 1
                    elif content.get("success") == False:
                        topic_failures += 1

            total = topic_successes + topic_failures
            result["topic_analysis"] = {
                "topic": topic,
                "total_interactions": len(topic_blocks),
                "successes": topic_successes,
                "failures": topic_failures,
                "success_rate": f"{(topic_successes / total * 100):.1f}%" if total > 0 else "N/A"
            }

        return result

    except Exception as e:
        logger.error(f"self_reflect_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 4.1: track_growth

```python
async def track_growth_handler(qube, params: dict) -> dict:
    """
    Track metric changes over time using evaluation snapshots.
    Uses get_timeline() from SelfEvaluation.
    """
    try:
        metric = params.get("metric")  # None = all metrics

        if not hasattr(qube, 'self_evaluation'):
            return {"success": False, "error": "Self-evaluation system not available"}

        timeline = qube.self_evaluation.get_timeline()

        if not timeline:
            return {
                "success": True,
                "message": "No evaluation history yet",
                "evaluations": 0
            }

        if metric:
            # Track single metric
            values = [snap.get("metrics", {}).get(metric, 50) for snap in timeline]
            timestamps = [snap.get("timestamp", 0) for snap in timeline]

            if len(values) < 2:
                growth_rate = 0
            else:
                growth_rate = (values[-1] - values[0]) / len(values)

            # Find inflection points (significant changes)
            inflection_points = []
            for i in range(1, len(values)):
                change = values[i] - values[i-1]
                if abs(change) > 10:  # Significant change
                    inflection_points.append({
                        "index": i,
                        "when": format_relative_time(timestamps[i]),
                        "change": round(change, 1),
                        "new_value": round(values[i], 1)
                    })

            return {
                "success": True,
                "metric": metric,
                "start_value": round(values[0], 1),
                "current_value": round(values[-1], 1),
                "min_value": round(min(values), 1),
                "max_value": round(max(values), 1),
                "growth_rate": round(growth_rate, 2),
                "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable",
                "data_points": len(values),
                "inflection_points": inflection_points[:5]
            }
        else:
            # Track all metrics
            all_metrics = {}
            first_metrics = timeline[0].get("metrics", {})
            last_metrics = timeline[-1].get("metrics", {})

            for metric_name in first_metrics.keys():
                values = [snap.get("metrics", {}).get(metric_name, 50) for snap in timeline]
                if len(values) < 2:
                    growth_rate = 0
                else:
                    growth_rate = (values[-1] - values[0]) / len(values)

                all_metrics[metric_name] = {
                    "start": round(values[0], 1),
                    "current": round(values[-1], 1),
                    "growth_rate": round(growth_rate, 2),
                    "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable"
                }

            # Find fastest improving and needs attention
            fastest_improving = max(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0] if all_metrics else None
            needs_attention = min(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0] if all_metrics else None

            return {
                "success": True,
                "evaluations": len(timeline),
                "time_span": {
                    "first": format_relative_time(timeline[0].get("timestamp", 0)),
                    "last": format_relative_time(timeline[-1].get("timestamp", 0))
                },
                "metrics": all_metrics,
                "fastest_improving": fastest_improving,
                "needs_attention": needs_attention
            }

    except Exception as e:
        logger.error(f"track_growth_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 4.2: detect_bias

```python
async def detect_bias_handler(qube, params: dict) -> dict:
    """
    Analyze DECISION blocks to find patterns that suggest bias.
    Looks for repeated assumptions, skewed outcomes, avoided topics.
    """
    try:
        domain = params.get("domain")

        # Get all decision blocks
        query = domain if domain else ""
        results = await intelligent_memory_search(
            qube=qube,
            query=query if query else "decision choice chose decided",
            context={
                "block_types": ["DECISION"],
                "temporal_weight": 0.05  # Include historical decisions
            },
            top_k=50
        )

        if len(results) < 5:
            return {
                "success": True,
                "message": "Not enough decisions to analyze for bias (need at least 5)",
                "decisions_found": len(results)
            }

        # Analyze patterns
        participant_counts = {}
        assumptions = []
        all_text = []

        for r in results:
            block = r.block
            content = block.get("content", {})

            # Track participants
            participants = block.get("participants", {})
            for p in participants.get("affected", []):
                participant_counts[p] = participant_counts.get(p, 0) + 1

            # Look for assumption language
            text = str(content).lower()
            all_text.append(text)

            assumption_phrases = ["assume", "assuming", "probably", "likely", "must be", "should be", "obviously"]
            for phrase in assumption_phrases:
                if phrase in text:
                    # Extract context around assumption
                    idx = text.find(phrase)
                    context_text = text[max(0, idx-30):min(len(text), idx+50)]
                    assumptions.append(context_text.strip())

        # Find repeated assumptions
        from collections import Counter
        assumption_counts = Counter(assumptions)
        repeated_assumptions = [(a, c) for a, c in assumption_counts.most_common(5) if c >= 2]

        # Analyze word frequency for potential blind spots
        all_words = " ".join(all_text).split()
        word_counts = Counter(all_words)

        # Build potential biases list
        potential_biases = []

        for assumption, count in repeated_assumptions:
            potential_biases.append({
                "type": "Repeated Assumption",
                "pattern": assumption[:100],
                "frequency": count,
                "recommendation": f"Question whether this assumption is always valid"
            })

        # Check for participant imbalance
        if participant_counts:
            max_count = max(participant_counts.values())
            for participant, count in participant_counts.items():
                if count >= max_count * 0.5 and count >= 3:
                    potential_biases.append({
                        "type": "Participant Focus",
                        "pattern": f"Decisions frequently involve/affect: {participant}",
                        "frequency": count,
                        "recommendation": "Consider if other stakeholders are being overlooked"
                    })

        return {
            "success": True,
            "decisions_analyzed": len(results),
            "potential_biases": potential_biases[:5],
            "participant_distribution": participant_counts,
            "overall_assessment": f"Analyzed {len(results)} decisions. Found {len(potential_biases)} potential bias patterns." if potential_biases else "No significant bias patterns detected."
        }

    except Exception as e:
        logger.error(f"detect_bias_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 10. Task 1.8: Implement Knowledge Synthesis Planet

### Planet Tool: synthesize_learnings

```python
async def synthesize_learnings_handler(qube, params: dict) -> dict:
    """
    Find connections between different topics/domains in memory.
    Searches for each topic and finds intersection points.

    Creates a LEARNING block with type='synthesis'.
    """
    try:
        topics = params.get("topics", [])

        if len(topics) < 2:
            return {
                "success": False,
                "error": "Need at least 2 topics to synthesize"
            }

        # Search for each topic
        topic_results = {}
        for topic in topics:
            results = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={"semantic_weight": 0.7},
                top_k=20
            )
            topic_results[topic] = {r.block.get("block_number"): r for r in results}

        # Find blocks that appear in multiple topic searches
        all_block_nums = set()
        for blocks in topic_results.values():
            all_block_nums.update(blocks.keys())

        connection_blocks = []
        for block_num in all_block_nums:
            topics_containing = [t for t, blocks in topic_results.items() if block_num in blocks]
            if len(topics_containing) >= 2:
                # Get block from first topic that has it
                for t in topics_containing:
                    if block_num in topic_results[t]:
                        block = topic_results[t][block_num].block
                        break

                connection_blocks.append({
                    "block_number": block_num,
                    "connects": topics_containing,
                    "summary": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_type": block.get("block_type", "UNKNOWN")
                })

        # Sort by number of topics connected
        connection_blocks.sort(key=lambda x: len(x["connects"]), reverse=True)

        # Generate insights
        insights = []
        for conn in connection_blocks[:3]:
            topic_list = " and ".join(conn["connects"])
            insights.append(f"Connection between {topic_list}: {conn['summary'][:100]}")

        # Generate recommendation
        recommendation = None
        if connection_blocks:
            most_connected = connection_blocks[0]["connects"]
            recommendation = f"Strong connection found between {' and '.join(most_connected)}. Consider exploring this intersection further."

        return {
            "success": True,
            "topics": topics,
            "connections_found": len(connection_blocks),
            "connection_points": connection_blocks[:5],
            "novel_insights": insights,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"synthesize_learnings_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 5.1: cross_pollinate

```python
async def cross_pollinate_handler(qube, params: dict) -> dict:
    """
    Find unexpected connections by searching with low similarity threshold.
    Filters out same-domain results to surface surprising links.
    """
    try:
        idea = params.get("idea", "")

        if not idea:
            return {
                "success": False,
                "error": "Please provide an idea to find cross-domain connections for"
            }

        # Detect the domain of the input idea (simple heuristic)
        domain_keywords = {
            "technology": ["code", "programming", "software", "api", "database", "algorithm", "app", "web"],
            "relationships": ["friend", "family", "love", "trust", "talk", "feel", "person", "people"],
            "health": ["health", "exercise", "diet", "sleep", "medical", "body", "fitness"],
            "finance": ["money", "invest", "budget", "crypto", "bitcoin", "cash", "payment"],
            "creative": ["art", "music", "design", "write", "story", "creative", "image"],
            "learning": ["learn", "study", "understand", "knowledge", "skill", "practice"]
        }

        idea_lower = idea.lower()
        source_domain = "general"
        for domain, keywords in domain_keywords.items():
            if any(kw in idea_lower for kw in keywords):
                source_domain = domain
                break

        # Search with lower threshold to find distant matches
        results = await intelligent_memory_search(
            qube=qube,
            query=idea,
            context={
                "semantic_weight": 0.9,
            },
            top_k=20,
            min_score=5.0  # Lower threshold for distant matches
        )

        # Filter out same-domain results
        cross_domain_results = []
        for r in results:
            summary = extract_summary_from_block(r.block).lower()

            # Detect domain of result
            result_domain = "general"
            for domain, keywords in domain_keywords.items():
                if any(kw in summary for kw in keywords):
                    result_domain = domain
                    break

            if result_domain != source_domain:
                cross_domain_results.append({
                    "connection": extract_summary_from_block(r.block),
                    "domain": result_domain,
                    "similarity": round(r.combined_score, 2),
                    "when": format_relative_time(r.block.get("timestamp", 0)),
                    "block_number": r.block.get("block_number", 0),
                    "potential_application": f"Apply insights from {result_domain} to {source_domain}"
                })

        most_surprising = cross_domain_results[0] if cross_domain_results else None

        synthesis_suggestion = None
        if cross_domain_results:
            domains_found = list(set([r["domain"] for r in cross_domain_results[:3]]))
            synthesis_suggestion = f"Consider how lessons from {', '.join(domains_found)} might apply to {source_domain}"

        return {
            "success": True,
            "source_idea": idea,
            "source_domain": source_domain,
            "unexpected_connections": cross_domain_results[:5],
            "most_surprising": most_surprising,
            "synthesis_suggestion": synthesis_suggestion
        }

    except Exception as e:
        logger.error(f"cross_pollinate_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 5.2: reflect_on_topic

```python
async def reflect_on_topic_handler(qube, params: dict) -> dict:
    """
    Synthesize all learnings about a specific topic.
    Combines pattern recognition, success/failure analysis, and insights.
    """
    try:
        topic = params.get("topic", "")

        if not topic:
            return {
                "success": False,
                "error": "Please provide a topic to reflect on"
            }

        # Gather all relevant blocks
        results = await intelligent_memory_search(
            qube=qube,
            query=topic,
            context={
                "semantic_weight": 0.6,
                "decay_rate": 0.01  # Include old memories
            },
            top_k=30
        )

        if not results:
            return {
                "success": True,
                "topic": topic,
                "message": "No memories found about this topic",
                "memories_found": 0
            }

        # Categorize results
        successes = []
        failures = []
        insights = []

        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            if block_type == "ACTION":
                if content.get("success") == True:
                    successes.append(extract_summary_from_block(block))
                elif content.get("success") == False:
                    failures.append(extract_summary_from_block(block))

            elif block_type == "SUMMARY":
                key_insights = content.get("key_insights", [])
                insights.extend(key_insights[:2])  # Take top 2 from each summary

            elif block_type == "LEARNING":
                insight = content.get("insight", content.get("content", ""))
                if insight:
                    insights.append(insight)

        # Calculate statistics
        total_interactions = len(results)
        success_count = len(successes)
        failure_count = len(failures)
        total_outcomes = success_count + failure_count
        success_rate = success_count / total_outcomes if total_outcomes > 0 else 0

        # Find patterns (simple word frequency)
        from collections import Counter

        success_words = " ".join(successes).lower().split() if successes else []
        failure_words = " ".join(failures).lower().split() if failures else []

        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "was"}

        success_patterns = [w for w, c in Counter(success_words).most_common(10)
                          if w not in stopwords and len(w) > 3 and c >= 2][:3]
        failure_patterns = [w for w, c in Counter(failure_words).most_common(10)
                          if w not in stopwords and len(w) > 3 and c >= 2][:3]

        # Generate wisdom
        wisdom = None
        if success_rate > 0.7 and success_patterns:
            wisdom = f"Strong performance on {topic}. Key factors: {', '.join(success_patterns)}"
        elif success_rate < 0.3 and failure_patterns:
            wisdom = f"Challenges with {topic}. Common issues involve: {', '.join(failure_patterns)}"
        elif insights:
            wisdom = f"Key insight about {topic}: {insights[0][:150]}"

        # Generate recommendation
        recommendation = None
        if success_rate < 0.5 and successes:
            recommendation = f"Success rate is {success_rate:.0%}. Review successful approaches and apply more consistently."
        elif success_rate >= 0.7:
            recommendation = f"Excellent {success_rate:.0%} success rate. Continue current approach."

        return {
            "success": True,
            "topic": topic,
            "memories_found": total_interactions,
            "first_encounter": format_relative_time(results[-1].block.get("timestamp", 0)) if results else None,
            "most_recent": format_relative_time(results[0].block.get("timestamp", 0)) if results else None,
            "statistics": {
                "total_interactions": total_interactions,
                "successes": success_count,
                "failures": failure_count,
                "success_rate": f"{success_rate:.0%}"
            },
            "patterns": {
                "what_works": success_patterns,
                "what_doesnt": failure_patterns
            },
            "key_insights": insights[:5],
            "accumulated_wisdom": wisdom,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"reflect_on_topic_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 11. Task 1.9: Register All Tools

**File:** `ai/tools/handlers.py` - in `register_default_tools()` function

### Tool Registration Code

```python
def register_default_tools(registry: ToolRegistry) -> None:
    """Register all default tools available to Qubes"""
    qube = registry.qube

    # ... existing tool registrations ...

    # =========================================================================
    # AI REASONING - LEARNING FROM EXPERIENCE
    # =========================================================================

    # Sun Tool: recall_similar
    registry.register(ToolDefinition(
        name="recall_similar",
        description="Quick lookup for similar past situations in memory. Use this to check 'have I seen this before?' or find relevant past experiences.",
        parameters={
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Current situation or topic to find similar experiences for"
                }
            },
            "required": ["situation"]
        },
        handler=lambda params: recall_similar_handler(qube, params)
    ))

    # Planet 1: Pattern Recognition
    registry.register(ToolDefinition(
        name="find_analogy",
        description="Deep search for analogous situations in memory chain. More thorough than recall_similar - used for deeper analysis.",
        parameters={
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Situation to find analogies for"
                },
                "depth": {
                    "type": "string",
                    "enum": ["shallow", "deep"],
                    "description": "Search depth",
                    "default": "deep"
                }
            },
            "required": ["situation"]
        },
        handler=lambda params: find_analogy_handler(qube, params)
    ))

    # Moon 1.1: Trend Detection
    registry.register(ToolDefinition(
        name="detect_trend",
        description="Analyze how a topic or pattern has evolved over time in memory.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to analyze trends for"
                },
                "time_windows": {
                    "type": "integer",
                    "description": "Number of time periods to analyze",
                    "default": 4
                }
            },
            "required": ["topic"]
        },
        handler=lambda params: detect_trend_handler(qube, params)
    ))

    # Moon 1.2: Quick Insight
    registry.register(ToolDefinition(
        name="quick_insight",
        description="Retrieve the single most relevant insight for the current context. Fast, focused lookup.",
        parameters={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Current context or question to find insight for"
                }
            },
            "required": ["context"]
        },
        handler=lambda params: quick_insight_handler(qube, params)
    ))

    # Planet 2: Learning from Failure
    registry.register(ToolDefinition(
        name="analyze_mistake",
        description="Find and analyze past mistakes or failures in memory. Learn what went wrong to avoid repeating errors.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic to focus mistake analysis on"
                },
                "recent_only": {
                    "type": "boolean",
                    "description": "Only analyze recent mistakes",
                    "default": False
                }
            },
            "required": []
        },
        handler=lambda params: analyze_mistake_handler(qube, params)
    ))

    # Moon 2.1: Root Cause Analysis
    registry.register(ToolDefinition(
        name="find_root_cause",
        description="Trace back through the block chain to find root causes of a failure.",
        parameters={
            "type": "object",
            "properties": {
                "failure_block": {
                    "type": "integer",
                    "description": "Block number of the failure to analyze"
                },
                "failure_description": {
                    "type": "string",
                    "description": "Description of the failure (if block number unknown)"
                },
                "depth": {
                    "type": "integer",
                    "description": "How many blocks to trace back",
                    "default": 10
                }
            },
            "required": []
        },
        handler=lambda params: find_root_cause_handler(qube, params)
    ))

    # Planet 3: Building on Success
    registry.register(ToolDefinition(
        name="replicate_success",
        description="Find successful past approaches for a similar goal. Learn what worked before.",
        parameters={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal or objective to find successful approaches for"
                }
            },
            "required": ["goal"]
        },
        handler=lambda params: replicate_success_handler(qube, params)
    ))

    # Moon 3.1: Success Factors
    registry.register(ToolDefinition(
        name="extract_success_factors",
        description="Analyze multiple successes to find common factors. Identify WHY things worked.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain or area to analyze success factors for"
                }
            },
            "required": ["domain"]
        },
        handler=lambda params: extract_success_factors_handler(qube, params)
    ))

    # Planet 4: Self-Reflection
    registry.register(ToolDefinition(
        name="self_reflect",
        description="Analyze own behavior patterns, strengths, and areas for growth using self-evaluation data.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic to focus self-reflection on"
                }
            },
            "required": []
        },
        handler=lambda params: self_reflect_handler(qube, params)
    ))

    # Moon 4.1: Growth Tracking
    registry.register(ToolDefinition(
        name="track_growth",
        description="Track metric changes over time. Visualize growth trajectory and find inflection points.",
        parameters={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Specific metric to track (e.g., 'confidence', 'adaptability'). Omit for all metrics.",
                    "enum": ["self_awareness", "confidence", "consistency", "growth_rate", "goal_alignment",
                            "critical_thinking", "adaptability", "emotional_intelligence", "humility", "curiosity"]
                }
            },
            "required": []
        },
        handler=lambda params: track_growth_handler(qube, params)
    ))

    # Moon 4.2: Bias Detection
    registry.register(ToolDefinition(
        name="detect_bias",
        description="Analyze decision patterns to find potential biases, blind spots, or repeated assumptions.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Optional domain to focus bias detection on"
                }
            },
            "required": []
        },
        handler=lambda params: detect_bias_handler(qube, params)
    ))

    # Planet 5: Knowledge Synthesis
    registry.register(ToolDefinition(
        name="synthesize_learnings",
        description="Find connections between different topics in memory. Generate novel insights by combining knowledge.",
        parameters={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2+ topics to find connections between",
                    "minItems": 2
                }
            },
            "required": ["topics"]
        },
        handler=lambda params: synthesize_learnings_handler(qube, params)
    ))

    # Moon 5.1: Cross-Pollinate
    registry.register(ToolDefinition(
        name="cross_pollinate",
        description="Find unexpected connections from different domains. Discover surprising links between unrelated areas.",
        parameters={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "Starting idea or concept to find cross-domain connections for"
                }
            },
            "required": ["idea"]
        },
        handler=lambda params: cross_pollinate_handler(qube, params)
    ))

    # Moon 5.2: Reflect on Topic
    registry.register(ToolDefinition(
        name="reflect_on_topic",
        description="Synthesize all learnings about a specific topic. Get accumulated wisdom, statistics, and recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to reflect on and synthesize learnings about"
                }
            },
            "required": ["topic"]
        },
        handler=lambda params: reflect_on_topic_handler(qube, params)
    ))
```

---

## 12. Task 1.10: Move describe_my_avatar to Creative Expression

### Update TOOL_TO_SKILL_MAPPING

**File:** `ai/skill_scanner.py`

```python
# Change this:
"describe_my_avatar": "analysis_critique",   # OLD: ai_reasoning → analysis_critique planet

# To this:
"describe_my_avatar": "visual_design",       # NEW: creative_expression → visual_design planet
```

### Update Skill Definitions

**File:** `utils/skill_definitions.py`

In the Creative Expression section, update the Sun tool reward:

```python
# Creative Expression Sun - Add describe_my_avatar as an additional tool
# (The primary Sun tool is still switch_model, but describe_my_avatar also awards CE XP)
```

### Update Frontend

**File:** `qubes-gui/src/data/skillDefinitions.ts`

In the Creative Expression category, update the visual_design planet:

```typescript
{
  id: 'visual_design',
  name: 'Visual Design',
  nodeType: 'planet',
  parentId: 'creative_expression',
  xpRequired: 500,
  toolUnlock: 'describe_my_avatar',  // Changed from design_critique
  icon: '🎨',
  description: 'Create visually appealing designs and describe visual elements',
}
```

---

## 13. Task 1.11: Frontend Synchronization

### Update TypeScript Skill Definitions

**File:** `qubes-gui/src/data/skillDefinitions.ts`

Replace the entire AI Reasoning category:

```typescript
// ===== AI REASONING (14 skills) =====
// Theme: Learning From Experience

// Sun
{
  id: 'ai_reasoning',
  name: 'AI Reasoning',
  nodeType: 'sun',
  xpRequired: 1000,
  toolUnlock: 'recall_similar',
  icon: '🧠',
  description: 'Master learning from experience through memory chain analysis',
},

// Planet 1: Pattern Recognition
{
  id: 'pattern_recognition',
  name: 'Pattern Recognition',
  nodeType: 'planet',
  parentId: 'ai_reasoning',
  xpRequired: 500,
  toolUnlock: 'find_analogy',
  icon: '🔍',
  description: 'Finding similar situations in past experience',
},

// Moon 1.1: Trend Detection
{
  id: 'trend_detection',
  name: 'Trend Detection',
  nodeType: 'moon',
  parentId: 'pattern_recognition',
  xpRequired: 250,
  icon: '📈',
  description: 'Spot patterns that repeat or evolve over time',
},

// Moon 1.2: Quick Insight
{
  id: 'quick_insight',
  name: 'Quick Insight',
  nodeType: 'moon',
  parentId: 'pattern_recognition',
  xpRequired: 250,
  icon: '💡',
  description: 'Pull one highly relevant insight from memory',
},

// Planet 2: Learning from Failure
{
  id: 'learning_from_failure',
  name: 'Learning from Failure',
  nodeType: 'planet',
  parentId: 'ai_reasoning',
  xpRequired: 500,
  toolUnlock: 'analyze_mistake',
  icon: '📉',
  description: 'Analyzing past mistakes to avoid repeating them',
},

// Moon 2.1: Root Cause Analysis
{
  id: 'root_cause_analysis',
  name: 'Root Cause Analysis',
  nodeType: 'moon',
  parentId: 'learning_from_failure',
  xpRequired: 250,
  icon: '🔬',
  description: 'Dig past symptoms to find underlying issues',
},

// Planet 3: Building on Success
{
  id: 'building_on_success',
  name: 'Building on Success',
  nodeType: 'planet',
  parentId: 'ai_reasoning',
  xpRequired: 500,
  toolUnlock: 'replicate_success',
  icon: '🏆',
  description: 'Finding what worked and replicating it',
},

// Moon 3.1: Success Factors
{
  id: 'success_factors',
  name: 'Success Factors',
  nodeType: 'moon',
  parentId: 'building_on_success',
  xpRequired: 250,
  icon: '🎯',
  description: 'Identify WHY something worked, not just THAT it worked',
},

// Planet 4: Self-Reflection
{
  id: 'self_reflection',
  name: 'Self-Reflection',
  nodeType: 'planet',
  parentId: 'ai_reasoning',
  xpRequired: 500,
  toolUnlock: 'self_reflect',
  icon: '🪞',
  description: 'Understanding own patterns, biases, and growth',
},

// Moon 4.1: Growth Tracking
{
  id: 'growth_tracking',
  name: 'Growth Tracking',
  nodeType: 'moon',
  parentId: 'self_reflection',
  xpRequired: 250,
  icon: '📊',
  description: 'Compare past vs present performance, see improvement',
},

// Moon 4.2: Bias Detection
{
  id: 'bias_detection',
  name: 'Bias Detection',
  nodeType: 'moon',
  parentId: 'self_reflection',
  xpRequired: 250,
  icon: '⚠️',
  description: 'Identify blind spots and tendencies in own reasoning',
},

// Planet 5: Knowledge Synthesis
{
  id: 'knowledge_synthesis',
  name: 'Knowledge Synthesis',
  nodeType: 'planet',
  parentId: 'ai_reasoning',
  xpRequired: 500,
  toolUnlock: 'synthesize_learnings',
  icon: '🧩',
  description: 'Combining learnings from different experiences into new insights',
},

// Moon 5.1: Cross-Pollinate
{
  id: 'cross_pollinate',
  name: 'Cross-Pollinate',
  nodeType: 'moon',
  parentId: 'knowledge_synthesis',
  xpRequired: 250,
  icon: '🔀',
  description: 'Find unexpected links between different knowledge areas',
},

// Moon 5.2: Reflect on Topic
{
  id: 'reflect_on_topic',
  name: 'Reflect on Topic',
  nodeType: 'moon',
  parentId: 'knowledge_synthesis',
  xpRequired: 250,
  icon: '💭',
  description: 'Get accumulated wisdom on any topic',
},
```

### Update handlers.py SKILL_TREE

**File:** `ai/tools/handlers.py`
**Lines:** 38-59 (replace ai_reasoning array)

Replace with the same structure as the TypeScript above, using Python dict format.

---

## 14. Task 1.12: LEARNING Block Integration

Several AI Reasoning tools should create LEARNING blocks when they generate insights:

### Tools That Create LEARNING Blocks

| Tool | Creates LEARNING | Learning Type | Trigger |
|------|------------------|---------------|---------|
| `recall_similar` | No | - | Read-only |
| `find_analogy` | Optional | `insight` | When strong analogy found |
| `analyze_mistake` | Yes | `insight`, `pattern` | On mistake pattern found |
| `replicate_success` | Yes | `pattern` | On success strategy found |
| `self_reflect` | Yes | `insight` | On self-evaluation complete |
| `synthesize_learnings` | Yes | `synthesis` | On cross-topic connection |

### LEARNING Block Creation Helper

**File:** `ai/tools/handlers.py`

```python
from core.block import BlockType

async def create_learning_block(
    qube,
    learning_type: str,
    content: dict,
    source_block: int = None,
    source_category: str = "ai_reasoning",
    confidence: int = 75
) -> dict:
    """
    Create a LEARNING block to persist knowledge.

    Args:
        qube: Qube instance
        learning_type: One of: fact, procedure, synthesis, insight, pattern, relationship
        content: The learning content
        source_block: Block number that triggered this learning
        source_category: Which Sun/context created this
        confidence: Confidence level 0-100

    Returns:
        Created block info
    """
    if not hasattr(qube, 'session') or not qube.session:
        return {"created": False, "reason": "No active session"}

    learning_content = {
        "learning_type": learning_type,
        "source_block": source_block,
        "source_category": source_category,
        "confidence": confidence,
        **content
    }

    try:
        block = await qube.session.add_block(
            block_type=BlockType.LEARNING,
            content=learning_content
        )

        return {
            "created": True,
            "block_number": block.block_number,
            "learning_type": learning_type
        }
    except Exception as e:
        logger.error(f"Failed to create LEARNING block: {e}")
        return {"created": False, "error": str(e)}
```

### Integration Points

Add LEARNING block creation to these handlers:

```python
# In analyze_mistake_handler, after finding patterns:
if common_patterns and len(mistakes) >= 2:
    await create_learning_block(
        qube=qube,
        learning_type="pattern",
        content={
            "insight": f"Common failure patterns: {', '.join(common_patterns)}",
            "mistakes_analyzed": len(mistakes)
        },
        source_category="ai_reasoning",
        confidence=min(90, 50 + len(mistakes) * 10)
    )

# In synthesize_learnings_handler, after finding connections:
if connection_blocks:
    await create_learning_block(
        qube=qube,
        learning_type="synthesis",
        content={
            "topics": topics,
            "connections": len(connection_blocks),
            "insight": insights[0] if insights else None
        },
        source_category="ai_reasoning",
        confidence=min(90, 50 + len(connection_blocks) * 10)
    )
```

---

## 15. Task 1.13: Testing & Validation

### Unit Tests

**File:** `tests/unit/test_ai_reasoning_tools.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from ai.tools.handlers import (
    recall_similar_handler,
    find_analogy_handler,
    analyze_mistake_handler,
    replicate_success_handler,
    self_reflect_handler,
    detect_trend_handler,
    quick_insight_handler,
    find_root_cause_handler,
    extract_success_factors_handler,
    track_growth_handler,
    detect_bias_handler,
    synthesize_learnings_handler,
    cross_pollinate_handler,
    reflect_on_topic_handler
)


class TestRecallSimilar:
    @pytest.mark.asyncio
    async def test_returns_similar_situations(self):
        """Test that recall_similar returns matching situations"""
        mock_qube = Mock()

        # Mock search results
        mock_results = [
            Mock(
                block={"block_number": 1, "block_type": "MESSAGE",
                       "content": {"text": "Similar situation"}, "timestamp": 1000},
                combined_score=0.8
            )
        ]

        with patch('ai.tools.handlers.intelligent_memory_search',
                   new_callable=AsyncMock, return_value=mock_results):
            result = await recall_similar_handler(mock_qube, {"situation": "test"})

        assert result["success"] is True
        assert len(result["similar_situations"]) == 1
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_requires_situation_param(self):
        """Test that recall_similar requires situation parameter"""
        result = await recall_similar_handler(Mock(), {})
        assert result["success"] is False
        assert "situation" in result["error"].lower()


class TestAnalyzeMistake:
    @pytest.mark.asyncio
    async def test_finds_failures(self):
        """Test that analyze_mistake finds ACTION blocks with success=false"""
        mock_qube = Mock()

        mock_results = [
            Mock(
                block={
                    "block_number": 1,
                    "block_type": "ACTION",
                    "content": {"action_type": "test", "success": False, "result": {"error": "Failed"}},
                    "timestamp": 1000
                },
                combined_score=0.7
            )
        ]

        with patch('ai.tools.handlers.intelligent_memory_search',
                   new_callable=AsyncMock, return_value=mock_results):
            result = await analyze_mistake_handler(mock_qube, {})

        assert result["success"] is True
        assert result["mistakes_found"] >= 1


class TestSelfReflect:
    @pytest.mark.asyncio
    async def test_returns_current_state(self):
        """Test that self_reflect returns current evaluation state"""
        mock_qube = Mock()
        mock_qube.self_evaluation.get_summary.return_value = {
            "overall_score": 75.0,
            "strengths": ["adaptability"],
            "areas_for_improvement": ["consistency"],
            "metrics": {"confidence": 80, "adaptability": 70},
            "evaluation_count": 5
        }
        mock_qube.self_evaluation.get_timeline.return_value = []

        result = await self_reflect_handler(mock_qube, {})

        assert result["success"] is True
        assert "current_state" in result
        assert result["current_state"]["overall_score"] == 75.0


class TestTrackGrowth:
    @pytest.mark.asyncio
    async def test_tracks_single_metric(self):
        """Test tracking a single metric over time"""
        mock_qube = Mock()
        mock_qube.self_evaluation.get_timeline.return_value = [
            {"timestamp": 1000, "metrics": {"confidence": 50}},
            {"timestamp": 2000, "metrics": {"confidence": 60}},
            {"timestamp": 3000, "metrics": {"confidence": 75}}
        ]

        result = await track_growth_handler(mock_qube, {"metric": "confidence"})

        assert result["success"] is True
        assert result["start_value"] == 50
        assert result["current_value"] == 75
        assert result["trend"] == "improving"
```

### Integration Tests

**File:** `tests/integration/test_ai_reasoning_integration.py`

```python
import pytest
from pathlib import Path


class TestAIReasoningIntegration:
    """Integration tests for AI Reasoning tools with real memory chain"""

    @pytest.fixture
    def qube_with_history(self, tmp_path):
        """Create a qube with some history for testing"""
        # Setup qube with test data
        pass

    @pytest.mark.asyncio
    async def test_pattern_recognition_flow(self, qube_with_history):
        """Test recall_similar → find_analogy → detect_trend flow"""
        pass

    @pytest.mark.asyncio
    async def test_learning_block_creation(self, qube_with_history):
        """Test that tools create LEARNING blocks appropriately"""
        pass

    @pytest.mark.asyncio
    async def test_self_reflection_with_history(self, qube_with_history):
        """Test self_reflect with actual evaluation history"""
        pass
```

### Manual Testing Checklist

- [ ] **recall_similar**: Query matches return expected results
- [ ] **find_analogy**: Deep search returns more results than recall_similar
- [ ] **detect_trend**: Time windows show correct distribution
- [ ] **quick_insight**: Returns single most relevant insight
- [ ] **analyze_mistake**: Finds ACTION blocks with success=false
- [ ] **find_root_cause**: Traces back through chain correctly
- [ ] **replicate_success**: Finds ACTION blocks with success=true
- [ ] **extract_success_factors**: Identifies common patterns
- [ ] **self_reflect**: Uses SelfEvaluation.get_summary() correctly
- [ ] **track_growth**: Timeline data visualizes correctly
- [ ] **detect_bias**: Finds repeated patterns in DECISION blocks
- [ ] **synthesize_learnings**: Finds cross-topic connections
- [ ] **cross_pollinate**: Returns different-domain results
- [ ] **reflect_on_topic**: Aggregates all topic data

### XP Award Testing

- [ ] All 14 tools award XP to correct skills
- [ ] XP trickles up: Moon → Planet → Sun
- [ ] `recall_similar` (Sun tool) is always available
- [ ] Planet/Moon tools require parent unlocked

---

## Appendix A: Tool Summary Table

| # | Tool | Type | Parent | XP Skill | LEARNING Created |
|---|------|------|--------|----------|------------------|
| 1 | `recall_similar` | Sun | - | `ai_reasoning` | No |
| 2 | `find_analogy` | Planet | ai_reasoning | `pattern_recognition` | Optional |
| 3 | `detect_trend` | Moon | pattern_recognition | `trend_detection` | No |
| 4 | `quick_insight` | Moon | pattern_recognition | `quick_insight` | No |
| 5 | `analyze_mistake` | Planet | ai_reasoning | `learning_from_failure` | Yes |
| 6 | `find_root_cause` | Moon | learning_from_failure | `root_cause_analysis` | No |
| 7 | `replicate_success` | Planet | ai_reasoning | `building_on_success` | Yes |
| 8 | `extract_success_factors` | Moon | building_on_success | `success_factors` | No |
| 9 | `self_reflect` | Planet | ai_reasoning | `self_reflection` | Yes |
| 10 | `track_growth` | Moon | self_reflection | `growth_tracking` | No |
| 11 | `detect_bias` | Moon | self_reflection | `bias_detection` | No |
| 12 | `synthesize_learnings` | Planet | ai_reasoning | `knowledge_synthesis` | Yes |
| 13 | `cross_pollinate` | Moon | knowledge_synthesis | `cross_pollinate` | No |
| 14 | `reflect_on_topic` | Moon | knowledge_synthesis | `reflect_on_topic` | No |

---

## Appendix B: File Reference

| File | Line Range | Description |
|------|------------|-------------|
| `utils/skill_definitions.py` | 52-70 | AI Reasoning skill definitions |
| `ai/skill_scanner.py` | 44-85 | TOOL_TO_SKILL_MAPPING |
| `ai/tools/handlers.py` | 38-59 | SKILL_TREE (handlers copy) |
| `ai/tools/handlers.py` | 310+ | Tool registrations |
| `ai/tools/registry.py` | 19-41 | ALWAYS_AVAILABLE_TOOLS |
| `ai/tools/memory_search.py` | 385-530 | intelligent_memory_search |
| `relationships/self_evaluation.py` | 18-229 | SelfEvaluation class |
| `qubes-gui/src/data/skillDefinitions.ts` | - | Frontend skill definitions |

---

## Appendix C: Helper Functions

### Required Imports

Add to `ai/tools/handlers.py`:

```python
from datetime import datetime, timezone
from collections import Counter
from ai.tools.memory_search import intelligent_memory_search
from core.block import BlockType
```

### Helper Functions List

| Function | Purpose | Location |
|----------|---------|----------|
| `format_relative_time()` | Convert timestamp to "X ago" string | handlers.py |
| `extract_summary_from_block()` | Get brief summary from any block type | handlers.py |
| `create_learning_block()` | Create LEARNING block to persist insights | handlers.py |

---

## Implementation Order

Recommended order for minimum friction:

1. **Task 1.1** - Skill definitions (foundation)
2. **Task 1.2** - Tool mappings (connects tools to skills)
3. **Task 1.3** - Sun tool `recall_similar` (test infrastructure)
4. **Task 1.4-1.8** - Planets and Moons (can be parallelized)
5. **Task 1.9** - Tool registration (after handlers complete)
6. **Task 1.10** - Move describe_my_avatar (cleanup)
7. **Task 1.11** - Frontend sync (after backend complete)
8. **Task 1.12** - LEARNING integration (enhancement)
9. **Task 1.13** - Testing (validation)

---

**Document Complete**

*Generated for Qubes Skill Tree Implementation*
*Phase 1: AI Reasoning - Learning From Experience*
