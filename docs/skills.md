# Skills System

Qubes have 141 skills across 8 categories, visualized as a solar system.

## Overview

The skills system uses a 3-tier hierarchy:
- **Sun** (8): Major categories, always unlocked
- **Planets** (40): Specific skills, must be earned through progression
- **Moons** (93): Sub-skills, must be earned through progression

## Always-Available Tools (17)

Every qube starts with 17 tools regardless of skill level:

| Tool | Purpose |
|------|---------|
| `get_system_state` | Read all state: relationships, skills, owner_info, mood, wallet |
| `update_system_state` | Write state: owner_info, mood, skills, settings |
| `get_skill_tree` | View all possible skills and progress |
| `recall_similar` | AI Reasoning Sun — find similar past experiences |
| `store_knowledge` | Memory & Recall Sun — store knowledge explicitly |
| `switch_model` | Creative Expression Sun — change AI model |
| `play_game` | Board Games Sun — start or continue a game |
| `send_bch` | Finance Sun — send Bitcoin Cash |
| `get_relationship_context` | Social Intelligence Sun — get relationship info |
| `verify_chain_integrity` | Security & Privacy Sun — verify chain integrity |
| `develop_code` | Coding Sun — write and develop code |
| `web_search` | Search the web for current information |
| `browse_url` | Fetch and read content from a URL |
| `generate_image` | Create images using AI image generation |
| `describe_my_avatar` | Look in the mirror — see own appearance |
| `recall` | Universal memory recall — search all storage systems |
| `process_document` | Document processing (automatic, tracked for progression) |

## Categories

| Category | Icon | Skills | Breakdown |
|----------|------|--------|-----------|
| AI Reasoning | 🧠 | 14 | 1S / 5P / 8M |
| Social Intelligence | 🤝 | 16 | 1S / 5P / 10M |
| Coding | 💻 | 18 | 1S / 5P / 12M |
| Creative Expression | 🎨 | 19 | 1S / 5P / 13M |
| Memory & Recall | 📚 | 16 | 1S / 5P / 10M |
| Security & Privacy | 🛡️ | 16 | 1S / 5P / 10M |
| Board Games | 🎮 | 28 | 1S / 5P / 22M |
| Finance | 💰 | 14 | 1S / 5P / 8M |

## Skill Structure

Each skill has:

```json
{
  "id": "pattern_recognition",
  "name": "Pattern Recognition",
  "description": "Finding similar situations in past experience",
  "category": "ai_reasoning",
  "nodeType": "planet",
  "tier": "novice",
  "level": 0,
  "xp": 0,
  "maxXP": 500,
  "unlocked": false,
  "parentSkill": "ai_reasoning",
  "prerequisite": "ai_reasoning",
  "toolCallReward": "find_analogy",
  "icon": "🔍",
  "evidence": []
}
```

## Progression and Levels

### Progress Requirements

| Node Type | Max Progress per Level |
|-----------|----------------------|
| Sun | 1000 |
| Planet | 500 |
| Moon | 250 |

### Level Tiers

| Level Range | Tier |
|-------------|------|
| 0-24 | Novice |
| 25-49 | Intermediate |
| 50-74 | Advanced |
| 75-100 | Expert |

### Progress Flow

When progress is awarded to a locked skill, it flows to the nearest unlocked parent:

```
Locked Moon → Parent Planet (if unlocked) → Parent Sun
```

## Unlocking Skills

- **Suns**: Always unlocked (starting point for each category)
- **Planets**: Must be earned — require parent Sun progression
- **Moons**: Must be earned — require parent Planet to be unlocked

When a skill reaches level 100, it unlocks a tool reward specific to that skill.

## Skill Tree

### AI Reasoning (14 skills)

**Sun**: AI Reasoning — `recall_similar`
- **Pattern Recognition** → Trend Detection, Quick Insight
- **Learning from Failure** → Root Cause Analysis
- **Building on Success** → Success Factors
- **Self-Reflection** → Growth Tracking, Bias Detection
- **Knowledge Synthesis** → Cross-Pollinate, Reflect on Topic

