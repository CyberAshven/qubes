"""
Relationship Progression System

Manages progression through relationship statuses based on trust, interactions, and time.
From config/trust_scoring.yaml progression_thresholds
"""

from datetime import datetime, timezone
from typing import Optional

from relationships.relationship import Relationship
from relationships.trust import TrustScorer
from utils.logging import get_logger

logger = get_logger(__name__)


def _broadcast_update(qube_id: str, entity_id: str, relationship: Relationship):
    """Broadcast relationship update via WebSocket (optional)"""
    try:
        from relationships.websocket_server import broadcast_relationship_update
        broadcast_relationship_update(
            qube_id=qube_id,
            entity_id=entity_id,
            relationship_data={
                "relationship_status": relationship.status,
                "overall_trust_score": relationship.trust,
                "friendship_level": relationship.friendship,
                "affection_level": relationship.affection,
                "respect_level": relationship.respect,
                "total_messages": relationship.messages_sent + relationship.messages_received,
                "successful_tasks": relationship.collaborations_successful,
            }
        )
    except Exception as e:
        logger.debug(f"WebSocket broadcast failed (may be disabled): {e}")


def _get_global_settings():
    """Lazy import to avoid circular dependency"""
    try:
        from config.global_settings import get_global_settings
        return get_global_settings()
    except ImportError:
        return None


