# Trait System Implementation Plan

## Overview

Replace the current manual tag system with an AI-attributed **Trait System** where qubes automatically detect and assign personality/behavioral traits to entities based on analyzing interactions.

**Current State**: Tags are manual organizational labels (family, coworker, mentor)
**Target State**: Traits are AI-derived behavioral characteristics (reliable, flirty, manipulative)

---

## Goals

1. **Automatic Attribution**: Qubes analyze interactions and assign traits without user intervention
2. **Evidence-Based**: Each trait backed by concrete metric data and confidence scores
3. **Dynamic Evolution**: Traits evolve as relationships develop over time
4. **Actionable Insights**: Traits inform trust calculations, warnings, and AI context
5. **User Transparency**: Users see what traits their qubes assign, with reasoning
6. **Cross-Qube Reputation**: Aggregate trait assessments visible across qubes (anonymous counts)
7. **Trait Decay**: Traits fade over time without reinforcement

---

## Timing: Anchor-Based Trait Assignment

Traits are **only assigned during anchors** (summarization events). This provides:

1. **Natural Timing**: Anchors already trigger relationship evaluations
2. **Sufficient Context**: Summarized conversation provides meaningful signal
3. **Transparency**: Users see trait assignments in SUMMARY blocks
4. **Efficiency**: No real-time computation overhead

### Flow

```
Conversation blocks accumulate
        ↓
Anchor triggered (summarization)
        ↓
For EACH entity mentioned (one at a time to avoid confusion):
        ↓
AI evaluates relationship:
  - 36 metrics (30 existing + 6 new)
  - Direct trait identification (hybrid approach)
        ↓
TraitDetector combines:
  - Metric-derived traits
  - AI-identified traits
        ↓
Apply difficulty scaling + decay
        ↓
Trait changes stored in evaluation record
        ↓
Cross-qube reputation aggregated
        ↓
SUMMARY block displays trait assignments
```

### SUMMARY Block Display

In the Blocks tab, SUMMARY blocks will show trait assignments:

```
┌─────────────────────────────────────────────────────────────┐
│ SUMMARY                                    2025-01-09 14:32 │
├─────────────────────────────────────────────────────────────┤
│ Discussed project deadlines and debugging strategies.       │
│ Alice helped troubleshoot the API issue.                    │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│ Trait Assignments:                                          │
│                                                             │
│ Alice:                                                      │
│   🎯 +reliable (72% → 78%)                                  │
│   💬 +responsive (NEW, 65%)                                 │
│   🧠 +analytical (68% → 71%)                                │
│                                                             │
│ Bob:                                                        │
│   ⏰ -punctual (55% → 48%)                                  │
│   😤 +impatient (NEW, 52%)                                  │
└─────────────────────────────────────────────────────────────┘
```

### Evaluation Record Enhancement

Each evaluation stored in `relationship.evaluations` will include trait data:

```python
{
    "timestamp": 1736445120,
    "summary": "Productive debugging session...",
    "reasoning": "Alice demonstrated patience and expertise...",
    "key_moments": ["Helped solve API bug", "Explained solution clearly"],
    "deltas": {
        "reliability": 2.0,
        "responsiveness": 3.0,
        # ... other metrics
    },
    # NEW: Trait assignment data
    "trait_changes": {
        "Alice": {
            "assigned": ["responsive"],           # New traits
            "strengthened": ["reliable", "analytical"],  # Score increased
            "weakened": [],                       # Score decreased
            "removed": []                         # Dropped below threshold
        },
        "Bob": {
            "assigned": ["impatient"],
            "strengthened": [],
            "weakened": ["punctual"],
            "removed": []
        }
    }
}
```

---

## Trait Taxonomy (80+ traits)

### Communication
| Trait | Opposite | Description |
|-------|----------|-------------|
| articulate | inarticulate | Expresses ideas clearly |
| verbose | terse | Uses many/few words |
| direct | indirect | Says things plainly vs hints |
| formal | casual | Communication register |
| sarcastic | literal | Uses irony frequently |
| responsive | unresponsive | Replies quickly/slowly |
| initiator | passive | Starts conversations vs waits |
| over-sharer | private | Shares too much/little |
| gossip | discreet | Spreads others' info |

### Social/Interpersonal
| Trait | Opposite | Description |
|-------|----------|-------------|
| warm | cold | Emotional accessibility |
| flirty | reserved | Romantic signaling |
| clingy | distant | Attachment style |
| supportive | dismissive | Response to others' problems |
| empathetic | apathetic | Emotional understanding |
| charming | off-putting | Social magnetism |
| inclusive | exclusive | Welcomes others in |
| humble | arrogant | Self-presentation |
| generous | selfish | Sharing resources/time |

### Emotional
| Trait | Opposite | Description |
|-------|----------|-------------|
| stable | volatile | Emotional consistency |
| optimistic | pessimistic | Outlook on situations |
| sensitive | thick-skinned | Reaction to criticism |
| anxious | relaxed | Baseline stress level |
| dramatic | understated | Emotional expression scale |
| reactive | measured | Speed of emotional response |

### Energy/Tempo
| Trait | Opposite | Description |
|-------|----------|-------------|
| high-energy | low-energy | Activity level |
| intense | laid-back | Engagement intensity |
| spontaneous | deliberate | Planning vs impulsive |
| consistent | erratic | Behavioral predictability |

