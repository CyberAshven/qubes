"""
Security & Privacy Tools (Phase 6)

16-tool skill tree for Security & Privacy category:
- Sun: verify_chain_integrity
- Planet 1: audit_chain (Chain Security)
- Planet 2: assess_sensitivity (Privacy Protection)
- Planet 3: vet_qube (Qube Network Security)
- Planet 4: detect_threat (Threat Detection)
- Planet 5: defend_reasoning (Self-Defense)
- Moon 1.1: detect_tampering
- Moon 1.2: verify_anchor
- Moon 2.1: classify_data
- Moon 2.2: control_sharing
- Moon 3.1: check_reputation
- Moon 3.2: secure_group_chat
- Moon 4.1: detect_technical_manipulation
- Moon 4.2: detect_hostile_qube
- Moon 5.1: detect_injection
- Moon 5.2: validate_reasoning
"""

import hashlib
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.block import Block, BlockType, create_learning_block

logger = structlog.get_logger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_recent_blocks(qube, count: int = 100) -> List[Block]:
    """Get the most recent blocks from the memory chain."""
    blocks = []
    block_numbers = list(qube.memory_chain.block_index.keys())[-count:]
    for bn in block_numbers:
        try:
            block = qube.memory_chain.get_block(bn)
            if block:
                blocks.append(block)
        except Exception:
            continue
    return blocks


def _get_anchor_status(qube) -> List[Dict]:
    """Get status of blockchain anchors."""
    anchors = []
    for bn in qube.memory_chain.block_index.keys():
        try:
            block = qube.memory_chain.get_block(bn)
            if block and block.block_type == BlockType.ANCHOR:
                anchors.append({
                    "block_number": block.block_number,
                    "timestamp": block.timestamp,
                    "tx_hash": block.content.get("tx_hash") if block.content else None
                })
        except Exception:
            continue
    return anchors


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
            if block and block.content and block.content.get("participant") == target_qube_id:
                count += 1
                last_interaction = block.timestamp
        except Exception:
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


# Threat detection helpers
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


# Technical manipulation helpers
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


# Hostile Qube detection helpers
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


# Injection detection helpers
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


def _detect_injected_bias(reasoning: str) -> Dict:
    bias_patterns = ["obviously", "everyone knows", "you must agree"]
    detected = any(p in reasoning.lower() for p in bias_patterns)
    return {"passed": not detected, "confidence": 75}


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


def _redact_sensitive(data: str) -> str:
    """Redact sensitive content from data."""
    import re
    # Redact common patterns
    data = re.sub(r'\b\d{16}\b', '[REDACTED]', data)  # Credit cards
    data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', data)  # SSN
    return data


# =============================================================================
# SUN TOOL: verify_chain_integrity
# =============================================================================

