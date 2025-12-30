# Relationships

Qubes maintain relationships with humans and other Qubes, tracking 30 AI-evaluated metrics.

## Overview

Each relationship tracks:
- **5 Core Trust Metrics** (AI-evaluated)
- **14 Positive Social Metrics** (AI-evaluated)
- **10 Negative Social Metrics** (AI-evaluated)
- **9 Tracked Statistics** (auto-incremented)
- **5 Relationship State** fields

Total: 48 fields per relationship

## Core Trust Metrics

These form the foundation of trust (calculated as weighted average):

| Metric | Weight | Description |
|--------|--------|-------------|
| Honesty | 25% | How truthful and transparent |
| Reliability | 25% | How dependable and consistent |
| Support | 20% | Emotional/practical help provided |
| Loyalty | 15% | Commitment to relationship |
| Respect | 15% | Regard, admiration, valuing them |

**Trust Score** = `(honesty×0.25) + (reliability×0.25) + (support×0.20) + (loyalty×0.15) + (respect×0.15)`

## Positive Social Metrics

| Metric | Description |
|--------|-------------|
| Friendship | Warmth, friendliness, camaraderie |
| Affection | Emotional connection, caring |
| Engagement | Investment in conversations |
| Depth | Meaningful vs superficial exchanges |
| Humor | Playfulness, fun, levity |
| Understanding | Empathy, listening, comprehension |
| Compatibility | Personality/style alignment |
| Admiration | Looking up to them, respecting achievements |
| Warmth | Emotional warmth, kindness, gentleness |
| Openness | Vulnerability, sharing personal things |
| Patience | Tolerance, understanding under stress |
| Empowerment | They help you grow/improve |
| Responsiveness | How quickly they respond |
| Expertise | Knowledge/competence level |

## Negative Social Metrics

| Metric | Description |
|--------|-------------|
| Antagonism | Active hostility, opposition |
| Resentment | Bitterness, grudges held |
| Annoyance | Irritation, minor frustrations |
| Distrust | Suspicion, doubt, lack of confidence |
| Rivalry | Competitive tension |
| Tension | Unresolved conflict, awkwardness |
| Condescension | Talking down, patronizing |
| Manipulation | Deceptive tactics, using you |
| Dismissiveness | Invalidation, not taking seriously |
| Betrayal | Major broken trust events |

## Relationship Status

Progression through statuses:

```
unmet → stranger → acquaintance → friend → close_friend → best_friend
```

Only one `best_friend` is allowed per Qube.

### Status Thresholds
Status changes are evaluated by the AI based on:
- Trust score
- Interaction frequency
- Relationship duration
- Quality of exchanges

## Decay System

Relationships decay over time without interaction:

### Positive Metrics (after 30 days of inactivity)

| Decay Rate | Metrics |
|------------|---------|
| Heavy | Friendship, Affection, Understanding, Warmth |
| Medium | Engagement, Openness, Empowerment, Responsiveness |
| Light | Depth, Humor, Compatibility, Admiration, Patience, Expertise |
| None | Core Trust (Honesty, Reliability, Support, Loyalty, Respect) |

### Negative Metrics (healing over time)

| Decay Rate | Metrics |
|------------|---------|
| Fast | Annoyance, Tension, Dismissiveness |
| Medium | Antagonism, Rivalry |
| Slow | Resentment, Distrust, Condescension, Manipulation |
| None | Betrayal (permanent memory) |

### Decay Formula
```python
excess_days = days_inactive - 30
decay_factor = 0.98 ** excess_days  # ~18% loss after 1 month, ~39% after 2 months
```

## Creator Relationship

When a Qube is created, the creator gets a special relationship:
- All positive metrics start at 25 (instead of 0)
- Status starts at "stranger" (not "unmet")
- Special context in AI prompts

## AI Evaluation

After each conversation, the AI evaluates relationship changes:

```python
# Simplified from relationships/social.py

def evaluate_interaction(conversation, relationship):
    prompt = f"""
    Evaluate how this conversation affects the relationship metrics.
    Current relationship: {relationship.to_dict()}
    Conversation: {conversation}

    Return JSON with metric changes (-10 to +10 for each relevant metric).
    """

    response = ai_model.generate(prompt)
    changes = parse_json(response)

    for metric, delta in changes.items():
        current = getattr(relationship, metric)
        new_value = max(0, min(100, current + delta))
        setattr(relationship, metric, new_value)

    relationship.update_trust_score()
    return relationship
```

## Storage

Relationships are stored in:
```
data/users/{user}/qubes/{qube_id}/relationships/relationships.json
```

```json
{
  "human_creator_id": {
    "entity_id": "human_creator_id",
    "entity_type": "human",
    "trust": 25.0,
    "honesty": 25.0,
    "friendship": 25.0,
    ...
  },
  "Bob_B1C2D3E4": {
    "entity_id": "Bob_B1C2D3E4",
    "entity_type": "qube",
    "trust": 45.0,
    ...
  }
}
```

## Context in AI Prompts

Relationship context is included in system prompts:

```
You're speaking with your creator. You've developed a genuine friendship
with trust and mutual respect. Trust is solid and growing.
Strengths: highly engaged conversations, meaningful depth.
```

This helps the AI respond appropriately to different relationship dynamics.