### Reliability/Trust
| Trait | Opposite | Description |
|-------|----------|-------------|
| reliable | flaky | Follows through |
| punctual | late | Time respect |
| honest | deceptive | Truthfulness |
| loyal | disloyal | Stands by others |
| trustworthy | sketchy | Overall dependability |
| transparent | secretive | Information sharing |
| genuine | manipulative | Authenticity of intent |

### Temperament
| Trait | Opposite | Description |
|-------|----------|-------------|
| patient | impatient | Tolerance for waiting |
| calm | quick-tempered | Anger threshold |
| assertive | passive | Standing up for self |
| confrontational | avoidant | Addresses vs dodges conflict |
| forgiving | grudge-holding | Lets things go |
| flexible | rigid | Adapts to change |

### Intellect/Thinking
| Trait | Opposite | Description |
|-------|----------|-------------|
| analytical | intuitive | Reasoning style |
| curious | incurious | Interest in learning |
| open-minded | closed-minded | Receptive to new ideas |
| creative | conventional | Novel thinking |
| detail-oriented | big-picture | Focus level |
| quick-witted | slow-thinking | Processing speed |

### Work/Effort
| Trait | Opposite | Description |
|-------|----------|-------------|
| hardworking | lazy | Effort level |
| ambitious | content | Drive for achievement |
| organized | chaotic | Structure preference |
| collaborative | competitive | Team orientation |
| perfectionist | good-enough | Quality standards |

### Social Dynamics
| Trait | Opposite | Description |
|-------|----------|-------------|
| leader | follower | Takes charge |
| dominant | submissive | Power dynamics |
| influential | impressionable | Affects vs affected by others |
| independent | dependent | Self-sufficiency |

### Warning Traits (negative, no opposites)
| Trait | Description |
|-------|-------------|
| manipulative | Uses others for personal gain |
| gaslighting | Denies reality to confuse |
| love-bombing | Excessive early affection |
| ghosting | Disappears without explanation |
| breadcrumbing | Gives minimal attention to string along |
| toxic | Generally harmful to interact with |
| narcissistic | Excessive self-focus |
| passive-aggressive | Indirect hostility |
| controlling | Tries to dictate others' behavior |
| jealous | Envious/possessive |
| petty | Focuses on small slights |
| two-faced | Different behavior to different people |

---

## New Metrics (6 additions)

To support trait detection, we add 6 new metrics to the existing 30 (total: 36).

| Metric | Category | Enables Traits | Description |
|--------|----------|----------------|-------------|
| verbosity | Communication | verbose, terse, articulate | How much someone writes/talks |
| punctuality | Reliability | punctual, late | Timeliness and schedule respect |
| emotional_stability | Emotional | stable, volatile, anxious | Consistency of emotional state |
| directness | Communication | direct, indirect, passive-aggressive | How plainly they communicate |
| energy_level | Energy | high-energy, low-energy, intense | Activity and engagement level |
| humor_style | Social | sarcastic, literal, playful | Type of humor used |

**Why these 6?**
- Cover trait categories that don't map to existing metrics
- Minimal addition (20% increase) for maximum trait coverage
- AI can still directly identify nuanced traits not covered

**Implementation**: Add to relationship evaluation prompt alongside existing 30 metrics.

---

## Hybrid Trait Detection

Traits are detected through **two complementary methods**:

### Method 1: Metric-Derived Traits
Calculate trait scores from weighted metric combinations:

```python
TRAIT_METRICS = {
    "reliable": {
        "primary": ["reliability", "punctuality", "honesty"],
        "supporting": ["responsiveness"],
        "threshold": 70.0
    },
    "verbose": {
        "primary": ["verbosity"],
        "supporting": ["engagement"],
        "threshold": 65.0
    }
}
```

### Method 2: AI Direct Identification
Ask AI to identify traits directly during evaluation:

```python
# Enhanced evaluation response
{
    "deltas": { ... },  # 36 metrics
    "detected_traits": {
        "entity_id": "alice_123",
        "traits": ["verbose", "supportive", "analytical"],
        "evidence": [
            "Alice wrote 500+ word explanations",
            "Offered to help debug without being asked"
        ]
    }
}
```

### Combining Both Methods

```python
def detect_traits(self, relationship, evaluation):
    # Get metric-derived traits
    metric_traits = self._derive_from_metrics(relationship)

    # Get AI-identified traits
    ai_traits = evaluation.get("detected_traits", {}).get("traits", [])

    # Combine: AI identification boosts confidence
    for trait in ai_traits:
        if trait in metric_traits:
            metric_traits[trait].confidence *= 1.2  # 20% boost
        else:
            # AI-only trait starts at lower confidence
            metric_traits[trait] = TraitScore(
                score=50.0,  # Needs metric support to grow
                source="ai_direct"
            )

    return metric_traits
```

---

## Current Architecture

### Tag System (to be replaced)

**TagDefinition** (`utils/clearance_profiles.py:137-172`):
```python
@dataclass
class TagDefinition:
    name: str           # e.g., "family", "coworker"
    description: str
    icon: str
    color: str
    is_default: bool
```

**Storage**: Simple string array in `Relationship.tags`

**Commands**:
- `get_available_tags()` - retrieves tag definitions
- `add_relationship_tag()` - manually adds tag
- `remove_relationship_tag()` - manually removes tag

### Relationship Evaluation Pipeline

**Location**: `core/session.py:1173-1335`

