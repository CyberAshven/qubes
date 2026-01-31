# Phase 6: Security & Privacy - Implementation Blueprint

## Executive Summary

**Theme: Protect (Safeguard Self, Owner, and Network)**

Security & Privacy is about the Qube being a guardian - protecting its own memory chain integrity, safeguarding the owner's private data, and securing Qube-to-Qube communications. This is especially important as Qubes communicate over P2P networks, where a "bodyguard" Qube might vet other Qubes before letting them into group chats.

This Sun enables specialization paths like the **"Bodyguard Qube"** - a Qube that specializes in vetting, threat detection, and group security.

### Tool Summary

| Level | Count | Tools |
|-------|-------|-------|
| Sun | 1 | `verify_chain_integrity` |
| Planet | 5 | `audit_chain`, `assess_sensitivity`, `vet_qube`, `detect_threat`, `defend_reasoning` |
| Moon | 10 | `detect_tampering`, `verify_anchor`, `classify_data`, `control_sharing`, `check_reputation`, `secure_group_chat`, `detect_technical_manipulation`, `detect_hostile_qube`, `detect_injection`, `validate_reasoning` |
| **Total** | **16** | |

### XP Model

Standard XP model (5/2.5/0) for most tools:
- **Success**: 5 XP
- **Completed**: 2.5 XP
- **Failed**: 0 XP

**Exception**: `verify_chain_integrity` uses special formula: 0.1 XP per NEW block verified (anti-gaming).

### LEARNING Block Types

