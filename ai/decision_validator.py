"""
Decision Validation Layer

Pre-flight checks for actions using relationship and self-evaluation metrics.
Provides warnings, confidence adjustments, or blocking based on validation strictness.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from config.user_preferences import DecisionConfig
from ai.tools.decision_support import get_effective_thresholds
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of decision validation"""
    allowed: bool
    confidence: float  # 0.0 to 1.0
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    blocking_reason: Optional[str] = None


class DecisionValidator:
    """Validates actions using relationship and self-evaluation metrics"""

    def __init__(self, qube):
        """
        Initialize validator with qube context

        Args:
            qube: Qube instance with decision_config, relationships, and self_evaluation
        """
        self.qube = qube
        self.config: DecisionConfig = qube.decision_config

    async def validate_action(
        self,
        action_type: str,
        target_entity: Optional[str] = None,
        **kwargs
    ) -> ValidationResult:
        """
        Validate action before execution

        Action types:
        - share_sensitive: Sharing private/sensitive information
        - delegate_critical: Delegating important task
        - trust_with_access: Granting system/data access
        - collaborate: Working together on task
        - teach: Providing instruction/guidance
        - advise: Giving advice/recommendations
        - web_search: Web search (no validation needed)
        - generate_image: Image generation (no validation needed)
        - memory_search: Memory search (no validation needed)
        - browse_url: Browse URL (no validation needed)

        Args:
            action_type: Type of action being validated
            target_entity: Entity ID of action target (optional)
            **kwargs: Additional action parameters

        Returns:
            ValidationResult with allowed/warnings/suggestions
        """
        # Skip validation for non-sensitive tools
        low_stakes_tools = {
            "web_search", "generate_image", "memory_search",
            "browse_url", "describe_my_avatar", "get_relationships",
            "query_decision_context", "compare_options", "check_my_capability"
        }

        if action_type in low_stakes_tools:
            return ValidationResult(
                allowed=True,
                confidence=1.0
            )

        # Map tool names to decision types
        action_to_decision_type = {
            "share_sensitive": "trust_sensitive",
            "delegate_critical": "delegation",
            "trust_with_access": "trust_sensitive",
            "collaborate": "collaboration",
            "teach": "collaboration",
            "advise": "collaboration"
        }

        decision_type = action_to_decision_type.get(action_type, "general")

        # Get effective thresholds (auto or manual)
        metrics = self.qube.self_evaluation.metrics if hasattr(self.qube, 'self_evaluation') else None
        effective_thresholds = get_effective_thresholds(self.config, metrics)

        # Initialize result
        warnings = []
        suggestions = []
        confidence = 1.0

        # Validate with target entity if provided
        if target_entity:
            rel = self.qube.relationships.get_relationship(target_entity)

            if not rel:
                warnings.append(f"No relationship history with {target_entity}")
                suggestions.append("Consider using query_decision_context tool to assess this entity first")
                confidence *= 0.7
            else:
                # Check relationship metrics against thresholds
                from ai.tools.decision_support import calculate_decision_score

                score = calculate_decision_score(
                    relationship=rel,
                    decision_type=decision_type,
                    config=self.config
                )

                # Apply strictness-based validation
                strictness = self.config.validation_strictness

                # Determine thresholds based on action type
                if decision_type == "trust_sensitive":
                    min_score = 70
                    min_trust = effective_thresholds["trust_threshold"]
                elif decision_type == "delegation":
                    min_score = 65
                    min_trust = effective_thresholds["trust_threshold"] - 10
                elif decision_type == "collaboration":
                    min_score = effective_thresholds["collaboration_threshold"]
                    min_trust = effective_thresholds["trust_threshold"] - 20
                else:
                    min_score = 50
                    min_trust = 40

                # Check negative metrics
                if rel.betrayal > self.config.max_betrayal:
                    if strictness >= 80:  # Hard mode
                        return ValidationResult(
                            allowed=False,
                            confidence=0.0,
                            warnings=[f"Betrayal history detected ({rel.betrayal:.0f})"],
                            blocking_reason=f"Entity {target_entity} has betrayal history above threshold ({self.config.max_betrayal})"
                        )
                    else:
                        warnings.append(f"⚠️ WARNING: Betrayal history ({rel.betrayal:.0f})")
                        confidence *= 0.5

                if rel.distrust > self.config.max_distrust:
                    warnings.append(f"High distrust level ({rel.distrust:.0f})")
                    confidence *= 0.7

                if rel.antagonism > self.config.max_antagonism:
                    warnings.append(f"Antagonism detected ({rel.antagonism:.0f})")
                    confidence *= 0.8

                # Check if score meets threshold
                if score < min_score:
                    if strictness >= 80:  # Hard mode - block
                        return ValidationResult(
                            allowed=False,
                            confidence=0.0,
                            warnings=[f"Decision score too low: {score:.1f} < {min_score}"],
                            suggestions=[
                                f"Build stronger relationship before {action_type}",
                                "Consider an entity with higher trust/reliability metrics"
                            ],
                            blocking_reason=f"Decision score {score:.1f} below minimum threshold {min_score}"
                        )
                    elif strictness >= 40:  # Medium mode - warn and reduce confidence
                        warnings.append(f"Decision score below recommended: {score:.1f} < {min_score}")
                        suggestions.append(f"Consider building stronger relationship before {action_type}")
                        confidence *= (score / min_score)  # Scale confidence by score ratio
                    else:  # Soft mode - just note it
                        warnings.append(f"Note: Decision score is {score:.1f}")

                # Check trust specifically
                if rel.trust < min_trust:
                    if strictness >= 80:
                        return ValidationResult(
                            allowed=False,
                            confidence=0.0,
                            warnings=[f"Trust too low: {rel.trust:.0f} < {min_trust}"],
                            blocking_reason=f"Trust level {rel.trust:.0f} below minimum threshold {min_trust}"
                        )
                    else:
                        warnings.append(f"Trust level: {rel.trust:.0f} (recommended: {min_trust}+)")
                        confidence *= (rel.trust / min_trust)

        # Self-evaluation validation (if action requires confidence)
        high_confidence_actions = {"teach", "advise", "delegate_critical"}

        if action_type in high_confidence_actions and hasattr(self.qube, 'self_evaluation'):
            from ai.tools.decision_support import assess_capability

            metrics = self.qube.self_evaluation.metrics
            capability_score = assess_capability(
                metrics=metrics,
                task_type=action_type,
                config=self.config
            )

            required_confidence = effective_thresholds["confidence_threshold"]

            if capability_score < required_confidence:
                if strictness >= 80:  # Hard mode - block
                    return ValidationResult(
                        allowed=False,
                        confidence=0.0,
                        warnings=[f"Self-assessment: capability score too low ({capability_score:.1f})"],
                        suggestions=["Consider requesting guidance or escalating to more experienced entity"],
                        blocking_reason=f"Capability score {capability_score:.1f} below confidence threshold {required_confidence}"
                    )
                else:
                    warnings.append(f"Self-assessment: capability score {capability_score:.1f} (recommended: {required_confidence}+)")
                    suggestions.append("Consider proceeding with caution or requesting peer review")
                    confidence *= (capability_score / 100)

        # Log validation decision
        logger.info(
            "action_validation",
            action_type=action_type,
            target_entity=target_entity,
            allowed=True,
            confidence=confidence,
            warnings=len(warnings),
            strictness=self.config.validation_strictness
        )

        return ValidationResult(
            allowed=True,
            confidence=max(0.0, min(1.0, confidence)),
            warnings=warnings,
            suggestions=suggestions
        )

    def get_strictness_level(self) -> str:
        """Get human-readable strictness level"""
        strictness = self.config.validation_strictness
        if strictness >= 80:
            return "hard"
        elif strictness >= 40:
            return "medium"
        else:
            return "soft"