**Flow**:
1. Conversation blocks grouped (after summarization)
2. `_evaluate_relationships_with_ai()` extracts participants
3. AI receives conversation context + 30 metric definitions
4. AI returns JSON with deltas (-5 to +5) for each metric
5. `_apply_relationship_deltas_from_summary()` applies changes

**30 Existing Metrics**:
- 5 Core Trust: honesty, reliability, support, loyalty, respect
- 14 Positive: friendship, affection, engagement, depth, humor, understanding, compatibility, admiration, warmth, openness, patience, empowerment, responsiveness, expertise
- 10 Negative: antagonism, resentment, annoyance, distrust, rivalry, tension, condescension, manipulation, dismissiveness, betrayal

### Relationship Storage

**Location**: `relationships/relationship.py`

**Key Fields**:
```python
self.tags: List[str] = []
self.evaluations: List[Dict[str, Any]] = []  # AI evaluation history
# Each evaluation contains timestamp, summary, reasoning, key_moments, deltas
```

---

## New Architecture

### TraitDefinition

**New file**: `utils/trait_definitions.py`

```python
@dataclass
class TraitDefinition:
    name: str                              # e.g., "reliable", "flirty"
    category: str                          # "communication", "social", etc.
    description: str
    icon: str
    color: str
    polarity: str                          # "positive", "negative", "neutral"

    # Detection parameters
    primary_metrics: List[str]             # metrics that strongly indicate trait
    supporting_metrics: List[str]          # metrics that weakly support trait
    negative_indicators: List[str]         # metrics that contradict trait
    confidence_threshold: float            # min score to assign (0-100)
    evidence_required: int                 # evaluations needed before confident

    # Optional relationships
    opposite_trait: Optional[str]          # e.g., "reliable" <-> "flaky"
    conflicting_traits: List[str]          # traits that rarely coexist
    reinforcing_traits: List[str]          # traits that often appear together
```

### Trait Configuration

**New file**: `config/trait_definitions.yaml`

```yaml
traits:
  reliable:
    category: reliability
    description: "Consistently follows through on commitments"
    icon: "🎯"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [reliability, honesty]
    supporting_metrics: [responsiveness, consistency]
    negative_indicators: [betrayal, dismissiveness]
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: flaky

  flirty:
    category: social
    description: "Engages in romantic or playful signaling"
    icon: "😏"
    color: "#ec4899"
    polarity: neutral
    primary_metrics: [warmth, affection, humor]
    supporting_metrics: [engagement, openness]
    negative_indicators: [antagonism, coldness]
    confidence_threshold: 65.0
    evidence_required: 2
    opposite_trait: reserved

  manipulative:
    category: warning
    description: "Uses others for personal gain through deception"
    icon: "🎭"
    color: "#ef4444"
    polarity: negative
    primary_metrics: [manipulation]
    supporting_metrics: [deception, betrayal]
    negative_indicators: [honesty, loyalty, transparency]
    confidence_threshold: 60.0
    evidence_required: 2
    is_warning: true
```

### TraitDetector

**New file**: `relationships/trait_detection.py`

```python
class TraitDetector:
    """Detects and scores traits based on relationship metrics."""

    def __init__(self, trait_definitions: Dict[str, TraitDefinition]):
        self.definitions = trait_definitions

    def calculate_trait_score(
        self,
        trait_name: str,
        relationship: Relationship
    ) -> float:
        """
        Calculate confidence score (0-100) for a trait.

        Weighted formula:
        - Primary metrics: 60% weight
        - Supporting metrics: 30% weight
        - Negative indicators: -10% per high value
        """

    def detect_traits(
        self,
        relationship: Relationship,
        evaluation: Dict[str, Any]
    ) -> Dict[str, TraitScore]:
        """
        Analyze metrics and return detected traits with scores.

        Returns dict of trait_name -> TraitScore with:
        - score: float (0-100)
        - is_confident: bool (above threshold + evidence)
        - evidence_count: int
        - trend: str ("rising", "stable", "falling")
        """

    def get_trait_evolution(
        self,
        relationship: Relationship,
        trait_name: str
    ) -> List[Dict]:
        """Return timeline of trait score changes."""
```

---

## Integration with Existing Settings

The trait system **must respect existing relationship difficulty settings** to ensure traits are also a "grind" and don't change too quickly.

### Difficulty Scaling

Existing difficulty settings (`config/trust_scoring.yaml` and `trust_scoring_long_grind.yaml`) already control:
- `min_interactions` for status progression
- Trust delta growth rates
- Time-based requirements (days known)

**Trait system will use the same scaling:**

| Difficulty | Evidence Required | Confidence Growth | Time Requirement |
|------------|-------------------|-------------------|------------------|
| quick | 2 evaluations | 1.0x (full) | None |
| normal | 3 evaluations | 0.8x | None |
| long | 5 evaluations | 0.5x | 7+ days known |
| extreme | 10 evaluations | 0.2x | 30+ days known |

### TraitDetector Settings Integration

