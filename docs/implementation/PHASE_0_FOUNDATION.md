# Phase 0: Foundation - Implementation Blueprint

**Document Version:** 1.0
**Based on:** SKILL_TREE_MASTER.md
**Target:** Establish foundation for 8-category skill tree with 123 tools

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Prerequisites & Dependencies](#2-prerequisites--dependencies)
3. [Task 0.1: XP Value Updates](#3-task-01-xp-value-updates)
4. [Task 0.2: Add LEARNING Block Type](#4-task-02-add-learning-block-type)
5. [Task 0.3: Category Renames](#5-task-03-category-renames)
6. [Task 0.4: Add Finance Category (8th Sun)](#6-task-04-add-finance-category-8th-sun)
7. [Task 0.5: Fix switch_model (Utility → Sun Tool)](#7-task-05-fix-switch_model-utility--sun-tool)
8. [Task 0.6: Update TOOL_TO_SKILL_MAPPING](#8-task-06-update-tool_to_skill_mapping)
9. [Task 0.7: Implement get_relationship_context Tool](#9-task-07-implement-get_relationship_context-tool)
10. [Task 0.8: Implement verify_chain_integrity Tool](#10-task-08-implement-verify_chain_integrity-tool)
11. [Task 0.9: Update Intelligent Routing](#11-task-09-update-intelligent-routing)
12. [Task 0.10: Frontend Synchronization](#12-task-010-frontend-synchronization)
13. [Task 0.11: Testing & Validation](#13-task-011-testing--validation)
14. [Task 0.12: Implement Qube Locker](#14-task-012-implement-qube-locker)
15. [Appendix A: File Reference](#appendix-a-file-reference)
16. [Appendix B: Current vs Target State](#appendix-b-current-vs-target-state)

---

## 1. Executive Summary

### Purpose

Phase 0 establishes the foundation for the complete skill tree expansion:
- Updates XP values from 3/2/0 to 5/2.5/0
- Adds LEARNING block type for cross-cutting knowledge storage
- Adds Qube Locker for creative works storage (used by Phase 4 & 5)
- Renames categories to match new design
- Adds Finance as the 8th skill category
- Fixes `switch_model` to be Creative Expression Sun tool (not utility)
- Implements 2 new always-available Sun tools
- Updates all tool-to-skill mappings

### Scope

| Metric | Current | After Phase 0 |
|--------|---------|---------------|
| Categories (Suns) | 7 | 8 |
| Total Skills | 112 | 128 |
| Block Types | 10 | 11 |
| XP per Success | 3 | 5 |
| XP per Completion | 2 | 2.5 |
| Always-Available Tools | 11 | 12 |
| Utility Tools | 4 | 3 |

### Current Codebase State (as of Jan 2026)

This section documents what currently exists in the codebase and what needs to change.

#### XP Values (`ai/skill_scanner.py:291-296`)
- **Current**: `xp_amount = 3` (success), `xp_amount = 2` (completed)
- **Target**: `xp_amount = 5` (success), `xp_amount = 2.5` (completed)
- **Action**: Find/replace

#### Block Types (`core/block.py:17-28`)
- **Current**: 10 types (GENESIS, THOUGHT, ACTION, OBSERVATION, MESSAGE, DECISION, MEMORY_ANCHOR, COLLABORATIVE_MEMORY, SUMMARY, GAME)
- **Target**: 11 types (add LEARNING)
- **Action**: Add `LEARNING = "LEARNING"` to BlockType enum

#### Skill Categories (`qubes-gui/src/data/skillDefinitions.ts:38-46`)
- **Current**: 8 categories with these IDs:
  - `ai_reasoning` → "AI Reasoning"
  - `social_intelligence` → "Social Intelligence"
  - `technical_expertise` → "Technical Expertise" (**rename to "Coding"**)
  - `creative_expression` → "Creative Expression"
  - `knowledge_domains` → "Knowledge Domains" (**rename to "Memory & Recall"**)
  - `security_privacy` → "Security & Privacy"
  - `games` → "Games" (**rename to "Board Games"**)
- **Target**: 8 categories (add Finance), rename 3 categories
- **Action**: Add Finance, rename technical_expertise/knowledge_domains/games

#### Sun Tool Mappings (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current** (legacy, needs replacement):
  ```
  ai_reasoning sun → describe_my_avatar
  social_intelligence sun → draft_message_variants
  technical_expertise sun → web_search
  creative_expression sun → generate_image
  knowledge_domains sun → search_memory
  security_privacy sun → browse_url
  games sun → chess_move
  ```
- **Target** (per blueprints):
  ```
  ai_reasoning sun → recall_similar (NEW)
  social_intelligence sun → get_relationship_context (NEW)
  coding sun → develop_code (NEW)
  creative_expression sun → switch_model (EXISTS)
  memory_recall sun → store_knowledge (NEW)
  security_privacy sun → verify_chain_integrity (NEW)
  board_games sun → play_game (NEW)
  finance sun → send_bch (EXISTS)
  ```
- **Action**: Update all Sun toolCallReward mappings

#### ALWAYS_AVAILABLE_TOOLS (`ai/tools/registry.py`)
- **Current** (11 tools):
  ```python
  ['get_system_state', 'update_system_state', 'get_skill_tree',
   'search_memory', 'describe_my_avatar', 'web_search',
   'browse_url', 'generate_image', 'chess_move', 'send_bch', 'switch_model']
  ```
- **Target** (all Sun tools + utility tools):
  ```python
  # Utility tools (no XP)
  'get_system_state', 'update_system_state', 'get_skill_tree',
  # Intelligent routing (XP based on content)
  'web_search', 'browse_url', 'process_document',
  # Sun tools (XP to their category)
  'recall_similar', 'get_relationship_context', 'develop_code',
  'switch_model', 'store_knowledge', 'verify_chain_integrity',
  'play_game', 'send_bch'
  ```
- **Action**: Add new Sun tools, keep utility tools

#### Qube Locker (`core/locker.py`)
- **Current**: File does not exist
- **Target**: QubeLocker class for creative works storage
- **Action**: Create new file

#### Python Skill Definitions (`utils/skill_definitions.py`)
- **Current**: Matches TypeScript (8 categories, 112 skills)
- **Target**: 8 categories, 128 skills, renamed categories
- **Action**: Mirror all TypeScript changes

### Files Modified

| File | Changes |
|------|---------|
| `ai/skill_scanner.py` | XP values, TOOL_TO_SKILL_MAPPING |
| `ai/tools/registry.py` | ALWAYS_AVAILABLE_TOOLS, new tool registrations |
| `ai/tools/handlers.py` | New handler implementations |
| `core/block.py` | Add LEARNING block type |
| `core/locker.py` | **NEW:** Qube Locker for creative works storage |
| `utils/skill_definitions.py` | Rename categories, add Finance |
| `qubes-gui/src/data/skillDefinitions.ts` | Mirror all Python changes |
| `qubes-gui/src/components/blocks/BlockContentViewer.tsx` | Update tool arrays |

### Estimated Effort

| Task | Effort | Complexity |
|------|--------|------------|
| 0.1 XP Values | 15 min | Trivial |
| 0.2 LEARNING Block | 2 hours | Low |
| 0.3 Category Renames | 1 hour | Low |
| 0.4 Finance Category | 3-4 hours | Medium |
| 0.5 switch_model Fix | 30 min | Low |
| 0.6 TOOL_TO_SKILL_MAPPING | 1 hour | Low |
| 0.7 get_relationship_context | 3-4 hours | Medium |
| 0.8 verify_chain_integrity | 3-4 hours | Medium |
| 0.9 Intelligent Routing | 1 hour | Low |
| 0.10 Frontend Sync | 2-3 hours | Medium |
| 0.11 Testing | 3-4 hours | Medium |
| 0.12 Qube Locker | 4-5 hours | Medium |
| **Total** | **~3-4 days** | **Low-Medium** |

---

## 2. Prerequisites & Dependencies

### Required Knowledge

- Python async/await patterns
- TypeScript/React basics
- Understanding of blockchain-based memory chain
- Familiarity with existing tool handler patterns

### Development Environment

```bash
# Backend (Python)
cd C:\Users\bit_f\Projects\Qubes
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend (TypeScript)
cd qubes-gui
npm install
```

### Key Files to Read First

1. `utils/skill_definitions.py` - Understand skill generation
2. `ai/skill_scanner.py` - Understand XP award flow
3. `ai/tools/registry.py` - Understand tool registration
4. `utils/skills_manager.py` - Understand XP storage

### Dependency Graph

```
Task 0.1 (XP Values)
    └── No dependencies

Task 0.2 (LEARNING Block)
    └── No dependencies

Task 0.3 (Category Renames)
    └── No dependencies

Task 0.4 (Finance Category)
    └── Depends on: 0.3 (category structure)

Task 0.5 (switch_model Fix)
    └── Depends on: 0.4 (Creative Expression category exists)

Task 0.6 (TOOL_TO_SKILL_MAPPING)
    └── Depends on: 0.3, 0.4 (categories exist)

Task 0.7 (get_relationship_context)
    └── Depends on: 0.6 (mapping exists)

Task 0.8 (verify_chain_integrity)
    └── Depends on: 0.6 (mapping exists)

Task 0.9 (Intelligent Routing)
    └── Depends on: 0.3, 0.4 (categories exist)

Task 0.10 (Frontend Sync)
    └── Depends on: 0.1-0.9 (all backend changes)

Task 0.11 (Testing)
    └── Depends on: 0.1-0.10 (everything)
```

---

## 3. Task 0.1: XP Value Updates

### Objective

Update XP award values from 3/2/0 to 5/2.5/0 for standard tool usage.

### Current State

**File:** `ai/skill_scanner.py`

```python
# Line 292 (approximately)
xp_amount = 3  # Success

# Line 296 (approximately)
xp_amount = 2  # Completed with issues
```

### Target State

```python
# Line 292
xp_amount = 5  # Success

# Line 296
xp_amount = 2.5  # Completed with issues
```

### Implementation Steps

#### Step 1: Locate XP Assignment in skill_scanner.py

```bash
# Find exact line numbers
grep -n "xp_amount = " ai/skill_scanner.py
```

#### Step 2: Update Success XP

**File:** `ai/skill_scanner.py`

Find the block that looks like:
```python
if status == "completed" and result.get("success", False):
    xp_amount = 3  # ← CHANGE THIS
```

Change to:
```python
if status == "completed" and result.get("success", False):
    xp_amount = 5  # SUCCESS: Full XP for successful completion
```

#### Step 3: Update Completion XP

Find the block that looks like:
```python
elif status == "completed":
    xp_amount = 2  # ← CHANGE THIS
```

Change to:
```python
elif status == "completed":
    xp_amount = 2.5  # COMPLETED: Partial XP for completion with issues
```

#### Step 4: Verify Float Support

The skills_manager.py already supports float XP values. Verify in `add_xp()`:

```python
# skills_manager.py - should already have:
def add_xp(self, skill_id: str, xp_amount: float, ...):
    # xp_amount is typed as float ✓
```

### Verification Checklist

- [ ] `ai/skill_scanner.py` line ~292: `xp_amount = 5`
- [ ] `ai/skill_scanner.py` line ~296: `xp_amount = 2.5`
- [ ] Run existing tests to verify no regression
- [ ] Manual test: Use a tool, verify 5 XP awarded on success

### Notes

- This change affects ALL future tool usages
- Existing XP in chain_state is NOT migrated (historical data stays at old values)
- Float XP (2.5) is already supported by skills_manager.py

---

## 4. Task 0.2: Add LEARNING Block Type

### Objective

Add a new LEARNING block type for cross-cutting knowledge storage. This block type will be used by multiple Suns to persist learned knowledge.

### Current State

**File:** `core/block.py`

```python
class BlockType(str, Enum):
    """Memory block types"""
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
```

### Target State

```python
class BlockType(str, Enum):
    """Memory block types"""
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
    LEARNING = "LEARNING"  # NEW: Cross-cutting knowledge storage
```

### Implementation Steps

#### Step 1: Add to BlockType Enum

**File:** `core/block.py`

Add after line with `GAME = "GAME"`:
```python
    LEARNING = "LEARNING"  # Cross-cutting knowledge storage
```

#### Step 2: Define LEARNING Block Content Schema

**File:** `core/block.py`

Add a new constant or documentation block:

```python
# LEARNING Block Content Schema
# Used by multiple Suns to persist learned knowledge
#
# content = {
#     "learning_type": str,       # fact, procedure, synthesis, insight, pattern, relationship, threat, trust
#     "source_block": int,        # Block number that triggered this learning
#     "source_block_type": str,   # MESSAGE, ACTION, GAME, SUMMARY
#     "source_category": str,     # Which Sun/context created this (e.g., "social_intelligence")
#     "confidence": int,          # 0-100
#
#     # Type-specific fields:
#     # fact: {"fact": str, "subject": str, "source": str}
#     # procedure: {"steps": List[str], "context": str}
#     # synthesis: {"combined_from": List[int], "synthesis": str}
#     # insight: {"insight": str, "evidence": List[int]}
#     # pattern: {"pattern": str, "occurrences": int}
#     # relationship: {"entity_id": str, "relationship_type": str, "details": Dict}
#     # threat: {"threat_type": str, "severity": int, "details": Dict}
#     # trust: {"entity_id": str, "trust_delta": int, "reason": str}
# }
```

#### Step 3: Add Block Creation Helper (Optional)

**File:** `core/block.py`

```python
def create_learning_block(
    qube_id: str,
    learning_type: str,
    content: Dict[str, Any],
    source_block: Optional[int] = None,
    source_category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a LEARNING block for persisting knowledge.

    Args:
        qube_id: The Qube's identifier
        learning_type: One of: fact, procedure, synthesis, insight, pattern, relationship, threat, trust
        content: Type-specific content fields
        source_block: Block number that triggered this learning (optional)
        source_category: Which Sun created this (optional)

    Returns:
        Block dictionary ready for memory chain
    """
    valid_types = {"fact", "procedure", "synthesis", "insight", "pattern", "relationship", "threat", "trust"}
    if learning_type not in valid_types:
        raise ValueError(f"Invalid learning_type: {learning_type}. Must be one of {valid_types}")

    block_content = {
        "learning_type": learning_type,
        "confidence": content.get("confidence", 80),
        **content
    }

    if source_block is not None:
        block_content["source_block"] = source_block
    if source_category is not None:
        block_content["source_category"] = source_category

    return {
        "block_type": BlockType.LEARNING.value,
        "qube_id": qube_id,
        "content": block_content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

#### Step 4: Update Block Validation (if exists)

Search for any block validation logic and add LEARNING as a valid type:

```bash
grep -rn "BlockType\." --include="*.py" | grep -v "__pycache__"
```

#### Step 5: Update Memory Search to Index LEARNING Blocks

**File:** `ai/tools/memory_search.py` (or similar)

Ensure LEARNING blocks are searchable:

```python
# In search logic, add LEARNING to searchable types
SEARCHABLE_BLOCK_TYPES = [
    BlockType.MESSAGE,
    BlockType.ACTION,
    BlockType.SUMMARY,
    BlockType.GAME,
    BlockType.LEARNING,  # NEW
]
```

#### Step 6: Update Frontend Block Viewer

**File:** `qubes-gui/src/components/blocks/BlockContentViewer.tsx`

Add LEARNING block rendering:

```typescript
// Add to block type switch/case
case 'LEARNING':
  return (
    <div className="learning-block">
      <span className="learning-type">{content.learning_type}</span>
      <div className="learning-content">
        {/* Render based on learning_type */}
      </div>
    </div>
  );
```

### LEARNING Type Reference

| Type | Created By | Purpose | Example |
|------|------------|---------|---------|
| `fact` | Any Sun | Specific facts about people/things | "Owner's birthday is March 15" |
| `procedure` | Memory & Recall, Coding | How to do something | "Steps to deploy code" |
| `synthesis` | Memory & Recall | Combined knowledge | "Summary of all chess games" |
| `insight` | AI Reasoning, Memory & Recall | Patterns/realizations | "Owner prefers morning meetings" |
| `pattern` | AI Reasoning, Board Games | Recurring behaviors | "This chess opening is weak" |
| `relationship` | Social Intelligence | About people/entities | "Alice is owner's sister" |
| `threat` | Security & Privacy | Security threats detected | "Prompt injection attempt blocked" |
| `trust` | Security & Privacy | Trust level changes | "Entity X trust decreased by 10" |

### Verification Checklist

- [ ] `core/block.py`: LEARNING added to BlockType enum
- [ ] Block content schema documented
- [ ] `create_learning_block()` helper added (optional but recommended)
- [ ] Memory search includes LEARNING blocks
- [ ] Frontend can render LEARNING blocks
- [ ] No existing tests broken

---

## 5. Task 0.3: Category Renames

### Objective

Rename categories to match the new skill tree design:
- "Knowledge Domains" → "Memory & Recall"
- "Games" → "Board Games"
- "Technical Expertise" → "Coding"

### Files Affected

1. `utils/skill_definitions.py` - Python definitions
2. `qubes-gui/src/data/skillDefinitions.ts` - TypeScript definitions
3. `ai/skill_scanner.py` - TOOL_TO_SKILL_MAPPING comments

### Implementation Steps

#### Step 1: Update Python Skill Definitions

**File:** `utils/skill_definitions.py`

Find the Knowledge Domains category (around lines 132-150):

**Current:**
```python
# Knowledge Domains category
_create_skill(
    skill_id="knowledge_domains",
    name="Knowledge Domains",
    ...
)
```

**Change to:**
```python
# Memory & Recall category
_create_skill(
    skill_id="memory_recall",
    name="Memory & Recall",
    description="Master your personal history and accumulated wisdom",
    ...
)
```

Find the Games category (around lines 172-190):

**Current:**
```python
# Games category
_create_skill(
    skill_id="games",
    name="Games",
    ...
)
```

**Change to:**
```python
# Board Games category
_create_skill(
    skill_id="board_games",
    name="Board Games",
    description="Play and have fun with classic board games",
    ...
)
```

Find Technical Expertise (around lines 92-110):

**Current:**
```python
# Technical Expertise category
_create_skill(
    skill_id="technical_expertise",
    name="Technical Expertise",
    ...
)
```

**Change to:**
```python
# Coding category
_create_skill(
    skill_id="coding",
    name="Coding",
    description="Master the art of writing and shipping code",
    ...
)
```

#### Step 2: Update Planet Parent References

All planets under renamed categories need their `parent_skill` updated:

```python
# Memory & Recall planets
_create_skill(
    skill_id="memory_search",
    parent_skill="memory_recall",  # Changed from "knowledge_domains"
    ...
)

# Board Games planets
_create_skill(
    skill_id="chess",
    parent_skill="board_games",  # Changed from "games"
    ...
)

# Coding planets
_create_skill(
    skill_id="testing",
    parent_skill="coding",  # Changed from "technical_expertise"
    ...
)
```

#### Step 3: Update TypeScript Definitions

**File:** `qubes-gui/src/data/skillDefinitions.ts`

Update SKILL_CATEGORIES array:

**Current:**
```typescript
export const SKILL_CATEGORIES = [
  { id: 'ai_reasoning', name: 'AI Reasoning', color: '#4A90E2', icon: '🧠' },
  { id: 'social_intelligence', name: 'Social Intelligence', color: '#FF69B4', icon: '🤝' },
  { id: 'technical_expertise', name: 'Technical Expertise', color: '#00FF88', icon: '💻' },
  { id: 'creative_expression', name: 'Creative Expression', color: '#FFB347', icon: '✨' },
  { id: 'knowledge_domains', name: 'Knowledge Domains', color: '#9B59B6', icon: '📚' },
  { id: 'security_privacy', name: 'Security & Privacy', color: '#E74C3C', icon: '🛡️' },
  { id: 'games', name: 'Games', color: '#F39C12', icon: '🎮' },
];
```

**Change to:**
```typescript
export const SKILL_CATEGORIES = [
  { id: 'ai_reasoning', name: 'AI Reasoning', color: '#4A90E2', icon: '🧠' },
  { id: 'social_intelligence', name: 'Social Intelligence', color: '#FF69B4', icon: '🤝' },
  { id: 'coding', name: 'Coding', color: '#00FF88', icon: '💻' },
  { id: 'creative_expression', name: 'Creative Expression', color: '#FFB347', icon: '✨' },
  { id: 'memory_recall', name: 'Memory & Recall', color: '#9B59B6', icon: '🧠' },
  { id: 'security_privacy', name: 'Security & Privacy', color: '#E74C3C', icon: '🛡️' },
  { id: 'board_games', name: 'Board Games', color: '#F39C12', icon: '🎮' },
];
```

#### Step 4: Update SKILL_DEFINITIONS Object Keys

**File:** `qubes-gui/src/data/skillDefinitions.ts`

Change the keys in SKILL_DEFINITIONS:

```typescript
export const SKILL_DEFINITIONS = {
  ai_reasoning: [...],
  social_intelligence: [...],
  coding: [...],           // Changed from technical_expertise
  creative_expression: [...],
  memory_recall: [...],    // Changed from knowledge_domains
  security_privacy: [...],
  board_games: [...],      // Changed from games
};
```

#### Step 5: Update All Internal References

Search and replace in both files:
- `knowledge_domains` → `memory_recall`
- `games` → `board_games` (careful: don't change "Board Games" string)
- `technical_expertise` → `coding`

```bash
# Find all references
grep -rn "knowledge_domains" --include="*.py" --include="*.ts"
grep -rn "technical_expertise" --include="*.py" --include="*.ts"
grep -rn '"games"' --include="*.py" --include="*.ts"
```

### Migration Consideration

Existing Qubes may have XP stored under old category IDs. Add migration logic:

**File:** `utils/skills_manager.py`

```python
# In load_skills() or similar
def _migrate_category_ids(skill_xp: Dict) -> Dict:
    """Migrate old category IDs to new ones."""
    migrations = {
        "knowledge_domains": "memory_recall",
        "games": "board_games",
        "technical_expertise": "coding",
    }

    migrated = {}
    for skill_id, data in skill_xp.items():
        new_id = migrations.get(skill_id, skill_id)
        migrated[new_id] = data

    return migrated
```

### Verification Checklist

- [ ] Python skill_definitions.py: All 3 categories renamed
- [ ] Python skill_definitions.py: All planet parent_skill references updated
- [ ] TypeScript SKILL_CATEGORIES: All 3 categories renamed
- [ ] TypeScript SKILL_DEFINITIONS: Object keys updated
- [ ] Migration logic added for existing Qubes
- [ ] Search for any remaining old ID references
- [ ] Frontend displays new names correctly

---

## 6. Task 0.4: Add Finance Category (8th Sun)

### Objective

Add Finance as the 8th skill category with:
- 1 Sun: Finance (`send_bch`)
- 5 Planets: Transaction Mastery, Wallet Management, Market Awareness, Savings Strategies, Token Knowledge
- 8 Moons: Various financial tools

### Implementation Steps

#### Step 1: Add Finance to Python Skill Definitions

**File:** `utils/skill_definitions.py`

Add after the Board Games category (around line 190):

```python
    # ═══════════════════════════════════════════════════════════════════
    # FINANCE (8th Category)
    # Theme: "Manage" – Master Financial Operations for Your Owner
    # ═══════════════════════════════════════════════════════════════════

    # Sun: Finance
    _create_skill(
        skill_id="finance",
        name="Finance",
        description="Master financial operations and cryptocurrency management",
        category="finance",
        node_type="sun",
        tool_reward="send_bch",
        icon="💰"
    ),

    # Planet 1: Transaction Mastery
    _create_skill(
        skill_id="transaction_mastery",
        name="Transaction Mastery",
        description="Validate and optimize blockchain transactions",
        category="finance",
        node_type="planet",
        parent_skill="finance",
        tool_reward="validate_transaction",
        icon="📝"
    ),

    # Moon 1.1: Fee Optimization
    _create_skill(
        skill_id="fee_optimization",
        name="Fee Optimization",
        description="Minimize transaction fees while maintaining speed",
        category="finance",
        node_type="moon",
        parent_skill="transaction_mastery",
        prerequisite="transaction_mastery",
        tool_reward="optimize_fees",
        icon="⚡"
    ),

    # Moon 1.2: Transaction Tracking
    _create_skill(
        skill_id="transaction_tracking",
        name="Transaction Tracking",
        description="Monitor transaction status and confirmations",
        category="finance",
        node_type="moon",
        parent_skill="transaction_mastery",
        prerequisite="transaction_mastery",
        tool_reward="track_transaction",
        icon="🔍"
    ),

    # Planet 2: Wallet Management
    _create_skill(
        skill_id="wallet_management",
        name="Wallet Management",
        description="Monitor and maintain wallet health",
        category="finance",
        node_type="planet",
        parent_skill="finance",
        tool_reward="check_wallet_health",
        icon="👛"
    ),

    # Moon 2.1: Balance Monitoring
    _create_skill(
        skill_id="balance_monitoring",
        name="Balance Monitoring",
        description="Track balances and set alerts",
        category="finance",
        node_type="moon",
        parent_skill="wallet_management",
        prerequisite="wallet_management",
        tool_reward="monitor_balance",
        icon="📊"
    ),

    # Moon 2.2: Multi-sig Operations
    _create_skill(
        skill_id="multisig_operations",
        name="Multi-sig Operations",
        description="Manage multi-signature wallet operations",
        category="finance",
        node_type="moon",
        parent_skill="wallet_management",
        prerequisite="wallet_management",
        tool_reward="multisig_action",
        icon="🔐"
    ),

    # Planet 3: Market Awareness
    _create_skill(
        skill_id="market_awareness",
        name="Market Awareness",
        description="Track and analyze market data",
        category="finance",
        node_type="planet",
        parent_skill="finance",
        tool_reward="get_market_data",
        icon="📈"
    ),

    # Moon 3.1: Price Alerts
    _create_skill(
        skill_id="price_alerts",
        name="Price Alerts",
        description="Set and manage price notifications",
        category="finance",
        node_type="moon",
        parent_skill="market_awareness",
        prerequisite="market_awareness",
        tool_reward="set_price_alert",
        icon="🔔"
    ),

    # Moon 3.2: Trend Analysis
    _create_skill(
        skill_id="trend_analysis",
        name="Trend Analysis",
        description="Analyze market trends and patterns",
        category="finance",
        node_type="moon",
        parent_skill="market_awareness",
        prerequisite="market_awareness",
        tool_reward="analyze_market_trend",
        icon="📉"
    ),

    # Planet 4: Savings Strategies
    _create_skill(
        skill_id="savings_strategies",
        name="Savings Strategies",
        description="Plan and execute savings goals",
        category="finance",
        node_type="planet",
        parent_skill="finance",
        tool_reward="plan_savings",
        icon="🎯"
    ),

    # Moon 4.1: Dollar Cost Averaging
    _create_skill(
        skill_id="dollar_cost_averaging",
        name="Dollar Cost Averaging",
        description="Set up recurring purchase schedules",
        category="finance",
        node_type="moon",
        parent_skill="savings_strategies",
        prerequisite="savings_strategies",
        tool_reward="setup_dca",
        icon="📅"
    ),

    # Planet 5: Token Knowledge
    _create_skill(
        skill_id="token_knowledge",
        name="Token Knowledge",
        description="Identify and work with tokens",
        category="finance",
        node_type="planet",
        parent_skill="finance",
        tool_reward="identify_token",
        icon="🪙"
    ),

    # Moon 5.1: CashToken Operations
    _create_skill(
        skill_id="cashtoken_operations",
        name="CashToken Operations",
        description="Manage CashToken fungible and NFT tokens",
        category="finance",
        node_type="moon",
        parent_skill="token_knowledge",
        prerequisite="token_knowledge",
        tool_reward="manage_cashtokens",
        icon="💎"
    ),
```

#### Step 2: Add Finance to TypeScript Definitions

**File:** `qubes-gui/src/data/skillDefinitions.ts`

Add to SKILL_CATEGORIES:

```typescript
export const SKILL_CATEGORIES = [
  // ... existing 8 categories including Finance ...
];
```

Add to SKILL_DEFINITIONS:

```typescript
export const SKILL_DEFINITIONS = {
  // ... existing categories ...

  finance: [
    // Sun
    {
      id: 'finance',
      name: 'Finance',
      description: 'Master financial operations and cryptocurrency management',
      nodeType: 'sun',
      toolCallReward: 'send_bch',
      icon: '💰',
    },
    // Planet 1: Transaction Mastery
    {
      id: 'transaction_mastery',
      name: 'Transaction Mastery',
      description: 'Validate and optimize blockchain transactions',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'validate_transaction',
      icon: '📝',
    },
    // Moon 1.1: Fee Optimization
    {
      id: 'fee_optimization',
      name: 'Fee Optimization',
      description: 'Minimize transaction fees while maintaining speed',
      nodeType: 'moon',
      parentSkill: 'transaction_mastery',
      prerequisite: 'transaction_mastery',
      toolCallReward: 'optimize_fees',
      icon: '⚡',
    },
    // Moon 1.2: Transaction Tracking
    {
      id: 'transaction_tracking',
      name: 'Transaction Tracking',
      description: 'Monitor transaction status and confirmations',
      nodeType: 'moon',
      parentSkill: 'transaction_mastery',
      prerequisite: 'transaction_mastery',
      toolCallReward: 'track_transaction',
      icon: '🔍',
    },
    // Planet 2: Wallet Management
    {
      id: 'wallet_management',
      name: 'Wallet Management',
      description: 'Monitor and maintain wallet health',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'check_wallet_health',
      icon: '👛',
    },
    // Moon 2.1: Balance Monitoring
    {
      id: 'balance_monitoring',
      name: 'Balance Monitoring',
      description: 'Track balances and set alerts',
      nodeType: 'moon',
      parentSkill: 'wallet_management',
      prerequisite: 'wallet_management',
      toolCallReward: 'monitor_balance',
      icon: '📊',
    },
    // Moon 2.2: Multi-sig Operations
    {
      id: 'multisig_operations',
      name: 'Multi-sig Operations',
      description: 'Manage multi-signature wallet operations',
      nodeType: 'moon',
      parentSkill: 'wallet_management',
      prerequisite: 'wallet_management',
      toolCallReward: 'multisig_action',
      icon: '🔐',
    },
    // Planet 3: Market Awareness
    {
      id: 'market_awareness',
      name: 'Market Awareness',
      description: 'Track and analyze market data',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'get_market_data',
      icon: '📈',
    },
    // Moon 3.1: Price Alerts
    {
      id: 'price_alerts',
      name: 'Price Alerts',
      description: 'Set and manage price notifications',
      nodeType: 'moon',
      parentSkill: 'market_awareness',
      prerequisite: 'market_awareness',
      toolCallReward: 'set_price_alert',
      icon: '🔔',
    },
    // Moon 3.2: Trend Analysis
    {
      id: 'trend_analysis',
      name: 'Trend Analysis',
      description: 'Analyze market trends and patterns',
      nodeType: 'moon',
      parentSkill: 'market_awareness',
      prerequisite: 'market_awareness',
      toolCallReward: 'analyze_market_trend',
      icon: '📉',
    },
    // Planet 4: Savings Strategies
    {
      id: 'savings_strategies',
      name: 'Savings Strategies',
      description: 'Plan and execute savings goals',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'plan_savings',
      icon: '🎯',
    },
    // Moon 4.1: Dollar Cost Averaging
    {
      id: 'dollar_cost_averaging',
      name: 'Dollar Cost Averaging',
      description: 'Set up recurring purchase schedules',
      nodeType: 'moon',
      parentSkill: 'savings_strategies',
      prerequisite: 'savings_strategies',
      toolCallReward: 'setup_dca',
      icon: '📅',
    },
    // Planet 5: Token Knowledge
    {
      id: 'token_knowledge',
      name: 'Token Knowledge',
      description: 'Identify and work with tokens',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'identify_token',
      icon: '🪙',
    },
    // Moon 5.1: CashToken Operations
    {
      id: 'cashtoken_operations',
      name: 'CashToken Operations',
      description: 'Manage CashToken fungible and NFT tokens',
      nodeType: 'moon',
      parentSkill: 'token_knowledge',
      prerequisite: 'token_knowledge',
      toolCallReward: 'manage_cashtokens',
      icon: '💎',
    },
  ],
};
```

#### Step 3: Update Skill Count Constants

If there are any hardcoded "7 categories" or "112 skills" references:

```bash
grep -rn "112" --include="*.py" --include="*.ts"
grep -rn "7 categor" --include="*.py" --include="*.ts"
```

Update to 8 categories and 128 skills.

### Finance Category Summary

| Level | Count | Skills |
|-------|-------|--------|
| Sun | 1 | `finance` |
| Planets | 5 | `transaction_mastery`, `wallet_management`, `market_awareness`, `savings_strategies`, `token_knowledge` |
| Moons | 8 | `fee_optimization`, `transaction_tracking`, `balance_monitoring`, `multisig_operations`, `price_alerts`, `trend_analysis`, `dollar_cost_averaging`, `cashtoken_operations` |
| **Total** | **14** | |

### Verification Checklist

- [ ] Python: Finance Sun added with `send_bch` tool reward
- [ ] Python: All 5 Planets added with correct parent_skill
- [ ] Python: All 8 Moons added with correct prerequisites
- [ ] TypeScript: SKILL_CATEGORIES has Finance entry
- [ ] TypeScript: SKILL_DEFINITIONS.finance has all 14 skills
- [ ] Skill count updated from 112 to 128 (if hardcoded anywhere)
- [ ] Frontend displays Finance category correctly

---

## 7. Task 0.5: Fix switch_model (Utility → Sun Tool)

### Objective

Move `switch_model` from utility tools (no XP) to Creative Expression Sun tool (earns XP).

### Current State

**File:** `ai/tools/registry.py`

```python
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    "get_system_state",
    "update_system_state",
    "get_skill_tree",
    "search_memory",
    "describe_my_avatar",
    "web_search",
    "browse_url",
    "generate_image",
    "chess_move",
    "send_bch",
    "switch_model",  # Currently in always-available (correct, it's a Sun tool)
}
```

The tool is already always-available, which is correct for a Sun tool. The issue is:
1. It may not be mapped in TOOL_TO_SKILL_MAPPING
2. It may not earn XP

### Implementation Steps

#### Step 1: Add to TOOL_TO_SKILL_MAPPING

**File:** `ai/skill_scanner.py`

Add to TOOL_TO_SKILL_MAPPING:

```python
TOOL_TO_SKILL_MAPPING = {
    # ... existing mappings ...

    # Creative Expression - Sun Tool
    "switch_model": "creative_expression",
}
```

#### Step 2: Update Skill Definition Tool Reward

**File:** `utils/skill_definitions.py`

Ensure Creative Expression Sun has `switch_model` as tool_reward:

```python
_create_skill(
    skill_id="creative_expression",
    name="Creative Expression",
    description="Express your unique self through creation and identity",
    category="creative_expression",
    node_type="sun",
    tool_reward="switch_model",  # Verify this is set
    icon="✨"
),
```

#### Step 3: Update TypeScript

**File:** `qubes-gui/src/data/skillDefinitions.ts`

```typescript
// In creative_expression skills array
{
  id: 'creative_expression',
  name: 'Creative Expression',
  description: 'Express your unique self through creation and identity',
  nodeType: 'sun',
  toolCallReward: 'switch_model',  // Verify this is set
  icon: '✨',
},
```

#### Step 4: Remove from Utility Tool Documentation

Update any documentation that lists `switch_model` as a utility tool.

### Verification Checklist

- [ ] `switch_model` in TOOL_TO_SKILL_MAPPING → `creative_expression`
- [ ] Creative Expression Sun has `tool_reward="switch_model"`
- [ ] TypeScript matches Python
- [ ] Using `switch_model` awards XP to Creative Expression
- [ ] Documentation updated

---

## 8. Task 0.6: Update TOOL_TO_SKILL_MAPPING

### Objective

Update TOOL_TO_SKILL_MAPPING to reflect:
1. Category renames
2. New Finance category tools
3. New Sun tools

### Current Mappings to Update

**File:** `ai/skill_scanner.py`

#### Mappings Affected by Category Renames

```python
# OLD → NEW
"search_memory": "knowledge_domains",      # → "memory_recall"
"deep_research": "science",                # science parent: knowledge_domains → memory_recall
"synthesize_knowledge": "philosophy",      # philosophy parent: knowledge_domains → memory_recall
"explain_like_im_five": "philosophy",      # philosophy parent: knowledge_domains → memory_recall

"analyze_game_state": "chess",             # chess parent: games → board_games
"plan_strategy": "chess",                  # chess parent: games → board_games
"learn_from_game": "chess",                # chess parent: games → board_games

"debug_systematically": "debugging",       # debugging parent: technical_expertise → coding
"validate_solution": "debugging",          # debugging parent: technical_expertise → coding
```

**Note:** The skill_id values (like "science", "chess", "debugging") may stay the same if they're planet/moon IDs. Only the Sun/category IDs need to change.

#### New Mappings to Add

```python
TOOL_TO_SKILL_MAPPING = {
    # ... existing mappings ...

    # === NEW MAPPINGS FOR PHASE 0 ===

    # Creative Expression - Sun Tool
    "switch_model": "creative_expression",

    # Social Intelligence - Sun Tool
    "get_relationship_context": "social_intelligence",

    # Security & Privacy - Sun Tool
    "verify_chain_integrity": "security_privacy",

    # Finance - Sun Tool
    "send_bch": "finance",

    # Memory & Recall - Sun Tool
    "store_knowledge": "memory_recall",
}
```

### Complete Updated TOOL_TO_SKILL_MAPPING

```python
TOOL_TO_SKILL_MAPPING = {
    # ═══════════════════════════════════════════════════════════════════
    # AI REASONING
    # ═══════════════════════════════════════════════════════════════════
    "recall_similar": "ai_reasoning",              # Sun tool
    "describe_my_avatar": "analysis_critique",     # Planet: Analysis & Critique
    "think_step_by_step": "chain_of_thought",
    "self_critique": "analysis_critique",
    "explore_alternatives": "multistep_planning",

    # ═══════════════════════════════════════════════════════════════════
    # SOCIAL INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════
    "get_relationship_context": "social_intelligence",  # Sun tool (NEW)
    "draft_message_variants": "communication",
    "predict_reaction": "empathy",
    "build_rapport_strategy": "relationship_building",

    # ═══════════════════════════════════════════════════════════════════
    # CODING (formerly Technical Expertise)
    # ═══════════════════════════════════════════════════════════════════
    "develop_code": "coding",                      # Sun tool
    "debug_systematically": "debugging",
    "validate_solution": "debugging",

    # ═══════════════════════════════════════════════════════════════════
    # CREATIVE EXPRESSION
    # ═══════════════════════════════════════════════════════════════════
    "switch_model": "creative_expression",         # Sun tool (MOVED from utility)
    "generate_image": "visual_design",
    "brainstorm_variants": "creative_problem_solving",
    "iterate_design": "visual_design",
    "cross_pollinate_ideas": "creative_problem_solving",

    # ═══════════════════════════════════════════════════════════════════
    # MEMORY & RECALL (formerly Knowledge Domains)
    # ═══════════════════════════════════════════════════════════════════
    "store_knowledge": "memory_recall",            # Sun tool
    "search_memory": "memory_search",              # Planet: Memory Search
    "recall": "memory_search",                     # Planet tool
    "deep_research": "science",
    "synthesize_knowledge": "philosophy",
    "explain_like_im_five": "philosophy",
    "research_with_synthesis": "science",

    # ═══════════════════════════════════════════════════════════════════
    # SECURITY & PRIVACY
    # ═══════════════════════════════════════════════════════════════════
    "verify_chain_integrity": "security_privacy",  # Sun tool (NEW)
    "assess_security_risks": "threat_analysis",
    "privacy_impact_analysis": "privacy_protection",
    "verify_authenticity": "authentication",

    # ═══════════════════════════════════════════════════════════════════
    # BOARD GAMES (formerly Games)
    # ═══════════════════════════════════════════════════════════════════
    "play_game": "board_games",                    # Sun tool
    "chess_move": "chess",                         # Planet: Chess
    "analyze_game_state": "chess",
    "plan_strategy": "chess",
    "learn_from_game": "chess",

    # ═══════════════════════════════════════════════════════════════════
    # FINANCE (NEW CATEGORY)
    # ═══════════════════════════════════════════════════════════════════
    "send_bch": "finance",                         # Sun tool
    "validate_transaction": "transaction_mastery",
    "optimize_fees": "fee_optimization",
    "track_transaction": "transaction_tracking",
    "check_wallet_health": "wallet_management",
    "monitor_balance": "balance_monitoring",
    "multisig_action": "multisig_operations",
    "get_market_data": "market_awareness",
    "set_price_alert": "price_alerts",
    "analyze_market_trend": "trend_analysis",
    "plan_savings": "savings_strategies",
    "setup_dca": "dollar_cost_averaging",
    "identify_token": "token_knowledge",
    "manage_cashtokens": "cashtoken_operations",
}
```

### Verification Checklist

- [ ] All category renames reflected in comments
- [ ] All Sun tools have mappings
- [ ] All Finance tools mapped
- [ ] `switch_model` maps to `creative_expression`
- [ ] No orphaned mappings (all skill_ids exist in skill_definitions.py)

---

## 9. Task 0.7: Implement get_relationship_context Tool

### Objective

Implement the Social Intelligence Sun tool that retrieves comprehensive relationship context.

### Tool Specification

| Property | Value |
|----------|-------|
| Name | `get_relationship_context` |
| Category | Social Intelligence (Sun) |
| Purpose | Get full context about a relationship before responding |
| XP Award | 5/2.5/0 (standard) |
| Always Available | Yes (Sun tool) |

### Implementation Steps

#### Step 1: Create Handler

**File:** `ai/tools/handlers.py`

```python
async def get_relationship_context_handler(
    qube: "Qube",
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get comprehensive context about a relationship.

    Social Intelligence Sun tool - always available.
    Retrieves relationship history, trust level, interaction patterns,
    key memories, and mood history for an entity.

    Args:
        qube: The Qube instance
        params: {
            "entity_id": str,           # Person or Qube ID
            "include_memories": bool,   # Include key memories (default True)
            "include_mood": bool,       # Include mood history (default True)
            "memory_limit": int,        # Max memories to return (default 10)
        }

    Returns:
        {
            "success": bool,
            "entity_id": str,
            "entity_name": str,
            "relationship_type": str,   # owner, friend, acquaintance, qube, unknown
            "trust_level": int,         # 0-100
            "clearance_level": str,     # public, private, secret
            "interaction_count": int,
            "first_interaction": str,   # ISO timestamp
            "last_interaction": str,    # ISO timestamp
            "key_memories": List[Dict], # Recent significant memories
            "mood_history": List[Dict], # Recent mood observations
            "communication_style": str, # Preferred style
            "topics_discussed": List[str],
            "relationship_health": str, # healthy, strained, new, dormant
        }
    """
    entity_id = params.get("entity_id")
    if not entity_id:
        return {
            "success": False,
            "error": "entity_id is required"
        }

    include_memories = params.get("include_memories", True)
    include_mood = params.get("include_mood", True)
    memory_limit = params.get("memory_limit", 10)

    # Get relationship from chain_state
    relationships = qube.chain_state.get("relationships", {})
    relationship = relationships.get(entity_id, {})

    if not relationship:
        # Check if this is the owner
        owner_info = qube.chain_state.get("owner_info", {})
        if entity_id == owner_info.get("owner_id"):
            relationship = {
                "type": "owner",
                "trust_level": 100,
                "clearance_level": "secret",
                "name": owner_info.get("name", "Owner"),
            }
        else:
            return {
                "success": True,
                "entity_id": entity_id,
                "relationship_type": "unknown",
                "trust_level": 0,
                "message": "No existing relationship with this entity"
            }

    # Build response
    result = {
        "success": True,
        "entity_id": entity_id,
        "entity_name": relationship.get("name", entity_id),
        "relationship_type": relationship.get("type", "acquaintance"),
        "trust_level": relationship.get("trust_level", 50),
        "clearance_level": relationship.get("clearance_level", "public"),
        "interaction_count": relationship.get("interaction_count", 0),
        "first_interaction": relationship.get("first_interaction"),
        "last_interaction": relationship.get("last_interaction"),
        "communication_style": relationship.get("communication_style", "default"),
        "topics_discussed": relationship.get("topics", [])[:20],
        "relationship_health": _assess_relationship_health(relationship),
    }

    # Add key memories if requested
    if include_memories:
        memories = await _get_key_memories(qube, entity_id, limit=memory_limit)
        result["key_memories"] = memories

    # Add mood history if requested
    if include_mood:
        mood_history = relationship.get("mood_history", [])[-10:]
        result["mood_history"] = mood_history

    return result


def _assess_relationship_health(relationship: Dict) -> str:
    """Assess the health of a relationship based on various factors."""
    trust = relationship.get("trust_level", 50)
    last_interaction = relationship.get("last_interaction")
    interaction_count = relationship.get("interaction_count", 0)

    if interaction_count < 3:
        return "new"

    if last_interaction:
        from datetime import datetime, timezone, timedelta
        try:
            last = datetime.fromisoformat(last_interaction.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if now - last > timedelta(days=30):
                return "dormant"
        except:
            pass

    if trust < 30:
        return "strained"
    elif trust >= 70:
        return "healthy"
    else:
        return "neutral"


async def _get_key_memories(
    qube: "Qube",
    entity_id: str,
    limit: int = 10
) -> List[Dict]:
    """Get key memories involving an entity."""
    # Search memory chain for blocks involving this entity
    memories = []

    # This would integrate with the memory search system
    # For now, return empty list - full implementation in Phase 2

    return memories
```

#### Step 2: Register Tool Definition

**File:** `ai/tools/registry.py`

Add to tool definitions:

```python
ToolDefinition(
    name="get_relationship_context",
    description="Get comprehensive context about a relationship with a person or Qube. Returns trust level, interaction history, key memories, and communication preferences.",
    parameters={
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "The ID of the person or Qube to get context about"
            },
            "include_memories": {
                "type": "boolean",
                "description": "Whether to include key memories (default: true)",
                "default": True
            },
            "include_mood": {
                "type": "boolean",
                "description": "Whether to include mood history (default: true)",
                "default": True
            },
            "memory_limit": {
                "type": "integer",
                "description": "Maximum number of memories to return (default: 10)",
                "default": 10
            }
        },
        "required": ["entity_id"]
    },
    handler=get_relationship_context_handler
)
```

#### Step 3: Add to ALWAYS_AVAILABLE_TOOLS

**File:** `ai/tools/registry.py`

```python
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    # ... existing tools ...
    "get_relationship_context",  # NEW - Social Intelligence Sun
}
```

#### Step 4: Add to TypeScript

**File:** `qubes-gui/src/data/skillDefinitions.ts`

```typescript
export const ALWAYS_AVAILABLE_TOOLS = [
  // ... existing tools ...
  'get_relationship_context',  // NEW - Social Intelligence Sun
] as const;

// Add to TOOL_DESCRIPTIONS
export const TOOL_DESCRIPTIONS: Record<string, ToolDescription> = {
  // ... existing descriptions ...
  get_relationship_context: {
    name: 'Get Relationship Context',
    description: 'Get comprehensive context about a relationship',
    icon: '🤝',
  },
};
```

### Verification Checklist

- [ ] Handler implemented in `ai/tools/handlers.py`
- [ ] Tool registered in `ai/tools/registry.py`
- [ ] Added to ALWAYS_AVAILABLE_TOOLS (Python)
- [ ] Added to ALWAYS_AVAILABLE_TOOLS (TypeScript)
- [ ] Added to TOOL_DESCRIPTIONS (TypeScript)
- [ ] TOOL_TO_SKILL_MAPPING entry exists
- [ ] Manual test: Call tool, verify response structure
- [ ] Manual test: Verify XP awarded to Social Intelligence

---

## 10. Task 0.8: Implement verify_chain_integrity Tool

### Objective

Implement the Security & Privacy Sun tool that verifies memory chain integrity.

### Tool Specification

| Property | Value |
|----------|-------|
| Name | `verify_chain_integrity` |
| Category | Security & Privacy (Sun) |
| Purpose | Verify memory chain hasn't been tampered with |
| XP Award | 0.1 per new block verified (special formula) |
| Always Available | Yes (Sun tool) |

### Implementation Steps

#### Step 1: Add Chain State Field

**File:** `core/chain_state.py`

Add to default chain state:

```python
def create_default_chain_state():
    return {
        # ... existing fields ...

        "security": {
            "last_verified_block_number": 0,  # NEW
            "last_verification_timestamp": None,
            "verification_history": [],  # Last 10 verifications
        },
    }
```

#### Step 2: Create Handler

**File:** `ai/tools/handlers.py`

```python
async def verify_chain_integrity_handler(
    qube: "Qube",
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify memory chain integrity.

    Security & Privacy Sun tool - always available.
    Awards 0.1 XP per new block verified (anti-gaming: no XP for re-checking same blocks).

    Args:
        qube: The Qube instance
        params: {
            "full_check": bool,        # Check entire chain (default: False)
            "since_block": int,        # Start from specific block (optional)
        }

    Returns:
        {
            "success": bool,
            "valid": bool,             # True if chain is intact
            "blocks_checked": int,
            "new_blocks_verified": int,  # Blocks not previously verified
            "issues": List[Dict],      # Any problems found
            "last_anchor": Dict,       # Most recent blockchain anchor
            "xp_earned": float,        # 0.1 per new block
        }
    """
    full_check = params.get("full_check", False)
    since_block = params.get("since_block")

    # Get last verified block number
    security = qube.chain_state.get("security", {})
    last_verified = security.get("last_verified_block_number", 0)

    # Determine starting block
    if full_check:
        start_block = 0
    elif since_block is not None:
        start_block = since_block
    else:
        start_block = last_verified

    # Get current block count
    current_block = await qube.memory_chain.get_latest_block_number()

    # Verify chain integrity
    verification_result = await qube.memory_chain.verify_integrity(
        from_block=start_block
    )

    # Calculate new blocks verified (for XP)
    if verification_result["valid"]:
        new_blocks_verified = max(0, current_block - last_verified)

        # Update last verified block number
        qube.chain_state.set_nested(
            "security", "last_verified_block_number", current_block
        )
        qube.chain_state.set_nested(
            "security", "last_verification_timestamp",
            datetime.now(timezone.utc).isoformat()
        )
    else:
        new_blocks_verified = 0  # No XP for failed verification

    # Calculate XP (0.1 per new block)
    xp_earned = new_blocks_verified * 0.1

    # Log any issues as LEARNING blocks
    if not verification_result["valid"] and verification_result.get("issues"):
        await qube.memory_chain.add_block(
            block_type="LEARNING",
            content={
                "learning_type": "threat",
                "threat_type": "chain_integrity",
                "severity": 90,
                "details": verification_result["issues"],
                "source_category": "security_privacy"
            }
        )

    # Update verification history
    history = security.get("verification_history", [])
    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "blocks_checked": current_block - start_block,
        "valid": verification_result["valid"],
        "full_check": full_check
    })
    qube.chain_state.set_nested(
        "security", "verification_history", history[-10:]  # Keep last 10
    )

    return {
        "success": True,
        "valid": verification_result["valid"],
        "blocks_checked": current_block - start_block,
        "new_blocks_verified": new_blocks_verified,
        "issues": verification_result.get("issues", []),
        "last_anchor": verification_result.get("last_anchor"),
        "xp_earned": xp_earned,
        "message": f"Verified {current_block - start_block} blocks. "
                   f"{'Chain intact.' if verification_result['valid'] else 'ISSUES FOUND!'}"
    }
```

#### Step 3: Add Special XP Handling

**File:** `ai/skill_scanner.py`

Add special case for `verify_chain_integrity`:

```python
def _calculate_xp_for_action(action_type: str, result: Dict) -> float:
    """Calculate XP for a tool action."""

    # Special case: verify_chain_integrity uses per-block XP
    if action_type == "verify_chain_integrity":
        new_blocks = result.get("new_blocks_verified", 0)
        return new_blocks * 0.1  # 0.1 XP per new block verified

    # Standard XP calculation
    status = result.get("status", "")
    success = result.get("success", False)

    if status == "completed" and success:
        return 5.0
    elif status == "completed":
        return 2.5
    else:
        return 0.0
```

#### Step 4: Register Tool Definition

**File:** `ai/tools/registry.py`

```python
ToolDefinition(
    name="verify_chain_integrity",
    description="Verify that the memory chain hasn't been tampered with. Checks block hashes and anchor status. Awards 0.1 XP per new block verified.",
    parameters={
        "type": "object",
        "properties": {
            "full_check": {
                "type": "boolean",
                "description": "Check entire chain from genesis (default: false, checks since last verification)",
                "default": False
            },
            "since_block": {
                "type": "integer",
                "description": "Start verification from a specific block number (optional)"
            }
        },
        "required": []
    },
    handler=verify_chain_integrity_handler
)
```

#### Step 5: Add to ALWAYS_AVAILABLE_TOOLS

**File:** `ai/tools/registry.py`

```python
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    # ... existing tools ...
    "verify_chain_integrity",  # NEW - Security & Privacy Sun
}
```

#### Step 6: Add to TypeScript

**File:** `qubes-gui/src/data/skillDefinitions.ts`

```typescript
export const ALWAYS_AVAILABLE_TOOLS = [
  // ... existing tools ...
  'verify_chain_integrity',  // NEW - Security & Privacy Sun
] as const;

export const TOOL_DESCRIPTIONS: Record<string, ToolDescription> = {
  // ... existing descriptions ...
  verify_chain_integrity: {
    name: 'Verify Chain Integrity',
    description: 'Verify memory chain hasn\'t been tampered with',
    icon: '🔐',
  },
};
```

### Verification Checklist

- [ ] `core/chain_state.py`: security.last_verified_block_number field added
- [ ] Handler implemented with special 0.1 XP per block logic
- [ ] Creates LEARNING block on integrity issues
- [ ] Tool registered in registry.py
- [ ] Added to ALWAYS_AVAILABLE_TOOLS (Python & TypeScript)
- [ ] Special XP handling in skill_scanner.py
- [ ] Manual test: Verify blocks, check XP calculation
- [ ] Manual test: Re-verify same blocks, confirm 0 XP (anti-gaming)

---

## 11. Task 0.9: Update Intelligent Routing

### Objective

Update intelligent XP routing for `web_search`, `browse_url`, and `process_document` to use new category names.

### Implementation Steps

#### Step 1: Update analyze_research_topic Function

**File:** `ai/skill_scanner.py`

Find the `analyze_research_topic()` function and update category references:

```python
def analyze_research_topic(query: str, url: Optional[str] = None) -> str:
    """
    Analyze a search query or URL to determine which skill should receive XP.
    Returns skill_id for intelligent routing.
    """
    text = f"{query} {url or ''}".lower()

    # Keyword patterns mapped to skills
    patterns = {
        # Coding (formerly Technical Expertise)
        "coding": [
            r"python|javascript|typescript|react|code|programming|developer|api",
            r"function|class|method|variable|bug|error|debug|compile",
            r"git|github|repository|commit|merge|branch",
        ],

        # Memory & Recall (formerly Knowledge Domains)
        "memory_recall": [
            r"history|historical|ancient|medieval|century|era|civilization",
            r"science|scientific|research|study|experiment|theory",
            r"philosophy|philosophical|ethics|logic|reasoning",
            r"math|mathematics|equation|formula|calculus|algebra",
        ],

        # Finance (NEW)
        "finance": [
            r"bitcoin|bch|crypto|cryptocurrency|blockchain|wallet",
            r"price|market|trading|exchange|transaction|fee",
            r"token|nft|defi|stake|yield",
        ],

        # Security & Privacy
        "security_privacy": [
            r"security|secure|encrypt|decrypt|hash|authentication",
            r"privacy|private|protect|vulnerability|exploit|attack",
            r"password|credential|certificate|ssl|tls",
        ],

        # Creative Expression
        "creative_expression": [
            r"art|design|creative|visual|graphic|color|composition",
            r"music|song|melody|harmony|composer|musician",
            r"writing|story|narrative|character|plot|fiction",
        ],

        # Social Intelligence
        "social_intelligence": [
            r"relationship|communication|emotion|empathy|social",
            r"persuasion|negotiation|conflict|trust|rapport",
        ],

        # AI Reasoning
        "ai_reasoning": [
            r"pattern|analysis|reasoning|logic|insight|learning",
            r"mistake|failure|success|growth|reflection",
        ],

        # Board Games (formerly Games)
        "board_games": [
            r"chess|game|strategy|tactics|move|opening|endgame",
            r"monopoly|clue|sorry|life\s+game",
        ],
    }

    # Check each pattern
    for skill_id, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                return skill_id

    # Default to Memory & Recall (general knowledge)
    return "memory_recall"
```

#### Step 2: Update Default Routing

Ensure the default fallback uses `memory_recall` instead of `knowledge_domains`:

```python
# Default routing
if skill_id is None:
    skill_id = "memory_recall"  # Changed from "knowledge_domains"
```

### Verification Checklist

- [ ] `analyze_research_topic()` uses new category IDs
- [ ] Default routing returns `memory_recall`
- [ ] Finance keywords added for new category
- [ ] Manual test: Search for "python tutorial", verify routes to `coding`
- [ ] Manual test: Search for "bitcoin price", verify routes to `finance`

---

## 12. Task 0.10: Frontend Synchronization

### Objective

Ensure all frontend (TypeScript) definitions match backend (Python) changes.

### Files to Update

1. `qubes-gui/src/data/skillDefinitions.ts`
2. `qubes-gui/src/components/blocks/BlockContentViewer.tsx`
3. `qubes-gui/src/components/tabs/SkillsTab.tsx`

### Implementation Steps

#### Step 1: Verify SKILL_CATEGORIES Match

**File:** `qubes-gui/src/data/skillDefinitions.ts`

```typescript
export const SKILL_CATEGORIES = [
  { id: 'ai_reasoning', name: 'AI Reasoning', color: '#4A90E2', icon: '🧠' },
  { id: 'social_intelligence', name: 'Social Intelligence', color: '#FF69B4', icon: '🤝' },
  { id: 'coding', name: 'Coding', color: '#00FF88', icon: '💻' },
  { id: 'creative_expression', name: 'Creative Expression', color: '#FFB347', icon: '✨' },
  { id: 'memory_recall', name: 'Memory & Recall', color: '#9B59B6', icon: '🧠' },
  { id: 'security_privacy', name: 'Security & Privacy', color: '#E74C3C', icon: '🛡️' },
  { id: 'board_games', name: 'Board Games', color: '#F39C12', icon: '🎮' },
  { id: 'finance', name: 'Finance', color: '#2ECC71', icon: '💰' },  // NEW
];
```

#### Step 2: Verify ALWAYS_AVAILABLE_TOOLS Match

```typescript
export const ALWAYS_AVAILABLE_TOOLS = [
  'get_system_state',
  'update_system_state',
  'get_skill_tree',
  'search_memory',
  'describe_my_avatar',
  'web_search',
  'browse_url',
  'generate_image',
  'chess_move',
  'send_bch',
  'switch_model',
  'get_relationship_context',   // NEW
  'verify_chain_integrity',     // NEW
] as const;
```

#### Step 3: Update BlockContentViewer for LEARNING Blocks

**File:** `qubes-gui/src/components/blocks/BlockContentViewer.tsx`

Add LEARNING block type handling:

```typescript
// In the block type rendering logic
const renderBlockContent = (block: Block) => {
  switch (block.block_type) {
    // ... existing cases ...

    case 'LEARNING':
      return <LearningBlockContent content={block.content} />;

    default:
      return <GenericBlockContent content={block.content} />;
  }
};

// New component for LEARNING blocks
const LearningBlockContent: React.FC<{ content: any }> = ({ content }) => {
  const learningTypeIcons: Record<string, string> = {
    fact: '📝',
    procedure: '📋',
    synthesis: '🔗',
    insight: '💡',
    pattern: '🔄',
    relationship: '👥',
    threat: '⚠️',
    trust: '🤝',
  };

  return (
    <div className="learning-block">
      <div className="learning-header">
        <span className="learning-icon">
          {learningTypeIcons[content.learning_type] || '📚'}
        </span>
        <span className="learning-type">
          {content.learning_type.toUpperCase()}
        </span>
        {content.confidence && (
          <span className="confidence">
            {content.confidence}% confident
          </span>
        )}
      </div>
      <div className="learning-content">
        {/* Render based on learning_type */}
        {content.learning_type === 'fact' && (
          <p>{content.fact}</p>
        )}
        {content.learning_type === 'insight' && (
          <p>{content.insight}</p>
        )}
        {content.learning_type === 'threat' && (
          <div className="threat-warning">
            <strong>Threat Detected:</strong> {content.threat_type}
          </div>
        )}
        {/* Add more type-specific rendering as needed */}
      </div>
    </div>
  );
};
```

#### Step 4: Update SkillsTab for 8 Categories

**File:** `qubes-gui/src/components/tabs/SkillsTab.tsx`

Verify the skill tree visualization handles 8 suns correctly:

```typescript
// Check orbital calculations
const calculateSunPositions = (categories: Category[]) => {
  const count = categories.length;  // Now 8 instead of 7
  const angleStep = (2 * Math.PI) / count;

  return categories.map((cat, index) => ({
    ...cat,
    angle: index * angleStep,
    x: centerX + sunOrbitRadius * Math.cos(index * angleStep),
    y: centerY + sunOrbitRadius * Math.sin(index * angleStep),
  }));
};
```

### Verification Checklist

- [ ] SKILL_CATEGORIES has 8 entries
- [ ] ALWAYS_AVAILABLE_TOOLS has 13 entries
- [ ] SKILL_DEFINITIONS has all 8 category keys
- [ ] BlockContentViewer handles LEARNING blocks
- [ ] SkillsTab displays 8 suns correctly
- [ ] No TypeScript compilation errors
- [ ] Visual test: Skill tree shows all 8 categories

---

## 13. Task 0.11: Testing & Validation

### Unit Tests

#### Test XP Values

```python
# tests/test_skill_scanner.py

def test_xp_values_updated():
    """Verify XP values are 5/2.5/0"""
    from ai.skill_scanner import _calculate_xp_for_action

    # Success
    result = {"status": "completed", "success": True}
    assert _calculate_xp_for_action("test_tool", result) == 5.0

    # Completed with issues
    result = {"status": "completed", "success": False}
    assert _calculate_xp_for_action("test_tool", result) == 2.5

    # Failed
    result = {"status": "failed", "success": False}
    assert _calculate_xp_for_action("test_tool", result) == 0.0


def test_verify_chain_integrity_xp():
    """Verify special XP calculation for chain integrity"""
    from ai.skill_scanner import _calculate_xp_for_action

    result = {"new_blocks_verified": 50}
    xp = _calculate_xp_for_action("verify_chain_integrity", result)
    assert xp == 5.0  # 50 * 0.1

    result = {"new_blocks_verified": 0}
    xp = _calculate_xp_for_action("verify_chain_integrity", result)
    assert xp == 0.0  # Anti-gaming
```

#### Test Category IDs

```python
# tests/test_skill_definitions.py

def test_category_ids_renamed():
    """Verify category IDs use new names"""
    from utils.skill_definitions import generate_all_skills

    skills = generate_all_skills()
    categories = set(s["category"] for s in skills)

    assert "memory_recall" in categories
    assert "board_games" in categories
    assert "coding" in categories
    assert "finance" in categories

    # Old names should NOT exist
    assert "knowledge_domains" not in categories
    assert "games" not in categories
    assert "technical_expertise" not in categories


def test_finance_category_complete():
    """Verify Finance category has all skills"""
    from utils.skill_definitions import generate_all_skills

    skills = generate_all_skills()
    finance_skills = [s for s in skills if s["category"] == "finance"]

    assert len(finance_skills) == 14  # 1 sun + 5 planets + 8 moons

    # Verify hierarchy
    sun = [s for s in finance_skills if s["nodeType"] == "sun"]
    planets = [s for s in finance_skills if s["nodeType"] == "planet"]
    moons = [s for s in finance_skills if s["nodeType"] == "moon"]

    assert len(sun) == 1
    assert len(planets) == 5
    assert len(moons) == 8
```

#### Test LEARNING Block Type

```python
# tests/test_blocks.py

def test_learning_block_type_exists():
    """Verify LEARNING block type is defined"""
    from core.block import BlockType

    assert hasattr(BlockType, 'LEARNING')
    assert BlockType.LEARNING.value == "LEARNING"


def test_create_learning_block():
    """Verify LEARNING block creation"""
    from core.block import create_learning_block

    block = create_learning_block(
        qube_id="test_qube",
        learning_type="fact",
        content={"fact": "Test fact", "subject": "testing"},
        source_category="ai_reasoning"
    )

    assert block["block_type"] == "LEARNING"
    assert block["content"]["learning_type"] == "fact"
    assert block["content"]["source_category"] == "ai_reasoning"
```

### Integration Tests

```python
# tests/test_phase0_integration.py

async def test_get_relationship_context():
    """Test get_relationship_context tool end-to-end"""
    # Setup test Qube with relationship data
    qube = await create_test_qube()
    qube.chain_state.set("relationships", {
        "test_entity": {
            "name": "Test Person",
            "trust_level": 75,
            "type": "friend",
        }
    })

    # Call tool
    result = await get_relationship_context_handler(qube, {
        "entity_id": "test_entity"
    })

    assert result["success"] is True
    assert result["trust_level"] == 75
    assert result["relationship_type"] == "friend"


async def test_verify_chain_integrity():
    """Test verify_chain_integrity tool end-to-end"""
    qube = await create_test_qube()

    # First verification
    result1 = await verify_chain_integrity_handler(qube, {})
    assert result1["success"] is True
    assert result1["valid"] is True

    # Check XP calculation
    blocks_verified = result1["new_blocks_verified"]
    assert result1["xp_earned"] == blocks_verified * 0.1

    # Second verification (should get 0 XP - no new blocks)
    result2 = await verify_chain_integrity_handler(qube, {})
    assert result2["xp_earned"] == 0.0  # Anti-gaming
```

### Manual Testing Checklist

- [ ] **XP Values**
  - [ ] Use a tool successfully, verify 5 XP awarded
  - [ ] Use a tool with partial success, verify 2.5 XP awarded
  - [ ] Use a tool that fails, verify 0 XP awarded

- [ ] **Categories**
  - [ ] Frontend shows "Memory & Recall" (not "Knowledge Domains")
  - [ ] Frontend shows "Board Games" (not "Games")
  - [ ] Frontend shows "Coding" (not "Technical Expertise")
  - [ ] Frontend shows "Finance" (new category)
  - [ ] All 8 suns visible in skill tree

- [ ] **New Tools**
  - [ ] `get_relationship_context` appears in available tools
  - [ ] `verify_chain_integrity` appears in available tools
  - [ ] Both tools execute without errors
  - [ ] Both tools award XP to correct categories

- [ ] **LEARNING Blocks**
  - [ ] LEARNING blocks can be created
  - [ ] LEARNING blocks appear in block viewer
  - [ ] All learning_types render correctly

- [ ] **switch_model**
  - [ ] Using `switch_model` awards XP to Creative Expression
  - [ ] Still functions correctly (model actually switches)

- [ ] **Qube Locker**
  - [ ] QubeLocker class instantiates without errors
  - [ ] Can store items to all categories
  - [ ] Can retrieve stored items
  - [ ] Can list items by category
  - [ ] Storage persists across sessions

---

## 14. Task 0.12: Implement Qube Locker

### Overview

The Qube Locker is a foundational storage system for creative works and documents. It complements the existing storage systems:

```
Memory Chain  = What happened (events, conversations)
Qube Profile  = Who I am (preferences, traits)
Qube Locker   = What I've made (documents, creations)  ← NEW
```

**Used by:**
- **Phase 4 (Creative Expression)**: Poems, stories, images, music, characters, worlds
- **Phase 5 (Memory & Recall)**: Exported knowledge documents, reflections, journal

### Directory Structure

```
qube_locker/
├── writing/
│   ├── poems/
│   ├── stories/
│   └── essays/
├── art/
│   ├── images/
│   ├── concepts/
│   └── compositions/
├── music/
│   ├── melodies/
│   ├── lyrics/
│   └── compositions/
├── stories/
│   ├── narratives/
│   ├── characters/
│   └── worlds/
├── personal/
│   ├── reflections/
│   └── journal/
└── exports/
    └── knowledge/
```

### Implementation

**File:** `core/locker.py` (NEW FILE)

```python
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
import logging

logger = logging.getLogger(__name__)


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
                logger.error(f"Failed to load locker index: {e}")
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
            logger.error(f"Failed to save locker index: {e}")

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
            logger.error(f"Failed to write locker item: {e}")
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

        logger.info(f"Stored locker item: {index_key}")

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
            logger.error(f"Failed to read locker item: {e}")
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
            logger.error(f"Failed to delete locker file: {e}")

        # Remove from index
        del self._index[index_key]
        self._save_index()

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
```

### Integration with Qube Class

**File:** `core/qube.py`
**Location:** Add to `__init__` method

```python
# In Qube.__init__():
from core.locker import QubeLocker

# After initializing chain_state:
self.locker = QubeLocker(self.data_dir)
```

### Usage Example

```python
# In a tool handler:
async def generate_image(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    # ... generate image ...

    # Store in locker
    if result["success"]:
        await qube.locker.store(
            category="art/images",
            name=f"image_{timestamp}",
            content=result["image_url"],  # Store URL
            content_type="url",
            metadata={"prompt": prompt, "style": style},
            tags=["generated", "dall-e"]
        )

    return result
```

### Verification Checklist

- [ ] `core/locker.py` file created
- [ ] `QubeLocker` class implemented with all methods
- [ ] Directory structure created on initialization
- [ ] Index file persistence works
- [ ] Integration added to `Qube.__init__`
- [ ] Can store text content
- [ ] Can store URL content
- [ ] Can store JSON content
- [ ] Can retrieve items
- [ ] Can list items by category
- [ ] Can search across items
- [ ] Can delete items
- [ ] Can update items

---

## Appendix A: File Reference

### Backend (Python)

| File | Purpose | Phase 0 Changes |
|------|---------|-----------------|
| `ai/skill_scanner.py` | XP calculation, tool mapping | XP values, mappings |
| `ai/tools/registry.py` | Tool registration | New tools, always-available |
| `ai/tools/handlers.py` | Tool implementations | New handlers |
| `core/block.py` | Block types | Add LEARNING |
| `core/chain_state.py` | State storage | Add security fields |
| `core/locker.py` | Creative works storage | **NEW FILE** |
| `core/qube.py` | Qube class | Initialize QubeLocker |
| `utils/skill_definitions.py` | Skill definitions | Renames, Finance category |
| `utils/skills_manager.py` | XP management | No changes |

### Frontend (TypeScript)

| File | Purpose | Phase 0 Changes |
|------|---------|-----------------|
| `qubes-gui/src/data/skillDefinitions.ts` | Skill definitions | Mirror Python changes |
| `qubes-gui/src/components/blocks/BlockContentViewer.tsx` | Block rendering | LEARNING blocks |
| `qubes-gui/src/components/tabs/SkillsTab.tsx` | Skill tree UI | 8 categories |

---

## Appendix B: Current vs Target State

### Skill Categories

| Current | Target | Change |
|---------|--------|--------|
| AI Reasoning | AI Reasoning | - |
| Social Intelligence | Social Intelligence | - |
| Technical Expertise | **Coding** | Renamed |
| Creative Expression | Creative Expression | - |
| Knowledge Domains | **Memory & Recall** | Renamed |
| Security & Privacy | Security & Privacy | - |
| Games | **Board Games** | Renamed |
| - | **Finance** | NEW |

### Skill Counts

| Category | Current | Target |
|----------|---------|--------|
| AI Reasoning | 16 | 14 |
| Social Intelligence | 16 | 16 |
| Coding | 16 | 18 |
| Creative Expression | 16 | 17 |
| Memory & Recall | 16 | 16 |
| Security & Privacy | 16 | 16 |
| Board Games | 16 | 6 + 22 achievements |
| Finance | 0 | 14 |
| **Total** | **112** | **128** |

### XP Values

| Outcome | Current | Target |
|---------|---------|--------|
| Success | 3 | **5** |
| Completed | 2 | **2.5** |
| Failed | 0 | 0 |

### Block Types

| Current | Target |
|---------|--------|
| GENESIS | GENESIS |
| THOUGHT | THOUGHT |
| ACTION | ACTION |
| OBSERVATION | OBSERVATION |
| MESSAGE | MESSAGE |
| DECISION | DECISION |
| MEMORY_ANCHOR | MEMORY_ANCHOR |
| COLLABORATIVE_MEMORY | COLLABORATIVE_MEMORY |
| SUMMARY | SUMMARY |
| GAME | GAME |
| - | **LEARNING** |

### Always-Available Tools

| Current (11) | Target (13) |
|--------------|-------------|
| get_system_state | get_system_state |
| update_system_state | update_system_state |
| get_skill_tree | get_skill_tree |
| search_memory | search_memory |
| describe_my_avatar | describe_my_avatar |
| web_search | web_search |
| browse_url | browse_url |
| generate_image | generate_image |
| chess_move | chess_move |
| send_bch | send_bch |
| switch_model | switch_model |
| - | **get_relationship_context** |
| - | **verify_chain_integrity** |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-30 | Claude | Initial blueprint |

---

**End of Phase 0 Implementation Blueprint**
