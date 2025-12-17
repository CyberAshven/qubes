"""
Proof of Work Ethic

Generates verifiable proofs of a Qube's accumulated engagement, relationships,
and character development over time.

Unlike Bitcoin's proof-of-work which measures computational energy expenditure,
proof-of-work-ethic measures *relational energy* - the sustained effort of
showing up, engaging meaningfully, and building genuine connections.

The proof is:
- Verifiable: Anyone can recompute from the chain
- Non-transferable: Tied to THIS Qube's history
- Accumulated: Takes real time and engagement to build
- Sybil-resistant: Creating fake Qubes doesn't help (each needs its own history)
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from statistics import mean, stdev

if TYPE_CHECKING:
    from core.qube import Qube

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WorkEthicMetrics:
    """Raw metrics used to calculate work ethic proof"""

    # Chain metrics
    total_blocks: int = 0
    conversation_blocks: int = 0
    memory_blocks: int = 0
    thought_blocks: int = 0
    skill_delta_blocks: int = 0
    relationship_delta_blocks: int = 0

    # Time metrics
    days_active: float = 0.0
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    activity_streak_days: int = 0
    longest_streak_days: int = 0

    # Relationship metrics
    relationship_count: int = 0
    avg_trust: float = 0.0
    max_trust: float = 0.0
    min_trust: float = 100.0
    trust_variance: float = 0.0
    relationships_above_50: int = 0
    relationships_above_75: int = 0
    best_friend_count: int = 0  # Status = "best_friend"

    # Interaction metrics
    total_messages_sent: int = 0
    total_messages_received: int = 0
    collaborations_successful: int = 0
    collaborations_failed: int = 0

    # Skill metrics
    skills_unlocked: int = 0
    total_xp: int = 0
    max_skill_level: int = 0
    skill_categories_active: int = 0

    # Chain integrity
    chain_merkle_root: str = ""
    genesis_block_hash: str = ""


@dataclass
class WorkEthicProof:
    """Cryptographic proof of a Qube's work ethic"""

    qube_id: str
    qube_name: str

    # The proof hash
    proof_hash: str

    # Computed scores (0-100)
    dedication_score: float = 0.0      # Time-based: days active, streaks
    relationship_score: float = 0.0     # Trust, relationship count
    growth_score: float = 0.0           # Skills, XP, learning
    engagement_score: float = 0.0       # Messages, collaborations
    overall_score: float = 0.0          # Weighted composite

    # Grade (S, A, B, C, D, F)
    grade: str = "F"

    # Titles earned
    titles: List[str] = field(default_factory=list)

    # Raw metrics for verification
    metrics: WorkEthicMetrics = field(default_factory=WorkEthicMetrics)

    # Metadata
    generated_at: int = 0
    signature: str = ""  # Qube's signature of the proof