```python
class TraitDetector:
    def __init__(
        self,
        trait_definitions: Dict[str, TraitDefinition],
        difficulty: str = "long",  # From user settings
        trust_personality: str = "balanced"  # Per-qube setting
    ):
        self.definitions = trait_definitions
        self.difficulty = difficulty
        self.trust_personality = trust_personality

        # Scale evidence requirements by difficulty
        self.evidence_multiplier = {
            "quick": 0.5,    # 2 evals instead of 4
            "normal": 0.75,  # 3 evals instead of 4
            "long": 1.0,     # Base requirement
            "extreme": 2.0   # 8 evals instead of 4
        }[difficulty]

        # Scale confidence growth rate
        self.confidence_growth_rate = {
            "quick": 1.0,
            "normal": 0.8,
            "long": 0.5,
            "extreme": 0.2
        }[difficulty]

    def calculate_trait_score(self, trait_name: str, relationship: Relationship) -> float:
        # ... existing calculation ...

        # Apply difficulty scaling to score changes
        raw_delta = new_score - old_score
        scaled_delta = raw_delta * self.confidence_growth_rate
        return old_score + scaled_delta

    def has_sufficient_evidence(self, trait_name: str, evidence_count: int) -> bool:
        base_requirement = self.definitions[trait_name].evidence_required
        scaled_requirement = int(base_requirement * self.evidence_multiplier)
        return evidence_count >= scaled_requirement
```

### Trust Personality Influence

Per-qube trust personality affects which trait categories are prioritized:

| Personality | Prioritized Trait Categories |
|-------------|------------------------------|
| Cautious | reliability, trust, warning traits |
| Balanced | All categories equally |
| Social | communication, social, emotional |
| Analytical | intellect, work, reliability |

```python
# In TraitDetector
PERSONALITY_BOOSTS = {
    "cautious": {
        "reliability": 1.2,  # 20% boost
        "trust": 1.2,
        "warning": 1.3,      # Extra sensitive to warning traits
    },
    "social": {
        "communication": 1.2,
        "social": 1.2,
        "emotional": 1.1,
    },
    "analytical": {
        "intellect": 1.2,
        "work": 1.2,
        "reliability": 1.1,
    },
    "balanced": {}  # No boosts
}

def calculate_trait_score(self, trait_name: str, relationship: Relationship) -> float:
    base_score = self._calculate_raw_score(trait_name, relationship)

    # Apply personality boost if applicable
    category = self.definitions[trait_name].category
    boost = PERSONALITY_BOOSTS.get(self.trust_personality, {}).get(category, 1.0)

    return min(100, base_score * boost)
```

### Config File Addition

**New section in `config/trust_scoring.yaml`:**

```yaml
# Trait Detection Settings
trait_detection:
  base_evidence_required: 4      # Evaluations needed before confident
  confidence_threshold: 65.0     # Min score to display trait
  evolution_log_threshold: 5.0   # Min change to log in evolution
  max_traits_displayed: 8        # Limit on relationship card

  # Difficulty multipliers (applied to base_evidence_required)
  difficulty_multipliers:
    quick: 0.5
    normal: 0.75
    long: 1.0
    extreme: 2.0

  # Confidence growth rates per difficulty
  growth_rates:
    quick: 1.0
    normal: 0.8
    long: 0.5
    extreme: 0.2

  # Trait decay - traits fade without reinforcement
  decay:
    enabled: true
    half_life_days:              # Days until confidence drops 50%
      quick: 30
      normal: 60
      long: 90
      extreme: 180

  # Warning trait special handling
  warning_traits:
    evidence_required: 2         # Fewer evals needed (catch bad actors early)
    confidence_threshold: 75.0   # Higher bar (avoid false positives)
    show_emerging: true          # Show even below threshold as heads-up
    emerging_threshold: 40.0     # Min score to show as "emerging warning"

  # Volatility detection
  volatility:
    window_size: 5               # Number of recent scores to analyze
    high_volatility_threshold: 25.0  # Std dev above this = volatile
```

**Long grind addition in `config/trust_scoring_long_grind.yaml`:**

```yaml
trait_detection:
  base_evidence_required: 8      # Double the base
  confidence_threshold: 70.0     # Higher bar
  time_known_requirement: 7      # Must know entity 7+ days

  decay:
    half_life_days:
      long: 180                  # Much slower decay
      extreme: 365

  warning_traits:
    evidence_required: 3         # Slightly more evidence needed
    confidence_threshold: 80.0   # Even higher bar
```

---

### Enhanced Relationship Fields

**Modified**: `relationships/relationship.py`

```python
# Replace simple tags with trait system
self.traits: List[str] = []                    # Active traits (backward compat)
self.trait_scores: Dict[str, TraitScore] = {}  # Full trait data

@dataclass
class TraitScore:
    score: float                # 0-100 confidence
    evidence_count: int         # evaluations supporting this
    first_detected: int         # timestamp
    last_updated: int           # timestamp
    consistency: float          # 0-100, score stability
    volatility: float           # 0-100, high = inconsistent signals (NEW)
    trend: str                  # "rising", "stable", "falling"
    source: str                 # "metric_derived", "ai_direct", "both" (NEW)

self.trait_evolution: List[Dict] = []  # Timeline of trait changes
# Each entry: {timestamp, trait, old_score, new_score, reason}

self.manual_trait_overrides: Dict[str, bool] = {}  # User overrides
# {trait_name: True (forced on) or False (forced off)}

self.trait_scores_version: str = "1.0"  # For migration compatibility (NEW)
```

### Integration with Evaluation Pipeline

**CRITICAL**: Evaluate **one entity at a time** to avoid AI confusion.

**Modified**: `core/session.py`