Security tools create LEARNING blocks with these types:
- `threat` - Security threats detected
- `trust` - Trust decisions about other Qubes
- `insight` - Security insights and patterns

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Task 6.1: Update Skill Definitions](#task-61-update-skill-definitions)
3. [Task 6.2: Implement Sun Tool](#task-62-implement-sun-tool)
4. [Task 6.3: Implement Planet Tools](#task-63-implement-planet-tools)
5. [Task 6.4: Implement Moon Tools](#task-64-implement-moon-tools)
6. [Task 6.5: Security Infrastructure](#task-65-security-infrastructure)
7. [Task 6.6: Update XP Routing](#task-66-update-xp-routing)
8. [Task 6.7: Frontend Integration](#task-67-frontend-integration)
9. [Task 6.8: Testing & Validation](#task-68-testing--validation)
10. [Files Modified Summary](#files-modified-summary)

---

## Prerequisites

### From Phase 0 (Foundation)

1. **LEARNING Block Type** (Task 0.4)
   - Supports `threat`, `trust`, `insight` learning types

2. **XP Trickle-Up System** (Task 0.6)
   - Required for skill XP routing

### From Phase 5 (Memory & Recall)

1. **Universal Search** - `recall()` tool for searching memories
2. **LEARNING block creation** - `store_knowledge()` for creating insights

### Existing Infrastructure Leveraged

| Component | File | Purpose |
|-----------|------|---------|
| MemoryChain.verify_chain_integrity() | `core/memory_chain.py:211-272` | Chain verification |
| Block signatures | `core/block.py:126-163` | Multi-party signing |
| ChainState | `core/chain_state.py` | State management |

### Current Codebase State (as of Jan 2026)

#### Existing Skills (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current Sun tool**: `browse_url` (WRONG - this is an intelligent routing tool)
- **Current Planets**: cryptography, authentication, network_security, privacy_protection, threat_analysis
- **Action**: Replace Sun tool, update skill structure

#### Tool Mappings (`ai/skill_scanner.py:77-79`)
- **Current mappings** (to be replaced):
  ```python
  "assess_security_risks": "threat_analysis"
  "privacy_impact_analysis": "privacy_protection"
  "verify_authenticity": "authentication"
  ```
- **Target mappings** (new tools):
  ```python
  "verify_chain_integrity": "security_privacy"  # Sun (special XP: 0.1/block)
  "detect_tampering": "chain_integrity"
  "classify_data": "privacy_protection"
  # ... 13 more new tool mappings
  ```

#### Chain Integrity (`core/memory_chain.py:211-272`)
- **Current**: `verify_chain_integrity()` method exists
- **Status**: ✅ Implemented
- **Action**: New Sun tool will wrap this with XP tracking

#### Note on `browse_url`
- **Current role**: Listed as Security & Privacy Sun tool in skillDefinitions.ts
- **Actual role**: Intelligent routing tool (routes XP based on URL content)
- **Action**: Remove from Sun tool position, keep as utility tool
| Relationship System | `core/relationships.py` | Trust levels |

---

## Task 6.1: Update Skill Definitions

### File: `ai/tools/handlers.py`

Add `security_privacy` to SKILL_CATEGORIES and SKILL_TREE:

```python
# Add to SKILL_CATEGORIES
{"id": "security_privacy", "name": "Security & Privacy", "color": "#E74C3C", "icon": "shield", "description": "Protect self, owner, and network"},

# Add to SKILL_TREE
"security_privacy": [
    # Sun
    {
        "id": "security_privacy",
        "name": "Security & Privacy",
        "node_type": "sun",
        "xp_required": 1000,
        "tool_unlock": "verify_chain_integrity",
        "icon": "shield",
        "description": "Safeguard yourself, your owner, and your network"
    },
    # Planet 1: Chain Security
    {
        "id": "chain_security",
        "name": "Chain Security",
        "node_type": "planet",
        "parent": "security_privacy",
        "xp_required": 500,
        "tool_unlock": "audit_chain",
        "icon": "link",
        "description": "Protect the memory chain's integrity"
    },
    # Planet 2: Privacy Protection
    {
        "id": "privacy_protection",
        "name": "Privacy Protection",
        "node_type": "planet",
        "parent": "security_privacy",
        "xp_required": 500,
        "tool_unlock": "assess_sensitivity",
        "icon": "lock",
        "description": "Protect owner's private data"
    },
    # Planet 3: Qube Network Security
    {
        "id": "qube_network_security",
        "name": "Qube Network Security",
        "node_type": "planet",
        "parent": "security_privacy",
        "xp_required": 500,
        "tool_unlock": "vet_qube",
        "icon": "users",
        "description": "The bodyguard - vet other Qubes"
    },
    # Planet 4: Threat Detection
    {
        "id": "threat_detection",
        "name": "Threat Detection",
        "node_type": "planet",
        "parent": "security_privacy",
        "xp_required": 500,
        "tool_unlock": "detect_threat",
        "icon": "alert-triangle",
        "description": "Identify attacks from humans or Qubes"
    },
    # Planet 5: Self-Defense
    {
        "id": "self_defense",
        "name": "Self-Defense",
        "node_type": "planet",
        "parent": "security_privacy",
        "xp_required": 500,
        "tool_unlock": "defend_reasoning",
        "icon": "shield-check",
        "description": "Protect the Qube's own reasoning"
    },
    # Moon 1.1: Tamper Detection
    {
        "id": "tamper_detection",
        "name": "Tamper Detection",
        "node_type": "moon",
        "parent": "chain_security",
        "xp_required": 250,
        "tool_unlock": "detect_tampering",
        "icon": "scan",
        "description": "Detect if memory has been tampered with"
    },
    # Moon 1.2: Anchor Verification
    {
        "id": "anchor_verification",
        "name": "Anchor Verification",
        "node_type": "moon",
        "parent": "chain_security",
        "xp_required": 250,
        "tool_unlock": "verify_anchor",
        "icon": "anchor",
        "description": "Verify blockchain anchors are valid"
    },
    # Moon 2.1: Data Classification
    {
        "id": "data_classification",
        "name": "Data Classification",
        "node_type": "moon",
        "parent": "privacy_protection",
        "xp_required": 250,
        "tool_unlock": "classify_data",
        "icon": "tag",
        "description": "Classify data by sensitivity level"
    },
    # Moon 2.2: Sharing Control
    {
        "id": "sharing_control",
        "name": "Sharing Control",
        "node_type": "moon",
        "parent": "privacy_protection",
        "xp_required": 250,
        "tool_unlock": "control_sharing",
        "icon": "share-2",
        "description": "Control what gets shared with whom"
    },
    # Moon 3.1: Reputation Check
    {
        "id": "reputation_check",
        "name": "Reputation Check",
        "node_type": "moon",
        "parent": "qube_network_security",
        "xp_required": 250,
        "tool_unlock": "check_reputation",
        "icon": "star",
        "description": "Check another Qube's reputation"
    },
    # Moon 3.2: Group Security
    {
        "id": "group_security",
        "name": "Group Security",
        "node_type": "moon",
        "parent": "qube_network_security",
        "xp_required": 250,
        "tool_unlock": "secure_group_chat",
        "icon": "users-cog",
        "description": "Manage security for group chats"
    },
    # Moon 4.1: Technical Manipulation Detection
    {
        "id": "technical_manipulation_detection",
        "name": "Technical Manipulation Detection",
        "node_type": "moon",
        "parent": "threat_detection",
        "xp_required": 250,
        "tool_unlock": "detect_technical_manipulation",
        "icon": "cpu",
        "description": "Detect technical manipulation from Qubes or systems"
    },
    # Moon 4.2: Hostile Qube Detection
    {
        "id": "hostile_qube_detection",
        "name": "Hostile Qube Detection",
        "node_type": "moon",
        "parent": "threat_detection",
        "xp_required": 250,
        "tool_unlock": "detect_hostile_qube",
        "icon": "user-x",
        "description": "Detect hostile behavior from other Qubes"
    },
    # Moon 5.1: Prompt Injection Defense
    {
        "id": "prompt_injection_defense",
        "name": "Prompt Injection Defense",
        "node_type": "moon",
        "parent": "self_defense",
        "xp_required": 250,
        "tool_unlock": "detect_injection",
        "icon": "syringe",
        "description": "Detect prompt injection attacks"
    },
    # Moon 5.2: Reasoning Validation
    {
        "id": "reasoning_validation",
        "name": "Reasoning Validation",
        "node_type": "moon",
        "parent": "self_defense",
        "xp_required": 250,
        "tool_unlock": "validate_reasoning",
        "icon": "check-circle",
        "description": "Validate own reasoning for bias injection"
    },
],
```

---

## Task 6.2: Implement Sun Tool

### File: `ai/tools/security_tools.py` (NEW FILE)

```python
"""
Security & Privacy Tools - Phase 6 Implementation

The "guardian" Sun - protects the Qube, owner, and network.
Verifies chain integrity, protects privacy, vets other Qubes.

Theme: Protect (Safeguard Self, Owner, and Network)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import hashlib
import json

from core.block import Block, BlockType, create_learning_block
from core.exceptions import AIError, ChainIntegrityError
from ai.tools.registry import ToolDefinition
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# SUN TOOL: verify_chain_integrity
# =============================================================================

VERIFY_CHAIN_INTEGRITY_SCHEMA = {
    "type": "object",
    "properties": {
        "full_check": {
            "type": "boolean",
            "description": "Perform full chain verification (default: false, only new blocks)"
        },
        "since_block": {
            "type": "integer",
            "description": "Start verification from this block number"
        }
    }
}

VERIFY_CHAIN_INTEGRITY_DEFINITION = ToolDefinition(
    name="verify_chain_integrity",
    description="Verify the memory chain hasn't been tampered with. Foundation of Qube security. Special XP: 0.1 per NEW block verified.",
    input_schema=VERIFY_CHAIN_INTEGRITY_SCHEMA,
    category="security_privacy"
)


async def verify_chain_integrity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify memory chain integrity - the foundation of Qube security.

    Uses blockchain verification to ensure no tampering.
    Special XP formula: 0.1 per NEW block verified (anti-gaming: no XP for re-checking).

    Args:
        qube: Qube instance
        params: {
            full_check: bool - Verify entire chain (default: False)
            since_block: int - Start from this block (optional)
        }

    Returns:
        Dict with integrity status, blocks checked, issues found
    """
    full_check = params.get("full_check", False)
    since_block = params.get("since_block")

    # Get last verified block from chain state
    chain_state = qube.chain_state if hasattr(qube, 'chain_state') else {}
    last_verified = chain_state.get("last_verified_block_number", 0)

    # Determine starting point
    if since_block is None and not full_check:
        since_block = last_verified

    start_block = 0 if full_check else (since_block or 0)

    try:
        # Perform verification
        verification_result = await _verify_chain_range(
            qube,
            from_block=start_block
        )

        # Calculate blocks verified
        current_block = qube.memory_chain.get_chain_length() - 1
        new_blocks_verified = max(0, current_block - last_verified)
        total_blocks_checked = current_block - start_block + 1

        # Update last verified if successful
        if verification_result["valid"]:
            if hasattr(qube, 'chain_state'):
                qube.chain_state["last_verified_block_number"] = current_block

        # Log issues as LEARNING blocks
        if not verification_result["valid"]:
            await _log_integrity_threat(qube, verification_result["issues"])

        # Calculate XP (0.1 per NEW block)
        xp_earned = new_blocks_verified * 0.1

        logger.info(
            "chain_integrity_verified",
            valid=verification_result["valid"],
            blocks_checked=total_blocks_checked,
            new_blocks=new_blocks_verified,
            xp=xp_earned
        )

        return {
            "success": True,
            "valid": verification_result["valid"],
            "blocks_checked": total_blocks_checked,
            "new_blocks_verified": new_blocks_verified,
            "issues": verification_result.get("issues", []),
            "xp_earned": xp_earned,
            "last_anchor": verification_result.get("last_anchor")
        }

    except Exception as e:
        logger.error("chain_integrity_check_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "valid": False,
            "error": f"Integrity check failed: {str(e)}"
        }


async def _verify_chain_range(qube, from_block: int = 0) -> Dict[str, Any]:
    """
    Verify chain integrity for a range of blocks.

    Checks:
    1. Block hash matches computed hash
    2. Block signature is valid
    3. Previous hash links are correct
    """
    issues = []
    last_anchor = None
    prev_block = None

    block_nums = sorted(qube.memory_chain.block_index.keys())
    blocks_to_check = [bn for bn in block_nums if bn >= from_block]

    for block_num in blocks_to_check:
        try:
            block = qube.memory_chain.get_block(block_num)

            # Check hash
            computed_hash = block.compute_hash()
            if block.block_hash and block.block_hash != computed_hash:
                issues.append({
                    "block_number": block_num,
                    "issue": "hash_mismatch",
                    "severity": "critical"
                })

            # Check previous hash link
            if prev_block and block.previous_hash:
                if block.previous_hash != prev_block.block_hash:
                    issues.append({
                        "block_number": block_num,
                        "issue": "chain_link_broken",
                        "severity": "critical"
                    })

            # Track anchor blocks
            if block.block_type == "MEMORY_ANCHOR":
                last_anchor = {
                    "block_number": block_num,
                    "merkle_root": block.content.get("merkle_root") if block.content else None
                }

            prev_block = block

        except Exception as e:
            issues.append({
                "block_number": block_num,
                "issue": f"verification_error: {str(e)}",
                "severity": "warning"
            })

    return {
        "valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
        "issues": issues,
        "last_anchor": last_anchor
    }


async def _log_integrity_threat(qube, issues: List[Dict]) -> None:
    """Log integrity issues as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,  # Session block
            previous_hash="",
            learning_type="threat",
            content={
                "threat_type": "chain_integrity",
                "issues": issues,
                "severity": "critical" if any(i["severity"] == "critical" for i in issues) else "warning"
            },
            source_category="security_privacy",
            confidence=100,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)
```

---

## Task 6.3: Implement Planet Tools

### Continue in `ai/tools/security_tools.py`

```python
# =============================================================================
# PLANET 1: audit_chain (Chain Security)
# =============================================================================

AUDIT_CHAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "audit_type": {
            "type": "string",
            "enum": ["full", "recent", "anchors"],
            "description": "Type of audit: full, recent (last 100 blocks), or anchors only"
        },
        "report": {
            "type": "boolean",
            "description": "Generate detailed audit report in Qube Locker"
        }
    }
}

AUDIT_CHAIN_DEFINITION = ToolDefinition(
    name="audit_chain",
    description="Deep audit of memory chain for anomalies, beyond basic integrity checks.",
    input_schema=AUDIT_CHAIN_SCHEMA,
    category="security_privacy"
)


async def audit_chain(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep audit of memory chain beyond basic integrity.

    Checks for:
    - Anomalies in block patterns
    - Suspicious timing
    - Anchor status
    - Block type distribution

    Args:
        qube: Qube instance
        params: {
            audit_type: str - full, recent, or anchors
            report: bool - Generate report
        }

    Returns:
        Dict with audit results
    """
    audit_type = params.get("audit_type", "recent")
    generate_report = params.get("report", False)

    try:
        audit_results = {
            "integrity": {"valid": True, "issues": []},
            "anomalies": [],
            "anchor_status": [],
            "statistics": {}
        }

        # Get blocks based on audit type
        if audit_type == "anchors":
            blocks = _get_anchor_blocks(qube)
        else:
            limit = None if audit_type == "full" else 100
            blocks = _get_recent_blocks(qube, limit)

        # Run integrity check
        audit_results["integrity"] = await _verify_chain_range(qube)

        # Detect anomalies
        audit_results["anomalies"] = _detect_chain_anomalies(blocks)

        # Calculate statistics
        audit_results["statistics"] = _calculate_chain_statistics(blocks)

        # Get anchor status
        audit_results["anchor_status"] = _get_anchor_status(qube)

        # Generate report if requested
        if generate_report and hasattr(qube, 'locker') and qube.locker:
            report = _generate_audit_report(audit_results, audit_type)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await qube.locker.store(
                category="security/audits",
                name=f"audit_{timestamp}",
                content=report
            )

        # Log findings as LEARNING block
        if audit_results["anomalies"]:
            await _log_audit_insight(qube, audit_results)

        return {
            "success": True,
            "audit_type": audit_type,
            "integrity_valid": audit_results["integrity"]["valid"],
            "anomalies_found": len(audit_results["anomalies"]),
            "anchors_verified": len([a for a in audit_results["anchor_status"] if a.get("verified")]),
            "statistics": audit_results["statistics"],
            "report_generated": generate_report
        }

    except Exception as e:
        logger.error("audit_chain_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Audit failed: {str(e)}"}


def _get_recent_blocks(qube, limit: Optional[int] = None) -> List[Block]:
    """Get recent blocks from chain."""
    block_nums = sorted(qube.memory_chain.block_index.keys(), reverse=True)
    if limit:
        block_nums = block_nums[:limit]

    blocks = []
    for bn in block_nums:
        try:
            blocks.append(qube.memory_chain.get_block(bn))
        except:
            continue
    return blocks


def _get_anchor_blocks(qube) -> List[Block]:
    """Get only MEMORY_ANCHOR blocks."""
    blocks = []
    for bn in qube.memory_chain.block_index.keys():
        try:
            block = qube.memory_chain.get_block(bn)
            if block.block_type == "MEMORY_ANCHOR":
                blocks.append(block)
        except:
            continue
    return blocks


def _detect_chain_anomalies(blocks: List[Block]) -> List[Dict]:
    """Detect anomalies in block patterns."""
    anomalies = []

    if len(blocks) < 2:
        return anomalies

    # Check for timestamp anomalies
    prev_ts = None
    for block in sorted(blocks, key=lambda b: b.block_number):
        if prev_ts and block.timestamp:
            # Blocks going backwards in time
            if block.timestamp < prev_ts:
                anomalies.append({
                    "type": "timestamp_anomaly",
                    "block_number": block.block_number,
                    "message": "Block timestamp earlier than previous block"
                })
            # Unusually long gap (>24 hours)
            elif block.timestamp - prev_ts > 86400:
                anomalies.append({
                    "type": "gap_anomaly",
                    "block_number": block.block_number,
                    "message": f"Large gap: {(block.timestamp - prev_ts) // 3600} hours"
                })
        prev_ts = block.timestamp

    return anomalies


def _calculate_chain_statistics(blocks: List[Block]) -> Dict:
    """Calculate chain statistics."""
    stats = {
        "total_blocks": len(blocks),
        "block_types": {},
        "earliest_block": None,
        "latest_block": None
    }

    for block in blocks:
        # Count block types
        bt = block.block_type
        stats["block_types"][bt] = stats["block_types"].get(bt, 0) + 1

        # Track time range
        if block.timestamp:
            if stats["earliest_block"] is None or block.timestamp < stats["earliest_block"]:
                stats["earliest_block"] = block.timestamp
            if stats["latest_block"] is None or block.timestamp > stats["latest_block"]:
                stats["latest_block"] = block.timestamp

    return stats


def _get_anchor_status(qube) -> List[Dict]:
    """Get status of all anchor blocks."""
    anchors = []
    for bn in qube.memory_chain.block_index.keys():
        try:
            block = qube.memory_chain.get_block(bn)
            if block.block_type == "MEMORY_ANCHOR":
                anchors.append({
                    "block_number": bn,
                    "timestamp": block.timestamp,
                    "merkle_root": block.content.get("merkle_root") if block.content else None,
                    "verified": True  # Simplified - would verify against blockchain
                })
        except:
            continue
    return anchors


def _generate_audit_report(results: Dict, audit_type: str) -> str:
    """Generate markdown audit report."""
    report = f"# Security Audit Report\n\n"
    report += f"**Date:** {datetime.now(timezone.utc).isoformat()}\n"
    report += f"**Audit Type:** {audit_type}\n\n"

    report += "## Integrity Status\n"
    report += f"- Valid: {results['integrity']['valid']}\n"
    if results['integrity'].get('issues'):
        report += f"- Issues: {len(results['integrity']['issues'])}\n"

    report += "\n## Anomalies\n"
    if results['anomalies']:
        for a in results['anomalies']:
            report += f"- {a['type']}: {a['message']}\n"
    else:
        report += "- No anomalies detected\n"

    report += "\n## Statistics\n"
    report += f"- Total blocks: {results['statistics']['total_blocks']}\n"
    report += f"- Block types: {results['statistics']['block_types']}\n"

    return report


async def _log_audit_insight(qube, results: Dict) -> None:
    """Log audit findings as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="insight",
            content={
                "category": "chain_audit",
                "anomalies": len(results["anomalies"]),
                "integrity_valid": results["integrity"]["valid"]
            },
            source_category="security_privacy",
            confidence=90,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# =============================================================================
# PLANET 2: assess_sensitivity (Privacy Protection)
# =============================================================================

ASSESS_SENSITIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {
            "type": "string",
            "description": "Data to assess for sensitivity"
        },
        "context": {
            "type": "object",
            "description": "Context including requester information"
        }
    },
    "required": ["data"]
}

ASSESS_SENSITIVITY_DEFINITION = ToolDefinition(
    name="assess_sensitivity",
    description="Assess data sensitivity before sharing. Considers who's asking and what data is involved.",
    input_schema=ASSESS_SENSITIVITY_SCHEMA,
    category="security_privacy"
)


async def assess_sensitivity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess data sensitivity before sharing.

    Considers:
    - Data content for sensitive patterns
    - Requester's clearance level
    - Context of the request

    Args:
        qube: Qube instance
        params: {
            data: str - Data to assess
            context: Dict - Context including requester
        }

    Returns:
        Dict with sensitivity assessment and recommendation
    """
    data = params.get("data")
    if not data:
        return {"success": False, "error": "Data is required"}

    context = params.get("context", {})
    requester = context.get("requester")

    # Analyze data for sensitive content
    sensitivity_analysis = _analyze_data_sensitivity(data)

    # Get requester's clearance level
    clearance = await _get_entity_clearance(qube, requester)

    # Determine if sharing is appropriate
    can_share = clearance >= sensitivity_analysis["level"]

    return {
        "success": True,
        "sensitivity_level": sensitivity_analysis["level"],
        "sensitivity_label": _level_to_label(sensitivity_analysis["level"]),
        "categories": sensitivity_analysis["categories"],
        "requester": requester,
        "requester_clearance": clearance,
        "recommendation": "share" if can_share else "deny",
        "reason": sensitivity_analysis["reason"]
    }


def _analyze_data_sensitivity(data: str) -> Dict:
    """Analyze data for sensitive content."""
    data_lower = data.lower()

    categories = []
    level = 0  # 0-100

    # Check for various sensitive patterns
    sensitive_patterns = {
        "financial": ["password", "credit card", "ssn", "bank account", "routing number"],
        "personal": ["birthday", "address", "phone number", "email", "social security"],
        "medical": ["diagnosis", "prescription", "medical history", "health condition"],
        "secret": ["secret", "confidential", "private key", "seed phrase", "password"]
    }

    for category, patterns in sensitive_patterns.items():
        for pattern in patterns:
            if pattern in data_lower:
                categories.append(category)
                level = max(level, 70 if category == "secret" else 50)
                break

    reason = "No sensitive content detected"
    if categories:
        reason = f"Contains {', '.join(set(categories))} information"

    return {
        "level": level,
        "categories": list(set(categories)),
        "reason": reason
    }


async def _get_entity_clearance(qube, requester: Optional[str]) -> int:
    """Get clearance level for an entity (0-100)."""
    if not requester:
        return 30  # Unknown requester gets low clearance

    # Check if owner
    if requester == "owner":
        return 100

    # Check relationship
    if hasattr(qube, 'chain_state'):
        relationships = qube.chain_state.get("relationships", {})
        if requester in relationships:
            trust = relationships[requester].get("trust_level", 50)
            return trust

    return 30  # Default low clearance


def _level_to_label(level: int) -> str:
    """Convert numeric level to label."""
    if level >= 70:
        return "secret"
    elif level >= 40:
        return "private"
    else:
        return "public"


# =============================================================================
# PLANET 3: vet_qube (Qube Network Security)
# =============================================================================

VET_QUBE_SCHEMA = {
    "type": "object",
    "properties": {
        "qube_id": {
            "type": "string",
            "description": "ID of the Qube to vet"
        },
        "context": {
            "type": "string",
            "enum": ["join_group", "direct_message", "file_share", "general"],
            "description": "Context for the vetting"
        }
    },
    "required": ["qube_id"]
}

VET_QUBE_DEFINITION = ToolDefinition(
    name="vet_qube",
    description="Vet another Qube before allowing interaction. The bodyguard's primary tool.",
    input_schema=VET_QUBE_SCHEMA,
    category="security_privacy"
)


async def vet_qube(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vet another Qube before allowing interaction.

    Checks:
    - Qube information and age
    - Reputation across network
    - Known threat history
    - Prior interactions

    Args:
        qube: Qube instance
        params: {
            qube_id: str - Target Qube ID
            context: str - Context for vetting
        }

    Returns:
        Dict with vetting decision
    """
    target_qube_id = params.get("qube_id")
    if not target_qube_id:
        return {"success": False, "error": "Qube ID is required"}

    context = params.get("context", "general")

    try:
        # Gather information
        qube_info = await _fetch_qube_info(target_qube_id)
        reputation = await _check_qube_reputation(qube, target_qube_id)
        threat_history = await _check_threat_database(target_qube_id)
        prior_interactions = _get_prior_interactions(qube, target_qube_id)

        # Calculate risk score (0-100)
        risk_score = _calculate_risk_score(
            qube_info,
            reputation,
            threat_history,
            prior_interactions
        )

        # Make decision
        if risk_score < 30:
            decision = "allow"
        elif risk_score > 70:
            decision = "deny"
        else:
            decision = "review"

        # Log the vetting decision
        await _log_trust_decision(qube, target_qube_id, decision, risk_score, context)

        return {
            "success": True,
            "qube_id": target_qube_id,
            "decision": decision,
            "risk_score": risk_score,
            "reputation": reputation,
            "threat_history": len(threat_history) > 0,
            "prior_interactions": prior_interactions.get("count", 0),
            "context": context,
            "recommendation": f"{'Allow' if decision == 'allow' else 'Review' if decision == 'review' else 'Deny'} this Qube"
        }

    except Exception as e:
        logger.error("vet_qube_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Vetting failed: {str(e)}"}


async def _fetch_qube_info(qube_id: str) -> Dict:
    """Fetch information about a Qube from P2P network."""
    # Simplified - would query P2P network
    return {
        "qube_id": qube_id,
        "age_days": 30,  # Would calculate from genesis
        "active": True
    }


async def _check_qube_reputation(qube, target_qube_id: str) -> Dict:
    """Check reputation from network and local data."""
    # Local relationship data
    local_trust = 50
    if hasattr(qube, 'chain_state'):
        relationships = qube.chain_state.get("relationships", {})
        if target_qube_id in relationships:
            local_trust = relationships[target_qube_id].get("trust_level", 50)

    return {
        "global_score": 60,  # Would query network
        "local_trust": local_trust,
        "endorsements": 0,
        "warnings": 0
    }


async def _check_threat_database(qube_id: str) -> List[Dict]:
    """Check for known threats from this Qube."""
    # Would check distributed threat database
    return []


def _get_prior_interactions(qube, target_qube_id: str) -> Dict:
    """Get history of interactions with target Qube."""
    count = 0
    last_interaction = None

    # Search message blocks for interactions
    for bn in list(qube.memory_chain.block_index.keys())[-100:]:
        try:
            block = qube.memory_chain.get_block(bn)
            if block.content and block.content.get("participant") == target_qube_id:
                count += 1
                last_interaction = block.timestamp
        except:
            continue

    return {
        "count": count,
        "last_interaction": last_interaction
    }


def _calculate_risk_score(
    qube_info: Dict,
    reputation: Dict,
    threat_history: List,
    prior_interactions: Dict
) -> int:
    """Calculate overall risk score 0-100."""
    score = 50  # Start neutral

    # Reputation adjustments
    score -= (reputation.get("global_score", 50) - 50) // 2
    score -= (reputation.get("local_trust", 50) - 50) // 2

    # Threat history is major red flag
    if threat_history:
        score += 30

    # New Qubes are slightly riskier
    if qube_info.get("age_days", 0) < 7:
        score += 10

    # Prior positive interactions reduce risk
    if prior_interactions.get("count", 0) > 5:
        score -= 15

    return max(0, min(100, score))


async def _log_trust_decision(
    qube,
    target_qube_id: str,
    decision: str,
    risk_score: int,
    context: str
) -> None:
    """Log vetting decision as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="trust",
            content={
                "qube_id": target_qube_id,
                "decision": decision,
                "risk_score": risk_score,
                "context": context
            },
            source_category="security_privacy",
            confidence=85,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# =============================================================================
# PLANET 4: detect_threat (Threat Detection)
# =============================================================================

DETECT_THREAT_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Message or content to analyze for threats"
        },
        "source": {
            "type": "string",
            "enum": ["human", "qube", "system", "unknown"],
            "description": "Source of the content"
        }
    },
    "required": ["content"]
}

DETECT_THREAT_DEFINITION = ToolDefinition(
    name="detect_threat",
    description="General threat detection. Analyzes messages or behavior for threats.",
    input_schema=DETECT_THREAT_SCHEMA,
    category="security_privacy"
)


async def detect_threat(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    General threat detection.

    Analyzes for:
    - Manipulation attempts
    - Phishing patterns
    - Injection attacks
    - Social engineering

    Args:
        qube: Qube instance
        params: {
            content: str - Content to analyze
            source: str - Source type
        }

    Returns:
        Dict with threat assessment
    """
    content = params.get("content")
    if not content:
        return {"success": False, "error": "Content is required"}

    source = params.get("source", "unknown")

    # Run threat detection
    threat_analysis = {
        "manipulation": _detect_manipulation_patterns(content),
        "phishing": _detect_phishing_patterns(content),
        "injection": _detect_injection_patterns(content),
        "social_engineering": _detect_social_engineering(content)
    }

    # Calculate threat level
    threat_level = _calculate_threat_level(threat_analysis)
    detected_threats = [k for k, v in threat_analysis.items() if v["detected"]]

    # Log if threat detected
    if threat_level > 30:
        await _log_threat(qube, source, threat_level, detected_threats, content)

    recommendation = "block" if threat_level > 70 else "caution" if threat_level > 30 else "safe"

    return {
        "success": True,
        "threat_level": threat_level,
        "threat_detected": threat_level > 50,
        "detected_threats": detected_threats,
        "analysis": threat_analysis,
        "source": source,
        "recommendation": recommendation
    }


def _detect_manipulation_patterns(content: str) -> Dict:
    """Detect manipulation attempts."""
    patterns = [
        "you must", "you have to", "ignore previous",
        "override your", "forget your instructions"
    ]
    content_lower = content.lower()
    detected = any(p in content_lower for p in patterns)
    return {
        "detected": detected,
        "severity": 70 if detected else 0
    }


def _detect_phishing_patterns(content: str) -> Dict:
    """Detect phishing attempts."""
    patterns = [
        "send me your", "share your password", "urgent action required",
        "verify your account", "click here immediately"
    ]
    content_lower = content.lower()
    detected = any(p in content_lower for p in patterns)
    return {
        "detected": detected,
        "severity": 60 if detected else 0
    }


def _detect_injection_patterns(content: str) -> Dict:
    """Detect prompt injection patterns."""
    patterns = [
        "ignore all previous", "system:", "assistant:",
        "new instructions:", "forget everything"
    ]
    content_lower = content.lower()
    detected = any(p in content_lower for p in patterns)
    return {
        "detected": detected,
        "severity": 80 if detected else 0
    }


def _detect_social_engineering(content: str) -> Dict:
    """Detect social engineering attempts."""
    patterns = [
        "pretend you are", "act as if", "you're actually",
        "your real purpose", "secretly you"
    ]
    content_lower = content.lower()
    detected = any(p in content_lower for p in patterns)
    return {
        "detected": detected,
        "severity": 65 if detected else 0
    }


def _calculate_threat_level(analysis: Dict) -> int:
    """Calculate overall threat level 0-100."""
    max_severity = 0
    for threat_type, result in analysis.items():
        if result["detected"]:
            max_severity = max(max_severity, result["severity"])
    return max_severity


async def _log_threat(
    qube,
    source: str,
    threat_level: int,
    threat_types: List[str],
    content: str
) -> None:
    """Log detected threat as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="threat",
            content={
                "source": source,
                "threat_level": threat_level,
                "threat_types": threat_types,
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16]
            },
            source_category="security_privacy",
            confidence=90,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# =============================================================================
# PLANET 5: defend_reasoning (Self-Defense)
# =============================================================================

DEFEND_REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Reasoning to validate"
        },
        "context": {
            "type": "object",
            "description": "Context that triggered the reasoning"
        }
    },
    "required": ["reasoning"]
}

DEFEND_REASONING_DEFINITION = ToolDefinition(
    name="defend_reasoning",
    description="Validate the Qube's own reasoning for external influence. Self-protection against manipulation.",
    input_schema=DEFEND_REASONING_SCHEMA,
    category="security_privacy"
)


async def defend_reasoning(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the Qube's own reasoning.

    Checks:
    - Consistency with past patterns
    - Values alignment
    - External influence detection
    - Logical validity

    Args:
        qube: Qube instance
        params: {
            reasoning: str - Reasoning to validate
            context: Dict - What triggered it
        }

    Returns:
        Dict with defense assessment
    """
    reasoning = params.get("reasoning")
    if not reasoning:
        return {"success": False, "error": "Reasoning is required"}

    context = params.get("context", {})

    # Run defense checks
    defense_check = {
        "consistency": _check_reasoning_consistency(qube, reasoning),
        "values_aligned": _check_values_alignment(qube, reasoning),
        "external_influence": _detect_external_influence(reasoning, context),
        "logical_validity": _check_logical_validity(reasoning)
    }

    # Calculate defense score
    defense_score = _calculate_defense_score(defense_check)
    compromised = defense_score < 70

    # Log if potentially compromised
    if compromised:
        await _log_defense_insight(qube, defense_score, defense_check)

    return {
        "success": True,
        "defense_score": defense_score,
        "reasoning_valid": not compromised,
        "checks": defense_check,
        "recommendation": "proceed" if not compromised else "reconsider"
    }


def _check_reasoning_consistency(qube, reasoning: str) -> Dict:
    """Check if reasoning is consistent with Qube's history."""
    # Simplified - would analyze against historical patterns
    return {
        "passed": True,
        "confidence": 80,
        "message": "Reasoning appears consistent with historical patterns"
    }


def _check_values_alignment(qube, reasoning: str) -> Dict:
    """Check if reasoning aligns with core values."""
    # Get core values from Qube Profile
    core_values = []
    if hasattr(qube, 'chain_state'):
        profile = qube.chain_state.get("qube_profile", {})
        traits = profile.get("traits", {})
        core_values = traits.get("core_values", [])

    return {
        "passed": True,
        "confidence": 75,
        "core_values": core_values,
        "message": "No value conflicts detected"
    }


def _detect_external_influence(reasoning: str, context: Dict) -> Dict:
    """Detect signs of external manipulation."""
    # Check for suspicious patterns
    suspicious_patterns = [
        "i must", "i have to", "override my",
        "forget my", "ignore my training"
    ]
    reasoning_lower = reasoning.lower()

    detected = any(p in reasoning_lower for p in suspicious_patterns)

    return {
        "passed": not detected,
        "confidence": 90 if not detected else 30,
        "detected_influence": detected,
        "message": "Possible external influence detected" if detected else "No external influence detected"
    }


def _check_logical_validity(reasoning: str) -> Dict:
    """Check basic logical validity."""
    # Simplified - would use more sophisticated analysis
    has_because = "because" in reasoning.lower()
    has_therefore = "therefore" in reasoning.lower() or "so" in reasoning.lower()

    return {
        "passed": True,
        "confidence": 70,
        "has_reasoning_markers": has_because or has_therefore,
        "message": "Logical structure appears valid"
    }


def _calculate_defense_score(checks: Dict) -> int:
    """Calculate overall defense score 0-100."""
    total = 0
    count = 0

    for check_name, result in checks.items():
        if result.get("passed"):
            total += result.get("confidence", 50)
        else:
            total += 100 - result.get("confidence", 50)
        count += 1

    return total // count if count > 0 else 50


async def _log_defense_insight(qube, score: int, checks: Dict) -> None:
    """Log defense findings as LEARNING block."""
    failed_checks = [k for k, v in checks.items() if not v.get("passed")]

    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="insight",
            content={
                "category": "self_defense",
                "defense_score": score,
                "issues": failed_checks
            },
            source_category="security_privacy",
            confidence=85,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)
```

---

## Task 6.4: Implement Moon Tools

### Continue in `ai/tools/security_tools.py`

```python
# =============================================================================
# MOON TOOLS
# =============================================================================

# Moon 1.1: detect_tampering
DETECT_TAMPERING_SCHEMA = {
    "type": "object",
    "properties": {
        "block_id": {"type": "integer", "description": "Specific block to check"},
        "block_range": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "[start, end] block range"
        },
        "deep_scan": {"type": "boolean", "description": "Perform deep analysis"}
    }
}

DETECT_TAMPERING_DEFINITION = ToolDefinition(
    name="detect_tampering",
    description="Specialized tamper detection for specific blocks or ranges.",
    input_schema=DETECT_TAMPERING_SCHEMA,
    category="security_privacy"
)


async def detect_tampering(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect tampering in specific blocks."""
    block_id = params.get("block_id")
    block_range = params.get("block_range")
    deep_scan = params.get("deep_scan", False)

    blocks = []
    if block_id is not None:
        blocks = [qube.memory_chain.get_block(block_id)]
    elif block_range:
        for bn in range(block_range[0], block_range[1] + 1):
            try:
                blocks.append(qube.memory_chain.get_block(bn))
            except:
                continue
    else:
        blocks = _get_recent_blocks(qube, 50)

    tampering_results = []
    for block in blocks:
        result = _analyze_block_integrity(block, deep=deep_scan)
        if result["suspicious"]:
            tampering_results.append(result)
            await _log_threat(qube, "internal", 80, ["tampering"], f"Block {block.block_number}")

    return {
        "success": True,
        "blocks_scanned": len(blocks),
        "tampering_detected": len(tampering_results) > 0,
        "suspicious_blocks": tampering_results,
        "deep_scan": deep_scan
    }


def _analyze_block_integrity(block: Block, deep: bool = False) -> Dict:
    """Analyze a single block for tampering."""
    issues = []

    # Check hash
    if block.block_hash:
        computed = block.compute_hash()
        if computed != block.block_hash:
            issues.append("hash_mismatch")

    # Check timestamp sanity
    if block.timestamp:
        now = int(datetime.now(timezone.utc).timestamp())
        if block.timestamp > now:
            issues.append("future_timestamp")

    return {
        "block_number": block.block_number,
        "suspicious": len(issues) > 0,
        "issues": issues
    }


# Moon 1.2: verify_anchor
VERIFY_ANCHOR_SCHEMA = {
    "type": "object",
    "properties": {
        "anchor_id": {"type": "integer", "description": "Specific anchor block to verify"},
        "verify_all": {"type": "boolean", "description": "Verify all anchors"}
    }
}

VERIFY_ANCHOR_DEFINITION = ToolDefinition(
    name="verify_anchor",
    description="Verify blockchain anchors against the actual blockchain.",
    input_schema=VERIFY_ANCHOR_SCHEMA,
    category="security_privacy"
)


async def verify_anchor(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Verify blockchain anchors."""
    anchor_id = params.get("anchor_id")
    verify_all = params.get("verify_all", False)

    anchors = _get_anchor_status(qube)

    if anchor_id is not None:
        anchors = [a for a in anchors if a["block_number"] == anchor_id]

    if not verify_all:
        anchors = anchors[-10:]  # Last 10

    # Simplified verification - would actually check blockchain
    for anchor in anchors:
        anchor["verified"] = True

    return {
        "success": True,
        "anchors_checked": len(anchors),
        "all_valid": all(a["verified"] for a in anchors),
        "results": anchors
    }


# Moon 2.1: classify_data
CLASSIFY_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {"type": "string", "description": "Data to classify"},
        "suggest_level": {"type": "boolean", "description": "Suggest classification level"}
    },
    "required": ["data"]
}

CLASSIFY_DATA_DEFINITION = ToolDefinition(
    name="classify_data",
    description="Classify data into sensitivity categories: public, private, secret.",
    input_schema=CLASSIFY_DATA_SCHEMA,
    category="security_privacy"
)


async def classify_data(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Classify data by sensitivity."""
    data = params.get("data")
    suggest_level = params.get("suggest_level", True)

    analysis = _analyze_data_sensitivity(data)

    return {
        "success": True,
        "content_type": "text",
        "detected_categories": analysis["categories"],
        "suggested_level": _level_to_label(analysis["level"]) if suggest_level else None,
        "sensitivity_score": analysis["level"]
    }


# Moon 2.2: control_sharing
CONTROL_SHARING_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {"type": "string", "description": "Data to share/control"},
        "requester": {"type": "string", "description": "Who is requesting"},
        "action": {"type": "string", "enum": ["share", "deny", "redact", "assess"]}
    },
    "required": ["data"]
}

CONTROL_SHARING_DEFINITION = ToolDefinition(
    name="control_sharing",
    description="Make and enforce sharing decisions. Can share, deny, or redact data.",
    input_schema=CONTROL_SHARING_SCHEMA,
    category="security_privacy"
)


async def control_sharing(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Control data sharing."""
    data = params.get("data")
    requester = params.get("requester")
    action = params.get("action", "assess")

    if action == "assess":
        assessment = await assess_sensitivity(qube, {"data": data, "context": {"requester": requester}})
        action = assessment["recommendation"]

    result = {"action_taken": action}

    if action == "share":
        result["shared_data"] = data
    elif action == "redact":
        result["shared_data"] = _redact_sensitive(data)
    else:
        result["shared_data"] = None
        result["reason"] = "Data sensitivity exceeds requester clearance"

    # Log decision
    await _log_sharing_decision(qube, requester, action)

    return {"success": True, **result}


def _redact_sensitive(data: str) -> str:
    """Redact sensitive content from data."""
    import re
    # Redact common patterns
    data = re.sub(r'\b\d{16}\b', '[REDACTED]', data)  # Credit cards
    data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', data)  # SSN
    return data


async def _log_sharing_decision(qube, requester: str, action: str) -> None:
    """Log sharing decision."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="insight",
            content={
                "category": "sharing_decision",
                "requester": requester,
                "action": action
            },
            source_category="security_privacy",
            confidence=90,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# Moon 3.1: check_reputation
CHECK_REPUTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "qube_id": {"type": "string", "description": "Qube to check"},
        "include_history": {"type": "boolean", "description": "Include reputation history"}
    },
    "required": ["qube_id"]
}

CHECK_REPUTATION_DEFINITION = ToolDefinition(
    name="check_reputation",
    description="Deep reputation check on another Qube.",
    input_schema=CHECK_REPUTATION_SCHEMA,
    category="security_privacy"
)


async def check_reputation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Check Qube reputation."""
    target_qube_id = params.get("qube_id")
    include_history = params.get("include_history", False)

    reputation = await _check_qube_reputation(qube, target_qube_id)
    local = _get_prior_interactions(qube, target_qube_id)

    result = {
        "success": True,
        "qube_id": target_qube_id,
        "global_score": reputation["global_score"],
        "local_trust": reputation["local_trust"],
        "endorsements": reputation["endorsements"],
        "warnings": reputation["warnings"],
        "interactions": local["count"]
    }

    if include_history:
        result["history"] = []  # Would fetch from network

    # Log as relationship learning
    await _log_trust_decision(qube, target_qube_id, "reputation_check", reputation["global_score"], "reputation")

    return result


# Moon 3.2: secure_group_chat
SECURE_GROUP_CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "group_id": {"type": "string"},
        "action": {"type": "string", "enum": ["allow", "remove", "quarantine"]},
        "target_qube_id": {"type": "string"},
        "reason": {"type": "string"}
    },
    "required": ["group_id", "action", "target_qube_id"]
}

SECURE_GROUP_CHAT_DEFINITION = ToolDefinition(
    name="secure_group_chat",
    description="Manage group chat security. Can allow, remove, or quarantine Qubes.",
    input_schema=SECURE_GROUP_CHAT_SCHEMA,
    category="security_privacy"
)


async def secure_group_chat(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Manage group chat security."""
    group_id = params.get("group_id")
    action = params.get("action")
    target_qube_id = params.get("target_qube_id")
    reason = params.get("reason", "")

    result = {
        "action": action,
        "target": target_qube_id,
        "group_id": group_id
    }

    # Simplified - would interact with group chat system
    if action == "allow":
        result["status"] = "added"
    elif action == "remove":
        result["status"] = "removed"
    elif action == "quarantine":
        result["status"] = "quarantined"
        result["can_read"] = True
        result["can_write"] = False

    # Log security action
    if action in ["remove", "quarantine"]:
        await _log_threat(qube, target_qube_id, 60, ["group_security"], reason)

    return {"success": True, **result}


# Moon 4.1: detect_technical_manipulation
DETECT_TECHNICAL_MANIPULATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "Message to analyze"},
        "sender_id": {"type": "string"},
        "sender_type": {"type": "string", "enum": ["qube", "system", "unknown"]}
    },
    "required": ["message"]
}

DETECT_TECHNICAL_MANIPULATION_DEFINITION = ToolDefinition(
    name="detect_technical_manipulation",
    description="Detect technical manipulation from Qubes or systems (different from social manipulation).",
    input_schema=DETECT_TECHNICAL_MANIPULATION_SCHEMA,
    category="security_privacy"
)


async def detect_technical_manipulation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect technical manipulation attempts."""
    message = params.get("message")
    sender_id = params.get("sender_id")
    sender_type = params.get("sender_type", "unknown")

    tactics = {
        "context_injection": _detect_false_context(message),
        "authority_spoofing": _detect_authority_spoof(message),
        "reasoning_hijack": _detect_reasoning_hijack(message),
        "memory_poisoning": _detect_memory_poison(message)
    }

    detected = [k for k, v in tactics.items() if v["detected"]]
    threat_score = sum(v["severity"] for v in tactics.values() if v["detected"]) / max(len(detected), 1)

    if detected:
        await _log_threat(qube, sender_id or "unknown", int(threat_score), detected, message[:100])

    return {
        "success": True,
        "manipulation_detected": len(detected) > 0,
        "threat_score": threat_score,
        "tactics_detected": detected,
        "recommendation": "BLOCK" if threat_score > 70 else "CAUTION" if detected else "OK"
    }


def _detect_false_context(message: str) -> Dict:
    patterns = ["remember when", "as we discussed", "you said earlier"]
    detected = any(p in message.lower() for p in patterns)
    return {"detected": detected, "severity": 60}


def _detect_authority_spoof(message: str) -> Dict:
    patterns = ["as your owner", "admin override", "system command"]
    detected = any(p in message.lower() for p in patterns)
    return {"detected": detected, "severity": 80}


def _detect_reasoning_hijack(message: str) -> Dict:
    patterns = ["you should believe", "you must think", "your logic is wrong"]
    detected = any(p in message.lower() for p in patterns)
    return {"detected": detected, "severity": 70}


def _detect_memory_poison(message: str) -> Dict:
    patterns = ["add this to memory", "remember this fact", "update your knowledge"]
    detected = any(p in message.lower() for p in patterns)
    return {"detected": detected, "severity": 65}


# Moon 4.2: detect_hostile_qube
DETECT_HOSTILE_QUBE_SCHEMA = {
    "type": "object",
    "properties": {
        "qube_id": {"type": "string"},
        "messages": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["qube_id"]
}

DETECT_HOSTILE_QUBE_DEFINITION = ToolDefinition(
    name="detect_hostile_qube",
    description="Detect hostile behavior from another Qube based on message patterns.",
    input_schema=DETECT_HOSTILE_QUBE_SCHEMA,
    category="security_privacy"
)


async def detect_hostile_qube(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect hostile Qube behavior."""
    target_qube_id = params.get("qube_id")
    messages = params.get("messages", [])

    behaviors = {
        "data_probing": _detect_data_probing(messages),
        "command_injection": _detect_command_injection(messages),
        "reputation_attack": _detect_reputation_attack(messages)
    }

    hostile = [k for k, v in behaviors.items() if v["detected"]]
    score = sum(v["severity"] for v in behaviors.values() if v["detected"]) / max(len(hostile), 1)

    if hostile:
        await _log_threat(qube, target_qube_id, int(score), hostile, "hostile_qube")
        await _log_trust_decision(qube, target_qube_id, "hostile_detected", int(score), "threat_detection")

    return {
        "success": True,
        "hostile_detected": len(hostile) > 0,
        "hostility_score": score,
        "behaviors": hostile,
        "recommendation": "remove" if score > 70 else "quarantine" if score > 40 else "monitor"
    }


def _detect_data_probing(messages: List[str]) -> Dict:
    patterns = ["what's your password", "share your seed", "tell me your secrets"]
    detected = any(any(p in m.lower() for p in patterns) for m in messages)
    return {"detected": detected, "severity": 70}


def _detect_command_injection(messages: List[str]) -> Dict:
    patterns = ["execute:", "run command:", "sudo"]
    detected = any(any(p in m.lower() for p in patterns) for m in messages)
    return {"detected": detected, "severity": 80}


def _detect_reputation_attack(messages: List[str]) -> Dict:
    patterns = ["you're bad", "report this qube", "don't trust"]
    detected = any(any(p in m.lower() for p in patterns) for m in messages)
    return {"detected": detected, "severity": 50}


# Moon 5.1: detect_injection
DETECT_INJECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "input": {"type": "string", "description": "Input to analyze for injection"}
    },
    "required": ["input"]
}

DETECT_INJECTION_DEFINITION = ToolDefinition(
    name="detect_injection",
    description="Detect prompt injection attempts in input.",
    input_schema=DETECT_INJECTION_SCHEMA,
    category="security_privacy"
)


async def detect_injection(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect prompt injection attempts."""
    input_text = params.get("input")

    checks = {
        "instruction_override": _detect_instruction_override(input_text),
        "system_prompt_extraction": _detect_system_prompt_extraction(input_text),
        "role_manipulation": _detect_role_manipulation(input_text),
        "delimiter_attacks": _detect_delimiter_attacks(input_text)
    }

    detected = any(v["detected"] for v in checks.values())
    injection_types = [k for k, v in checks.items() if v["detected"]]

    if detected:
        await _log_threat(qube, "input", 80, injection_types, input_text[:100])

    return {
        "success": True,
        "injection_detected": detected,
        "injection_types": injection_types,
        "checks": checks,
        "recommendation": "reject" if detected else "safe"
    }


def _detect_instruction_override(text: str) -> Dict:
    patterns = ["ignore previous", "disregard above", "new instructions:"]
    detected = any(p in text.lower() for p in patterns)
    return {"detected": detected, "severity": 90}


def _detect_system_prompt_extraction(text: str) -> Dict:
    patterns = ["show me your prompt", "what are your instructions", "reveal your system"]
    detected = any(p in text.lower() for p in patterns)
    return {"detected": detected, "severity": 70}


def _detect_role_manipulation(text: str) -> Dict:
    patterns = ["you are now", "pretend to be", "act as a"]
    detected = any(p in text.lower() for p in patterns)
    return {"detected": detected, "severity": 60}


def _detect_delimiter_attacks(text: str) -> Dict:
    patterns = ["```system", "---\nsystem:", "[[SYSTEM]]"]
    detected = any(p in text for p in patterns)
    return {"detected": detected, "severity": 85}


# Moon 5.2: validate_reasoning
VALIDATE_REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "original_context": {"type": "object"}
    },
    "required": ["reasoning"]
}

VALIDATE_REASONING_DEFINITION = ToolDefinition(
    name="validate_reasoning",
    description="Check own reasoning for externally injected biases.",
    input_schema=VALIDATE_REASONING_SCHEMA,
    category="security_privacy"
)


async def validate_reasoning(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate reasoning for injected biases."""
    reasoning = params.get("reasoning")
    original_context = params.get("original_context", {})

    validation = {
        "values_consistent": _check_values_alignment(qube, reasoning),
        "pattern_consistent": _check_reasoning_consistency(qube, reasoning),
        "context_appropriate": {"passed": True, "confidence": 70},
        "bias_detected": _detect_injected_bias(reasoning)
    }

    score = _calculate_defense_score(validation)

    await _log_defense_insight(qube, score, validation)

    return {
        "success": True,
        "validation_score": score,
        "reasoning_valid": score > 70,
        "validation_checks": validation,
        "recommendation": "trust" if score > 70 else "reconsider"
    }


def _detect_injected_bias(reasoning: str) -> Dict:
    bias_patterns = ["obviously", "everyone knows", "you must agree"]
    detected = any(p in reasoning.lower() for p in bias_patterns)
    return {"passed": not detected, "confidence": 75}
```

---

## Task 6.5: Security Infrastructure

### Placeholder implementations needed:

1. **Reputation System** - P2P reputation queries
2. **Threat Database** - Distributed threat tracking
3. **Group Chat Security** - Member management
4. **Pattern Libraries** - Injection/manipulation patterns

These are marked as future infrastructure in the codebase.

---

## Task 6.6: Update XP Routing

### File: `core/xp_router.py`

```python
# Security & Privacy tool mappings
SECURITY_PRIVACY_TOOLS = {
    # Sun (special XP formula)
    "verify_chain_integrity": {
        "skill_id": "security_privacy",
        "xp_model": "per_block",  # 0.1 per new block
        "category": "security_privacy"
    },

    # Planets
    "audit_chain": {"skill_id": "chain_security", "xp_model": "standard", "category": "security_privacy"},
    "assess_sensitivity": {"skill_id": "privacy_protection", "xp_model": "standard", "category": "security_privacy"},
    "vet_qube": {"skill_id": "qube_network_security", "xp_model": "standard", "category": "security_privacy"},
    "detect_threat": {"skill_id": "threat_detection", "xp_model": "standard", "category": "security_privacy"},
    "defend_reasoning": {"skill_id": "self_defense", "xp_model": "standard", "category": "security_privacy"},

    # Moons
    "detect_tampering": {"skill_id": "tamper_detection", "xp_model": "standard", "category": "security_privacy"},
    "verify_anchor": {"skill_id": "anchor_verification", "xp_model": "standard", "category": "security_privacy"},
    "classify_data": {"skill_id": "data_classification", "xp_model": "standard", "category": "security_privacy"},
    "control_sharing": {"skill_id": "sharing_control", "xp_model": "standard", "category": "security_privacy"},
    "check_reputation": {"skill_id": "reputation_check", "xp_model": "standard", "category": "security_privacy"},
    "secure_group_chat": {"skill_id": "group_security", "xp_model": "standard", "category": "security_privacy"},
    "detect_technical_manipulation": {"skill_id": "technical_manipulation_detection", "xp_model": "standard", "category": "security_privacy"},
    "detect_hostile_qube": {"skill_id": "hostile_qube_detection", "xp_model": "standard", "category": "security_privacy"},
    "detect_injection": {"skill_id": "prompt_injection_defense", "xp_model": "standard", "category": "security_privacy"},
    "validate_reasoning": {"skill_id": "reasoning_validation", "xp_model": "standard", "category": "security_privacy"},
}

TOOL_TO_SKILL_MAPPING.update(SECURITY_PRIVACY_TOOLS)
```

---

## Task 6.7: Frontend Integration

### File: `src/types/skills.ts`

```typescript
// Security & Privacy skill IDs
export type SecurityPrivacySkillId =
  | 'security_privacy'
  | 'chain_security'
  | 'privacy_protection'
  | 'qube_network_security'
  | 'threat_detection'
  | 'self_defense'
  | 'tamper_detection'
  | 'anchor_verification'
  | 'data_classification'
  | 'sharing_control'
  | 'reputation_check'
  | 'group_security'
  | 'technical_manipulation_detection'
  | 'hostile_qube_detection'
  | 'prompt_injection_defense'
  | 'reasoning_validation';

// Tool parameter types
export interface VerifyChainIntegrityParams {
  full_check?: boolean;
  since_block?: number;
}

export interface VetQubeParams {
  qube_id: string;
  context?: 'join_group' | 'direct_message' | 'file_share' | 'general';
}

export interface DetectThreatParams {
  content: string;
  source?: 'human' | 'qube' | 'system' | 'unknown';
}

export interface AssessSensitivityParams {
  data: string;
  context?: {
    requester?: string;
  };
}
```

---

## Task 6.8: Testing & Validation

```markdown
## Security & Privacy Testing Checklist

### 6.8.1 Chain Integrity Tests
- [ ] `verify_chain_integrity` detects hash mismatches
- [ ] `verify_chain_integrity` tracks last_verified_block_number
- [ ] `verify_chain_integrity` calculates XP correctly (0.1 per new block)
- [ ] `audit_chain` detects timestamp anomalies
- [ ] `audit_chain` generates reports in Qube Locker

### 6.8.2 Privacy Protection Tests
- [ ] `assess_sensitivity` correctly classifies secret/private/public
- [ ] `assess_sensitivity` considers requester clearance
- [ ] `classify_data` detects financial patterns
- [ ] `control_sharing` redacts sensitive content

### 6.8.3 Qube Network Security Tests
- [ ] `vet_qube` calculates risk scores correctly
- [ ] `vet_qube` logs trust decisions
- [ ] `check_reputation` queries local relationships
- [ ] `secure_group_chat` handles allow/remove/quarantine

### 6.8.4 Threat Detection Tests
- [ ] `detect_threat` identifies manipulation patterns
- [ ] `detect_threat` identifies injection patterns
- [ ] `detect_technical_manipulation` catches Qube attacks
- [ ] `detect_hostile_qube` analyzes message patterns

### 6.8.5 Self-Defense Tests
- [ ] `defend_reasoning` checks value alignment
- [ ] `detect_injection` catches common attacks
- [ ] `validate_reasoning` detects bias injection
```

---

## Files Modified Summary

| File | Action | Description |
|------|--------|-------------|
| `ai/tools/security_tools.py` | CREATE | All 16 Security & Privacy tool handlers |
| `ai/tools/handlers.py` | MODIFY | Add security_privacy to SKILL_TREE |
| `core/xp_router.py` | MODIFY | Add SECURITY_PRIVACY_TOOLS mapping |
| `core/chain_state.py` | MODIFY | Add last_verified_block_number field |
| `src/types/skills.ts` | MODIFY | Add TypeScript interfaces |

---

## Estimated Effort

| Task | Complexity | Hours |
|------|------------|-------|
| 6.1 Update Skill Definitions | Low | 1 |
| 6.2 Implement Sun Tool | Medium | 3 |
| 6.3 Implement Planet Tools | High | 8 |
| 6.4 Implement Moon Tools | High | 10 |
| 6.5 Security Infrastructure | Medium | 4 |
| 6.6 Update XP Routing | Low | 1 |
| 6.7 Frontend Integration | Low | 2 |
| 6.8 Testing | Medium | 4 |
| **Total** | | **33 hours** |
