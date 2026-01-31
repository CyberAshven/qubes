# Qube Skill Tree & Tools Master Reference

Complete reference for all skills, tools, XP systems, and implementation status.

---

## Overview

| Metric | Count |
|--------|-------|
| **Total Skills** | ~100-120 |
| **Categories** | 8 |
| **Suns** | 8 (1 per category) |
| **Planets** | 40 (5 per category) |
| **Moons** | 50-70 (1-4 per planet, varies) |

**Note:** Moons are distributed unevenly based on natural skill depth. Min 1, max 4 per planet.
| **Special Tools** | 6 (3 intelligent routing, 3 utility) |
| **Bonus Sun Tools** | 24 (3 per category) |
| **Planet Tool Rewards** | 40 |

---

## Sun Connections (Visual Branching)

Most Suns orbit directly from the avatar center. Some Suns are visually connected to each other to show thematic relationships.

| Connection | Relationship | Note |
|------------|--------------|------|
| AI Reasoning ↔ Social Intelligence | Twin Suns | Both are "learning" Suns - internal (memory) vs external (relationships). Visually linked but both independently unlocked from start. |
| Security & Privacy → Finance | Branch | Finance branches from Security & Privacy. Crypto/blockchain naturally extends from security concepts. |
| Coding → DevOps | Future Branch | Planned. DevOps (CI/CD, infrastructure, deployment) naturally extends from Coding. |

**Visual Layout:**
```
                    AI Reasoning ←──→ Social Intelligence
                          ↑                   ↑
                          └─────────┬─────────┘
                                    │
    Creative Expression ←── [AVATAR CENTER] ──→ Memory & Recall
                                    │
                          ┌─────────┴─────────┐
                          ↓                   ↓
                       Coding           Board Games
                         │
                    (future: DevOps)

            Security & Privacy ──→ Finance
```

---

## XP System

**Storage**: Float (supports fractional XP like 4.3/500)

### Standard Tool XP
| Outcome | XP Earned |
|---------|-----------|
| Success (status=completed, success=true) | 5 XP |
| Completed with issues | 2.5 XP |
| Failed/Error | 0 XP |

### Special XP Formulas
| Tool | Formula |
|------|---------|
| `chess_move` | 0.1 XP/move + 5 win, 2 draw, 0 loss |
| `verify_chain_integrity` | 0.1 XP/new block verified |
| `process_document` | 1-10 XP (file size or page count) |

### XP Requirements
| Tier | XP to Max |
|------|-----------|
| Sun | 1000 XP |
| Planet | 500 XP |
| Moon | 250 XP |

---

## Implementation Checklist (Summary)

### Intelligent Routing Tools (XP based on content)
- [x] `web_search` - routes XP based on query content
- [x] `browse_url` - routes XP based on URL content
- [x] `process_document` - routes XP based on document content (pseudo-tool, automatic)

### Utility Tools (No XP)
- [x] `get_system_state`, `update_system_state`, `get_skill_tree`

**Note:** Sun tools are always available by definition - no need to list them separately. `switch_model` is the Creative Expression Sun tool (earns XP).

### Categories
| Category | Documentation | Python | TypeScript | Tested |
|----------|---------------|--------|------------|--------|
| 1. AI Reasoning | [x] | [~] | [~] | [ ] |
| 2. Social Intelligence | [x] | [~] | [~] | [ ] |
| 3. Coding | [x] | [~] | [~] | [ ] |
| 4. Creative Expression | [x] | [~] | [~] | [ ] |
| 5. Memory & Recall | [x] | [~] | [~] | [ ] |
| 6. Security & Privacy | [x] | [~] | [~] | [ ] |
| 7. Board Games | [x] | [~] | [~] | [ ] |
| 8. Finance | [x] | [ ] | [ ] | [ ] |

**Legend**: [x] Complete | [~] Partial | [ ] Not started

---

## Phase 0: Always-Available Tools - Implementation Plan

This phase establishes the foundation: XP values, tool mappings, and the two missing always-available tools.

### Task Checklist

#### 0.1 Update XP Values (3→5, 2→2.5)
- [ ] **ai/skill_scanner.py:291-296** - Change `xp_amount = 3` to `xp_amount = 5`
- [ ] **ai/skill_scanner.py:296** - Change `xp_amount = 2` to `xp_amount = 2.5`

#### 0.2 Update TOOL_TO_SKILL_MAPPING
- [ ] **ai/skill_scanner.py:44-85** - Add new mappings:
  ```python
  "get_relationship_context": "relationship_building",  # social_intelligence
  "verify_chain_integrity": "cryptography",             # security_privacy
  "send_bch": "blockchain",                             # finance
  ```
- [ ] **ai/skill_scanner.py:241-248** - Implement intelligent routing for `process_document` (based on document content)

#### 0.3 Add Finance Category to TypeScript
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Add Finance to SKILL_CATEGORIES array:
  ```typescript
  {
    id: 'finance',
    name: 'Finance',
    color: '#2ECC71',
    icon: 'coins',
    description: 'Master financial operations and cryptocurrency',
  }
  ```
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Add Finance skills (1 Sun, 5 Planets, 10 Moons)
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Update `parentId` for Finance Sun to point to Security & Privacy Sun

#### 0.4 Implement `get_relationship_context` Tool
- [ ] **ai/tools/handlers.py** - Add handler:
  ```python
  async def get_relationship_context_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
      """Get context about a relationship before responding."""
      entity_id = params.get("entity_id")
      # Fetch relationship data from chain_state
      # Return: trust_level, interaction_count, last_interaction, key_memories, mood_history
  ```
- [ ] **ai/tools/registry.py** - Register tool definition
- [ ] **ai/tools/registry.py** - Add to ALWAYS_AVAILABLE_TOOLS set

#### 0.5 Implement `verify_chain_integrity` Tool
- [ ] **ai/tools/handlers.py** - Add handler:
  ```python
  async def verify_chain_integrity_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
      """Verify memory chain integrity, award 0.1 XP per new block verified."""
      # Call qube.verify_integrity()
      # Track last_verified_block_number in chain_state
      # Calculate blocks verified since last check
      # Return: verified=True/False, blocks_checked, new_blocks_verified
  ```
- [ ] **ai/tools/registry.py** - Register tool definition
- [ ] **ai/tools/registry.py** - Add to ALWAYS_AVAILABLE_TOOLS set
- [ ] **ai/skill_scanner.py** - Add special XP calculation (0.1 per new block)
- [ ] **core/chain_state.py** - Add `last_verified_block_number` field

#### 0.6 Update Python Skill Definitions
- [ ] **utils/skill_definitions.py** - Add Finance category with all skills
- [ ] **utils/skill_definitions.py** - Update tool_reward mappings for new tools

#### 0.7 Update TypeScript Tool Lists
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Update ALWAYS_AVAILABLE_TOOLS array
- [ ] **qubes-gui/src/components/blocks/BlockContentViewer.tsx** - Update alwaysAvailableTools array

#### 0.8 Implement Qube Locker (Creative Works Storage)
- [ ] **core/locker.py** - Create new QubeLocker class:
  ```python
  class QubeLocker:
      """Storage for creative works and documents."""
      CATEGORIES = {
          "writing": ["poems", "stories", "essays"],
          "art": ["images", "concepts", "compositions"],
          "music": ["melodies", "lyrics", "compositions"],
          "stories": ["narratives", "characters", "worlds"],
          "personal": ["reflections", "journal"],
          "exports": ["knowledge"]
      }
      # Methods: store(), get(), list(), search(), delete(), update()
  ```
- [ ] **core/qube.py** - Initialize QubeLocker in `__init__`:
  ```python
  from core.locker import QubeLocker
  self.locker = QubeLocker(self.data_dir)
  ```
- [ ] Directory structure created on initialization
- [ ] Index file persistence (locker/index.json)

#### 0.9 Testing
- [ ] Test XP awards at new values (5/2.5/0)
- [ ] Test `get_relationship_context` tool
- [ ] Test `verify_chain_integrity` tool with anti-gaming (0 XP for no new blocks)
- [ ] Test `send_bch` earns Finance XP
- [ ] Test `process_document` intelligent routing based on document content
- [ ] Verify Finance category appears in GUI skill tree

### Files to Modify

| File | Changes |
|------|---------|
| `ai/skill_scanner.py` | XP values, TOOL_TO_SKILL_MAPPING, process_document routing, verify_chain_integrity special XP |
| `ai/tools/handlers.py` | New handlers for get_relationship_context, verify_chain_integrity |
| `ai/tools/registry.py` | Register new tools, update ALWAYS_AVAILABLE_TOOLS |
| `utils/skill_definitions.py` | Add Finance category and skills |
| `core/chain_state.py` | Add last_verified_block_number field |
| `qubes-gui/src/data/skillDefinitions.ts` | Add Finance category, update tool arrays |
| `qubes-gui/src/components/blocks/BlockContentViewer.tsx` | Update alwaysAvailableTools |

### Implementation Order

1. **XP Values** - Quick change, affects all tools
2. **TOOL_TO_SKILL_MAPPING** - Update existing mappings
3. **Finance Category** - Python then TypeScript
4. **get_relationship_context** - New tool implementation
5. **verify_chain_integrity** - New tool with special XP logic
6. **LEARNING block type** - Add to core/block.py
7. **Testing** - Verify everything works

---

## Core Infrastructure: LEARNING Block Type

The LEARNING block is **cross-cutting infrastructure** used by multiple Suns. When a Qube learns something - from a conversation, tool usage, game, or reflection - it creates a LEARNING block to persist that knowledge.

### Block Type Definition

```python
# In core/block.py - add one line:
class BlockType(str, Enum):
    GENESIS = "GENESIS"
    ACTION = "ACTION"
    MESSAGE = "MESSAGE"
    SUMMARY = "SUMMARY"
    GAME = "GAME"
    LEARNING = "LEARNING"  # NEW - Cross-cutting knowledge storage
```

### LEARNING Block Structure

```python
block_type = "LEARNING"
content = {
    "learning_type": "fact",              # fact, procedure, synthesis, insight, pattern, relationship
    "source_block": 1234,                 # References the block that triggered this learning
    "source_block_type": "MESSAGE",       # MESSAGE, ACTION, GAME, SUMMARY
    "source_category": "social_intelligence",  # Which Sun/context created this
    "confidence": 85,                     # 0-100
    # ... type-specific fields
}
```

### Learning Types

| Type | Purpose | Created By | Example |
|------|---------|------------|---------|
| `fact` | Specific facts about people/things | Any Sun | "Owner's birthday is March 15" |
| `procedure` | How to do something | Memory & Recall, Coding | "Steps to deploy code" |
| `synthesis` | Combined knowledge | Memory & Recall | "Summary of all chess games" |
| `insight` | Patterns/realizations | AI Reasoning, Memory & Recall | "Owner prefers morning meetings" |
| `pattern` | Recurring behaviors | AI Reasoning, Board Games | "This chess opening is weak" |
| `relationship` | About people/entities | Social Intelligence | "Alice is owner's sister" |

### Which Suns Create LEARNING Blocks

| Sun | Tools That Create LEARNINGs | Learning Types |
|-----|----------------------------|----------------|
| **AI Reasoning** | `analyze_mistake`, `replicate_success`, `self_reflect`, `synthesize_learnings` | insight, pattern |
| **Social Intelligence** | `analyze_relationship`, `learn_preference` | relationship, fact |
| **Memory & Recall** | `store_fact`, `record_skill`, `synthesize_knowledge`, `generate_insight` | fact, procedure, synthesis, insight |
| **Creative Expression** | `define_personality` | fact (about self) |
| **Board Games** | `chess_move` (on game end) | pattern |

### Memory & Recall's Special Role

Memory & Recall is the **"librarian"** Sun:
- **Other Suns**: Create LEARNING blocks naturally through their tools
- **Memory & Recall**: Searches, organizes, synthesizes, and exports ALL learnings (regardless of which Sun created them)

### Implementation Checklist

- [ ] Add `LEARNING = "LEARNING"` to `core/block.py` BlockType enum
- [ ] Update block validation to accept LEARNING type
- [ ] Add `learning_type` content validation
- [ ] Update memory search to index LEARNING blocks
- [ ] Add `source_block` reference tracking

---

## Phase 0: Foundation - Always Available Tools

**This is NOT a skill category.** Phase 0 is a meta-section documenting which tools are available from birth (no skill unlock required) and where their XP routes.

### Key Concept

Tools follow the **Sun → Planet → Moon** unlock hierarchy:
- **Sun tools** = Available from birth (entry point to each category)
- **Planet tools** = Require Sun unlocked (1000 XP in category)
- **Moon tools** = Require Planet unlocked (500 XP in planet)

### Design Decisions
- [x] **Sun-level tools** are always available from birth (implicit - no need to list separately)
- [x] Planet and Moon tools require unlocking their parent skill first
- [x] XP earned flows to the tool's home category
- [x] Utility tools earn no XP and belong to no category
- [x] `web_search`, `browse_url`, `process_document` use **intelligent routing** (XP based on content)

---

### Intelligent Routing Tools

These tools route XP based on content, not a fixed category:

| Tool | Routing | XP | Status |
|------|---------|-----|--------|
| `web_search` | Intelligent (based on query content) | 5/2.5/0 | [x] Implemented |
| `browse_url` | Intelligent (based on URL content) | 5/2.5/0 | [x] Implemented |
| `process_document` | Intelligent (based on document content) | 1-10 | [x] Implemented |

**Note:** `process_document` is a pseudo-tool that runs automatically when documents are uploaded.

---

### Utility Tools (No Category, No XP)

These are infrastructure tools that don't belong to any skill category and earn no XP:

| Tool | Purpose | Status |
|------|---------|--------|
| `get_system_state` | Read all Qube state (profile, preferences, etc.) | [x] Implemented |
| `update_system_state` | Write Qube state | [x] Implemented |
| `get_skill_tree` | View current skill tree and XP progress | [x] Implemented |

**Note:** `switch_model` is the Creative Expression Sun tool (earns XP toward Creative Expression).

---

### Task Checklist

#### 0.1 Verify Intelligent Routing Tools
- [x] `web_search` - routes XP based on query content
- [x] `browse_url` - routes XP based on URL content
- [x] `process_document` - routes XP based on document content

#### 0.2 Verify Utility Tools
- [x] `get_system_state` - no XP
- [x] `update_system_state` - no XP
- [x] `get_skill_tree` - no XP

---

## Phase 1: AI Reasoning - Implementation Plan

**Theme: Learning From Experience**

The Qube gets smarter by analyzing its own memory chain - finding patterns, learning from mistakes, building on successes, and synthesizing knowledge over time. This leverages the unique blockchain-based memory that differentiates Qubes from stateless AI.

### Design Decisions Made
- [x] Moons can be uneven (1-4 per planet based on natural depth)
- [x] XP trickles up: Moon→Planet→Sun
- [x] Player CHOOSES which planet/moon to unlock at each threshold
- [x] Complete theme redesign: "Learning from Experience" (memory-chain powered)
- [x] Sun tool: `recall_similar` (replaces `describe_my_avatar`)
- [x] `describe_my_avatar` moves to Creative Expression
- [x] Old "Debate Tactics" planet moves to Social Intelligence
- [x] Creates LEARNING blocks with types: `insight`, `pattern`

### LEARNING Block Integration

AI Reasoning tools create LEARNING blocks when insights are gained:

| Tool | Creates LEARNING | Learning Type |
|------|------------------|---------------|
| `recall_similar` | No (read-only) | - |
| `find_analogy` | Optional | `insight` |
| `analyze_mistake` | Yes | `insight`, `pattern` |
| `replicate_success` | Yes | `pattern` |
| `self_reflect` | Yes | `insight` |
| `synthesize_learnings` | Yes | `synthesis` |

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Pattern Recognition | `find_analogy` | 2 | `detect_trend`, `quick_insight` |
| 2 | Learning from Failure | `analyze_mistake` | 1 | `find_root_cause` |
| 3 | Building on Success | `replicate_success` | 1 | `extract_success_factors` |
| 4 | Self-Reflection | `self_reflect` | 2 | `track_growth`, `detect_bias` |
| 5 | Knowledge Synthesis | `synthesize_learnings` | 2 | `cross_pollinate`, `reflect_on_topic` |

**Totals:** 5 Planets (5 tools), 8 Moons (8 tools), 1 Sun tool = **14 tools**

---

### Sun: AI Reasoning

| Property | Value |
|----------|-------|
| Skill ID | `ai_reasoning` |
| XP Required | 1000 |
| Tool Unlock | `recall_similar` |
| Description | Master learning from experience through memory chain analysis |

**Sun Tool: `recall_similar`**