```python
async def _evaluate_relationships_with_ai(self, conversation_context: str):
    """
    Evaluate all mentioned entities, ONE AT A TIME.

    Why one-per-call:
    - Prevents AI from confusing who said what
    - Ensures accurate trait attribution
    - Allows validation that response matches requested entity
    """
    entities = self._extract_mentioned_entities(conversation_context)

    # Process each entity separately (can parallelize with asyncio.gather)
    evaluation_tasks = [
        self._evaluate_single_entity(entity, conversation_context)
        for entity in entities
    ]
    results = await asyncio.gather(*evaluation_tasks)

    return results

async def _evaluate_single_entity(
    self,
    entity: Entity,
    conversation_context: str
) -> EntityEvaluation:
    """
    Evaluate ONE entity's relationship metrics and traits.
    """
    prompt = f"""
    Evaluate the relationship with this specific entity based on the conversation.

    ENTITY TO EVALUATE:
    - ID: {entity.id}
    - Name: {entity.name}

    CONVERSATION:
    {conversation_context}

    Return JSON with:
    1. "entity_id": "{entity.id}"  (MUST match, for validation)
    2. "deltas": {{ metric deltas for all 36 metrics }}
    3. "detected_traits": ["trait1", "trait2", ...]
    4. "trait_evidence": {{ "trait1": "quote or observation", ... }}
    """

    response = await self.ai.complete(prompt)

    # VALIDATE: Response must be for the correct entity
    if response.get("entity_id") != entity.id:
        logger.warning(f"Entity mismatch: expected {entity.id}, got {response.get('entity_id')}")
        return None  # Discard mismatched response

    return response

def _apply_relationship_deltas_from_summary(self, relationship, evaluation):
    # Existing: apply metric deltas
    relationship.apply_deltas(evaluation["deltas"])

    # NEW: detect and update traits
    detector = TraitDetector(
        self.trait_definitions,
        difficulty=self.user_settings.relationship_difficulty,
        trust_personality=self.qube.trust_personality
    )
    new_traits = detector.detect_traits(
        relationship,
        evaluation,
        ai_detected=evaluation.get("detected_traits", []),
        ai_evidence=evaluation.get("trait_evidence", {})
    )

    # Check for trait notifications
    self.trait_notifier.check_and_notify(
        relationship.entity_id,
        relationship.trait_scores,
        new_traits
    )

    # Update trait scores
    for trait_name, trait_score in new_traits.items():
        old_score = relationship.trait_scores.get(trait_name)
        relationship.trait_scores[trait_name] = trait_score

        # Log evolution if significant change
        if old_score and abs(old_score.score - trait_score.score) > 5:
            relationship.trait_evolution.append({
                "timestamp": int(time.time()),
                "trait": trait_name,
                "old_score": old_score.score,
                "new_score": trait_score.score,
                "evaluation_id": evaluation.get("id")
            })

    # Update active traits list (confident traits only)
    relationship.traits = [
        name for name, score in relationship.trait_scores.items()
        if score.is_confident and not relationship.manual_trait_overrides.get(name) == False
    ]

    # Update cross-qube reputation
    self.reputation_service.update_assessment(
        entity_id=relationship.entity_id,
        qube_id=self.qube.id,
        traits=relationship.trait_scores,
        evidence_count=len(relationship.evaluations)
    )
```

---

## Frontend Changes

### TraitBadges Component

**New file**: `qubes-gui/src/components/relationships/TraitBadges.tsx`

```tsx
interface TraitScore {
  score: number;
  evidence_count: number;
  first_detected: number;
  trend: 'rising' | 'stable' | 'falling';
}

interface TraitBadgesProps {
  traits: Record<string, TraitScore>;
  traitDefinitions: Record<string, TraitDefinition>;
  onRemoveTrait?: (trait: string) => void;  // Manual override
}

// Display confident traits as colored badges
// High confidence (75+): solid color, full size
// Medium (50-74): medium opacity
// Emerging (25-49): faded, "new" indicator
// Hover shows evidence + trend
```

### TraitTimeline Component

**New file**: `qubes-gui/src/components/relationships/TraitTimeline.tsx`

```tsx
interface TraitTimelineProps {
  evolution: TraitEvolution[];
  traitDefinitions: Record<string, TraitDefinition>;
}

// Interactive timeline showing:
// - Trait gains (green dots)
// - Trait losses (red dots)
// - Score changes (line chart per trait)
// - Correlation with relationship status changes
```

### Replace TagManager

**Modified**: `qubes-gui/src/components/relationships/TagManager.tsx`

Rename to `TraitManager.tsx`:
- Display auto-detected traits prominently
- Show confidence scores and trends
- Allow manual override (add/remove)
- "Why this trait?" info popover
- Warning traits highlighted in red

### Relationship Card Updates

**Modified**: `qubes-gui/src/components/tabs/RelationshipsTab.tsx`

```tsx
// In expanded card view:
<TraitBadges
  traits={rel.trait_scores}
  traitDefinitions={availableTraits}
  onRemoveTrait={(trait) => handleTraitOverride(rel.entity_id, trait, false)}
/>

// Warning traits shown prominently at top if present
{hasWarningTraits && (
  <div className="bg-red-500/10 border border-red-500/30 rounded p-2">
    <span className="text-red-400">Warning traits detected</span>
    <TraitBadges traits={warningTraits} />
  </div>
)}
```

### SUMMARY Block Trait Display (Blocks Tab)

**Modified**: `qubes-gui/src/components/tabs/BlocksTab.tsx`

When rendering SUMMARY blocks, include trait assignment section:

```tsx
interface TraitChange {
  trait: string;
  type: 'assigned' | 'strengthened' | 'weakened' | 'removed';
  old_score?: number;
  new_score: number;
}

interface SummaryTraitData {
  [entityName: string]: TraitChange[];
}

// In SUMMARY block rendering:
{block.type === 'SUMMARY' && block.trait_changes && (
  <div className="mt-3 pt-3 border-t border-glass-border">
    <h5 className="text-text-secondary text-xs font-semibold mb-2">
      Trait Assignments
    </h5>
    {Object.entries(block.trait_changes).map(([entity, changes]) => (
      <div key={entity} className="mb-2">
        <span className="text-text-primary text-sm">{entity}:</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {changes.map((change) => (
            <TraitChangeBadge
              key={change.trait}
              trait={change.trait}
              type={change.type}
              oldScore={change.old_score}
              newScore={change.new_score}
            />
          ))}
        </div>
      </div>
    ))}
  </div>
)}
```

**New component**: `TraitChangeBadge.tsx`

```tsx
// Shows trait changes with visual indicators:
// +trait (NEW, 65%)     - green, new assignment
// +trait (72% → 78%)    - green arrow up, strengthened
// -trait (55% → 48%)    - orange arrow down, weakened
// ✕trait (removed)      - red strikethrough, removed
```

### Search & Filter by Trait

**Modified**: `qubes-gui/src/components/tabs/RelationshipsTab.tsx`

Add trait-based search and filtering:

```tsx
// State for trait filtering
const [searchQuery, setSearchQuery] = useState('');
const [traitFilter, setTraitFilter] = useState<string | null>(null);

// Filter relationships by trait or search
const filteredRelationships = relationships.filter(rel => {
  // Text search (name)
  if (searchQuery && !rel.name.toLowerCase().includes(searchQuery.toLowerCase())) {
    return false;
  }
  // Trait filter
  if (traitFilter && !rel.traits.includes(traitFilter)) {
    return false;
  }
  return true;
});

// UI: Search bar + trait filter dropdown
<div className="flex gap-2 mb-4">
  <input
    type="text"
    placeholder="Search relationships..."
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    className="flex-1 px-3 py-2 bg-glass-bg border border-glass-border rounded"
  />
  <select
    value={traitFilter || ''}
    onChange={(e) => setTraitFilter(e.target.value || null)}
    className="px-3 py-2 bg-glass-bg border border-glass-border rounded"
  >
    <option value="">All traits</option>
    <option value="__warning__">⚠️ Warning traits</option>
    {allTraits.map(trait => (
      <option key={trait} value={trait}>{trait}</option>
    ))}
  </select>
</div>
```

**Modified**: `qubes-gui/src/components/NetworkGraph.tsx`

Add trait highlight mode:

```tsx
// State for trait highlighting
const [highlightTrait, setHighlightTrait] = useState<string | null>(null);

// Node styling based on trait highlight
const getNodeOpacity = (node: NetworkNode) => {
  if (!highlightTrait) return 1.0;
  if (node.traits?.includes(highlightTrait)) return 1.0;
  return 0.3;  // Dim nodes without the trait
};

// Trait highlight selector in legend panel
<div className="mt-2">
  <label className="text-xs text-text-secondary">Highlight trait:</label>
  <select
    value={highlightTrait || ''}
    onChange={(e) => setHighlightTrait(e.target.value || null)}
    className="w-full mt-1 px-2 py-1 text-xs bg-glass-bg border border-glass-border rounded"
  >
    <option value="">None</option>
    {allTraits.map(trait => (
      <option key={trait} value={trait}>{trait}</option>
    ))}
  </select>
</div>
```

### Volatile Trait Display

Show volatility indicator on unstable traits:

```tsx
// In TraitBadges component
{trait.volatility > 25 && (
  <span className="text-yellow-400 ml-1" title="Inconsistent signals">⚡</span>
)}

// Example display:
// 🎯 reliable (72%) ⚡  <- lightning means volatile
```

### Community Reputation Display

**New component**: `CommunityReputation.tsx`

```tsx
interface CommunityReputationProps {
  entityId: string;
  reputation: AggregatedReputation;
}

export const CommunityReputation: React.FC<CommunityReputationProps> = ({
  entityId,
  reputation
}) => {
  if (reputation.total_qubes < 2) return null;  // Need 2+ qubes for community

  return (
    <div className="mt-3 pt-3 border-t border-glass-border">
      <h5 className="text-text-secondary text-xs font-semibold mb-2">
        Community Reputation ({reputation.total_qubes} qubes)
      </h5>

      {/* Warning flags first */}
      {Object.entries(reputation.warning_flags).map(([trait, count]) => (
        <div key={trait} className="text-red-400 text-xs mb-1">
          ⚠️ {trait} - {count}/{reputation.total_qubes} flagged
        </div>
      ))}

      {/* Consensus traits */}
      {Object.entries(reputation.trait_consensus).map(([trait, avgScore]) => (
        <div key={trait} className="text-text-tertiary text-xs mb-1">
          ✅ {trait} - avg {avgScore.toFixed(0)}%
        </div>
      ))}
    </div>
  );
};
```

---

## GUI Bridge Commands

**Modified**: `gui_bridge.py`