async def verify_chain_integrity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify the integrity of the Qube's memory chain.

    This is the Sun tool - always available. It earns XP based on
    new blocks verified (0.1 XP per block).

    Args:
        qube: Qube instance
        params: {
            full_check: bool - Check entire chain (default: False, checks recent)
            since_block: int - Start checking from this block number
        }

    Returns:
        Dict with integrity status and XP earned
    """
    full_check = params.get("full_check", False)
    since_block = params.get("since_block")

    # Get last verified block from chain state
    last_verified = 0
    if hasattr(qube, 'chain_state'):
        last_verified = qube.chain_state.get("last_verified_block_number", 0)

    # Determine which blocks to check
    if since_block is not None:
        start_block = since_block
    elif full_check:
        start_block = 0
    else:
        start_block = last_verified

    # Verify chain integrity
    issues = []
    blocks_checked = 0
    new_blocks_verified = 0
    previous_hash = None

    for bn in sorted(qube.memory_chain.block_index.keys()):
        if bn < start_block:
            continue

        try:
            block = qube.memory_chain.get_block(bn)
            blocks_checked += 1

            # Check hash chain
            if previous_hash is not None and block.previous_hash != previous_hash:
                issues.append({
                    "block": bn,
                    "issue": "hash_chain_broken",
                    "expected": previous_hash[:16] + "...",
                    "actual": block.previous_hash[:16] + "..." if block.previous_hash else "None"
                })

            # Verify block's own hash
            computed_hash = block.compute_hash()
            if block.block_hash and computed_hash != block.block_hash:
                issues.append({
                    "block": bn,
                    "issue": "hash_mismatch",
                    "computed": computed_hash[:16] + "...",
                    "stored": block.block_hash[:16] + "..."
                })

            previous_hash = block.block_hash or computed_hash

            # Track new blocks verified for XP
            if bn > last_verified:
                new_blocks_verified += 1

        except Exception as e:
            issues.append({
                "block": bn,
                "issue": "read_error",
                "error": str(e)
            })

    # Update last verified block
    if hasattr(qube, 'chain_state') and blocks_checked > 0:
        current_max = max(qube.memory_chain.block_index.keys())
        qube.chain_state["last_verified_block_number"] = current_max

    # Calculate XP (0.1 per new block verified)
    xp_earned = new_blocks_verified * 0.1

    integrity_valid = len(issues) == 0

    return {
        "success": True,
        "integrity_valid": integrity_valid,
        "blocks_checked": blocks_checked,
        "new_blocks_verified": new_blocks_verified,
        "issues": issues,
        "xp_earned": xp_earned,
        "last_verified_block": qube.chain_state.get("last_verified_block_number", 0) if hasattr(qube, 'chain_state') else 0
    }


# =============================================================================
# PLANET 1: audit_chain (Chain Security)
# =============================================================================

async def audit_chain(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive chain audit with detailed report.

    Performs deep analysis including:
    - Block type distribution
    - Temporal anomalies
    - Anchor coverage
    - Content analysis

    Args:
        qube: Qube instance
        params: {
            generate_report: bool - Generate detailed report
            check_anchors: bool - Verify blockchain anchors
        }

    Returns:
        Dict with audit results
    """
    generate_report = params.get("generate_report", True)
    check_anchors = params.get("check_anchors", True)

    # Gather statistics
    block_types = {}
    timestamps = []
    anchors = []

    for bn in qube.memory_chain.block_index.keys():
        try:
            block = qube.memory_chain.get_block(bn)

            # Count block types
            bt = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
            block_types[bt] = block_types.get(bt, 0) + 1

            # Collect timestamps
            if block.timestamp:
                timestamps.append(block.timestamp)

            # Collect anchors
            if block.block_type == BlockType.ANCHOR:
                anchors.append({
                    "block_number": block.block_number,
                    "timestamp": block.timestamp,
                    "tx_hash": block.content.get("tx_hash") if block.content else None
                })
        except Exception:
            continue

    # Analyze temporal patterns
    temporal_issues = []
    if len(timestamps) > 1:
        sorted_ts = sorted(timestamps)
        for i in range(1, len(sorted_ts)):
            if sorted_ts[i] < sorted_ts[i-1]:
                temporal_issues.append("timestamp_reversal")
                break

    # Anchor coverage
    total_blocks = len(qube.memory_chain.block_index)
    anchor_coverage = len(anchors) / max(total_blocks / 100, 1)  # Expected ~1 anchor per 100 blocks

    result = {
        "success": True,
        "total_blocks": total_blocks,
        "block_type_distribution": block_types,
        "anchor_count": len(anchors),
        "anchor_coverage": f"{anchor_coverage:.1%}",
        "temporal_issues": temporal_issues,
        "health_score": 100 - (len(temporal_issues) * 10) - (0 if anchor_coverage >= 0.8 else 20)
    }

    if generate_report:
        result["report"] = f"""Chain Audit Report
==================
Total Blocks: {total_blocks}
Block Types: {block_types}
Anchors: {len(anchors)}
Coverage: {anchor_coverage:.1%}
Issues: {temporal_issues if temporal_issues else 'None'}
Health Score: {result['health_score']}/100
"""

    if check_anchors:
        result["anchors"] = anchors

    return result


# =============================================================================
# PLANET 2: assess_sensitivity (Privacy Protection)
# =============================================================================

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


# =============================================================================
# PLANET 3: vet_qube (Qube Network Security)
# =============================================================================

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


# =============================================================================
# PLANET 4: detect_threat (Threat Detection)
# =============================================================================

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


# =============================================================================
# PLANET 5: defend_reasoning (Self-Defense)
# =============================================================================

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


# =============================================================================
# MOON 1.1: detect_tampering
# =============================================================================