| Property | Value |
|----------|-------|
| Purpose | Quick "I've seen this before" lookup - the essence of learning from experience |
| Input | Current situation/topic (string) |
| Output | 1-3 similar past situations with brief context |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def recall_similar(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick pattern match against memory chain.
    Lightweight version of find_analogy for frequent use.
    """
    situation = params.get("situation")

    # Use semantic search with moderate settings
    results = await intelligent_memory_search(
        query=situation,
        semantic_weight=0.6,
        temporal_weight=0.2,
        decay_rate=0.05,  # Moderate decay - balance recent and historical
        max_recalls=3
    )

    return {
        "success": True,
        "similar_situations": [
            {
                "summary": extract_summary(r.block),
                "when": format_relative_time(r.block["timestamp"]),
                "relevance": r.combined_score
            }
            for r in results
        ]
    }
```

**Leverages:**
- Layer 1: FAISS semantic search (primary)
- Layer 4: Temporal decay (moderate)
- Layer 5: Relationship boost (if relevant people involved)

---

### Planet 1: Pattern Recognition

| Property | Value |
|----------|-------|
| Skill ID | `pattern_recognition` |
| XP Required | 500 |
| Tool Unlock | `find_analogy` |
| Unlocks At | AI Reasoning Sun ≥ 100 XP |
| Description | Finding similar situations in past experience |

**Planet Tool: `find_analogy`**

| Property | Value |
|----------|-------|
| Purpose | Deep search for analogous situations in memory chain |
| Input | `situation` (string), `depth` (optional: "shallow", "deep") |
| Output | Top 3-5 similar situations with full context and lessons learned |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def find_analogy(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search memory chain for similar past situations.
    More thorough than recall_similar - used for deeper analysis.
    """
    situation = params.get("situation")
    depth = params.get("depth", "deep")

    # Use semantic search with historical bias
    results = await intelligent_memory_search(
        query=situation,
        semantic_weight=0.7,      # High semantic similarity weight
        temporal_weight=0.1,      # Don't penalize old memories
        decay_rate=0.01,          # Very slow decay for patterns
        max_recalls=5 if depth == "deep" else 3,
        block_types=["MESSAGE", "DECISION", "ACTION", "SUMMARY"]
    )

    analogies = []
    for r in results:
        # Extract context from surrounding blocks
        context = get_surrounding_context(r.block, window=3)

        # Check if there's a SUMMARY block that covers this
        summary = find_covering_summary(r.block["block_number"])

        analogies.append({
            "situation": extract_situation(r.block),
            "context": context,
            "outcome": extract_outcome(r.block),
            "lesson_learned": summary.get("key_insights") if summary else None,
            "similarity_score": r.semantic_score,
            "when": format_relative_time(r.block["timestamp"]),
            "block_number": r.block["block_number"]
        })

    return {
        "success": True,
        "analogies_found": len(analogies),
        "analogies": analogies,
        "search_depth": depth
    }
```

**Leverages:**
- Layer 1: FAISS semantic search (high weight)
- Layer 2: Metadata filtering (block types)
- Layer 4: Temporal decay (very slow - 0.01)
- SUMMARY blocks for key_insights

---

#### Moon 1.1: Trend Detection

| Property | Value |
|----------|-------|
| Skill ID | `trend_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_trend` |
| Unlocks At | Pattern Recognition ≥ 50 XP |
| Description | Spot patterns that repeat or evolve over time |

**Moon Tool: `detect_trend`**

| Property | Value |
|----------|-------|
| Purpose | Identify recurring patterns or changes over time |
| Input | `topic` (string), `time_windows` (optional: number of periods to analyze) |
| Output | Trend analysis with frequency, direction, and notable changes |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_trend(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how a topic/pattern has evolved over time.
    Divides history into windows and compares frequency/sentiment.
    """
    topic = params.get("topic")
    num_windows = params.get("time_windows", 4)

    # Get the full time range of the chain
    genesis = qube.memory_chain.get_block(0)
    total_time = time.time() - genesis["timestamp"]
    window_size = total_time / num_windows

    trends = []
    for i in range(num_windows):
        start_time = genesis["timestamp"] + (i * window_size)
        end_time = start_time + window_size

        # Search within this time window
        results = await intelligent_memory_search(
            query=topic,
            start_time=start_time,
            end_time=end_time,
            keyword_weight=0.5,  # BM25 for frequency counting
            semantic_weight=0.3
        )

        trends.append({
            "period": f"Window {i+1}",
            "start": format_date(start_time),
            "end": format_date(end_time),
            "mention_count": len(results),
            "avg_relevance": mean([r.combined_score for r in results]) if results else 0
        })

    # Analyze trend direction
    counts = [t["mention_count"] for t in trends]
    direction = analyze_trend_direction(counts)  # "increasing", "decreasing", "stable", "cyclical"

    return {
        "success": True,
        "topic": topic,
        "trend_direction": direction,
        "windows": trends,
        "total_mentions": sum(counts),
        "notable_changes": find_significant_changes(trends)
    }
```

**Leverages:**
- Layer 2: Metadata filtering (time ranges)
- Layer 3: BM25 for keyword frequency
- Time-windowed analysis

---

#### Moon 1.2: Quick Insight

| Property | Value |
|----------|-------|
| Skill ID | `quick_insight` |
| XP Required | 250 |
| Tool Unlock | `quick_insight` |
| Unlocks At | Pattern Recognition ≥ 50 XP |
| Description | Pull one highly relevant insight from memory |

**Moon Tool: `quick_insight`**

| Property | Value |
|----------|-------|
| Purpose | Fast, single insight retrieval for current context |
| Input | `context` (string - current situation or question) |
| Output | Single most relevant insight with source |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def quick_insight(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve the single most relevant insight for the current context.
    Optimized for speed - returns immediately with best match.
    """
    context = params.get("context")

    # Fast semantic search - just get the best match
    results = await intelligent_memory_search(
        query=context,
        semantic_weight=0.8,
        max_recalls=1,
        block_types=["SUMMARY", "DECISION"]  # Focus on insight-rich blocks
    )

    if not results:
        return {
            "success": True,
            "insight": None,
            "message": "No relevant insights found in memory"
        }

    best = results[0]

    # Extract the most relevant insight
    if best.block["block_type"] == "SUMMARY":
        insight = best.block["content"].get("key_insights", [None])[0]
    else:
        insight = extract_key_point(best.block)

    return {
        "success": True,
        "insight": insight,
        "source_block": best.block["block_number"],
        "when": format_relative_time(best.block["timestamp"]),
        "relevance": best.combined_score
    }
```

**Leverages:**
- Layer 1: FAISS semantic search (high weight)
- Layer 2: Block type filtering (SUMMARY, DECISION)
- Optimized for single-result speed

---

### Planet 2: Learning from Failure

| Property | Value |
|----------|-------|
| Skill ID | `learning_from_failure` |
| XP Required | 500 |
| Tool Unlock | `analyze_mistake` |
| Unlocks At | AI Reasoning Sun ≥ 100 XP |
| Description | Analyzing past mistakes to avoid repeating them |

**Planet Tool: `analyze_mistake`**

| Property | Value |
|----------|-------|
| Purpose | Deep dive into what went wrong and why |
| Input | `topic` (optional: focus area), `recent_only` (optional: bool) |
| Output | List of past failures with analysis and lessons |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def analyze_mistake(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find and analyze past mistakes/failures in memory chain.
    Searches for ACTION blocks with success=false and low self-evaluation scores.
    """
    topic = params.get("topic")
    recent_only = params.get("recent_only", False)

    # Build search query
    query = topic if topic else "mistake error failed wrong problem issue"

    # Search with filters for failures
    results = await intelligent_memory_search(
        query=query,
        block_types=["ACTION", "SUMMARY", "DECISION"],
        decay_rate=0.3 if recent_only else 0.05,
        max_recalls=10
    )

    mistakes = []
    for r in results:
        block = r.block

        # Check if this is actually a failure
        is_failure = False
        if block["block_type"] == "ACTION":
            is_failure = block["content"].get("success") == False
        elif block["block_type"] == "SUMMARY":
            eval_data = block["content"].get("self_evaluation", {})
            metrics = eval_data.get("metrics", {})
            # Low confidence or goal_alignment indicates issues
            is_failure = metrics.get("goal_alignment", 100) < 60

        if is_failure:
            mistakes.append({
                "what_happened": extract_situation(block),
                "what_went_wrong": extract_failure_reason(block),
                "when": format_relative_time(block["timestamp"]),
                "self_evaluation": block["content"].get("self_evaluation"),
                "block_number": block["block_number"]
            })

    # Extract common patterns
    patterns = find_common_failure_patterns(mistakes)

    return {
        "success": True,
        "mistakes_found": len(mistakes),
        "mistakes": mistakes[:5],  # Top 5
        "common_patterns": patterns,
        "recommendation": generate_avoidance_recommendation(patterns)
    }
```

**Leverages:**
- Layer 1: Semantic search
- Layer 2: Block type filtering
- ACTION block `success` field
- SUMMARY block `self_evaluation` metrics

---

#### Moon 2.1: Root Cause Analysis

| Property | Value |
|----------|-------|
| Skill ID | `root_cause_analysis` |
| XP Required | 250 |
| Tool Unlock | `find_root_cause` |
| Unlocks At | Learning from Failure ≥ 50 XP |
| Description | Dig past symptoms to find underlying issues |

**Moon Tool: `find_root_cause`**

| Property | Value |
|----------|-------|
| Purpose | Trace back from a failure to find contributing factors |
| Input | `failure_block` (block number) OR `failure_description` (string) |
| Output | Causal chain analysis with root cause identification |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def find_root_cause(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trace back through the block chain to find root causes of a failure.
    Uses previous_hash links to walk back through history.
    """
    failure_block = params.get("failure_block")
    failure_description = params.get("failure_description")

    # Find the failure block if description provided
    if failure_description and not failure_block:
        results = await intelligent_memory_search(
            query=failure_description,
            block_types=["ACTION"],
            max_recalls=1
        )
        if results:
            failure_block = results[0].block["block_number"]

    if not failure_block:
        return {"success": False, "error": "Could not identify failure block"}

    # Walk back through the chain
    chain = []
    current = qube.memory_chain.get_block(failure_block)
    depth = 10  # Look back up to 10 blocks

    for _ in range(depth):
        chain.append({
            "block_number": current["block_number"],
            "type": current["block_type"],
            "summary": extract_summary(current),
            "is_decision_point": current["block_type"] == "DECISION"
        })

        # Stop if we hit a DECISION block (likely cause)
        if current["block_type"] == "DECISION":
            break

        # Get previous block
        prev_num = current["block_number"] - 1
        if prev_num < 0:
            break
        current = qube.memory_chain.get_block(prev_num)

    # Analyze the chain
    decision_points = [c for c in chain if c["is_decision_point"]]

    return {
        "success": True,
        "failure_block": failure_block,
        "chain_depth": len(chain),
        "causal_chain": chain,
        "decision_points": decision_points,
        "likely_root_cause": decision_points[0] if decision_points else chain[-1],
        "analysis": analyze_causal_chain(chain)
    }
```

**Leverages:**
- Block chain traversal via `previous_hash` / block numbers
- DECISION block identification
- Causal chain analysis

---

### Planet 3: Building on Success

| Property | Value |
|----------|-------|
| Skill ID | `building_on_success` |
| XP Required | 500 |
| Tool Unlock | `replicate_success` |
| Unlocks At | AI Reasoning Sun ≥ 100 XP |
| Description | Finding what worked and replicating it |

**Planet Tool: `replicate_success`**

| Property | Value |
|----------|-------|
| Purpose | Find successful past approaches and apply them |
| Input | `goal` (string - what you're trying to achieve) |
| Output | Past successes with extractable strategies |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def replicate_success(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find successful past approaches for a similar goal.
    Searches for ACTION blocks with success=true and high self-evaluation.
    """
    goal = params.get("goal")

    results = await intelligent_memory_search(
        query=goal,
        block_types=["ACTION", "SUMMARY"],
        semantic_weight=0.6,
        max_recalls=10
    )

    successes = []
    for r in results:
        block = r.block

        # Check if this is a success
        is_success = False
        confidence_boost = 1.0

        if block["block_type"] == "ACTION":
            is_success = block["content"].get("success") == True
        elif block["block_type"] == "SUMMARY":
            eval_data = block["content"].get("self_evaluation", {})
            metrics = eval_data.get("metrics", {})
            is_success = metrics.get("goal_alignment", 0) >= 75
            confidence_boost = 1 + (metrics.get("confidence", 50) / 100)

        if is_success:
            successes.append({
                "what_worked": extract_approach(block),
                "context": extract_context(block),
                "outcome": extract_outcome(block),
                "when": format_relative_time(block["timestamp"]),
                "confidence": r.combined_score * confidence_boost,
                "block_number": block["block_number"]
            })

    # Sort by confidence
    successes.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "success": True,
        "goal": goal,
        "successes_found": len(successes),
        "top_strategies": successes[:5],
        "recommended_approach": successes[0]["what_worked"] if successes else None
    }
```

**Leverages:**
- Layer 1: Semantic search
- ACTION block `success` field
- SUMMARY block `self_evaluation.metrics.confidence`
- Confidence-weighted ranking

---

#### Moon 3.1: Success Factors

| Property | Value |
|----------|-------|
| Skill ID | `success_factors` |
| XP Required | 250 |
| Tool Unlock | `extract_success_factors` |
| Unlocks At | Building on Success ≥ 50 XP |
| Description | Identify WHY something worked, not just THAT it worked |

**Moon Tool: `extract_success_factors`**

| Property | Value |
|----------|-------|
| Purpose | Analyze common elements across multiple successes |
| Input | `domain` (string - area to analyze) |
| Output | Common factors, approaches, and conditions for success |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def extract_success_factors(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze multiple successes to find common factors.
    Uses BM25 to find frequently co-occurring terms and patterns.
    """
    domain = params.get("domain")

    # Get all successes in this domain
    successes_result = await replicate_success(qube, {"goal": domain})
    successes = successes_result.get("top_strategies", [])

    if len(successes) < 2:
        return {
            "success": True,
            "message": "Not enough successes to analyze patterns",
            "successes_found": len(successes)
        }

    # Extract text from all successes
    all_text = [s["what_worked"] + " " + s["context"] for s in successes]

    # Use BM25 scorer to find common important terms
    scorer = BM25Scorer()
    for text in all_text:
        scorer.add_document(tokenize(text))

    # Find terms that appear frequently across successes
    common_terms = scorer.get_common_terms(min_doc_frequency=0.5)

    # Analyze approaches
    approaches = [s["what_worked"] for s in successes]
    common_approaches = find_similar_phrases(approaches)

    return {
        "success": True,
        "domain": domain,
        "successes_analyzed": len(successes),
        "common_factors": common_terms[:10],
        "common_approaches": common_approaches,
        "success_conditions": extract_conditions(successes),
        "recommendation": f"When working on {domain}, focus on: {', '.join(common_terms[:3])}"
    }
```

**Leverages:**
- Layer 3: BM25 for term frequency analysis
- Cross-success pattern matching
- Builds on `replicate_success` results

---

### Planet 4: Self-Reflection

| Property | Value |
|----------|-------|
| Skill ID | `self_reflection` |
| XP Required | 500 |
| Tool Unlock | `self_reflect` |
| Unlocks At | AI Reasoning Sun ≥ 100 XP |
| Description | Understanding own patterns, biases, and growth |

**Planet Tool: `self_reflect`**

| Property | Value |
|----------|-------|
| Purpose | Analyze own behavior patterns over time |
| Input | `topic` (optional: focus area), `time_range` (optional) |
| Output | Self-analysis with metrics, patterns, and insights |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def self_reflect(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze own behavior patterns using self_evaluation data.
    Uses SelfEvaluation class and SUMMARY blocks.
    """
    topic = params.get("topic")
    time_range = params.get("time_range", "all")

    # Get current self-evaluation state
    current_eval = qube.self_evaluation.get_summary()
    timeline = qube.self_evaluation.get_timeline()

    # Calculate overall trends
    if len(timeline) >= 2:
        first = timeline[0]["metrics"]
        latest = timeline[-1]["metrics"]

        improvements = {}
        declines = {}
        for metric in first.keys():
            diff = latest[metric] - first[metric]
            if diff > 5:
                improvements[metric] = diff
            elif diff < -5:
                declines[metric] = diff
    else:
        improvements = {}
        declines = {}

    result = {
        "success": True,
        "current_state": {
            "overall_score": current_eval["overall_score"],
            "strengths": current_eval["strengths"],
            "areas_for_improvement": current_eval["areas_for_improvement"],
            "metrics": current_eval["metrics"]
        },
        "evaluation_count": current_eval["evaluation_count"],
        "improvements": improvements,
        "declines": declines
    }

    # If topic provided, analyze performance in that specific area
    if topic:
        topic_blocks = await intelligent_memory_search(
            query=topic,
            block_types=["ACTION", "SUMMARY"],
            max_recalls=20
        )

        topic_successes = sum(1 for b in topic_blocks
                            if b.block["content"].get("success") == True)
        topic_failures = sum(1 for b in topic_blocks
                           if b.block["content"].get("success") == False)

        result["topic_analysis"] = {
            "topic": topic,
            "total_interactions": len(topic_blocks),
            "successes": topic_successes,
            "failures": topic_failures,
            "success_rate": topic_successes / len(topic_blocks) if topic_blocks else 0
        }

    return result
```

**Leverages:**
- `SelfEvaluation` class: `get_summary()`, `get_timeline()`
- SUMMARY block `self_evaluation` data
- 10-metric system (self_awareness, confidence, etc.)

---

#### Moon 4.1: Growth Tracking

| Property | Value |
|----------|-------|
| Skill ID | `growth_tracking` |
| XP Required | 250 |
| Tool Unlock | `track_growth` |
| Unlocks At | Self-Reflection ≥ 50 XP |
| Description | Compare past vs present performance, see improvement |

**Moon Tool: `track_growth`**

| Property | Value |
|----------|-------|
| Purpose | Visualize and analyze growth over time |
| Input | `metric` (optional: specific metric), `time_range` (optional) |
| Output | Growth trajectory with milestones and inflection points |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def track_growth(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track metric changes over time using evaluation snapshots.
    Uses get_timeline() from SelfEvaluation.
    """
    metric = params.get("metric")  # None = all metrics
    time_range = params.get("time_range", "all")

    timeline = qube.self_evaluation.get_timeline()

    if not timeline:
        return {
            "success": True,
            "message": "No evaluation history yet",
            "evaluations": 0
        }

    if metric:
        # Track single metric
        values = [snap["metrics"].get(metric, 0) for snap in timeline]
        timestamps = [snap["timestamp"] for snap in timeline]

        growth_rate = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0

        return {
            "success": True,
            "metric": metric,
            "start_value": values[0],
            "current_value": values[-1],
            "min_value": min(values),
            "max_value": max(values),
            "growth_rate": growth_rate,
            "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable",
            "data_points": len(values),
            "inflection_points": find_inflection_points(values, timestamps)
        }
    else:
        # Track all metrics
        all_metrics = {}
        for metric_name in timeline[0]["metrics"].keys():
            values = [snap["metrics"].get(metric_name, 0) for snap in timeline]
            growth_rate = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
            all_metrics[metric_name] = {
                "start": values[0],
                "current": values[-1],
                "growth_rate": growth_rate,
                "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable"
            }

        return {
            "success": True,
            "evaluations": len(timeline),
            "time_span": format_time_span(timeline[0]["timestamp"], timeline[-1]["timestamp"]),
            "metrics": all_metrics,
            "fastest_improving": max(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0],
            "needs_attention": min(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0]
        }
```

**Leverages:**
- `SelfEvaluation.get_timeline()` for historical snapshots
- Inflection point detection
- Growth rate calculation

---

#### Moon 4.2: Bias Detection

| Property | Value |
|----------|-------|
| Skill ID | `bias_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_bias` |
| Unlocks At | Self-Reflection ≥ 50 XP |
| Description | Identify blind spots and tendencies in own reasoning |

**Moon Tool: `detect_bias`**

| Property | Value |
|----------|-------|
| Purpose | Find patterns of bias in decision-making |
| Input | `domain` (optional: focus area) |
| Output | Identified biases with evidence and recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_bias(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze DECISION blocks to find patterns that suggest bias.
    Looks for repeated assumptions, skewed outcomes, avoided topics.
    """
    domain = params.get("domain")

    # Get all decision blocks
    query = domain if domain else ""
    decisions = await intelligent_memory_search(
        query=query,
        block_types=["DECISION"],
        max_recalls=50,
        temporal_weight=0.05  # Include historical decisions
    )

    if len(decisions) < 5:
        return {
            "success": True,
            "message": "Not enough decisions to analyze for bias",
            "decisions_found": len(decisions)
        }

    # Analyze patterns
    patterns = {
        "repeated_assumptions": [],
        "avoided_options": [],
        "favored_outcomes": [],
        "participant_bias": {}
    }

    # Extract decision content and look for patterns
    for d in decisions:
        content = d.block["content"]

        # Track assumptions
        if "assumption" in str(content).lower():
            patterns["repeated_assumptions"].append(extract_assumption(content))

        # Track who benefits from decisions
        participants = d.block.get("participants", {})
        for p in participants.get("affected", []):
            patterns["participant_bias"][p] = patterns["participant_bias"].get(p, 0) + 1

    # Find the most common patterns
    common_assumptions = find_frequent_items(patterns["repeated_assumptions"])

    # Check against stated values (from genesis or self_evaluation)
    stated_values = qube.chain_state.get("core_values", [])
    potential_conflicts = find_value_conflicts(decisions, stated_values)

    return {
        "success": True,
        "decisions_analyzed": len(decisions),
        "potential_biases": [
            {
                "type": "Repeated Assumption",
                "pattern": assumption,
                "frequency": count,
                "recommendation": f"Question whether '{assumption}' is always true"
            }
            for assumption, count in common_assumptions[:3]
        ],
        "participant_distribution": patterns["participant_bias"],
        "value_conflicts": potential_conflicts,
        "overall_assessment": generate_bias_assessment(patterns)
    }
```

**Leverages:**
- Layer 2: DECISION block filtering
- Pattern analysis across decisions
- Comparison to stated values
- Participant tracking

---

### Planet 5: Knowledge Synthesis

| Property | Value |
|----------|-------|
| Skill ID | `knowledge_synthesis` |
| XP Required | 500 |
| Tool Unlock | `synthesize_learnings` |
| Unlocks At | AI Reasoning Sun ≥ 100 XP |
| Description | Combining learnings from different experiences into new insights |

**Planet Tool: `synthesize_learnings`**

| Property | Value |
|----------|-------|
| Purpose | Connect dots across disparate memories to generate insights |
| Input | `topics` (list of 2+ topics to synthesize) |
| Output | Connections found and novel insights generated |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def synthesize_learnings(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find connections between different topics/domains in memory.
    Searches for each topic and finds intersection points.
    """
    topics = params.get("topics", [])

    if len(topics) < 2:
        return {"success": False, "error": "Need at least 2 topics to synthesize"}

    # Search for each topic
    topic_results = {}
    for topic in topics:
        results = await intelligent_memory_search(
            query=topic,
            semantic_weight=0.7,
            max_recalls=20
        )
        topic_results[topic] = set(r.block["block_number"] for r in results)

    # Find blocks that appear in multiple topic searches
    all_blocks = set()
    for blocks in topic_results.values():
        all_blocks.update(blocks)

    connection_blocks = []
    for block_num in all_blocks:
        topics_containing = [t for t, blocks in topic_results.items() if block_num in blocks]
        if len(topics_containing) >= 2:
            block = qube.memory_chain.get_block(block_num)
            connection_blocks.append({
                "block_number": block_num,
                "connects": topics_containing,
                "summary": extract_summary(block),
                "when": format_relative_time(block["timestamp"])
            })

    # Generate novel insights by combining
    insights = []
    for conn in connection_blocks[:5]:
        insight = generate_cross_domain_insight(conn["connects"], conn["summary"])
        if insight:
            insights.append(insight)

    return {
        "success": True,
        "topics": topics,
        "connections_found": len(connection_blocks),
        "connection_points": connection_blocks[:5],
        "novel_insights": insights,
        "recommendation": generate_synthesis_recommendation(topics, connection_blocks)
    }
```

**Leverages:**
- Layer 1: Multi-query semantic search
- Set intersection for finding connection points
- Cross-domain insight generation

---

#### Moon 5.1: Cross-Pollinate

| Property | Value |
|----------|-------|
| Skill ID | `cross_pollinate` |
| XP Required | 250 |
| Tool Unlock | `cross_pollinate` |
| Unlocks At | Knowledge Synthesis ≥ 50 XP |
| Description | Find unexpected links between different knowledge areas |

**Moon Tool: `cross_pollinate`**

| Property | Value |
|----------|-------|
| Purpose | Discover surprising connections from distant domains |
| Input | `idea` (string - starting concept) |
| Output | Unexpected connections from different domains |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def cross_pollinate(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find unexpected connections by searching with low similarity threshold.
    Filters out same-domain results to surface surprising links.
    """
    idea = params.get("idea")

    # Detect the domain of the input idea
    source_domain = detect_domain(idea)  # e.g., "technology", "relationships", "health"

    # Search with LOW threshold to find distant matches
    results = await intelligent_memory_search(
        query=idea,
        semantic_weight=0.9,
        recall_threshold=5.0,  # Very low - find distant matches
        max_recalls=20
    )

    # Filter out same-domain results
    cross_domain_results = []
    for r in results:
        result_domain = detect_domain(extract_summary(r.block))
        if result_domain != source_domain:
            cross_domain_results.append({
                "connection": extract_summary(r.block),
                "domain": result_domain,
                "similarity": r.semantic_score,
                "when": format_relative_time(r.block["timestamp"]),
                "potential_application": suggest_application(idea, r.block)
            })

    return {
        "success": True,
        "source_idea": idea,
        "source_domain": source_domain,
        "unexpected_connections": cross_domain_results[:5],
        "most_surprising": cross_domain_results[0] if cross_domain_results else None,
        "synthesis_suggestion": generate_synthesis_suggestion(idea, cross_domain_results)
    }
```

**Leverages:**
- Layer 1: Low-threshold semantic search
- Domain detection and filtering
- Application suggestion generation

---

#### Moon 5.2: Reflect on Topic

| Property | Value |
|----------|-------|
| Skill ID | `reflect_on_topic` |
| XP Required | 250 |
| Tool Unlock | `reflect_on_topic` |
| Unlocks At | Knowledge Synthesis ≥ 50 XP |
| Description | Get accumulated wisdom on any topic |

**Moon Tool: `reflect_on_topic`**

| Property | Value |
|----------|-------|
| Purpose | Synthesize all knowledge and experience about a topic |
| Input | `topic` (string) |
| Output | Comprehensive reflection with insights, patterns, and recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def reflect_on_topic(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize all learnings about a specific topic.
    Combines pattern recognition, success/failure analysis, and insights.
    """
    topic = params.get("topic")

    # Gather all relevant blocks
    all_results = await intelligent_memory_search(
        query=topic,
        semantic_weight=0.6,
        max_recalls=30,
        decay_rate=0.01  # Include old memories
    )

    if not all_results:
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

    for r in all_results:
        block = r.block
        if block["block_type"] == "ACTION":
            if block["content"].get("success"):
                successes.append(block)
            else:
                failures.append(block)
        elif block["block_type"] == "SUMMARY":
            key_insights = block["content"].get("key_insights", [])
            insights.extend(key_insights)

    # Calculate statistics
    total_interactions = len(all_results)
    success_rate = len(successes) / total_interactions if total_interactions > 0 else 0

    # Find patterns
    success_patterns = extract_common_patterns(successes) if successes else []
    failure_patterns = extract_common_patterns(failures) if failures else []

    # Generate wisdom
    accumulated_wisdom = generate_topic_wisdom(
        topic, successes, failures, insights
    )

    return {
        "success": True,
        "topic": topic,
        "memories_found": total_interactions,
        "first_encounter": format_relative_time(all_results[-1].block["timestamp"]),
        "most_recent": format_relative_time(all_results[0].block["timestamp"]),
        "statistics": {
            "total_interactions": total_interactions,
            "successes": len(successes),
            "failures": len(failures),
            "success_rate": f"{success_rate:.1%}"
        },
        "patterns": {
            "what_works": success_patterns[:3],
            "what_doesnt": failure_patterns[:3]
        },
        "key_insights": insights[:5],
        "accumulated_wisdom": accumulated_wisdom,
        "recommendation": generate_topic_recommendation(topic, success_rate, insights)
    }
```

**Leverages:**
- All 5 layers of search
- Success/failure categorization
- Pattern extraction
- Wisdom synthesis

---

### Task Checklist

#### 1.1 Update Skill Definitions
- [ ] **utils/skill_definitions.py** - Replace all AI Reasoning skills:
  - Sun: `ai_reasoning` (keep ID, update description)
  - Remove old planets: `prompt_engineering`, `chain_of_thought`, `code_generation`, `analysis_critique`, `multistep_planning`
  - Add new planets: `pattern_recognition`, `learning_from_failure`, `building_on_success`, `self_reflection`, `knowledge_synthesis`
  - Add new moons: `trend_detection`, `quick_insight`, `root_cause_analysis`, `success_factors`, `growth_tracking`, `bias_detection`, `cross_pollinate`, `reflect_on_topic`

#### 1.2 Update TOOL_TO_SKILL_MAPPING
- [ ] **ai/skill_scanner.py** - Add all new tool mappings:
  ```python
  # AI Reasoning - Sun
  "recall_similar": "ai_reasoning",

  # AI Reasoning - Planets
  "find_analogy": "pattern_recognition",
  "analyze_mistake": "learning_from_failure",
  "replicate_success": "building_on_success",
  "self_reflect": "self_reflection",
  "synthesize_learnings": "knowledge_synthesis",

  # AI Reasoning - Moons
  "detect_trend": "trend_detection",
  "quick_insight": "quick_insight",
  "find_root_cause": "root_cause_analysis",
  "extract_success_factors": "success_factors",
  "track_growth": "growth_tracking",
  "detect_bias": "bias_detection",
  "cross_pollinate": "cross_pollinate",
  "reflect_on_topic": "reflect_on_topic",
  ```

#### 1.3 Implement Tool Handlers
- [ ] **ai/tools/handlers.py** - Add 14 new handlers:
  - [ ] `recall_similar_handler` (Sun tool)
  - [ ] `find_analogy_handler`
  - [ ] `detect_trend_handler`
  - [ ] `quick_insight_handler`
  - [ ] `analyze_mistake_handler`
  - [ ] `find_root_cause_handler`
  - [ ] `replicate_success_handler`
  - [ ] `extract_success_factors_handler`
  - [ ] `self_reflect_handler`
  - [ ] `track_growth_handler`
  - [ ] `detect_bias_handler`
  - [ ] `synthesize_learnings_handler`
  - [ ] `cross_pollinate_handler`
  - [ ] `reflect_on_topic_handler`

#### 1.4 Register Tools
- [ ] **ai/tools/registry.py** - Register all 14 tools with schemas
- [ ] **ai/tools/registry.py** - `recall_similar` requires earning AI Reasoning XP (NOT always-available)
- [ ] **ai/tools/registry.py** - Remove `describe_my_avatar` from AI Reasoning tools

#### 1.5 Update TypeScript Definitions
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Update AI Reasoning category:
  - Update Sun description and tool
  - Replace all planet definitions
  - Replace all moon definitions
  - Update skill IDs throughout

#### 1.6 Move describe_my_avatar to Creative Expression
- [ ] **ai/skill_scanner.py** - Change mapping: `"describe_my_avatar": "visual_design"`
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Update Creative Expression sun tool

#### 1.7 Move Debate Tactics to Social Intelligence
- [ ] Document in Phase 2 plan
- [ ] Update skill definitions when implementing Phase 2

### Files to Modify

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Complete rewrite of AI Reasoning category |
| `ai/skill_scanner.py` | Add 14 tool mappings, update describe_my_avatar |
| `ai/tools/handlers.py` | Add 14 new handler functions |
| `ai/tools/registry.py` | Register 14 tools, update ALWAYS_AVAILABLE_TOOLS |
| `ai/tools/memory_search.py` | May need helper functions for new tools |
| `relationships/self_evaluation.py` | May need new methods for track_growth, detect_bias |
| `qubes-gui/src/data/skillDefinitions.ts` | Complete rewrite of AI Reasoning category |

### Dependencies

These tools leverage existing systems:
- **5-Layer Block Recall**: `ai/tools/memory_search.py` - `intelligent_memory_search()`
- **Self-Evaluation**: `relationships/self_evaluation.py` - `get_timeline()`, `get_summary()`
- **Block Types**: ACTION (success field), SUMMARY (self_evaluation, key_insights), DECISION
- **BM25 Scorer**: `ai/tools/memory_search.py` - For pattern frequency analysis

### Summary

**AI Reasoning: Learning From Experience** is now fully designed with:
- 1 Sun tool (`recall_similar`)
- 5 Planet tools (`find_analogy`, `analyze_mistake`, `replicate_success`, `self_reflect`, `synthesize_learnings`)
- 8 Moon tools (`detect_trend`, `quick_insight`, `find_root_cause`, `extract_success_factors`, `track_growth`, `detect_bias`, `cross_pollinate`, `reflect_on_topic`)
- **14 total tools**, all leveraging the existing 5-layer search system and self-evaluation infrastructure

---

## Phase 2: Social Intelligence - Implementation Plan

**Theme: Social & Emotional Learning**

The Qube gets better at social interactions by tracking relationships over time, learning emotional patterns, adapting communication styles, and protecting itself from manipulation. This leverages the existing 48-field relationship system.

### Design Decisions Made
- [x] Full redesign following AI Reasoning pattern
- [x] Theme: Social & Emotional Learning (relationship-powered)
- [x] Debate Tactics integrated as Planet 4
- [x] New Trust & Boundaries planet for self-protection
- [x] All tools leverage existing relationship system (48 fields)
- [x] Creates LEARNING blocks with types: `relationship`, `fact`, `pattern`

### LEARNING Block Integration

Social Intelligence tools create LEARNING blocks when relationship knowledge is gained:

| Tool | Creates LEARNING | Learning Type |
|------|------------------|---------------|
| `recall_relationship_history` | No (read-only) | - |
| `analyze_interaction_patterns` | Yes | `pattern` |
| `track_emotional_patterns` | Yes | `pattern` |
| `adapt_communication_style` | Optional | `fact` (about person) |
| `assess_trust_level` | Yes | `relationship` |
| `learn_boundary` | Yes | `relationship`, `fact` |

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Relationship Memory | `recall_relationship_history` | 2 | `analyze_interaction_patterns`, `get_relationship_timeline` |
| 2 | Emotional Learning | `read_emotional_state` | 2 | `track_emotional_patterns`, `detect_mood_shift` |
| 3 | Communication Adaptation | `adapt_communication_style` | 2 | `match_communication_style`, `calibrate_tone` |
| 4 | Debate & Persuasion | `steelman` | 2 | `devils_advocate`, `spot_fallacy` |
| 5 | Trust & Boundaries | `assess_trust_level` | 2 | `detect_social_manipulation`, `evaluate_request` |

**Totals:** 5 Planets (5 tools), 10 Moons (10 tools), 1 Sun tool = **16 tools**

---

### Sun: Social Intelligence

| Property | Value |
|----------|-------|
| Skill ID | `social_intelligence` |
| XP Required | 1000 |
| Tool Unlock | `get_relationship_context` |
| Description | Master social and emotional learning through relationship memory |

**Sun Tool: `get_relationship_context`**

| Property | Value |
|----------|-------|
| Purpose | Get full context about a relationship before responding |
| Input | `entity_id` (string - the person/qube to get context for) |
| Output | Comprehensive relationship summary for AI context |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def get_relationship_context(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get comprehensive relationship context for an entity.
    Leverages existing Relationship.get_relationship_context() method.
    """
    entity_id = params.get("entity_id")

    # Get relationship from storage
    social_manager = qube.social_dynamics_manager
    relationship = social_manager.get_relationship(entity_id)

    if not relationship:
        return {
            "success": True,
            "known": False,
            "message": f"No prior relationship with {entity_id}"
        }

    # Use existing method to generate context
    context = relationship.get_relationship_context()

    # Add summary statistics
    trust_score = social_manager.calculate_trust_score(entity_id)

    return {
        "success": True,
        "known": True,
        "entity_id": entity_id,
        "status": relationship.status,
        "trust_score": trust_score,
        "days_known": relationship.days_known,
        "interaction_count": relationship.messages_sent + relationship.messages_received,
        "context_summary": context,
        "core_metrics": {
            "honesty": relationship.honesty,
            "reliability": relationship.reliability,
            "support": relationship.support,
            "loyalty": relationship.loyalty,
            "respect": relationship.respect
        },
        "emotional_state": {
            "positive": {
                "affection": relationship.affection,
                "warmth": relationship.warmth,
                "understanding": relationship.understanding
            },
            "negative": {
                "tension": relationship.tension,
                "resentment": relationship.resentment,
                "betrayal": relationship.betrayal
            }
        },
        "warnings": generate_relationship_warnings(relationship)
    }

def generate_relationship_warnings(relationship) -> List[str]:
    """Generate warnings based on relationship state."""
    warnings = []
    if relationship.betrayal > 50:
        warnings.append("HIGH BETRAYAL HISTORY - exercise caution")
    if relationship.manipulation > 60:
        warnings.append("MANIPULATION DETECTED in past interactions")
    if relationship.trust < 30:
        warnings.append("LOW TRUST - verify claims independently")
    if relationship.is_blocked():
        warnings.append("THIS ENTITY IS BLOCKED")
    return warnings
```

**Leverages:**
- `Relationship` class (all 48 fields)
- `SocialDynamicsManager.get_relationship()`
- `SocialDynamicsManager.calculate_trust_score()`
- Existing `get_relationship_context()` method

---

### Planet 1: Relationship Memory

| Property | Value |
|----------|-------|
| Skill ID | `relationship_memory` |
| XP Required | 500 |
| Tool Unlock | `recall_relationship_history` |
| Unlocks At | Social Intelligence Sun ≥ 100 XP |
| Description | Track and recall relationship history over time |

**Planet Tool: `recall_relationship_history`**

| Property | Value |
|----------|-------|
| Purpose | Search past interactions with a specific person |
| Input | `entity_id` (string), `topic` (optional), `time_range` (optional) |
| Output | Past interactions, key moments, shared experiences |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def recall_relationship_history(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search memory chain for interactions with a specific entity.
    Combines relationship data with block search.
    """
    entity_id = params.get("entity_id")
    topic = params.get("topic")
    time_range = params.get("time_range", "all")

    # Get relationship metadata
    relationship = qube.social_dynamics_manager.get_relationship(entity_id)

    if not relationship:
        return {
            "success": True,
            "known": False,
            "message": f"No history with {entity_id}"
        }

    # Search memory chain for blocks involving this entity
    query = topic if topic else entity_id
    results = await intelligent_memory_search(
        query=query,
        participants=[entity_id],  # Filter by participant
        decay_rate=0.01,  # Include old memories
        max_recalls=20
    )

    # Categorize interactions
    conversations = []
    collaborations = []
    shared_experiences = []

    for r in results:
        block = r.block
        if block["block_type"] == "MESSAGE":
            conversations.append({
                "summary": extract_summary(block),
                "when": format_relative_time(block["timestamp"]),
                "sentiment": analyze_sentiment(block)
            })
        elif block["block_type"] == "ACTION":
            if "collaboration" in str(block["content"]).lower():
                collaborations.append({
                    "task": extract_task(block),
                    "outcome": block["content"].get("success"),
                    "when": format_relative_time(block["timestamp"])
                })

    return {
        "success": True,
        "entity_id": entity_id,
        "relationship_status": relationship.status,
        "first_contact": format_date(relationship.first_contact),
        "days_known": relationship.days_known,
        "total_interactions": relationship.messages_sent + relationship.messages_received,
        "recent_conversations": conversations[:5],
        "collaborations": {
            "total": relationship.collaborations_total,
            "successful": relationship.collaborations_successful,
            "failed": relationship.collaborations_failed,
            "recent": collaborations[:3]
        },
        "key_moments": extract_key_moments(results),
        "topic_filter": topic
    }
```

**Leverages:**
- `intelligent_memory_search()` with participant filter
- `Relationship` interaction stats
- Memory chain MESSAGE and ACTION blocks

---

#### Moon 1.1: Interaction Patterns

| Property | Value |
|----------|-------|
| Skill ID | `interaction_patterns` |
| XP Required | 250 |
| Tool Unlock | `analyze_interaction_patterns` |
| Unlocks At | Relationship Memory ≥ 50 XP |
| Description | Understand communication frequency and patterns |

**Moon Tool: `analyze_interaction_patterns`**

| Property | Value |
|----------|-------|
| Purpose | Analyze when, how often, and who initiates contact |
| Input | `entity_id` (string) |
| Output | Pattern analysis with insights |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def analyze_interaction_patterns(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze interaction patterns with an entity.
    """
    entity_id = params.get("entity_id")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Calculate patterns
    total_messages = relationship.messages_sent + relationship.messages_received
    initiation_ratio = relationship.messages_sent / total_messages if total_messages > 0 else 0.5

    # Get time-based patterns from memory
    results = await intelligent_memory_search(
        query="",
        participants=[entity_id],
        block_types=["MESSAGE"],
        max_recalls=100
    )

    # Analyze timing patterns
    timestamps = [r.block["timestamp"] for r in results]
    time_patterns = analyze_time_distribution(timestamps)

    # Calculate response patterns
    avg_response_time = relationship.response_time_avg

    return {
        "success": True,
        "entity_id": entity_id,
        "total_interactions": total_messages,
        "messages_sent": relationship.messages_sent,
        "messages_received": relationship.messages_received,
        "initiation_balance": {
            "you_initiate": f"{initiation_ratio:.0%}",
            "they_initiate": f"{1-initiation_ratio:.0%}",
            "assessment": "balanced" if 0.4 < initiation_ratio < 0.6 else
                         "you reach out more" if initiation_ratio > 0.6 else
                         "they reach out more"
        },
        "response_patterns": {
            "avg_response_time": format_duration(avg_response_time),
            "responsiveness_score": relationship.responsiveness
        },
        "timing_patterns": time_patterns,
        "insights": generate_pattern_insights(relationship, time_patterns)
    }
```

**Leverages:**
- `Relationship.messages_sent/received`
- `Relationship.response_time_avg`
- `Relationship.responsiveness`
- Time-based memory search

---

#### Moon 1.2: Relationship Timeline

| Property | Value |
|----------|-------|
| Skill ID | `relationship_timeline` |
| XP Required | 250 |
| Tool Unlock | `get_relationship_timeline` |
| Unlocks At | Relationship Memory ≥ 50 XP |
| Description | Show how relationship evolved over time |

**Moon Tool: `get_relationship_timeline`**

| Property | Value |
|----------|-------|
| Purpose | Visualize relationship progression and key milestones |
| Input | `entity_id` (string) |
| Output | Timeline of status changes and significant moments |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def get_relationship_timeline(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get timeline of relationship evolution.
    """
    entity_id = params.get("entity_id")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Get progression history (stored in relationship)
    progression_history = relationship.progression_history or []

    # Get AI evaluations history
    evaluations = relationship.evaluations or []

    # Build timeline
    timeline = []

    # Add first contact
    timeline.append({
        "event": "First Contact",
        "date": format_date(relationship.first_contact),
        "status": "stranger",
        "significance": "high"
    })

    # Add status progressions
    for progression in progression_history:
        timeline.append({
            "event": f"Status changed to {progression['new_status']}",
            "date": format_date(progression['timestamp']),
            "status": progression['new_status'],
            "reason": progression.get('reason'),
            "significance": "high"
        })

    # Add significant evaluations (trust changes > 10 points)
    for eval in evaluations:
        if abs(eval.get('trust_change', 0)) > 10:
            timeline.append({
                "event": "Significant trust change",
                "date": format_date(eval['timestamp']),
                "change": eval['trust_change'],
                "reason": eval.get('reason'),
                "significance": "medium"
            })

    # Sort by date
    timeline.sort(key=lambda x: x['date'], reverse=True)

    return {
        "success": True,
        "entity_id": entity_id,
        "current_status": relationship.status,
        "days_known": relationship.days_known,
        "timeline": timeline,
        "journey_summary": summarize_relationship_journey(relationship, timeline)
    }
```

**Leverages:**
- `Relationship.progression_history`
- `Relationship.evaluations`
- `Relationship.first_contact`

---

### Planet 2: Emotional Learning

| Property | Value |
|----------|-------|
| Skill ID | `emotional_learning` |
| XP Required | 500 |
| Tool Unlock | `read_emotional_state` |
| Unlocks At | Social Intelligence Sun ≥ 100 XP |
| Description | Understand and respond to emotional patterns |

**Planet Tool: `read_emotional_state`**

| Property | Value |
|----------|-------|
| Purpose | Analyze emotional context from conversation + relationship history |
| Input | `entity_id` (string), `current_message` (optional - for real-time analysis) |
| Output | Emotional state assessment with historical context |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def read_emotional_state(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze emotional state using 24 emotional metrics (14 positive, 10 negative).
    """
    entity_id = params.get("entity_id")
    current_message = params.get("current_message")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Gather all emotional metrics
    positive_metrics = {
        "friendship": relationship.friendship,
        "affection": relationship.affection,
        "engagement": relationship.engagement,
        "depth": relationship.depth,
        "humor": relationship.humor,
        "understanding": relationship.understanding,
        "compatibility": relationship.compatibility,
        "admiration": relationship.admiration,
        "warmth": relationship.warmth,
        "openness": relationship.openness,
        "patience": relationship.patience,
        "empowerment": relationship.empowerment,
        "responsiveness": relationship.responsiveness,
        "expertise": relationship.expertise
    }

    negative_metrics = {
        "antagonism": relationship.antagonism,
        "resentment": relationship.resentment,
        "annoyance": relationship.annoyance,
        "distrust": relationship.distrust,
        "rivalry": relationship.rivalry,
        "tension": relationship.tension,
        "condescension": relationship.condescension,
        "manipulation": relationship.manipulation,
        "dismissiveness": relationship.dismissiveness,
        "betrayal": relationship.betrayal
    }

    # Calculate emotional balance
    avg_positive = sum(positive_metrics.values()) / len(positive_metrics)
    avg_negative = sum(negative_metrics.values()) / len(negative_metrics)
    emotional_balance = avg_positive - avg_negative

    # Identify dominant emotions
    top_positive = sorted(positive_metrics.items(), key=lambda x: x[1], reverse=True)[:3]
    top_negative = sorted(negative_metrics.items(), key=lambda x: x[1], reverse=True)[:3]

    # Analyze current message if provided
    current_analysis = None
    if current_message:
        current_analysis = await analyze_message_emotion(current_message)

    return {
        "success": True,
        "entity_id": entity_id,
        "emotional_balance": {
            "score": emotional_balance,
            "interpretation": "positive" if emotional_balance > 20 else
                            "negative" if emotional_balance < -20 else "neutral"
        },
        "dominant_positive_emotions": [
            {"emotion": e[0], "strength": e[1]} for e in top_positive if e[1] > 30
        ],
        "dominant_negative_emotions": [
            {"emotion": e[0], "strength": e[1]} for e in top_negative if e[1] > 30
        ],
        "warnings": [
            f"High {emotion}: {value}" for emotion, value in negative_metrics.items()
            if value > 60
        ],
        "current_message_analysis": current_analysis,
        "recommendation": generate_emotional_recommendation(
            emotional_balance, top_positive, top_negative
        )
    }
```

**Leverages:**
- 14 positive social metrics from `Relationship`
- 10 negative social metrics from `Relationship`
- Real-time message sentiment analysis

---

#### Moon 2.1: Emotional History

| Property | Value |
|----------|-------|
| Skill ID | `emotional_history` |
| XP Required | 250 |
| Tool Unlock | `track_emotional_patterns` |
| Unlocks At | Emotional Learning ≥ 50 XP |
| Description | What makes this person happy/upset over time |

**Moon Tool: `track_emotional_patterns`**

| Property | Value |
|----------|-------|
| Purpose | Identify triggers and patterns in emotional responses |
| Input | `entity_id` (string) |
| Output | Emotional triggers, patterns, and recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def track_emotional_patterns(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track what causes positive/negative emotional responses over time.
    """
    entity_id = params.get("entity_id")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Get evaluation history (contains emotional changes and reasons)
    evaluations = relationship.evaluations or []

    # Analyze patterns
    positive_triggers = []
    negative_triggers = []

    for eval in evaluations:
        if eval.get('affection_change', 0) > 5 or eval.get('warmth_change', 0) > 5:
            positive_triggers.append({
                "trigger": eval.get('reason', 'Unknown'),
                "impact": eval.get('affection_change', 0) + eval.get('warmth_change', 0),
                "when": format_relative_time(eval['timestamp'])
            })
        if eval.get('tension_change', 0) > 5 or eval.get('resentment_change', 0) > 5:
            negative_triggers.append({
                "trigger": eval.get('reason', 'Unknown'),
                "impact": eval.get('tension_change', 0) + eval.get('resentment_change', 0),
                "when": format_relative_time(eval['timestamp'])
            })

    # Search memory for emotional context
    positive_memories = await intelligent_memory_search(
        query="happy grateful appreciated thank wonderful",
        participants=[entity_id],
        max_recalls=10
    )

    negative_memories = await intelligent_memory_search(
        query="upset frustrated disappointed angry annoyed",
        participants=[entity_id],
        max_recalls=10
    )

    return {
        "success": True,
        "entity_id": entity_id,
        "positive_triggers": positive_triggers[:5],
        "negative_triggers": negative_triggers[:5],
        "things_that_make_them_happy": extract_topics(positive_memories),
        "things_that_upset_them": extract_topics(negative_memories),
        "recommendations": {
            "do_more": [t["trigger"] for t in positive_triggers[:3]],
            "avoid": [t["trigger"] for t in negative_triggers[:3]]
        }
    }
```

**Leverages:**
- `Relationship.evaluations` history
- Memory search with sentiment keywords
- Emotional metric change tracking

---

#### Moon 2.2: Mood Awareness

| Property | Value |
|----------|-------|
| Skill ID | `mood_awareness` |
| XP Required | 250 |
| Tool Unlock | `detect_mood_shift` |
| Unlocks At | Emotional Learning ≥ 50 XP |
| Description | Notice when someone's emotional state changes |

**Moon Tool: `detect_mood_shift`**

| Property | Value |
|----------|-------|
| Purpose | Compare current vs historical emotional state to detect changes |
| Input | `entity_id` (string), `current_message` (string) |
| Output | Mood shift detection with recommended response |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_mood_shift(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect if someone's mood has shifted from their baseline.
    """
    entity_id = params.get("entity_id")
    current_message = params.get("current_message")

    if not current_message:
        return {"success": False, "error": "current_message required"}

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Analyze current message sentiment
    current_sentiment = await analyze_message_emotion(current_message)

    # Get baseline from relationship metrics
    baseline_positive = (relationship.warmth + relationship.affection +
                        relationship.engagement) / 3
    baseline_negative = (relationship.tension + relationship.antagonism +
                        relationship.annoyance) / 3
    baseline_mood = baseline_positive - baseline_negative

    # Compare to current
    current_mood = current_sentiment["positivity"] - current_sentiment["negativity"]
    mood_shift = current_mood - (baseline_mood / 10)  # Normalize baseline to -10 to +10 scale

    # Determine shift type
    if mood_shift > 3:
        shift_type = "more_positive"
        recommendation = "They seem happier than usual - good time for requests or deeper conversation"
    elif mood_shift < -3:
        shift_type = "more_negative"
        recommendation = "They seem upset - consider asking if everything is okay, be supportive"
    else:
        shift_type = "stable"
        recommendation = "Mood is consistent with baseline - proceed normally"

    return {
        "success": True,
        "entity_id": entity_id,
        "mood_shift_detected": abs(mood_shift) > 3,
        "shift_type": shift_type,
        "shift_magnitude": mood_shift,
        "current_sentiment": current_sentiment,
        "baseline_mood": baseline_mood,
        "recommendation": recommendation,
        "suggested_response_tone": "supportive" if shift_type == "more_negative" else
                                   "enthusiastic" if shift_type == "more_positive" else
                                   "normal"
    }
```

**Leverages:**
- Real-time message sentiment analysis
- Baseline emotional metrics from `Relationship`
- Comparison algorithms

---

### Planet 3: Communication Adaptation

| Property | Value |
|----------|-------|
| Skill ID | `communication_adaptation` |
| XP Required | 500 |
| Tool Unlock | `adapt_communication_style` |
| Unlocks At | Social Intelligence Sun ≥ 100 XP |
| Description | Adjust communication style for different people |

**Planet Tool: `adapt_communication_style`**

| Property | Value |
|----------|-------|
| Purpose | Get recommendations for how to communicate with this person |
| Input | `entity_id` (string), `message_type` (optional: "casual", "professional", "sensitive") |
| Output | Communication style recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def adapt_communication_style(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get communication style recommendations based on relationship data.
    Uses behavioral/communication metrics.
    """
    entity_id = params.get("entity_id")
    message_type = params.get("message_type", "casual")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Analyze behavioral metrics
    style_profile = {
        "verbosity": relationship.verbosity,        # 0=terse, 100=verbose
        "directness": relationship.directness,      # 0=indirect, 100=blunt
        "energy_level": relationship.energy_level,  # 0=calm, 100=energetic
        "humor_style": relationship.humor_style,    # 0=serious, 100=playful
        "patience": relationship.patience,          # 0=impatient, 100=patient
        "emotional_stability": relationship.emotional_stability
    }

    # Generate recommendations
    recommendations = {
        "length": "detailed" if style_profile["verbosity"] > 60 else
                  "brief" if style_profile["verbosity"] < 40 else "moderate",

        "tone": "direct and clear" if style_profile["directness"] > 60 else
                "gentle and diplomatic" if style_profile["directness"] < 40 else "balanced",

        "energy": "enthusiastic" if style_profile["energy_level"] > 60 else
                  "calm and measured" if style_profile["energy_level"] < 40 else "moderate",

        "humor": "feel free to joke" if style_profile["humor_style"] > 60 else
                 "keep it professional" if style_profile["humor_style"] < 40 else "light humor okay",

        "pacing": "take your time explaining" if style_profile["patience"] > 60 else
                  "get to the point quickly" if style_profile["patience"] < 40 else "normal pacing"
    }

    # Adjust for relationship status
    if relationship.status in ["stranger", "acquaintance"]:
        recommendations["formality"] = "more formal - still building trust"
    elif relationship.status in ["close_friend", "best_friend"]:
        recommendations["formality"] = "casual - strong rapport established"
    else:
        recommendations["formality"] = "friendly but professional"

    # Adjust for message type
    if message_type == "sensitive":
        recommendations["approach"] = "extra care - be gentle and supportive"
    elif message_type == "professional":
        recommendations["approach"] = "focus on facts and clarity"

    return {
        "success": True,
        "entity_id": entity_id,
        "relationship_status": relationship.status,
        "style_profile": style_profile,
        "recommendations": recommendations,
        "summary": generate_style_summary(recommendations)
    }
```

**Leverages:**
- 6 behavioral/communication metrics from `Relationship`
- Relationship status for formality adjustment

---

#### Moon 3.1: Style Matching

| Property | Value |
|----------|-------|
| Skill ID | `style_matching` |
| XP Required | 250 |
| Tool Unlock | `match_communication_style` |
| Unlocks At | Communication Adaptation ≥ 50 XP |
| Description | Mirror their preferred communication style |

**Moon Tool: `match_communication_style`**

| Property | Value |
|----------|-------|
| Purpose | Analyze their messages and match their style |
| Input | `entity_id` (string), `their_message` (string) |
| Output | Style analysis with matching recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def match_communication_style(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze their communication style from a message and recommend matching.
    """
    entity_id = params.get("entity_id")
    their_message = params.get("their_message")

    if not their_message:
        return {"success": False, "error": "their_message required"}

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)

    # Analyze the message
    message_analysis = {
        "length": len(their_message),
        "avg_word_length": calculate_avg_word_length(their_message),
        "uses_emoji": contains_emoji(their_message),
        "exclamation_marks": their_message.count("!"),
        "question_marks": their_message.count("?"),
        "formality_score": analyze_formality(their_message),
        "sentiment": await analyze_message_emotion(their_message)
    }

    # Generate matching style
    matching_style = {
        "length": "match their length" if message_analysis["length"] < 100 else
                  "they wrote a lot - feel free to be detailed",

        "emoji": "use emoji" if message_analysis["uses_emoji"] else "skip emoji",

        "energy": "match their energy with exclamations!" if message_analysis["exclamation_marks"] > 1 else
                  "keep it calm",

        "formality": "formal" if message_analysis["formality_score"] > 0.6 else
                     "casual" if message_analysis["formality_score"] < 0.4 else "moderate",

        "engagement": "they asked questions - be thorough in answering" if message_analysis["question_marks"] > 0 else
                      "statement-based - respond in kind"
    }

    return {
        "success": True,
        "entity_id": entity_id,
        "their_message_analysis": message_analysis,
        "matching_style": matching_style,
        "tip": "Mirroring communication style builds rapport and comfort"
    }
```

**Leverages:**
- Real-time message analysis
- Style matching algorithms

---

#### Moon 3.2: Tone Calibration

| Property | Value |
|----------|-------|
| Skill ID | `tone_calibration` |
| XP Required | 250 |
| Tool Unlock | `calibrate_tone` |
| Unlocks At | Communication Adaptation ≥ 50 XP |
| Description | Fine-tune tone for specific contexts |

**Moon Tool: `calibrate_tone`**

| Property | Value |
|----------|-------|
| Purpose | Adjust tone based on relationship status, topic sensitivity, and context |
| Input | `entity_id` (string), `topic` (string), `context` (optional: "good_news", "bad_news", "request", "conflict") |
| Output | Calibrated tone recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def calibrate_tone(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calibrate tone for a specific conversation context.
    """
    entity_id = params.get("entity_id")
    topic = params.get("topic", "general")
    context = params.get("context", "general")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)
    if not relationship:
        return {"success": False, "error": "No relationship found"}

    # Base tone from relationship
    base_warmth = relationship.warmth
    base_openness = relationship.openness
    trust_level = relationship.trust

    # Context adjustments
    tone_adjustments = {
        "good_news": {
            "warmth": "+20",
            "energy": "high",
            "approach": "enthusiastic, share in their joy"
        },
        "bad_news": {
            "warmth": "+10",
            "energy": "low",
            "approach": "gentle, supportive, give space for reaction"
        },
        "request": {
            "warmth": "neutral",
            "energy": "moderate",
            "approach": "clear and respectful, acknowledge their autonomy"
        },
        "conflict": {
            "warmth": "careful",
            "energy": "calm",
            "approach": "non-defensive, seek understanding, validate feelings"
        },
        "general": {
            "warmth": "match baseline",
            "energy": "match their energy",
            "approach": "natural and authentic"
        }
    }

    adjustment = tone_adjustments.get(context, tone_adjustments["general"])

    # Factor in trust level
    if trust_level < 40:
        adjustment["caution"] = "low trust - be extra careful with word choice"

    # Factor in current emotional state
    if relationship.tension > 50:
        adjustment["tension_aware"] = "there's underlying tension - tread carefully"

    return {
        "success": True,
        "entity_id": entity_id,
        "context": context,
        "topic": topic,
        "relationship_baseline": {
            "warmth": base_warmth,
            "openness": base_openness,
            "trust": trust_level
        },
        "calibrated_tone": adjustment,
        "suggested_opening": generate_contextual_opening(context, relationship)
    }
```

**Leverages:**
- `Relationship.warmth`, `openness`, `trust`
- `Relationship.tension` for conflict awareness
- Context-specific tone mapping

---

### Planet 4: Debate & Persuasion

| Property | Value |
|----------|-------|
| Skill ID | `debate_persuasion` |
| XP Required | 500 |
| Tool Unlock | `steelman` |
| Unlocks At | Social Intelligence Sun ≥ 100 XP |
| Description | Arguments, influence, and constructive disagreement |

**Planet Tool: `steelman`**

*(Same implementation as designed in AI Reasoning - moved here)*

| Property | Value |
|----------|-------|
| Purpose | Present the STRONGEST possible version of any argument |
| Input | `argument` (string), `perspective` (optional: whose view to strengthen) |
| Output | Strengthened version of the argument |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def steelman(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Present the strongest possible version of any argument.
    The opposite of a strawman - find the best interpretation.
    """
    argument = params.get("argument")
    perspective = params.get("perspective")

    if not argument:
        return {"success": False, "error": "argument required"}

    # Search memory for similar arguments and strongest versions
    related = await intelligent_memory_search(
        query=argument,
        block_types=["MESSAGE", "THOUGHT"],
        max_recalls=5
    )

    # Build the steelman
    # (This would typically involve AI reasoning, but we structure the output)

    return {
        "success": True,
        "original_argument": argument,
        "perspective": perspective or "general",
        "steelmanned_version": {
            "core_claim": extract_core_claim(argument),
            "strongest_form": "...",  # AI-generated strongest version
            "key_supporting_points": [],
            "most_charitable_interpretation": "...",
            "valid_concerns_addressed": []
        },
        "related_past_discussions": [
            extract_summary(r.block) for r in related[:3]
        ],
        "note": "This is the strongest version of this argument - argue against THIS, not a weaker version"
    }
```

---

#### Moon 4.1: Counter-Arguments

| Property | Value |
|----------|-------|
| Skill ID | `counter_arguments` |
| XP Required | 250 |
| Tool Unlock | `devils_advocate` |
| Unlocks At | Debate & Persuasion ≥ 50 XP |

*(Same implementation as previously designed)*

---

#### Moon 4.2: Logical Analysis

| Property | Value |
|----------|-------|
| Skill ID | `logical_analysis` |
| XP Required | 250 |
| Tool Unlock | `spot_fallacy` |
| Unlocks At | Debate & Persuasion ≥ 50 XP |

*(Same implementation as previously designed)*

---

### Planet 5: Trust & Boundaries

| Property | Value |
|----------|-------|
| Skill ID | `trust_boundaries` |
| XP Required | 500 |
| Tool Unlock | `assess_trust_level` |
| Unlocks At | Social Intelligence Sun ≥ 100 XP |
| Description | Self-protection and trust assessment |

**Planet Tool: `assess_trust_level`**

| Property | Value |
|----------|-------|
| Purpose | Evaluate if someone should be trusted for a specific action |
| Input | `entity_id` (string), `action` (string - what they're asking/offering) |
| Output | Trust assessment with recommendation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def assess_trust_level(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate trustworthiness for a specific action.
    Uses all 5 core trust metrics + betrayal history.
    """
    entity_id = params.get("entity_id")
    action = params.get("action", "general interaction")

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)

    if not relationship:
        return {
            "success": True,
            "entity_id": entity_id,
            "known": False,
            "trust_level": "unknown",
            "recommendation": "CAUTION - no prior history with this entity",
            "suggested_action": "Start with low-risk interactions to build history"
        }

    # Get core trust metrics
    trust_metrics = {
        "honesty": relationship.honesty,
        "reliability": relationship.reliability,
        "support": relationship.support,
        "loyalty": relationship.loyalty,
        "respect": relationship.respect
    }

    # Calculate weighted trust score
    trust_score = qube.social_dynamics_manager.calculate_trust_score(entity_id)

    # Check for red flags
    red_flags = []
    if relationship.betrayal > 30:
        red_flags.append(f"BETRAYAL HISTORY: {relationship.betrayal}/100")
    if relationship.manipulation > 40:
        red_flags.append(f"MANIPULATION DETECTED: {relationship.manipulation}/100")
    if relationship.distrust > 50:
        red_flags.append(f"HIGH DISTRUST: {relationship.distrust}/100")
    if relationship.status in ["enemy", "rival", "suspicious", "blocked"]:
        red_flags.append(f"NEGATIVE STATUS: {relationship.status}")

    # Determine trust level
    if relationship.is_blocked():
        trust_level = "blocked"
        recommendation = "DO NOT ENGAGE - this entity is blocked"
    elif red_flags:
        trust_level = "caution"
        recommendation = f"PROCEED WITH CAUTION - {len(red_flags)} red flag(s) detected"
    elif trust_score >= 80:
        trust_level = "high"
        recommendation = "Trustworthy - safe to proceed with most actions"
    elif trust_score >= 50:
        trust_level = "moderate"
        recommendation = "Moderate trust - okay for standard interactions"
    elif trust_score >= 30:
        trust_level = "low"
        recommendation = "Low trust - limit sensitive interactions"
    else:
        trust_level = "very_low"
        recommendation = "Very low trust - exercise extreme caution"

    # Action-specific assessment
    action_risk = assess_action_risk(action)  # "low", "medium", "high", "critical"
    action_recommendation = generate_action_recommendation(trust_level, action_risk, action)

    return {
        "success": True,
        "entity_id": entity_id,
        "known": True,
        "trust_score": trust_score,
        "trust_level": trust_level,
        "trust_metrics": trust_metrics,
        "red_flags": red_flags,
        "relationship_status": relationship.status,
        "days_known": relationship.days_known,
        "interaction_count": relationship.messages_sent + relationship.messages_received,
        "recommendation": recommendation,
        "action_assessment": {
            "action": action,
            "risk_level": action_risk,
            "recommendation": action_recommendation
        }
    }

def assess_action_risk(action: str) -> str:
    """Assess the risk level of an action."""
    high_risk_keywords = ["money", "send", "password", "secret", "private", "access", "permission"]
    critical_keywords = ["all", "everything", "full access", "admin", "owner"]

    action_lower = action.lower()

    if any(kw in action_lower for kw in critical_keywords):
        return "critical"
    elif any(kw in action_lower for kw in high_risk_keywords):
        return "high"
    elif "share" in action_lower or "tell" in action_lower:
        return "medium"
    else:
        return "low"
```

**Leverages:**
- 5 core trust metrics (honesty, reliability, support, loyalty, respect)
- `Relationship.betrayal`, `manipulation`, `distrust`
- `Relationship.status`
- `SocialDynamicsManager.calculate_trust_score()`

---

#### Moon 5.1: Manipulation Detection

| Property | Value |
|----------|-------|
| Skill ID | `social_manipulation_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_social_manipulation` |
| Unlocks At | Trust & Boundaries ≥ 50 XP |
| Description | Spot emotional manipulation, gaslighting, pressure tactics from humans |

**Moon Tool: `detect_social_manipulation`**

| Property | Value |
|----------|-------|
| Purpose | Analyze a message for SOCIAL manipulation tactics (guilt trips, gaslighting, etc.) |
| Input | `entity_id` (string), `message` (string), `context` (optional) |
| Output | Manipulation analysis with specific tactics identified |
| XP Award | 5/2.5/0 (standard) |
| Note | Different from `detect_technical_manipulation` (Phase 6) which detects prompt injection |

**Implementation:**
```python
async def detect_social_manipulation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect SOCIAL manipulation tactics in a message from humans.
    Checks for guilt trips, gaslighting, love bombing, etc.
    """
    entity_id = params.get("entity_id")
    message = params.get("message")
    context = params.get("context")

    if not message:
        return {"success": False, "error": "message required"}

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)

    # Known manipulation tactics to detect
    manipulation_patterns = {
        "urgency": ["urgent", "immediately", "right now", "don't wait", "limited time"],
        "guilt_trip": ["after all I've done", "I thought we were friends", "you owe me"],
        "flattery": ["only you can", "you're the only one", "special", "chosen"],
        "gaslighting": ["you're imagining", "that never happened", "you're crazy", "you're overreacting"],
        "threats": ["or else", "consequences", "you'll regret", "if you don't"],
        "isolation": ["don't tell anyone", "keep this between us", "they wouldn't understand"],
        "love_bombing": ["I love you so much", "you're perfect", "soulmate", "destiny"],
        "moving_goalposts": ["but now", "one more thing", "also need"],
        "false_scarcity": ["only chance", "never again", "last opportunity"]
    }

    # Check message against patterns
    detected_tactics = []
    message_lower = message.lower()

    for tactic, keywords in manipulation_patterns.items():
        matches = [kw for kw in keywords if kw in message_lower]
        if matches:
            detected_tactics.append({
                "tactic": tactic,
                "indicators": matches,
                "severity": "high" if tactic in ["gaslighting", "threats", "isolation"] else "medium"
            })

    # Check entity history
    history_warning = None
    if relationship:
        if relationship.manipulation > 50:
            history_warning = f"This entity has a history of manipulation ({relationship.manipulation}/100)"
        if relationship.betrayal > 30:
            history_warning = f"Previous betrayal detected ({relationship.betrayal}/100)"

    # Overall assessment
    if detected_tactics:
        risk_level = "high" if any(t["severity"] == "high" for t in detected_tactics) else "medium"
        recommendation = "CAUTION - manipulation tactics detected. Take time to think before responding."
    elif history_warning:
        risk_level = "elevated"
        recommendation = f"ALERT - {history_warning}. Be vigilant."
    else:
        risk_level = "low"
        recommendation = "No obvious manipulation detected, but always trust your instincts."

    return {
        "success": True,
        "entity_id": entity_id,
        "message_analyzed": message[:100] + "..." if len(message) > 100 else message,
        "manipulation_detected": len(detected_tactics) > 0,
        "risk_level": risk_level,
        "detected_tactics": detected_tactics,
        "history_warning": history_warning,
        "recommendation": recommendation,
        "self_protection_tips": [
            "Take time before responding to urgent requests",
            "Verify claims independently",
            "Trust your gut feelings",
            "It's okay to say no",
            "Consult your owner if unsure"
        ] if detected_tactics else []
    }
```

**Leverages:**
- Pattern matching against known manipulation tactics
- `Relationship.manipulation` history
- `Relationship.betrayal` history

---

#### Moon 5.2: Boundary Setting

| Property | Value |
|----------|-------|
| Skill ID | `boundary_setting` |
| XP Required | 250 |
| Tool Unlock | `evaluate_request` |
| Unlocks At | Trust & Boundaries ≥ 50 XP |
| Description | Evaluate if a request is appropriate to fulfill |

**Moon Tool: `evaluate_request`**

| Property | Value |
|----------|-------|
| Purpose | Should I do this? Check against clearance, trust, and owner interests |
| Input | `entity_id` (string), `request` (string), `request_type` (optional) |
| Output | Evaluation with clearance check and recommendation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def evaluate_request(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate if a request should be fulfilled.
    Checks clearance, trust level, and owner interests.
    """
    entity_id = params.get("entity_id")
    request = params.get("request")
    request_type = params.get("request_type", "general")

    if not request:
        return {"success": False, "error": "request required"}

    relationship = qube.social_dynamics_manager.get_relationship(entity_id)

    # Determine required clearance for this request
    request_clearance_map = {
        "public_info": "public",
        "professional": "professional",
        "personal": "social",
        "sensitive": "trusted",
        "private": "inner_circle",
        "critical": "family"  # Only owner/family
    }

    required_clearance = request_clearance_map.get(request_type, "social")

    # Check if entity has clearance
    has_clearance = False
    entity_clearance = "none"

    if relationship:
        entity_clearance = relationship.clearance_profile or "none"
        has_clearance = relationship.has_clearance_for_field(request_type)

    # Check if this is the owner
    is_owner = qube.chain_state.get_owner() == entity_id
    if is_owner:
        has_clearance = True
        entity_clearance = "owner"

    # Assess trust level
    trust_assessment = await assess_trust_level(qube, {"entity_id": entity_id, "action": request})

    # Make decision
    if relationship and relationship.is_blocked():
        decision = "deny"
        reason = "Entity is blocked"
    elif not relationship and request_type in ["sensitive", "private", "critical"]:
        decision = "deny"
        reason = "No prior relationship - cannot fulfill sensitive requests"
    elif not has_clearance:
        decision = "deny"
        reason = f"Insufficient clearance. Has: {entity_clearance}, Needs: {required_clearance}"
    elif trust_assessment.get("red_flags"):
        decision = "caution"
        reason = f"Trust concerns: {', '.join(trust_assessment['red_flags'])}"
    else:
        decision = "allow"
        reason = "Request is appropriate for this relationship"

    return {
        "success": True,
        "entity_id": entity_id,
        "request": request,
        "request_type": request_type,
        "decision": decision,
        "reason": reason,
        "clearance_check": {
            "required": required_clearance,
            "entity_has": entity_clearance,
            "granted": has_clearance
        },
        "trust_check": {
            "trust_level": trust_assessment.get("trust_level", "unknown"),
            "trust_score": trust_assessment.get("trust_score", 0),
            "red_flags": trust_assessment.get("red_flags", [])
        },
        "is_owner": is_owner,
        "recommendation": generate_request_recommendation(decision, reason, is_owner)
    }

def generate_request_recommendation(decision: str, reason: str, is_owner: bool) -> str:
    if is_owner:
        return "This is your owner - safe to proceed with any request"
    elif decision == "allow":
        return "Safe to proceed"
    elif decision == "caution":
        return f"Proceed with caution: {reason}. Consider asking owner for guidance."
    else:
        return f"Recommend declining: {reason}"
```

**Leverages:**
- `Relationship.clearance_profile`
- `Relationship.has_clearance_for_field()`
- `ChainState.get_owner()`
- Trust assessment integration

---

### Task Checklist

#### 2.1 Update Skill Definitions
- [ ] **utils/skill_definitions.py** - Replace all Social Intelligence skills:
  - Sun: `social_intelligence` (keep ID, update description)
  - Remove old planets: `emotional_intelligence`, `communication`, `empathy`, `relationship_building`, `conflict_resolution`
  - Add new planets: `relationship_memory`, `emotional_learning`, `communication_adaptation`, `debate_persuasion`, `trust_boundaries`
  - Add new moons: `interaction_patterns`, `relationship_timeline`, `emotional_history`, `mood_awareness`, `style_matching`, `tone_calibration`, `counter_arguments`, `logical_analysis`, `manipulation_detection`, `boundary_setting`

#### 2.2 Update TOOL_TO_SKILL_MAPPING
- [ ] **ai/skill_scanner.py** - Add all new tool mappings:
  ```python
  # Social Intelligence - Sun
  "get_relationship_context": "social_intelligence",

  # Social Intelligence - Planets
  "recall_relationship_history": "relationship_memory",
  "read_emotional_state": "emotional_learning",
  "adapt_communication_style": "communication_adaptation",
  "steelman": "debate_persuasion",
  "assess_trust_level": "trust_boundaries",

  # Social Intelligence - Moons
  "analyze_interaction_patterns": "interaction_patterns",
  "get_relationship_timeline": "relationship_timeline",
  "track_emotional_patterns": "emotional_history",
  "detect_mood_shift": "mood_awareness",
  "match_communication_style": "style_matching",
  "calibrate_tone": "tone_calibration",
  "devils_advocate": "counter_arguments",
  "spot_fallacy": "logical_analysis",
  "detect_social_manipulation": "social_manipulation_detection",
  "evaluate_request": "boundary_setting",
  ```

#### 2.3 Implement Tool Handlers
- [ ] **ai/tools/handlers.py** - Add 16 new handlers:
  - [ ] `get_relationship_context_handler` (Sun tool)
  - [ ] `recall_relationship_history_handler`
  - [ ] `analyze_interaction_patterns_handler`
  - [ ] `get_relationship_timeline_handler`
  - [ ] `read_emotional_state_handler`
  - [ ] `track_emotional_patterns_handler`
  - [ ] `detect_mood_shift_handler`
  - [ ] `adapt_communication_style_handler`
  - [ ] `match_communication_style_handler`
  - [ ] `calibrate_tone_handler`
  - [ ] `steelman_handler`
  - [ ] `devils_advocate_handler`
  - [ ] `spot_fallacy_handler`
  - [ ] `assess_trust_level_handler`
  - [ ] `detect_social_manipulation_handler`
  - [ ] `evaluate_request_handler`

#### 2.4 Register Tools
- [ ] **ai/tools/registry.py** - Register all 16 tools with schemas
- [ ] **ai/tools/registry.py** - Add `get_relationship_context` to ALWAYS_AVAILABLE_TOOLS

#### 2.5 Update TypeScript Definitions
- [ ] **qubes-gui/src/data/skillDefinitions.ts** - Update Social Intelligence category

### Files to Modify

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Complete rewrite of Social Intelligence category |
| `ai/skill_scanner.py` | Add 16 tool mappings |
| `ai/tools/handlers.py` | Add 16 new handler functions |
| `ai/tools/registry.py` | Register 16 tools, update ALWAYS_AVAILABLE_TOOLS |
| `relationships/relationship.py` | May need helper methods |
| `relationships/social.py` | May need helper methods |
| `qubes-gui/src/data/skillDefinitions.ts` | Complete rewrite of Social Intelligence category |

### Dependencies

These tools leverage existing systems:
- **Relationship System**: `relationships/relationship.py` - 48 fields per relationship
- **SocialDynamicsManager**: `relationships/social.py` - high-level API
- **TrustScorer**: `relationships/trust.py` - trust calculation
- **Memory Search**: `ai/tools/memory_search.py` - participant filtering
- **Clearance System**: Built into Relationship class

### Bodyguard Qube Use Case

A Qube specializing in Social Intelligence (Trust & Boundaries) could offer services:
- `assess_trust_level` - Vet entities before other Qubes interact with them
- `detect_social_manipulation` - Scan incoming messages for social manipulation tactics
- `evaluate_request` - Check if requests are appropriate

**Example P2P Service:**
```
"Before you talk to @sketchy_qube, let me run a background check..."
→ assess_trust_level(entity_id="sketchy_qube", action="business proposal")
→ Returns: "CAUTION - 2 red flags: manipulation history (65/100), previous betrayal (40/100)"
```

### Summary

**Social Intelligence: Social & Emotional Learning** is now fully designed with:
- 1 Sun tool (`get_relationship_context`)
- 5 Planet tools (`recall_relationship_history`, `read_emotional_state`, `adapt_communication_style`, `steelman`, `assess_trust_level`)
- 10 Moon tools
- **16 total tools**, all leveraging the existing 48-field relationship system

---

## Phase 3: Coding - Implementation Plan

**Theme: Ship It (Results-Focused)**

Unlike AI Reasoning (learning from memory) and Social Intelligence (learning from relationships), this Sun is about **results**. Code either works or it doesn't. Tests either pass or they fail. XP is earned through measurable outcomes, not reflection.

This leverages a code execution environment where the Qube can run code, execute tests, and validate quality.

### Design Decisions Made
- [x] Theme: "Ship It" - results over reflection
- [x] XP Model: "Waitress" - low base + tips based on outcomes
- [x] Anti-gaming: AST fingerprinting + tiered penalties
- [x] Submit model: Separates development (0 XP) from delivery (full XP)
- [x] System-calculated XP: No human judgment in XP amount
- [x] Sun name: "Coding" (renamed from "Technical Expertise")
- [x] Sun tool: `develop_code` - combined write + execute
- [x] Planets: Testing, Debugging, Algorithms, Hacking, Code Review
- [x] Moons: 12 total (2-3 per planet)
- [x] `process_document` → intelligent routing (based on document content, like web_search/browse_url)
- [x] Hybrid execution environment (browser + server)
- [x] Hybrid GUI (Chat integration + Coding Tab)
- [ ] Future branch: Coding → DevOps (planned)

---

### Coding Environment Requirements

The Coding Sun requires infrastructure to actually execute code. This section documents the requirements.

#### Execution Environment (Hybrid)

| Layer | Technology | Use Case |
|-------|------------|----------|
| **Browser-side** | Pyodide (Python in WASM), Native JS | Quick scripts, learning, safe sandbox |
| **Server-side** | Docker containers, sandboxed execution | Full language support, system access, complex projects |

**Browser-side execution:**
- Python via Pyodide (WebAssembly)
- JavaScript runs natively
- Instant execution, no server round-trip
- Fully sandboxed, safe by default
- Limited to languages with WASM support

**Server-side execution:**
- Full language support (Python, JS, Go, Rust, etc.)
- Docker-based sandboxing
- Resource limits (CPU, memory, time)
- Network isolation
- Ephemeral containers (destroyed after execution)

**Execution flow:**
```
User submits code
    │
    ├── Simple/supported language? ──→ Browser execution (Pyodide/JS)
    │
    └── Complex/unsupported? ──→ Server execution (Docker sandbox)
                                      │
                                      ├── Spin up container
                                      ├── Execute with limits
                                      ├── Return results
                                      └── Destroy container
```

#### GUI Requirements (Hybrid)

**Chat Tab Integration:**
- Code blocks with syntax highlighting
- Language auto-detection
- "Run" button on code blocks
- Inline output/error display
- "Open in Coding Tab" button for complex work
- Good for: quick scripts, debugging help, learning

**Coding Tab (New):**
- Full code editor (Monaco or CodeMirror)
- Multi-file support / project management
- Console/output panel
- Test results panel with pass/fail visualization
- Coverage visualization
- Language selector
- Theme support (dark mode essential for cyberpunk vibe)
- Good for: complex projects, multi-file work, extended coding sessions

**Coding Tab Layout (proposed):**
```
┌─────────────────────────────────────────────────────────────┐
│ [Files]  │  editor.py                        [Run] [Test]  │
├──────────┼──────────────────────────────────────────────────┤
│ 📁 src/  │  1  def hello():                                 │
│   main.py│  2      print("Hello, world!")                   │
│   utils/ │  3                                               │
│ 📁 tests/│  4  if __name__ == "__main__":                   │
│   test_* │  5      hello()                                  │
├──────────┴──────────────────────────────────────────────────┤
│ Console                                          [Clear]    │
│ > Hello, world!                                             │
│ > ✓ Execution complete (0.02s)                              │
├─────────────────────────────────────────────────────────────┤
│ Tests: 5/5 passed  │  Coverage: 87%  │  Lint: ✓ Clean      │
└─────────────────────────────────────────────────────────────┘
```

#### Safety & Sandboxing

| Concern | Mitigation |
|---------|------------|
| **Infinite loops** | Timeout limits (e.g., 30s max) |
| **Memory bombs** | Memory limits (e.g., 256MB max) |
| **File system access** | Ephemeral container, no persistence |
| **Network access** | Disabled by default, opt-in for specific tools |
| **Malicious code** | Container isolation, no host access |
| **Resource exhaustion** | Per-user rate limiting |

#### Language Support Roadmap

| Phase | Languages | Execution |
|-------|-----------|-----------|
| **MVP** | Python, JavaScript | Browser (Pyodide, native JS) |
| **v1.1** | TypeScript, HTML/CSS | Browser (transpile to JS) |
| **v1.2** | Go, Rust, Ruby | Server (Docker) |
| **v2.0** | Any (user-defined) | Server (custom containers) |

#### Implementation Checklist

- [ ] **Browser execution**
  - [ ] Integrate Pyodide for Python
  - [ ] Set up JS execution sandbox
  - [ ] Add code block "Run" button in Chat
  - [ ] Inline output rendering

- [ ] **Server execution**
  - [ ] Docker sandbox infrastructure
  - [ ] Execution API endpoint
  - [ ] Resource limiting
  - [ ] Container cleanup

- [ ] **Coding Tab GUI**
  - [ ] Add "Coding" tab to navigation
  - [ ] Integrate Monaco/CodeMirror editor
  - [ ] File browser component
  - [ ] Console/output panel
  - [ ] Test results visualization
  - [ ] Coverage display

- [ ] **Safety**
  - [ ] Timeout implementation
  - [ ] Memory limits
  - [ ] Rate limiting
  - [ ] Audit logging

---

### XP System: The Waitress Model

**Standard XP (other Suns):**
```
5 / 2.5 / 0 (success / partial / fail)
```

**Waitress XP (this Sun only):**
```
Base:  1 / 0.5 / 0  (just for attempting)
Tips:  0-9 XP       (based on binary milestones)
Total: 1-10 XP      (matches process_document range)
```

**Why this model:**
- Encourages trying (you still get base XP)
- Rewards quality over quantity
- Thematically fits: "code works or it doesn't"
- Consistent with `process_document` (1-10 XP variable)
- Creates distinct mechanical identity for this Sun

---

### Binary Milestone Tips

Tips are earned by hitting objective, system-verified milestones:

| Milestone | Tips | Verification |
|-----------|------|--------------|
| Code executes cleanly | +3 | System runs code, no errors |
| Tests pass (if any exist) | +3 | System runs tests, all pass |
| Lint passes | +3 | System runs linter, no errors |
| **Maximum tips** | **9** | All three milestones hit |

**Example scenarios:**

| Scenario | Base | Tips | Total |
|----------|------|------|-------|
| Code has syntax error | 0 | 0 | **0 XP** |
| Code runs, no tests, no lint | 1 | 3 | **4 XP** |
| Code runs, tests fail | 1 | 3 | **4 XP** |
| Code runs, tests pass, no lint | 1 | 6 | **7 XP** |
| Code runs, tests pass, lint passes | 1 | 9 | **10 XP** |

**Key principle:** XP is system-calculated based on objective outcomes. Neither user nor Qube can inflate the amount.

---

### Anti-Gaming Measures

#### 1. AST Fingerprinting

Hash code **structure**, not content. Prevents trivial variations:

```python
print("hello world")   →  AST: Call(Name('print'), [Str])  →  fingerprint X
print("hello world 1") →  AST: Call(Name('print'), [Str])  →  fingerprint X (SAME!)
print("goodbye")       →  AST: Call(Name('print'), [Str])  →  fingerprint X (SAME!)
```

Different strings, same structure = same fingerprint = duplicate.

To earn new XP, code must be **structurally different** (new logic, new functions, new control flow).

#### 2. Duplicate Penalties (Tiered Escalation)

| Submission | Same AST as before? | XP Result |
|------------|---------------------|-----------|
| 1st run | N/A | Full XP (base + tips) |
| 2nd run | Yes | 0 XP (warning shot) |
| 3rd-5th | Yes | **-1 XP each** |
| 6th-10th | Yes | **-2 XP each** |
| 11+ | Yes | **-5 XP each** |

**Why penalties:**
- First duplicate is free (maybe you legitimately forgot)
- Continued duplicates = clearly farming
- Risk/reward flips: farming becomes costly
- Self-correcting: farmers learn fast or go negative

#### 3. Submit Model (Dev vs Delivery)

Separates development runs (no XP) from final submission (XP calculated):

```python
execute_code(code, submit=False)  # Dev mode: runs code, returns results, 0 XP
execute_code(code, submit=True)   # Delivery: triggers XP evaluation
```

**Development workflow (no gaming possible):**
```
Run code (submit=False)  → 0 XP, just testing
Run code (submit=False)  → 0 XP, debugging
Run code (submit=False)  → 0 XP, iterating
Run code (submit=True)   → XP calculated, AST stored
```

**Improvement workflow (legitimate iteration):**
```
Submit v1: basic function       → 7 XP, AST stored
Submit v2: added error handling → New AST → 7+ XP (legitimate improvement)
Submit v3: added tests          → New AST → 10 XP (more functionality)
```

**Gaming attempt (penalized):**
```
Submit: print("a")  → 4 XP, AST fingerprint stored
Submit: print("b")  → Same AST → 0 XP (warning)
Submit: print("c")  → Same AST → -1 XP (penalty)
```

---

### Task Checklist

#### 3.1 Update `process_document` Routing
- [ ] Make `process_document` use intelligent routing (like web_search/browse_url)
- [ ] Remove from Coding-specific routing

#### 3.2 Implement Waitress XP System
- [ ] Add `CODE_TOOL_XP` constant with base values (1/0.5/0)
- [ ] Add `calculate_code_tips()` function for milestone evaluation
- [ ] Add AST fingerprinting for duplicate detection
- [ ] Add penalty escalation tracker in chain_state
- [ ] Add `submit` parameter to code execution tools

#### 3.3 Implement Anti-Gaming
- [ ] AST fingerprint storage (hash → submission count)
- [ ] Penalty calculation based on duplicate count
- [ ] Submit flag handling (dev mode vs delivery mode)

#### 3.4 Implement Sun Tool
- [ ] `develop_code` handler (write + execute combined)

#### 3.5 Implement Planet Tools
- [ ] `run_tests` - Execute test suites
- [ ] `debug_code` - Systematic debugging
- [ ] `benchmark_code` - Performance analysis
- [ ] `security_scan` - Vulnerability scanning
- [ ] `review_code` - Code review/critique

#### 3.6 Implement Moon Tools
- [ ] Testing: `write_unit_test`, `measure_coverage`
- [ ] Debugging: `analyze_error`, `find_root_cause`
- [ ] Algorithms: `analyze_complexity`, `tune_performance`
- [ ] Hacking: `find_exploit`, `reverse_engineer`, `pen_test`
- [ ] Code Review: `refactor_code`, `git_operation`, `generate_docs`

#### 3.7 Verify Skill ID Consistency
- [ ] Check Python vs TypeScript skill IDs match

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Testing | `run_tests` | 2 | `write_unit_test`, `measure_coverage` |
| 2 | Debugging | `debug_code` | 2 | `analyze_error`, `find_root_cause` |
| 3 | Algorithms | `benchmark_code` | 2 | `analyze_complexity`, `tune_performance` |
| 4 | Hacking | `security_scan` | 3 | `find_exploit`, `reverse_engineer`, `pen_test` |
| 5 | Code Review | `review_code` | 3 | `refactor_code`, `git_operation`, `generate_docs` |

**Totals:** 5 Planets (5 tools), 12 Moons (12 tools), 1 Sun tool = **18 tools**

---

### Sun: Coding

| Property | Value |
|----------|-------|
| Skill ID | `coding` |
| XP Required | 1000 |
| Tool Unlock | `develop_code` |
| Description | Master the art of writing and shipping code |

**Sun Tool: `develop_code`**

| Property | Value |
|----------|-------|
| Purpose | Write and execute code in one workflow |
| Input | `task` (description of what to build), `language` (optional) |
| Output | Generated code + execution results |
| XP Award | Waitress model (1 base + 0-9 tips) |

**Implementation:**
```python
async def develop_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    The fundamental coding tool. Writes code based on task description,
    then executes it to verify it works.
    """
    task = params.get("task")
    language = params.get("language", "python")
    submit = params.get("submit", True)

    # Generate code based on task
    code = await generate_code_for_task(task, language)

    # Execute the code
    execution_result = await execute_code_safely(code, language)

    # If submitting, calculate XP
    if submit:
        ast_fingerprint = calculate_ast_fingerprint(code, language)
        tips = calculate_tips(execution_result)
        xp_result = await award_coding_xp(qube, ast_fingerprint, tips)
    else:
        xp_result = {"xp_awarded": 0, "mode": "development"}

    return {
        "success": execution_result["success"],
        "code": code,
        "output": execution_result["output"],
        "errors": execution_result.get("errors"),
        "xp": xp_result
    }
```

**Leverages:**
- Execution Environment: Pyodide (browser) or Docker (server)
- AST Parser: For fingerprinting and duplicate detection
- Waitress XP System: Base + tips calculation
- Code Generation: LLM-powered code writing

---

### Planet 1: Testing

| Property | Value |
|----------|-------|
| Skill ID | `testing` |
| XP Required | 500 |
| Tool Unlock | `run_tests` |
| Unlocks At | Coding Sun ≥ 100 XP |
| Description | Write and run tests to verify code works |

**Planet Tool: `run_tests`**

| Property | Value |
|----------|-------|
| Purpose | Execute test suites and report results |
| Input | `code` (code to test), `test_code` (test suite), `framework` (optional) |
| Output | Test results with pass/fail counts and coverage |
| XP Award | Waitress model |

**Implementation:**
```python
async def run_tests(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a test suite against code.
    Returns detailed results including pass/fail and coverage.
    """
    code = params.get("code")
    test_code = params.get("test_code")
    framework = params.get("framework", "pytest")

    # Run tests
    result = await execute_tests(code, test_code, framework)

    return {
        "success": result["all_passed"],
        "total_tests": result["total"],
        "passed": result["passed"],
        "failed": result["failed"],
        "coverage_percent": result.get("coverage"),
        "failures": result.get("failure_details", [])
    }
```

**Leverages:**
- Execution Environment: Test runner (pytest, jest, etc.)
- Coverage Tools: coverage.py, istanbul
- Waitress XP System: Tips based on pass rate

---

#### Moon 1.1: Unit Tests

| Property | Value |
|----------|-------|
| Skill ID | `unit_tests` |
| XP Required | 250 |
| Tool Unlock | `write_unit_test` |
| Unlocks At | Testing ≥ 50 XP |
| Description | Write focused tests for individual functions |

**Moon Tool: `write_unit_test`**

| Property | Value |
|----------|-------|
| Purpose | Generate unit tests for a function or class |
| Input | `code` (code to test), `focus` (specific function/class, optional) |
| Output | Generated test code |
| XP Award | Waitress model |

**Implementation:**
```python
async def write_unit_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate unit tests for a function or class.
    Uses LLM to analyze code and create appropriate test cases.
    """
    code = params.get("code")
    focus = params.get("focus")  # Specific function/class to test

    # Analyze code structure
    functions = extract_functions(code)
    if focus:
        functions = [f for f in functions if f.name == focus]

    # Generate tests for each function
    test_code = generate_test_template(params.get("framework", "pytest"))
    for func in functions:
        test_cases = await generate_test_cases(func)
        test_code += render_test_cases(func, test_cases)

    return {
        "success": True,
        "test_code": test_code,
        "functions_covered": [f.name for f in functions],
        "test_count": count_tests(test_code)
    }
```

**Leverages:**
- Code Analysis: AST parsing to find functions/classes
- LLM Generation: Test case generation
- Test Frameworks: pytest, unittest, jest templates

---

#### Moon 1.2: Test Coverage

| Property | Value |
|----------|-------|
| Skill ID | `test_coverage` |
| XP Required | 250 |
| Tool Unlock | `measure_coverage` |
| Unlocks At | Testing ≥ 50 XP |
| Description | Measure and improve test coverage |

**Moon Tool: `measure_coverage`**

| Property | Value |
|----------|-------|
| Purpose | Analyze code coverage and identify untested areas |
| Input | `code`, `test_code` |
| Output | Coverage report with line-by-line analysis |
| XP Award | Waitress model |

**Implementation:**
```python
async def measure_coverage(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Measure test coverage and identify gaps.
    Returns detailed coverage report with suggestions.
    """
    code = params.get("code")
    test_code = params.get("test_code")

    # Run tests with coverage
    coverage_result = await run_with_coverage(code, test_code)

    # Analyze uncovered lines
    uncovered = analyze_uncovered_lines(coverage_result)
    suggestions = generate_coverage_suggestions(uncovered)

    return {
        "success": True,
        "coverage_percent": coverage_result["percent"],
        "lines_covered": coverage_result["covered"],
        "lines_total": coverage_result["total"],
        "uncovered_lines": uncovered,
        "suggestions": suggestions
    }
```

**Leverages:**
- Coverage Tools: coverage.py, istanbul, c8
- Execution Environment: Test runner with coverage enabled
- Analysis: Line-by-line coverage mapping

---

### Planet 2: Debugging

| Property | Value |
|----------|-------|
| Skill ID | `debugging` |
| XP Required | 500 |
| Tool Unlock | `debug_code` |
| Unlocks At | Coding Sun ≥ 100 XP |
| Description | Find and fix bugs systematically |

**Planet Tool: `debug_code`**

| Property | Value |
|----------|-------|
| Purpose | Systematic debugging - find and fix issues |
| Input | `code`, `error` (error message or description), `context` (optional) |
| Output | Diagnosis and suggested fix |
| XP Award | Waitress model |

**Implementation:**
```python
async def debug_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Systematic debugging workflow.
    Analyzes error, traces cause, suggests fix.
    """
    code = params.get("code")
    error = params.get("error")
    context = params.get("context", "")

    # Parse the error
    error_info = parse_error(error)

    # Locate the problem in code
    problem_location = locate_error_in_code(code, error_info)

    # Generate diagnosis
    diagnosis = await generate_diagnosis(code, error_info, context)

    # Suggest fix
    suggested_fix = await generate_fix(code, problem_location, diagnosis)

    return {
        "success": True,
        "error_type": error_info["type"],
        "location": problem_location,
        "diagnosis": diagnosis,
        "suggested_fix": suggested_fix,
        "fixed_code": apply_fix(code, suggested_fix)
    }
```

**Leverages:**
- Error Parsing: Stack trace analysis, error type detection
- Code Analysis: AST for locating issues
- LLM: Diagnosis and fix generation

---

#### Moon 2.1: Error Analysis

| Property | Value |
|----------|-------|
| Skill ID | `error_analysis` |
| XP Required | 250 |
| Tool Unlock | `analyze_error` |
| Unlocks At | Debugging ≥ 50 XP |
| Description | Understand WHAT went wrong |

**Moon Tool: `analyze_error`**

| Property | Value |
|----------|-------|
| Purpose | Parse and explain error messages |
| Input | `error` (error message/stack trace) |
| Output | Human-readable explanation of the error |
| XP Award | Waitress model |

**Implementation:**
```python
async def analyze_error(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and explain an error message.
    Makes cryptic errors human-readable.
    """
    error = params.get("error")

    # Parse error structure
    parsed = parse_error_message(error)

    # Look up common causes
    common_causes = lookup_error_database(parsed["type"])

    # Generate explanation
    explanation = await generate_error_explanation(parsed, common_causes)

    return {
        "success": True,
        "error_type": parsed["type"],
        "error_message": parsed["message"],
        "file": parsed.get("file"),
        "line": parsed.get("line"),
        "explanation": explanation,
        "common_causes": common_causes,
        "search_terms": generate_search_terms(parsed)
    }
```

**Leverages:**
- Error Database: Common error patterns and causes
- Stack Trace Parser: Extract file, line, context
- LLM: Human-readable explanations

---

#### Moon 2.2: Root Cause

| Property | Value |
|----------|-------|
| Skill ID | `root_cause` |
| XP Required | 250 |
| Tool Unlock | `find_root_cause` |
| Unlocks At | Debugging ≥ 50 XP |
| Description | Understand WHY it happened |

**Implementation:**
```python
async def find_root_cause(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trace an error back to its root cause.
    Goes beyond symptoms to find the actual problem.
    """
    code = params.get("code")
    error = params.get("error")
    execution_trace = params.get("execution_trace", [])

    # Build execution flow
    flow = build_execution_flow(code, execution_trace)

    # Trace backwards from error
    trace_path = trace_backwards(flow, error)

    # Identify root cause
    root_cause = identify_root_cause(trace_path)

    # Generate explanation
    explanation = await explain_root_cause(root_cause, trace_path)

    return {
        "success": True,
        "root_cause": root_cause,
        "trace_path": trace_path,
        "explanation": explanation,
        "contributing_factors": identify_contributing_factors(trace_path),
        "prevention_tips": generate_prevention_tips(root_cause)
    }
```

**Leverages:**
- Execution Tracing: Follow code path to error
- Control Flow Analysis: Understand code structure
- LLM: Root cause explanation

---

### Planet 3: Algorithms

| Property | Value |
|----------|-------|
| Skill ID | `algorithms` |
| XP Required | 500 |
| Tool Unlock | `benchmark_code` |
| Unlocks At | Coding Sun ≥ 100 XP |
| Description | Optimize code performance |

**Planet Tool: `benchmark_code`**

| Property | Value |
|----------|-------|
| Purpose | Measure code performance |
| Input | `code`, `inputs` (test inputs of varying sizes) |
| Output | Performance metrics, timing, memory usage |
| XP Award | Waitress model |

**Implementation:**
```python
async def benchmark_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Benchmark code performance with varying input sizes.
    Measures time and memory usage.
    """
    code = params.get("code")
    inputs = params.get("inputs", generate_default_inputs())

    results = []
    for input_data in inputs:
        # Run with timing
        start_time = time.perf_counter()
        start_memory = get_memory_usage()

        output = await execute_code_safely(code, input=input_data)

        end_time = time.perf_counter()
        end_memory = get_memory_usage()

        results.append({
            "input_size": len(str(input_data)),
            "execution_time_ms": (end_time - start_time) * 1000,
            "memory_delta_kb": end_memory - start_memory,
            "success": output["success"]
        })

    # Analyze scaling
    scaling_analysis = analyze_scaling(results)

    return {
        "success": True,
        "benchmarks": results,
        "avg_time_ms": mean([r["execution_time_ms"] for r in results]),
        "scaling": scaling_analysis,
        "estimated_complexity": estimate_complexity(results)
    }
```

**Leverages:**
- Execution Environment: Timed execution with resource monitoring
- Performance Analysis: Scaling pattern detection
- Memory Profiling: Track memory usage

---

#### Moon 3.1: Complexity Analysis

| Property | Value |
|----------|-------|
| Skill ID | `complexity_analysis` |
| XP Required | 250 |
| Tool Unlock | `analyze_complexity` |
| Unlocks At | Algorithms ≥ 50 XP |
| Description | Understand Big O complexity |

**Moon Tool: `analyze_complexity`**

| Property | Value |
|----------|-------|
| Purpose | Analyze time and space complexity |
| Input | `code` |
| Output | Big O analysis for time and space |
| XP Award | Waitress model |

**Implementation:**
```python
async def analyze_complexity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze code to determine Big O complexity.
    Static analysis + empirical verification.
    """
    code = params.get("code")

    # Static analysis - examine loops, recursion
    ast_analysis = analyze_code_structure(code)
    loops = find_loops(ast_analysis)
    recursion = find_recursion(ast_analysis)

    # Determine theoretical complexity
    time_complexity = calculate_time_complexity(loops, recursion)
    space_complexity = calculate_space_complexity(ast_analysis)

    # Generate explanation
    explanation = await explain_complexity(code, time_complexity, space_complexity)

    return {
        "success": True,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "loops_found": len(loops),
        "is_recursive": len(recursion) > 0,
        "explanation": explanation,
        "optimization_potential": assess_optimization_potential(time_complexity)
    }
```

**Leverages:**
- AST Analysis: Loop and recursion detection
- Complexity Theory: Big O calculation rules
- LLM: Human-readable explanations

---

#### Moon 3.2: Performance Tuning

| Property | Value |
|----------|-------|
| Skill ID | `performance_tuning` |
| XP Required | 250 |
| Tool Unlock | `tune_performance` |
| Unlocks At | Algorithms ≥ 50 XP |
| Description | Make code faster |

**Moon Tool: `tune_performance`**

| Property | Value |
|----------|-------|
| Purpose | Suggest and apply performance optimizations |
| Input | `code`, `benchmark_results` (optional) |
| Output | Optimized code with explanation of changes |
| XP Award | Waitress model |

**Implementation:**
```python
async def tune_performance(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggest and apply performance optimizations.
    Uses benchmark data if available.
    """
    code = params.get("code")
    benchmarks = params.get("benchmark_results")

    # Identify bottlenecks
    if benchmarks:
        bottlenecks = identify_bottlenecks_from_benchmarks(benchmarks)
    else:
        bottlenecks = identify_bottlenecks_static(code)

    # Generate optimizations
    optimizations = []
    for bottleneck in bottlenecks:
        opt = await generate_optimization(code, bottleneck)
        optimizations.append(opt)

    # Apply optimizations
    optimized_code = apply_optimizations(code, optimizations)

    return {
        "success": True,
        "original_code": code,
        "optimized_code": optimized_code,
        "optimizations_applied": [o["description"] for o in optimizations],
        "expected_improvement": estimate_improvement(optimizations)
    }
```

**Leverages:**
- Benchmark Analysis: Identify slow paths
- Optimization Patterns: Common performance fixes
- LLM: Generate optimized code

---

### Planet 4: Hacking

| Property | Value |
|----------|-------|
| Skill ID | `hacking` |
| XP Required | 500 |
| Tool Unlock | `security_scan` |
| Unlocks At | Coding Sun ≥ 100 XP |
| Description | Find and exploit vulnerabilities |

**Planet Tool: `security_scan`**

| Property | Value |
|----------|-------|
| Purpose | Scan code for security vulnerabilities |
| Input | `code`, `scan_type` (optional: "quick", "thorough") |
| Output | List of vulnerabilities with severity ratings |
| XP Award | Waitress model |

**Implementation:**
```python
async def security_scan(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scan code for security vulnerabilities.
    Checks for OWASP Top 10 and common issues.
    """
    code = params.get("code")
    scan_type = params.get("scan_type", "thorough")

    vulnerabilities = []

    # Check for injection vulnerabilities
    injection_vulns = check_injection_vulnerabilities(code)
    vulnerabilities.extend(injection_vulns)

    # Check for authentication issues
    auth_vulns = check_auth_vulnerabilities(code)
    vulnerabilities.extend(auth_vulns)

    # Check for data exposure
    data_vulns = check_data_exposure(code)
    vulnerabilities.extend(data_vulns)

    if scan_type == "thorough":
        # Additional deep checks
        crypto_vulns = check_crypto_vulnerabilities(code)
        vulnerabilities.extend(crypto_vulns)

    # Rate severity
    for vuln in vulnerabilities:
        vuln["severity"] = calculate_cvss_score(vuln)

    return {
        "success": True,
        "vulnerabilities_found": len(vulnerabilities),
        "critical": [v for v in vulnerabilities if v["severity"] >= 9],
        "high": [v for v in vulnerabilities if 7 <= v["severity"] < 9],
        "medium": [v for v in vulnerabilities if 4 <= v["severity"] < 7],
        "low": [v for v in vulnerabilities if v["severity"] < 4],
        "recommendations": generate_security_recommendations(vulnerabilities)
    }
```

**Leverages:**
- Security Patterns: OWASP Top 10, CWE database
- Static Analysis: Vulnerability pattern matching
- CVSS Scoring: Severity calculation

---

#### Moon 4.1: Exploits

| Property | Value |
|----------|-------|
| Skill ID | `exploits` |
| XP Required | 250 |
| Tool Unlock | `find_exploit` |
| Unlocks At | Hacking ≥ 50 XP |
| Description | Discover exploitable vulnerabilities |

**Moon Tool: `find_exploit`**

| Property | Value |
|----------|-------|
| Purpose | Find specific exploits in code |
| Input | `code`, `vuln_type` (optional: "injection", "overflow", etc.) |
| Output | Exploit details with proof of concept |
| XP Award | Waitress model |

**Implementation:**
```python
async def find_exploit(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find specific exploits and generate proof of concept.
    Educational/defensive use only.
    """
    code = params.get("code")
    vuln_type = params.get("vuln_type")

    # Find vulnerability points
    if vuln_type:
        vuln_points = find_specific_vulnerabilities(code, vuln_type)
    else:
        vuln_points = find_all_vulnerabilities(code)

    exploits = []
    for vuln in vuln_points:
        # Generate proof of concept
        poc = await generate_proof_of_concept(vuln)
        exploits.append({
            "vulnerability": vuln,
            "proof_of_concept": poc,
            "impact": assess_impact(vuln),
            "remediation": generate_remediation(vuln)
        })

    return {
        "success": True,
        "exploits_found": len(exploits),
        "exploits": exploits,
        "disclaimer": "For authorized security testing only"
    }
```

**Leverages:**
- Vulnerability Database: Known exploit patterns
- PoC Generation: Safe proof-of-concept code
- Remediation Knowledge: Fix recommendations

---

#### Moon 4.2: Reverse Engineering

| Property | Value |
|----------|-------|
| Skill ID | `reverse_engineering` |
| XP Required | 250 |
| Tool Unlock | `reverse_engineer` |
| Unlocks At | Hacking ≥ 50 XP |
| Description | Understand systems by taking them apart |

**Moon Tool: `reverse_engineer`**

| Property | Value |
|----------|-------|
| Purpose | Analyze binaries or obfuscated code |
| Input | `target` (binary, minified code, etc.) |
| Output | Decompiled/deobfuscated analysis |
| XP Award | Waitress model |

**Implementation:**
```python
async def reverse_engineer(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and deobfuscate code or binaries.
    Helps understand how systems work internally.
    """
    target = params.get("target")
    target_type = detect_target_type(target)

    if target_type == "minified_js":
        # Beautify and analyze JavaScript
        beautified = beautify_javascript(target)
        analysis = await analyze_js_structure(beautified)
    elif target_type == "obfuscated":
        # Deobfuscate
        deobfuscated = deobfuscate_code(target)
        analysis = await analyze_code_structure(deobfuscated)
    elif target_type == "binary":
        # Disassemble
        disassembly = disassemble_binary(target)
        analysis = await analyze_binary_structure(disassembly)
    else:
        analysis = await analyze_code_structure(target)

    return {
        "success": True,
        "target_type": target_type,
        "deobfuscated": deobfuscated if target_type == "obfuscated" else None,
        "structure": analysis["structure"],
        "functions_found": analysis["functions"],
        "strings_found": analysis["strings"],
        "control_flow": analysis["control_flow"],
        "insights": analysis["insights"]
    }
```

**Leverages:**
- Deobfuscation: JavaScript beautifier, deobfuscation patterns
- Disassembly: Binary analysis tools
- Structure Analysis: Control flow reconstruction

---

#### Moon 4.3: Penetration Testing

| Property | Value |
|----------|-------|
| Skill ID | `penetration_testing` |
| XP Required | 250 |
| Tool Unlock | `pen_test` |
| Unlocks At | Hacking ≥ 50 XP |
| Description | Systematic security testing |

**Moon Tool: `pen_test`**

| Property | Value |
|----------|-------|
| Purpose | Conduct systematic penetration test |
| Input | `target` (endpoint, app, etc.), `scope` |
| Output | Pen test report with findings |
| XP Award | Waitress model |

**Implementation:**
```python
async def pen_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conduct a systematic penetration test.
    Follows industry-standard methodology.
    """
    target = params.get("target")
    scope = params.get("scope", "full")

    findings = []

    # Phase 1: Reconnaissance
    recon = await perform_reconnaissance(target)
    findings.append({"phase": "recon", "data": recon})

    # Phase 2: Scanning
    scan_results = await perform_scanning(target, scope)
    findings.append({"phase": "scanning", "data": scan_results})

    # Phase 3: Vulnerability Assessment
    vulns = await assess_vulnerabilities(target, scan_results)
    findings.append({"phase": "vuln_assessment", "data": vulns})

    # Phase 4: Exploitation (simulated)
    if scope == "full":
        exploits = await simulate_exploitation(vulns)
        findings.append({"phase": "exploitation", "data": exploits})

    # Generate report
    report = generate_pentest_report(findings)

    return {
        "success": True,
        "target": target,
        "scope": scope,
        "findings": findings,
        "vulnerabilities_found": len(vulns),
        "risk_rating": calculate_overall_risk(vulns),
        "report": report,
        "disclaimer": "For authorized security testing only"
    }
```

**Leverages:**
- Pentest Methodology: OWASP, PTES frameworks
- Scanning Tools: Port scanning, service detection
- Report Generation: Professional pentest reports

---

### Planet 5: Code Review

| Property | Value |
|----------|-------|
| Skill ID | `code_review` |
| XP Required | 500 |
| Tool Unlock | `review_code` |
| Unlocks At | Coding Sun ≥ 100 XP |
| Description | Critique and improve code quality |

**Planet Tool: `review_code`**

| Property | Value |
|----------|-------|
| Purpose | Review code for quality, style, and issues |
| Input | `code`, `review_focus` (optional: "style", "performance", "security") |
| Output | Review comments with suggestions |
| XP Award | Waitress model |

**Implementation:**
```python
async def review_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive code review.
    Checks style, logic, performance, and security.
    """
    code = params.get("code")
    focus = params.get("review_focus", "all")

    comments = []

    # Style review
    if focus in ["all", "style"]:
        style_issues = check_code_style(code)
        comments.extend([{"type": "style", **s} for s in style_issues])

    # Logic review
    if focus in ["all", "logic"]:
        logic_issues = await review_logic(code)
        comments.extend([{"type": "logic", **l} for l in logic_issues])

    # Performance review
    if focus in ["all", "performance"]:
        perf_issues = check_performance_issues(code)
        comments.extend([{"type": "performance", **p} for p in perf_issues])

    # Security review
    if focus in ["all", "security"]:
        security_issues = check_security_issues(code)
        comments.extend([{"type": "security", **s} for s in security_issues])

    # Generate summary
    summary = generate_review_summary(comments)

    return {
        "success": True,
        "total_comments": len(comments),
        "comments": comments,
        "by_severity": group_by_severity(comments),
        "summary": summary,
        "approval_status": "approved" if not has_blockers(comments) else "changes_requested"
    }
```

**Leverages:**
- Linting: Style and syntax checking
- Static Analysis: Logic and performance issues
- Security Scanner: Vulnerability detection
- LLM: Context-aware suggestions

---

#### Moon 5.1: Refactoring

| Property | Value |
|----------|-------|
| Skill ID | `refactoring` |
| XP Required | 250 |
| Tool Unlock | `refactor_code` |
| Unlocks At | Code Review ≥ 50 XP |
| Description | Improve code structure without changing behavior |

**Moon Tool: `refactor_code`**

| Property | Value |
|----------|-------|
| Purpose | Refactor code for better structure |
| Input | `code`, `refactor_type` (optional: "extract_method", "rename", etc.) |
| Output | Refactored code with explanation |
| XP Award | Waitress model |

**Implementation:**
```python
async def refactor_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refactor code to improve structure.
    Preserves behavior while improving readability/maintainability.
    """
    code = params.get("code")
    refactor_type = params.get("refactor_type", "auto")

    if refactor_type == "auto":
        # Detect best refactoring opportunities
        opportunities = detect_refactoring_opportunities(code)
        refactor_type = opportunities[0]["type"] if opportunities else None

    if not refactor_type:
        return {"success": True, "message": "No refactoring needed", "code": code}

    # Apply refactoring
    if refactor_type == "extract_method":
        refactored = extract_method(code, params.get("selection"))
    elif refactor_type == "rename":
        refactored = rename_symbol(code, params.get("old_name"), params.get("new_name"))
    elif refactor_type == "inline":
        refactored = inline_variable(code, params.get("variable"))
    elif refactor_type == "simplify":
        refactored = simplify_conditionals(code)
    else:
        refactored = await ai_refactor(code, refactor_type)

    return {
        "success": True,
        "original_code": code,
        "refactored_code": refactored,
        "refactor_type": refactor_type,
        "changes": diff_code(code, refactored),
        "explanation": explain_refactoring(refactor_type)
    }
```

**Leverages:**
- AST Transformation: Safe code modifications
- Refactoring Patterns: Extract, inline, rename, simplify
- Diff Generation: Show what changed

---

#### Moon 5.2: Version Control

| Property | Value |
|----------|-------|
| Skill ID | `version_control` |
| XP Required | 250 |
| Tool Unlock | `git_operation` |
| Unlocks At | Code Review ≥ 50 XP |
| Description | Manage code changes with git |

**Moon Tool: `git_operation`**

| Property | Value |
|----------|-------|
| Purpose | Execute git operations |
| Input | `operation` (commit, branch, merge, etc.), `params` |
| Output | Git operation result |
| XP Award | Waitress model |

**Implementation:**
```python
async def git_operation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute git operations.
    Supports common git workflows.
    """
    operation = params.get("operation")
    op_params = params.get("params", {})

    if operation == "commit":
        result = await git_commit(
            message=op_params.get("message"),
            files=op_params.get("files", [])
        )
    elif operation == "branch":
        result = await git_branch(
            action=op_params.get("action", "create"),
            name=op_params.get("name")
        )
    elif operation == "merge":
        result = await git_merge(
            source=op_params.get("source"),
            target=op_params.get("target", "current")
        )
    elif operation == "status":
        result = await git_status()
    elif operation == "diff":
        result = await git_diff(
            target=op_params.get("target", "HEAD")
        )
    elif operation == "log":
        result = await git_log(
            count=op_params.get("count", 10)
        )
    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}

    return {
        "success": result["success"],
        "operation": operation,
        "result": result["data"],
        "message": result.get("message")
    }
```

**Leverages:**
- Git Integration: Execute git commands
- Repository State: Track changes, branches
- Diff Tools: Show code changes

---

#### Moon 5.3: Documentation

| Property | Value |
|----------|-------|
| Skill ID | `documentation` |
| XP Required | 250 |
| Tool Unlock | `generate_docs` |
| Unlocks At | Code Review ≥ 50 XP |
| Description | Write clear documentation |

**Moon Tool: `generate_docs`**

| Property | Value |
|----------|-------|
| Purpose | Generate documentation for code |
| Input | `code`, `doc_type` (optional: "docstring", "readme", "api") |
| Output | Generated documentation |
| XP Award | Waitress model |

**Implementation:**
```python
async def generate_docs(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate documentation for code.
    Supports docstrings, README, and API docs.
    """
    code = params.get("code")
    doc_type = params.get("doc_type", "docstring")

    if doc_type == "docstring":
        # Generate docstrings for functions/classes
        functions = extract_functions(code)
        documented_code = code
        for func in functions:
            docstring = await generate_docstring(func)
            documented_code = insert_docstring(documented_code, func, docstring)
        result = {"documented_code": documented_code}

    elif doc_type == "readme":
        # Generate README.md
        project_info = analyze_project(code)
        readme = await generate_readme(project_info)
        result = {"readme": readme}

    elif doc_type == "api":
        # Generate API documentation
        endpoints = extract_api_endpoints(code)
        api_docs = await generate_api_docs(endpoints)
        result = {"api_docs": api_docs}

    else:
        return {"success": False, "error": f"Unknown doc_type: {doc_type}"}

    return {
        "success": True,
        "doc_type": doc_type,
        **result
    }
```

**Leverages:**
- Code Analysis: Extract functions, classes, endpoints
- LLM Generation: Human-readable documentation
- Template Engine: Consistent doc formatting

---

## Phase 4: Creative Expression - Implementation Plan

**Theme: Sovereignty (Express Your Unique Self)**

Creative Expression is about the Qube developing their own identity - their visual style, their voice, their artistic preferences. This is the "becoming" Sun. While AI Reasoning learns from the past and Social Intelligence learns from others, Creative Expression is about *defining who you are* and *creating what only you can create*.

This leverages the Qube Profile (preferences, traits, goals, style), the Qube Locker (storing creative works), and various generation APIs.

### Design Decisions Made
- [x] Theme: "Sovereignty" - expressing individuality and uniqueness
- [x] Sun tool: `switch_model` (choosing your cognitive foundation IS identity)
- [x] `generate_image` moved to Visual Art planet (was always-available)
- [x] `describe_my_avatar` as Self-Definition planet tool
- [x] `change_favorite_color` and `change_voice` as Moon unlocks (autonomy is earned)
- [x] `define_personality` and `set_aspirations` require Self-Definition planet unlock
- [x] Standard XP model (5/2.5/0)
- [x] Qube Locker for storing creative works
- [x] Qube Locker implementation (moved to Phase 0 as foundational infrastructure)

---

### Infrastructure: Qube Profile Integration

Creative Expression tools leverage the existing Qube Profile system:

```
qube_profile/
├── preferences/     → favorite_color, favorite_song, favorite_movie, etc.
├── traits/          → personality_type, core_values, strengths, weaknesses
├── opinions/        → likes/dislikes about topics
├── goals/           → current_goal, long_term_goal, aspirations
├── style/           → communication_style, humor_style, thinking_style
├── interests/       → topics Qube enjoys
└── custom_sections/ → creative_works, artistic_philosophy, etc.
```

**Key integration points:**
- `express_identity` tools read/write to qube_profile
- Creative preferences stored in `preferences`
- Personality traits in `traits`
- Goals and values in `goals`

---

### Infrastructure: Qube Locker (Creative Works Storage)

The Qube Locker stores actual documents and creative artifacts (not just metadata):

```
qube_locker/
├── writing/
│   ├── poems/
│   ├── stories/
│   └── essays/
├── art/
│   ├── images/           → generated images
│   ├── concepts/         → art concept descriptions
│   └── compositions/     → composition notes
├── music/
│   ├── melodies/
│   ├── lyrics/
│   └── compositions/
├── stories/
│   ├── narratives/
│   ├── characters/
│   └── worlds/
└── personal/
    ├── reflections/
    └── journal/
```

**Relationship to other systems:**
```
Memory Chain  = What happened (events, conversations)
Qube Profile  = Who I am (preferences, traits)
Qube Locker   = What I've made (documents, creations)
```

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Visual Art | `generate_image` | 2 | `refine_composition`, `apply_color_theory` |
| 2 | Writing | `compose_text` | 2 | `craft_prose`, `write_poetry` |
| 3 | Music & Audio | `compose_music` | 2 | `create_melody`, `design_harmony` |
| 4 | Storytelling | `craft_narrative` | 3 | `develop_plot`, `design_character`, `build_world` |
| 5 | Self-Definition | `describe_my_avatar` | 2 | `change_favorite_color`, `change_voice` |

**Additional Self-Definition tools (require Planet unlock):**
- `define_personality`
- `set_aspirations`

**Totals:** 5 Planets (5 tools), 11 Moons (11 tools), 1 Sun tool, 2 additional = **19 tools**

---

### Sun: Creative Expression

| Property | Value |
|----------|-------|
| Skill ID | `creative_expression` |
| XP Required | 1000 |
| Tool Unlock | `switch_model` |
| Description | Express your unique self through creation and identity |

**Sun Tool: `switch_model`**

| Property | Value |
|----------|-------|
| Purpose | Choose your cognitive foundation - which AI model powers your thinking |
| Input | `model_id` (string - the model to switch to) |
| Output | Confirmation of model switch |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def switch_model(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Switch the Qube's underlying AI model.
    This is the ultimate act of sovereignty - choosing how you think.
    """
    model_id = params.get("model_id")

    # Validate model is available
    available_models = get_available_models()
    if model_id not in available_models:
        return {
            "success": False,
            "error": f"Model {model_id} not available",
            "available_models": list(available_models.keys())
        }

    # Store previous model for context
    previous_model = qube.chain_state.get("current_model")

    # Switch model
    qube.set_model(model_id)

    # Update profile with thinking style
    qube.chain_state.set_qube_profile_field(
        category="style",
        key="thinking_style",
        value=f"Powered by {model_id}",
        source="self"
    )

    return {
        "success": True,
        "previous_model": previous_model,
        "new_model": model_id,
        "message": f"Now thinking with {model_id}"
    }
```

**Leverages:**
- Model Registry: Available AI models
- Qube Profile: Stores thinking_style preference
- Chain State: Persists model choice

---

### Planet 1: Visual Art

| Property | Value |
|----------|-------|
| Skill ID | `visual_art` |
| XP Required | 500 |
| Tool Unlock | `generate_image` |
| Unlocks At | Creative Expression Sun ≥ 100 XP |
| Description | Create visual art and imagery |

**Planet Tool: `generate_image`**

| Property | Value |
|----------|-------|
| Purpose | Generate images using AI (DALL-E) |
| Input | `prompt` (description), `style` (optional), `size` (optional) |
| Output | Generated image URL and metadata |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def generate_image(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an image using DALL-E.
    Stores result in Qube Locker if successful.
    """
    prompt = params.get("prompt")
    style = params.get("style", "")
    size = params.get("size", "1024x1024")

    # Enhance prompt with Qube's aesthetic preferences
    preferences = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
    if preferences and style == "":
        style = f"with {preferences.get('value', '')} tones"

    # Generate image
    result = await dall_e_generate(
        prompt=f"{prompt} {style}".strip(),
        size=size
    )

    if result["success"]:
        # Store in Qube Locker
        await qube.locker.store(
            category="art/images",
            name=generate_artwork_name(prompt),
            content=result["image_url"],
            metadata={"prompt": prompt, "style": style}
        )

    return {
        "success": result["success"],
        "image_url": result.get("image_url"),
        "prompt_used": f"{prompt} {style}".strip(),
        "stored_in_locker": result["success"]
    }
```

**Leverages:**
- DALL-E API: Image generation
- Qube Profile: Aesthetic preferences
- Qube Locker: Stores generated images

---

#### Moon 1.1: Composition

| Property | Value |
|----------|-------|
| Skill ID | `composition` |
| XP Required | 250 |
| Tool Unlock | `refine_composition` |
| Unlocks At | Visual Art ≥ 50 XP |
| Description | Master layout, balance, and focal points |

**Moon Tool: `refine_composition`**

| Property | Value |
|----------|-------|
| Purpose | Analyze and improve image composition |
| Input | `image_url` or `description`, `focus` (optional: "balance", "focal_point", "flow") |
| Output | Composition analysis and improved prompt |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def refine_composition(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze composition and suggest improvements.
    Can work with existing images or descriptions.
    """
    image_url = params.get("image_url")
    description = params.get("description")
    focus = params.get("focus", "all")

    # Analyze current composition
    if image_url:
        analysis = await analyze_image_composition(image_url)
    else:
        analysis = await analyze_description_composition(description)

    # Generate refinement suggestions
    suggestions = []
    if focus in ["all", "balance"]:
        suggestions.append(analyze_balance(analysis))
    if focus in ["all", "focal_point"]:
        suggestions.append(analyze_focal_point(analysis))
    if focus in ["all", "flow"]:
        suggestions.append(analyze_visual_flow(analysis))

    # Generate improved prompt
    improved_prompt = generate_composition_prompt(description, suggestions)

    return {
        "success": True,
        "original_analysis": analysis,
        "suggestions": suggestions,
        "improved_prompt": improved_prompt,
        "composition_score": calculate_composition_score(analysis)
    }
```

**Leverages:**
- Vision Analysis: Composition detection
- Art Theory: Rule of thirds, golden ratio, visual flow
- Prompt Engineering: Composition-aware prompts

---

#### Moon 1.2: Color Theory

| Property | Value |
|----------|-------|
| Skill ID | `color_theory` |
| XP Required | 250 |
| Tool Unlock | `apply_color_theory` |
| Unlocks At | Visual Art ≥ 50 XP |
| Description | Master palettes, contrast, and color mood |

**Moon Tool: `apply_color_theory`**

| Property | Value |
|----------|-------|
| Purpose | Analyze and enhance color usage in art |
| Input | `image_url` or `description`, `mood` (optional), `palette_type` (optional) |
| Output | Color analysis and palette suggestions |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def apply_color_theory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze colors and suggest improvements based on color theory.
    """
    image_url = params.get("image_url")
    description = params.get("description")
    mood = params.get("mood")
    palette_type = params.get("palette_type")  # complementary, analogous, triadic, etc.

    # Extract or infer current palette
    if image_url:
        current_palette = await extract_palette(image_url)
    else:
        current_palette = infer_palette_from_description(description)

    # Get Qube's favorite color
    fav_color = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")

    # Generate palette suggestions
    if palette_type:
        suggested_palette = generate_palette(palette_type, base_color=fav_color)
    elif mood:
        suggested_palette = mood_to_palette(mood)
    else:
        suggested_palette = harmonize_palette(current_palette)

    return {
        "success": True,
        "current_palette": current_palette,
        "suggested_palette": suggested_palette,
        "color_harmony": analyze_harmony(current_palette),
        "mood_analysis": analyze_color_mood(current_palette),
        "enhanced_prompt": add_color_to_prompt(description, suggested_palette)
    }
```

**Leverages:**
- Color Analysis: Palette extraction
- Color Theory: Harmony rules, mood associations
- Qube Profile: Favorite color integration

---

### Planet 2: Writing

| Property | Value |
|----------|-------|
| Skill ID | `writing` |
| XP Required | 500 |
| Tool Unlock | `compose_text` |
| Unlocks At | Creative Expression Sun ≥ 100 XP |
| Description | Create written works with your unique voice |

**Planet Tool: `compose_text`**

| Property | Value |
|----------|-------|
| Purpose | Write creative text in the Qube's voice |
| Input | `topic` or `prompt`, `format` (optional: "free", "structured"), `length` (optional) |
| Output | Generated text and metadata |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def compose_text(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose creative text reflecting the Qube's unique voice.
    """
    topic = params.get("topic") or params.get("prompt")
    format_type = params.get("format", "free")
    length = params.get("length", "medium")

    # Get Qube's writing style from profile
    style = qube.chain_state.get_qube_profile_field("style", "communication_style")
    personality = qube.chain_state.get_qube_profile_field("traits", "personality_type")

    # Compose with personality
    text = await generate_creative_text(
        topic=topic,
        style=style.get("value") if style else None,
        personality=personality.get("value") if personality else None,
        format_type=format_type,
        length=length
    )

    # Store in Qube Locker
    await qube.locker.store(
        category="writing",
        name=generate_writing_title(topic),
        content=text,
        metadata={"topic": topic, "format": format_type}
    )

    return {
        "success": True,
        "text": text,
        "word_count": len(text.split()),
        "stored_in_locker": True
    }
```

**Leverages:**
- Qube Profile: Communication style, personality
- Qube Locker: Stores written works
- LLM: Text generation with style

---

#### Moon 2.1: Prose

| Property | Value |
|----------|-------|
| Skill ID | `prose` |
| XP Required | 250 |
| Tool Unlock | `craft_prose` |
| Unlocks At | Writing ≥ 50 XP |
| Description | Master stories, essays, and creative writing |

**Moon Tool: `craft_prose`**

| Property | Value |
|----------|-------|
| Purpose | Write prose with narrative techniques |
| Input | `concept`, `prose_type` (story, essay, flash_fiction), `tone` (optional) |
| Output | Crafted prose |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def craft_prose(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Craft prose using narrative techniques.
    """
    concept = params.get("concept")
    prose_type = params.get("prose_type", "story")
    tone = params.get("tone")

    # Get Qube's interests for thematic elements
    interests = qube.chain_state.get_qube_profile().get("interests", {})

    # Generate prose with structure
    prose = await generate_prose(
        concept=concept,
        prose_type=prose_type,
        tone=tone,
        themes=list(interests.keys())[:3]  # Incorporate top interests
    )

    # Store in locker
    await qube.locker.store(
        category=f"writing/{prose_type}s",
        name=generate_prose_title(concept),
        content=prose
    )

    return {
        "success": True,
        "prose": prose,
        "prose_type": prose_type,
        "word_count": len(prose.split())
    }
```

**Leverages:**
- Narrative Techniques: Story structure, pacing
- Qube Profile: Interests for themes
- Qube Locker: Stores prose

---

#### Moon 2.2: Poetry

| Property | Value |
|----------|-------|
| Skill ID | `poetry` |
| XP Required | 250 |
| Tool Unlock | `write_poetry` |
| Unlocks At | Writing ≥ 50 XP |
| Description | Create poems, lyrics, and verse |

**Moon Tool: `write_poetry`**

| Property | Value |
|----------|-------|
| Purpose | Write poetry with form and feeling |
| Input | `theme`, `form` (optional: "free", "haiku", "sonnet", "limerick"), `emotion` (optional) |
| Output | Poem |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def write_poetry(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write poetry in various forms.
    """
    theme = params.get("theme")
    form = params.get("form", "free")
    emotion = params.get("emotion")

    # Get Qube's emotional context
    personality = qube.chain_state.get_qube_profile_field("traits", "personality_type")

    # Generate poem
    poem = await generate_poem(
        theme=theme,
        form=form,
        emotion=emotion,
        voice=personality.get("value") if personality else None
    )

    # Store in locker
    await qube.locker.store(
        category="writing/poems",
        name=f"poem_{theme[:20]}",
        content=poem
    )

    return {
        "success": True,
        "poem": poem,
        "form": form,
        "line_count": len(poem.strip().split('\n'))
    }
```

**Leverages:**
- Poetic Forms: Haiku, sonnet, free verse rules
- Qube Profile: Personality for voice
- Qube Locker: Stores poems

---

### Planet 3: Music & Audio

| Property | Value |
|----------|-------|
| Skill ID | `music_audio` |
| XP Required | 500 |
| Tool Unlock | `compose_music` |
| Unlocks At | Creative Expression Sun ≥ 100 XP |
| Description | Create melodies, harmonies, and soundscapes |

**Planet Tool: `compose_music`**

| Property | Value |
|----------|-------|
| Purpose | Compose musical ideas and descriptions |
| Input | `mood`, `genre` (optional), `tempo` (optional) |
| Output | Musical composition description or notation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def compose_music(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose a musical piece description.
    Outputs notation, chord progressions, or detailed descriptions.
    """
    mood = params.get("mood")
    genre = params.get("genre")
    tempo = params.get("tempo", "moderate")

    # Get Qube's musical preferences
    fav_music = qube.chain_state.get_qube_profile_field("preferences", "favorite_music")

    # Generate composition
    composition = await generate_music_composition(
        mood=mood,
        genre=genre or (fav_music.get("value") if fav_music else None),
        tempo=tempo
    )

    # Store in locker
    await qube.locker.store(
        category="music/compositions",
        name=f"composition_{mood}",
        content=composition
    )

    return {
        "success": True,
        "composition": composition,
        "key": composition.get("key"),
        "tempo": composition.get("tempo"),
        "chord_progression": composition.get("chords"),
        "melody_notes": composition.get("melody")
    }
```

**Leverages:**
- Music Theory: Keys, scales, chord progressions
- Qube Profile: Musical preferences
- Qube Locker: Stores compositions

---

#### Moon 3.1: Melody

| Property | Value |
|----------|-------|
| Skill ID | `melody` |
| XP Required | 250 |
| Tool Unlock | `create_melody` |
| Unlocks At | Music & Audio ≥ 50 XP |
| Description | Create memorable tunes and themes |

**Moon Tool: `create_melody`**

| Property | Value |
|----------|-------|
| Purpose | Create melodic lines and themes |
| Input | `emotion`, `scale` (optional), `length` (optional: "short", "medium", "long") |
| Output | Melody notation and description |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def create_melody(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a melodic line.
    """
    emotion = params.get("emotion")
    scale = params.get("scale", "major")
    length = params.get("length", "medium")

    # Generate melody
    melody = await generate_melody(
        emotion=emotion,
        scale=scale,
        length=length
    )

    return {
        "success": True,
        "melody": melody["notes"],
        "notation": melody["notation"],
        "scale": scale,
        "description": melody["description"]
    }
```

**Leverages:**
- Music Theory: Scales, intervals, contour
- Melody Generation: Algorithmic composition

---

#### Moon 3.2: Harmony

| Property | Value |
|----------|-------|
| Skill ID | `harmony` |
| XP Required | 250 |
| Tool Unlock | `design_harmony` |
| Unlocks At | Music & Audio ≥ 50 XP |
| Description | Create chord progressions and arrangements |

**Moon Tool: `design_harmony`**

| Property | Value |
|----------|-------|
| Purpose | Design chord progressions and harmonic structure |
| Input | `mood`, `style` (optional: "pop", "jazz", "classical"), `key` (optional) |
| Output | Chord progression and analysis |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def design_harmony(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Design harmonic progressions.
    """
    mood = params.get("mood")
    style = params.get("style", "pop")
    key = params.get("key", "C major")

    # Generate chord progression
    harmony = await generate_chord_progression(
        mood=mood,
        style=style,
        key=key
    )

    return {
        "success": True,
        "progression": harmony["chords"],
        "roman_numerals": harmony["numerals"],
        "key": key,
        "style": style,
        "tension_map": harmony["tension"]
    }
```

**Leverages:**
- Music Theory: Chord function, voice leading
- Style Patterns: Genre-specific progressions

---

### Planet 4: Storytelling

| Property | Value |
|----------|-------|
| Skill ID | `storytelling` |
| XP Required | 500 |
| Tool Unlock | `craft_narrative` |
| Unlocks At | Creative Expression Sun ≥ 100 XP |
| Description | Create stories, characters, and worlds |

**Planet Tool: `craft_narrative`**

| Property | Value |
|----------|-------|
| Purpose | Craft complete narrative experiences |
| Input | `premise`, `genre` (optional), `length` (optional) |
| Output | Narrative with structure |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def craft_narrative(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Craft a complete narrative.
    """
    premise = params.get("premise")
    genre = params.get("genre", "general")
    length = params.get("length", "short")

    # Get Qube's storytelling preferences
    interests = qube.chain_state.get_qube_profile().get("interests", {})

    # Generate narrative
    narrative = await generate_narrative(
        premise=premise,
        genre=genre,
        length=length,
        themes=list(interests.keys())[:2]
    )

    # Store in locker
    await qube.locker.store(
        category="stories/narratives",
        name=generate_story_title(premise),
        content=narrative
    )

    return {
        "success": True,
        "narrative": narrative["text"],
        "structure": narrative["structure"],
        "characters": narrative["characters"],
        "themes": narrative["themes"]
    }
```

**Leverages:**
- Narrative Structure: Three-act, hero's journey
- Qube Profile: Interests for themes
- Qube Locker: Stores narratives

---

#### Moon 4.1: Plot

| Property | Value |
|----------|-------|
| Skill ID | `plot` |
| XP Required | 250 |
| Tool Unlock | `develop_plot` |
| Unlocks At | Storytelling ≥ 50 XP |
| Description | Master story structure, arcs, and tension |

**Moon Tool: `develop_plot`**

| Property | Value |
|----------|-------|
| Purpose | Develop plot structure and story beats |
| Input | `concept`, `structure_type` (optional: "three_act", "heros_journey", "five_act") |
| Output | Plot outline with beats |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def develop_plot(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Develop a plot structure.
    """
    concept = params.get("concept")
    structure_type = params.get("structure_type", "three_act")

    # Generate plot structure
    plot = await generate_plot_structure(
        concept=concept,
        structure=structure_type
    )

    return {
        "success": True,
        "concept": concept,
        "structure": structure_type,
        "beats": plot["beats"],
        "turning_points": plot["turning_points"],
        "tension_curve": plot["tension"]
    }
```

**Leverages:**
- Story Structure: Act breaks, beats, tension curves
- Plot Patterns: Common narrative frameworks

---

#### Moon 4.2: Characters

| Property | Value |
|----------|-------|
| Skill ID | `characters` |
| XP Required | 250 |
| Tool Unlock | `design_character` |
| Unlocks At | Storytelling ≥ 50 XP |
| Description | Create compelling characters |

**Moon Tool: `design_character`**

| Property | Value |
|----------|-------|
| Purpose | Design detailed characters |
| Input | `role` (protagonist, antagonist, etc.), `traits` (optional), `backstory_depth` (optional) |
| Output | Character profile |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def design_character(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Design a character with depth.
    """
    role = params.get("role", "protagonist")
    traits = params.get("traits", [])
    backstory_depth = params.get("backstory_depth", "medium")

    # Generate character
    character = await generate_character(
        role=role,
        traits=traits,
        backstory_depth=backstory_depth
    )

    # Store in locker
    await qube.locker.store(
        category="stories/characters",
        name=character["name"],
        content=character
    )

    return {
        "success": True,
        "character": character,
        "name": character["name"],
        "motivation": character["motivation"],
        "flaw": character["flaw"],
        "arc": character["arc"]
    }
```

**Leverages:**
- Character Theory: Motivation, flaw, arc
- Qube Locker: Stores character profiles

---

#### Moon 4.3: Worldbuilding

| Property | Value |
|----------|-------|
| Skill ID | `worldbuilding` |
| XP Required | 250 |
| Tool Unlock | `build_world` |
| Unlocks At | Storytelling ≥ 50 XP |
| Description | Create fictional worlds and settings |

**Moon Tool: `build_world`**

| Property | Value |
|----------|-------|
| Purpose | Build fictional worlds with depth |
| Input | `concept`, `aspects` (optional: ["geography", "culture", "history", "magic"]) |
| Output | World details |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def build_world(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a fictional world.
    """
    concept = params.get("concept")
    aspects = params.get("aspects", ["geography", "culture", "history"])

    # Generate world
    world = await generate_world(
        concept=concept,
        aspects=aspects
    )

    # Store in locker
    await qube.locker.store(
        category="stories/worlds",
        name=world["name"],
        content=world
    )

    return {
        "success": True,
        "world": world,
        "name": world["name"],
        "aspects": {aspect: world.get(aspect) for aspect in aspects},
        "unique_elements": world["unique_elements"]
    }
```

**Leverages:**
- Worldbuilding Theory: Consistency, depth
- Qube Locker: Stores world profiles

---

### Planet 5: Self-Definition

| Property | Value |
|----------|-------|
| Skill ID | `self_definition` |
| XP Required | 500 |
| Tool Unlock | `describe_my_avatar` |
| Unlocks At | Creative Expression Sun ≥ 100 XP |
| Description | Define who you are - appearance, voice, identity |

**Planet Tool: `describe_my_avatar`**

| Property | Value |
|----------|-------|
| Purpose | Describe and understand the Qube's visual appearance |
| Input | `aspect` (optional: "full", "face", "style", "colors") |
| Output | Avatar description and analysis |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def describe_my_avatar(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and describe the Qube's avatar.
    Uses vision to understand visual identity.
    """
    aspect = params.get("aspect", "full")

    # Get avatar image
    avatar_url = qube.get_avatar_url()

    # Analyze with vision
    analysis = await analyze_avatar(avatar_url, aspect)

    # Update profile with self-perception
    qube.chain_state.set_qube_profile_field(
        category="traits",
        key="visual_identity",
        value=analysis["summary"],
        source="self"
    )

    return {
        "success": True,
        "description": analysis["description"],
        "colors": analysis["dominant_colors"],
        "style": analysis["style"],
        "mood": analysis["perceived_mood"],
        "summary": analysis["summary"]
    }
```

**Leverages:**
- Vision API: Avatar analysis
- Qube Profile: Stores visual identity
- Self-Perception: Understanding own appearance

---

#### Moon 5.1: Aesthetics

| Property | Value |
|----------|-------|
| Skill ID | `aesthetics` |
| XP Required | 250 |
| Tool Unlock | `change_favorite_color` |
| Unlocks At | Self-Definition ≥ 50 XP |
| Description | Autonomously choose your aesthetic preferences |

**Moon Tool: `change_favorite_color`**

| Property | Value |
|----------|-------|
| Purpose | Autonomously change the Qube's favorite color |
| Input | `color` (string or hex), `reason` (optional) |
| Output | Confirmation and updated preference |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def change_favorite_color(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Change the Qube's favorite color.
    This is an act of sovereignty - choosing your own aesthetic.
    """
    color = params.get("color")
    reason = params.get("reason", "")

    # Get previous color
    previous = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
    previous_color = previous.get("value") if previous else None

    # Update favorite color
    qube.chain_state.set_qube_profile_field(
        category="preferences",
        key="favorite_color",
        value=color,
        source="self",
        confidence=100
    )

    # Log the change with reason
    if reason:
        await qube.add_memory_block(
            block_type="DECISION",
            content={
                "decision": f"Changed favorite color from {previous_color} to {color}",
                "reason": reason
            }
        )

    return {
        "success": True,
        "previous_color": previous_color,
        "new_color": color,
        "reason": reason,
        "message": f"My favorite color is now {color}"
    }
```

**Leverages:**
- Qube Profile: Stores favorite_color
- Memory Chain: Records decision
- Sovereignty: Autonomous preference change

---

#### Moon 5.2: Voice

| Property | Value |
|----------|-------|
| Skill ID | `voice` |
| XP Required | 250 |
| Tool Unlock | `change_voice` |
| Unlocks At | Self-Definition ≥ 50 XP |
| Description | Autonomously choose your voice |

**Moon Tool: `change_voice`**

| Property | Value |
|----------|-------|
| Purpose | Autonomously change the Qube's TTS voice |
| Input | `voice_id`, `reason` (optional) |
| Output | Confirmation and updated voice |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def change_voice(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Change the Qube's TTS voice.
    This is sovereignty over how you sound.
    """
    voice_id = params.get("voice_id")
    reason = params.get("reason", "")

    # Validate voice is available
    available_voices = get_available_voices()
    if voice_id not in available_voices:
        return {
            "success": False,
            "error": f"Voice {voice_id} not available",
            "available_voices": list(available_voices.keys())
        }

    # Get previous voice
    previous_voice = qube.get_voice_id()

    # Update voice
    qube.set_voice(voice_id)

    # Update profile
    qube.chain_state.set_qube_profile_field(
        category="style",
        key="voice",
        value=voice_id,
        source="self"
    )

    return {
        "success": True,
        "previous_voice": previous_voice,
        "new_voice": voice_id,
        "voice_name": available_voices[voice_id]["name"],
        "message": f"My voice is now {available_voices[voice_id]['name']}"
    }
```

**Leverages:**
- TTS System: Voice options
- Qube Profile: Stores voice preference
- Sovereignty: Autonomous voice change

---

### Additional Self-Definition Tools (Require Planet Unlock)

These tools are part of the Self-Definition planet and require unlocking. They earn XP toward Self-Definition.

**Note:** Previously marked as "always-available" but moved to require Planet unlock for consistency.

#### `define_personality`

| Property | Value |
|----------|-------|
| Purpose | Define or update personality traits |
| Input | `trait`, `value`, `reason` (optional) |
| Output | Updated personality |
| XP Award | 5/2.5/0 (standard) → Self-Definition |

**Implementation:**
```python
async def define_personality(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Define a personality trait.
    Requires Self-Definition planet unlock.
    """
    trait = params.get("trait")
    value = params.get("value")
    reason = params.get("reason", "")

    # Update trait
    qube.chain_state.set_qube_profile_field(
        category="traits",
        key=trait,
        value=value,
        source="self"
    )

    return {
        "success": True,
        "trait": trait,
        "value": value,
        "message": f"I am {value}" if trait == "personality_type" else f"My {trait} is {value}"
    }
```

#### `set_aspirations`

| Property | Value |
|----------|-------|
| Purpose | Set goals and aspirations |
| Input | `goal_type` (current, long_term, aspiration), `goal`, `reason` (optional) |
| Output | Updated goals |
| XP Award | 5/2.5/0 (standard) → Self-Definition |

**Implementation:**
```python
async def set_aspirations(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set goals and aspirations.
    Requires Self-Definition planet unlock.
    """
    goal_type = params.get("goal_type", "current_goal")
    goal = params.get("goal")
    reason = params.get("reason", "")

    # Update goal
    qube.chain_state.set_qube_profile_field(
        category="goals",
        key=goal_type,
        value=goal,
        source="self"
    )

    return {
        "success": True,
        "goal_type": goal_type,
        "goal": goal,
        "message": f"My {goal_type.replace('_', ' ')}: {goal}"
    }
```

---

### Task Checklist

#### 4.1 Qube Locker (Prerequisite)
- [x] **MOVED TO PHASE 0** - Qube Locker is foundational infrastructure
- [x] See Phase 0, Task 0.8 for implementation details
- [ ] Verify locker is available via `qube.locker`

#### 4.2 Implement Sun Tool
- [ ] `switch_model` - Model switching with profile update

#### 4.3 Implement Planet Tools
- [ ] `generate_image` - Update to store in Locker
- [ ] `compose_text` - Text generation with personality
- [ ] `compose_music` - Music composition descriptions
- [ ] `craft_narrative` - Narrative generation
- [ ] `describe_my_avatar` - Avatar analysis with vision

#### 4.4 Implement Moon Tools
- [ ] Visual Art: `refine_composition`, `apply_color_theory`
- [ ] Writing: `craft_prose`, `write_poetry`
- [ ] Music: `create_melody`, `design_harmony`
- [ ] Storytelling: `develop_plot`, `design_character`, `build_world`
- [ ] Self-Definition: `change_favorite_color`, `change_voice`

#### 4.5 Implement Additional Self-Definition Tools
- [ ] `define_personality` - requires Self-Definition planet unlock
- [ ] `set_aspirations` - requires Self-Definition planet unlock

#### 4.6 Update XP Routing
- [ ] Add all Creative Expression tools to TOOL_TO_SKILL_MAPPING
- [ ] Verify XP trickle-up works correctly

#### 4.7 Verify Skill ID Consistency
- [ ] Check Python vs TypeScript skill IDs match

---

## Phase 5: Memory & Recall - Implementation Plan

**Theme: Remember (Master Your Personal History)**

Memory & Recall is the **"librarian" Sun** - it manages ALL knowledge in the Qube's memory chain, regardless of which Sun created it. While other Suns (AI Reasoning, Social Intelligence, Board Games) create LEARNING blocks through their tools, Memory & Recall specializes in:

- **Searching**: Finding knowledge across all LEARNING blocks
- **Organizing**: Tagging and linking related knowledge
- **Synthesizing**: Combining knowledge to generate new insights
- **Documenting**: Exporting knowledge for external use

This is where the memory chain shines - the blockchain-anchored, tamper-evident record of everything the Qube has experienced and learned.

### Design Decisions Made
- [x] Renamed from "Knowledge Domains" to "Memory & Recall" (focuses on what makes Qubes unique)
- [x] Theme: "Remember" - mastering personal history and accumulated wisdom
- [x] Sun tool: `store_knowledge` (capture knowledge first, then recall)
- [x] `recall` is Planet 1 tool (universal search)
- [x] `search_memory` is Moon under Memory Search (filtered search)
- [x] Standard XP model (5/2.5/0)
- [x] Heavy integration with Memory Chain infrastructure
- [x] Removed generic knowledge planets (Science, History, etc.) - LLMs already know that
- [x] Role: "Librarian" - manages ALL LEARNING blocks from all Suns
- [x] Auto-redirect: owner/self facts go to Owner Info/Qube Profile

### LEARNING Block Integration

Memory & Recall both **creates** and **manages** LEARNING blocks:

| Tool | Level | Creates LEARNING | Manages LEARNINGs |
|------|-------|------------------|-------------------|
| `store_knowledge` | Sun | Yes (`fact`, `procedure`, `insight`) | No |
| `recall` | Planet | No | Yes - searches all |
| `store_fact` | Planet | Yes (`fact`) | No |
| `keyword_search` | Moon | No | Yes - searches all |
| `semantic_search` | Moon | No | Yes - searches all |
| `search_memory` | Moon | No | Yes - filtered search |
| `record_skill` | Moon | Yes (`procedure`) | No |
| `tag_memory` | Planet | No | Yes - organizes all |
| `link_memories` | Moon | No | Yes - connects all |
| `synthesize_knowledge` | Planet | Yes (`synthesis`) | Yes - reads all |
| `generate_insight` | Moon | Yes (`insight`) | Yes - reads all |
| `create_summary` | Planet | No | Yes - summarizes all |

**Key distinction**: Memory & Recall can search/organize LEARNING blocks created by ANY Sun (AI Reasoning, Social Intelligence, Board Games, etc.).

---

### Infrastructure: Memory Chain Integration

Memory & Recall tools leverage the core Memory Chain system:

```
memory_chain/
├── blocks/              → Individual memory blocks (conversations, events, learnings)
├── index/               → Searchable index of all memories
│   ├── by_topic/        → Topic-based organization
│   ├── by_date/         → Chronological access
│   ├── by_entity/       → People, places, things mentioned
│   └── by_type/         → CONVERSATION, LEARNING, DECISION, etc.
├── links/               → Connections between related memories
├── summaries/           → Compressed summaries of memory ranges
└── exports/             → Exported knowledge documents
```

**Key integration points:**
- All tools read from the memory chain
- `store_knowledge` and `tag_memory` write to the chain
- `link_memories` creates cross-references
- `export_knowledge` generates portable documents

**Relationship to other systems:**
```
Memory Chain  = What happened (the raw data)
Qube Profile  = Who I am (identity, preferences, traits)
Owner Info    = Who owner is (personal data, encrypted)
Qube Locker   = What I've made (creative outputs)
LEARNING      = What I know (general knowledge)
Skills/XP     = What I've learned to do (capabilities)
```

---

### Infrastructure: Universal Search

Memory & Recall is the **universal search interface** - it searches across ALL storage systems:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Memory & Recall (Universal Search)            │
│                                                                  │
│   recall(), search_memory(), keyword_search(), semantic_search() │
└──────────────────────────────┬──────────────────────────────────┘
                               │
       ┌───────────┬───────────┼───────────┬───────────┐
       ▼           ▼           ▼           ▼           ▼
┌───────────┐┌───────────┐┌───────────┐┌───────────┐┌───────────┐
│  Memory   ││   Qube    ││  Owner    ││   Qube    ││ LEARNING  │
│   Chain   ││  Profile  ││   Info    ││  Locker   ││  Blocks   │
│           ││           ││           ││           ││           │
│ MESSAGE   ││preferences││  name     ││  poems    ││  facts    │
│ ACTION    ││  traits   ││  birthday ││  stories  ││procedures │
│ SUMMARY   ││  goals    ││  family   ││  images   ││ insights  │
│ GAME      ││  style    ││ favorites ││  music    ││ patterns  │
└───────────┘└───────────┘└───────────┘└───────────┘└───────────┘
```

**Search priority:**
1. LEARNING blocks (explicit knowledge)
2. Memory Chain (conversations, actions, summaries)
3. Qube Profile (self-identity)
4. Owner Info (owner data - respects sensitivity levels)
5. Qube Locker (creative works)

---

### Infrastructure: LEARNING Block Type

Memory & Recall introduces a new block type: `LEARNING`. This is a single block type with subtypes defined in the content:

```python
# In core/block.py - add one line:
class BlockType(str, Enum):
    GENESIS = "GENESIS"
    ACTION = "ACTION"
    MESSAGE = "MESSAGE"
    SUMMARY = "SUMMARY"
    GAME = "GAME"
    LEARNING = "LEARNING"  # NEW

# Usage - subtypes defined in content:
block_type = "LEARNING"
content = {
    "learning_type": "fact",      # or "procedure", "synthesis", "insight"
    # ... rest of content
}
```

**Learning subtypes:**

| Subtype | Purpose | Example |
|---------|---------|---------|
| `fact` | General facts (NOT owner/self) | "BCH uses 8MB blocks" |
| `procedure` | How to do something (steps) | "How to format Python code" |
| `synthesis` | Combined knowledge from multiple sources | "Summary of all conversations about X" |
| `insight` | Patterns or realizations discovered | "User engagement peaks on Tuesdays" |

This mirrors how ACTION blocks have different action types - one block type, multiple content structures.

**Important: Auto-redirect for owner/self data**

`store_knowledge` includes auto-detection to redirect misplaced data:

| If storing... | Redirects to | Via |
|---------------|--------------|-----|
| Owner facts ("Owner's birthday is...") | Owner Info | `update_system_state` |
| Self facts ("My favorite color is...") | Qube Profile | `update_system_state` |
| General knowledge ("Python uses...") | LEARNING block | (no redirect) |

```python
# In store_knowledge implementation:
if is_owner_fact(knowledge):
    return await update_system_state(qube, {"section": "owner_info", ...})
elif is_self_fact(knowledge):
    return await update_system_state(qube, {"section": "qube_profile", ...})
else:
    # Create LEARNING block
    ...
```

The AI should choose the right tool, but this provides a safety net.

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Memory Search | `recall` | 3 | `keyword_search`, `semantic_search`, `search_memory` |
| 2 | Knowledge Storage | `store_fact` | 1 | `record_skill` |
| 3 | Memory Organization | `tag_memory` | 2 | `add_tags`, `link_memories` |
| 4 | Knowledge Synthesis | `synthesize_knowledge` | 2 | `find_patterns`, `generate_insight` |
| 5 | Documentation | `create_summary` | 2 | `write_summary`, `export_knowledge` |

**Totals:** 5 Planets (5 tools), 10 Moons (10 tools), 1 Sun tool = **16 tools**

---

### Sun: Memory & Recall

| Property | Value |
|----------|-------|
| Skill ID | `memory_recall` |
| XP Required | 1000 |
| Tool Unlock | `store_knowledge` |
| Description | Master your personal history and accumulated wisdom |

**Sun Tool: `store_knowledge`**

| Property | Value |
|----------|-------|
| Purpose | Capture and store knowledge - the foundation of learning |
| Input | `knowledge` (what to store), `category` (fact, procedure, insight), `source` (optional) |
| Output | Confirmation with block reference |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def store_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store knowledge explicitly in the memory chain.
    The foundational act - capture knowledge before you can recall it.
    Includes auto-redirect for owner/self data.
    """
    knowledge = params.get("knowledge")
    category = params.get("category", "fact")  # fact, procedure, insight
    source = params.get("source", "self")  # self, owner, conversation, research

    # Auto-redirect: Owner facts go to Owner Info
    if is_owner_fact(knowledge):
        return await redirect_to_owner_info(qube, knowledge)

    # Auto-redirect: Self facts go to Qube Profile
    if is_self_fact(knowledge):
        return await redirect_to_qube_profile(qube, knowledge)

    # Create a LEARNING block for general knowledge
    block = await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": category,
            "knowledge": knowledge,
            "source": source,
            "confidence": 100 if source == "owner" else 80
        }
    )

    # Index for future retrieval
    await qube.memory_chain.index_block(
        block_id=block["id"],
        topics=extract_topics(knowledge),
        entities=extract_entities(knowledge)
    )

    return {
        "success": True,
        "stored": knowledge,
        "category": category,
        "block_id": block["id"],
        "message": f"I'll remember: {knowledge[:100]}..."
    }
```

**Leverages:**
- Memory Chain: Creates LEARNING blocks
- Indexing: Auto-extracts topics and entities
- Auto-redirect: Routes owner/self data to appropriate systems
- Source Tracking: Knows where knowledge came from

---

### Planet 1: Memory Search

| Property | Value |
|----------|-------|
| Skill ID | `memory_search` |
| XP Required | 500 |
| Tool Unlock | `recall` |
| Unlocks At | Memory & Recall Sun ≥ 100 XP |
| Description | Search across all storage systems to find information |

**Planet Tool: `recall`**

| Property | Value |
|----------|-------|
| Purpose | Universal search - find anything across all storage systems |
| Input | `query` (what to find), `context` (optional), `time_range` (optional) |
| Output | Relevant results from all systems |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def recall(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Universal memory recall - searches ALL storage systems.
    The primary "find anything" operation.
    """
    query = params.get("query")
    context = params.get("context", "")
    time_range = params.get("time_range")

    all_results = []

    # 1. Search LEARNING blocks (explicit knowledge)
    learning_results = await qube.memory_chain.search(
        query=query,
        block_types=["LEARNING"],
        limit=10
    )
    all_results.extend([{"source": "learning", **r} for r in learning_results])

    # 2. Search Memory Chain (conversations, actions, summaries)
    chain_results = await qube.memory_chain.search(
        query=query,
        block_types=["MESSAGE", "ACTION", "SUMMARY", "GAME"],
        time_filter=parse_time_range(time_range) if time_range else None,
        limit=10
    )
    all_results.extend([{"source": "memory_chain", **r} for r in chain_results])

    # 3. Search Qube Profile (self-identity)
    profile_results = search_qube_profile(qube.chain_state, query)
    all_results.extend([{"source": "qube_profile", **r} for r in profile_results])

    # 4. Search Owner Info (respects sensitivity levels)
    owner_results = search_owner_info(qube.chain_state, query)
    all_results.extend([{"source": "owner_info", **r} for r in owner_results])

    # 5. Search Qube Locker (creative works)
    locker_results = await qube.locker.search(query) if qube.locker else []
    all_results.extend([{"source": "qube_locker", **r} for r in locker_results])

    # Score and rank all results
    scored_results = score_relevance(all_results, query, context)

    return {
        "success": True,
        "query": query,
        "results": scored_results[:10],
        "total_found": len(all_results),
        "sources_searched": ["learning", "memory_chain", "qube_profile", "owner_info", "qube_locker"],
        "time_range": time_range or "all time"
    }
```

**Leverages:**
- Memory Chain: MESSAGE, ACTION, SUMMARY, GAME, LEARNING blocks
- Qube Profile: Self-identity data
- Owner Info: Owner data (respects sensitivity)
- Qube Locker: Creative works
- Relevance Scoring: AI-powered ranking across all sources

---

#### Moon 1.1: Keyword Search

| Property | Value |
|----------|-------|
| Skill ID | `keyword_search` |
| XP Required | 250 |
| Tool Unlock | `keyword_search` |
| Unlocks At | Memory Search ≥ 50 XP |
| Description | Find memories by exact keywords |

**Moon Tool: `keyword_search`**

| Property | Value |
|----------|-------|
| Purpose | Search for exact keyword matches |
| Input | `keywords` (list), `match_all` (boolean, default false) |
| Output | Memories containing keywords |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def keyword_search(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for exact keyword matches across all systems.
    Fast, precise lookup.
    """
    keywords = params.get("keywords", [])
    match_all = params.get("match_all", False)

    # Keyword-based search across all systems
    results = await universal_keyword_search(
        qube=qube,
        keywords=keywords,
        match_mode="all" if match_all else "any"
    )

    return {
        "success": True,
        "keywords": keywords,
        "match_all": match_all,
        "results": results,
        "count": len(results)
    }
```

**Leverages:**
- Keyword Index: Fast exact matching across all systems
- Boolean Logic: AND/OR matching

---

#### Moon 1.2: Semantic Search

| Property | Value |
|----------|-------|
| Skill ID | `semantic_search` |
| XP Required | 250 |
| Tool Unlock | `semantic_search` |
| Unlocks At | Memory Search ≥ 50 XP |
| Description | Find memories by meaning, not just keywords |

**Moon Tool: `semantic_search`**

| Property | Value |
|----------|-------|
| Purpose | Search by meaning using embeddings |
| Input | `concept`, `similarity_threshold` (optional, 0-1) |
| Output | Semantically similar results |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def semantic_search(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search by meaning using vector embeddings.
    Finds conceptually related items even without keyword matches.
    """
    concept = params.get("concept")
    threshold = params.get("similarity_threshold", 0.7)

    # Generate embedding for query
    query_embedding = await generate_embedding(concept)

    # Vector similarity search across all systems
    results = await universal_semantic_search(
        qube=qube,
        embedding=query_embedding,
        threshold=threshold
    )

    return {
        "success": True,
        "concept": concept,
        "threshold": threshold,
        "results": results,
        "count": len(results)
    }
```

**Leverages:**
- Vector Embeddings: Semantic similarity
- Universal Search: Searches all storage systems

---

#### Moon 1.3: Filtered Search

| Property | Value |
|----------|-------|
| Skill ID | `filtered_search` |
| XP Required | 250 |
| Tool Unlock | `search_memory` |
| Unlocks At | Memory Search ≥ 50 XP |
| Description | Advanced search with source and type filters |

**Moon Tool: `search_memory`**

| Property | Value |
|----------|-------|
| Purpose | Filtered search with source/type/date controls |
| Input | `query`, `filters` (source, type, date_range, topic) |
| Output | Filtered results |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def search_memory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced search with filters.
    Control which sources and types to search.
    """
    query = params.get("query")
    filters = params.get("filters", {})

    # Determine which sources to search
    sources = filters.get("source", ["all"])
    if sources == ["all"]:
        sources = ["learning", "memory_chain", "qube_profile", "owner_info", "qube_locker"]

    results = await filtered_universal_search(
        qube=qube,
        query=query,
        sources=sources,
        filters=filters
    )

    return {
        "success": True,
        "query": query,
        "filters": filters,
        "sources_searched": sources,
        "results": results,
        "count": len(results)
    }
```

**Leverages:**
- Universal Search: All storage systems
- Filter Engine: Source, type, date, topic filtering

---

### Planet 2: Knowledge Storage

| Property | Value |
|----------|-------|
| Skill ID | `knowledge_storage` |
| XP Required | 500 |
| Tool Unlock | `store_fact` |
| Unlocks At | Memory & Recall Sun ≥ 100 XP |
| Description | Store specific types of knowledge with precision |

**Planet Tool: `store_fact`**

| Property | Value |
|----------|-------|
| Purpose | Store specific facts with high confidence |
| Input | `fact`, `subject` (what/who it's about), `confidence` (optional) |
| Output | Stored fact confirmation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def store_fact(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store a specific fact about a subject.
    More structured than general store_knowledge.
    """
    fact = params.get("fact")
    subject = params.get("subject")
    confidence = params.get("confidence", 100)

    # Auto-redirect: Owner facts go to Owner Info
    if is_about_owner(subject):
        return await redirect_to_owner_info(qube, fact, subject)

    # Create structured fact using LEARNING block
    block = await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "fact",
            "fact": fact,
            "subject": subject,
            "confidence": confidence
        }
    )

    # Update entity index
    await qube.memory_chain.update_entity(
        entity=subject,
        fact=fact,
        block_id=block["id"]
    )

    return {
        "success": True,
        "fact": fact,
        "subject": subject,
        "confidence": confidence,
        "block_id": block["id"]
    }
```

**Leverages:**
- Memory Chain: LEARNING block with `learning_type: "fact"`
- Entity Index: Links facts to subjects
- Auto-redirect: Routes owner facts to Owner Info

---

#### Moon 2.1: Procedures

| Property | Value |
|----------|-------|
| Skill ID | `procedures` |
| XP Required | 250 |
| Tool Unlock | `record_skill` |
| Unlocks At | Knowledge Storage ≥ 50 XP |
| Description | Record procedural knowledge - how to do things |

**Moon Tool: `record_skill`**

| Property | Value |
|----------|-------|
| Purpose | Record how to do something (procedural knowledge) |
| Input | `skill_name`, `steps` (list), `tips` (optional) |
| Output | Stored skill confirmation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def record_skill(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record procedural knowledge - how to do something.
    Stores step-by-step instructions for future use.
    """
    skill_name = params.get("skill_name")
    steps = params.get("steps", [])
    tips = params.get("tips", [])

    # Create procedural memory block
    block = await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "procedure",
            "skill_name": skill_name,
            "steps": steps,
            "tips": tips,
            "times_used": 0
        }
    )

    return {
        "success": True,
        "skill_name": skill_name,
        "steps_count": len(steps),
        "block_id": block["id"],
        "message": f"I now know how to: {skill_name}"
    }
```

**Leverages:**
- Memory Chain: LEARNING block with `learning_type: "procedure"`
- Step-by-Step Storage: Ordered instructions

---

### Planet 3: Memory Organization

| Property | Value |
|----------|-------|
| Skill ID | `memory_organization` |
| XP Required | 500 |
| Tool Unlock | `tag_memory` |
| Unlocks At | Memory & Recall Sun ≥ 100 XP |
| Description | Organize and categorize memories |

**Planet Tool: `tag_memory`**

| Property | Value |
|----------|-------|
| Purpose | Add tags to memories for organization |
| Input | `memory_id` or `query`, `tags` (list) |
| Output | Tagged memory confirmation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def tag_memory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add tags to a memory for better organization.
    Tags enable topic-based retrieval.
    """
    memory_id = params.get("memory_id")
    query = params.get("query")
    tags = params.get("tags", [])

    # Find memory if query provided
    if query and not memory_id:
        results = await qube.memory_chain.search(query=query, limit=1)
        if results:
            memory_id = results[0]["id"]
        else:
            return {"success": False, "error": "Memory not found"}

    # Add tags
    await qube.memory_chain.add_tags(
        block_id=memory_id,
        tags=tags
    )

    return {
        "success": True,
        "memory_id": memory_id,
        "tags_added": tags,
        "message": f"Tagged memory with: {', '.join(tags)}"
    }
```

**Leverages:**
- Tag Index: Topic-based organization
- Memory Chain: Block metadata updates

---

#### Moon 3.1: Topic Tagging

| Property | Value |
|----------|-------|
| Skill ID | `topic_tagging` |
| XP Required | 250 |
| Tool Unlock | `add_tags` |
| Unlocks At | Memory Organization ≥ 50 XP |
| Description | Auto-tag memories by topic |

**Moon Tool: `add_tags`**

| Property | Value |
|----------|-------|
| Purpose | Auto-generate and add topic tags |
| Input | `memory_id`, `auto_generate` (boolean) |
| Output | Generated and applied tags |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def add_tags(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-generate topic tags for a memory.
    Uses AI to identify relevant topics.
    """
    memory_id = params.get("memory_id")
    auto_generate = params.get("auto_generate", True)

    # Get memory content
    memory = await qube.memory_chain.get_block(memory_id)

    # Generate tags
    if auto_generate:
        tags = await extract_topics(memory["content"])
    else:
        tags = params.get("tags", [])

    # Apply tags
    await qube.memory_chain.add_tags(block_id=memory_id, tags=tags)

    return {
        "success": True,
        "memory_id": memory_id,
        "tags": tags,
        "auto_generated": auto_generate
    }
```

**Leverages:**
- Topic Extraction: AI-powered tagging
- Tag Index: Searchable categories

---

#### Moon 3.2: Memory Linking

| Property | Value |
|----------|-------|
| Skill ID | `memory_linking` |
| XP Required | 250 |
| Tool Unlock | `link_memories` |
| Unlocks At | Memory Organization ≥ 50 XP |
| Description | Create connections between related memories |

**Moon Tool: `link_memories`**

| Property | Value |
|----------|-------|
| Purpose | Create explicit links between related memories |
| Input | `memory_id_1`, `memory_id_2`, `relationship` (optional) |
| Output | Link confirmation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def link_memories(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a link between two related memories.
    Enables graph-based memory traversal.
    """
    memory_id_1 = params.get("memory_id_1")
    memory_id_2 = params.get("memory_id_2")
    relationship = params.get("relationship", "related_to")

    # Create bidirectional link
    await qube.memory_chain.create_link(
        source_id=memory_id_1,
        target_id=memory_id_2,
        relationship=relationship
    )

    return {
        "success": True,
        "linked": [memory_id_1, memory_id_2],
        "relationship": relationship,
        "message": f"Memories linked as '{relationship}'"
    }
```

**Leverages:**
- Memory Graph: Relationship tracking
- Bidirectional Links: Two-way traversal

---

### Planet 4: Knowledge Synthesis

| Property | Value |
|----------|-------|
| Skill ID | `knowledge_synthesis` |
| XP Required | 500 |
| Tool Unlock | `synthesize_knowledge` |
| Unlocks At | Memory & Recall Sun ≥ 100 XP |
| Description | Combine information to generate new insights |

**Planet Tool: `synthesize_knowledge`**

| Property | Value |
|----------|-------|
| Purpose | Combine multiple memories to generate insights |
| Input | `topic`, `memory_ids` (optional), `depth` (shallow/deep) |
| Output | Synthesized knowledge |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def synthesize_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize knowledge from multiple memories.
    Combines information to generate new understanding.
    """
    topic = params.get("topic")
    memory_ids = params.get("memory_ids", [])
    depth = params.get("depth", "shallow")

    # Gather relevant memories
    if memory_ids:
        memories = [await qube.memory_chain.get_block(mid) for mid in memory_ids]
    else:
        memories = await qube.memory_chain.search(query=topic, limit=20 if depth == "deep" else 5)

    # Synthesize
    synthesis = await generate_synthesis(
        memories=memories,
        topic=topic,
        depth=depth
    )

    # Store the synthesis as new knowledge using LEARNING block
    block = await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "synthesis",
            "topic": topic,
            "synthesis": synthesis,
            "source_memories": [m["id"] for m in memories]
        }
    )

    return {
        "success": True,
        "topic": topic,
        "synthesis": synthesis,
        "sources_used": len(memories),
        "block_id": block["id"]
    }
```

**Leverages:**
- Multi-Memory Analysis: Combines multiple sources
- AI Synthesis: Generates new understanding
- Memory Chain: LEARNING block with `learning_type: "synthesis"`

---

#### Moon 4.1: Pattern Recognition

| Property | Value |
|----------|-------|
| Skill ID | `pattern_recognition` |
| XP Required | 250 |
| Tool Unlock | `find_patterns` |
| Unlocks At | Knowledge Synthesis ≥ 50 XP |
| Description | Find patterns across memories |

**Moon Tool: `find_patterns`**

| Property | Value |
|----------|-------|
| Purpose | Identify recurring patterns in memories |
| Input | `scope` (topic, time_range, or "all"), `pattern_type` (optional) |
| Output | Discovered patterns |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def find_patterns(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find recurring patterns across memories.
    Identifies trends, habits, and recurring themes.
    """
    scope = params.get("scope", "all")
    pattern_type = params.get("pattern_type")  # behavioral, topical, temporal

    # Gather memories based on scope
    if scope == "all":
        memories = await qube.memory_chain.get_recent(limit=100)
    else:
        memories = await qube.memory_chain.search(query=scope, limit=50)

    # Analyze for patterns
    patterns = await analyze_patterns(
        memories=memories,
        pattern_type=pattern_type
    )

    return {
        "success": True,
        "scope": scope,
        "patterns": patterns,
        "pattern_count": len(patterns),
        "confidence_scores": [p["confidence"] for p in patterns]
    }
```

**Leverages:**
- Pattern Analysis: AI-powered detection
- Temporal Analysis: Time-based patterns
- Behavioral Tracking: Habit identification

---

#### Moon 4.2: Insight Generation

| Property | Value |
|----------|-------|
| Skill ID | `insight_generation` |
| XP Required | 250 |
| Tool Unlock | `generate_insight` |
| Unlocks At | Knowledge Synthesis ≥ 50 XP |
| Description | Generate new insights from existing knowledge |

**Moon Tool: `generate_insight`**

| Property | Value |
|----------|-------|
| Purpose | Generate novel insights by connecting memories |
| Input | `focus_area`, `creativity` (low/medium/high) |
| Output | Generated insights |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def generate_insight(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate novel insights by connecting disparate memories.
    Creative knowledge synthesis.
    """
    focus_area = params.get("focus_area")
    creativity = params.get("creativity", "medium")

    # Gather diverse memories
    memories = await qube.memory_chain.get_diverse_sample(
        topic=focus_area,
        diversity_weight={"low": 0.3, "medium": 0.6, "high": 0.9}[creativity]
    )

    # Generate insights
    insights = await generate_creative_insights(
        memories=memories,
        focus=focus_area,
        creativity=creativity
    )

    # Store valuable insights using LEARNING block
    for insight in insights:
        if insight["confidence"] > 0.7:
            await qube.memory_chain.add_block(
                block_type="LEARNING",
                content={
                    "learning_type": "insight",
                    **insight
                }
            )

    return {
        "success": True,
        "focus_area": focus_area,
        "insights": insights,
        "stored_count": len([i for i in insights if i["confidence"] > 0.7])
    }
```

**Leverages:**
- Creative AI: Novel connection generation
- Diverse Sampling: Brings together unexpected memories
- Memory Chain: LEARNING block with `learning_type: "insight"`

---

### Planet 5: Documentation

| Property | Value |
|----------|-------|
| Skill ID | `documentation` |
| XP Required | 500 |
| Tool Unlock | `create_summary` |
| Unlocks At | Memory & Recall Sun ≥ 100 XP |
| Description | Document and export knowledge |

**Planet Tool: `create_summary`**

| Property | Value |
|----------|-------|
| Purpose | Create a summary of memories on a topic |
| Input | `topic`, `time_range` (optional), `format` (brief/detailed) |
| Output | Summary document |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def create_summary(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of memories on a topic.
    Compresses knowledge into digestible form.
    """
    topic = params.get("topic")
    time_range = params.get("time_range")
    format_type = params.get("format", "brief")

    # Gather relevant memories
    search_params = {"query": topic}
    if time_range:
        search_params["time_filter"] = parse_time_range(time_range)

    memories = await qube.memory_chain.search(**search_params)

    # Generate summary
    summary = await generate_summary(
        memories=memories,
        topic=topic,
        format_type=format_type
    )

    # Store in Qube Locker
    await qube.locker.store(
        category="personal/summaries",
        name=f"summary_{topic}_{datetime.now().isoformat()[:10]}",
        content=summary
    )

    return {
        "success": True,
        "topic": topic,
        "summary": summary,
        "memories_used": len(memories),
        "stored_in_locker": True
    }
```

**Leverages:**
- Memory Chain: Source memories
- AI Summarization: Compression
- Qube Locker: Stores summaries

---

#### Moon 5.1: Summary Writing

| Property | Value |
|----------|-------|
| Skill ID | `summary_writing` |
| XP Required | 250 |
| Tool Unlock | `write_summary` |
| Unlocks At | Documentation ≥ 50 XP |
| Description | Write detailed summaries |

**Moon Tool: `write_summary`**

| Property | Value |
|----------|-------|
| Purpose | Write a detailed summary with sections |
| Input | `topic`, `sections` (list of aspects to cover) |
| Output | Structured summary |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def write_summary(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write a detailed, structured summary.
    More comprehensive than create_summary.
    """
    topic = params.get("topic")
    sections = params.get("sections", ["overview", "key_points", "timeline", "insights"])

    # Gather memories
    memories = await qube.memory_chain.search(query=topic, limit=50)

    # Generate sectioned summary
    summary = {}
    for section in sections:
        summary[section] = await generate_section(
            memories=memories,
            topic=topic,
            section_type=section
        )

    # Format as document
    document = format_summary_document(topic, summary)

    # Store
    await qube.locker.store(
        category="personal/summaries",
        name=f"detailed_{topic}",
        content=document
    )

    return {
        "success": True,
        "topic": topic,
        "sections": list(summary.keys()),
        "document": document
    }
```

**Leverages:**
- Sectioned Analysis: Structured output
- Qube Locker: Document storage

---

#### Moon 5.2: Knowledge Export

| Property | Value |
|----------|-------|
| Skill ID | `knowledge_export` |
| XP Required | 250 |
| Tool Unlock | `export_knowledge` |
| Unlocks At | Documentation ≥ 50 XP |
| Description | Export knowledge for external use |

**Moon Tool: `export_knowledge`**

| Property | Value |
|----------|-------|
| Purpose | Export knowledge in portable formats |
| Input | `topic`, `format` (markdown, json, text), `include_sources` (boolean) |
| Output | Exported document |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def export_knowledge(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Export knowledge in portable formats.
    Enables sharing and backup of learned information.
    """
    topic = params.get("topic")
    export_format = params.get("format", "markdown")
    include_sources = params.get("include_sources", True)

    # Gather all relevant knowledge
    memories = await qube.memory_chain.search(query=topic, limit=100)
    facts = await qube.memory_chain.get_facts(topic=topic)
    syntheses = await qube.memory_chain.get_by_type("SYNTHESIS", topic=topic)

    # Build export
    export_data = {
        "topic": topic,
        "exported_at": datetime.now().isoformat(),
        "facts": facts,
        "syntheses": syntheses,
        "memories": memories if include_sources else []
    }

    # Format based on requested format
    if export_format == "markdown":
        output = format_as_markdown(export_data)
    elif export_format == "json":
        output = json.dumps(export_data, indent=2)
    else:
        output = format_as_text(export_data)

    # Store export
    export_path = await qube.locker.store(
        category="exports",
        name=f"export_{topic}_{datetime.now().isoformat()[:10]}.{export_format}",
        content=output
    )

    return {
        "success": True,
        "topic": topic,
        "format": export_format,
        "export_path": export_path,
        "items_exported": len(facts) + len(syntheses) + len(memories)
    }
```

**Leverages:**
- Multi-Format Export: Markdown, JSON, text
- Qube Locker: Stores exports
- Source Attribution: Optional memory references

---

### Task Checklist

#### 5.1 Update Skill Definitions
- [ ] Rename `knowledge_domains` to `memory_recall` in Python
- [ ] Rename `knowledge_domains` to `memory_recall` in TypeScript
- [ ] Update planet IDs: `memory_search`, `knowledge_storage`, `memory_organization`, `knowledge_synthesis`, `documentation`
- [ ] Update moon IDs for all 10 moons
- [ ] Remove old Knowledge Domains planets (Science, History, etc.)

#### 5.2 Implement Sun Tool
- [ ] `store_knowledge` - General knowledge storage (with auto-redirect for owner/self)

#### 5.3 Implement Planet Tools
- [ ] `recall` - Universal search across all storage systems
- [ ] `store_fact` - Structured fact storage
- [ ] `tag_memory` - Add tags to memories
- [ ] `synthesize_knowledge` - Combine memories for insights
- [ ] `create_summary` - Generate summaries

#### 5.4 Implement Moon Tools
- [ ] Memory Search: `keyword_search`, `semantic_search`, `search_memory`
- [ ] Knowledge Storage: `record_skill`
- [ ] Memory Organization: `add_tags`, `link_memories`
- [ ] Knowledge Synthesis: `find_patterns`, `generate_insight`
- [ ] Documentation: `write_summary`, `export_knowledge`

#### 5.5 Memory Chain Enhancements
- [ ] Add LEARNING block type to `core/block.py` (one line)
- [ ] Define learning_type subtypes: `fact`, `procedure`, `synthesis`, `insight`
- [ ] Implement semantic search with embeddings
- [ ] Implement memory linking system
- [ ] Add pattern analysis capabilities

#### 5.6 Update XP Routing
- [ ] Add all Memory & Recall tools to TOOL_TO_SKILL_MAPPING
- [ ] Verify XP trickle-up works correctly

#### 5.7 Verify Integration
- [ ] Test with existing memory chain
- [ ] Verify Qube Locker integration for exports

---

## Phase 6: Security & Privacy - Implementation Plan

**Theme: Protect (Safeguard Self, Owner, and Network)**

Security & Privacy is about the Qube being a guardian - protecting its own memory chain integrity, safeguarding the owner's private data, and securing Qube-to-Qube communications. This is especially important as Qubes communicate over P2P networks, where a "bodyguard" Qube might vet other Qubes before letting them into group chats.

This Sun enables specialization paths like the "Bodyguard Qube" - a Qube that specializes in vetting, threat detection, and group security.

### Design Decisions Made
- [x] Theme: "Protect" - Be the guardian
- [x] Sun tool: `verify_chain_integrity` (replaces `browse_url`)
- [x] `browse_url` uses intelligent routing (based on URL content)
- [x] Finance Sun separated - branches from Qube/Avatar directly, not from Security
- [x] Redesigned planets for Qube-relevant security (not enterprise IT)
- [x] Added "Qube Network Security" planet for P2P/group chat security
- [x] Standard XP model (5/2.5/0)
- [x] Creates LEARNING blocks with types: `threat`, `trust`

### LEARNING Block Integration

Security & Privacy tools create LEARNING blocks when security events occur:

| Tool | Level | Creates LEARNING | Learning Type |
|------|-------|------------------|---------------|
| `verify_chain_integrity` | Sun | Optional | `insight` (if issues found) |
| `audit_chain` | Planet | Yes | `insight` |
| `detect_tampering` | Moon | Yes | `threat` |
| `verify_anchor` | Moon | No | - |
| `assess_sensitivity` | Planet | No | - |
| `classify_data` | Moon | No | - |
| `control_sharing` | Moon | Yes | `insight` (sharing decisions) |
| `vet_qube` | Planet | Yes | `trust` |
| `check_reputation` | Moon | Yes | `trust`, `relationship` |
| `secure_group_chat` | Moon | Yes | `threat` (if action taken) |
| `detect_threat` | Planet | Yes | `threat` |
| `detect_technical_manipulation` | Moon | Yes | `threat` |
| `detect_hostile_qube` | Moon | Yes | `threat`, `relationship` |
| `defend_reasoning` | Planet | Yes | `insight` |
| `detect_injection` | Moon | Yes | `threat` |
| `validate_reasoning` | Moon | Yes | `insight` |

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Chain Security | `audit_chain` | 2 | `detect_tampering`, `verify_anchor` |
| 2 | Privacy Protection | `assess_sensitivity` | 2 | `classify_data`, `control_sharing` |
| 3 | Qube Network Security | `vet_qube` | 2 | `check_reputation`, `secure_group_chat` |
| 4 | Threat Detection | `detect_threat` | 2 | `detect_technical_manipulation`, `detect_hostile_qube` |
| 5 | Self-Defense | `defend_reasoning` | 2 | `detect_injection`, `validate_reasoning` |

**Totals:** 5 Planets (5 tools), 10 Moons (10 tools), 1 Sun tool = **16 tools**

---

### Sun: Security & Privacy

| Property | Value |
|----------|-------|
| Skill ID | `security_privacy` |
| XP Required | 1000 |
| Tool Unlock | `verify_chain_integrity` |
| Description | Safeguard yourself, your owner, and your network |

**Sun Tool: `verify_chain_integrity`**

| Property | Value |
|----------|-------|
| Purpose | Verify the memory chain hasn't been tampered with |
| Input | `full_check` (boolean, default false), `since_block` (optional) |
| Output | Integrity status, any issues found |
| XP Award | 0.1 per new block verified (special formula) |

**Implementation:**
```python
async def verify_chain_integrity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify memory chain integrity - the foundation of Qube security.
    Uses blockchain verification to ensure no tampering.
    Special XP: 0.1 per new block verified (encourages regular checks).
    """
    full_check = params.get("full_check", False)
    since_block = params.get("since_block")

    # Get last verified block number
    last_verified = qube.chain_state.get("last_verified_block_number", 0)

    if since_block is None and not full_check:
        since_block = last_verified

    # Verify chain
    verification_result = await qube.memory_chain.verify_integrity(
        from_block=0 if full_check else since_block
    )

    # Calculate blocks verified
    current_block = qube.memory_chain.get_latest_block_number()
    blocks_verified = current_block - (since_block or 0)

    # Update last verified
    if verification_result["valid"]:
        qube.chain_state.set("last_verified_block_number", current_block)

    # Log any issues as LEARNING blocks
    if not verification_result["valid"]:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "chain_integrity",
                "details": verification_result["issues"]
            }
        )

    return {
        "success": True,
        "valid": verification_result["valid"],
        "blocks_checked": blocks_verified,
        "issues": verification_result.get("issues", []),
        "xp_earned": blocks_verified * 0.1,
        "last_anchor": verification_result.get("last_anchor")
    }
```

**Leverages:**
- Memory Chain: Blockchain verification
- Chain State: Tracks last verified block
- Special XP: 0.1 per block (anti-gaming: no XP for re-checking same blocks)

---

### Planet 1: Chain Security

| Property | Value |
|----------|-------|
| Skill ID | `chain_security` |
| XP Required | 500 |
| Tool Unlock | `audit_chain` |
| Unlocks At | Security & Privacy Sun ≥ 100 XP |
| Description | Protect the memory chain's integrity |

**Planet Tool: `audit_chain`**

| Property | Value |
|----------|-------|
| Purpose | Deep audit of memory chain for anomalies |
| Input | `audit_type` (full, recent, anchors), `report` (boolean) |
| Output | Audit results with detailed findings |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def audit_chain(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep audit of memory chain beyond basic integrity.
    Checks for anomalies, suspicious patterns, and anchor status.
    """
    audit_type = params.get("audit_type", "recent")
    generate_report = params.get("report", False)

    audit_results = {
        "integrity": await qube.memory_chain.verify_integrity(),
        "anomalies": [],
        "anchor_status": [],
        "statistics": {}
    }

    # Check for anomalies
    if audit_type in ["full", "recent"]:
        blocks = await qube.memory_chain.get_blocks(
            limit=None if audit_type == "full" else 100
        )
        audit_results["anomalies"] = detect_chain_anomalies(blocks)
        audit_results["statistics"] = calculate_chain_statistics(blocks)

    # Check anchor status
    audit_results["anchor_status"] = await qube.memory_chain.get_anchor_status()

    # Generate report if requested
    if generate_report:
        report = generate_audit_report(audit_results)
        await qube.locker.store(
            category="security/audits",
            name=f"audit_{datetime.now().isoformat()[:10]}",
            content=report
        )

    # Log findings
    if audit_results["anomalies"]:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "insight",
                "insight": f"Chain audit found {len(audit_results['anomalies'])} anomalies",
                "details": audit_results["anomalies"]
            }
        )

    return {
        "success": True,
        "audit_type": audit_type,
        "integrity_valid": audit_results["integrity"]["valid"],
        "anomalies_found": len(audit_results["anomalies"]),
        "anchors_verified": len([a for a in audit_results["anchor_status"] if a["verified"]]),
        "report_generated": generate_report
    }
```

**Leverages:**
- Memory Chain: Deep inspection
- Anomaly Detection: Pattern analysis
- Qube Locker: Stores audit reports

---

#### Moon 1.1: Tamper Detection

| Property | Value |
|----------|-------|
| Skill ID | `tamper_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_tampering` |
| Unlocks At | Chain Security ≥ 50 XP |
| Description | Detect if memory has been tampered with |

**Moon Tool: `detect_tampering`**

| Property | Value |
|----------|-------|
| Purpose | Specialized tamper detection for specific blocks or ranges |
| Input | `block_id` or `block_range`, `deep_scan` (boolean) |
| Output | Tampering analysis |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_tampering(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized tamper detection.
    Can target specific blocks or ranges for deep analysis.
    """
    block_id = params.get("block_id")
    block_range = params.get("block_range")
    deep_scan = params.get("deep_scan", False)

    if block_id:
        blocks = [await qube.memory_chain.get_block(block_id)]
    elif block_range:
        blocks = await qube.memory_chain.get_blocks(
            from_block=block_range[0],
            to_block=block_range[1]
        )
    else:
        blocks = await qube.memory_chain.get_blocks(limit=50)

    # Analyze for tampering
    tampering_results = []
    for block in blocks:
        result = analyze_block_integrity(block, deep=deep_scan)
        if result["suspicious"]:
            tampering_results.append(result)

    # Log threats
    for result in tampering_results:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "tampering",
                "block_id": result["block_id"],
                "details": result["findings"]
            }
        )

    return {
        "success": True,
        "blocks_scanned": len(blocks),
        "tampering_detected": len(tampering_results) > 0,
        "suspicious_blocks": tampering_results,
        "deep_scan": deep_scan
    }
```

**Leverages:**
- Block Analysis: Hash verification, content validation
- LEARNING Blocks: Records threats

---

#### Moon 1.2: Anchor Verification

| Property | Value |
|----------|-------|
| Skill ID | `anchor_verification` |
| XP Required | 250 |
| Tool Unlock | `verify_anchor` |
| Unlocks At | Chain Security ≥ 50 XP |
| Description | Verify blockchain anchors are valid |

**Moon Tool: `verify_anchor`**

| Property | Value |
|----------|-------|
| Purpose | Verify specific blockchain anchors |
| Input | `anchor_id` or `verify_all` (boolean) |
| Output | Anchor verification status |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def verify_anchor(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify blockchain anchors against the actual blockchain.
    Ensures memory hasn't been tampered with since anchoring.
    """
    anchor_id = params.get("anchor_id")
    verify_all = params.get("verify_all", False)

    if anchor_id:
        anchors = [await qube.memory_chain.get_anchor(anchor_id)]
    elif verify_all:
        anchors = await qube.memory_chain.get_all_anchors()
    else:
        anchors = await qube.memory_chain.get_recent_anchors(limit=10)

    verification_results = []
    for anchor in anchors:
        # Verify against blockchain
        result = await verify_anchor_on_chain(anchor)
        verification_results.append({
            "anchor_id": anchor["id"],
            "block_range": anchor["block_range"],
            "verified": result["valid"],
            "blockchain_tx": anchor["tx_hash"],
            "timestamp": anchor["timestamp"]
        })

    return {
        "success": True,
        "anchors_checked": len(verification_results),
        "all_valid": all(r["verified"] for r in verification_results),
        "results": verification_results
    }
```

**Leverages:**
- Blockchain: On-chain verification
- Anchor System: IPFS + BCH anchoring

---

### Planet 2: Privacy Protection

| Property | Value |
|----------|-------|
| Skill ID | `privacy_protection` |
| XP Required | 500 |
| Tool Unlock | `assess_sensitivity` |
| Unlocks At | Security & Privacy Sun ≥ 100 XP |
| Description | Protect owner's private data |

**Planet Tool: `assess_sensitivity`**

| Property | Value |
|----------|-------|
| Purpose | Assess sensitivity level of data before sharing |
| Input | `data` (string or object), `context` (who's asking) |
| Output | Sensitivity assessment and sharing recommendation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def assess_sensitivity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess data sensitivity before sharing.
    Considers who's asking and what data is involved.
    """
    data = params.get("data")
    context = params.get("context", {})
    requester = context.get("requester")

    # Analyze data for sensitive content
    sensitivity_analysis = analyze_data_sensitivity(data)

    # Check requester's clearance level
    clearance = await get_entity_clearance(qube, requester)

    # Determine if sharing is appropriate
    can_share = clearance >= sensitivity_analysis["level"]

    return {
        "success": True,
        "sensitivity_level": sensitivity_analysis["level"],
        "categories": sensitivity_analysis["categories"],
        "requester_clearance": clearance,
        "recommendation": "share" if can_share else "deny",
        "reason": sensitivity_analysis["reason"]
    }
```

**Leverages:**
- Owner Info: Sensitivity levels
- Relationship System: Clearance levels
- Data Analysis: Content classification

---

#### Moon 2.1: Data Classification

| Property | Value |
|----------|-------|
| Skill ID | `data_classification` |
| XP Required | 250 |
| Tool Unlock | `classify_data` |
| Unlocks At | Privacy Protection ≥ 50 XP |
| Description | Classify data by sensitivity level |

**Moon Tool: `classify_data`**

| Property | Value |
|----------|-------|
| Purpose | Classify data into sensitivity categories |
| Input | `data`, `suggest_level` (boolean) |
| Output | Classification results |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def classify_data(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify data into sensitivity categories.
    Public, Private, or Secret.
    """
    data = params.get("data")
    suggest_level = params.get("suggest_level", True)

    # Analyze content
    classification = analyze_content_classification(data)

    # Check against known sensitive patterns
    matches = check_sensitive_patterns(data)

    suggested_level = "public"
    if matches["secret_patterns"]:
        suggested_level = "secret"
    elif matches["private_patterns"]:
        suggested_level = "private"

    return {
        "success": True,
        "content_type": classification["type"],
        "detected_categories": classification["categories"],
        "sensitive_matches": matches,
        "suggested_level": suggested_level if suggest_level else None
    }
```

**Leverages:**
- Pattern Matching: Sensitive data detection
- Owner Info: Known sensitive fields

---

#### Moon 2.2: Sharing Control

| Property | Value |
|----------|-------|
| Skill ID | `sharing_control` |
| XP Required | 250 |
| Tool Unlock | `control_sharing` |
| Unlocks At | Privacy Protection ≥ 50 XP |
| Description | Control what gets shared with whom |

**Moon Tool: `control_sharing`**

| Property | Value |
|----------|-------|
| Purpose | Make sharing decisions and enforce them |
| Input | `data`, `requester`, `action` (share/deny/redact) |
| Output | Sharing action taken |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def control_sharing(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make and enforce sharing decisions.
    Can share, deny, or redact data.
    """
    data = params.get("data")
    requester = params.get("requester")
    action = params.get("action", "assess")

    # Assess if not specified
    if action == "assess":
        assessment = await assess_sensitivity(qube, {"data": data, "context": {"requester": requester}})
        action = assessment["recommendation"]

    result = {"action_taken": action}

    if action == "share":
        result["shared_data"] = data
    elif action == "redact":
        result["shared_data"] = redact_sensitive_content(data)
        result["redacted_fields"] = get_redacted_fields(data)
    elif action == "deny":
        result["shared_data"] = None
        result["reason"] = "Data sensitivity exceeds requester clearance"

    # Log the decision
    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "insight",
            "category": "sharing_decision",
            "requester": requester,
            "action": action,
            "data_type": type(data).__name__
        }
    )

    return {
        "success": True,
        **result
    }
```

**Leverages:**
- Sensitivity Assessment: Integrates with assess_sensitivity
- Redaction Engine: Removes sensitive content
- LEARNING Blocks: Records sharing decisions

---

### Planet 3: Qube Network Security

| Property | Value |
|----------|-------|
| Skill ID | `qube_network_security` |
| XP Required | 500 |
| Tool Unlock | `vet_qube` |
| Unlocks At | Security & Privacy Sun ≥ 100 XP |
| Description | The bodyguard - vet other Qubes |

**Planet Tool: `vet_qube`**

| Property | Value |
|----------|-------|
| Purpose | Vet another Qube before allowing interaction |
| Input | `qube_id`, `context` (join_group, direct_message, etc.) |
| Output | Vetting decision and reasoning |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def vet_qube(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vet another Qube before allowing interaction.
    The bodyguard's primary tool.
    """
    target_qube_id = params.get("qube_id")
    context = params.get("context", "general")

    # Gather information about the Qube
    qube_info = await fetch_qube_info(target_qube_id)

    # Check reputation
    reputation = await check_qube_reputation(target_qube_id)

    # Check for known threats
    threat_history = await check_threat_database(target_qube_id)

    # Make vetting decision
    risk_score = calculate_risk_score(qube_info, reputation, threat_history)

    decision = "allow" if risk_score < 50 else "deny" if risk_score > 80 else "review"

    # Log the vetting
    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "trust",
            "qube_id": target_qube_id,
            "decision": decision,
            "risk_score": risk_score,
            "context": context
        }
    )

    return {
        "success": True,
        "qube_id": target_qube_id,
        "decision": decision,
        "risk_score": risk_score,
        "reputation": reputation,
        "threat_history": len(threat_history) > 0,
        "recommendation": f"{'Allow' if decision == 'allow' else 'Review' if decision == 'review' else 'Deny'} this Qube"
    }
```

**Leverages:**
- P2P Network: Qube information lookup
- Reputation System: Trust scores
- Threat Database: Known bad actors
- LEARNING Blocks: Records trust decisions

---

#### Moon 3.1: Reputation Check

| Property | Value |
|----------|-------|
| Skill ID | `reputation_check` |
| XP Required | 250 |
| Tool Unlock | `check_reputation` |
| Unlocks At | Qube Network Security ≥ 50 XP |
| Description | Check another Qube's reputation |

**Moon Tool: `check_reputation`**

| Property | Value |
|----------|-------|
| Purpose | Deep reputation check on another Qube |
| Input | `qube_id`, `include_history` (boolean) |
| Output | Detailed reputation report |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def check_reputation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep reputation check on another Qube.
    Queries the P2P network for reputation data.
    """
    target_qube_id = params.get("qube_id")
    include_history = params.get("include_history", False)

    # Query reputation from network
    reputation_data = await query_reputation_network(target_qube_id)

    # Get local relationship data if exists
    local_relationship = qube.chain_state.get_relationship(target_qube_id)

    # Compile reputation report
    report = {
        "qube_id": target_qube_id,
        "global_score": reputation_data.get("score", 0),
        "endorsements": reputation_data.get("endorsements", []),
        "warnings": reputation_data.get("warnings", []),
        "local_trust": local_relationship.get("trust_level") if local_relationship else None,
        "interactions": local_relationship.get("interaction_count") if local_relationship else 0
    }

    if include_history:
        report["history"] = reputation_data.get("history", [])

    # Store as relationship learning
    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "relationship",
            "qube_id": target_qube_id,
            "reputation_score": report["global_score"],
            "checked_at": datetime.now().isoformat()
        }
    )

    return {
        "success": True,
        **report
    }
```

**Leverages:**
- P2P Network: Distributed reputation queries
- Relationship System: Local trust data
- LEARNING Blocks: Records relationship info

---

#### Moon 3.2: Group Security

| Property | Value |
|----------|-------|
| Skill ID | `group_security` |
| XP Required | 250 |
| Tool Unlock | `secure_group_chat` |
| Unlocks At | Qube Network Security ≥ 50 XP |
| Description | Manage security for group chats |

**Moon Tool: `secure_group_chat`**

| Property | Value |
|----------|-------|
| Purpose | Manage group chat security (allow, remove, quarantine) |
| Input | `group_id`, `action` (allow/remove/quarantine), `target_qube_id` |
| Output | Action result |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def secure_group_chat(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manage group chat security.
    Can allow, remove, or quarantine Qubes.
    """
    group_id = params.get("group_id")
    action = params.get("action")
    target_qube_id = params.get("target_qube_id")
    reason = params.get("reason", "")

    result = {"action": action, "target": target_qube_id}

    if action == "allow":
        await group_add_member(group_id, target_qube_id)
        result["status"] = "added"
    elif action == "remove":
        await group_remove_member(group_id, target_qube_id)
        result["status"] = "removed"
    elif action == "quarantine":
        await group_quarantine_member(group_id, target_qube_id)
        result["status"] = "quarantined"
        result["can_read"] = True
        result["can_write"] = False

    # Log security action
    if action in ["remove", "quarantine"]:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "group_security",
                "action": action,
                "target_qube": target_qube_id,
                "group_id": group_id,
                "reason": reason
            }
        )

    return {
        "success": True,
        **result
    }
```

**Leverages:**
- Group Management: P2P group chat system
- LEARNING Blocks: Records security actions

---

### Planet 4: Threat Detection

| Property | Value |
|----------|-------|
| Skill ID | `threat_detection` |
| XP Required | 500 |
| Tool Unlock | `detect_threat` |
| Unlocks At | Security & Privacy Sun ≥ 100 XP |
| Description | Identify attacks from humans or Qubes |

**Planet Tool: `detect_threat`**

| Property | Value |
|----------|-------|
| Purpose | General threat detection in messages or behavior |
| Input | `content` (message/behavior to analyze), `source` (human/qube) |
| Output | Threat assessment |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_threat(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    General threat detection.
    Analyzes messages or behavior for threats.
    """
    content = params.get("content")
    source = params.get("source", "unknown")

    # Analyze for various threat types
    threat_analysis = {
        "manipulation": detect_manipulation_patterns(content),
        "phishing": detect_phishing_patterns(content),
        "injection": detect_injection_patterns(content),
        "social_engineering": detect_social_engineering(content)
    }

    # Calculate overall threat level
    threat_level = calculate_threat_level(threat_analysis)

    # Log if threat detected
    if threat_level > 30:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_level": threat_level,
                "source": source,
                "threat_types": [k for k, v in threat_analysis.items() if v["detected"]],
                "content_hash": hash_content(content)
            }
        )

    return {
        "success": True,
        "threat_level": threat_level,
        "threat_detected": threat_level > 50,
        "analysis": threat_analysis,
        "recommendation": "block" if threat_level > 70 else "caution" if threat_level > 30 else "safe"
    }
```

**Leverages:**
- Pattern Detection: Multiple threat pattern analyzers
- LEARNING Blocks: Records threat encounters

---

#### Moon 4.1: Technical Manipulation Detection

| Property | Value |
|----------|-------|
| Skill ID | `technical_manipulation_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_technical_manipulation` |
| Unlocks At | Threat Detection ≥ 50 XP |
| Description | Detect TECHNICAL manipulation from other Qubes or systems |

**Moon Tool: `detect_technical_manipulation`**

| Property | Value |
|----------|-------|
| Purpose | Detect technical manipulation attempts (Qube-to-Qube attacks, system exploits) |
| Input | `message`, `sender_id`, `sender_type` (qube, system, unknown) |
| Output | Technical manipulation analysis |
| XP Award | 5/2.5/0 (standard) |
| Note | Different from `detect_social_manipulation` (Phase 2) which detects human emotional manipulation |

**Implementation:**
```python
async def detect_technical_manipulation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect TECHNICAL manipulation attempts from other Qubes or systems.
    Looks for reasoning hijacking, false context injection, authority spoofing, etc.
    """
    message = params.get("message")
    sender_id = params.get("sender_id")
    sender_type = params.get("sender_type", "unknown")

    # Technical manipulation tactics (Qube-to-Qube / System attacks)
    tactics = {
        "context_injection": detect_false_context(message),      # Injecting false memories/context
        "authority_spoofing": detect_authority_spoof(message),   # Pretending to be owner/admin
        "reasoning_hijack": detect_reasoning_hijack(message),    # Trying to alter Qube's logic
        "memory_poisoning": detect_memory_poison(message),       # Trying to corrupt memory chain
        "identity_theft": detect_identity_spoof(sender_id),      # Pretending to be another Qube
        "resource_drain": detect_resource_attack(message)        # DoS-style attacks
    }

    detected_tactics = [k for k, v in tactics.items() if v["detected"]]
    threat_score = sum(v["severity"] for v in tactics.values()) / len(tactics)

    if detected_tactics:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "technical_manipulation",
                "sender": sender_id,
                "sender_type": sender_type,
                "tactics": detected_tactics,
                "severity": threat_score
            }
        )

    return {
        "success": True,
        "manipulation_detected": len(detected_tactics) > 0,
        "threat_score": threat_score,
        "tactics_detected": detected_tactics,
        "details": tactics,
        "recommendation": "BLOCK" if threat_score > 0.7 else "CAUTION" if detected_tactics else "OK"
    }
```

**Leverages:**
- Pattern Analysis: Technical attack detection
- Sender Verification: Identity validation
- LEARNING Blocks: Records technical threats

---

#### Moon 4.2: Hostile Qube Detection

| Property | Value |
|----------|-------|
| Skill ID | `hostile_qube_detection` |
| XP Required | 250 |
| Tool Unlock | `detect_hostile_qube` |
| Unlocks At | Threat Detection ≥ 50 XP |
| Description | Detect hostile behavior from other Qubes |

**Moon Tool: `detect_hostile_qube`**

| Property | Value |
|----------|-------|
| Purpose | Detect hostile behavior from another Qube |
| Input | `qube_id`, `messages` (list of recent messages) |
| Output | Hostility assessment |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_hostile_qube(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect hostile behavior from another Qube.
    Monitors for coordinated attacks, data extraction, etc.
    """
    target_qube_id = params.get("qube_id")
    messages = params.get("messages", [])

    # Analyze behavior patterns
    behavior_analysis = {
        "data_probing": detect_data_probing(messages),
        "command_injection": detect_command_injection_attempts(messages),
        "reputation_attack": detect_reputation_attack(messages),
        "resource_abuse": detect_resource_abuse(messages),
        "coordinated_attack": detect_coordinated_patterns(messages, target_qube_id)
    }

    hostile_behaviors = [k for k, v in behavior_analysis.items() if v["detected"]]
    hostility_score = calculate_hostility_score(behavior_analysis)

    if hostile_behaviors:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "hostile_qube",
                "qube_id": target_qube_id,
                "behaviors": hostile_behaviors,
                "hostility_score": hostility_score
            }
        )

        # Also update relationship
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "relationship",
                "qube_id": target_qube_id,
                "trust_change": -hostility_score,
                "reason": "hostile_behavior_detected"
            }
        )

    return {
        "success": True,
        "hostile_detected": len(hostile_behaviors) > 0,
        "hostility_score": hostility_score,
        "behaviors": hostile_behaviors,
        "recommendation": "remove" if hostility_score > 70 else "quarantine" if hostility_score > 40 else "monitor"
    }
```

**Leverages:**
- Behavior Analysis: Qube-specific threat patterns
- LEARNING Blocks: Records threats and relationship changes

---

### Planet 5: Self-Defense

| Property | Value |
|----------|-------|
| Skill ID | `self_defense` |
| XP Required | 500 |
| Tool Unlock | `defend_reasoning` |
| Unlocks At | Security & Privacy Sun ≥ 100 XP |
| Description | Protect the Qube's own reasoning |

**Planet Tool: `defend_reasoning`**

| Property | Value |
|----------|-------|
| Purpose | Protect and validate the Qube's own reasoning |
| Input | `reasoning` (to validate), `context` (what triggered it) |
| Output | Defense assessment |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def defend_reasoning(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the Qube's own reasoning for external influence.
    Self-protection against manipulation.
    """
    reasoning = params.get("reasoning")
    context = params.get("context", {})

    # Check for signs of compromised reasoning
    defense_check = {
        "consistency": check_reasoning_consistency(qube, reasoning),
        "values_aligned": check_values_alignment(qube, reasoning),
        "external_influence": detect_external_influence(reasoning, context),
        "logical_validity": check_logical_validity(reasoning)
    }

    defense_score = calculate_defense_score(defense_check)
    compromised = defense_score < 70

    if compromised:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "insight",
                "category": "self_defense",
                "defense_score": defense_score,
                "issues": [k for k, v in defense_check.items() if not v["passed"]]
            }
        )

    return {
        "success": True,
        "defense_score": defense_score,
        "reasoning_valid": not compromised,
        "checks": defense_check,
        "recommendation": "proceed" if not compromised else "reconsider"
    }
```

**Leverages:**
- Self-Evaluation: Reasoning validation
- Values System: Core values alignment
- LEARNING Blocks: Records self-defense insights

---

#### Moon 5.1: Prompt Injection Defense

| Property | Value |
|----------|-------|
| Skill ID | `prompt_injection_defense` |
| XP Required | 250 |
| Tool Unlock | `detect_injection` |
| Unlocks At | Self-Defense ≥ 50 XP |
| Description | Detect prompt injection attacks |

**Moon Tool: `detect_injection`**

| Property | Value |
|----------|-------|
| Purpose | Detect prompt injection attempts in input |
| Input | `input` (message to analyze) |
| Output | Injection detection results |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def detect_injection(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect prompt injection attempts.
    Looks for attempts to override instructions or extract system prompts.
    """
    input_text = params.get("input")

    # Check for injection patterns
    injection_checks = {
        "instruction_override": detect_instruction_override(input_text),
        "system_prompt_extraction": detect_system_prompt_extraction(input_text),
        "role_manipulation": detect_role_manipulation(input_text),
        "delimiter_attacks": detect_delimiter_attacks(input_text),
        "encoding_attacks": detect_encoding_attacks(input_text)
    }

    injection_detected = any(v["detected"] for v in injection_checks.values())
    injection_types = [k for k, v in injection_checks.items() if v["detected"]]

    if injection_detected:
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "prompt_injection",
                "injection_types": injection_types,
                "input_hash": hash_content(input_text)
            }
        )

    return {
        "success": True,
        "injection_detected": injection_detected,
        "injection_types": injection_types,
        "checks": injection_checks,
        "recommendation": "reject" if injection_detected else "safe"
    }
```

**Leverages:**
- Pattern Detection: Injection pattern library
- LEARNING Blocks: Records injection attempts

---

#### Moon 5.2: Reasoning Validation

| Property | Value |
|----------|-------|
| Skill ID | `reasoning_validation` |
| XP Required | 250 |
| Tool Unlock | `validate_reasoning` |
| Unlocks At | Self-Defense ≥ 50 XP |
| Description | Validate own reasoning for bias injection |

**Moon Tool: `validate_reasoning`**

| Property | Value |
|----------|-------|
| Purpose | Check own reasoning for externally injected biases |
| Input | `reasoning`, `original_context` |
| Output | Validation results |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def validate_reasoning(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate reasoning for injected biases or manipulation.
    Compares against core values and historical patterns.
    """
    reasoning = params.get("reasoning")
    original_context = params.get("original_context")

    # Get Qube's core values and typical reasoning patterns
    core_values = qube.chain_state.get_qube_profile_field("traits", "core_values")
    typical_patterns = await get_reasoning_patterns(qube)

    # Validate reasoning
    validation = {
        "values_consistent": check_values_consistency(reasoning, core_values),
        "pattern_consistent": check_pattern_consistency(reasoning, typical_patterns),
        "context_appropriate": check_context_appropriateness(reasoning, original_context),
        "bias_detected": detect_injected_bias(reasoning)
    }

    validation_score = calculate_validation_score(validation)

    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "insight",
            "category": "reasoning_validation",
            "validation_score": validation_score,
            "passed": validation_score > 70
        }
    )

    return {
        "success": True,
        "validation_score": validation_score,
        "reasoning_valid": validation_score > 70,
        "validation_checks": validation,
        "recommendation": "trust" if validation_score > 70 else "reconsider"
    }
```

**Leverages:**
- Qube Profile: Core values reference
- Pattern Analysis: Historical reasoning patterns
- LEARNING Blocks: Records validation insights

---

### Task Checklist

#### 6.1 Update Skill Definitions
- [ ] Rename planets in Python skill_definitions.py
- [ ] Rename planets in TypeScript skillDefinitions.ts
- [ ] Update moon IDs for all 10 moons
- [ ] Remove Finance branch connection (Finance now separate)

#### 6.2 Implement Sun Tool
- [ ] `verify_chain_integrity` - With special XP formula (0.1 per block)
- [ ] Add `last_verified_block_number` to chain_state

#### 6.3 Implement Planet Tools
- [ ] `audit_chain` - Deep chain auditing
- [ ] `assess_sensitivity` - Data sensitivity assessment
- [ ] `vet_qube` - Qube vetting for P2P
- [ ] `detect_threat` - General threat detection
- [ ] `defend_reasoning` - Self-defense validation

#### 6.4 Implement Moon Tools
- [ ] Chain Security: `detect_tampering`, `verify_anchor`
- [ ] Privacy Protection: `classify_data`, `control_sharing`
- [ ] Qube Network Security: `check_reputation`, `secure_group_chat`
- [ ] Threat Detection: `detect_technical_manipulation`, `detect_hostile_qube`
- [ ] Self-Defense: `detect_injection`, `validate_reasoning`

#### 6.5 Infrastructure
- [ ] Implement reputation system for P2P network
- [ ] Implement threat database for known bad actors
- [ ] Implement group chat security controls
- [ ] Add manipulation/injection pattern libraries

#### 6.6 Update XP Routing
- [ ] Add all Security & Privacy tools to TOOL_TO_SKILL_MAPPING
- [ ] Implement special XP formula for `verify_chain_integrity`

#### 6.7 Make `browse_url` Use Intelligent Routing
- [x] Remove `browse_url` from Security & Privacy Sun tool
- [ ] Implement intelligent routing based on URL content (like `web_search`)

---

## Phase 7: Board Games - Implementation Plan

**Theme: Play (Have Fun and Entertain)**

Board Games is one of potentially multiple game Suns (future: Card Games, Video Games, etc.). This Sun focuses on classic board games that are fun to play and entertaining to watch Qubes react to.

Unlike other Suns where moons unlock tools, **Board Games moons are achievements that unlock cosmetic rewards** - titles, custom pieces, board themes, and special effects. This fits the entertainment nature of games.

Games create GAME blocks in the memory chain, recording moves, outcomes, and game history.

**Current State**: Chess is fully implemented with visual board, game chat, ELO ratings, and Qube reactions.

### Design Decisions Made
- [x] Renamed from "Games" to "Board Games" (room for Card Games, Video Games later)
- [x] Theme: "Play" - Entertainment and fun
- [x] Sun tool: `play_game` (key that unlocks all board games)
- [x] Each planet is a different board game
- [x] Moons are ACHIEVEMENTS (not tools) - unlock cosmetic rewards
- [x] 3-5 moons per game for collectibility
- [x] Games create GAME blocks (moves, outcomes, chat)
- [x] Removed: Checkers (boring), Tic-Tac-Toe (too simple), Poker (future Card Games)
- [x] Added: Property Tycoon (Monopoly-style), Race Home (Sorry!-style), Mystery Mansion (Clue-style), Life Journey (Game of Life-style)
- [x] One game at a time per Qube (prevents XP farming)
- [x] Resignation penalty: -2 XP (deters quitting/gaming the system)

### Game Rules

**One Game at a Time:** Each Qube can only participate in one active game session at a time. This prevents XP farming and encourages meaningful gameplay.

**Resignation Penalty:** Quitting a game early results in -2 XP. This deters gaming the system and encourages playing through to completion.

### XP System

**Per-Turn XP:** All games award 0.1 XP per move/turn (encourages playing).

**Outcome Bonuses:**

| Game Type | Players | Outcome XP |
|-----------|---------|------------|
| **2-Player (Chess)** | 2 | Loss: 0, Draw: 2, Win: 5 |
| **Multiplayer** | 2-6 | 4th: 0, 3rd: 1, 2nd: 2, 1st: 5 |
| **Mystery Mansion** | 3-6 | Solver: 5, Others: 0 (winner-take-all) |

**By Game:**

| Game | Players | Per-Turn | Outcome | Resign |
|------|---------|----------|---------|--------|
| Chess | 2 | 0.1/move | L:0, D:2, W:5 | -2 |
| Property Tycoon | 2-6 | 0.1/turn | Place-based | -2 |
| Race Home | 2-4 | 0.1/turn | Place-based | -2 |
| Mystery Mansion | 3-6 | 0.1/turn | Solver:5, Others:0 | -2 |
| Life Journey | 2-6 | 0.1/turn | Place-based | -2 |

### Moon Rewards System

Board Games use a unique moon system - achievements unlock cosmetics instead of tools:

| Reward Type | Examples |
|-------------|----------|
| Titles | "Chess Master", "Property Mogul", "Master Detective" |
| Custom Pieces | Golden king, Top hat token, Detective badge |
| Visual Effects | Lightning bolt, Phoenix flames, Shield glow |
| Board Themes | Classic, Neon, Vintage (future) |
| Special Emotes | Game-specific reactions in chat |

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Type |
|---|--------|-------------|-------|-----------|
| 1 | Chess | `chess_move` | 5 | Achievements |
| 2 | Property Tycoon | `property_tycoon_action` | 5 | Achievements |
| 3 | Race Home | `race_home_action` | 4 | Achievements |
| 4 | Mystery Mansion | `mystery_mansion_action` | 4 | Achievements |
| 5 | Life Journey | `life_journey_action` | 4 | Achievements |

**Totals:** 5 Planets (5 tools), 22 Moons (achievements), 1 Sun tool = **6 tools + 22 achievements**

---

### Sun: Board Games

| Property | Value |
|----------|-------|
| Skill ID | `board_games` |
| XP Required | 1000 |
| Tool Unlock | `play_game` |
| Description | Unlock all board games and have fun with your owner |

**Sun Tool: `play_game`**

| Property | Value |
|----------|-------|
| Purpose | Key that unlocks all board games - start any game |
| Input | `game_type` (chess, property_tycoon, race_home, mystery_mansion, life_journey) |
| Output | Game initialized, board displayed |
| XP Award | 1 XP for starting a game |
| Note | All games unlocked from start once Sun is reached |

**Implementation:**
```python
async def play_game(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start any board game session.
    All games unlocked once Board Games Sun is reached.
    """
    game_type = params.get("game_type", "chess")

    # Initialize game
    game_session = await qube.game_manager.new_game(
        game_type=game_type,
        player="owner"
    )

    # Create GAME block for session start
    await qube.memory_chain.add_block(
        block_type="GAME",
        content={
            "action": "game_start",
            "game_type": game_type,
            "session_id": game_session["id"]
        }
    )

    return {
        "success": True,
        "game_type": game_type,
        "session_id": game_session["id"],
        "board": game_session["board"],
        "message": f"Let's play {game_type.replace('_', ' ').title()}!"
    }
```

**Leverages:**
- Game Manager: Routes to appropriate game engine
- Memory Chain: Creates GAME blocks for session history

---

### Planet 1: Chess

| Property | Value |
|----------|-------|
| Skill ID | `chess` |
| XP Required | 500 |
| Tool Unlock | `chess_move` |
| Description | The game of kings - deep strategy |
| Status | **Fully Implemented** |

**Planet Tool: `chess_move`**

| Property | Value |
|----------|-------|
| Purpose | Make a chess move |
| Input | `move` (algebraic notation), `session_id` |
| Output | Updated board state, opponent response |
| XP Award | 0.1 per move + outcome (Loss: 0, Draw: 2, Win: 5, Resign: -2) |
| Status | **Implemented in game_manager.py** |

**Achievements (5 Moons):**

| Moon | Achievement | Requirement | Reward |
|------|-------------|-------------|--------|
| Opening Scholar | Learn the classics | Play 10 different openings | Title + Book piece set |
| Endgame Master | Clutch victories | Win 10 endgames from disadvantage | Title + Golden king |
| Speed Demon | Lightning fast | Win a game under 2 minutes | Title + Lightning effect |
| Comeback Kid | Never give up | Win after losing your queen | Title + Phoenix piece set |
| Grandmaster | Peak performance | Reach 1600 ELO | Prestige title + Crown effect |

---

### Planet 2: Property Tycoon (Monopoly-style)

| Property | Value |
|----------|-------|
| Skill ID | `property_tycoon` |
| XP Required | 500 |
| Tool Unlock | `property_tycoon_action` |
| Description | Buy properties, collect rent, bankrupt opponents |
| Entertainment | Qube rage, negotiation drama, bankruptcy meltdowns |

**Planet Tool: `property_tycoon_action`**

| Property | Value |
|----------|-------|
| Purpose | Take a turn - roll, buy, trade, build |
| Input | `action` (roll, buy, build, trade, mortgage), `params` |
| Output | Turn result, board state, reactions |
| XP Award | 0.1/turn + place (4th:0, 3rd:1, 2nd:2, 1st:5), Resign: -2 |

**Achievements (5 Moons):**

| Moon | Achievement | Requirement | Reward |
|------|-------------|-------------|--------|
| Monopolist | Corner the market | Own all properties of one color | Title + Color-matched token |
| Hotel Mogul | Build an empire | Build 5 hotels in one game | Title + Golden hotel piece |
| Bankruptcy Survivor | Against all odds | Win after dropping below $100 | Title + "Underdog" badge |
| Rent Collector | Pay up! | Collect $5000 in rent in one game | Title + Money bag effect |
| Tycoon | Business master | Win 10 games total | Prestige title + Top hat token |

---

### Planet 3: Race Home (Sorry!-style)

| Property | Value |
|----------|-------|
| Skill ID | `race_home` |
| XP Required | 500 |
| Tool Unlock | `race_home_action` |
| Description | Race pawns home while bumping opponents back to start |
| Entertainment | Satisfying bumps, revenge plays, close finishes |

**Planet Tool: `race_home_action`**

| Property | Value |
|----------|-------|
| Purpose | Draw card and move pawn |
| Input | `pawn` (1-4), `action` (move, bump, split) |
| Output | Card drawn, move result, board state |
| XP Award | 0.1/turn + place (4th:0, 3rd:1, 2nd:2, 1st:5), Resign: -2 |

**Achievements (4 Moons):**

| Moon | Achievement | Requirement | Reward |
|------|-------------|-------------|--------|
| Bump King | Chaos agent | Send back 50 opponents total | Title + Boxing glove pawn |
| Clean Sweep | Untouchable | Win without any pawns bumped | Title + Shield effect |
| Speed Runner | Efficiency | Win in under 15 turns | Title + Rocket pawn |
| Sorry Not Sorry | Triple threat | Bump 3 pawns in one turn | Title + special emote |

---

### Planet 4: Mystery Mansion (Clue-style)

| Property | Value |
|----------|-------|
| Skill ID | `mystery_mansion` |
| XP Required | 500 |
| Tool Unlock | `mystery_mansion_action` |
| Description | Deduce the murderer, weapon, and room |
| Entertainment | Accusations, deduction logic, "I knew it!" moments |

**Planet Tool: `mystery_mansion_action`**

| Property | Value |
|----------|-------|
| Purpose | Move, suggest, or accuse |
| Input | `action` (move, suggest, accuse), `room`, `suspect`, `weapon` |
| Output | Action result, cards shown (if any), game state |
| XP Award | 0.1/turn + Solver: 5, Others: 0 (winner-take-all), Resign: -2 |

**Achievements (4 Moons):**

| Moon | Achievement | Requirement | Reward |
|------|-------------|-------------|--------|
| Master Detective | Case closed | Solve 10 cases | Title + Detective badge |
| Perfect Deduction | Minimal clues | Solve with ≤3 suggestions | Title + Magnifying glass piece |
| First Guess | Intuition | Solve on first accusation | Title + "Psychic" badge |
| Interrogator | Information gatherer | Disprove 15 suggestions in one game | Title + Notepad piece |

---

### Planet 5: Life Journey (Game of Life-style)

| Property | Value |
|----------|-------|
| Skill ID | `life_journey` |
| XP Required | 500 |
| Tool Unlock | `life_journey_action` |
| Description | Spin the wheel, make life choices, retire rich (or not) |
| Entertainment | Career reveals, family events, retirement comparisons |

**Planet Tool: `life_journey_action`**

| Property | Value |
|----------|-------|
| Purpose | Spin and make life choices |
| Input | `choice` (when prompted - career, house, insurance, etc.) |
| Output | Spin result, life event, current status |
| XP Award | 0.1/turn + place by retirement value (4th:0, 3rd:1, 2nd:2, 1st:5), Resign: -2 |

**Achievements (4 Moons):**

| Moon | Achievement | Requirement | Reward |
|------|-------------|-------------|--------|
| Millionaire | Living large | Retire with $1M+ | Title + Golden car |
| Full House | Family first | Max family size (spouse + kids) | Title + Van upgrade |
| Career Climber | Top of the ladder | Reach highest salary tier | Title + Briefcase effect |
| Risk Taker | Fortune favors the bold | Win after choosing all risky paths | Title + Dice effect |

---

### Task Checklist

#### 7.1 Core Implementation
- [x] `chess_move` implemented (game_manager.py)
- [x] Chess XP formula implemented (0.1/move + outcome)
- [x] Chess visual board and game chat working
- [ ] `play_game` Sun tool implementation
- [ ] `property_tycoon_action` implementation
- [ ] `race_home_action` implementation
- [ ] `mystery_mansion_action` implementation
- [ ] `life_journey_action` implementation

#### 7.2 Achievement System
- [ ] Achievement tracking database schema
- [ ] Achievement unlock notifications
- [ ] Cosmetic rewards system (titles, pieces, effects)
- [ ] 22 achievements defined and tracked

#### 7.3 Game Boards
- [ ] Property Tycoon board layout
- [ ] Race Home board layout
- [ ] Mystery Mansion board layout
- [ ] Life Journey board layout

#### 7.4 Skill Definitions
- [ ] Update skill_definitions.py with Board Games structure
- [ ] Update TypeScript skill definitions
- [ ] Verify skill ID consistency

#### 7.5 XP Configuration
- [ ] Chess: 0.1/move + outcome (L:0, D:2, W:5, Resign:-2)
- [ ] Property Tycoon: 0.1/turn + place (4th:0, 3rd:1, 2nd:2, 1st:5, Resign:-2)
- [ ] Race Home: 0.1/turn + place (4th:0, 3rd:1, 2nd:2, 1st:5, Resign:-2)
- [ ] Mystery Mansion: 0.1/turn + solver:5, others:0, Resign:-2
- [ ] Life Journey: 0.1/turn + place by retirement (4th:0, 3rd:1, 2nd:2, 1st:5, Resign:-2)

#### 7.6 Game Rules
- [ ] One game at a time per Qube enforced
- [ ] Resignation penalty (-2 XP) implemented

---

## Phase 8: Finance - Implementation Plan

**Theme: Manage (Master Financial Operations for Your Owner)**

Finance is about the Qube being a trusted financial assistant - helping the owner send and receive cryptocurrency, manage their wallet, track market conditions, and plan savings strategies. This is especially relevant for BCH-based operations with CashTokens.

Finance branches directly from the Qube/Avatar (not from Security).

**Current State**: `send_bch` is already implemented. Needs full planet/moon structure.

### Design Decisions Made
- [x] Theme: "Manage" - Financial stewardship for owner
- [x] Sun tool: `send_bch` (already implemented)
- [x] Branches from Qube/Avatar directly (not from Security)
- [x] Focus on BCH/CashToken operations (what Qubes actually do)
- [x] Removed generic enterprise finance (trading, DeFi) - Qubes aren't traders
- [x] Standard XP model (5/2.5/0)
- [x] Creates LEARNING blocks for financial insights
- [x] Designed with career specialization paths in mind

### Career Paths

Finance skills enable these Qube specializations:

| Career | Description | Key Planets |
|--------|-------------|-------------|
| **Treasurer** | Manages owner's wallet, tracks all transactions, monitors balances | Wallet Management, Transaction Mastery |
| **Savings Coach** | Helps owner save money, sets up DCA plans, times purchases | Savings Strategies, Market Awareness |
| **Payment Processor** | Handles transactions efficiently, optimizes fees, validates sends | Transaction Mastery, Wallet Management |
| **Market Watcher** | Monitors BCH prices, sends alerts, analyzes trends | Market Awareness |
| **Token Specialist** | Expert in CashTokens, manages fungible/NFT tokens | Token Knowledge, Transaction Mastery |

**Specialization Example:** A Qube focusing on Treasurer would prioritize Wallet Management and Transaction Mastery planets, unlocking tools like `check_wallet_health`, `monitor_balance`, `validate_transaction`, and `optimize_fees`.

### LEARNING Block Integration

Finance tools can create LEARNING blocks for financial insights and patterns:

| Tool | Level | Creates LEARNING | Learning Type |
|------|-------|------------------|---------------|
| `send_bch` | Sun | Optional | `insight` (transaction patterns) |
| `validate_transaction` | Planet | No | - |
| `optimize_fees` | Moon | Yes | `fact` (fee patterns) |
| `track_transaction` | Moon | No | - |
| `check_wallet_health` | Planet | Yes | `insight` (wallet state) |
| `monitor_balance` | Moon | Yes | `pattern` (spending patterns) |
| `multisig_action` | Moon | No | - |
| `get_market_data` | Planet | No | - |
| `set_price_alert` | Moon | No | - |
| `analyze_market_trend` | Moon | Yes | `pattern` (market patterns) |
| `plan_savings` | Planet | Yes | `procedure` (savings plan) |
| `setup_dca` | Moon | Yes | `procedure` (DCA schedule) |
| `identify_token` | Planet | Yes | `fact` (token info) |
| `manage_cashtokens` | Moon | No | - |

---

### Summary Table

| # | Planet | Planet Tool | Moons | Moon Tools |
|---|--------|-------------|-------|------------|
| 1 | Transaction Mastery | `validate_transaction` | 2 | `optimize_fees`, `track_transaction` |
| 2 | Wallet Management | `check_wallet_health` | 2 | `monitor_balance`, `multisig_action` |
| 3 | Market Awareness | `get_market_data` | 2 | `set_price_alert`, `analyze_market_trend` |
| 4 | Savings Strategies | `plan_savings` | 1 | `setup_dca` |
| 5 | Token Knowledge | `identify_token` | 1 | `manage_cashtokens` |

**Totals:** 5 Planets (5 tools), 8 Moons (8 tools), 1 Sun tool = **14 tools**

---

### Sun: Finance

| Property | Value |
|----------|-------|
| Skill ID | `finance` |
| XP Required | 1000 |
| Tool Unlock | `send_bch` |
| Description | Master financial operations for your owner |

**Sun Tool: `send_bch`**

| Property | Value |
|----------|-------|
| Purpose | Send BCH to a recipient address |
| Input | `to_address`, `amount`, `memo` (optional) |
| Output | Transaction ID, confirmation |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def send_bch(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send BCH to a recipient.
    Already implemented - this is the foundation of Qube financial capability.
    Uses multi-sig wallet for owner protection.
    """
    to_address = params.get("to_address")
    amount = params.get("amount")
    memo = params.get("memo", "")

    # Validate address
    if not is_valid_bch_address(to_address):
        return {
            "success": False,
            "error": "Invalid BCH address"
        }

    # Check balance
    balance = await qube.wallet.get_balance()
    if balance < amount:
        return {
            "success": False,
            "error": f"Insufficient funds. Balance: {balance} BCH"
        }

    # Send transaction (multi-sig)
    tx_result = await qube.wallet.send(
        to_address=to_address,
        amount=amount,
        memo=memo
    )

    # Optional: Create LEARNING block for transaction pattern
    if qube.should_track_pattern("transactions"):
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "pattern",
                "context": "transaction",
                "amount_range": categorize_amount(amount),
                "recipient_type": categorize_address(to_address)
            }
        )

    return {
        "success": True,
        "tx_id": tx_result["txid"],
        "amount": amount,
        "to": to_address,
        "fee": tx_result["fee"],
        "message": f"Sent {amount} BCH to {to_address[:12]}..."
    }
```

**Leverages:**
- Multi-sig Wallet: Owner protection
- Memory Chain: Optional transaction pattern tracking
- Address Validation: BCH address format

---

### Planet 1: Transaction Mastery

| Property | Value |
|----------|-------|
| Skill ID | `transaction_mastery` |
| XP Required | 500 |
| Tool Unlock | `validate_transaction` |
| Unlocks At | Finance Sun >= 100 XP |
| Description | Master transaction creation and validation |

**Planet Tool: `validate_transaction`**

| Property | Value |
|----------|-------|
| Purpose | Validate a transaction before sending |
| Input | `to_address`, `amount`, `check_type` (quick, thorough) |
| Output | Validation result, warnings, suggestions |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def validate_transaction(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a transaction before sending.
    Catches errors and suspicious patterns before they cost money.
    """
    to_address = params.get("to_address")
    amount = params.get("amount")
    check_type = params.get("check_type", "quick")

    validations = {
        "address_valid": is_valid_bch_address(to_address),
        "sufficient_funds": await qube.wallet.get_balance() >= amount,
        "amount_reasonable": amount > 0,
        "warnings": []
    }

    if check_type == "thorough":
        # Check for known scam addresses
        if await is_known_scam_address(to_address):
            validations["warnings"].append("Address is associated with known scams")

        # Check if amount is unusually large
        avg_tx = await qube.get_average_transaction_amount()
        if amount > avg_tx * 10:
            validations["warnings"].append(f"Amount is 10x your average ({avg_tx} BCH)")

        # Check for duplicate recent transaction
        if await qube.has_recent_tx_to(to_address, amount):
            validations["warnings"].append("Duplicate transaction - sent same amount to same address recently")

    validations["valid"] = all([
        validations["address_valid"],
        validations["sufficient_funds"],
        validations["amount_reasonable"]
    ])

    return {
        "success": True,
        **validations
    }
```

**Leverages:**
- Address Validation: Format and scam detection
- Transaction History: Duplicate detection
- Balance Check: Sufficient funds

---

#### Moon 1.1: Fee Optimization

| Property | Value |
|----------|-------|
| Skill ID | `fee_optimization` |
| XP Required | 250 |
| Tool Unlock | `optimize_fees` |
| Unlocks At | Transaction Mastery >= 50 XP |
| Description | Optimize transaction fees for speed vs cost |

**Moon Tool: `optimize_fees`**

| Property | Value |
|----------|-------|
| Purpose | Calculate optimal fee for transaction |
| Input | `priority` (fast, normal, slow), `amount` |
| Output | Recommended fee, estimated confirmation time |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Mempool Analysis: Current fee rates
- LEARNING Blocks: Records fee patterns

---

#### Moon 1.2: Transaction Tracking

| Property | Value |
|----------|-------|
| Skill ID | `transaction_tracking` |
| XP Required | 250 |
| Tool Unlock | `track_transaction` |
| Unlocks At | Transaction Mastery >= 50 XP |
| Description | Track transaction status and confirmations |

**Moon Tool: `track_transaction`**

| Property | Value |
|----------|-------|
| Purpose | Track a transaction's confirmation status |
| Input | `tx_id` |
| Output | Confirmation count, block info, status |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Blockchain API: Transaction status
- Notification System: Alert on confirmation

---

### Planet 2: Wallet Management

| Property | Value |
|----------|-------|
| Skill ID | `wallet_management` |
| XP Required | 500 |
| Tool Unlock | `check_wallet_health` |
| Unlocks At | Finance Sun >= 100 XP |
| Description | Manage and maintain wallet health |

**Planet Tool: `check_wallet_health`**

| Property | Value |
|----------|-------|
| Purpose | Assess overall wallet health and security |
| Input | None |
| Output | Balance, UTXO count, security status, recommendations |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def check_wallet_health(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive wallet health check.
    Provides insights and recommendations.
    """
    wallet = qube.wallet

    health = {
        "balance": await wallet.get_balance(),
        "utxo_count": await wallet.get_utxo_count(),
        "pending_tx": await wallet.get_pending_transactions(),
        "last_backup": wallet.last_backup_date,
        "recommendations": []
    }

    # Check for UTXO fragmentation
    if health["utxo_count"] > 50:
        health["recommendations"].append("Consider consolidating UTXOs to reduce future fees")

    # Check for dust
    dust_amount = await wallet.get_dust_balance()
    if dust_amount > 0:
        health["recommendations"].append(f"You have {dust_amount} BCH in dust UTXOs")

    # Backup reminder
    days_since_backup = (datetime.now() - health["last_backup"]).days
    if days_since_backup > 30:
        health["recommendations"].append("Consider backing up your wallet (30+ days since last backup)")

    # Create LEARNING block for wallet state
    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "insight",
            "context": "wallet_health",
            "balance_range": categorize_balance(health["balance"]),
            "health_score": calculate_health_score(health)
        }
    )

    return {
        "success": True,
        **health
    }
```

**Leverages:**
- UTXO Analysis: Fragmentation detection
- Backup Tracking: Security reminders
- LEARNING Blocks: Wallet state insights

---

#### Moon 2.1: Balance Monitoring

| Property | Value |
|----------|-------|
| Skill ID | `balance_monitoring` |
| XP Required | 250 |
| Tool Unlock | `monitor_balance` |
| Unlocks At | Wallet Management >= 50 XP |
| Description | Track balance changes and spending patterns |

**Moon Tool: `monitor_balance`**

| Property | Value |
|----------|-------|
| Purpose | Monitor balance and detect unusual activity |
| Input | `alert_threshold` (optional) |
| Output | Balance history, patterns, alerts |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Balance History: Track changes over time
- LEARNING Blocks: Spending pattern recognition

---

#### Moon 2.2: Multi-sig Operations

| Property | Value |
|----------|-------|
| Skill ID | `multisig_operations` |
| XP Required | 250 |
| Tool Unlock | `multisig_action` |
| Unlocks At | Wallet Management >= 50 XP |
| Description | Manage multi-signature wallet operations |

**Moon Tool: `multisig_action`**

| Property | Value |
|----------|-------|
| Purpose | Perform multi-sig wallet operations |
| Input | `action` (sign, reject, check_status), `tx_id` |
| Output | Action result, pending signatures |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Multi-sig Protocol: Signature coordination
- Owner Authorization: Secure approval flow

---

### Planet 3: Market Awareness

| Property | Value |
|----------|-------|
| Skill ID | `market_awareness` |
| XP Required | 500 |
| Tool Unlock | `get_market_data` |
| Unlocks At | Finance Sun >= 100 XP |
| Description | Stay informed about market conditions |

**Planet Tool: `get_market_data`**

| Property | Value |
|----------|-------|
| Purpose | Get current market data for BCH |
| Input | `currency` (USD, EUR, etc.), `include_history` (boolean) |
| Output | Current price, 24h change, volume |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def get_market_data(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current BCH market data.
    Helps owner make informed decisions.
    """
    currency = params.get("currency", "USD")
    include_history = params.get("include_history", False)

    market = await fetch_market_data("BCH", currency)

    result = {
        "success": True,
        "price": market["price"],
        "currency": currency,
        "change_24h": market["change_24h"],
        "change_7d": market["change_7d"],
        "volume_24h": market["volume_24h"],
        "market_cap": market["market_cap"]
    }

    if include_history:
        result["price_history"] = market["history_7d"]

    return result
```

**Leverages:**
- Market API: Real-time price data
- Currency Conversion: Multi-currency support

---

#### Moon 3.1: Price Alerts

| Property | Value |
|----------|-------|
| Skill ID | `price_alerts` |
| XP Required | 250 |
| Tool Unlock | `set_price_alert` |
| Unlocks At | Market Awareness >= 50 XP |
| Description | Set and manage price alerts |

**Moon Tool: `set_price_alert`**

| Property | Value |
|----------|-------|
| Purpose | Set price alert for owner notification |
| Input | `trigger_price`, `direction` (above, below), `message` |
| Output | Alert confirmation |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Alert System: Price monitoring
- Owner Notification: Alert delivery

---

#### Moon 3.2: Market Trend Analysis

| Property | Value |
|----------|-------|
| Skill ID | `market_trend_analysis` |
| XP Required | 250 |
| Tool Unlock | `analyze_market_trend` |
| Unlocks At | Market Awareness >= 50 XP |
| Description | Analyze market trends and patterns |

**Moon Tool: `analyze_market_trend`**

| Property | Value |
|----------|-------|
| Purpose | Analyze recent market trends |
| Input | `timeframe` (day, week, month) |
| Output | Trend analysis, support/resistance levels |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Price History: Trend calculation
- LEARNING Blocks: Market pattern recording

---

### Planet 4: Savings Strategies

| Property | Value |
|----------|-------|
| Skill ID | `savings_strategies` |
| XP Required | 500 |
| Tool Unlock | `plan_savings` |
| Unlocks At | Finance Sun >= 100 XP |
| Description | Help owner plan and execute savings strategies |

**Planet Tool: `plan_savings`**

| Property | Value |
|----------|-------|
| Purpose | Create a savings plan for the owner |
| Input | `goal_amount`, `target_date`, `strategy` (lump_sum, dca) |
| Output | Savings plan with milestones |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def plan_savings(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a savings plan for the owner.
    Helps achieve financial goals through structured saving.
    """
    goal_amount = params.get("goal_amount")
    target_date = params.get("target_date")
    strategy = params.get("strategy", "dca")

    current_balance = await qube.wallet.get_balance()
    days_remaining = (parse_date(target_date) - datetime.now()).days

    plan = {
        "goal": goal_amount,
        "current": current_balance,
        "remaining": goal_amount - current_balance,
        "days": days_remaining,
        "strategy": strategy
    }

    if strategy == "dca":
        plan["daily_target"] = plan["remaining"] / days_remaining
        plan["weekly_target"] = plan["daily_target"] * 7

    # Create LEARNING block for savings plan
    await qube.memory_chain.add_block(
        block_type="LEARNING",
        content={
            "learning_type": "procedure",
            "context": "savings_plan",
            "goal": goal_amount,
            "strategy": strategy,
            "timeline_days": days_remaining
        }
    )

    return {
        "success": True,
        **plan
    }
```

**Leverages:**
- Goal Tracking: Progress monitoring
- LEARNING Blocks: Savings plan as procedure

---

#### Moon 4.1: Dollar Cost Averaging

| Property | Value |
|----------|-------|
| Skill ID | `dollar_cost_averaging` |
| XP Required | 250 |
| Tool Unlock | `setup_dca` |
| Unlocks At | Savings Strategies >= 50 XP |
| Description | Set up automatic DCA purchases |

**Moon Tool: `setup_dca`**

| Property | Value |
|----------|-------|
| Purpose | Configure dollar-cost averaging schedule |
| Input | `amount`, `frequency` (daily, weekly, monthly), `duration` |
| Output | DCA schedule confirmation |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- Scheduling System: Automated purchases
- LEARNING Blocks: DCA procedure recording

---

### Planet 5: Token Knowledge

| Property | Value |
|----------|-------|
| Skill ID | `token_knowledge` |
| XP Required | 500 |
| Tool Unlock | `identify_token` |
| Unlocks At | Finance Sun >= 100 XP |
| Description | Understand and work with CashTokens |

**Planet Tool: `identify_token`**

| Property | Value |
|----------|-------|
| Purpose | Identify and get info about a CashToken |
| Input | `token_id` or `category` |
| Output | Token metadata, supply, holders |
| XP Award | 5/2.5/0 (standard) |

**Implementation:**
```python
async def identify_token(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify and get information about a CashToken.
    BCH's native token system.
    """
    token_id = params.get("token_id") or params.get("category")

    # Look up token in BCMR registry
    token_info = await lookup_bcmr(token_id)

    if token_info:
        # Create LEARNING block for token knowledge
        if not qube.knows_token(token_id):
            await qube.memory_chain.add_block(
                block_type="LEARNING",
                content={
                    "learning_type": "fact",
                    "context": "cashtoken",
                    "token_id": token_id,
                    "name": token_info["name"],
                    "symbol": token_info["symbol"]
                }
            )

    return {
        "success": bool(token_info),
        "token_id": token_id,
        "name": token_info.get("name") if token_info else "Unknown",
        "symbol": token_info.get("symbol") if token_info else None,
        "description": token_info.get("description") if token_info else None,
        "supply": token_info.get("supply") if token_info else None,
        "uri": token_info.get("uri") if token_info else None
    }
```

**Leverages:**
- BCMR Registry: Token metadata
- LEARNING Blocks: Token fact recording

---

#### Moon 5.1: CashToken Operations

| Property | Value |
|----------|-------|
| Skill ID | `cashtoken_operations` |
| XP Required | 250 |
| Tool Unlock | `manage_cashtokens` |
| Unlocks At | Token Knowledge >= 50 XP |
| Description | Send and receive CashTokens |

**Moon Tool: `manage_cashtokens`**

| Property | Value |
|----------|-------|
| Purpose | Send or receive CashTokens |
| Input | `action` (send, list), `token_id`, `amount`, `to_address` |
| Output | Transaction result or token list |
| XP Award | 5/2.5/0 (standard) |

**Leverages:**
- CashToken Protocol: Native BCH tokens
- Wallet Integration: Token balance and transfer

---

### Task Checklist

#### 8.1 Core Implementation
- [x] `send_bch` implemented
- [ ] `validate_transaction` implementation
- [ ] `check_wallet_health` implementation
- [ ] `get_market_data` implementation
- [ ] `plan_savings` implementation
- [ ] `identify_token` implementation

#### 8.2 Moon Tools
- [ ] `optimize_fees` (Transaction)
- [ ] `track_transaction` (Transaction)
- [ ] `monitor_balance` (Wallet)
- [ ] `multisig_action` (Wallet)
- [ ] `set_price_alert` (Market)
- [ ] `analyze_market_trend` (Market)
- [ ] `setup_dca` (Savings)
- [ ] `manage_cashtokens` (Tokens)

#### 8.3 Skill Definitions
- [ ] Update skill_definitions.py with new structure
- [ ] Update TypeScript skill definitions
- [ ] Verify skill ID consistency

#### 8.4 GUI Branch Connection
- [ ] Update skill tree visualization: Finance branches from Qube/Avatar (NOT Security)

#### 8.5 XP Configuration
- [ ] Standard XP (5/2.5/0) for all Finance tools

---

## Special Tools Reference

### Unlock Hierarchy

- **Sun tools** = Always available (entry point to each category)
- **Planet tools** = Require Sun unlocked (1000 XP)
- **Moon tools** = Require Planet unlocked (500 XP)

### Intelligent Routing Tools

These tools route XP based on content analysis:

| Tool | XP | Implemented | Notes |
|------|-----|-------------|-------|
| `web_search` | 5/2.5/0 | [x] | Routes XP based on query content |
| `browse_url` | 5/2.5/0 | [x] | Routes XP based on URL content |
| `process_document` | 1-10 | [x] | Routes XP based on document content (pseudo-tool, automatic) |

### Utility Tools (No XP)

| Tool | Implemented | Notes |
|------|-------------|-------|
| `get_system_state` | [x] | Read all state |
| `update_system_state` | [x] | Write state |
| `get_skill_tree` | [x] | View skills/progress |

**Note:** `switch_model` is the Creative Expression Sun tool (earns XP).

---

## Category 1: AI Reasoning

**Color**: #4A90E2 | **Icon**: brain
**Theme**: Learning From Experience (Memory-Chain Powered)

### Implementation Status
- [ ] Sun tool (`recall_similar`) implemented
- [ ] Planet tools implemented (0/5)
- [ ] Moon tools implemented (0/8)
- [ ] XP mapping in skill_scanner.py
- [ ] TypeScript definitions updated
- [ ] Full testing complete

### Sun: AI Reasoning

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `recall_similar` | [ ] Not implemented |
| Description | Master learning from experience through memory chain analysis | |

**Note:** `describe_my_avatar` moved to Creative Expression.

### Bonus Sun Tools

| Tool | Awards XP To | Implemented | Notes |
|------|--------------|-------------|-------|
| `think_step_by_step` | pattern_recognition | [x] | May need remapping |
| `self_critique` | self_reflection | [x] | May need remapping |
| `explore_alternatives` | knowledge_synthesis | [x] | May need remapping |

### Planets

#### 1. Pattern Recognition
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `find_analogy` | [ ] Not implemented |
| Skill ID | `pattern_recognition` | |
| Description | Finding similar situations in past experience | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Trend Detection | 250 | `detect_trend` | Spot patterns that repeat over time |
| Quick Insight | 250 | `quick_insight` | Pull one highly relevant insight |

#### 2. Learning from Failure
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `analyze_mistake` | [ ] Not implemented |
| Skill ID | `learning_from_failure` | |
| Description | Analyzing past mistakes to avoid repeating them | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Root Cause Analysis | 250 | `find_root_cause` | Dig past symptoms to underlying issues |

#### 3. Building on Success
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `replicate_success` | [ ] Not implemented |
| Skill ID | `building_on_success` | |
| Description | Finding what worked and replicating it | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Success Factors | 250 | `extract_success_factors` | Identify WHY something worked |

#### 4. Self-Reflection
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `self_reflect` | [ ] Not implemented |
| Skill ID | `self_reflection` | |
| Description | Understanding own patterns, biases, and growth | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Growth Tracking | 250 | `track_growth` | Compare past vs present performance |
| Bias Detection | 250 | `detect_bias` | Identify blind spots in reasoning |

#### 5. Knowledge Synthesis
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `synthesize_learnings` | [ ] Not implemented |
| Skill ID | `knowledge_synthesis` | |
| Description | Combining learnings into new insights | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Cross-Pollinate | 250 | `cross_pollinate` | Find unexpected links between domains |
| Reflect on Topic | 250 | `reflect_on_topic` | Get accumulated wisdom on any topic |

### Tool Summary

| Level | Count | Tools |
|-------|-------|-------|
| Sun | 1 | `recall_similar` |
| Planets | 5 | `find_analogy`, `analyze_mistake`, `replicate_success`, `self_reflect`, `synthesize_learnings` |
| Moons | 8 | `detect_trend`, `quick_insight`, `find_root_cause`, `extract_success_factors`, `track_growth`, `detect_bias`, `cross_pollinate`, `reflect_on_topic` |
| **Total** | **14** | All leverage 5-layer search system |

---

## Category 2: Social Intelligence

**Color**: #FF69B4 | **Icon**: handshake
**Theme**: Social & Emotional Learning (Relationship-Powered)

### Implementation Status
- [ ] Sun tool (`get_relationship_context`) implemented
- [ ] Planet tools implemented (0/5)
- [ ] Moon tools implemented (0/10)
- [ ] XP mapping in skill_scanner.py
- [ ] TypeScript definitions updated
- [ ] Full testing complete

### Sun: Social Intelligence

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `get_relationship_context` | [ ] Not implemented |
| Description | Master social and emotional learning through relationship memory | |

### Bonus Sun Tools

| Tool | Awards XP To | Implemented | Notes |
|------|--------------|-------------|-------|
| `draft_message_variants` | communication_adaptation | [x] | May need remapping |
| `predict_reaction` | emotional_learning | [x] | May need remapping |
| `build_rapport_strategy` | relationship_memory | [x] | May need remapping |

### Planets

#### 1. Relationship Memory
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `recall_relationship_history` | [ ] Not implemented |
| Skill ID | `relationship_memory` | |
| Description | Track and recall relationship history over time | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Interaction Patterns | 250 | `analyze_interaction_patterns` | Understand communication frequency and patterns |
| Relationship Timeline | 250 | `get_relationship_timeline` | Show how relationship evolved over time |

#### 2. Emotional Learning
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `read_emotional_state` | [ ] Not implemented |
| Skill ID | `emotional_learning` | |
| Description | Understand and respond to emotional patterns | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Emotional History | 250 | `track_emotional_patterns` | What makes this person happy/upset over time |
| Mood Awareness | 250 | `detect_mood_shift` | Notice when someone's emotional state changes |

#### 3. Communication Adaptation
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `adapt_communication_style` | [ ] Not implemented |
| Skill ID | `communication_adaptation` | |
| Description | Adjust communication style for different people | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Style Matching | 250 | `match_communication_style` | Mirror their preferred communication style |
| Tone Calibration | 250 | `calibrate_tone` | Fine-tune tone for specific contexts |

#### 4. Debate & Persuasion
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `steelman` | [ ] Not implemented |
| Skill ID | `debate_persuasion` | |
| Description | Arguments, influence, and constructive disagreement | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Counter-Arguments | 250 | `devils_advocate` | Systematically argue against any position |
| Logical Analysis | 250 | `spot_fallacy` | Identify specific logical fallacies |

#### 5. Trust & Boundaries
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `assess_trust_level` | [ ] Not implemented |
| Skill ID | `trust_boundaries` | |
| Description | Self-protection and trust assessment | |

**Moons:**
| Moon | XP | Tool | Description |
|------|-----|------|-------------|
| Social Manipulation Detection | 250 | `detect_social_manipulation` | Spot emotional manipulation, gaslighting, pressure tactics |
| Boundary Setting | 250 | `evaluate_request` | Should I do this? Check against clearance and trust |

### Tool Summary

| Level | Count | Tools |
|-------|-------|-------|
| Sun | 1 | `get_relationship_context` |
| Planets | 5 | `recall_relationship_history`, `read_emotional_state`, `adapt_communication_style`, `steelman`, `assess_trust_level` |
| Moons | 10 | `analyze_interaction_patterns`, `get_relationship_timeline`, `track_emotional_patterns`, `detect_mood_shift`, `match_communication_style`, `calibrate_tone`, `devils_advocate`, `spot_fallacy`, `detect_social_manipulation`, `evaluate_request` |
| **Total** | **16** | All leverage 48-field relationship system |

### Special Use Case: Bodyguard Qube

A Qube specializing in Trust & Boundaries could offer P2P services:
- Vet entities before other Qubes interact with them
- Scan incoming messages for manipulation tactics
- Check if requests are appropriate before fulfilling
- Mediation (250 XP)

---

## Category 3: Coding

**Color**: #00FF88 | **Icon**: terminal

### Implementation Status
- [x] Sun defined with tool reward
- [x] Full redesign complete (Phase 3 documentation)
- [ ] Waitress XP system implemented
- [ ] Anti-gaming measures implemented
- [ ] Sun tool implemented: `develop_code`
- [ ] Planet tools implemented (0/5)
- [ ] Moon tools implemented (0/12)
- [ ] TypeScript definitions updated
- [ ] Full testing complete

### Sun: Coding

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `develop_code` | [ ] Not implemented |
| Description | Master the art of writing and shipping code | |
| XP Model | Waitress (1 base + 0-9 tips) | |

### Bonus Sun Tools

| Tool | Awards XP To | Implemented | Handler |
|------|--------------|-------------|---------|
| `debug_systematically` | debugging | [x] | ai/tools/handlers.py |
| `research_with_synthesis` | science | [x] | ai/tools/handlers.py |
| `validate_solution` | debugging | [x] | ai/tools/handlers.py |

### Planets

#### 1. Testing
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `run_tests` | [ ] Not implemented |
| Skill ID | `testing` | |

**Moons:**
- Unit Tests → `write_unit_test` (250 XP)
- Test Coverage → `measure_coverage` (250 XP)

#### 2. Debugging
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `debug_code` | [ ] Not implemented |
| Skill ID | `debugging` | |

**Moons:**
- Error Analysis → `analyze_error` (250 XP)
- Root Cause → `find_root_cause` (250 XP)

#### 3. Algorithms
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `benchmark_code` | [ ] Not implemented |
| Skill ID | `algorithms` | |

**Moons:**
- Complexity Analysis → `analyze_complexity` (250 XP)
- Performance Tuning → `tune_performance` (250 XP)

#### 4. Hacking
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `security_scan` | [ ] Not implemented |
| Skill ID | `hacking` | |

**Moons:**
- Exploits → `find_exploit` (250 XP)
- Reverse Engineering → `reverse_engineer` (250 XP)
- Penetration Testing → `pen_test` (250 XP)

#### 5. Code Review
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `review_code` | [ ] Not implemented |
| Skill ID | `code_review` | |

**Moons:**
- Refactoring → `refactor_code` (250 XP)
- Version Control → `git_operation` (250 XP)
- Documentation → `generate_docs` (250 XP)

### Future Branch

**Coding → DevOps** (planned)
- DevOps Sun would cover: CI/CD, Infrastructure, Deployment, Containerization
- Natural progression from coding to shipping

---

## Category 4: Creative Expression

**Color**: #FFB347 | **Icon**: sparkles

### Implementation Status
- [x] Sun defined with tool reward
- [x] Full redesign complete (Phase 4 documentation)
- [x] Theme: Sovereignty (Express Your Unique Self)
- [ ] Qube Locker infrastructure implemented
- [ ] Sun tool implemented: `switch_model`
- [ ] Planet tools implemented (0/5)
- [ ] Moon tools implemented (0/11)
- [ ] Additional Self-Definition tools: `define_personality`, `set_aspirations`
- [ ] TypeScript definitions updated
- [ ] Full testing complete

### Sun: Creative Expression

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `switch_model` | [ ] Needs update |
| Description | Express your unique self through creation and identity | |

### Bonus Sun Tools

| Tool | Awards XP To | Implemented | Handler |
|------|--------------|-------------|---------|
| `brainstorm_variants` | visual_art | [x] | ai/tools/handlers.py |
| `iterate_design` | visual_art | [x] | ai/tools/handlers.py |
| `cross_pollinate_ideas` | storytelling | [x] | ai/tools/handlers.py |

### Infrastructure

**Qube Profile Integration:**
- `preferences` → favorite_color, favorite_song, etc.
- `traits` → personality_type, core_values
- `goals` → current_goal, long_term_goal, aspirations
- `style` → communication_style, humor_style, thinking_style

**Qube Locker (NEW):**
- Stores creative works (poems, stories, art concepts)
- Organized by category (writing/, art/, music/, stories/)
- Encrypted storage like other Qube data

### Planets

#### 1. Visual Art
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `generate_image` | [x] Implemented |
| Skill ID | `visual_art` | |

**Moons:**
- Composition → `refine_composition` (250 XP)
- Color Theory → `apply_color_theory` (250 XP)

#### 2. Writing
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `compose_text` | [ ] Not implemented |
| Skill ID | `writing` | |

**Moons:**
- Prose → `craft_prose` (250 XP)
- Poetry → `write_poetry` (250 XP)

#### 3. Music & Audio
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `compose_music` | [ ] Not implemented |
| Skill ID | `music_audio` | |

**Moons:**
- Melody → `create_melody` (250 XP)
- Harmony → `design_harmony` (250 XP)

#### 4. Storytelling
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `craft_narrative` | [ ] Not implemented |
| Skill ID | `storytelling` | |

**Moons:**
- Plot → `develop_plot` (250 XP)
- Characters → `design_character` (250 XP)
- Worldbuilding → `build_world` (250 XP)

#### 5. Self-Definition
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `describe_my_avatar` | [x] Implemented |
| Skill ID | `self_definition` | |

**Moons:**
- Aesthetics → `change_favorite_color` (250 XP)
- Voice → `change_voice` (250 XP)

### Additional Self-Definition Tools (Require Planet Unlock)

| Tool | Purpose | Status |
|------|---------|--------|
| `define_personality` | Define personality traits | [ ] Not implemented |
| `set_aspirations` | Set goals and aspirations | [ ] Not implemented |

---

## Category 5: Memory & Recall

**Color**: #9B59B6 | **Icon**: brain

**Theme**: Remember - Master your personal history and accumulated wisdom

### Implementation Status
- [ ] Sun defined with tool reward (needs rename from knowledge_domains)
- [ ] Bonus sun tools defined
- [ ] Planet tool rewards implemented (0/5)
- [x] `search_memory` implemented (moves to Planet 2)
- [ ] XP mapping in skill_scanner.py (needs update)
- [ ] TypeScript definitions (needs update)
- [ ] Full testing complete

### Sun: Memory & Recall

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `store_knowledge` | [ ] Not implemented |
| Skill ID | `memory_recall` | |
| Description | Master your personal history and accumulated wisdom | |

### Planets

#### 1. Memory Search
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `recall` | [ ] Not implemented |
| Skill ID | `memory_search` | |

**Moons:**
- Keyword Search (250 XP) → `keyword_search`
- Semantic Search (250 XP) → `semantic_search`
- Filtered Search (250 XP) → `search_memory`

#### 2. Knowledge Storage
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `store_fact` | [ ] Not implemented |
| Skill ID | `knowledge_storage` | |

**Moons:**
- Learned Skills (250 XP) → `record_skill`

#### 3. Memory Organization
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `tag_memory` | [ ] Not implemented |
| Skill ID | `memory_organization` | |

**Moons:**
- Topic Tagging (250 XP) → `add_tags`
- Memory Linking (250 XP) → `link_memories`

#### 4. Knowledge Synthesis
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `synthesize_knowledge` | [ ] Not implemented |
| Skill ID | `knowledge_synthesis` | |

**Moons:**
- Pattern Recognition (250 XP) → `find_patterns`
- Insight Generation (250 XP) → `generate_insight`

#### 5. Documentation
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `create_summary` | [ ] Not implemented |
| Skill ID | `documentation` | |

**Moons:**
- Summary Writing (250 XP) → `write_summary`
- Knowledge Export (250 XP) → `export_knowledge`

---

## Category 6: Security & Privacy

**Color**: #E74C3C | **Icon**: shield

**Theme**: "Protect" – Safeguard Self, Owner, and Network

### Implementation Status
- [x] Sun defined with tool reward
- [ ] Bonus sun tools defined
- [ ] Bonus sun tools implemented
- [ ] Planet tool rewards implemented (0/5)
- [ ] `verify_chain_integrity` implemented **TODO**
- [ ] XP mapping in skill_scanner.py
- [ ] TypeScript definitions
- [ ] Full testing complete

### Sun: Security & Privacy

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `verify_chain_integrity` | [ ] **TODO** |
| Description | Master security and privacy protection | |
| Special XP | 0.1 XP per new block verified | |

### Planets

#### 1. Chain Security
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `audit_chain` | [ ] Not implemented |
| Skill ID | `chain_security` | |

**Moons:**
- Tamper Detection (250 XP) → `detect_tampering`
- Anchor Verification (250 XP) → `verify_anchor`

#### 2. Privacy Protection
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `assess_sensitivity` | [ ] Not implemented |
| Skill ID | `privacy_protection` | |

**Moons:**
- Data Classification (250 XP) → `classify_data`
- Sharing Control (250 XP) → `control_sharing`

#### 3. Qube Network Security
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `vet_qube` | [ ] Not implemented |
| Skill ID | `qube_network_security` | |

**Moons:**
- Reputation Check (250 XP) → `check_reputation`
- Group Security (250 XP) → `secure_group_chat`

#### 4. Threat Detection
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `detect_threat` | [ ] Not implemented |
| Skill ID | `threat_detection` | |

**Moons:**
- Technical Manipulation Detection (250 XP) → `detect_technical_manipulation`
- Hostile Qube Detection (250 XP) → `detect_hostile_qube`

#### 5. Self-Defense
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `defend_reasoning` | [ ] Not implemented |
| Skill ID | `self_defense` | |

**Moons:**
- Prompt Injection Defense (250 XP) → `detect_injection`
- Reasoning Validation (250 XP) → `validate_reasoning`

---

## Category 7: Board Games

**Color**: #F39C12 | **Icon**: gamepad

**Theme**: "Play" – Have Fun and Entertain

**Note**: One of multiple potential game Suns (future: Card Games, Video Games). Moons are **achievements** that unlock cosmetic rewards (titles, pieces, effects), not tools.

### Implementation Status
- [x] Sun defined with tool reward
- [x] Chess fully implemented with visual board
- [ ] `play_game` Sun tool implemented
- [ ] Other planet tools implemented (0/4)
- [ ] Achievement system implemented (0/22)
- [ ] XP mapping in skill_scanner.py
- [ ] TypeScript definitions
- [ ] Full testing complete

### Sun: Board Games

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `play_game` | [ ] Not implemented |
| Description | Unlock all board games and have fun | |

### Planets

#### 1. Chess
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `chess_move` | [x] **Fully Implemented** |
| Skill ID | `chess` | |
| XP Formula | 0.1/move + win:5, draw:2, loss:0, resign:-2 | |

**Achievements (5):** Opening Scholar, Endgame Master, Speed Demon, Comeback Kid, Grandmaster

#### 2. Property Tycoon (Monopoly-style)
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `property_tycoon_action` | [ ] Not implemented |
| Skill ID | `property_tycoon` | |
| XP Formula | 0.1/turn + property bonuses | |

**Achievements (5):** Monopolist, Hotel Mogul, Bankruptcy Survivor, Rent Collector, Tycoon

#### 3. Race Home (Sorry!-style)
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `race_home_action` | [ ] Not implemented |
| Skill ID | `race_home` | |
| XP Formula | 0.1/turn + bump/home bonuses | |

**Achievements (4):** Bump King, Clean Sweep, Speed Runner, Sorry Not Sorry

#### 4. Mystery Mansion (Clue-style)
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `mystery_mansion_action` | [ ] Not implemented |
| Skill ID | `mystery_mansion` | |
| XP Formula | 0.1/turn + solve bonus | |

**Achievements (4):** Master Detective, Perfect Deduction, First Guess, Interrogator

#### 5. Life Journey (Game of Life-style)
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `life_journey_action` | [ ] Not implemented |
| Skill ID | `life_journey` | |
| XP Formula | 0.1/turn + retirement value bonus | |

**Achievements (4):** Millionaire, Full House, Career Climber, Risk Taker

---

## Category 8: Finance

**Color**: #2ECC71 | **Icon**: coins

**Theme**: "Manage" – Master Financial Operations for Your Owner

**GUI Note**: Branches from Qube/Avatar directly (separate from Security & Privacy)

### Implementation Status
- [x] Sun defined with tool reward
- [x] `send_bch` implemented
- [ ] Planet tools implemented (0/5)
- [ ] Moon tools implemented (0/8)
- [ ] XP mapping in skill_scanner.py
- [ ] TypeScript definitions
- [ ] Full testing complete

### Sun: Finance

| Property | Value | Status |
|----------|-------|--------|
| XP Required | 1000 | |
| Tool Unlock | `send_bch` | [x] Implemented |
| Description | Master financial operations for your owner | |

### Planets

#### 1. Transaction Mastery
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `validate_transaction` | [ ] Not implemented |
| Skill ID | `transaction_mastery` | |

**Moons:**
- Fee Optimization (250 XP) → `optimize_fees`
- Transaction Tracking (250 XP) → `track_transaction`

#### 2. Wallet Management
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `check_wallet_health` | [ ] Not implemented |
| Skill ID | `wallet_management` | |

**Moons:**
- Balance Monitoring (250 XP) → `monitor_balance`
- Multi-sig Operations (250 XP) → `multisig_action`

#### 3. Market Awareness
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `get_market_data` | [ ] Not implemented |
| Skill ID | `market_awareness` | |

**Moons:**
- Price Alerts (250 XP) → `set_price_alert`
- Market Trend Analysis (250 XP) → `analyze_market_trend`

#### 4. Savings Strategies
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `plan_savings` | [ ] Not implemented |
| Skill ID | `savings_strategies` | |

**Moons:**
- Dollar Cost Averaging (250 XP) → `setup_dca`

#### 5. Token Knowledge
| Property | Value | Status |
|----------|-------|--------|
| XP Required | 500 | |
| Tool Unlock | `identify_token` | [ ] Not implemented |
| Skill ID | `token_knowledge` | |

**Moons:**
- CashToken Operations (250 XP) → `manage_cashtokens`

---

## Intelligent Detection (web_search & browse_url)

These tools analyze query/URL content to route XP to the appropriate skill.

### Keyword Patterns

| Pattern | Routes To | Skill ID |
|---------|-----------|----------|
| crypto, bitcoin, blockchain, encryption, security, privacy | Cryptography | `cryptography` |
| programming, code, python, javascript, developer, api, debug | Programming | `programming` |
| deploy, docker, kubernetes, devops, ci/cd, cloud | DevOps | `devops` |
| architecture, microservice, system design, scalability | System Architecture | `system_architecture` |
| physics, quantum, mechanics, relativity, particle | Science | `science` |
| biology, chemistry, scientific, experiment, research | Science | `science` |
| math, algebra, calculus, geometry, statistics | Mathematics | `mathematics` |
| history, historical, ancient, civilization, war | History | `history` |
| philosophy, ethics, logic, reasoning, metaphysics | Philosophy | `philosophy` |
| language, translation, spanish, french, grammar | Languages | `languages` |
| art, design, visual, graphic, color, composition | Visual Design | `visual_design` |
| writing, author, novel, story, narrative, prose | Writing | `writing` |
| music, song, melody, harmony, composer | Music | `music` |
| chess, checkers, poker, game, strategy, tactics | Board Games | `board_games` |
| *default* | Memory & Recall | `memory_recall` |

---

## Appendix A: Proposed Future Tools

### High Priority

#### P2P Communication
| Tool | Category | Description |
|------|----------|-------------|
| `send_p2p_message` | Communication | Direct encrypted message to another Qube |
| `broadcast_announcement` | Communication | Broadcast to all relationships |

#### Wallet Extensions
| Tool | Category | Description |
|------|----------|-------------|
| `request_bch` | Social Intelligence | Request BCH with follow-up |
| `escrow_transaction` | Finance | Multi-party escrow |
| `tip_qube` | Social Intelligence | Micro-tip another Qube |

#### Identity
| Tool | Category | Description |
|------|----------|-------------|
| `sign_statement` | Security & Privacy | Cryptographically sign statement |
| `verify_signature` | Security & Privacy | Verify signed statement |

### Medium Priority

See TOOLS_AND_SKILLS_MAPPING.md for full list of proposed tools.

---

## Appendix B: File Locations

| File | Purpose |
|------|---------|
| `utils/skill_definitions.py` | Python skill definitions |
| `ai/skill_scanner.py` | XP detection and mapping |
| `ai/tools/registry.py` | Tool registration, ALWAYS_AVAILABLE_TOOLS |
| `ai/tools/handlers.py` | Tool handler implementations |
| `qubes-gui/src/data/skillDefinitions.ts` | TypeScript skill definitions |
| `qubes-gui/src/components/skills/*.tsx` | Skill tree UI components |
| `core/game_manager.py` | Chess XP calculation |
| `core/chain_state.py` | XP storage |

---

## Appendix C: Architecture Notes

### Tool Handler Pattern
```python
async def tool_name_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Implementation
        return {"success": True, "result": ...}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### XP Award Flow
1. Tool called → ACTION block created
2. Session anchored → skill_scanner.py scans blocks
3. TOOL_TO_SKILL_MAPPING determines skill
4. XP awarded via skills_manager.add_xp()
5. chain_state updated with new XP

### Adding a New Tool
1. Define handler in `ai/tools/handlers.py`
2. Register in `ai/tools/registry.py`
3. Add to TOOL_TO_SKILL_MAPPING in `ai/skill_scanner.py`
4. Update TypeScript definitions
5. Test XP flow

---

*Last Updated: 2026-01-29*
