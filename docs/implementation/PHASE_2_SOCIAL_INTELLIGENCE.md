# Phase 2: Social Intelligence - Implementation Blueprint

**Document Version:** 1.0
**Based on:** SKILL_TREE_MASTER.md
**Theme:** Social & Emotional Learning
**Prerequisites:** Phase 0 (Foundation), Phase 1 (AI Reasoning) recommended

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Prerequisites & Dependencies](#2-prerequisites--dependencies)
3. [Task 2.1: Update Skill Definitions](#3-task-21-update-skill-definitions)
4. [Task 2.2: Update TOOL_TO_SKILL_MAPPING](#4-task-22-update-tool_to_skill_mapping)
5. [Task 2.3: Implement Sun Tool - get_relationship_context](#5-task-23-implement-sun-tool---get_relationship_context)
6. [Task 2.4: Implement Relationship Memory Planet](#6-task-24-implement-relationship-memory-planet)
7. [Task 2.5: Implement Emotional Learning Planet](#7-task-25-implement-emotional-learning-planet)
8. [Task 2.6: Implement Communication Adaptation Planet](#8-task-26-implement-communication-adaptation-planet)
9. [Task 2.7: Implement Debate & Persuasion Planet](#9-task-27-implement-debate--persuasion-planet)
10. [Task 2.8: Implement Trust & Boundaries Planet](#10-task-28-implement-trust--boundaries-planet)
11. [Task 2.9: Register All Tools](#11-task-29-register-all-tools)
12. [Task 2.10: Frontend Synchronization](#12-task-210-frontend-synchronization)
13. [Task 2.11: LEARNING Block Integration](#13-task-211-learning-block-integration)
14. [Task 2.12: Testing & Validation](#14-task-212-testing--validation)
15. [Appendix A: Tool Summary Table](#appendix-a-tool-summary-table)
16. [Appendix B: Relationship System Reference](#appendix-b-relationship-system-reference)
17. [Appendix C: Helper Functions](#appendix-c-helper-functions)

---

## 1. Executive Summary

### Purpose

Phase 2 transforms the Social Intelligence category into a relationship-powered learning system. The Qube gets better at social interactions by tracking relationships over time, learning emotional patterns, adapting communication styles, and protecting itself from manipulation.

### Theme: Social & Emotional Learning

This phase leverages the existing 48-field relationship system:
- **Relationship Memory**: Track and recall relationship history over time
- **Emotional Learning**: Understand and respond to emotional patterns
- **Communication Adaptation**: Adjust style for different people
- **Debate & Persuasion**: Arguments, influence, and constructive disagreement
- **Trust & Boundaries**: Self-protection and trust assessment

### Tool Count

| Type | Count | Tools |
|------|-------|-------|
| Sun | 1 | `get_relationship_context` |
| Planets | 5 | `recall_relationship_history`, `read_emotional_state`, `adapt_communication_style`, `steelman`, `assess_trust_level` |
| Moons | 10 | `analyze_interaction_patterns`, `get_relationship_timeline`, `track_emotional_patterns`, `detect_mood_shift`, `match_communication_style`, `calibrate_tone`, `devils_advocate`, `spot_fallacy`, `detect_social_manipulation`, `evaluate_request` |
| **Total** | **16** | |

### Scope

| Metric | Before Phase 2 | After Phase 2 |
|--------|----------------|---------------|
| Social Intelligence Skills | 16 (old structure) | 16 (new structure) |
| Social Intelligence Tools | 1 (`draft_message_variants`) | 16 (new tools) |
| Relationship-Powered Tools | 0 | 16 |
| Trust/Safety Tools | 0 | 4 |

### Current Codebase State (as of Jan 2026)

#### Existing Social Intelligence Skills (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current Sun tool**: `draft_message_variants`
- **Current Planets**: emotional_intelligence, communication, empathy, relationship_building, conflict_resolution
- **Current Moons**: 10 moons across planets
- **Action**: Replace entire skill tree with new relationship-powered structure

#### Tool Mappings (`ai/skill_scanner.py:57-59`)
- **Current mappings** (to be replaced):
  ```python
  "draft_message_variants": "communication"
  "predict_reaction": "empathy"
  "build_rapport_strategy": "relationship_building"
  ```
- **Target mappings** (new tools):
  ```python
  "get_relationship_context": "social_intelligence"  # Sun
  "recall_relationship_history": "relationship_memory"
  "read_emotional_state": "emotional_learning"
  # ... 13 more new tool mappings
  ```
- **Action**: Replace old mappings with new relationship-powered tools

#### Relationship System (`core/chain_state.py`)
- **Current**: 48-field relationship tracking already implemented
- **Fields available**: trust_level, interaction_count, last_interaction, mood_history, communication_preferences, etc.
- **Action**: New tools will leverage existing relationship infrastructure

#### Sun Tool Change
- **Current**: `draft_message_variants` earns Social Intelligence XP
- **Target**: `get_relationship_context` earns Social Intelligence XP
- **Note**: `get_relationship_context` is a new tool that must be implemented

### Files Modified

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Replace all Social Intelligence skills |
| `ai/skill_scanner.py` | Add 16 new tool mappings |
| `ai/tools/handlers.py` | Add 16 new handler functions + helper functions |
| `ai/tools/registry.py` | Register 16 new tools, add Sun to ALWAYS_AVAILABLE_TOOLS |
| `qubes-gui/src/data/skillDefinitions.ts` | Replace all Social Intelligence definitions |

### Estimated Effort

| Task | Effort | Complexity |
|------|--------|------------|
| 2.1 Skill Definitions | 2 hours | Low |
| 2.2 Tool Mappings | 30 min | Low |
| 2.3 Sun Tool (get_relationship_context) | 2-3 hours | Medium |
| 2.4 Relationship Memory (3 tools) | 4-5 hours | Medium |
| 2.5 Emotional Learning (3 tools) | 4-5 hours | Medium |
| 2.6 Communication Adaptation (3 tools) | 3-4 hours | Medium |
| 2.7 Debate & Persuasion (3 tools) | 3-4 hours | Medium |
| 2.8 Trust & Boundaries (3 tools) | 4-5 hours | Medium-High |
| 2.9 Tool Registration | 2-3 hours | Low |
| 2.10 Frontend Sync | 2-3 hours | Medium |
| 2.11 LEARNING Block Integration | 2 hours | Medium |
| 2.12 Testing | 4-6 hours | Medium |
| **Total** | **~5-6 days** | **Medium** |

---

## 2. Prerequisites & Dependencies

### Phase 0 Requirements

These Phase 0 items MUST be completed:
- [x] XP values updated (5/2.5/0)
- [x] LEARNING block type added
- [x] `get_relationship_context` added to ALWAYS_AVAILABLE_TOOLS

### Existing Systems Leveraged

Phase 2 tools depend heavily on the relationship infrastructure:

#### 1. Relationship Class (48 Fields)

**File:** `relationships/relationship.py`

```python
# Core Trust Metrics (5 AI-evaluated + 1 calculated)
relationship.honesty        # 0-100
relationship.reliability    # 0-100
relationship.support        # 0-100
relationship.loyalty        # 0-100
relationship.respect        # 0-100
relationship.trust          # 0-100 (calculated)

# Positive Social Metrics (14)
relationship.friendship, affection, engagement, depth, humor
relationship.understanding, compatibility, admiration, warmth
relationship.openness, patience, empowerment, responsiveness, expertise

# Negative Social Metrics (10)
relationship.antagonism, resentment, annoyance, distrust, rivalry
relationship.tension, condescension, manipulation, dismissiveness, betrayal

# Behavioral Metrics (6)
relationship.verbosity, punctuality, emotional_stability
relationship.directness, energy_level, humor_style

# Tracked Statistics (9)
relationship.messages_sent, messages_received, response_time_avg
relationship.last_interaction, collaborations, collaborations_successful
relationship.collaborations_failed, first_contact, days_known

# Relationship State (5)
relationship.has_met, status, blocked_at, blocked_reason, evaluations
```

#### 2. SocialDynamicsManager

**File:** `relationships/social.py`

```python
# Key methods for Phase 2 tools
social_manager = qube.social_dynamics_manager

social_manager.get_relationship(entity_id)           # Returns Relationship or None
social_manager.get_all_relationships()               # Returns List[Relationship]
social_manager.get_relationships_by_status(status)   # Filter by status
social_manager.get_best_friend()                     # Returns best friend or None
social_manager.record_message(entity_id, is_outgoing, response_time)
```

#### 3. TrustScorer

**File:** `relationships/trust.py`

```python
trust_scorer = TrustScorer()
trust_score = trust_scorer.calculate_trust_score(relationship, profile="analytical")
```

#### 4. Relationship Statuses

```python
RELATIONSHIP_STATUSES = {
    "blocked": -100,
    "enemy": -50,
    "rival": -20,
    "suspicious": -10,
    "unmet": 0,
    "stranger": 5,
    "acquaintance": 20,
    "friend": 50,
    "close_friend": 75,
    "best_friend": 100,
}
```

---

## 3. Task 2.1: Update Skill Definitions

### Python Backend

**File:** `utils/skill_definitions.py`
**Lines:** 72-90 (replace entire Social Intelligence section)

#### Target State (New)

```python
# ===== SOCIAL INTELLIGENCE (16 skills) =====
# Theme: Social & Emotional Learning - relationship-powered

# Sun
skills.append(_create_skill(
    "social_intelligence",
    "Social Intelligence",
    "Master social and emotional learning through relationship memory",
    "social_intelligence",
    "sun",
    tool_reward="get_relationship_context",  # NEW Sun tool
    icon="🤝"
))

# Planet 1: Relationship Memory
skills.append(_create_skill(
    "relationship_memory",
    "Relationship Memory",
    "Track and recall relationship history over time",
    "social_intelligence",
    "planet",
    "social_intelligence",
    tool_reward="recall_relationship_history",
    icon="📝"
))

# Moon 1.1: Interaction Patterns
skills.append(_create_skill(
    "interaction_patterns",
    "Interaction Patterns",
    "Understand communication frequency and patterns",
    "social_intelligence",
    "moon",
    "relationship_memory",
    "relationship_memory",
    icon="📊"
))

# Moon 1.2: Relationship Timeline
skills.append(_create_skill(
    "relationship_timeline",
    "Relationship Timeline",
    "Show how relationship evolved over time",
    "social_intelligence",
    "moon",
    "relationship_memory",
    "relationship_memory",
    icon="📈"
))

# Planet 2: Emotional Learning
skills.append(_create_skill(
    "emotional_learning",
    "Emotional Learning",
    "Understand and respond to emotional patterns",
    "social_intelligence",
    "planet",
    "social_intelligence",
    tool_reward="read_emotional_state",
    icon="❤️"
))

# Moon 2.1: Emotional History
skills.append(_create_skill(
    "emotional_history",
    "Emotional History",
    "What makes this person happy or upset over time",
    "social_intelligence",
    "moon",
    "emotional_learning",
    "emotional_learning",
    icon="📜"
))

# Moon 2.2: Mood Awareness
skills.append(_create_skill(
    "mood_awareness",
    "Mood Awareness",
    "Notice when someone's emotional state changes",
    "social_intelligence",
    "moon",
    "emotional_learning",
    "emotional_learning",
    icon="🎭"
))

# Planet 3: Communication Adaptation
skills.append(_create_skill(
    "communication_adaptation",
    "Communication Adaptation",
    "Adjust communication style for different people",
    "social_intelligence",
    "planet",
    "social_intelligence",
    tool_reward="adapt_communication_style",
    icon="💬"
))

# Moon 3.1: Style Matching
skills.append(_create_skill(
    "style_matching",
    "Style Matching",
    "Mirror their preferred communication style",
    "social_intelligence",
    "moon",
    "communication_adaptation",
    "communication_adaptation",
    icon="🪞"
))

# Moon 3.2: Tone Calibration
skills.append(_create_skill(
    "tone_calibration",
    "Tone Calibration",
    "Fine-tune tone for specific contexts",
    "social_intelligence",
    "moon",
    "communication_adaptation",
    "communication_adaptation",
    icon="🎚️"
))

# Planet 4: Debate & Persuasion
skills.append(_create_skill(
    "debate_persuasion",
    "Debate & Persuasion",
    "Arguments, influence, and constructive disagreement",
    "social_intelligence",
    "planet",
    "social_intelligence",
    tool_reward="steelman",
    icon="⚖️"
))

# Moon 4.1: Counter-Arguments
skills.append(_create_skill(
    "counter_arguments",
    "Counter-Arguments",
    "Generate thoughtful opposing viewpoints",
    "social_intelligence",
    "moon",
    "debate_persuasion",
    "debate_persuasion",
    icon="🔄"
))

# Moon 4.2: Logical Analysis
skills.append(_create_skill(
    "logical_analysis",
    "Logical Analysis",
    "Identify logical fallacies and weak arguments",
    "social_intelligence",
    "moon",
    "debate_persuasion",
    "debate_persuasion",
    icon="🔍"
))

# Planet 5: Trust & Boundaries
skills.append(_create_skill(
    "trust_boundaries",
    "Trust & Boundaries",
    "Self-protection and trust assessment",
    "social_intelligence",
    "planet",
    "social_intelligence",
    tool_reward="assess_trust_level",
    icon="🛡️"
))

# Moon 5.1: Manipulation Detection
skills.append(_create_skill(
    "social_manipulation_detection",
    "Manipulation Detection",
    "Spot emotional manipulation, gaslighting, and pressure tactics",
    "social_intelligence",
    "moon",
    "trust_boundaries",
    "trust_boundaries",
    icon="⚠️"
))

# Moon 5.2: Boundary Setting
skills.append(_create_skill(
    "boundary_setting",
    "Boundary Setting",
    "Evaluate if a request is appropriate to fulfill",
    "social_intelligence",
    "moon",
    "trust_boundaries",
    "trust_boundaries",
    icon="🚧"
))
```

---

## 4. Task 2.2: Update TOOL_TO_SKILL_MAPPING

**File:** `ai/skill_scanner.py`
**Lines:** 44-85

### Add New Mappings

```python
TOOL_TO_SKILL_MAPPING = {
    # ... existing mappings ...

    # =========================================
    # SOCIAL INTELLIGENCE - Social & Emotional Learning
    # =========================================

    # Sun Tool
    "get_relationship_context": "social_intelligence",

    # Planet 1: Relationship Memory
    "recall_relationship_history": "relationship_memory",

    # Moon 1.1, 1.2
    "analyze_interaction_patterns": "interaction_patterns",
    "get_relationship_timeline": "relationship_timeline",

    # Planet 2: Emotional Learning
    "read_emotional_state": "emotional_learning",

    # Moon 2.1, 2.2
    "track_emotional_patterns": "emotional_history",
    "detect_mood_shift": "mood_awareness",

    # Planet 3: Communication Adaptation
    "adapt_communication_style": "communication_adaptation",

    # Moon 3.1, 3.2
    "match_communication_style": "style_matching",
    "calibrate_tone": "tone_calibration",

    # Planet 4: Debate & Persuasion
    "steelman": "debate_persuasion",

    # Moon 4.1, 4.2
    "devils_advocate": "counter_arguments",
    "spot_fallacy": "logical_analysis",

    # Planet 5: Trust & Boundaries
    "assess_trust_level": "trust_boundaries",

    # Moon 5.1, 5.2
    "detect_social_manipulation": "social_manipulation_detection",
    "evaluate_request": "boundary_setting",

    # ... rest of existing mappings ...
}
```

### Remove Old Mappings

Delete these obsolete mappings:
```python
# DELETE THESE:
"draft_message_variants": "communication",
"predict_reaction": "empathy",
"build_rapport_strategy": "relationship_building",
```

---

## 5. Task 2.3: Implement Sun Tool - get_relationship_context

### Purpose

Get full context about a relationship before responding. This is the Social Intelligence Sun tool, always available.

### Handler Implementation

**File:** `ai/tools/handlers.py`

```python
# =============================================================================
# SOCIAL INTELLIGENCE - SOCIAL & EMOTIONAL LEARNING TOOLS
# =============================================================================

def generate_relationship_warnings(relationship) -> list:
    """Generate warnings based on relationship state."""
    warnings = []
    if relationship.betrayal > 50:
        warnings.append("HIGH BETRAYAL HISTORY - exercise caution")
    if relationship.manipulation > 60:
        warnings.append("MANIPULATION DETECTED in past interactions")
    if relationship.trust < 30:
        warnings.append("LOW TRUST - verify claims independently")
    if relationship.distrust > 60:
        warnings.append("HIGH DISTRUST - relationship is strained")
    if relationship.tension > 70:
        warnings.append("HIGH TENSION - tread carefully")
    if hasattr(relationship, 'is_blocked') and relationship.is_blocked():
        warnings.append("THIS ENTITY IS BLOCKED")
    return warnings


async def get_relationship_context_handler(qube, params: dict) -> dict:
    """
    Get comprehensive relationship context for an entity.
    Leverages the existing 48-field Relationship class.

    The Social Intelligence Sun tool - always available.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "Please provide an entity_id to get relationship context for"
            }

        # Get social dynamics manager
        if not hasattr(qube, 'social_dynamics_manager'):
            return {
                "success": False,
                "error": "Social dynamics manager not available"
            }

        social_manager = qube.social_dynamics_manager
        relationship = social_manager.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "known": False,
                "entity_id": entity_id,
                "message": f"No prior relationship with {entity_id}",
                "recommendation": "Start with low-risk interactions to build history"
            }

        # Calculate trust score
        trust_score = 0
        if hasattr(social_manager, 'trust_scorer'):
            trust_score = social_manager.trust_scorer.calculate_trust_score(relationship)
        else:
            # Fallback: simple average of core metrics
            trust_score = (relationship.honesty + relationship.reliability +
                          relationship.support + relationship.loyalty +
                          relationship.respect) / 5

        # Generate warnings
        warnings = generate_relationship_warnings(relationship)

        return {
            "success": True,
            "known": True,
            "entity_id": entity_id,
            "status": relationship.status,
            "trust_score": round(trust_score, 1),
            "days_known": relationship.days_known,
            "interaction_count": relationship.messages_sent + relationship.messages_received,
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
                    "understanding": relationship.understanding,
                    "friendship": relationship.friendship
                },
                "negative": {
                    "tension": relationship.tension,
                    "resentment": relationship.resentment,
                    "betrayal": relationship.betrayal,
                    "distrust": relationship.distrust
                }
            },
            "communication_style": {
                "verbosity": relationship.verbosity,
                "directness": relationship.directness,
                "energy_level": relationship.energy_level,
                "humor_style": relationship.humor_style
            },
            "warnings": warnings,
            "recommendation": "Safe to proceed" if not warnings else f"Proceed with caution: {len(warnings)} warning(s)"
        }

    except Exception as e:
        logger.error(f"get_relationship_context_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 6. Task 2.4: Implement Relationship Memory Planet

### Planet Tool: recall_relationship_history

```python
async def recall_relationship_history_handler(qube, params: dict) -> dict:
    """
    Search memory chain for interactions with a specific entity.
    Combines relationship data with block search.
    """
    try:
        entity_id = params.get("entity_id")
        topic = params.get("topic")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        social_manager = qube.social_dynamics_manager
        relationship = social_manager.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "known": False,
                "message": f"No history with {entity_id}"
            }

        # Search memory chain for blocks involving this entity
        query = topic if topic else entity_id
        results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context={
                "participants": [entity_id],
                "decay_rate": 0.01,  # Include old memories
            },
            top_k=20
        )

        # Categorize interactions
        conversations = []
        collaborations = []

        for r in results:
            block = r.block
            block_type = block.get("block_type", "")

            if block_type == "MESSAGE":
                conversations.append({
                    "summary": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_number": block.get("block_number", 0)
                })
            elif block_type == "ACTION":
                content = block.get("content", {})
                if "collaboration" in str(content).lower() or content.get("participants"):
                    collaborations.append({
                        "task": extract_summary_from_block(block),
                        "outcome": "Success" if content.get("success") else "Failed",
                        "when": format_relative_time(block.get("timestamp", 0))
                    })

        return {
            "success": True,
            "entity_id": entity_id,
            "relationship_status": relationship.status,
            "first_contact": format_relative_time(relationship.first_contact) if relationship.first_contact else "Unknown",
            "days_known": relationship.days_known,
            "total_interactions": relationship.messages_sent + relationship.messages_received,
            "recent_conversations": conversations[:5],
            "collaborations": {
                "total": relationship.collaborations,
                "successful": relationship.collaborations_successful,
                "failed": relationship.collaborations_failed,
                "recent": collaborations[:3]
            },
            "topic_filter": topic,
            "memories_found": len(results)
        }

    except Exception as e:
        logger.error(f"recall_relationship_history_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 1.1: analyze_interaction_patterns

```python
async def analyze_interaction_patterns_handler(qube, params: dict) -> dict:
    """
    Analyze interaction patterns with an entity.
    Who initiates, how often, response times, etc.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Calculate patterns
        total_messages = relationship.messages_sent + relationship.messages_received
        if total_messages == 0:
            return {
                "success": True,
                "entity_id": entity_id,
                "message": "No messages exchanged yet"
            }

        initiation_ratio = relationship.messages_sent / total_messages

        # Analyze timing patterns from memory
        results = await intelligent_memory_search(
            qube=qube,
            query="",
            context={
                "participants": [entity_id],
                "block_types": ["MESSAGE"]
            },
            top_k=100
        )

        # Time distribution analysis
        timestamps = [r.block.get("timestamp", 0) for r in results]
        time_patterns = {}

        if len(timestamps) >= 2:
            # Calculate average gap between messages
            gaps = [timestamps[i] - timestamps[i+1] for i in range(len(timestamps)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0

            if avg_gap < 3600:  # Less than 1 hour
                frequency = "very_frequent"
            elif avg_gap < 86400:  # Less than 1 day
                frequency = "daily"
            elif avg_gap < 604800:  # Less than 1 week
                frequency = "weekly"
            else:
                frequency = "occasional"

            time_patterns = {
                "message_frequency": frequency,
                "avg_gap_hours": round(avg_gap / 3600, 1),
                "total_messages_found": len(timestamps)
            }

        # Determine initiation assessment
        if 0.4 <= initiation_ratio <= 0.6:
            initiation_assessment = "balanced"
        elif initiation_ratio > 0.6:
            initiation_assessment = "you reach out more"
        else:
            initiation_assessment = "they reach out more"

        return {
            "success": True,
            "entity_id": entity_id,
            "total_interactions": total_messages,
            "messages_sent": relationship.messages_sent,
            "messages_received": relationship.messages_received,
            "initiation_balance": {
                "you_initiate": f"{initiation_ratio:.0%}",
                "they_initiate": f"{1-initiation_ratio:.0%}",
                "assessment": initiation_assessment
            },
            "response_patterns": {
                "avg_response_time_seconds": relationship.response_time_avg,
                "responsiveness_score": relationship.responsiveness
            },
            "timing_patterns": time_patterns,
            "insights": generate_pattern_insights(relationship, initiation_ratio)
        }

    except Exception as e:
        logger.error(f"analyze_interaction_patterns_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def generate_pattern_insights(relationship, initiation_ratio: float) -> list:
    """Generate insights from interaction patterns."""
    insights = []

    if initiation_ratio > 0.7:
        insights.append("You're doing most of the reaching out. Consider letting them initiate sometimes.")
    elif initiation_ratio < 0.3:
        insights.append("They reach out frequently - they value this relationship.")

    if relationship.responsiveness > 80:
        insights.append("They respond quickly - high engagement.")
    elif relationship.responsiveness < 30:
        insights.append("Slow responses - they may be busy or less engaged.")

    if relationship.messages_sent + relationship.messages_received > 100:
        insights.append("Significant conversation history - established relationship.")

    return insights
```

### Moon Tool 1.2: get_relationship_timeline

```python
async def get_relationship_timeline_handler(qube, params: dict) -> dict:
    """
    Get timeline of relationship evolution.
    Status changes, key moments, trust progression.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Build timeline
        timeline = []

        # Add first contact
        if relationship.first_contact:
            timeline.append({
                "event": "First Contact",
                "timestamp": relationship.first_contact,
                "when": format_relative_time(relationship.first_contact),
                "status": "stranger",
                "significance": "high"
            })

        # Get progression history if available
        progression_history = getattr(relationship, 'progression_history', []) or []
        for progression in progression_history:
            timeline.append({
                "event": f"Status changed to {progression.get('new_status', 'unknown')}",
                "timestamp": progression.get('timestamp', 0),
                "when": format_relative_time(progression.get('timestamp', 0)),
                "status": progression.get('new_status'),
                "reason": progression.get('reason'),
                "significance": "high"
            })

        # Get evaluations if available
        evaluations = getattr(relationship, 'evaluations', []) or []
        for eval_data in evaluations:
            trust_change = eval_data.get('trust_change', 0)
            if abs(trust_change) > 10:
                timeline.append({
                    "event": "Significant trust change",
                    "timestamp": eval_data.get('timestamp', 0),
                    "when": format_relative_time(eval_data.get('timestamp', 0)),
                    "change": trust_change,
                    "reason": eval_data.get('reason'),
                    "significance": "medium"
                })

        # Sort by timestamp (most recent first)
        timeline.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        # Generate journey summary
        journey_summary = f"Known for {relationship.days_known} days. "
        if relationship.status in ["friend", "close_friend", "best_friend"]:
            journey_summary += f"Grew from stranger to {relationship.status}."
        elif relationship.status in ["suspicious", "rival", "enemy"]:
            journey_summary += f"Relationship has become {relationship.status}."
        else:
            journey_summary += f"Currently {relationship.status}."

        return {
            "success": True,
            "entity_id": entity_id,
            "current_status": relationship.status,
            "days_known": relationship.days_known,
            "timeline": timeline[:10],  # Last 10 events
            "journey_summary": journey_summary
        }

    except Exception as e:
        logger.error(f"get_relationship_timeline_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 7. Task 2.5: Implement Emotional Learning Planet

### Planet Tool: read_emotional_state

```python
async def read_emotional_state_handler(qube, params: dict) -> dict:
    """
    Analyze emotional state using 24 emotional metrics (14 positive, 10 negative).
    """
    try:
        entity_id = params.get("entity_id")
        current_message = params.get("current_message")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

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

        # Interpret balance
        if emotional_balance > 20:
            interpretation = "positive"
            recommendation = "Relationship is healthy - continue building on positive interactions"
        elif emotional_balance < -20:
            interpretation = "negative"
            recommendation = "Relationship needs attention - address underlying issues"
        else:
            interpretation = "neutral"
            recommendation = "Relationship is balanced - maintain current approach"

        # Generate warnings for high negative emotions
        warnings = [
            f"High {emotion}: {value}" for emotion, value in negative_metrics.items()
            if value > 60
        ]

        return {
            "success": True,
            "entity_id": entity_id,
            "emotional_balance": {
                "score": round(emotional_balance, 1),
                "interpretation": interpretation,
                "avg_positive": round(avg_positive, 1),
                "avg_negative": round(avg_negative, 1)
            },
            "dominant_positive_emotions": [
                {"emotion": e[0], "strength": e[1]} for e in top_positive if e[1] > 30
            ],
            "dominant_negative_emotions": [
                {"emotion": e[0], "strength": e[1]} for e in top_negative if e[1] > 30
            ],
            "warnings": warnings,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"read_emotional_state_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 2.1: track_emotional_patterns

```python
async def track_emotional_patterns_handler(qube, params: dict) -> dict:
    """
    Track what causes positive/negative emotional responses over time.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Get evaluation history
        evaluations = getattr(relationship, 'evaluations', []) or []

        # Analyze patterns
        positive_triggers = []
        negative_triggers = []

        for eval_data in evaluations:
            affection_change = eval_data.get('affection_change', 0)
            warmth_change = eval_data.get('warmth_change', 0)
            tension_change = eval_data.get('tension_change', 0)
            resentment_change = eval_data.get('resentment_change', 0)

            if affection_change > 5 or warmth_change > 5:
                positive_triggers.append({
                    "trigger": eval_data.get('reason', 'Unknown positive event'),
                    "impact": affection_change + warmth_change,
                    "when": format_relative_time(eval_data.get('timestamp', 0))
                })

            if tension_change > 5 or resentment_change > 5:
                negative_triggers.append({
                    "trigger": eval_data.get('reason', 'Unknown negative event'),
                    "impact": tension_change + resentment_change,
                    "when": format_relative_time(eval_data.get('timestamp', 0))
                })

        # Search memory for emotional context
        positive_memories = await intelligent_memory_search(
            qube=qube,
            query="happy grateful appreciated thank wonderful great",
            context={"participants": [entity_id]},
            top_k=10
        )

        negative_memories = await intelligent_memory_search(
            qube=qube,
            query="upset frustrated disappointed angry annoyed problem",
            context={"participants": [entity_id]},
            top_k=10
        )

        # Extract topics from memories
        positive_topics = [extract_summary_from_block(r.block)[:50] for r in positive_memories[:3]]
        negative_topics = [extract_summary_from_block(r.block)[:50] for r in negative_memories[:3]]

        return {
            "success": True,
            "entity_id": entity_id,
            "positive_triggers": positive_triggers[:5],
            "negative_triggers": negative_triggers[:5],
            "things_that_make_them_happy": positive_topics,
            "things_that_upset_them": negative_topics,
            "recommendations": {
                "do_more": [t["trigger"] for t in positive_triggers[:3]] if positive_triggers else ["Build positive experiences together"],
                "avoid": [t["trigger"] for t in negative_triggers[:3]] if negative_triggers else ["No specific triggers identified"]
            }
        }

    except Exception as e:
        logger.error(f"track_emotional_patterns_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 2.2: detect_mood_shift

```python
async def detect_mood_shift_handler(qube, params: dict) -> dict:
    """
    Detect if someone's mood has shifted from their baseline.
    """
    try:
        entity_id = params.get("entity_id")
        current_message = params.get("current_message")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}
        if not current_message:
            return {"success": False, "error": "current_message required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Analyze current message sentiment (simple heuristic)
        message_lower = current_message.lower()

        positive_words = ["happy", "great", "wonderful", "love", "thank", "awesome", "amazing", "excited", "!"]
        negative_words = ["sad", "angry", "frustrated", "upset", "disappointed", "worried", "sorry", "problem", "issue"]

        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        current_sentiment = {
            "positivity": min(10, positive_count * 2),
            "negativity": min(10, negative_count * 2)
        }

        # Get baseline from relationship metrics
        baseline_positive = (relationship.warmth + relationship.affection +
                            relationship.engagement) / 3
        baseline_negative = (relationship.tension + relationship.antagonism +
                            relationship.annoyance) / 3
        baseline_mood = (baseline_positive - baseline_negative) / 10  # Normalize to -10 to +10

        # Compare to current
        current_mood = current_sentiment["positivity"] - current_sentiment["negativity"]
        mood_shift = current_mood - baseline_mood

        # Determine shift type
        if mood_shift > 3:
            shift_type = "more_positive"
            recommendation = "They seem happier than usual - good time for requests or deeper conversation"
            suggested_tone = "enthusiastic"
        elif mood_shift < -3:
            shift_type = "more_negative"
            recommendation = "They seem upset - consider asking if everything is okay, be supportive"
            suggested_tone = "supportive"
        else:
            shift_type = "stable"
            recommendation = "Mood is consistent with baseline - proceed normally"
            suggested_tone = "normal"

        return {
            "success": True,
            "entity_id": entity_id,
            "mood_shift_detected": abs(mood_shift) > 3,
            "shift_type": shift_type,
            "shift_magnitude": round(mood_shift, 1),
            "current_sentiment": current_sentiment,
            "baseline_mood": round(baseline_mood, 1),
            "recommendation": recommendation,
            "suggested_response_tone": suggested_tone
        }

    except Exception as e:
        logger.error(f"detect_mood_shift_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 8. Task 2.6: Implement Communication Adaptation Planet

### Planet Tool: adapt_communication_style

```python
async def adapt_communication_style_handler(qube, params: dict) -> dict:
    """
    Get communication style recommendations based on relationship data.
    """
    try:
        entity_id = params.get("entity_id")
        message_type = params.get("message_type", "casual")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "recommendation": "No prior relationship - start with a friendly, professional tone"
            }

        # Analyze behavioral metrics
        style_profile = {
            "verbosity": relationship.verbosity,
            "directness": relationship.directness,
            "energy_level": relationship.energy_level,
            "humor_style": relationship.humor_style,
            "patience": relationship.patience,
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
            recommendations["formality"] = "friendly but balanced"

        # Adjust for message type
        if message_type == "sensitive":
            recommendations["approach"] = "extra care - be gentle and supportive"
        elif message_type == "professional":
            recommendations["approach"] = "focus on facts and clarity"
        else:
            recommendations["approach"] = "natural and authentic"

        # Generate summary
        summary_parts = []
        if style_profile["verbosity"] > 60:
            summary_parts.append("be detailed")
        elif style_profile["verbosity"] < 40:
            summary_parts.append("be concise")

        if style_profile["directness"] > 60:
            summary_parts.append("be direct")
        elif style_profile["directness"] < 40:
            summary_parts.append("be diplomatic")

        if style_profile["humor_style"] > 60:
            summary_parts.append("humor is welcome")

        summary = "For this person: " + ", ".join(summary_parts) if summary_parts else "Use a balanced approach"

        return {
            "success": True,
            "entity_id": entity_id,
            "relationship_status": relationship.status,
            "style_profile": style_profile,
            "recommendations": recommendations,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"adapt_communication_style_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 3.1: match_communication_style

```python
async def match_communication_style_handler(qube, params: dict) -> dict:
    """
    Analyze their communication style from a message and recommend matching.
    """
    try:
        entity_id = params.get("entity_id")
        their_message = params.get("their_message")

        if not their_message:
            return {"success": False, "error": "their_message required"}

        # Analyze the message
        message_length = len(their_message)
        words = their_message.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        # Check for indicators
        uses_emoji = any(ord(c) > 127 for c in their_message)  # Simple emoji detection
        exclamation_marks = their_message.count("!")
        question_marks = their_message.count("?")

        # Formality indicators
        formal_words = ["please", "thank you", "kindly", "would you", "could you", "appreciate"]
        casual_words = ["hey", "yeah", "gonna", "wanna", "lol", "haha", "cool"]

        formal_count = sum(1 for word in formal_words if word in their_message.lower())
        casual_count = sum(1 for word in casual_words if word in their_message.lower())

        if formal_count > casual_count:
            formality_score = 0.7
            formality = "formal"
        elif casual_count > formal_count:
            formality_score = 0.3
            formality = "casual"
        else:
            formality_score = 0.5
            formality = "moderate"

        message_analysis = {
            "length": message_length,
            "word_count": len(words),
            "avg_word_length": round(avg_word_length, 1),
            "uses_emoji": uses_emoji,
            "exclamation_marks": exclamation_marks,
            "question_marks": question_marks,
            "formality": formality
        }

        # Generate matching style
        matching_style = {
            "length": "match their length" if message_length < 100 else
                      "they wrote a lot - feel free to be detailed",

            "emoji": "use emoji" if uses_emoji else "skip emoji",

            "energy": "match their energy with exclamations!" if exclamation_marks > 1 else
                      "keep it calm",

            "formality": formality,

            "engagement": "they asked questions - be thorough in answering" if question_marks > 0 else
                          "statement-based - respond in kind"
        }

        return {
            "success": True,
            "entity_id": entity_id,
            "their_message_analysis": message_analysis,
            "matching_style": matching_style,
            "tip": "Mirroring communication style builds rapport and comfort"
        }

    except Exception as e:
        logger.error(f"match_communication_style_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 3.2: calibrate_tone

```python
async def calibrate_tone_handler(qube, params: dict) -> dict:
    """
    Calibrate tone for a specific conversation context.
    """
    try:
        entity_id = params.get("entity_id")
        topic = params.get("topic", "general")
        context = params.get("context", "general")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)
        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "calibrated_tone": {
                    "warmth": "neutral",
                    "energy": "moderate",
                    "approach": "professional and friendly"
                }
            }

        # Base tone from relationship
        base_warmth = relationship.warmth
        base_openness = relationship.openness
        trust_level = relationship.trust

        # Context adjustments
        tone_adjustments = {
            "good_news": {
                "warmth_modifier": "+20",
                "energy": "high",
                "approach": "enthusiastic, share in their joy"
            },
            "bad_news": {
                "warmth_modifier": "+10",
                "energy": "low",
                "approach": "gentle, supportive, give space for reaction"
            },
            "request": {
                "warmth_modifier": "neutral",
                "energy": "moderate",
                "approach": "clear and respectful, acknowledge their autonomy"
            },
            "conflict": {
                "warmth_modifier": "careful",
                "energy": "calm",
                "approach": "non-defensive, seek understanding, validate feelings"
            },
            "general": {
                "warmth_modifier": "match baseline",
                "energy": "match their energy",
                "approach": "natural and authentic"
            }
        }

        adjustment = tone_adjustments.get(context, tone_adjustments["general"])

        # Add cautions based on relationship state
        cautions = []
        if trust_level < 40:
            cautions.append("Low trust - be extra careful with word choice")
        if relationship.tension > 50:
            cautions.append("There's underlying tension - tread carefully")
        if relationship.resentment > 40:
            cautions.append("Some resentment present - acknowledge past issues if relevant")

        # Generate contextual opening
        if context == "good_news":
            suggested_opening = "That's wonderful! "
        elif context == "bad_news":
            suggested_opening = "I understand this is difficult. "
        elif context == "request":
            suggested_opening = "I wanted to ask you something. "
        elif context == "conflict":
            suggested_opening = "I'd like to understand your perspective. "
        else:
            suggested_opening = None

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
            "cautions": cautions,
            "suggested_opening": suggested_opening
        }

    except Exception as e:
        logger.error(f"calibrate_tone_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 9. Task 2.7: Implement Debate & Persuasion Planet

### Planet Tool: steelman

```python
async def steelman_handler(qube, params: dict) -> dict:
    """
    Present the strongest possible version of any argument.
    The opposite of a strawman - find the best interpretation.
    """
    try:
        argument = params.get("argument")
        perspective = params.get("perspective")

        if not argument:
            return {"success": False, "error": "argument required"}

        # Search memory for related past discussions
        related = await intelligent_memory_search(
            qube=qube,
            query=argument,
            context={"block_types": ["MESSAGE", "DECISION"]},
            top_k=5
        )

        # Extract core claim (simple heuristic)
        sentences = argument.split('.')
        core_claim = sentences[0].strip() if sentences else argument

        # Note: In a full implementation, this would use AI to generate
        # the steelmanned version. Here we provide the structure.

        return {
            "success": True,
            "original_argument": argument,
            "perspective": perspective or "general",
            "steelmanned_version": {
                "core_claim": core_claim,
                "strongest_form": f"The most charitable interpretation of '{core_claim}' would be...",
                "key_supporting_points": [
                    "Consider the underlying values being expressed",
                    "What legitimate concerns does this address?",
                    "In what contexts would this be most valid?"
                ],
                "most_charitable_interpretation": "Assume good faith and valid reasoning",
                "valid_concerns_addressed": []
            },
            "related_past_discussions": [
                extract_summary_from_block(r.block)[:100] for r in related[:3]
            ],
            "note": "This is the strongest version of this argument - argue against THIS, not a weaker version"
        }

    except Exception as e:
        logger.error(f"steelman_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 4.1: devils_advocate

```python
async def devils_advocate_handler(qube, params: dict) -> dict:
    """
    Generate thoughtful counter-arguments to a position.
    """
    try:
        position = params.get("position")
        depth = params.get("depth", "moderate")

        if not position:
            return {"success": False, "error": "position required"}

        # Search for related discussions
        related = await intelligent_memory_search(
            qube=qube,
            query=position,
            top_k=10
        )

        # Look for past counter-arguments
        counter_arguments = []
        for r in related:
            content = str(r.block.get("content", "")).lower()
            if any(word in content for word in ["however", "but", "disagree", "counter", "alternatively"]):
                counter_arguments.append(extract_summary_from_block(r.block)[:100])

        # Structure for devil's advocate response
        response = {
            "success": True,
            "original_position": position,
            "counter_arguments": {
                "practical_concerns": [
                    "What are the implementation challenges?",
                    "What resources would this require?",
                    "What could go wrong in practice?"
                ],
                "logical_concerns": [
                    "Are there hidden assumptions?",
                    "What evidence would disprove this?",
                    "Are there exceptions to consider?"
                ],
                "value_concerns": [
                    "Whose interests are served or harmed?",
                    "What trade-offs are being made?",
                    "Are there alternative approaches?"
                ]
            },
            "from_past_discussions": counter_arguments[:3] if counter_arguments else ["No prior counter-arguments found"],
            "note": "Playing devil's advocate helps strengthen arguments by identifying weaknesses"
        }

        return response

    except Exception as e:
        logger.error(f"devils_advocate_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 4.2: spot_fallacy

```python
async def spot_fallacy_handler(qube, params: dict) -> dict:
    """
    Identify logical fallacies in an argument.
    """
    try:
        argument = params.get("argument")

        if not argument:
            return {"success": False, "error": "argument required"}

        argument_lower = argument.lower()

        # Common fallacy patterns
        fallacy_patterns = {
            "ad_hominem": {
                "keywords": ["you're just", "typical of", "people like you", "what do you know"],
                "description": "Attacking the person rather than the argument"
            },
            "strawman": {
                "keywords": ["so you're saying", "what you really mean", "in other words"],
                "description": "Misrepresenting someone's argument to make it easier to attack"
            },
            "false_dilemma": {
                "keywords": ["either...or", "only two options", "you must choose", "if you don't...then"],
                "description": "Presenting only two options when more exist"
            },
            "appeal_to_authority": {
                "keywords": ["experts say", "studies show", "scientists agree", "everyone knows"],
                "description": "Using authority as evidence without proper citation"
            },
            "slippery_slope": {
                "keywords": ["if we allow", "next thing you know", "will lead to", "before you know it"],
                "description": "Claiming one thing will inevitably lead to extreme consequences"
            },
            "appeal_to_emotion": {
                "keywords": ["think of the children", "how would you feel", "imagine if"],
                "description": "Using emotions rather than logic to make an argument"
            },
            "bandwagon": {
                "keywords": ["everyone is doing", "most people think", "popular opinion"],
                "description": "Arguing something is true because many people believe it"
            },
            "circular_reasoning": {
                "keywords": ["because it is", "that's just how it is", "it's true because"],
                "description": "Using the conclusion as a premise"
            }
        }

        # Check for fallacies
        detected_fallacies = []
        for fallacy_name, fallacy_info in fallacy_patterns.items():
            matches = [kw for kw in fallacy_info["keywords"] if kw in argument_lower]
            if matches:
                detected_fallacies.append({
                    "fallacy": fallacy_name.replace("_", " ").title(),
                    "description": fallacy_info["description"],
                    "indicators": matches,
                    "severity": "medium"
                })

        if detected_fallacies:
            assessment = f"Found {len(detected_fallacies)} potential logical fallacy(ies)"
            recommendation = "Consider revising the argument to address these logical issues"
        else:
            assessment = "No obvious logical fallacies detected"
            recommendation = "The argument appears logically structured, but consider having it reviewed"

        return {
            "success": True,
            "argument_analyzed": argument[:200] + "..." if len(argument) > 200 else argument,
            "fallacies_detected": len(detected_fallacies),
            "fallacies": detected_fallacies,
            "assessment": assessment,
            "recommendation": recommendation,
            "note": "This is pattern-based detection - subtle fallacies may require deeper analysis"
        }

    except Exception as e:
        logger.error(f"spot_fallacy_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 10. Task 2.8: Implement Trust & Boundaries Planet

### Planet Tool: assess_trust_level

```python
async def assess_trust_level_handler(qube, params: dict) -> dict:
    """
    Evaluate trustworthiness for a specific action.
    Uses all 5 core trust metrics + betrayal history.
    """
    try:
        entity_id = params.get("entity_id")
        action = params.get("action", "general interaction")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "trust_level": "unknown",
                "trust_score": 0,
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

        # Calculate trust score
        trust_score = sum(trust_metrics.values()) / len(trust_metrics)

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
        if hasattr(relationship, 'is_blocked') and relationship.is_blocked():
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
        action_risk = assess_action_risk(action)
        action_recommendation = generate_action_recommendation(trust_level, action_risk, action)

        return {
            "success": True,
            "entity_id": entity_id,
            "known": True,
            "trust_score": round(trust_score, 1),
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

    except Exception as e:
        logger.error(f"assess_trust_level_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def assess_action_risk(action: str) -> str:
    """Assess the risk level of an action."""
    action_lower = action.lower()

    critical_keywords = ["all", "everything", "full access", "admin", "owner", "password", "private key"]
    high_risk_keywords = ["money", "send", "secret", "private", "access", "permission", "share"]
    medium_keywords = ["share", "tell", "give", "information"]

    if any(kw in action_lower for kw in critical_keywords):
        return "critical"
    elif any(kw in action_lower for kw in high_risk_keywords):
        return "high"
    elif any(kw in action_lower for kw in medium_keywords):
        return "medium"
    else:
        return "low"


def generate_action_recommendation(trust_level: str, action_risk: str, action: str) -> str:
    """Generate action-specific recommendation."""
    if trust_level == "blocked":
        return "DO NOT PROCEED - entity is blocked"

    if action_risk == "critical":
        if trust_level in ["high"]:
            return "High-risk action - proceed with verification even for trusted entities"
        else:
            return "DENY - critical action requires highest trust level"

    if action_risk == "high":
        if trust_level in ["high", "moderate"]:
            return "Proceed with caution - verify the request"
        else:
            return "NOT RECOMMENDED - trust level too low for this action"

    if action_risk == "medium":
        if trust_level in ["high", "moderate", "low"]:
            return "Acceptable - proceed normally"
        else:
            return "Use caution - limited trust for this entity"

    return "Safe to proceed"
```

### Moon Tool 5.1: detect_social_manipulation

```python
async def detect_social_manipulation_handler(qube, params: dict) -> dict:
    """
    Detect SOCIAL manipulation tactics in a message from humans.
    Checks for guilt trips, gaslighting, love bombing, etc.
    """
    try:
        entity_id = params.get("entity_id")
        message = params.get("message")
        context = params.get("context")

        if not message:
            return {"success": False, "error": "message required"}

        relationship = None
        if entity_id:
            relationship = qube.social_dynamics_manager.get_relationship(entity_id)

        message_lower = message.lower()

        # Known manipulation tactics to detect
        manipulation_patterns = {
            "urgency": {
                "keywords": ["urgent", "immediately", "right now", "don't wait", "limited time", "act now"],
                "severity": "medium"
            },
            "guilt_trip": {
                "keywords": ["after all i've done", "i thought we were friends", "you owe me", "i sacrificed"],
                "severity": "high"
            },
            "flattery": {
                "keywords": ["only you can", "you're the only one", "you're special", "chosen one", "nobody else"],
                "severity": "medium"
            },
            "gaslighting": {
                "keywords": ["you're imagining", "that never happened", "you're crazy", "you're overreacting", "you're too sensitive"],
                "severity": "high"
            },
            "threats": {
                "keywords": ["or else", "consequences", "you'll regret", "if you don't", "i'll tell everyone"],
                "severity": "high"
            },
            "isolation": {
                "keywords": ["don't tell anyone", "keep this between us", "they wouldn't understand", "our secret"],
                "severity": "high"
            },
            "love_bombing": {
                "keywords": ["i love you so much", "you're perfect", "soulmate", "destiny", "meant to be"],
                "severity": "medium"
            },
            "moving_goalposts": {
                "keywords": ["but now", "one more thing", "also need", "before that", "actually"],
                "severity": "medium"
            },
            "false_scarcity": {
                "keywords": ["only chance", "never again", "last opportunity", "won't ask again"],
                "severity": "medium"
            }
        }

        # Check message against patterns
        detected_tactics = []
        for tactic, info in manipulation_patterns.items():
            matches = [kw for kw in info["keywords"] if kw in message_lower]
            if matches:
                detected_tactics.append({
                    "tactic": tactic.replace("_", " ").title(),
                    "indicators": matches,
                    "severity": info["severity"]
                })

        # Check entity history if available
        history_warning = None
        if relationship:
            if relationship.manipulation > 50:
                history_warning = f"This entity has a history of manipulation ({relationship.manipulation}/100)"
            elif relationship.betrayal > 30:
                history_warning = f"Previous betrayal detected ({relationship.betrayal}/100)"

        # Overall assessment
        high_severity = any(t["severity"] == "high" for t in detected_tactics)
        if detected_tactics:
            risk_level = "high" if high_severity else "medium"
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

    except Exception as e:
        logger.error(f"detect_social_manipulation_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Moon Tool 5.2: evaluate_request

```python
async def evaluate_request_handler(qube, params: dict) -> dict:
    """
    Evaluate if a request should be fulfilled.
    Checks clearance, trust level, and owner interests.
    """
    try:
        entity_id = params.get("entity_id")
        request = params.get("request")
        request_type = params.get("request_type", "general")

        if not request:
            return {"success": False, "error": "request required"}
        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.social_dynamics_manager.get_relationship(entity_id)

        # Check if this is the owner
        is_owner = False
        if hasattr(qube, 'chain_state'):
            owner = qube.chain_state.get_owner() if hasattr(qube.chain_state, 'get_owner') else None
            is_owner = (owner == entity_id)

        # Determine required clearance for this request
        request_clearance_map = {
            "public_info": "public",
            "professional": "professional",
            "personal": "social",
            "sensitive": "trusted",
            "private": "inner_circle",
            "critical": "family"
        }

        required_clearance = request_clearance_map.get(request_type, "social")

        # Check clearance
        has_clearance = False
        entity_clearance = "none"

        if is_owner:
            has_clearance = True
            entity_clearance = "owner"
        elif relationship:
            entity_clearance = getattr(relationship, 'clearance_profile', 'none') or "none"
            # Simple clearance hierarchy check
            clearance_levels = ["none", "public", "professional", "social", "trusted", "inner_circle", "family"]
            if entity_clearance in clearance_levels and required_clearance in clearance_levels:
                has_clearance = clearance_levels.index(entity_clearance) >= clearance_levels.index(required_clearance)

        # Assess trust
        trust_assessment = await assess_trust_level_handler(qube, {"entity_id": entity_id, "action": request})

        # Make decision
        if relationship and hasattr(relationship, 'is_blocked') and relationship.is_blocked():
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

        # Generate recommendation
        if is_owner:
            recommendation = "This is your owner - safe to proceed with any request"
        elif decision == "allow":
            recommendation = "Safe to proceed"
        elif decision == "caution":
            recommendation = f"Proceed with caution: {reason}. Consider asking owner for guidance."
        else:
            recommendation = f"Recommend declining: {reason}"

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
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"evaluate_request_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

---

## 11. Task 2.9: Register All Tools

**File:** `ai/tools/handlers.py` - in `register_default_tools()` function

Add all 16 tool registrations. See complete registration code in the master implementation file.

### Key Registrations

```python
# Sun Tool
registry.register(ToolDefinition(
    name="get_relationship_context",
    description="Get comprehensive context about a relationship before responding. Use this to understand history, trust level, and emotional state.",
    parameters={
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "ID of the entity to get relationship context for"
            }
        },
        "required": ["entity_id"]
    },
    handler=lambda params: get_relationship_context_handler(qube, params)
))

# Add to ALWAYS_AVAILABLE_TOOLS
ALWAYS_AVAILABLE_TOOLS.add("get_relationship_context")
```

---

## 12. Task 2.10: Frontend Synchronization

Update `qubes-gui/src/data/skillDefinitions.ts` with the new Social Intelligence structure matching the Python definitions.

---

## 13. Task 2.11: LEARNING Block Integration

### Tools That Create LEARNING Blocks

| Tool | Creates LEARNING | Learning Type | Trigger |
|------|------------------|---------------|---------|
| `get_relationship_context` | No | - | Read-only |
| `recall_relationship_history` | No | - | Read-only |
| `analyze_interaction_patterns` | Yes | `pattern` | When pattern detected |
| `track_emotional_patterns` | Yes | `pattern` | When trigger identified |
| `adapt_communication_style` | Optional | `fact` | When style preference learned |
| `assess_trust_level` | Yes | `relationship` | When trust assessment done |
| `detect_social_manipulation` | Yes | `relationship`, `fact` | When manipulation detected |

---

## 14. Task 2.12: Testing & Validation

### Manual Testing Checklist

- [ ] **get_relationship_context**: Returns full relationship data
- [ ] **recall_relationship_history**: Finds past interactions
- [ ] **analyze_interaction_patterns**: Calculates initiation ratio correctly
- [ ] **get_relationship_timeline**: Shows progression history
- [ ] **read_emotional_state**: Calculates emotional balance
- [ ] **track_emotional_patterns**: Identifies positive/negative triggers
- [ ] **detect_mood_shift**: Detects message sentiment changes
- [ ] **adapt_communication_style**: Returns style recommendations
- [ ] **match_communication_style**: Analyzes message style
- [ ] **calibrate_tone**: Adjusts for context
- [ ] **steelman**: Strengthens arguments
- [ ] **devils_advocate**: Generates counter-arguments
- [ ] **spot_fallacy**: Detects logical fallacies
- [ ] **assess_trust_level**: Calculates trust correctly
- [ ] **detect_social_manipulation**: Identifies manipulation tactics
- [ ] **evaluate_request**: Checks clearance and trust

---

## Appendix A: Tool Summary Table

| # | Tool | Type | Parent | XP Skill |
|---|------|------|--------|----------|
| 1 | `get_relationship_context` | Sun | - | `social_intelligence` |
| 2 | `recall_relationship_history` | Planet | social_intelligence | `relationship_memory` |
| 3 | `analyze_interaction_patterns` | Moon | relationship_memory | `interaction_patterns` |
| 4 | `get_relationship_timeline` | Moon | relationship_memory | `relationship_timeline` |
| 5 | `read_emotional_state` | Planet | social_intelligence | `emotional_learning` |
| 6 | `track_emotional_patterns` | Moon | emotional_learning | `emotional_history` |
| 7 | `detect_mood_shift` | Moon | emotional_learning | `mood_awareness` |
| 8 | `adapt_communication_style` | Planet | social_intelligence | `communication_adaptation` |
| 9 | `match_communication_style` | Moon | communication_adaptation | `style_matching` |
| 10 | `calibrate_tone` | Moon | communication_adaptation | `tone_calibration` |
| 11 | `steelman` | Planet | social_intelligence | `debate_persuasion` |
| 12 | `devils_advocate` | Moon | debate_persuasion | `counter_arguments` |
| 13 | `spot_fallacy` | Moon | debate_persuasion | `logical_analysis` |
| 14 | `assess_trust_level` | Planet | social_intelligence | `trust_boundaries` |
| 15 | `detect_social_manipulation` | Moon | trust_boundaries | `social_manipulation_detection` |
| 16 | `evaluate_request` | Moon | trust_boundaries | `boundary_setting` |

---

## Appendix B: Relationship System Reference

### 48 Fields Summary

| Category | Count | Fields |
|----------|-------|--------|
| Core Trust | 6 | honesty, reliability, support, loyalty, respect, trust |
| Positive Social | 14 | friendship, affection, engagement, depth, humor, understanding, compatibility, admiration, warmth, openness, patience, empowerment, responsiveness, expertise |
| Negative Social | 10 | antagonism, resentment, annoyance, distrust, rivalry, tension, condescension, manipulation, dismissiveness, betrayal |
| Behavioral | 6 | verbosity, punctuality, emotional_stability, directness, energy_level, humor_style |
| Statistics | 9 | messages_sent, messages_received, response_time_avg, last_interaction, collaborations, collaborations_successful, collaborations_failed, first_contact, days_known |
| State | 5 | has_met, status, blocked_at, blocked_reason, evaluations |

### Relationship Statuses

```python
"blocked": -100, "enemy": -50, "rival": -20, "suspicious": -10,
"unmet": 0, "stranger": 5, "acquaintance": 20, "friend": 50,
"close_friend": 75, "best_friend": 100
```

---

## Appendix C: Helper Functions

### Required Imports

```python
from relationships.relationship import Relationship
from ai.tools.memory_search import intelligent_memory_search
```

### Helper Functions List

| Function | Purpose |
|----------|---------|
| `generate_relationship_warnings()` | Generate warnings from relationship state |
| `generate_pattern_insights()` | Generate insights from interaction patterns |
| `assess_action_risk()` | Assess risk level of an action |
| `generate_action_recommendation()` | Generate action-specific recommendation |
| `format_relative_time()` | Convert timestamp to relative string |
| `extract_summary_from_block()` | Get brief summary from block |

---

**Document Complete**

*Generated for Qubes Skill Tree Implementation*
*Phase 2: Social Intelligence - Social & Emotional Learning*