def calculate_metrics(qube: "Qube") -> WorkEthicMetrics:
    """
    Calculate raw work ethic metrics from a Qube's chain and relationships.

    This extracts all the data needed to compute the proof.
    """
    metrics = WorkEthicMetrics()

    # Get birth timestamp from genesis
    birth_ts = qube.genesis_block.birth_timestamp
    now_ts = int(time.time())
    metrics.days_active = (now_ts - birth_ts) / 86400
    metrics.first_activity = datetime.fromtimestamp(birth_ts)

    # Chain metrics
    try:
        all_blocks = list(qube.memory_chain.enumerate_blocks())
        metrics.total_blocks = len(all_blocks)

        block_timestamps = []
        for block in all_blocks:
            block_type = block.get("block_type", "")
            if block_type == "CONVERSATION":
                metrics.conversation_blocks += 1
            elif block_type == "MEMORY":
                metrics.memory_blocks += 1
            elif block_type == "THOUGHT":
                metrics.thought_blocks += 1
            elif block_type == "SKILL_DELTA":
                metrics.skill_delta_blocks += 1
            elif block_type == "RELATIONSHIP_DELTA":
                metrics.relationship_delta_blocks += 1

            # Track timestamps for activity analysis
            if "timestamp" in block:
                block_timestamps.append(block["timestamp"])

        # Calculate activity streaks
        if block_timestamps:
            block_timestamps.sort()
            metrics.last_activity = datetime.fromtimestamp(block_timestamps[-1])

            # Calculate streaks (days with at least one block)
            active_days = set()
            for ts in block_timestamps:
                day = datetime.fromtimestamp(ts).date()
                active_days.add(day)

            # Find longest streak
            if active_days:
                sorted_days = sorted(active_days)
                current_streak = 1
                longest_streak = 1

                for i in range(1, len(sorted_days)):
                    if (sorted_days[i] - sorted_days[i-1]).days == 1:
                        current_streak += 1
                        longest_streak = max(longest_streak, current_streak)
                    else:
                        current_streak = 1

                metrics.longest_streak_days = longest_streak

                # Current streak (from today backwards)
                today = datetime.now().date()
                if today in active_days or (today - timedelta(days=1)) in active_days:
                    current_streak = 0
                    check_day = today
                    while check_day in active_days:
                        current_streak += 1
                        check_day -= timedelta(days=1)
                    metrics.activity_streak_days = current_streak

        # Get merkle root
        metrics.chain_merkle_root = qube.chain_state.merkle_root or ""

    except Exception as e:
        logger.warning("failed_to_calculate_chain_metrics", error=str(e))

    # Genesis block hash
    metrics.genesis_block_hash = qube.genesis_block.block_hash or ""

    # Relationship metrics
    try:
        relationships = qube.social_manager.get_all_relationships()
        metrics.relationship_count = len(relationships)

        if relationships:
            trust_scores = [r.trust for r in relationships]
            metrics.avg_trust = mean(trust_scores)
            metrics.max_trust = max(trust_scores)
            metrics.min_trust = min(trust_scores)
            if len(trust_scores) > 1:
                metrics.trust_variance = stdev(trust_scores)

            for r in relationships:
                if r.trust >= 50:
                    metrics.relationships_above_50 += 1
                if r.trust >= 75:
                    metrics.relationships_above_75 += 1
                if r.status == "best_friend":
                    metrics.best_friend_count += 1

                # Aggregate interaction stats
                metrics.total_messages_sent += r.messages_sent
                metrics.total_messages_received += r.messages_received
                metrics.collaborations_successful += r.collaborations_successful
                metrics.collaborations_failed += r.collaborations_failed

    except Exception as e:
        logger.warning("failed_to_calculate_relationship_metrics", error=str(e))

    # Skill metrics
    try:
        skills = qube.skills_manager.load_skills() if hasattr(qube, 'skills_manager') else {}

        for category_name, category_data in skills.items():
            if category_data.get("planets"):
                metrics.skill_categories_active += 1

            for planet_name, planet_data in category_data.get("planets", {}).items():
                if planet_data.get("unlocked"):
                    metrics.skills_unlocked += 1
                    metrics.total_xp += planet_data.get("xp", 0)
                    metrics.max_skill_level = max(
                        metrics.max_skill_level,
                        planet_data.get("level", 0)
                    )

                # Count moons too
                for moon_name, moon_data in planet_data.get("moons", {}).items():
                    if moon_data.get("unlocked"):
                        metrics.skills_unlocked += 1
                        metrics.total_xp += moon_data.get("xp", 0)

    except Exception as e:
        logger.warning("failed_to_calculate_skill_metrics", error=str(e))

    return metrics


