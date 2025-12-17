"""
Decision Support Logic

Core functions for calculating decision scores, generating recommendations,
and assessing capabilities using relationship and self-evaluation metrics.
"""

from typing import Dict, Any, Optional
from config.user_preferences import DecisionConfig


def calculate_decision_score(
    relationship,
    decision_type: str,
    config: DecisionConfig,
    requirements: Optional[Dict[str, bool]] = None
) -> float:
    """
    Calculate decision score for a relationship based on decision type

    Args:
        relationship: Relationship object with metrics
        decision_type: Type of decision (collaboration, trust_sensitive, delegation, etc.)
        config: User's decision configuration
        requirements: Optional task-specific requirements

    Returns:
        Score from 0-100
    """
    requirements = requirements or {}

    # Base score from trust (always important)
    score = relationship.trust * 0.3

    # Decision type specific weights
    if decision_type == "collaboration":
        score += relationship.reliability * 0.25
        score += relationship.expertise * 0.15
        score += relationship.friendship * 0.15
        score += relationship.engagement * 0.15

    elif decision_type == "trust_sensitive":
        score += relationship.honesty * 0.30
        score += relationship.reliability * 0.25
        score += relationship.loyalty * 0.15

    elif decision_type == "delegation":
        score += relationship.reliability * 0.30
        score += relationship.expertise * 0.25
        score += relationship.responsiveness * 0.15

    elif decision_type == "information_sharing":
        score += relationship.honesty * 0.25
        score += relationship.understanding * 0.20
        score += relationship.depth * 0.15
        score += relationship.openness * 0.10

    else:  # general
        score += relationship.reliability * 0.20
        score += relationship.honesty * 0.20
        score += relationship.friendship * 0.15
        score += relationship.expertise * 0.15

    # Task-specific requirement bonuses
    if requirements.get("needs_reliability"):
        score += relationship.reliability * 0.10
    if requirements.get("needs_expertise"):
        score += relationship.expertise * 0.10
    if requirements.get("needs_creativity"):
        score += relationship.openness * 0.10

    # Apply negative metric penalties
    if relationship.antagonism > config.max_antagonism:
        score *= 0.7  # 30% penalty
    if relationship.distrust > config.max_distrust:
        score *= 0.6  # 40% penalty
    if relationship.betrayal > config.max_betrayal:
        score *= 0.3  # 70% penalty (severe)

    # Apply metric influence setting
    influence = config.metric_influence / 100.0
    # Scale score between baseline (50) and calculated score
    score = 50 + ((score - 50) * influence)

    return max(0, min(100, score))


def generate_recommendation(
    relationship,
    score: float,
    decision_type: str,
    config: DecisionConfig
) -> str:
    """
    Generate natural language recommendation based on score

    Args:
        relationship: Relationship object
        score: Calculated decision score
        decision_type: Type of decision
        config: User's decision configuration

    Returns:
        Human-readable recommendation string
    """
    entity_name = relationship.entity_name or relationship.entity_id

    # Score-based recommendation
    if score >= 80:
        base = f"{entity_name} is an excellent choice"
    elif score >= 65:
        base = f"{entity_name} is a good choice"
    elif score >= 50:
        base = f"{entity_name} is acceptable, but consider alternatives"
    else:
        base = f"{entity_name} may not be ideal"

    # Add context based on decision type
    if decision_type == "collaboration":
        context = f"with trust={relationship.trust:.0f}, reliability={relationship.reliability:.0f}, expertise={relationship.expertise:.0f}"
    elif decision_type == "trust_sensitive":
        context = f"with trust={relationship.trust:.0f}, honesty={relationship.honesty:.0f}, loyalty={relationship.loyalty:.0f}"
    elif decision_type == "delegation":
        context = f"with reliability={relationship.reliability:.0f}, expertise={relationship.expertise:.0f}, responsiveness={relationship.responsiveness:.0f}"
    else:
        context = f"with trust={relationship.trust:.0f}, reliability={relationship.reliability:.0f}"

    # Add warnings for negative metrics
    warnings = []
    if relationship.antagonism > config.max_antagonism:
        warnings.append(f"high antagonism ({relationship.antagonism:.0f})")
    if relationship.distrust > config.max_distrust:
        warnings.append(f"distrust present ({relationship.distrust:.0f})")
    if relationship.betrayal > config.max_betrayal:
        warnings.append(f"⚠️ history of betrayal ({relationship.betrayal:.0f})")

    warning_text = f". WARNING: {', '.join(warnings)}" if warnings else ""

    return f"{base} ({context}){warning_text}."


def explain_score(
    relationship,
    score: float,
    decision_type: str,
    config: DecisionConfig
) -> str:
    """
    Explain why a score was calculated

    Args:
        relationship: Relationship object
        score: Calculated score
        decision_type: Type of decision
        config: User's decision configuration

    Returns:
        Explanation string
    """
    entity_name = relationship.entity_name or relationship.entity_id

    # Identify strongest and weakest aspects
    metrics = {
        "trust": relationship.trust,
        "reliability": relationship.reliability,
        "honesty": relationship.honesty,
        "expertise": relationship.expertise,
        "friendship": relationship.friendship,
    }

    sorted_metrics = sorted(metrics.items(), key=lambda x: x[1], reverse=True)
    strongest = sorted_metrics[0]
    weakest = sorted_metrics[-1]

    explanation = f"Score {score:.1f}/100: Strong in {strongest[0]} ({strongest[1]:.0f})"

    if weakest[1] < 50:
        explanation += f", weak in {weakest[0]} ({weakest[1]:.0f})"

    # Add negative flags
    if relationship.betrayal > config.max_betrayal:
        explanation += f". ⚠️ Betrayal history ({relationship.betrayal:.0f})"
    elif relationship.antagonism > config.max_antagonism:
        explanation += f". Antagonism concern ({relationship.antagonism:.0f})"

    return explanation