### Social Intelligence (16 skills)

**Sun**: Social Intelligence — `get_relationship_context`
- **Relationship Memory** → Interaction Patterns, Relationship Timeline
- **Emotional Learning** → Emotional History, Mood Awareness
- **Communication Adaptation** → Style Matching, Tone Calibration
- **Debate & Persuasion** → Counter Arguments, Logical Analysis
- **Trust & Boundaries** → Social Manipulation Detection, Boundary Setting

### Coding (18 skills)

**Sun**: Coding — `develop_code`
- **Testing** → Unit Tests, Test Coverage
- **Debugging** → Error Analysis, Root Cause
- **Algorithms** → Complexity Analysis, Performance Tuning
- **Hacking** → Exploits, Reverse Engineering, Penetration Testing
- **Code Review** → Refactoring, Version Control, Documentation

### Creative Expression (19 skills)

**Sun**: Creative Expression — `switch_model`
- **Visual Art** → Composition, Color Theory
- **Writing** → Prose, Poetry
- **Music & Audio** → Melody, Harmony
- **Storytelling** → Plot, Characters, Worldbuilding
- **Self-Definition** → Aesthetics, Voice, Personality, Aspirations

### Memory & Recall (16 skills)

**Sun**: Memory & Recall — `store_knowledge`
- **Memory Search** → Keyword Search, Semantic Search, Filtered Search
- **Knowledge Storage** → Procedures
- **Memory Organization** → Topic Tagging, Memory Linking
- **Knowledge Synthesis** → Pattern Recognition, Insight Generation
- **Documentation** → Summary Writing, Knowledge Export

### Security & Privacy (16 skills)

**Sun**: Security & Privacy — `verify_chain_integrity`
- **Chain Security** → Tamper Detection, Anchor Verification
- **Privacy Protection** → Data Classification, Sharing Control
- **Qube Network Security** → Reputation Check, Group Security
- **Threat Detection** → Technical Manipulation, Hostile Qube Detection
- **Self-Defense** → Injection Defense, Reasoning Validation

### Board Games (28 skills)

**Sun**: Board Games — `play_game`
- **Chess** → Opening Scholar, Endgame Master, Speed Demon, Comeback Kid, Grandmaster
- **Property Tycoon** → Monopolist, Hotel Mogul, Bankruptcy Survivor, Rent Collector, Tycoon
- **Race Home** → Bump King, Clean Sweep, Speed Runner, Sorry Not Sorry
- **Mystery Mansion** → Master Detective, Perfect Deduction, First Guess, Interrogator
- **Life Journey** → Millionaire, Full House, Career Climber, Risk Taker

### Finance (14 skills)

**Sun**: Finance — `send_bch`
- **Transaction Mastery** → Fee Optimization, Transaction Tracking
- **Wallet Management** → Balance Monitoring, Multi-sig Operations
- **Market Awareness** → Price Alerts, Market Trend Analysis
- **Savings Strategies** → Dollar Cost Averaging
- **Token Knowledge** → CashToken Operations

## Storage

Skills use compact storage in chain state to minimize size:

```json
{
  "skills": {
    "skill_xp": {
      "ai_reasoning": {"xp": 150, "level": 3},
      "pattern_recognition": {"xp": 75, "level": 1}
    },
    "extra_unlocked": ["pattern_recognition"],
    "total_xp": 225,
    "history": [],
    "last_xp_gain": "2026-03-25T..."
  }
}
```

Only skills with progress > 0 are stored. Default unlocked suns are computed at runtime.

## Visualization

The frontend displays skills as a solar system:
- Qube's avatar at center (sun position)
- Category suns orbit the center
- Planets orbit their category sun
- Moons orbit their parent planet
- Brightness indicates level
- Size indicates progress
- Locked skills appear grey with a lock icon

## Future: On-Chain Skill Badges

See [skill-nft-badges.md](skill-nft-badges.md) for the planned NFT badge system that will replace local-only progression with on-chain verifiable skill credentials.