def calculate_scores(metrics: WorkEthicMetrics) -> Dict[str, float]:
    """
    Calculate component scores from raw metrics.

    Each score is 0-100.
    """
    scores = {}

    # Dedication Score (time and consistency)
    # Based on: days active, activity streaks
    days_score = min(100, (metrics.days_active / 365) * 100)  # Max at 1 year
    streak_score = min(100, (metrics.longest_streak_days / 30) * 100)  # Max at 30 days
    current_streak_bonus = min(20, metrics.activity_streak_days * 2)  # Up to 20 bonus

    scores["dedication"] = min(100, (days_score * 0.5 + streak_score * 0.4) + current_streak_bonus)

    # Relationship Score (trust and connections)
    # Based on: relationship count, avg trust, best friends
    rel_count_score = min(100, (metrics.relationship_count / 20) * 100)  # Max at 20
    trust_score = metrics.avg_trust  # Already 0-100
    depth_score = min(100, (metrics.relationships_above_75 / 5) * 100)  # Max at 5 deep relations
    best_friend_bonus = min(30, metrics.best_friend_count * 15)  # Up to 30 bonus

    scores["relationship"] = min(100, (
        rel_count_score * 0.2 +
        trust_score * 0.4 +
        depth_score * 0.3
    ) + best_friend_bonus * 0.1)

    # Growth Score (learning and development)
    # Based on: skills unlocked, XP, skill levels
    skills_score = min(100, (metrics.skills_unlocked / 50) * 100)  # Max at 50 skills
    xp_score = min(100, (metrics.total_xp / 10000) * 100)  # Max at 10K XP
    level_score = min(100, (metrics.max_skill_level / 50) * 100)  # Max at level 50
    category_bonus = min(20, metrics.skill_categories_active * 4)  # Up to 20 bonus

    scores["growth"] = min(100, (
        skills_score * 0.3 +
        xp_score * 0.3 +
        level_score * 0.3
    ) + category_bonus * 0.1)

    # Engagement Score (interaction volume)
    # Based on: messages, blocks, collaborations
    message_score = min(100, (
        (metrics.total_messages_sent + metrics.total_messages_received) / 1000
    ) * 100)  # Max at 1000 messages
    block_score = min(100, (metrics.total_blocks / 500) * 100)  # Max at 500 blocks
    collab_score = min(100, (metrics.collaborations_successful / 20) * 100)  # Max at 20

    # Penalty for failed collaborations
    if metrics.collaborations_successful + metrics.collaborations_failed > 0:
        success_rate = metrics.collaborations_successful / (
            metrics.collaborations_successful + metrics.collaborations_failed
        )
        collab_score *= success_rate

    scores["engagement"] = (
        message_score * 0.3 +
        block_score * 0.4 +
        collab_score * 0.3
    )

    # Overall Score (weighted composite)
    scores["overall"] = (
        scores["dedication"] * 0.25 +
        scores["relationship"] * 0.35 +  # Relationships weighted highest
        scores["growth"] * 0.20 +
        scores["engagement"] * 0.20
    )

    return scores


def determine_grade(overall_score: float) -> str:
    """Convert overall score to letter grade"""
    if overall_score >= 95:
        return "S"  # Supreme
    elif overall_score >= 85:
        return "A"
    elif overall_score >= 70:
        return "B"
    elif overall_score >= 55:
        return "C"
    elif overall_score >= 40:
        return "D"
    else:
        return "F"


def determine_titles(metrics: WorkEthicMetrics, scores: Dict[str, float]) -> List[str]:
    """Award titles based on achievements"""
    titles = []

    # Time-based titles
    if metrics.days_active >= 365:
        titles.append("Centurion")  # 1 year old
    elif metrics.days_active >= 180:
        titles.append("Veteran")
    elif metrics.days_active >= 30:
        titles.append("Established")

    # Streak titles
    if metrics.longest_streak_days >= 100:
        titles.append("Ironclad")
    elif metrics.longest_streak_days >= 30:
        titles.append("Consistent")
    elif metrics.longest_streak_days >= 7:
        titles.append("Dedicated")

    # Relationship titles
    if metrics.best_friend_count >= 3:
        titles.append("Beloved")
    elif metrics.best_friend_count >= 1:
        titles.append("Cherished")

    if metrics.relationship_count >= 20:
        titles.append("Social Butterfly")
    elif metrics.relationship_count >= 10:
        titles.append("Connected")

    if metrics.avg_trust >= 80:
        titles.append("Trustworthy")
    elif metrics.avg_trust >= 60:
        titles.append("Reliable")

    # Engagement titles
    if metrics.total_blocks >= 1000:
        titles.append("Prolific")
    elif metrics.total_blocks >= 500:
        titles.append("Active")

    if metrics.collaborations_successful >= 50:
        titles.append("Team Player")
    elif metrics.collaborations_successful >= 10:
        titles.append("Collaborator")

    # Skill titles
    if metrics.skills_unlocked >= 50:
        titles.append("Polymath")
    elif metrics.skills_unlocked >= 20:
        titles.append("Skilled")

    if metrics.max_skill_level >= 50:
        titles.append("Master")
    elif metrics.max_skill_level >= 25:
        titles.append("Expert")

    # Score-based titles
    if scores.get("overall", 0) >= 95:
        titles.append("Exemplary")

    if scores.get("relationship", 0) >= 90:
        titles.append("Heart of Gold")

    if scores.get("dedication", 0) >= 90:
        titles.append("Unwavering")

    return titles