class RelationshipProgressionManager:
    """
    Manages automatic and manual relationship progression

    Handles progression through:
    unmet → stranger → acquaintance → friend → close_friend → best_friend
    """

    def __init__(self, trust_scorer: Optional[TrustScorer] = None):
        """
        Initialize progression manager

        Args:
            trust_scorer: TrustScorer instance (creates default if None)
        """
        self.trust_scorer = trust_scorer or TrustScorer()

        logger.info("progression_manager_initialized")

    def check_and_progress(
        self,
        relationship: Relationship,
        trust_profile: Optional[str] = None,
        qube_id: Optional[str] = None
    ) -> bool:
        """
        Check if relationship can progress and update if eligible

        Args:
            relationship: Relationship to check
            trust_profile: Trust scoring profile to use
            qube_id: ID of the qube (for WebSocket broadcasts)

        Returns:
            True if progressed, False otherwise
        """
        # Calculate current trust score
        trust_score = self.trust_scorer.calculate_trust_score(relationship, trust_profile)
        relationship.trust = trust_score

        # Get total interactions
        total_interactions = (
            relationship.messages_sent +
            relationship.messages_received
        )

        current_status = relationship.status
        new_status = self._determine_eligible_status(
            relationship,
            trust_score,
            total_interactions
        )

        if new_status != current_status:
            relationship.progress_status(new_status)

            logger.info(
                "relationship_progressed",
                entity_id=relationship.entity_id,
                old_status=current_status,
                new_status=new_status,
                trust_score=trust_score,
                interactions=total_interactions
            )

            # Broadcast progression event
            if qube_id:
                try:
                    from relationships.websocket_server import broadcast_relationship_progression
                    broadcast_relationship_progression(
                        qube_id=qube_id,
                        entity_id=relationship.entity_id,
                        old_status=current_status,
                        new_status=new_status,
                        trust_score=trust_score
                    )
                except Exception as e:
                    logger.debug(f"WebSocket broadcast failed: {e}")

            return True

        return False

    def _determine_eligible_status(
        self,
        relationship: Relationship,
        trust_score: float,
        total_interactions: int
    ) -> str:
        """
        Determine the highest status this relationship qualifies for

        Args:
            relationship: Relationship to evaluate
            trust_score: Current trust score
            total_interactions: Total interaction count

        Returns:
            Highest eligible status
        """
        # Special cases
        if not relationship.has_met:
            return "unmet"

        if relationship.is_best_friend:
            return "best_friend"

        # Check from highest to lowest (excluding best_friend which is manual)
        statuses = ["close_friend", "friend", "acquaintance", "stranger"]

        for status in statuses:
            if self._meets_requirements(relationship, status, trust_score, total_interactions):
                return status

        # Default to stranger if has_met
        return "stranger"

    def _meets_requirements(
        self,
        relationship: Relationship,
        status: str,
        trust_score: float,
        total_interactions: int
    ) -> bool:
        """
        Check if relationship meets requirements for a status

        Args:
            relationship: Relationship to check
            status: Target status
            trust_score: Current trust score
            total_interactions: Total interaction count

        Returns:
            True if requirements met
        """
        # Get thresholds
        min_trust = self.trust_scorer.get_progression_threshold(status)
        min_interactions = self.trust_scorer.get_min_interactions(status)

        # Trust score check
        if trust_score < min_trust:
            return False

        # Interaction count check
        if total_interactions < min_interactions:
            return False

        # Additional requirements for specific statuses
        # Check collaboration requirements from global settings
        global_settings = _get_global_settings()
        if global_settings:
            min_collabs = global_settings.get_min_collaborations()
        else:
            # Fallback to hardcoded (long grind mode)
            min_collabs = {
                "friend": 3,
                "close_friend": 15,
                "best_friend": 30
            }

        if status == "friend":
            required_collabs = min_collabs.get("friend", 3)
            if relationship.collaborations_successful < required_collabs:
                return False

        if status == "close_friend":
            # LONG GRIND MODE: Requires higher affection/respect and more collaborations
            if relationship.affection < 75 or relationship.respect < 75:  # Was 70
                return False
            required_collabs = min_collabs.get("close_friend", 15)
            if relationship.collaborations_successful < required_collabs:
                return False

        return True

    def designate_best_friend(
        self,
        relationship: Relationship,
        current_best_friend: Optional[Relationship] = None,
        qube_id: Optional[str] = None
    ) -> bool:
        """
        Manually designate someone as best friend

        Note: Only ONE best friend allowed per Qube. Will demote current best friend.

        Args:
            relationship: Relationship to promote
            current_best_friend: Current best friend (will be demoted)
            qube_id: ID of the qube (for WebSocket broadcasts)

        Returns:
            True if successful, False if requirements not met
        """
        # Check requirements
        # LONG GRIND MODE: Higher trust threshold (was 90)
        if relationship.trust < 95:
            logger.warning(
                "best_friend_trust_too_low",
                entity_id=relationship.entity_id,
                trust_score=relationship.trust,
                required=95
            )
            return False

        total_interactions = (
            relationship.messages_sent +
            relationship.messages_received
        )
        # LONG GRIND MODE: 10x more interactions (was 50)
        if total_interactions < 500:
            logger.warning(
                "best_friend_interactions_too_low",
                entity_id=relationship.entity_id,
                interactions=total_interactions,
                required=500
            )
            return False

        # LONG GRIND MODE: Requires many successful collaborations
        if relationship.collaborations_successful < 30:
            logger.warning(
                "best_friend_collaborations_too_low",
                entity_id=relationship.entity_id,
                collaborations=relationship.collaborations_successful,
                required=30
            )
            return False

        # LONG GRIND MODE: Requires high affection
        if relationship.affection < 85:
            logger.warning(
                "best_friend_affection_too_low",
                entity_id=relationship.entity_id,
                affection=relationship.affection,
                required=85
            )
            return False

        # Demote current best friend if exists
        if current_best_friend and current_best_friend.entity_id != relationship.entity_id:
            current_best_friend.is_best_friend = False
            current_best_friend.progress_status("close_friend")

            logger.info(
                "best_friend_demoted",
                old_best_friend=current_best_friend.entity_id,
                new_best_friend=relationship.entity_id
            )

        # Promote to best friend
        relationship.is_best_friend = True
        relationship.progress_status("best_friend")

        logger.info(
            "best_friend_designated",
            entity_id=relationship.entity_id
        )

        # Broadcast best friend change
        if qube_id:
            try:
                from relationships.websocket_server import broadcast_best_friend_changed
                old_bf_id = current_best_friend.entity_id if current_best_friend else None
                broadcast_best_friend_changed(
                    qube_id=qube_id,
                    old_best_friend=old_bf_id,
                    new_best_friend=relationship.entity_id
                )
            except Exception as e:
                logger.debug(f"WebSocket broadcast failed: {e}")

        return True

    def update_friendship_metrics(self, relationship: Relationship) -> None:
        """
        Update friendship_level, affection_level, respect_level

        From config: friendship_scoring weights

        Args:
            relationship: Relationship to update
        """
        if relationship.status not in ["friend", "close_friend", "best_friend"]:
            # Not friends yet
            relationship.friendship = 0
            return

        # Get scoring weights from config
        weights = self.trust_scorer.config.get("friendship_scoring", {
            "interaction_frequency_weight": 0.30,
            "successful_collaboration_weight": 0.40,
            "time_known_weight": 0.10,
            "compatibility_weight": 0.20
        })

        # Calculate components
        interaction_score = min(100, relationship.interaction_frequency_per_day * 20)

        collaboration_score = min(100, relationship.collaborations_successful * 10)

        # Time known (months since friendship anniversary)
        if relationship.friendship_anniversary:
            time_known_months = (
                (datetime.now(timezone.utc).timestamp() - relationship.friendship_anniversary)
                / (30 * 24 * 3600)
            )
            time_score = min(100, time_known_months * 5)
        else:
            time_score = 0

        compatibility_score = relationship.compatibility_score

        # Weighted friendship level
        friendship_level = (
            weights["interaction_frequency_weight"] * interaction_score +
            weights["successful_collaboration_weight"] * collaboration_score +
            weights["time_known_weight"] * time_score +
            weights["compatibility_weight"] * compatibility_score
        )

        relationship.friendship = round(max(0, min(100, friendship_level)), 2)

        # Update affection and respect based on shared experiences
        self._update_affection_respect(relationship)

        logger.debug(
            "friendship_metrics_updated",
            entity_id=relationship.entity_id,
            friendship_level=relationship.friendship,
            affection=relationship.affection,
            respect=relationship.respect
        )

    def _update_affection_respect(self, relationship: Relationship) -> None:
        """
        Update affection and respect based on shared experiences

        Args:
            relationship: Relationship to update
        """
        # Count positive/negative experiences
        positive_exp = sum(
            1 for exp in relationship.shared_experiences
            if exp.get("sentiment") == "positive"
        )
        negative_exp = sum(
            1 for exp in relationship.shared_experiences
            if exp.get("sentiment") == "negative"
        )

        # Affection increases with positive experiences
        # LONG GRIND MODE: Slower affection growth (2x slower)
        affection_delta = (positive_exp * 1) - (negative_exp * 2)  # Was 2 and -3
        relationship.affection = max(0, min(100, 50 + affection_delta))

        # Respect increases with successful collaborations and honesty
        # LONG GRIND MODE: Slower respect growth (2.5x slower)
        respect_base = relationship.honesty_score * 0.5
        respect_collab = relationship.collaborations_successful * 2  # Was 5
        relationship.respect = max(0, min(100, respect_base + respect_collab))

    def handle_interaction(
        self,
        relationship: Relationship,
        is_outgoing: bool,
        response_time_seconds: Optional[float] = None
    ) -> None:
        """
        Record an interaction and update metrics

        Args:
            relationship: Relationship to update
            is_outgoing: True if message sent, False if received
            response_time_seconds: Response time if applicable
        """
        # Update counters
        if is_outgoing:
            relationship.messages_sent += 1
        else:
            relationship.messages_received += 1

        # Update last interaction
        relationship.last_interaction_timestamp = int(datetime.now(timezone.utc).timestamp())

        # Mark as met if first interaction
        if not relationship.has_met:
            relationship.mark_as_met(block_number=None)  # Block number set elsewhere

        # Update responsiveness if response time provided
        if response_time_seconds is not None and not is_outgoing:
            self.trust_scorer.update_responsiveness(relationship, response_time_seconds)

        # Update interaction frequency
        self._update_interaction_frequency(relationship)

        logger.debug(
            "interaction_recorded",
            entity_id=relationship.entity_id,
            is_outgoing=is_outgoing,
            total_sent=relationship.messages_sent,
            total_received=relationship.messages_received
        )

    def _update_interaction_frequency(self, relationship: Relationship) -> None:
        """
        Calculate interactions per day

        Args:
            relationship: Relationship to update
        """
        if not relationship.first_contact_timestamp:
            relationship.interaction_frequency_per_day = 0.0
            return

        # Calculate days since first contact
        days_known = (
            (datetime.now(timezone.utc).timestamp() - relationship.first_contact_timestamp)
            / (24 * 3600)
        )

        if days_known < 0.1:  # Less than ~2 hours
            days_known = 0.1  # Avoid division issues

        total_interactions = (
            relationship.messages_sent +
            relationship.messages_received
        )

        relationship.interaction_frequency_per_day = round(total_interactions / days_known, 2)

    def handle_collaboration_outcome(
        self,
        relationship: Relationship,
        succeeded: bool,
        importance: float = 1.0
    ) -> None:
        """
        Record collaboration outcome and update trust

        Args:
            relationship: Relationship to update
            succeeded: Whether collaboration succeeded
            importance: Importance multiplier (0.1 to 3.0)
        """
        relationship.total_collaborations += 1

        if succeeded:
            relationship.collaborations_successful += 1
            # Add positive shared experience
            relationship.add_shared_experience(
                event="Successful collaboration",
                sentiment="positive",
                details={"importance": importance}
            )
        else:
            relationship.failed_joint_tasks += 1
            # Add negative shared experience
            relationship.add_shared_experience(
                event="Failed collaboration",
                sentiment="negative",
                details={"importance": importance}
            )

        # Update reliability trust component
        self.trust_scorer.update_reliability(relationship, succeeded, importance)

        logger.info(
            "collaboration_recorded",
            entity_id=relationship.entity_id,
            succeeded=succeeded,
            importance=importance,
            total_successful=relationship.collaborations_successful,
            total_failed=relationship.failed_joint_tasks
        )