```python
# Keep for backward compat, but return traits
@tauri_command
async def get_available_tags(user_id: str, qube_id: str) -> Dict:
    """Returns trait definitions instead of tag definitions."""

# Renamed internally but same API
@tauri_command
async def add_relationship_tag(user_id, qube_id, entity_id, tag, password) -> Dict:
    """Add manual trait override."""

@tauri_command
async def remove_relationship_tag(user_id, qube_id, entity_id, tag, password) -> Dict:
    """Remove trait (manual override to hide)."""

# NEW commands
@tauri_command
async def get_trait_details(user_id, qube_id, entity_id, trait_name) -> Dict:
    """Get full trait info: score, evidence, timeline, reasoning."""

@tauri_command
async def get_trait_evolution(user_id, qube_id, entity_id) -> List[Dict]:
    """Get trait change timeline for entity."""
```

---

## Enforcement & Application

### 1. Warning System

When interacting with someone who has warning traits:

```python
# In conversation context building
if relationship.has_warning_traits():
    warnings = relationship.get_warning_traits()
    context += f"\n\nWARNING: This person has been flagged as: {warnings}"
    context += f"Exercise appropriate caution in interactions."
```

### 2. AI Context Awareness

Include traits in AI prompts:

```python
def build_entity_context(self, entity_id: str) -> str:
    rel = self.relationships.get(entity_id)
    if rel and rel.traits:
        trait_str = ", ".join(rel.traits)
        return f"[{rel.name} - Traits: {trait_str}]"
```

### 3. Trust Score Modifiers

Traits can influence trust calculations:

```python
# In trust scoring
def calculate_trust_modifier(traits: List[str]) -> float:
    modifier = 0.0
    for trait in traits:
        if trait in TRUST_POSITIVE_TRAITS:  # reliable, honest, loyal
            modifier += 2.0
        elif trait in TRUST_NEGATIVE_TRAITS:  # manipulative, deceptive
            modifier -= 5.0
    return modifier
```

### 4. Communication Hints

Surface trait-based suggestions:

```python
def get_communication_hints(traits: List[str]) -> List[str]:
    hints = []
    if "direct" in traits:
        hints.append("Prefers straightforward communication")
    if "sensitive" in traits:
        hints.append("Be mindful of tone - they may take things personally")
    if "verbose" in traits:
        hints.append("Expect detailed responses")
    return hints
```

### 5. Trait Notifications

Alert users when important trait changes occur:

```python
class TraitNotificationService:
    def check_and_notify(self, entity_id: str, old_traits: Dict, new_traits: Dict):
        # Warning trait first assigned
        for trait in new_traits:
            if trait in WARNING_TRAITS and trait not in old_traits:
                self.notify_warning_trait(entity_id, trait)

        # Major trait shift (>20 points)
        for trait, score in new_traits.items():
            old_score = old_traits.get(trait, {}).get("score", 0)
            if abs(score.score - old_score) > 20:
                self.notify_major_shift(entity_id, trait, old_score, score.score)

    def notify_warning_trait(self, entity_id: str, trait: str):
        # Push notification to user
        notification = {
            "type": "warning_trait",
            "severity": "high",
            "message": f"⚠️ Warning: {entity_name} flagged as '{trait}'",
            "entity_id": entity_id,
            "trait": trait
        }
        self.push_notification(notification)
```

---

## Cross-Qube Reputation System

Trait assessments are **automatically shared** across qubes for the same user, providing aggregate reputation visibility.

### Design Principles

1. **Automatic Sharing**: All trait assessments shared by default (no opt-in required)
2. **Anonymous Counts**: Users see "3 qubes flagged X" not "Alice and Bob flagged X"
3. **Weighted by Evidence**: Assessments from qubes with more evaluations count more
4. **Per-User Aggregation**: Only aggregates within a single user's qubes

### Reputation Data Structure

```python
@dataclass
class CrossQubeReputation:
    entity_id: str
    assessments: List[QubeAssessment]  # One per qube that knows this entity

@dataclass
class QubeAssessment:
    qube_id: str
    traits: Dict[str, TraitScore]
    evidence_count: int  # Total evaluations this qube has done
    last_updated: int

def aggregate_reputation(assessments: List[QubeAssessment]) -> AggregatedReputation:
    """
    Combine assessments from multiple qubes into aggregate view.
    Weight by evidence count (more evaluations = more weight).
    """
    trait_votes: Dict[str, List[WeightedVote]] = {}

    for assessment in assessments:
        weight = min(assessment.evidence_count / 10, 1.0)  # Cap at 10 evals
        for trait, score in assessment.traits.items():
            if score.is_confident:
                trait_votes.setdefault(trait, []).append(
                    WeightedVote(score=score.score, weight=weight)
                )

    return AggregatedReputation(
        total_qubes=len(assessments),
        trait_consensus={
            trait: weighted_average(votes)
            for trait, votes in trait_votes.items()
        },
        warning_flags={
            trait: len(votes)
            for trait, votes in trait_votes.items()
            if trait in WARNING_TRAITS and len(votes) >= 2
        }
    )
```

### UI Display

```
┌─────────────────────────────────────────────────────────────┐
│ Dave Johnson                                                │
├─────────────────────────────────────────────────────────────┤
│ Your Assessment (Alph):                                     │
│   🎯 reliable (78%)  💬 verbose (72%)  🤝 supportive (68%) │
│                                                             │
│ Community Reputation (3 qubes):                            │
│   ✅ reliable - 3/3 agree (avg: 75%)                       │
│   💬 verbose - 2/3 agree (avg: 68%)                        │
│   ⚠️ manipulative - 2/3 flagged                            │
└─────────────────────────────────────────────────────────────┘
```