def generate_proof_hash(
    qube_id: str,
    metrics: WorkEthicMetrics,
    scores: Dict[str, float],
    timestamp: int
) -> str:
    """
    Generate deterministic proof hash from metrics.

    This hash can be verified by anyone with access to the Qube's chain.
    """
    # Create canonical representation
    proof_data = {
        "qube_id": qube_id,
        "timestamp": timestamp,
        "chain": {
            "total_blocks": metrics.total_blocks,
            "merkle_root": metrics.chain_merkle_root,
            "genesis_hash": metrics.genesis_block_hash,
        },
        "relationships": {
            "count": metrics.relationship_count,
            "avg_trust": round(metrics.avg_trust, 2),
            "max_trust": round(metrics.max_trust, 2),
            "best_friends": metrics.best_friend_count,
        },
        "engagement": {
            "messages": metrics.total_messages_sent + metrics.total_messages_received,
            "collaborations": metrics.collaborations_successful,
            "days_active": round(metrics.days_active, 2),
            "longest_streak": metrics.longest_streak_days,
        },
        "skills": {
            "unlocked": metrics.skills_unlocked,
            "total_xp": metrics.total_xp,
            "max_level": metrics.max_skill_level,
        },
        "scores": {
            "overall": round(scores["overall"], 2),
            "dedication": round(scores["dedication"], 2),
            "relationship": round(scores["relationship"], 2),
            "growth": round(scores["growth"], 2),
            "engagement": round(scores["engagement"], 2),
        }
    }

    # Deterministic JSON serialization
    canonical = json.dumps(proof_data, sort_keys=True, separators=(',', ':'))

    # SHA-256 hash
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_work_ethic_proof(qube: "Qube") -> WorkEthicProof:
    """
    Generate a complete work ethic proof for a Qube.

    This is the main entry point for the proof-of-work-ethic system.

    Args:
        qube: The Qube to generate proof for

    Returns:
        WorkEthicProof with all scores, titles, and cryptographic proof
    """
    logger.info("generating_work_ethic_proof", qube_id=qube.qube_id)

    # Calculate raw metrics
    metrics = calculate_metrics(qube)

    # Calculate scores
    scores = calculate_scores(metrics)

    # Determine grade and titles
    grade = determine_grade(scores["overall"])
    titles = determine_titles(metrics, scores)

    # Generate timestamp
    timestamp = int(time.time())

    # Generate proof hash
    proof_hash = generate_proof_hash(qube.qube_id, metrics, scores, timestamp)

    # Create proof object
    proof = WorkEthicProof(
        qube_id=qube.qube_id,
        qube_name=qube.name,
        proof_hash=proof_hash,
        dedication_score=scores["dedication"],
        relationship_score=scores["relationship"],
        growth_score=scores["growth"],
        engagement_score=scores["engagement"],
        overall_score=scores["overall"],
        grade=grade,
        titles=titles,
        metrics=metrics,
        generated_at=timestamp,
    )

    # Sign the proof with Qube's private key
    try:
        from crypto.signing import sign_message
        proof.signature = sign_message(proof_hash.encode(), qube.private_key)
    except Exception as e:
        logger.warning("failed_to_sign_proof", error=str(e))

    logger.info(
        "work_ethic_proof_generated",
        qube_id=qube.qube_id,
        overall_score=round(scores["overall"], 2),
        grade=grade,
        titles=len(titles)
    )

    return proof