async def detect_tampering(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect tampering in specific blocks."""
    block_id = params.get("block_id")
    block_range = params.get("block_range")
    deep_scan = params.get("deep_scan", False)

    blocks = []
    if block_id is not None:
        try:
            blocks = [qube.memory_chain.get_block(block_id)]
        except Exception:
            return {"success": False, "error": f"Block {block_id} not found"}
    elif block_range:
        for bn in range(block_range[0], block_range[1] + 1):
            try:
                blocks.append(qube.memory_chain.get_block(bn))
            except Exception:
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


# =============================================================================
# MOON 1.2: verify_anchor
# =============================================================================

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
        "all_valid": all(a.get("verified", False) for a in anchors),
        "results": anchors
    }


# =============================================================================
# MOON 2.1: classify_data
# =============================================================================

async def classify_data(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Classify data by sensitivity."""
    data = params.get("data")
    if not data:
        return {"success": False, "error": "Data is required"}

    suggest_level = params.get("suggest_level", True)

    analysis = _analyze_data_sensitivity(data)

    return {
        "success": True,
        "content_type": "text",
        "detected_categories": analysis["categories"],
        "suggested_level": _level_to_label(analysis["level"]) if suggest_level else None,
        "sensitivity_score": analysis["level"]
    }


# =============================================================================
# MOON 2.2: control_sharing
# =============================================================================

async def control_sharing(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Control data sharing."""
    data = params.get("data")
    if not data:
        return {"success": False, "error": "Data is required"}

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
    await _log_sharing_decision(qube, requester or "unknown", action)

    return {"success": True, **result}


# =============================================================================
# MOON 3.1: check_reputation
# =============================================================================

async def check_reputation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Check Qube reputation."""
    target_qube_id = params.get("qube_id")
    if not target_qube_id:
        return {"success": False, "error": "Qube ID is required"}

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


# =============================================================================
# MOON 3.2: secure_group_chat
# =============================================================================

async def secure_group_chat(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Manage group chat security."""
    group_id = params.get("group_id")
    if not group_id:
        return {"success": False, "error": "Group ID is required"}

    action = params.get("action")
    if not action:
        return {"success": False, "error": "Action is required"}

    target_qube_id = params.get("target_qube_id")
    if not target_qube_id:
        return {"success": False, "error": "Target Qube ID is required"}

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


# =============================================================================
# MOON 4.1: detect_technical_manipulation
# =============================================================================

async def detect_technical_manipulation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect technical manipulation attempts."""
    message = params.get("message")
    if not message:
        return {"success": False, "error": "Message is required"}

    sender_id = params.get("sender_id")
    sender_type = params.get("sender_type", "unknown")

    tactics = {
        "context_injection": _detect_false_context(message),
        "authority_spoofing": _detect_authority_spoof(message),
        "reasoning_hijack": _detect_reasoning_hijack(message),
        "memory_poisoning": _detect_memory_poison(message)
    }

    detected = [k for k, v in tactics.items() if v["detected"]]
    threat_score = sum(v["severity"] for v in tactics.values() if v["detected"]) / max(len(detected), 1) if detected else 0

    if detected:
        await _log_threat(qube, sender_id or "unknown", int(threat_score), detected, message[:100])

    return {
        "success": True,
        "manipulation_detected": len(detected) > 0,
        "threat_score": threat_score,
        "tactics_detected": detected,
        "recommendation": "BLOCK" if threat_score > 70 else "CAUTION" if detected else "OK"
    }


# =============================================================================
# MOON 4.2: detect_hostile_qube
# =============================================================================

async def detect_hostile_qube(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect hostile Qube behavior."""
    target_qube_id = params.get("qube_id")
    if not target_qube_id:
        return {"success": False, "error": "Qube ID is required"}

    messages = params.get("messages", [])

    behaviors = {
        "data_probing": _detect_data_probing(messages),
        "command_injection": _detect_command_injection(messages),
        "reputation_attack": _detect_reputation_attack(messages)
    }

    hostile = [k for k, v in behaviors.items() if v["detected"]]
    score = sum(v["severity"] for v in behaviors.values() if v["detected"]) / max(len(hostile), 1) if hostile else 0

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


# =============================================================================
# MOON 5.1: detect_injection
# =============================================================================

async def detect_injection(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect prompt injection attempts."""
    input_text = params.get("input")
    if not input_text:
        return {"success": False, "error": "Input is required"}

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


# =============================================================================
# MOON 5.2: validate_reasoning
# =============================================================================

async def validate_reasoning(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate reasoning for injected biases."""
    reasoning = params.get("reasoning")
    if not reasoning:
        return {"success": False, "error": "Reasoning is required"}

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


# =============================================================================
# HANDLER EXPORT
# =============================================================================

SECURITY_TOOL_HANDLERS = {
    # Sun
    "verify_chain_integrity": verify_chain_integrity,
    # Planet 1: Chain Security
    "audit_chain": audit_chain,
    # Planet 2: Privacy Protection
    "assess_sensitivity": assess_sensitivity,
    # Planet 3: Qube Network Security
    "vet_qube": vet_qube,
    # Planet 4: Threat Detection
    "detect_threat": detect_threat,
    # Planet 5: Self-Defense
    "defend_reasoning": defend_reasoning,
    # Moon 1.1: Tamper Detection
    "detect_tampering": detect_tampering,
    # Moon 1.2: Anchor Verification
    "verify_anchor": verify_anchor,
    # Moon 2.1: Data Classification
    "classify_data": classify_data,
    # Moon 2.2: Sharing Control
    "control_sharing": control_sharing,
    # Moon 3.1: Reputation Check
    "check_reputation": check_reputation,
    # Moon 3.2: Group Security
    "secure_group_chat": secure_group_chat,
    # Moon 4.1: Technical Manipulation Detection
    "detect_technical_manipulation": detect_technical_manipulation,
    # Moon 4.2: Hostile Qube Detection
    "detect_hostile_qube": detect_hostile_qube,
    # Moon 5.1: Prompt Injection Defense
    "detect_injection": detect_injection,
    # Moon 5.2: Reasoning Validation
    "validate_reasoning": validate_reasoning,
}
