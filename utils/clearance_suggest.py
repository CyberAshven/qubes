"""
Clearance Suggestion System

Suggests appropriate clearance based on relationship status.
Tags are organizational only and do not affect clearance.
"""

from typing import List, Optional, Tuple
from utils.clearance_profiles import (
    CLEARANCE_HIERARCHY, LEVEL_TO_NAME, ClearanceConfig
)


# Base clearance suggestion from status
STATUS_TO_BASE_LEVEL = {
    "blocked": 0,
    "enemy": 0,
    "rival": 0,
    "suspicious": 0,
    "unmet": 0,
    "stranger": 1,      # public
    "acquaintance": 3,  # social
    "friend": 4,        # trusted
    "close_friend": 5,  # inner_circle
    "best_friend": 5,   # inner_circle
}


def suggest_clearance(
    status: str,
    tags: List[str],
    config: Optional[ClearanceConfig] = None
) -> Tuple[str, str]:
    """
    Suggest appropriate clearance based on status.

    Note: Tags are organizational only and do not affect clearance suggestions.

    Args:
        status: Relationship status
        tags: List of relationship tags (not used for clearance, kept for API compat)
        config: Optional ClearanceConfig (not used, kept for API compat)

    Returns:
        Tuple of (suggested_profile_name, reason)
    """
    # Special case: coworker tag suggests professional track for low-trust
    if "coworker" in tags and status in ["stranger", "acquaintance", "unmet"]:
        return ("professional", "Professional contact")

    # Get base level from status
    base_level = STATUS_TO_BASE_LEVEL.get(status, 0)

    # Build reason string
    reason = f"Based on relationship status: {status}"

    suggested_name = LEVEL_TO_NAME.get(base_level, "none")

    return (suggested_name, reason)


def get_clearance_for_status_change(
    old_status: str,
    new_status: str,
    current_clearance: str,
    tags: List[str],
    config: Optional[ClearanceConfig] = None
) -> Optional[Tuple[str, str]]:
    """
    Check if clearance should be updated after a status change.

    Returns:
        None if no change suggested, or (new_clearance, reason) tuple
    """
    old_suggested, _ = suggest_clearance(old_status, tags, config)
    new_suggested, reason = suggest_clearance(new_status, tags, config)

    # Only suggest if:
    # 1. New suggestion differs from old suggestion
    # 2. Current clearance matches old suggestion (hasn't been manually set)
    if new_suggested != old_suggested and current_clearance == old_suggested:
        return (new_suggested, reason)

    return None