def assess_capability(
    metrics: Dict[str, float],
    task_type: str,
    config: DecisionConfig
) -> float:
    """
    Assess own capability for a task using self-evaluation metrics

    Args:
        metrics: Self-evaluation metrics dictionary
        task_type: Type of task to assess
        config: User's decision configuration

    Returns:
        Capability score from 0-100
    """
    # Base capability from confidence
    capability = metrics.get("confidence", 50) * 0.4

    # Add critical thinking (important for most tasks)
    capability += metrics.get("critical_thinking", 50) * 0.3

    # Add task-specific metrics
    task_type_lower = task_type.lower()

    if "analysis" in task_type_lower or "research" in task_type_lower:
        capability += metrics.get("critical_thinking", 50) * 0.15
        capability += metrics.get("curiosity", 50) * 0.15

    elif "creative" in task_type_lower or "writing" in task_type_lower:
        capability += metrics.get("curiosity", 50) * 0.15
        capability += metrics.get("adaptability", 50) * 0.15

    elif "teach" in task_type_lower or "advise" in task_type_lower or "help" in task_type_lower:
        capability += metrics.get("emotional_intelligence", 50) * 0.15
        capability += metrics.get("humility", 50) * 0.15

    elif "lead" in task_type_lower or "manage" in task_type_lower:
        capability += metrics.get("consistency", 50) * 0.15
        capability += metrics.get("goal_alignment", 50) * 0.15

    else:  # generic task
        capability += metrics.get("adaptability", 50) * 0.15
        capability += metrics.get("consistency", 50) * 0.15

    # Apply metric influence setting
    influence = config.metric_influence / 100.0
    capability = 50 + ((capability - 50) * influence)

    return max(0, min(100, capability))


def generate_self_assessment(
    capable: bool,
    score: float,
    task_type: str
) -> str:
    """
    Generate natural language self-assessment

    Args:
        capable: Whether qube is capable
        score: Capability score
        task_type: Type of task

    Returns:
        Self-assessment recommendation
    """
    if capable and score >= 80:
        return f"I'm well-equipped to handle {task_type}. My capabilities align strongly with this task."
    elif capable and score >= 60:
        return f"I can handle {task_type}, though it may not be my strongest area. I'll do my best."
    elif not capable and score >= 40:
        return f"I have limited capability for {task_type}. Consider consulting someone more experienced, or I can try with your guidance."
    else:
        return f"I'm not confident in my ability to handle {task_type} effectively. I recommend finding someone with stronger expertise in this area."


def calculate_auto_thresholds(metrics: Dict[str, float]) -> Dict[str, int]:
    """
    Calculate auto-thresholds based on self-evaluation metrics

    Args:
        metrics: Self-evaluation metrics dictionary

    Returns:
        Dictionary with auto-calculated thresholds
    """
    # Use self-evaluation metrics to derive decision thresholds
    # Philosophy: A Qube should hold others to similar standards it holds itself

    thresholds = {}

    # Trust threshold based on emotional intelligence + consistency
    emotional_intelligence = metrics.get("emotional_intelligence", 50)
    consistency = metrics.get("consistency", 50)
    thresholds["trust_threshold"] = int((emotional_intelligence * 0.6) + (consistency * 0.4))

    # Expertise threshold based on critical thinking
    critical_thinking = metrics.get("critical_thinking", 50)
    thresholds["expertise_threshold"] = int(critical_thinking * 0.9)  # Slightly lower bar for others

    # Collaboration threshold based on adaptability + emotional intelligence
    adaptability = metrics.get("adaptability", 50)
    thresholds["collaboration_threshold"] = int((adaptability * 0.5) + (emotional_intelligence * 0.5))

    # Confidence threshold matches own confidence
    confidence = metrics.get("confidence", 50)
    thresholds["confidence_threshold"] = int(confidence * 0.9)  # Expect similar confidence in others

    # Humility threshold based on own humility
    humility = metrics.get("humility", 50)
    thresholds["humility_threshold"] = int(humility)  # Expect same level of humility

    # Ensure all values are within 0-100 range
    for key in thresholds:
        thresholds[key] = max(0, min(100, thresholds[key]))

    return thresholds


def get_effective_thresholds(config: DecisionConfig, metrics: Optional[Dict[str, float]] = None) -> Dict[str, int]:
    """
    Get effective thresholds, either from config or auto-calculated

    Args:
        config: Decision configuration
        metrics: Optional self-evaluation metrics for auto-calculation

    Returns:
        Dictionary with effective threshold values
    """
    # If auto-thresholds disabled or no metrics, use config values
    if not config.auto_thresholds or not metrics:
        return {
            "trust_threshold": config.trust_threshold,
            "expertise_threshold": config.expertise_threshold,
            "collaboration_threshold": config.collaboration_threshold,
            "confidence_threshold": config.confidence_threshold,
            "humility_threshold": config.humility_threshold,
        }

    # Calculate auto-thresholds from self-evaluation
    return calculate_auto_thresholds(metrics)