### Storage

**New file**: `data/users/{user_id}/reputation/entity_reputation.json`

```json
{
  "entity_123": {
    "assessments": [
      {
        "qube_id": "alph",
        "traits": {"reliable": {"score": 78, "confident": true}},
        "evidence_count": 12,
        "last_updated": 1736445120
      },
      {
        "qube_id": "beta",
        "traits": {"reliable": {"score": 72, "confident": true}},
        "evidence_count": 8,
        "last_updated": 1736400000
      }
    ],
    "aggregated": {
      "total_qubes": 2,
      "consensus": {"reliable": 75.5},
      "warning_flags": {}
    }
  }
}
```

---

## Data Migration

Existing manual tags will be **discarded** during migration. Users will start fresh with AI-derived traits.

```python
def migrate_to_trait_system(relationship: Relationship):
    """
    Migration strategy: Clean slate.

    - Discard existing tags (user chose to lose them)
    - Initialize empty trait_scores
    - Traits will be populated naturally via AI evaluation
    """
    relationship.tags = []  # Clear old tags
    relationship.trait_scores = {}
    relationship.trait_scores_version = "1.0"
    relationship.trait_evolution = []
    relationship.manual_trait_overrides = {}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Backend)
1. Create `TraitDefinition` dataclass
2. Create `config/trait_definitions.yaml` with all traits
3. Implement `TraitDetector` class
4. Add trait fields to `Relationship` class
5. Update serialization/deserialization
6. Create migration script

### Phase 2: Evaluation Integration
1. Integrate `TraitDetector` into evaluation pipeline
2. Store trait evolution in relationship data
3. Update GUI bridge commands
4. Add trait-related logging

### Phase 3: Frontend Display
1. Create `TraitBadges` component
2. Create `TraitTimeline` component
3. Refactor `TagManager` to `TraitManager`
4. Update relationship cards
5. Add trait detail popovers

### Phase 4: Enforcement
1. Add warning trait display
2. Integrate traits into AI context
3. Add trust score modifiers
4. Create communication hints system

### Phase 5: Polish
1. Trait conflict detection
2. Trait prediction (forecasting)
3. Performance optimization
4. Comprehensive testing

---

## Files to Create

| File | Purpose |
|------|---------|
| `utils/trait_definitions.py` | TraitDefinition class, DEFAULT_TRAITS, WARNING_TRAITS |
| `config/trait_definitions.yaml` | All 80+ trait configurations with metric correlations |
| `relationships/trait_detection.py` | TraitDetector class with decay, volatility |
| `relationships/reputation.py` | CrossQubeReputation, ReputationService |
| `services/trait_notifications.py` | TraitNotificationService for alerts |
| `qubes-gui/src/components/relationships/TraitBadges.tsx` | Trait display with volatility indicator |
| `qubes-gui/src/components/relationships/TraitTimeline.tsx` | Evolution view |
| `qubes-gui/src/components/relationships/TraitChangeBadge.tsx` | SUMMARY block trait change display |
| `qubes-gui/src/components/relationships/CommunityReputation.tsx` | Cross-qube reputation display |
| `data/users/{user_id}/reputation/` | Directory for reputation storage |

## Files to Modify

| File | Changes |
|------|---------|
| `relationships/relationship.py` | Add trait fields, TraitScore class, version field |
| `core/session.py` | One-entity-per-call evaluation, trait detection integration |
| `gui_bridge.py` | Update tag commands, add trait/reputation commands |
| `config/trust_scoring.yaml` | Add trait_detection section with decay, warning, volatility |
| `config/trust_scoring_long_grind.yaml` | Add long grind trait settings |
| `qubes-gui/src/components/relationships/TagManager.tsx` | Refactor to TraitManager |
| `qubes-gui/src/components/tabs/RelationshipsTab.tsx` | TraitBadges, search/filter, CommunityReputation |
| `qubes-gui/src/components/tabs/BlocksTab.tsx` | Show trait assignments in SUMMARY blocks |
| `qubes-gui/src/components/NetworkGraph.tsx` | Traits on nodes, highlight mode |

---

## Resolved Decisions

| Question | Decision |
|----------|----------|
| Trait detection method | Hybrid: 6 new metrics + AI direct identification |
| Trait decay | Yes, with half-life scaled by difficulty (30-180 days) |
| Warning trait handling | Fewer evals (2), higher confidence (75%), show emerging |
| Conflicting signals | Track volatility score, show ⚡ indicator |
| Cross-qube visibility | Yes, automatic sharing, anonymous counts, weighted by evidence |
| Custom tags migration | Discard (clean slate) |
| Entity evaluation | One-per-call to avoid confusion |
| Owner traits | None (just "Owner" badge) |

---

## Remaining Open Questions

1. **Override Limits**: Should there be limits on manual overrides to prevent gaming?
2. **Trait Granularity**: Are 80+ traits too many? Should we start with a smaller set?
3. **Notification Frequency**: How often should users be notified of trait changes?

---

## Success Metrics

1. Traits are automatically assigned after sufficient evaluations (difficulty-scaled)
2. Trait confidence correlates with relationship length and interaction depth
3. Warning traits surface appropriately for problematic entities
4. Cross-qube consensus provides meaningful reputation signal
5. Users find traits more intuitive than raw metrics
6. AI context awareness improves conversation quality
7. Volatile traits are correctly identified and flagged
