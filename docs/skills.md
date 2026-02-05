# Skills System

Qubes have 112 skills across 8 categories, visualized as a solar system.

## Overview

The skills system uses a 3-tier hierarchy:
- **Sun** (8): Major categories, always unlocked
- **Planets** (35): Specific skills, unlock via prerequisites
- **Moons** (70): Sub-skills, unlock via parent planet

## Categories

| Category | Icon | Color | Description |
|----------|------|-------|-------------|
| AI Reasoning | 🧠 | #4A90E2 | Problem-solving, code generation |
| Social Intelligence | 🤝 | #FF69B4 | Emotional intelligence, communication |
| Technical Expertise | 💻 | #00FF88 | Programming, DevOps, architecture |
| Creative Expression | 🎨 | #FFB347 | Writing, design, music |
| Knowledge Domains | 📚 | #9B59B6 | Science, history, philosophy |
| Security & Privacy | 🛡️ | #E74C3C | Cryptography, authentication |
| Games | 🎮 | #F39C12 | Chess, poker, strategy games |

## Skill Structure

Each skill has:

```json
{
  "id": "prompt_engineering",
  "name": "Prompt Engineering",
  "description": "Craft effective prompts to elicit desired AI responses",
  "category": "ai_reasoning",
  "nodeType": "planet",
  "tier": "novice",
  "level": 0,
  "xp": 0,
  "maxXP": 500,
  "unlocked": false,
  "parentSkill": "ai_reasoning_sun",
  "prerequisite": null,
  "toolCallReward": "analyze_prompt_quality",
  "icon": "✍️",
  "evidence": []
}
```

## XP and Levels

### XP Requirements

| Node Type | Max XP per Level |
|-----------|------------------|
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

### XP Flow

When XP is awarded to a locked skill, it flows to the nearest unlocked parent:

```
Locked Moon → Parent Planet (if unlocked) → Parent Sun
```

## Unlocking Skills

### Prerequisites
- Suns: Always unlocked (starting point)
- Planets: Require parent Sun to be at a certain level
- Moons: Require parent Planet to be unlocked

### Tool Rewards
When a skill reaches level 100, it unlocks a tool:

| Skill | Tool Unlocked |
|-------|---------------|
| AI Reasoning Sun | `describe_my_avatar` |
| Technical Expertise Sun | `web_search` |
| Knowledge Domains Sun | `search_memory` |
| Security & Privacy Sun | `verify_chain_integrity` |
| Games Sun | `describe_my_skills` |

## XP Sources

XP is awarded based on demonstrated skill usage:

### From AI Reasoning
- Using chain-of-thought → Chain of Thought skill
- Writing code → Code Generation skill
- Analyzing content → Analysis & Critique skill

### From Tool Calls
- Web search → Technical Expertise
- Memory search → Knowledge Domains
- Decision making → AI Reasoning

### From Conversations
- Emotional topics → Emotional Intelligence
- Conflict resolution → Conflict Resolution skill
- Creative writing → Writing skill

## Evidence Tracking

Each skill tracks evidence of usage:

```json
{
  "evidence": [
    {
      "block_id": "5_ACTION_1699999999",
      "xp_gained": 25,
      "timestamp": "2024-11-14T12:00:00Z",
      "description": "Used web_search to find Python documentation"
    }
  ]
}
```

This creates an auditable trail of skill development.

## Skill Definitions

### AI Reasoning (16 skills)

**Sun**: AI Reasoning
**Planets**: Prompt Engineering, Chain of Thought, Code Generation, Analysis & Critique, Multi-step Planning
**Moons**: Clarity & Precision, Context Building, Problem Decomposition, Step Verification, Design Patterns, Code Optimization, Deep Analysis, Constructive Feedback, Strategic Planning, Plan Adaptation

### Social Intelligence (16 skills)

**Sun**: Social Intelligence
**Planets**: Emotional Intelligence, Communication, Empathy, Relationship Building, Conflict Resolution
**Moons**: Self-Awareness, Emotion Regulation, Active Listening, Persuasion, Perspective Taking, Compassion, Trust Building, Rapport Building, Negotiation, Mediation

### Technical Expertise (16 skills)

**Sun**: Technical Expertise
**Planets**: Programming, DevOps, System Architecture, Debugging, API Integration
**Moons**: Algorithms, Data Structures, CI/CD, Containerization, Microservices, Scalability, Performance Profiling, Testing Strategies, REST APIs, GraphQL

### Creative Expression (16 skills)

**Sun**: Creative Expression
**Planets**: Writing, Visual Design, Music, Storytelling, Creative Problem Solving
**Moons**: Style & Voice, Grammar & Syntax, Composition, Color Theory, Music Theory, Music Composition, Plot Development, Character Development, Brainstorming, Lateral Thinking

### Knowledge Domains (16 skills)

**Sun**: Knowledge Domains
**Planets**: Science, History, Philosophy, Mathematics, Languages
**Moons**: Physics, Biology, World History, Historical Patterns, Ethics, Logic, Algebra, Calculus, Translation, Cultural Understanding

### Security & Privacy (16 skills)

**Sun**: Security & Privacy
**Planets**: Cryptography, Authentication, Network Security, Privacy Protection, Threat Analysis
**Moons**: Symmetric Encryption, Asymmetric Encryption, Multi-Factor Auth, OAuth & SSO, Firewalls, VPN & Tunneling, Data Minimization, Anonymization, Vulnerability Scanning, Penetration Testing

### Games (16 skills)

**Sun**: Games
**Planets**: Chess, Checkers, Battleship, Poker, Tic-Tac-Toe
**Moons**: Opening Theory, Endgame Technique, Strategic Play, Tactical Moves, Ship Placement, Targeting Strategy, Pot Odds, Player Reading, Perfect Play, Variant Games

## Storage

Skills are stored in:
```
data/users/{user}/qubes/{qube_id}/skills/
├── skills.json        # Current skill states
└── skill_history.json # XP gain events (last 1000)
```

## Visualization

The frontend displays skills as a solar system:
- Qube's avatar at center (sun position)
- Category suns orbit the center
- Planets orbit their category sun
- Moons orbit their parent planet
- Brightness indicates level
- Size indicates XP progress
