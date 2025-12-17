"""
Relationships Module

Phase 5: Relationships & Social Dynamics

Provides:
- Relationship data structures and persistence
- Configurable trust scoring algorithms
- Automatic relationship progression
- Shared experiences tracking
- Third-party reputation aggregation
- Best friend management

Usage:
    from relationships import SocialDynamicsManager

    # Initialize for a Qube
    social = SocialDynamicsManager(
        qube_data_dir="data/qubes/Alice_A1B2C3D4",
        trust_profile="analytical"
    )

    # Record an interaction
    rel = social.record_message(
        entity_id="B2C3D4E5",
        is_outgoing=True
    )

    # Record a collaboration
    rel = social.record_collaboration(
        entity_id="B2C3D4E5",
        succeeded=True,
        importance=1.5
    )

    # Get trust score
    trust = social.calculate_trust_score("B2C3D4E5")

    # Designate best friend
    social.designate_best_friend("B2C3D4E5")
"""

from relationships.relationship import Relationship, RelationshipStorage
from relationships.trust import TrustScorer
from relationships.progression import RelationshipProgressionManager
from relationships.social import SocialDynamicsManager
from relationships.memory_refresh import refresh_memory_from_peer
from relationships.websocket_server import (
    get_ws_server,
    broadcast_relationship_update,
    broadcast_relationship_progression,
    broadcast_best_friend_changed,
)

__all__ = [
    "Relationship",
    "RelationshipStorage",
    "TrustScorer",
    "RelationshipProgressionManager",
    "SocialDynamicsManager",
    "refresh_memory_from_peer",
    "get_ws_server",
    "broadcast_relationship_update",
    "broadcast_relationship_progression",
    "broadcast_best_friend_changed",
]