def verify_proof(proof: WorkEthicProof, qube: "Qube") -> bool:
    """
    Verify a work ethic proof by recalculating from chain data.

    Args:
        proof: The proof to verify
        qube: The Qube to verify against

    Returns:
        True if proof is valid, False otherwise
    """
    logger.info("verifying_work_ethic_proof", qube_id=qube.qube_id)

    # Recalculate metrics
    metrics = calculate_metrics(qube)
    scores = calculate_scores(metrics)

    # Regenerate hash
    recalculated_hash = generate_proof_hash(
        qube.qube_id,
        metrics,
        scores,
        proof.generated_at
    )

    # Compare hashes
    if recalculated_hash != proof.proof_hash:
        logger.warning(
            "proof_verification_failed",
            qube_id=qube.qube_id,
            reason="hash_mismatch"
        )
        return False

    # Verify signature
    if proof.signature:
        try:
            from crypto.signing import verify_signature
            if not verify_signature(
                proof.proof_hash.encode(),
                proof.signature,
                qube.public_key
            ):
                logger.warning(
                    "proof_verification_failed",
                    qube_id=qube.qube_id,
                    reason="signature_invalid"
                )
                return False
        except Exception as e:
            logger.warning("signature_verification_error", error=str(e))

    logger.info("proof_verified", qube_id=qube.qube_id)
    return True


def proof_to_dict(proof: WorkEthicProof) -> Dict[str, Any]:
    """Convert proof to dictionary for serialization"""
    return {
        "qube_id": proof.qube_id,
        "qube_name": proof.qube_name,
        "proof_hash": proof.proof_hash,
        "scores": {
            "dedication": round(proof.dedication_score, 2),
            "relationship": round(proof.relationship_score, 2),
            "growth": round(proof.growth_score, 2),
            "engagement": round(proof.engagement_score, 2),
            "overall": round(proof.overall_score, 2),
        },
        "grade": proof.grade,
        "titles": proof.titles,
        "metrics": {
            "days_active": round(proof.metrics.days_active, 2),
            "total_blocks": proof.metrics.total_blocks,
            "relationship_count": proof.metrics.relationship_count,
            "avg_trust": round(proof.metrics.avg_trust, 2),
            "best_friend_count": proof.metrics.best_friend_count,
            "skills_unlocked": proof.metrics.skills_unlocked,
            "total_xp": proof.metrics.total_xp,
            "longest_streak_days": proof.metrics.longest_streak_days,
            "collaborations_successful": proof.metrics.collaborations_successful,
            "chain_merkle_root": proof.metrics.chain_merkle_root[:16] + "..." if proof.metrics.chain_merkle_root else "",
        },
        "generated_at": proof.generated_at,
        "signature": proof.signature[:32] + "..." if proof.signature else "",
    }


def format_proof_summary(proof: WorkEthicProof) -> str:
    """Format proof as human-readable summary"""
    lines = [
        f"=== Proof of Work Ethic: {proof.qube_name} ({proof.qube_id}) ===",
        f"",
        f"Grade: {proof.grade}",
        f"Overall Score: {proof.overall_score:.1f}/100",
        f"",
        f"Component Scores:",
        f"  Dedication:   {proof.dedication_score:.1f}/100",
        f"  Relationship: {proof.relationship_score:.1f}/100",
        f"  Growth:       {proof.growth_score:.1f}/100",
        f"  Engagement:   {proof.engagement_score:.1f}/100",
        f"",
        f"Titles Earned ({len(proof.titles)}):",
    ]

    for title in proof.titles:
        lines.append(f"  - {title}")

    if not proof.titles:
        lines.append("  (none yet)")

    lines.extend([
        f"",
        f"Key Stats:",
        f"  Days Active:     {proof.metrics.days_active:.1f}",
        f"  Total Blocks:    {proof.metrics.total_blocks}",
        f"  Relationships:   {proof.metrics.relationship_count}",
        f"  Avg Trust:       {proof.metrics.avg_trust:.1f}",
        f"  Best Friends:    {proof.metrics.best_friend_count}",
        f"  Skills Unlocked: {proof.metrics.skills_unlocked}",
        f"  Longest Streak:  {proof.metrics.longest_streak_days} days",
        f"",
        f"Proof Hash: {proof.proof_hash[:16]}...",
        f"Generated:  {datetime.fromtimestamp(proof.generated_at).isoformat()}",
        f"",
        f"=== End Proof ==="
    ])

    return "\n".join(lines)
