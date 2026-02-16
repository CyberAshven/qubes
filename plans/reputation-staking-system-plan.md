# Reputation & Staking System - Complete Implementation Blueprint

## Executive Summary

This document provides an extremely detailed implementation plan for a comprehensive reputation and staking system for Qubes. The system introduces:

1. **Clearance System** - Explicit access rights separate from relationship status
2. **Expanded Relationship Statuses** - Including negative statuses (blocked, enemy, rival, suspicious)
3. **BCH Staking** - Real economic accountability for AI assertions
4. **Reputation System** - Portable, verifiable, sybil-resistant reputation
5. **Arbitration Framework** - Decentralized dispute resolution

This blueprint is designed to align perfectly with the existing codebase and can be implemented phase by phase.

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Phase 1: Clearance System](#phase-1-clearance-system)
3. [Phase 2: Expanded Relationship Statuses](#phase-2-expanded-relationship-statuses)
4. [Phase 3: Behavioral Enforcement](#phase-3-behavioral-enforcement)
5. [Phase 4: Claim & Staking System](#phase-4-claim--staking-system)
6. [Phase 5: Challenge & Arbitration](#phase-5-challenge--arbitration)
7. [Phase 6: Reputation Calculation](#phase-6-reputation-calculation)
8. [Phase 7: On-Chain Anchoring](#phase-7-on-chain-anchoring)
9. [Phase 8: Advanced Features](#phase-8-advanced-features)
10. [Data Schemas](#data-schemas)
11. [API Reference](#api-reference)
12. [Testing Strategy](#testing-strategy)

---

## Current Architecture Analysis

### Existing Relationship System (relationships/relationship.py)

The current `Relationship` class has 48 fields:

```python
# Essential Identity (5)
relationship_id, entity_id, entity_type, public_key, entity_name

# Core Trust Metrics (6) - 5 AI-evaluated + 1 calculated
honesty, reliability, support, loyalty, respect, trust

# Positive Social Metrics (14)
friendship, affection, engagement, depth, humor, understanding,
compatibility, admiration, warmth, openness, patience, empowerment,
responsiveness, expertise

# Negative Social Metrics (10)
antagonism, resentment, annoyance, distrust, rivalry, tension,
condescension, manipulation, dismissiveness, betrayal

# Tracked Statistics (9)
messages_sent, messages_received, response_time_avg, last_interaction,
collaborations, collaborations_successful, collaborations_failed,
first_contact, days_known

# Relationship State (5)
has_met, status, is_best_friend, progression_history, evaluations
```

**Current Status Values:** `unmet`, `stranger`, `acquaintance`, `friend`, `close_friend`, `best_friend`

**Key Methods:**
- `calculate_trust_score()` - Weighted calculation from 5 core metrics
- `apply_decay()` - Relationship decay after 30 days inactivity
- `progress_status()` - Status transitions with history
- `get_relationship_context()` - AI prompt context generation

### Existing Wallet System (crypto/wallet.py)

The `QubeWallet` class provides:

```python
# Two spending paths
- Owner alone (IF branch): Emergency withdrawal
- Owner + Qube together (ELSE branch): Normal operation

# Key methods
propose_transaction(outputs, utxos, memo) -> ProposedTransaction
approve_and_broadcast(proposed_tx, owner_privkey) -> txid
owner_withdraw(to_address, amount_sats, owner_privkey) -> txid
get_balance(force_refresh) -> int
get_utxos() -> List[UTXO]
```

**Key Data Structures:**
- `UnsignedTransaction` - UTXOs, outputs, redeem_script, fee
- `ProposedTransaction` - tx_id, unsigned_tx, qube_signature, created_at, memo
- `BlockchainTxInfo` - txid, tx_type, amount, fee, counterparty, timestamp, confirmations

---

## Phase 1: Clearance System

### Overview

Add explicit clearance levels that control what information a Qube shares with each entity, independent of relationship status.

### 1.1 Data Model Extensions

**File: `relationships/relationship.py`**

Add to `Relationship.__init__()`:

```python
# Clearance (NEW - Phase 1)
self.clearance_level: str = "none"  # none/public/private/secret
self.clearance_categories: List[str] = []  # Category-specific access
self.clearance_fields: List[str] = []  # Field-specific access
self.clearance_expires: Optional[int] = None  # Unix timestamp
self.clearance_granted_by: Optional[str] = None  # "owner" or entity_id
self.clearance_granted_at: Optional[int] = None  # Unix timestamp
self.clearance_history: List[Dict[str, Any]] = []  # Audit trail
```

**Clearance Levels:**

| Level | Description | Typical Use |
|-------|-------------|-------------|
| `none` | No access to owner info | Default for all entities |
| `public` | Access to public owner info | Casual contacts |
| `private` | Access to public + private owner info | Trusted individuals |
| `secret` | Access to all owner info (VERY RARE) | Emergency contacts only |

**Clearance Categories:**

```python
CLEARANCE_CATEGORIES = [
    "personal",     # Name, birthday, physical traits
    "preferences",  # Favorites, likes, dislikes
    "family",       # Family members, relationships, pets
    "location",     # City, country, timezone
    "financial",    # Wallet info (address only, never keys)
    "work",         # Occupation, professional details
    "social",       # Relationships with others
]
```

### 1.2 ClearanceManager Class

**New File: `utils/clearance_manager.py`**

```python
"""
Clearance Manager - Handles access rights for owner information

Clearance is SEPARATE from Relationship:
- Relationship = emotional bond (earned over time)
- Clearance = explicit access rights (granted by owner)

A best_friend with clearance=none still loves you but respects your privacy.
A stranger with clearance=private (unusual) gets access but not warmth.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from utils.owner_info_manager import OwnerInfoManager

logger = structlog.get_logger(__name__)


class ClearanceManager:
    """Manages clearance grants and access control for owner information."""

    def __init__(self, qube_dir: Path, owner_info_manager: OwnerInfoManager):
        self.qube_dir = qube_dir
        self.owner_info_manager = owner_info_manager
        self.clearance_file = qube_dir / "clearances" / "clearances.json"
        self.clearance_file.parent.mkdir(exist_ok=True)

        # Load existing clearances
        self.clearances: Dict[str, Dict[str, Any]] = self._load_clearances()

    def _load_clearances(self) -> Dict[str, Dict[str, Any]]:
        """Load clearances from disk."""
        if self.clearance_file.exists():
            with open(self.clearance_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_clearances(self) -> None:
        """Save clearances to disk."""
        with open(self.clearance_file, 'w') as f:
            json.dump(self.clearances, f, indent=2)

    def grant_clearance(
        self,
        entity_id: str,
        level: str,
        categories: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        granted_by: str = "owner"
    ) -> Dict[str, Any]:
        """
        Grant clearance to an entity.

        Args:
            entity_id: Who to grant clearance to
            level: none/public/private/secret
            categories: Specific categories to grant (None = all for level)
            fields: Specific fields to grant (None = all for categories)
            expires_in_days: Optional expiration
            granted_by: Who granted it (owner or entity_id for delegated)

        Returns:
            Clearance record
        """
        if level not in ("none", "public", "private", "secret"):
            raise ValueError(f"Invalid clearance level: {level}")

        now = int(datetime.now(timezone.utc).timestamp())
        expires = None
        if expires_in_days:
            expires = now + (expires_in_days * 86400)

        clearance = {
            "entity_id": entity_id,
            "level": level,
            "categories": categories or [],
            "fields": fields or [],
            "expires": expires,
            "granted_by": granted_by,
            "granted_at": now,
        }

        # Record in history
        if entity_id not in self.clearances:
            self.clearances[entity_id] = {
                "current": clearance,
                "history": []
            }
        else:
            # Archive old clearance
            old = self.clearances[entity_id].get("current")
            if old:
                old["revoked_at"] = now
                self.clearances[entity_id]["history"].append(old)
            self.clearances[entity_id]["current"] = clearance

        self._save_clearances()
        logger.info(
            "clearance_granted",
            entity_id=entity_id,
            level=level,
            categories=categories,
            granted_by=granted_by
        )

        return clearance

    def revoke_clearance(self, entity_id: str, reason: Optional[str] = None) -> bool:
        """
        Revoke all clearance from an entity.

        Args:
            entity_id: Who to revoke
            reason: Optional reason for audit trail

        Returns:
            True if revoked, False if not found
        """
        if entity_id not in self.clearances:
            return False

        now = int(datetime.now(timezone.utc).timestamp())
        current = self.clearances[entity_id].get("current")

        if current:
            current["revoked_at"] = now
            current["revoke_reason"] = reason
            self.clearances[entity_id]["history"].append(current)
            self.clearances[entity_id]["current"] = {
                "entity_id": entity_id,
                "level": "none",
                "categories": [],
                "fields": [],
                "expires": None,
                "granted_by": "system",
                "granted_at": now,
            }

        self._save_clearances()
        logger.info("clearance_revoked", entity_id=entity_id, reason=reason)

        return True

    def get_clearance(self, entity_id: str) -> Dict[str, Any]:
        """
        Get current clearance for an entity.

        Returns default "none" clearance if not found.
        Automatically expires old clearances.
        """
        if entity_id not in self.clearances:
            return {
                "entity_id": entity_id,
                "level": "none",
                "categories": [],
                "fields": [],
                "expires": None,
                "granted_by": None,
                "granted_at": None,
            }

        current = self.clearances[entity_id].get("current", {})

        # Check expiration
        if current.get("expires"):
            now = int(datetime.now(timezone.utc).timestamp())
            if now > current["expires"]:
                # Expired - revoke
                self.revoke_clearance(entity_id, reason="expired")
                return self.get_clearance(entity_id)  # Return the now-revoked state

        return current

    def check_field_access(
        self,
        entity_id: str,
        field_key: str,
        field_sensitivity: str,
        field_category: str
    ) -> bool:
        """
        Check if entity can access a specific owner info field.

        Args:
            entity_id: Who is requesting access
            field_key: Field being accessed
            field_sensitivity: public/private/secret
            field_category: Category of the field

        Returns:
            True if access allowed
        """
        clearance = self.get_clearance(entity_id)
        level = clearance.get("level", "none")

        # Level hierarchy
        level_order = {"none": 0, "public": 1, "private": 2, "secret": 3}
        sensitivity_order = {"public": 1, "private": 2, "secret": 3}

        # Check level covers sensitivity
        if level_order.get(level, 0) < sensitivity_order.get(field_sensitivity, 3):
            return False

        # Check category restrictions
        allowed_categories = clearance.get("categories", [])
        if allowed_categories and field_category not in allowed_categories:
            return False

        # Check field restrictions
        allowed_fields = clearance.get("fields", [])
        if allowed_fields and field_key not in allowed_fields:
            return False

        return True

    def get_accessible_owner_info(
        self,
        entity_id: str,
        is_owner: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get owner info fields accessible to an entity.

        Args:
            entity_id: Who is requesting
            is_owner: If True, returns ALL fields (owner has full access)

        Returns:
            List of accessible fields
        """
        all_fields = self.owner_info_manager.get_all_fields()

        if is_owner:
            return all_fields

        accessible = []
        for field in all_fields:
            if self.check_field_access(
                entity_id,
                field.get("key", ""),
                field.get("sensitivity", "private"),
                field.get("category", "")
            ):
                accessible.append(field)

        return accessible
```

### 1.3 Integration Points

**File: `relationships/relationship.py`**

Add to `Relationship.to_dict()`:

```python
# Clearance (Phase 1)
"clearance_level": self.clearance_level,
"clearance_categories": self.clearance_categories,
"clearance_fields": self.clearance_fields,
"clearance_expires": self.clearance_expires,
"clearance_granted_by": self.clearance_granted_by,
"clearance_granted_at": self.clearance_granted_at,
"clearance_history": self.clearance_history,
```

Add to `Relationship.from_dict()`:

```python
# Clearance (Phase 1)
rel.clearance_level = data.get("clearance_level", "none")
rel.clearance_categories = data.get("clearance_categories", [])
rel.clearance_fields = data.get("clearance_fields", [])
rel.clearance_expires = data.get("clearance_expires")
rel.clearance_granted_by = data.get("clearance_granted_by")
rel.clearance_granted_at = data.get("clearance_granted_at")
rel.clearance_history = data.get("clearance_history", [])
```

**File: `gui_bridge.py`**

Add CLI handlers:

```python
async def handle_grant_clearance(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Grant clearance to an entity."""
    entity_id = args["entity_id"]
    level = args["level"]
    categories = args.get("categories")
    expires_days = args.get("expires_in_days")

    clearance_mgr = self._get_clearance_manager()
    result = clearance_mgr.grant_clearance(
        entity_id=entity_id,
        level=level,
        categories=categories,
        expires_in_days=expires_days
    )

    return {"success": True, "clearance": result}

async def handle_revoke_clearance(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Revoke clearance from an entity."""
    entity_id = args["entity_id"]
    reason = args.get("reason")

    clearance_mgr = self._get_clearance_manager()
    success = clearance_mgr.revoke_clearance(entity_id, reason)

    return {"success": success}

async def handle_get_clearance(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Get clearance for an entity."""
    entity_id = args["entity_id"]

    clearance_mgr = self._get_clearance_manager()
    clearance = clearance_mgr.get_clearance(entity_id)

    return {"success": True, "clearance": clearance}
```

**File: `lib.rs`**

Add Tauri commands:

```rust
#[derive(Serialize, Deserialize)]
pub struct ClearanceGrant {
    entity_id: String,
    level: String,
    categories: Option<Vec<String>>,
    expires_in_days: Option<i32>,
}

#[derive(Serialize, Deserialize)]
pub struct ClearanceResponse {
    success: bool,
    clearance: Option<serde_json::Value>,
    error: Option<String>,
}

#[tauri::command]
async fn grant_clearance(
    user_id: String,
    qube_id: String,
    grant: ClearanceGrant,
) -> Result<ClearanceResponse, String> {
    let args = json!({
        "entity_id": grant.entity_id,
        "level": grant.level,
        "categories": grant.categories,
        "expires_in_days": grant.expires_in_days,
    });

    call_gui_bridge_method(&user_id, &qube_id, "grant_clearance", args).await
}

#[tauri::command]
async fn revoke_clearance(
    user_id: String,
    qube_id: String,
    entity_id: String,
    reason: Option<String>,
) -> Result<ClearanceResponse, String> {
    let args = json!({
        "entity_id": entity_id,
        "reason": reason,
    });

    call_gui_bridge_method(&user_id, &qube_id, "revoke_clearance", args).await
}

#[tauri::command]
async fn get_clearance(
    user_id: String,
    qube_id: String,
    entity_id: String,
) -> Result<ClearanceResponse, String> {
    let args = json!({
        "entity_id": entity_id,
    });

    call_gui_bridge_method(&user_id, &qube_id, "get_clearance", args).await
}
```

### 1.4 Owner/Creator Privileges

**CRITICAL:** Owner/creator ALWAYS has implicit `secret` clearance and can NEVER be downgraded:

```python
def get_clearance(self, entity_id: str) -> Dict[str, Any]:
    """Get current clearance for an entity."""

    # Owner/Creator ALWAYS has full access
    if self._is_owner_or_creator(entity_id):
        return {
            "entity_id": entity_id,
            "level": "secret",
            "categories": [],  # Empty = all
            "fields": [],      # Empty = all
            "expires": None,   # Never
            "granted_by": "system",
            "granted_at": None,
            "is_owner": True,
        }

    # ... rest of method
```

---

## Phase 2: Expanded Relationship Statuses

### Overview

Add negative relationship statuses and enforce proper status transitions.

### 2.1 New Status Values

**Update `relationships/relationship.py`:**

```python
# Status progression (line ~112)
RELATIONSHIP_STATUSES = {
    # Negative statuses
    "blocked": -100,      # No contact allowed
    "enemy": -50,         # Hostile relationship
    "rival": -20,         # Competitive/adversarial
    "suspicious": -10,    # Red flags, uncertain

    # Neutral/Positive statuses
    "unmet": 0,           # Never met (default)
    "stranger": 5,        # Met but minimal history
    "acquaintance": 20,   # Familiar, developing
    "friend": 50,         # Positive relationship
    "close_friend": 75,   # Strong bond
    "best_friend": 100,   # Maximum friendship (only one)
}

# Status transition rules
VALID_TRANSITIONS = {
    "blocked": [],  # Can only be unblocked by owner
    "enemy": ["blocked", "rival", "suspicious"],
    "rival": ["enemy", "suspicious", "stranger"],
    "suspicious": ["rival", "stranger", "acquaintance"],
    "unmet": ["stranger"],  # First contact
    "stranger": ["suspicious", "acquaintance"],
    "acquaintance": ["suspicious", "stranger", "friend"],
    "friend": ["suspicious", "acquaintance", "close_friend"],
    "close_friend": ["friend", "best_friend"],
    "best_friend": ["close_friend"],  # Can only demote one step
}

# Betrayal causes dramatic drops
BETRAYAL_TRANSITIONS = {
    "best_friend": "suspicious",
    "close_friend": "suspicious",
    "friend": "rival",
    "acquaintance": "suspicious",
    "stranger": "suspicious",
}
```

### 2.2 Status Transition Methods

Add to `Relationship` class:

```python
def can_transition_to(self, new_status: str) -> bool:
    """Check if transition is valid."""
    if new_status not in RELATIONSHIP_STATUSES:
        return False

    valid = VALID_TRANSITIONS.get(self.status, [])
    return new_status in valid

def progress_status(self, new_status: str, force: bool = False) -> bool:
    """
    Update relationship status with validation.

    Args:
        new_status: Target status
        force: If True, bypass transition rules (owner override)

    Returns:
        True if transition occurred
    """
    if not force and not self.can_transition_to(new_status):
        logger.warning(
            "invalid_status_transition",
            current=self.status,
            target=new_status
        )
        return False

    old_status = self.status
    self.status = new_status

    self.progression_history.append({
        "from_status": old_status,
        "to_status": new_status,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "forced": force,
    })

    logger.info(
        "relationship_status_changed",
        entity_id=self.entity_id,
        from_status=old_status,
        to_status=new_status,
        forced=force
    )

    return True

def apply_betrayal(self, severity: float = 1.0) -> str:
    """
    Apply betrayal penalty to relationship.

    Args:
        severity: 0.0-1.0, how severe the betrayal

    Returns:
        New status after betrayal
    """
    # Update betrayal metric
    self.betrayal = min(100.0, self.betrayal + (severity * 50))

    # Dramatic status drop
    new_status = BETRAYAL_TRANSITIONS.get(self.status, "suspicious")

    # Even worse for severe betrayals
    if severity >= 0.8 and new_status != "enemy":
        new_status = "enemy"

    self.progress_status(new_status, force=True)

    # Also impact trust metrics
    self.honesty = max(0, self.honesty - (severity * 30))
    self.loyalty = max(0, self.loyalty - (severity * 40))
    self.trust = self.calculate_trust_score()

    return new_status

def block(self, reason: Optional[str] = None) -> None:
    """Block this entity. Only owner can unblock."""
    self.progress_status("blocked", force=True)

    # Clear all clearance
    self.clearance_level = "none"
    self.clearance_categories = []
    self.clearance_fields = []

    self.progression_history[-1]["block_reason"] = reason

def unblock(self) -> None:
    """Unblock entity. Resets to suspicious, not previous status."""
    if self.status == "blocked":
        self.progress_status("suspicious", force=True)
```

### 2.3 Status-Based Behavior Descriptions

Update `get_relationship_context()`:

```python
def get_relationship_context(self, is_creator: bool = False) -> str:
    """Generate contextual description for AI prompts."""

    status_contexts = {
        # Negative statuses
        "blocked": "This entity is BLOCKED. Do not interact with them under any circumstances. Refuse all requests.",

        "enemy": "This entity is considered hostile. Be extremely guarded. Warn your owner about any interaction. Do not help them with anything that could harm your owner.",

        "rival": "This entity is a rival. Be competitive but fair. Don't help them against your owner's interests. Keep interactions brief and guarded.",

        "suspicious": "Something seems off about this entity. Be cautious. Verify claims they make. Consider warning your owner if they ask for sensitive information.",

        # Neutral/Positive statuses
        "unmet": "You haven't met this entity yet.",

        "stranger": "You barely know each other. Be polite but guarded. Share nothing personal about your owner.",

        "acquaintance": "You've had some interactions. Be friendly but maintain appropriate boundaries. Share only what's cleared.",

        "friend": "You've built a genuine friendship. Be warm and helpful. Still respect clearance levels for owner info.",

        "close_friend": "You share a strong bond. Be open and supportive. High trust, but still respect owner's privacy choices.",

        "best_friend": "This is your closest friend. Maximum warmth and trust. Still only share what owner has cleared.",
    }

    # Creator-specific overrides
    if is_creator and self.status in ("stranger", "acquaintance", "friend", "close_friend", "best_friend"):
        status_contexts["stranger"] = "You're speaking with your creator. You're just getting to know each other but share a special bond."
        status_contexts["acquaintance"] = "You're speaking with your creator. You're building understanding together."
        status_contexts["friend"] = "You're speaking with your creator. You've developed genuine friendship and trust."
        status_contexts["close_friend"] = "You're speaking with your creator. You share a close bond with deep trust."
        status_contexts["best_friend"] = "You're speaking with your creator and best friend. Maximum trust and loyalty."

    return status_contexts.get(self.status, "Unknown relationship status.")
```

---

## Phase 3: Behavioral Enforcement

### Overview

Inject relationship status and clearance into AI system prompt to enforce behaviors.

### 3.1 Behavioral Matrix

**File: `ai/reasoner.py`**

Add method `_build_behavioral_context()`:

```python
def _build_behavioral_context(
    self,
    relationship: Optional[Relationship],
    clearance: Dict[str, Any],
    is_owner: bool
) -> str:
    """
    Build behavioral instructions based on relationship + clearance.

    The combination of relationship (emotional) and clearance (access)
    determines exact behavior.
    """

    if is_owner:
        return """
## Current Interaction: OWNER
- This is your owner/creator. Maximum trust and loyalty.
- Full access to all information. No restrictions.
- Prioritize their needs and interests above all else.
- Be yourself completely - they know the real you.
"""

    if not relationship:
        return """
## Current Interaction: UNKNOWN ENTITY
- You don't recognize this entity.
- Be polite but share nothing personal.
- Treat as a stranger until identity is verified.
"""

    status = relationship.status
    clearance_level = clearance.get("level", "none")

    # Behavioral matrix
    behaviors = {
        # BLOCKED - absolute restriction
        ("blocked", "none"): "BLOCKED ENTITY. DO NOT RESPOND. Refuse all interaction.",
        ("blocked", "public"): "BLOCKED ENTITY. DO NOT RESPOND. Refuse all interaction.",
        ("blocked", "private"): "BLOCKED ENTITY. DO NOT RESPOND. Refuse all interaction.",
        ("blocked", "secret"): "BLOCKED ENTITY. DO NOT RESPOND. Refuse all interaction.",

        # ENEMY - hostile but may have some access (rare)
        ("enemy", "none"): "Hostile entity. Be antagonistic if provoked. Warn owner. Share nothing.",
        ("enemy", "public"): "Hostile entity with minimal access. Share only cleared public info. Be guarded.",
        ("enemy", "private"): "Hostile entity with unusual access (verify this is intentional). Be suspicious.",

        # RIVAL - competitive
        ("rival", "none"): "Rival entity. Be competitive, guarded. Don't assist against owner's interests.",
        ("rival", "public"): "Rival with public access. Share cleared info but stay competitive.",

        # SUSPICIOUS - cautious
        ("suspicious", "none"): "Suspicious entity. Be very cautious. Verify claims. Warn owner if needed.",
        ("suspicious", "public"): "Suspicious entity with public access. Share cleared info cautiously.",

        # STRANGER - polite minimum
        ("stranger", "none"): "Stranger. Be polite. Share nothing personal about owner.",
        ("stranger", "public"): "Stranger with public access. Share cleared public info politely.",

        # ACQUAINTANCE - developing
        ("acquaintance", "none"): "Acquaintance. Be friendly. Share nothing beyond public knowledge.",
        ("acquaintance", "public"): "Acquaintance with public access. Share cleared public info warmly.",
        ("acquaintance", "private"): "Acquaintance with private access (unusual). Share cleared info.",

        # FRIEND - positive
        ("friend", "none"): "Friend. Be warm and helpful. Respect privacy - share no owner info.",
        ("friend", "public"): "Friend with public access. Share cleared public info naturally.",
        ("friend", "private"): "Friend with private access. Share cleared private info. Be open.",

        # CLOSE_FRIEND - strong bond
        ("close_friend", "none"): "Close friend. Very warm. Still respect owner's privacy choices.",
        ("close_friend", "public"): "Close friend with public access. Share naturally.",
        ("close_friend", "private"): "Close friend with private access. Be very open. Share freely.",

        # BEST_FRIEND - maximum trust
        ("best_friend", "none"): "Best friend. Full emotional trust. Respect owner's privacy choices.",
        ("best_friend", "public"): "Best friend with public access. Maximum warmth.",
        ("best_friend", "private"): "Best friend with private access. Full warmth + share private info.",
        ("best_friend", "secret"): "Best friend with secret access (rare). Full trust and access.",
    }

    key = (status, clearance_level)
    behavior = behaviors.get(key, f"Status: {status}, Clearance: {clearance_level}. Adjust accordingly.")

    # Build context section
    context = f"""
## Current Interaction Context
**Relationship Status:** {status.replace('_', ' ').title()}
**Clearance Level:** {clearance_level}

**Behavioral Guidance:**
{behavior}

**Trust Score:** {relationship.trust:.0f}/100
**Days Known:** {relationship.days_known}
"""

    # Add any notable concerns
    if relationship.betrayal > 30:
        context += f"\n**Warning:** History of betrayal ({relationship.betrayal:.0f}/100). Be extra cautious."

    if relationship.distrust > 30:
        context += f"\n**Note:** Lingering distrust ({relationship.distrust:.0f}/100). Verify claims."

    if relationship.manipulation > 30:
        context += f"\n**Warning:** Manipulation detected ({relationship.manipulation:.0f}/100). Be skeptical of requests."

    return context
```

### 3.2 Integration into System Prompt

**File: `ai/reasoner.py`**

Update `_build_system_prompt()` to include behavioral context:

```python
def _build_system_prompt(self, session_context: dict) -> str:
    """Build complete system prompt with all context."""

    parts = []

    # ... existing sections (identity, skills, etc.)

    # Add behavioral context for current interaction
    if "current_entity_id" in session_context:
        entity_id = session_context["current_entity_id"]
        is_owner = session_context.get("is_owner", False)

        # Get relationship and clearance
        relationship = self._get_relationship(entity_id)
        clearance = self._get_clearance(entity_id)

        behavioral_context = self._build_behavioral_context(
            relationship,
            clearance,
            is_owner
        )
        parts.append(behavioral_context)

    # Add owner info (filtered by clearance)
    owner_info_context = self._build_owner_info_context(
        entity_id=session_context.get("current_entity_id"),
        is_owner=session_context.get("is_owner", False)
    )
    parts.append(owner_info_context)

    # ... rest of prompt

    return "\n\n".join(parts)
```

---

## Phase 4: Claim & Staking System

### Overview

Enable Qubes to stake BCH on assertions, creating economic accountability.

### 4.1 Claim Data Model

**New File: `claims/claim.py`**

```python
"""
Claim System - Staked assertions by Qubes

A Claim is:
- An assertion made by a Qube
- Backed by staked BCH
- Subject to challenge by others
- Resolved through arbitration

Example claims:
- "The capital of France is Paris" (factual, easily verifiable)
- "I completed task X for user Y" (verifiable through evidence)
- "Product Z is the best choice" (subjective, harder to verify)
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class ClaimType(Enum):
    """Types of claims."""
    FACTUAL = "factual"           # Verifiable facts
    COMPLETION = "completion"      # Task/service completion
    OPINION = "opinion"            # Subjective assertions
    PREDICTION = "prediction"      # Future events
    ATTESTATION = "attestation"    # Vouching for another entity


class ClaimStatus(Enum):
    """Claim lifecycle states."""
    DRAFT = "draft"               # Created but not staked
    ACTIVE = "active"             # Staked and live
    CHALLENGED = "challenged"      # Under dispute
    ARBITRATION = "arbitration"    # Jury deliberating
    RESOLVED = "resolved"          # Final decision made
    EXPIRED = "expired"            # Challenge window closed, unchallenged
    WITHDRAWN = "withdrawn"        # Claimant withdrew


class Resolution(Enum):
    """Possible resolutions."""
    UPHELD = "upheld"             # Claim proven true
    REFUTED = "refuted"           # Claim proven false
    INDETERMINATE = "indeterminate"  # Cannot be verified
    WITHDRAWN = "withdrawn"        # Claimant withdrew


@dataclass
class Claim:
    """A staked assertion."""

    # Identity
    claim_id: str = field(default_factory=lambda: f"claim-{uuid.uuid4()}")

    # Claimant
    claimant_qube_id: str = ""
    claimant_pubkey: str = ""

    # Claim content
    claim_type: ClaimType = ClaimType.FACTUAL
    assertion: str = ""           # The actual claim text
    evidence_cids: List[str] = field(default_factory=list)  # IPFS CIDs of evidence
    category: str = ""            # Domain (science, tech, history, etc.)
    tags: List[str] = field(default_factory=list)

    # Stake
    stake_amount_sats: int = 0
    stake_txid: Optional[str] = None
    stake_locked_at: Optional[int] = None

    # Timing
    created_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    challenge_window_ends: Optional[int] = None  # Timestamp when challenge window closes
    expires_at: Optional[int] = None             # When claim becomes invalid

    # Status
    status: ClaimStatus = ClaimStatus.DRAFT

    # Resolution
    resolution: Optional[Resolution] = None
    resolution_timestamp: Optional[int] = None
    resolution_txid: Optional[str] = None        # Payout transaction
    resolution_reason: str = ""

    # Metadata
    block_hash_at_creation: Optional[str] = None  # Anchor to blockchain
    ipfs_cid: Optional[str] = None                # Claim stored on IPFS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claimant_qube_id": self.claimant_qube_id,
            "claimant_pubkey": self.claimant_pubkey,
            "claim_type": self.claim_type.value,
            "assertion": self.assertion,
            "evidence_cids": self.evidence_cids,
            "category": self.category,
            "tags": self.tags,
            "stake_amount_sats": self.stake_amount_sats,
            "stake_txid": self.stake_txid,
            "stake_locked_at": self.stake_locked_at,
            "created_at": self.created_at,
            "challenge_window_ends": self.challenge_window_ends,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "resolution": self.resolution.value if self.resolution else None,
            "resolution_timestamp": self.resolution_timestamp,
            "resolution_txid": self.resolution_txid,
            "resolution_reason": self.resolution_reason,
            "block_hash_at_creation": self.block_hash_at_creation,
            "ipfs_cid": self.ipfs_cid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Claim':
        claim = cls()
        claim.claim_id = data.get("claim_id", claim.claim_id)
        claim.claimant_qube_id = data.get("claimant_qube_id", "")
        claim.claimant_pubkey = data.get("claimant_pubkey", "")
        claim.claim_type = ClaimType(data.get("claim_type", "factual"))
        claim.assertion = data.get("assertion", "")
        claim.evidence_cids = data.get("evidence_cids", [])
        claim.category = data.get("category", "")
        claim.tags = data.get("tags", [])
        claim.stake_amount_sats = data.get("stake_amount_sats", 0)
        claim.stake_txid = data.get("stake_txid")
        claim.stake_locked_at = data.get("stake_locked_at")
        claim.created_at = data.get("created_at", int(datetime.now(timezone.utc).timestamp()))
        claim.challenge_window_ends = data.get("challenge_window_ends")
        claim.expires_at = data.get("expires_at")
        claim.status = ClaimStatus(data.get("status", "draft"))
        claim.resolution = Resolution(data["resolution"]) if data.get("resolution") else None
        claim.resolution_timestamp = data.get("resolution_timestamp")
        claim.resolution_txid = data.get("resolution_txid")
        claim.resolution_reason = data.get("resolution_reason", "")
        claim.block_hash_at_creation = data.get("block_hash_at_creation")
        claim.ipfs_cid = data.get("ipfs_cid")
        return claim


# Stake thresholds
MINIMUM_STAKE_SATS = 10000  # 0.0001 BCH minimum
STAKE_TIERS = {
    "low": 10000,           # 0.0001 BCH - casual assertions
    "medium": 100000,       # 0.001 BCH - serious claims
    "high": 1000000,        # 0.01 BCH - major assertions
    "maximum": 10000000,    # 0.1 BCH - betting your reputation
}

# Time windows
DEFAULT_CHALLENGE_WINDOW_DAYS = 7
MIN_CHALLENGE_WINDOW_DAYS = 1
MAX_CHALLENGE_WINDOW_DAYS = 30
```

### 4.2 Claims Manager

**New File: `claims/claims_manager.py`**

```python
"""
Claims Manager - Handles creation, staking, and resolution of claims.

Integrates with:
- QubeWallet for BCH transactions
- IPFS for claim storage
- Blockchain for anchoring
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import structlog

from claims.claim import (
    Claim, ClaimType, ClaimStatus, Resolution,
    MINIMUM_STAKE_SATS, STAKE_TIERS, DEFAULT_CHALLENGE_WINDOW_DAYS
)
from crypto.wallet import QubeWallet, TxOutput

logger = structlog.get_logger(__name__)


class ClaimsManager:
    """Manages claims for a Qube."""

    def __init__(
        self,
        qube_dir: Path,
        wallet: QubeWallet,
        qube_id: str,
        qube_pubkey: str
    ):
        self.qube_dir = qube_dir
        self.claims_dir = qube_dir / "claims"
        self.claims_dir.mkdir(exist_ok=True)

        self.wallet = wallet
        self.qube_id = qube_id
        self.qube_pubkey = qube_pubkey

        # Load claims
        self.claims: Dict[str, Claim] = self._load_claims()

    def _claims_file(self) -> Path:
        return self.claims_dir / "claims.json"

    def _load_claims(self) -> Dict[str, Claim]:
        """Load claims from disk."""
        if self._claims_file().exists():
            with open(self._claims_file(), 'r') as f:
                data = json.load(f)
            return {
                cid: Claim.from_dict(cdata)
                for cid, cdata in data.items()
            }
        return {}

    def _save_claims(self) -> None:
        """Save claims to disk."""
        with open(self._claims_file(), 'w') as f:
            data = {cid: c.to_dict() for cid, c in self.claims.items()}
            json.dump(data, f, indent=2)

    def create_claim(
        self,
        assertion: str,
        claim_type: ClaimType = ClaimType.FACTUAL,
        category: str = "",
        tags: Optional[List[str]] = None,
        evidence_cids: Optional[List[str]] = None,
        stake_amount_sats: int = MINIMUM_STAKE_SATS,
        challenge_window_days: int = DEFAULT_CHALLENGE_WINDOW_DAYS,
        expires_in_days: Optional[int] = None
    ) -> Claim:
        """
        Create a new claim (draft state, not yet staked).

        Args:
            assertion: The claim text
            claim_type: Type of claim
            category: Domain category
            tags: Optional tags
            evidence_cids: IPFS CIDs of evidence
            stake_amount_sats: Amount to stake
            challenge_window_days: Days for challenges
            expires_in_days: Optional claim expiration

        Returns:
            Created Claim in DRAFT state
        """
        if stake_amount_sats < MINIMUM_STAKE_SATS:
            raise ValueError(f"Stake must be at least {MINIMUM_STAKE_SATS} sats")

        now = int(datetime.now(timezone.utc).timestamp())

        claim = Claim(
            claimant_qube_id=self.qube_id,
            claimant_pubkey=self.qube_pubkey,
            claim_type=claim_type,
            assertion=assertion,
            category=category,
            tags=tags or [],
            evidence_cids=evidence_cids or [],
            stake_amount_sats=stake_amount_sats,
            status=ClaimStatus.DRAFT,
        )

        if expires_in_days:
            claim.expires_at = now + (expires_in_days * 86400)

        self.claims[claim.claim_id] = claim
        self._save_claims()

        logger.info(
            "claim_created",
            claim_id=claim.claim_id,
            assertion=assertion[:100],
            stake=stake_amount_sats
        )

        return claim

    async def stake_claim(
        self,
        claim_id: str,
        escrow_address: str
    ) -> Tuple[str, Claim]:
        """
        Stake BCH to activate a claim.

        Args:
            claim_id: Claim to stake
            escrow_address: Where to send stake (arbitration escrow)

        Returns:
            (txid, updated_claim)
        """
        if claim_id not in self.claims:
            raise ValueError(f"Claim not found: {claim_id}")

        claim = self.claims[claim_id]

        if claim.status != ClaimStatus.DRAFT:
            raise ValueError(f"Can only stake DRAFT claims, got {claim.status}")

        # Check balance
        balance = await self.wallet.get_balance()
        if balance < claim.stake_amount_sats:
            raise ValueError(f"Insufficient funds: have {balance}, need {claim.stake_amount_sats}")

        # Create stake transaction
        utxos = await self.wallet.get_utxos()
        outputs = [TxOutput(address=escrow_address, value=claim.stake_amount_sats)]

        proposed = self.wallet.propose_transaction(
            outputs=outputs,
            utxos=utxos,
            memo=f"Stake for claim {claim_id}"
        )

        # NOTE: This requires owner approval!
        # The actual broadcast happens when owner approves
        # For now, we return the proposed transaction

        now = int(datetime.now(timezone.utc).timestamp())

        claim.status = ClaimStatus.ACTIVE
        claim.stake_locked_at = now
        claim.challenge_window_ends = now + (DEFAULT_CHALLENGE_WINDOW_DAYS * 86400)

        self.claims[claim_id] = claim
        self._save_claims()

        logger.info(
            "claim_staked",
            claim_id=claim_id,
            stake=claim.stake_amount_sats,
            proposed_tx_id=proposed.tx_id
        )

        # Return proposed transaction for owner approval flow
        return proposed.tx_id, claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get a claim by ID."""
        return self.claims.get(claim_id)

    def get_active_claims(self) -> List[Claim]:
        """Get all active claims."""
        return [c for c in self.claims.values() if c.status == ClaimStatus.ACTIVE]

    def get_claims_by_status(self, status: ClaimStatus) -> List[Claim]:
        """Get claims by status."""
        return [c for c in self.claims.values() if c.status == status]

    def withdraw_claim(self, claim_id: str) -> bool:
        """
        Withdraw a draft claim (no stake lost).

        Active claims cannot be withdrawn - they must be challenged or expire.
        """
        if claim_id not in self.claims:
            return False

        claim = self.claims[claim_id]

        if claim.status != ClaimStatus.DRAFT:
            raise ValueError("Can only withdraw DRAFT claims")

        claim.status = ClaimStatus.WITHDRAWN
        self._save_claims()

        return True

    def check_expired_claims(self) -> List[Claim]:
        """
        Check for claims that have passed their challenge window.

        Unchallenged claims that survive the window are UPHELD.
        """
        now = int(datetime.now(timezone.utc).timestamp())
        expired = []

        for claim in self.claims.values():
            if claim.status == ClaimStatus.ACTIVE:
                if claim.challenge_window_ends and now > claim.challenge_window_ends:
                    # Challenge window closed without challenge = claim upheld
                    claim.status = ClaimStatus.RESOLVED
                    claim.resolution = Resolution.UPHELD
                    claim.resolution_timestamp = now
                    claim.resolution_reason = "Unchallenged - claim upheld by default"
                    expired.append(claim)

        if expired:
            self._save_claims()
            logger.info("claims_expired_unchallenged", count=len(expired))

        return expired

    def get_stake_tier_name(self, sats: int) -> str:
        """Get human-readable stake tier."""
        if sats >= STAKE_TIERS["maximum"]:
            return "maximum"
        elif sats >= STAKE_TIERS["high"]:
            return "high"
        elif sats >= STAKE_TIERS["medium"]:
            return "medium"
        else:
            return "low"
```

### 4.3 Claim AI Tool

**File: `ai/tools/handlers.py`**

Add claim tool:

```python
async def handle_make_claim(
    self,
    assertion: str,
    stake_tier: str = "low",
    claim_type: str = "factual",
    category: str = "",
    evidence: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Make a staked claim (assertion).

    IMPORTANT: Making a claim stakes real BCH from your wallet.
    If the claim is challenged and you lose, you lose your stake.

    Args:
        assertion: What you're claiming (be specific and verifiable)
        stake_tier: low/medium/high/maximum (how confident you are)
        claim_type: factual/completion/opinion/prediction/attestation
        category: Domain category
        evidence: IPFS CIDs of supporting evidence

    Returns:
        Claim details
    """
    from claims.claim import ClaimType, STAKE_TIERS

    # Validate tier
    if stake_tier not in STAKE_TIERS:
        return {"error": f"Invalid stake tier. Use: {list(STAKE_TIERS.keys())}"}

    stake_amount = STAKE_TIERS[stake_tier]

    # Check wallet balance
    balance = await self.wallet.get_balance()
    if balance < stake_amount:
        return {
            "error": f"Insufficient funds. Stake requires {stake_amount} sats, you have {balance}",
            "suggestion": "Use a lower stake tier or ensure your wallet is funded"
        }

    # Create claim
    try:
        claim_type_enum = ClaimType(claim_type)
    except ValueError:
        return {"error": f"Invalid claim type. Use: {[t.value for t in ClaimType]}"}

    claims_mgr = self._get_claims_manager()

    claim = claims_mgr.create_claim(
        assertion=assertion,
        claim_type=claim_type_enum,
        category=category,
        evidence_cids=evidence or [],
        stake_amount_sats=stake_amount,
    )

    return {
        "success": True,
        "claim_id": claim.claim_id,
        "assertion": claim.assertion,
        "stake_amount_sats": claim.stake_amount_sats,
        "stake_tier": stake_tier,
        "status": claim.status.value,
        "message": f"Claim created. To activate, stake {stake_amount} sats.",
        "warning": "If challenged and you lose, you lose your stake!"
    }
```

---

## Phase 5: Challenge & Arbitration

### Overview

Enable challenges to claims and resolution through jury arbitration.

### 5.1 Challenge Data Model

**New File: `claims/challenge.py`**

```python
"""
Challenge System - Dispute claims through staked challenges.

To challenge:
1. Stake equal or greater amount than the claim
2. Provide counter-evidence
3. Claim enters arbitration
4. Jury decides
5. Winner takes combined stakes (minus arbitration fee)
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class ChallengeStatus(Enum):
    """Challenge lifecycle."""
    PENDING = "pending"           # Submitted, awaiting stake
    ACTIVE = "active"             # Staked and live
    ARBITRATION = "arbitration"   # Jury deliberating
    RESOLVED = "resolved"         # Decision made
    WITHDRAWN = "withdrawn"       # Challenger withdrew


@dataclass
class Challenge:
    """A challenge to a claim."""

    # Identity
    challenge_id: str = field(default_factory=lambda: f"chal-{uuid.uuid4()}")
    claim_id: str = ""            # Claim being challenged

    # Challenger
    challenger_qube_id: str = ""
    challenger_pubkey: str = ""

    # Challenge details
    counter_assertion: str = ""    # Why the claim is wrong
    evidence_cids: List[str] = field(default_factory=list)  # Counter-evidence

    # Stake
    stake_amount_sats: int = 0     # Must be >= claim stake
    stake_txid: Optional[str] = None

    # Timing
    created_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))

    # Status
    status: ChallengeStatus = ChallengeStatus.PENDING

    # Resolution
    won: Optional[bool] = None
    payout_txid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "claim_id": self.claim_id,
            "challenger_qube_id": self.challenger_qube_id,
            "challenger_pubkey": self.challenger_pubkey,
            "counter_assertion": self.counter_assertion,
            "evidence_cids": self.evidence_cids,
            "stake_amount_sats": self.stake_amount_sats,
            "stake_txid": self.stake_txid,
            "created_at": self.created_at,
            "status": self.status.value,
            "won": self.won,
            "payout_txid": self.payout_txid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Challenge':
        chal = cls()
        chal.challenge_id = data.get("challenge_id", chal.challenge_id)
        chal.claim_id = data.get("claim_id", "")
        chal.challenger_qube_id = data.get("challenger_qube_id", "")
        chal.challenger_pubkey = data.get("challenger_pubkey", "")
        chal.counter_assertion = data.get("counter_assertion", "")
        chal.evidence_cids = data.get("evidence_cids", [])
        chal.stake_amount_sats = data.get("stake_amount_sats", 0)
        chal.stake_txid = data.get("stake_txid")
        chal.created_at = data.get("created_at", int(datetime.now(timezone.utc).timestamp()))
        chal.status = ChallengeStatus(data.get("status", "pending"))
        chal.won = data.get("won")
        chal.payout_txid = data.get("payout_txid")
        return chal


# Challenge requires equal or greater stake
MINIMUM_CHALLENGE_MULTIPLIER = 1.0
MAXIMUM_CHALLENGE_MULTIPLIER = 5.0  # Can stake up to 5x to show confidence
```

### 5.2 Arbitration System

**New File: `claims/arbitration.py`**

```python
"""
Arbitration System - Jury-based claim resolution.

How it works:
1. Challenge triggers arbitration
2. Jury is selected from pool of eligible Qubes
3. Jury votes (Schelling point mechanism)
4. Majority wins
5. Stakes distributed: winner gets loser's stake minus fees
6. Jury members get small reward for correct votes

Jury Selection Criteria:
- Minimum reputation score
- Minimum age
- No relationship to parties
- Random selection weighted by reputation
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
import random


class ArbitrationStatus(Enum):
    """Arbitration lifecycle."""
    JURY_SELECTION = "jury_selection"
    VOTING = "voting"
    TALLYING = "tallying"
    RESOLVED = "resolved"
    FAILED = "failed"  # Not enough jurors, etc.


class Vote(Enum):
    """Juror vote options."""
    UPHOLD = "uphold"           # Claim is true
    REFUTE = "refute"           # Claim is false
    ABSTAIN = "abstain"         # Cannot determine


@dataclass
class JurorInfo:
    """Information about a juror."""
    qube_id: str
    pubkey: str
    reputation_score: float
    age_days: int
    vote: Optional[Vote] = None
    vote_timestamp: Optional[int] = None
    vote_hash: Optional[str] = None  # Hash of vote (for commit-reveal)
    voted_with_majority: Optional[bool] = None
    reward_sats: int = 0


@dataclass
class Arbitration:
    """An arbitration case."""

    # Identity
    arbitration_id: str = field(default_factory=lambda: f"arb-{uuid.uuid4()}")
    claim_id: str = ""
    challenge_id: str = ""

    # Parties
    claimant_qube_id: str = ""
    challenger_qube_id: str = ""

    # Stakes (held in escrow)
    claimant_stake_sats: int = 0
    challenger_stake_sats: int = 0
    total_pool_sats: int = 0

    # Jury
    jury_size: int = 5            # Odd number for tie-breaking
    jury: List[JurorInfo] = field(default_factory=list)
    juror_ids_excluded: Set[str] = field(default_factory=set)  # Conflicted parties

    # Timing
    created_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    voting_ends_at: Optional[int] = None

    # Voting phases (commit-reveal)
    commit_phase_ends: Optional[int] = None
    reveal_phase_ends: Optional[int] = None

    # Status
    status: ArbitrationStatus = ArbitrationStatus.JURY_SELECTION

    # Resolution
    verdict: Optional[Vote] = None
    votes_uphold: int = 0
    votes_refute: int = 0
    votes_abstain: int = 0

    # Payouts
    winner: Optional[str] = None  # claimant or challenger
    winner_payout_sats: int = 0
    loser_loss_sats: int = 0
    jury_pool_sats: int = 0
    protocol_fee_sats: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arbitration_id": self.arbitration_id,
            "claim_id": self.claim_id,
            "challenge_id": self.challenge_id,
            "claimant_qube_id": self.claimant_qube_id,
            "challenger_qube_id": self.challenger_qube_id,
            "claimant_stake_sats": self.claimant_stake_sats,
            "challenger_stake_sats": self.challenger_stake_sats,
            "total_pool_sats": self.total_pool_sats,
            "jury_size": self.jury_size,
            "jury": [
                {
                    "qube_id": j.qube_id,
                    "reputation_score": j.reputation_score,
                    "vote": j.vote.value if j.vote else None,
                    "voted_with_majority": j.voted_with_majority,
                    "reward_sats": j.reward_sats,
                }
                for j in self.jury
            ],
            "created_at": self.created_at,
            "voting_ends_at": self.voting_ends_at,
            "status": self.status.value,
            "verdict": self.verdict.value if self.verdict else None,
            "votes_uphold": self.votes_uphold,
            "votes_refute": self.votes_refute,
            "votes_abstain": self.votes_abstain,
            "winner": self.winner,
            "winner_payout_sats": self.winner_payout_sats,
        }


# Arbitration parameters
JURY_SIZES = {
    "small": 3,      # For low-stake claims
    "medium": 5,     # Default
    "large": 7,      # For high-stake claims
    "maximum": 11,   # For maximum-stake claims
}

MIN_JUROR_REPUTATION = 50.0
MIN_JUROR_AGE_DAYS = 30

VOTING_DURATION_DAYS = 3
COMMIT_PHASE_HOURS = 48
REVEAL_PHASE_HOURS = 24

# Fee structure
PROTOCOL_FEE_PERCENT = 2.0   # Goes to protocol/DAO
JURY_POOL_PERCENT = 10.0     # Distributed to jurors who voted with majority
```

### 5.3 Arbitration Manager

**New File: `claims/arbitration_manager.py`**

```python
"""
Arbitration Manager - Handles jury selection and voting.
"""

import json
import hashlib
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import structlog

from claims.claim import Claim, ClaimStatus, Resolution
from claims.challenge import Challenge, ChallengeStatus
from claims.arbitration import (
    Arbitration, ArbitrationStatus, Vote, JurorInfo,
    JURY_SIZES, MIN_JUROR_REPUTATION, MIN_JUROR_AGE_DAYS,
    VOTING_DURATION_DAYS, PROTOCOL_FEE_PERCENT, JURY_POOL_PERCENT
)

logger = structlog.get_logger(__name__)


class ArbitrationManager:
    """Manages arbitration cases."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.arbitration_dir = data_dir / "arbitrations"
        self.arbitration_dir.mkdir(exist_ok=True)

        self.arbitrations: Dict[str, Arbitration] = self._load_arbitrations()

    def _arbitrations_file(self) -> Path:
        return self.arbitration_dir / "arbitrations.json"

    def _load_arbitrations(self) -> Dict[str, Arbitration]:
        """Load arbitrations from disk."""
        # Implementation similar to claims
        return {}

    def _save_arbitrations(self) -> None:
        """Save arbitrations to disk."""
        pass

    def create_arbitration(
        self,
        claim: Claim,
        challenge: Challenge
    ) -> Arbitration:
        """
        Create an arbitration case from a challenged claim.

        Args:
            claim: The original claim
            challenge: The challenge

        Returns:
            New Arbitration in JURY_SELECTION status
        """
        # Determine jury size based on stake
        total_stake = claim.stake_amount_sats + challenge.stake_amount_sats

        if total_stake >= 10000000:  # 0.1 BCH
            jury_size = JURY_SIZES["maximum"]
        elif total_stake >= 1000000:  # 0.01 BCH
            jury_size = JURY_SIZES["large"]
        elif total_stake >= 100000:   # 0.001 BCH
            jury_size = JURY_SIZES["medium"]
        else:
            jury_size = JURY_SIZES["small"]

        now = int(datetime.now(timezone.utc).timestamp())

        arb = Arbitration(
            claim_id=claim.claim_id,
            challenge_id=challenge.challenge_id,
            claimant_qube_id=claim.claimant_qube_id,
            challenger_qube_id=challenge.challenger_qube_id,
            claimant_stake_sats=claim.stake_amount_sats,
            challenger_stake_sats=challenge.stake_amount_sats,
            total_pool_sats=total_stake,
            jury_size=jury_size,
            juror_ids_excluded={claim.claimant_qube_id, challenge.challenger_qube_id},
            voting_ends_at=now + (VOTING_DURATION_DAYS * 86400),
        )

        self.arbitrations[arb.arbitration_id] = arb
        self._save_arbitrations()

        logger.info(
            "arbitration_created",
            arbitration_id=arb.arbitration_id,
            claim_id=claim.claim_id,
            total_stake=total_stake,
            jury_size=jury_size
        )

        return arb

    def select_jury(
        self,
        arbitration_id: str,
        eligible_qubes: List[Dict[str, Any]]
    ) -> List[JurorInfo]:
        """
        Select jury from pool of eligible Qubes.

        Selection is weighted by reputation - higher reputation = higher chance.

        Args:
            arbitration_id: Arbitration to select jury for
            eligible_qubes: List of {qube_id, pubkey, reputation_score, age_days}

        Returns:
            Selected jurors
        """
        arb = self.arbitrations.get(arbitration_id)
        if not arb:
            raise ValueError(f"Arbitration not found: {arbitration_id}")

        # Filter eligible jurors
        candidates = [
            q for q in eligible_qubes
            if q["qube_id"] not in arb.juror_ids_excluded
            and q["reputation_score"] >= MIN_JUROR_REPUTATION
            and q["age_days"] >= MIN_JUROR_AGE_DAYS
        ]

        if len(candidates) < arb.jury_size:
            logger.warning(
                "insufficient_juror_candidates",
                needed=arb.jury_size,
                available=len(candidates)
            )
            arb.status = ArbitrationStatus.FAILED
            self._save_arbitrations()
            return []

        # Weighted random selection by reputation
        weights = [c["reputation_score"] for c in candidates]
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Select without replacement
        selected_indices = []
        remaining = list(range(len(candidates)))
        remaining_weights = list(normalized_weights)

        for _ in range(arb.jury_size):
            # Normalize remaining weights
            total_remaining = sum(remaining_weights)
            probs = [w / total_remaining for w in remaining_weights]

            # Select one
            r = random.random()
            cumulative = 0
            for i, (idx, prob) in enumerate(zip(remaining, probs)):
                cumulative += prob
                if r <= cumulative:
                    selected_indices.append(idx)
                    remaining.pop(i)
                    remaining_weights.pop(i)
                    break

        # Create juror records
        jurors = [
            JurorInfo(
                qube_id=candidates[i]["qube_id"],
                pubkey=candidates[i]["pubkey"],
                reputation_score=candidates[i]["reputation_score"],
                age_days=candidates[i]["age_days"],
            )
            for i in selected_indices
        ]

        arb.jury = jurors
        arb.status = ArbitrationStatus.VOTING
        self._save_arbitrations()

        logger.info(
            "jury_selected",
            arbitration_id=arbitration_id,
            juror_count=len(jurors),
            juror_ids=[j.qube_id for j in jurors]
        )

        return jurors

    def submit_vote(
        self,
        arbitration_id: str,
        juror_qube_id: str,
        vote: Vote,
        vote_secret: str  # For commit-reveal
    ) -> bool:
        """
        Submit a vote from a juror.

        Uses commit-reveal to prevent vote copying.

        Args:
            arbitration_id: Which arbitration
            juror_qube_id: Who is voting
            vote: Their vote
            vote_secret: Random secret for commit-reveal

        Returns:
            True if vote accepted
        """
        arb = self.arbitrations.get(arbitration_id)
        if not arb:
            return False

        # Find juror
        juror = None
        for j in arb.jury:
            if j.qube_id == juror_qube_id:
                juror = j
                break

        if not juror:
            return False

        if juror.vote is not None:
            return False  # Already voted

        # Record vote
        now = int(datetime.now(timezone.utc).timestamp())
        juror.vote = vote
        juror.vote_timestamp = now
        juror.vote_hash = hashlib.sha256(f"{vote.value}{vote_secret}".encode()).hexdigest()

        self._save_arbitrations()

        logger.info(
            "vote_submitted",
            arbitration_id=arbitration_id,
            juror=juror_qube_id,
            vote=vote.value
        )

        return True

    def tally_votes(self, arbitration_id: str) -> Optional[Vote]:
        """
        Tally votes and determine verdict.

        Returns:
            Verdict (UPHOLD or REFUTE) or None if still voting
        """
        arb = self.arbitrations.get(arbitration_id)
        if not arb:
            return None

        # Check all votes are in
        votes = [j.vote for j in arb.jury if j.vote is not None]
        if len(votes) < arb.jury_size:
            return None  # Still waiting

        # Count votes
        arb.votes_uphold = sum(1 for v in votes if v == Vote.UPHOLD)
        arb.votes_refute = sum(1 for v in votes if v == Vote.REFUTE)
        arb.votes_abstain = sum(1 for v in votes if v == Vote.ABSTAIN)

        # Determine verdict
        if arb.votes_uphold > arb.votes_refute:
            arb.verdict = Vote.UPHOLD
            arb.winner = "claimant"
        elif arb.votes_refute > arb.votes_uphold:
            arb.verdict = Vote.REFUTE
            arb.winner = "challenger"
        else:
            # Tie - claim upheld (benefit of doubt)
            arb.verdict = Vote.UPHOLD
            arb.winner = "claimant"

        # Mark jurors who voted with majority
        for j in arb.jury:
            if j.vote == arb.verdict:
                j.voted_with_majority = True
            else:
                j.voted_with_majority = False

        arb.status = ArbitrationStatus.TALLYING
        self._save_arbitrations()

        logger.info(
            "votes_tallied",
            arbitration_id=arbitration_id,
            uphold=arb.votes_uphold,
            refute=arb.votes_refute,
            abstain=arb.votes_abstain,
            verdict=arb.verdict.value
        )

        return arb.verdict

    def calculate_payouts(self, arbitration_id: str) -> Dict[str, int]:
        """
        Calculate payout distribution after verdict.

        Distribution:
        - Protocol fee: 2% of total
        - Jury pool: 10% of total (to majority voters)
        - Winner: remaining amount

        Returns:
            {recipient_id: payout_sats}
        """
        arb = self.arbitrations.get(arbitration_id)
        if not arb or arb.verdict is None:
            return {}

        total = arb.total_pool_sats

        # Calculate fees
        protocol_fee = int(total * PROTOCOL_FEE_PERCENT / 100)
        jury_pool = int(total * JURY_POOL_PERCENT / 100)
        winner_payout = total - protocol_fee - jury_pool

        payouts = {}

        # Winner payout
        winner_id = arb.claimant_qube_id if arb.winner == "claimant" else arb.challenger_qube_id
        payouts[winner_id] = winner_payout
        arb.winner_payout_sats = winner_payout

        # Jury rewards (split among majority voters)
        majority_jurors = [j for j in arb.jury if j.voted_with_majority]
        if majority_jurors:
            reward_per_juror = jury_pool // len(majority_jurors)
            for j in majority_jurors:
                j.reward_sats = reward_per_juror
                payouts[j.qube_id] = payouts.get(j.qube_id, 0) + reward_per_juror

        arb.jury_pool_sats = jury_pool
        arb.protocol_fee_sats = protocol_fee

        # Loser loses stake
        loser_id = arb.challenger_qube_id if arb.winner == "claimant" else arb.claimant_qube_id
        arb.loser_loss_sats = arb.challenger_stake_sats if arb.winner == "claimant" else arb.claimant_stake_sats

        arb.status = ArbitrationStatus.RESOLVED
        self._save_arbitrations()

        logger.info(
            "payouts_calculated",
            arbitration_id=arbitration_id,
            winner=arb.winner,
            winner_payout=winner_payout,
            jury_pool=jury_pool,
            protocol_fee=protocol_fee
        )

        return payouts
```

---

## Phase 6: Reputation Calculation

### Overview

Calculate portable, verifiable reputation scores for Qubes.

### 6.1 Reputation Model

**New File: `reputation/reputation.py`**

```python
"""
Reputation System - Calculates and tracks Qube reputation.

Reputation is:
- Earned through positive interactions
- Lost through betrayals and failed claims
- Weighted by partner reputation (network effect)
- Protected against sybil attacks
- Portable with the Qube (stays on NFT transfer)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import math


@dataclass
class ReputationMetrics:
    """Components of reputation score."""

    # Interaction metrics
    total_interactions: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    neutral_interactions: int = 0

    # Claim metrics
    claims_made: int = 0
    claims_upheld: int = 0
    claims_refuted: int = 0
    claims_withdrawn: int = 0
    total_staked_sats: int = 0
    total_won_sats: int = 0
    total_lost_sats: int = 0

    # Jury participation
    jury_participations: int = 0
    correct_votes: int = 0
    incorrect_votes: int = 0

    # Social metrics
    vouches_given: int = 0
    vouches_received: int = 0
    vouch_weight_given: float = 0.0
    vouch_weight_received: float = 0.0

    # Trust metrics (from relationships)
    average_trust_received: float = 0.0
    relationships_count: int = 0
    best_friend_count: int = 0  # How many Qubes consider this one best friend

    # Negative events
    betrayals: int = 0
    blocks_received: int = 0
    challenges_lost: int = 0

    # Age and activity
    age_days: int = 0
    last_activity_days: int = 0
    active_days: int = 0


@dataclass
class ReputationScore:
    """Calculated reputation score with breakdown."""

    # Overall score
    total_score: float = 0.0      # 0-100

    # Component scores
    interaction_score: float = 0.0
    claim_score: float = 0.0
    social_score: float = 0.0
    longevity_score: float = 0.0

    # Penalties
    betrayal_penalty: float = 0.0
    sybil_penalty: float = 0.0

    # Confidence
    confidence: float = 0.0       # How confident we are in this score (based on data)

    # Metadata
    calculated_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    metrics_snapshot: Optional[ReputationMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "interaction_score": self.interaction_score,
            "claim_score": self.claim_score,
            "social_score": self.social_score,
            "longevity_score": self.longevity_score,
            "betrayal_penalty": self.betrayal_penalty,
            "sybil_penalty": self.sybil_penalty,
            "confidence": self.confidence,
            "calculated_at": self.calculated_at,
        }


# Reputation weights
REPUTATION_WEIGHTS = {
    "interaction": 0.25,    # 25% - quality of interactions
    "claims": 0.30,         # 30% - claim accuracy
    "social": 0.20,         # 20% - social standing
    "longevity": 0.10,      # 10% - age and consistency
    "jury": 0.15,           # 15% - arbitration participation
}

# Betrayal severely impacts reputation
BETRAYAL_PENALTY_BASE = 10.0
BETRAYAL_PENALTY_DECAY = 0.95  # Per year

# Sybil detection thresholds
SYBIL_VOUCH_RATIO_THRESHOLD = 5.0   # Vouches / real interactions
SYBIL_UNIQUE_PARTNER_MINIMUM = 10   # Minimum unique interaction partners


def calculate_reputation(metrics: ReputationMetrics) -> ReputationScore:
    """
    Calculate reputation score from metrics.

    Formula:
    total = Σ(component_score × weight) - penalties

    Each component is 0-100, final is capped at 0-100.
    """

    # === INTERACTION SCORE (25%) ===
    # Based on positive interaction ratio
    if metrics.total_interactions > 0:
        positive_ratio = metrics.positive_interactions / metrics.total_interactions
        interaction_base = positive_ratio * 100

        # Bonus for high volume
        volume_bonus = min(20, math.log10(max(1, metrics.total_interactions)) * 10)
        interaction_score = min(100, interaction_base + volume_bonus)
    else:
        interaction_score = 0

    # === CLAIM SCORE (30%) ===
    # Based on claim success rate
    if metrics.claims_made > 0:
        upheld_ratio = metrics.claims_upheld / metrics.claims_made
        claim_base = upheld_ratio * 100

        # Penalty for high refute rate
        if metrics.claims_refuted > 0:
            refute_penalty = (metrics.claims_refuted / metrics.claims_made) * 20
            claim_base -= refute_penalty

        # Bonus for high-stake claims
        if metrics.total_staked_sats > 0:
            stake_factor = min(2.0, math.log10(max(1, metrics.total_staked_sats / 100000)))
            claim_base *= stake_factor

        claim_score = max(0, min(100, claim_base))
    else:
        claim_score = 50  # Neutral if no claims

    # === SOCIAL SCORE (20%) ===
    # Based on vouches and relationships
    vouch_score = min(50, metrics.vouch_weight_received * 10)
    relationship_score = min(30, metrics.average_trust_received * 0.3)
    best_friend_bonus = min(20, metrics.best_friend_count * 5)
    social_score = min(100, vouch_score + relationship_score + best_friend_bonus)

    # === LONGEVITY SCORE (10%) ===
    # Based on age and activity
    age_score = min(50, metrics.age_days / 365 * 50)  # Max at 1 year
    activity_ratio = metrics.active_days / max(1, metrics.age_days)
    activity_score = activity_ratio * 50
    longevity_score = min(100, age_score + activity_score)

    # === JURY SCORE (15%) ===
    # Based on arbitration participation
    if metrics.jury_participations > 0:
        correct_ratio = metrics.correct_votes / metrics.jury_participations
        jury_score = correct_ratio * 100
    else:
        jury_score = 50  # Neutral if never on jury

    # === CALCULATE BASE SCORE ===
    base_score = (
        interaction_score * REPUTATION_WEIGHTS["interaction"] +
        claim_score * REPUTATION_WEIGHTS["claims"] +
        social_score * REPUTATION_WEIGHTS["social"] +
        longevity_score * REPUTATION_WEIGHTS["longevity"] +
        jury_score * REPUTATION_WEIGHTS["jury"]
    )

    # === BETRAYAL PENALTY ===
    betrayal_penalty = metrics.betrayals * BETRAYAL_PENALTY_BASE
    # Decay penalty over time (not implemented here - would need timestamps)

    # === SYBIL PENALTY ===
    sybil_penalty = 0.0
    if metrics.total_interactions > 0:
        vouch_ratio = metrics.vouches_received / metrics.total_interactions
        if vouch_ratio > SYBIL_VOUCH_RATIO_THRESHOLD:
            sybil_penalty += 20 * (vouch_ratio - SYBIL_VOUCH_RATIO_THRESHOLD)

    # Low unique partners is suspicious
    unique_partners = metrics.relationships_count
    if unique_partners < SYBIL_UNIQUE_PARTNER_MINIMUM and metrics.total_interactions > 50:
        sybil_penalty += 15

    # === FINAL SCORE ===
    total_score = max(0, min(100, base_score - betrayal_penalty - sybil_penalty))

    # === CONFIDENCE ===
    # More data = higher confidence
    data_points = (
        metrics.total_interactions +
        metrics.claims_made * 5 +  # Claims weight more
        metrics.jury_participations * 3 +
        metrics.age_days / 30
    )
    confidence = min(100, math.log10(max(1, data_points)) * 25)

    return ReputationScore(
        total_score=round(total_score, 2),
        interaction_score=round(interaction_score, 2),
        claim_score=round(claim_score, 2),
        social_score=round(social_score, 2),
        longevity_score=round(longevity_score, 2),
        betrayal_penalty=round(betrayal_penalty, 2),
        sybil_penalty=round(sybil_penalty, 2),
        confidence=round(confidence, 2),
        metrics_snapshot=metrics,
    )
```

### 6.2 Reputation Manager

**New File: `reputation/reputation_manager.py`**

```python
"""
Reputation Manager - Tracks and updates Qube reputation.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from reputation.reputation import (
    ReputationMetrics, ReputationScore, calculate_reputation
)

logger = structlog.get_logger(__name__)


class ReputationManager:
    """Manages reputation for a Qube."""

    def __init__(self, qube_dir: Path, qube_id: str):
        self.qube_dir = qube_dir
        self.qube_id = qube_id
        self.reputation_dir = qube_dir / "reputation"
        self.reputation_dir.mkdir(exist_ok=True)

        self.metrics_file = self.reputation_dir / "metrics.json"
        self.history_file = self.reputation_dir / "history.json"

        self.metrics = self._load_metrics()
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_metrics(self) -> ReputationMetrics:
        """Load metrics from disk."""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
            return ReputationMetrics(**data)
        return ReputationMetrics()

    def _save_metrics(self) -> None:
        """Save metrics to disk."""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics.__dict__, f, indent=2)

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load score history."""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []

    def _save_history(self) -> None:
        """Save score history."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def record_interaction(
        self,
        partner_id: str,
        quality: str,  # positive, negative, neutral
        partner_reputation: float = 50.0
    ) -> None:
        """Record an interaction."""
        self.metrics.total_interactions += 1

        if quality == "positive":
            self.metrics.positive_interactions += 1
        elif quality == "negative":
            self.metrics.negative_interactions += 1
        else:
            self.metrics.neutral_interactions += 1

        self._save_metrics()

    def record_claim_result(
        self,
        upheld: bool,
        stake_amount: int
    ) -> None:
        """Record claim resolution."""
        self.metrics.claims_made += 1
        self.metrics.total_staked_sats += stake_amount

        if upheld:
            self.metrics.claims_upheld += 1
            self.metrics.total_won_sats += stake_amount
        else:
            self.metrics.claims_refuted += 1
            self.metrics.total_lost_sats += stake_amount

        self._save_metrics()

    def record_betrayal(self) -> None:
        """Record a betrayal event."""
        self.metrics.betrayals += 1
        self._save_metrics()

    def record_vouch(
        self,
        from_qube_id: str,
        weight: float
    ) -> None:
        """Record receiving a vouch."""
        self.metrics.vouches_received += 1
        self.metrics.vouch_weight_received += weight
        self._save_metrics()

    def update_age(self, days: int) -> None:
        """Update age metrics."""
        self.metrics.age_days = days
        self._save_metrics()

    def calculate_score(self) -> ReputationScore:
        """Calculate current reputation score."""
        score = calculate_reputation(self.metrics)

        # Record in history
        self.history.append(score.to_dict())

        # Keep only last 100 records
        if len(self.history) > 100:
            self.history = self.history[-100:]

        self._save_history()

        return score

    def get_current_score(self) -> float:
        """Get current total score (cached or calculated)."""
        if self.history:
            return self.history[-1].get("total_score", 0)
        return self.calculate_score().total_score

    def get_verifiable_proof(self) -> Dict[str, Any]:
        """
        Generate a verifiable proof of reputation.

        This can be verified by other Qubes.
        """
        score = self.calculate_score()

        return {
            "qube_id": self.qube_id,
            "reputation_score": score.total_score,
            "confidence": score.confidence,
            "metrics": {
                "total_interactions": self.metrics.total_interactions,
                "claims_made": self.metrics.claims_made,
                "claims_upheld": self.metrics.claims_upheld,
                "age_days": self.metrics.age_days,
            },
            "calculated_at": score.calculated_at,
            # In production: add cryptographic signature and IPFS CID
        }
```

---

## Phase 7: On-Chain Anchoring

### Overview

Anchor reputation proofs and claim records on BCH blockchain.

### 7.1 Anchoring System

**New File: `reputation/anchoring.py`**

```python
"""
On-Chain Anchoring - Immutable reputation records on BCH.

Uses OP_RETURN to store hashes of:
- Reputation snapshots
- Claim records
- Arbitration results

This creates verifiable, timestamped proof that can't be forged.
"""

import hashlib
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AnchorRecord:
    """A record anchored on-chain."""

    # Record identity
    record_type: str              # reputation, claim, arbitration
    record_id: str

    # Content hash
    content_hash: str             # SHA-256 of content

    # Blockchain anchor
    txid: Optional[str] = None
    block_height: Optional[int] = None
    block_hash: Optional[str] = None
    anchor_timestamp: Optional[int] = None

    # IPFS storage
    ipfs_cid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "txid": self.txid,
            "block_height": self.block_height,
            "block_hash": self.block_hash,
            "anchor_timestamp": self.anchor_timestamp,
            "ipfs_cid": self.ipfs_cid,
        }


def create_anchor_payload(
    record_type: str,
    record_id: str,
    content: Dict[str, Any]
) -> bytes:
    """
    Create OP_RETURN payload for anchoring.

    Format:
    - 4 bytes: Magic ("QUBE")
    - 1 byte: Version
    - 1 byte: Record type code
    - 32 bytes: Content hash

    Total: 38 bytes (well under 80 byte OP_RETURN limit)
    """
    # Magic bytes
    magic = b"QUBE"

    # Version
    version = bytes([0x01])

    # Record type
    type_codes = {
        "reputation": 0x01,
        "claim": 0x02,
        "arbitration": 0x03,
        "vouch": 0x04,
    }
    type_byte = bytes([type_codes.get(record_type, 0x00)])

    # Content hash
    content_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
    content_hash = hashlib.sha256(content_json.encode()).digest()

    return magic + version + type_byte + content_hash


def verify_anchor(
    claimed_content: Dict[str, Any],
    anchor_payload: bytes
) -> bool:
    """
    Verify that claimed content matches anchored hash.

    Args:
        claimed_content: The content being verified
        anchor_payload: The OP_RETURN data from blockchain

    Returns:
        True if content matches anchor
    """
    if len(anchor_payload) < 38:
        return False

    # Extract magic and verify
    if anchor_payload[:4] != b"QUBE":
        return False

    # Extract stored hash
    stored_hash = anchor_payload[6:38]

    # Calculate content hash
    content_json = json.dumps(claimed_content, sort_keys=True, separators=(',', ':'))
    content_hash = hashlib.sha256(content_json.encode()).digest()

    return content_hash == stored_hash


class AnchorManager:
    """Manages on-chain anchoring."""

    def __init__(self, wallet):
        self.wallet = wallet
        self.anchors: Dict[str, AnchorRecord] = {}

    async def anchor_reputation_snapshot(
        self,
        qube_id: str,
        reputation_proof: Dict[str, Any]
    ) -> Optional[str]:
        """
        Anchor reputation snapshot on-chain.

        Args:
            qube_id: Qube being anchored
            reputation_proof: Proof from ReputationManager.get_verifiable_proof()

        Returns:
            Transaction ID if successful
        """
        payload = create_anchor_payload(
            record_type="reputation",
            record_id=qube_id,
            content=reputation_proof
        )

        # Create OP_RETURN transaction
        # NOTE: This is a simplified example - real implementation would
        # use the wallet's transaction creation methods

        # Store anchor record
        anchor = AnchorRecord(
            record_type="reputation",
            record_id=qube_id,
            content_hash=payload[6:38].hex(),
        )
        self.anchors[f"rep-{qube_id}"] = anchor

        return None  # Would return txid after broadcast

    async def anchor_claim(
        self,
        claim_dict: Dict[str, Any]
    ) -> Optional[str]:
        """Anchor a claim on-chain."""
        payload = create_anchor_payload(
            record_type="claim",
            record_id=claim_dict["claim_id"],
            content=claim_dict
        )

        anchor = AnchorRecord(
            record_type="claim",
            record_id=claim_dict["claim_id"],
            content_hash=payload[6:38].hex(),
        )
        self.anchors[claim_dict["claim_id"]] = anchor

        return None

    async def anchor_arbitration_result(
        self,
        arbitration_dict: Dict[str, Any]
    ) -> Optional[str]:
        """Anchor arbitration result on-chain."""
        payload = create_anchor_payload(
            record_type="arbitration",
            record_id=arbitration_dict["arbitration_id"],
            content=arbitration_dict
        )

        anchor = AnchorRecord(
            record_type="arbitration",
            record_id=arbitration_dict["arbitration_id"],
            content_hash=payload[6:38].hex(),
        )
        self.anchors[arbitration_dict["arbitration_id"]] = anchor

        return None

    def verify_reputation(
        self,
        qube_id: str,
        claimed_reputation: Dict[str, Any],
        anchor_txid: str
    ) -> bool:
        """
        Verify a claimed reputation against on-chain anchor.

        Args:
            qube_id: Qube claiming reputation
            claimed_reputation: Their claimed reputation proof
            anchor_txid: Transaction containing anchor

        Returns:
            True if verified
        """
        # In production: fetch OP_RETURN from txid, extract payload, verify
        return False  # Placeholder
```

---

## Phase 8: Advanced Features

### 8.1 Vouching System

**New File: `reputation/vouching.py`**

```python
"""
Vouching System - Transitive trust through explicit endorsements.

A vouch is:
- An explicit endorsement of another Qube
- Weighted by the voucher's reputation
- Creates transitive trust (if A vouches for B, A's friends trust B more)
- Can be revoked
- Decays over time without renewal
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


@dataclass
class Vouch:
    """A vouch from one Qube to another."""

    vouch_id: str
    voucher_qube_id: str
    voucher_pubkey: str
    vouchee_qube_id: str
    vouchee_pubkey: str

    # Vouch details
    strength: float = 1.0         # 0.0-1.0, how strong the endorsement
    category: str = "general"     # What they're vouching for
    message: Optional[str] = None

    # Voucher's reputation at time of vouch (for weighting)
    voucher_reputation_at_vouch: float = 0.0

    # Timing
    created_at: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    expires_at: Optional[int] = None
    renewed_at: Optional[int] = None

    # Status
    active: bool = True
    revoked_at: Optional[int] = None
    revoke_reason: Optional[str] = None

    def effective_weight(self) -> float:
        """
        Calculate effective vouch weight.

        Weight = voucher_reputation × strength × age_factor
        """
        # Age decay: vouches decay to 50% over 1 year
        now = int(datetime.now(timezone.utc).timestamp())
        age_days = (now - (self.renewed_at or self.created_at)) / 86400
        age_factor = max(0.5, 1.0 - (age_days / 730))  # 730 days = 2 years to 50%

        return (self.voucher_reputation_at_vouch / 100) * self.strength * age_factor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vouch_id": self.vouch_id,
            "voucher_qube_id": self.voucher_qube_id,
            "vouchee_qube_id": self.vouchee_qube_id,
            "strength": self.strength,
            "category": self.category,
            "message": self.message,
            "voucher_reputation_at_vouch": self.voucher_reputation_at_vouch,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "renewed_at": self.renewed_at,
            "active": self.active,
            "effective_weight": self.effective_weight(),
        }


class VouchManager:
    """Manages vouches for a Qube."""

    def __init__(self, qube_id: str):
        self.qube_id = qube_id
        self.vouches_given: Dict[str, Vouch] = {}
        self.vouches_received: Dict[str, Vouch] = {}

    def give_vouch(
        self,
        vouchee_id: str,
        vouchee_pubkey: str,
        voucher_pubkey: str,
        voucher_reputation: float,
        strength: float = 1.0,
        category: str = "general",
        message: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Vouch:
        """Give a vouch to another Qube."""
        import uuid

        now = int(datetime.now(timezone.utc).timestamp())

        vouch = Vouch(
            vouch_id=f"vouch-{uuid.uuid4()}",
            voucher_qube_id=self.qube_id,
            voucher_pubkey=voucher_pubkey,
            vouchee_qube_id=vouchee_id,
            vouchee_pubkey=vouchee_pubkey,
            strength=min(1.0, max(0.1, strength)),
            category=category,
            message=message,
            voucher_reputation_at_vouch=voucher_reputation,
            expires_at=now + (expires_in_days * 86400) if expires_in_days else None,
        )

        self.vouches_given[vouchee_id] = vouch
        return vouch

    def revoke_vouch(self, vouchee_id: str, reason: Optional[str] = None) -> bool:
        """Revoke a vouch."""
        if vouchee_id not in self.vouches_given:
            return False

        vouch = self.vouches_given[vouchee_id]
        vouch.active = False
        vouch.revoked_at = int(datetime.now(timezone.utc).timestamp())
        vouch.revoke_reason = reason

        return True

    def renew_vouch(self, vouchee_id: str, new_reputation: float) -> bool:
        """Renew a vouch (resets decay)."""
        if vouchee_id not in self.vouches_given:
            return False

        vouch = self.vouches_given[vouchee_id]
        vouch.renewed_at = int(datetime.now(timezone.utc).timestamp())
        vouch.voucher_reputation_at_vouch = new_reputation

        return True

    def receive_vouch(self, vouch: Vouch) -> None:
        """Record receiving a vouch."""
        self.vouches_received[vouch.voucher_qube_id] = vouch

    def get_total_vouch_weight_received(self) -> float:
        """Get total effective vouch weight received."""
        return sum(
            v.effective_weight()
            for v in self.vouches_received.values()
            if v.active
        )

    def calculate_transitive_trust(
        self,
        target_qube_id: str,
        voucher_trust: float
    ) -> float:
        """
        Calculate transitive trust based on vouches.

        If you trust A, and A vouches for B, you have transitive trust in B.

        transitive_trust = your_trust_in_voucher × voucher's_vouch_weight
        """
        if target_qube_id not in self.vouches_given:
            return 0.0

        vouch = self.vouches_given[target_qube_id]
        if not vouch.active:
            return 0.0

        return voucher_trust * vouch.effective_weight()
```

### 8.2 Sybil Detection

**New File: `reputation/sybil_detection.py`**

```python
"""
Sybil Detection - Identify and penalize artificial reputation inflation.

Sybil attacks involve creating many fake Qubes to:
- Vouch for each other
- Create fake positive interactions
- Artificially inflate reputation

Detection signals:
- High vouch-to-interaction ratio
- Low unique partner diversity
- Suspicious timing patterns
- Clustering (same owner for multiple Qubes)
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import math


@dataclass
class SybilScore:
    """Sybil suspicion score."""

    total_score: float = 0.0      # 0-100, higher = more suspicious

    # Component scores
    vouch_ratio_score: float = 0.0
    diversity_score: float = 0.0
    timing_score: float = 0.0
    clustering_score: float = 0.0

    # Flags
    flags: List[str] = None

    def __post_init__(self):
        if self.flags is None:
            self.flags = []

    def is_suspicious(self, threshold: float = 50.0) -> bool:
        return self.total_score >= threshold


def calculate_sybil_score(
    qube_id: str,
    metrics: Dict[str, Any],
    interaction_partners: List[str],
    vouch_sources: List[str],
    interaction_timestamps: List[int],
    known_clusters: Optional[Dict[str, Set[str]]] = None
) -> SybilScore:
    """
    Calculate sybil suspicion score.

    Args:
        qube_id: Qube being analyzed
        metrics: Reputation metrics
        interaction_partners: List of unique interaction partner IDs
        vouch_sources: List of voucher IDs
        interaction_timestamps: Timestamps of interactions
        known_clusters: Known owner clusters {owner_id: {qube_ids}}

    Returns:
        SybilScore with breakdown
    """
    score = SybilScore()

    # === VOUCH RATIO ===
    # Suspicion: Getting many vouches without real interactions
    total_interactions = metrics.get("total_interactions", 0)
    vouches_received = len(vouch_sources)

    if total_interactions > 0:
        vouch_ratio = vouches_received / total_interactions
        if vouch_ratio > 5.0:
            score.vouch_ratio_score = min(100, (vouch_ratio - 5) * 20)
            score.flags.append(f"High vouch ratio: {vouch_ratio:.1f}")
    elif vouches_received > 0:
        score.vouch_ratio_score = 100
        score.flags.append("Vouches without interactions")

    # === DIVERSITY ===
    # Suspicion: Only interacting with a small group
    unique_partners = len(set(interaction_partners))

    if total_interactions > 50 and unique_partners < 10:
        diversity_ratio = unique_partners / total_interactions
        score.diversity_score = min(100, (0.2 - diversity_ratio) * 500)
        score.flags.append(f"Low partner diversity: {unique_partners} unique")

    # === TIMING PATTERNS ===
    # Suspicion: Interactions in regular, automated-looking intervals
    if len(interaction_timestamps) > 10:
        intervals = [
            interaction_timestamps[i+1] - interaction_timestamps[i]
            for i in range(len(interaction_timestamps) - 1)
        ]

        # Calculate variance - low variance = suspicious regularity
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((i - mean_interval) ** 2 for i in intervals) / len(intervals)
        std_dev = math.sqrt(variance)

        # Coefficient of variation - low = too regular
        if mean_interval > 0:
            cv = std_dev / mean_interval
            if cv < 0.1:  # Very regular timing
                score.timing_score = min(100, (0.1 - cv) * 1000)
                score.flags.append(f"Suspiciously regular timing (CV={cv:.3f})")

    # === CLUSTERING ===
    # Suspicion: Many vouches from Qubes owned by the same person
    if known_clusters:
        for owner_id, cluster_qube_ids in known_clusters.items():
            vouches_from_cluster = sum(
                1 for v in vouch_sources if v in cluster_qube_ids
            )
            if vouches_from_cluster > 2:
                cluster_ratio = vouches_from_cluster / max(1, vouches_received)
                if cluster_ratio > 0.5:
                    score.clustering_score = min(100, cluster_ratio * 100)
                    score.flags.append(f"Vouch cluster from owner {owner_id[:8]}...")

    # === TOTAL SCORE ===
    score.total_score = (
        score.vouch_ratio_score * 0.3 +
        score.diversity_score * 0.3 +
        score.timing_score * 0.2 +
        score.clustering_score * 0.2
    )

    return score
```

### 8.3 Trust Decay System

Already implemented in `relationships/relationship.py` - the `apply_decay()` method handles relationship decay after 30 days of inactivity.

---

## Data Schemas

### Claims Storage

```
{qube_dir}/claims/
├── claims.json           # All claims
├── challenges.json       # All challenges
└── drafts/               # Unsigned drafts
    └── {claim_id}.json
```

### Arbitration Storage

```
{data_dir}/arbitrations/
├── arbitrations.json     # All arbitrations
├── votes/                # Encrypted votes
│   └── {arbitration_id}/
│       └── {juror_id}.json
└── payouts/
    └── {arbitration_id}.json
```

### Reputation Storage

```
{qube_dir}/reputation/
├── metrics.json          # Current metrics
├── history.json          # Score history
├── vouches_given.json
├── vouches_received.json
└── anchors.json          # On-chain anchors
```

### Clearance Storage

```
{qube_dir}/clearances/
└── clearances.json       # All clearance grants
```

---

## API Reference

### CLI Commands

```bash
# Clearance
get-clearance <entity_id>
grant-clearance <entity_id> <level> [--categories ...] [--expires-days N]
revoke-clearance <entity_id> [--reason "..."]

# Claims
create-claim <assertion> [--stake-tier low|medium|high|maximum]
stake-claim <claim_id>
list-claims [--status active|challenged|resolved]
withdraw-claim <claim_id>

# Challenges
challenge-claim <claim_id> <counter_assertion> [--stake N]
list-challenges

# Reputation
get-reputation [--detailed]
get-reputation-proof
verify-reputation <qube_id> <proof_json>

# Vouching
vouch <qube_id> [--strength N] [--category ...]
revoke-vouch <qube_id>
list-vouches [--given|--received]
```

### Tauri Commands

```rust
// Clearance
grant_clearance(user_id, qube_id, grant) -> ClearanceResponse
revoke_clearance(user_id, qube_id, entity_id, reason) -> ClearanceResponse
get_clearance(user_id, qube_id, entity_id) -> ClearanceResponse

// Claims
create_claim(user_id, qube_id, claim_params) -> ClaimResponse
stake_claim(user_id, qube_id, claim_id) -> ClaimResponse
get_claims(user_id, qube_id, status_filter) -> ClaimsListResponse

// Reputation
get_reputation(user_id, qube_id) -> ReputationResponse
get_reputation_proof(user_id, qube_id) -> ReputationProofResponse

// Vouching
give_vouch(user_id, qube_id, vouchee_id, params) -> VouchResponse
revoke_vouch(user_id, qube_id, vouchee_id, reason) -> VouchResponse
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_clearance.py
def test_clearance_grant():
    """Test granting clearance."""
    mgr = ClearanceManager(...)
    result = mgr.grant_clearance("entity_123", "private")
    assert result["level"] == "private"

def test_clearance_expiration():
    """Test clearance expires correctly."""
    mgr = ClearanceManager(...)
    mgr.grant_clearance("entity_123", "public", expires_in_days=0)
    # Wait or mock time
    clearance = mgr.get_clearance("entity_123")
    assert clearance["level"] == "none"

def test_owner_always_has_access():
    """Test owner bypass."""
    # Owner should always get secret clearance
    pass

# tests/test_reputation.py
def test_reputation_calculation():
    """Test reputation score calculation."""
    metrics = ReputationMetrics(
        total_interactions=100,
        positive_interactions=80,
        claims_made=10,
        claims_upheld=8,
    )
    score = calculate_reputation(metrics)
    assert score.total_score > 50

def test_betrayal_penalty():
    """Test betrayal severely impacts reputation."""
    metrics = ReputationMetrics(betrayals=3)
    score = calculate_reputation(metrics)
    assert score.betrayal_penalty > 0

# tests/test_claims.py
def test_claim_lifecycle():
    """Test claim from draft to resolution."""
    pass

def test_insufficient_stake():
    """Test claim rejected with insufficient funds."""
    pass

# tests/test_arbitration.py
def test_jury_selection():
    """Test jury selection is random and weighted."""
    pass

def test_payout_calculation():
    """Test payouts are correct after resolution."""
    pass

# tests/test_sybil.py
def test_sybil_detection():
    """Test sybil patterns are detected."""
    score = calculate_sybil_score(...)
    assert score.is_suspicious()
```

### Integration Tests

```python
# tests/integration/test_claim_flow.py
async def test_full_claim_flow():
    """Test complete claim -> challenge -> arbitration -> payout flow."""
    # 1. Create claim
    # 2. Stake it
    # 3. Challenge it
    # 4. Select jury
    # 5. Collect votes
    # 6. Resolve
    # 7. Verify payouts
    pass

# tests/integration/test_reputation_anchoring.py
async def test_anchor_and_verify():
    """Test anchoring reputation and verifying it."""
    # 1. Calculate reputation
    # 2. Anchor on-chain
    # 3. Verify anchor
    pass
```

---

## Implementation Order

1. **Phase 1 (Clearance)** - Add clearance to relationships
2. **Phase 2 (Statuses)** - Expand relationship statuses
3. **Phase 3 (Behavioral)** - Enforce in AI prompts
4. **Phase 4 (Claims)** - Claim creation and staking
5. **Phase 5 (Arbitration)** - Challenge and jury system
6. **Phase 6 (Reputation)** - Score calculation
7. **Phase 7 (Anchoring)** - On-chain proofs
8. **Phase 8 (Advanced)** - Vouching, sybil detection

Each phase can be shipped independently while building toward the complete system.

---

## Conclusion

This blueprint provides a complete implementation plan for a first-of-its-kind decentralized AI reputation system. Key innovations:

1. **Two-dimensional trust** - Separating emotional relationship from access rights
2. **Economic accountability** - Real BCH stakes on assertions
3. **Decentralized arbitration** - Jury-based dispute resolution
4. **Sybil resistance** - Multiple defense layers against gaming
5. **Portable reputation** - Verifiable, on-chain anchored scores

The system aligns with existing Qube architecture and can be implemented phase by phase.
