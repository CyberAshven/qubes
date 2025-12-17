"""
Memory Refresh Protocol

Allows qubes to accept and re-anchor shared memories from peers when
they have asymmetric anchoring (one qube anchored, the other didn't).

This solves the "Bob forgot but Alice remembers" problem by allowing
Alice to refresh Bob's memory with cryptographically signed proof.
"""

import time
from typing import List, Dict, Any
from pathlib import Path

from core.block import Block
from crypto.signing import verify_block_signature
from utils.logging import get_logger

logger = get_logger(__name__)


async def refresh_memory_from_peer(
    qube,
    peer_qube_id: str,
    shared_blocks: List[Block]
) -> Dict[str, Any]:
    """
    Accept peer's memory of shared experiences

    Validates that this qube participated and signed these blocks,
    then re-anchors them into the local memory chain.

    This enables the "memory refresh" pattern:
    - Alice and Bob have conversation
    - Both sign collaborative blocks
    - Alice anchors, Bob doesn't
    - Later, Alice can remind Bob by sending the signed blocks
    - Bob verifies his own signature and re-anchors

    Args:
        qube: This Qube instance
        peer_qube_id: Peer offering the memory
        shared_blocks: Blocks from peer's permanent chain

    Returns:
        {
            "accepted": int,  # Blocks accepted and re-anchored
            "rejected": int,  # Blocks rejected (invalid)
            "reasons": List[str],  # Rejection reasons
            "relationship_updates_applied": bool
        }
    """
    accepted = 0
    rejected = 0
    rejection_reasons = []

    logger.info(
        "memory_refresh_requested",
        peer=peer_qube_id,
        blocks_offered=len(shared_blocks),
        qube_id=qube.qube_id
    )

    for block in shared_blocks:
        # Convert to dict if needed
        block_dict = block.to_dict() if hasattr(block, 'to_dict') else block

        # 1. Verify this qube was a participant
        participants = block_dict.get("content", {}).get("participants", [])
        if qube.qube_id not in participants:
            rejected += 1
            rejection_reasons.append(
                f"Block {block_dict.get('block_number')}: Not a participant"
            )
            logger.warning(
                "memory_refresh_rejected_not_participant",
                peer=peer_qube_id,
                block_num=block_dict.get("block_number"),
                qube_id=qube.qube_id
            )
            continue

        # 2. Verify this qube's signature exists
        signatures = block_dict.get("signatures", {})
        if isinstance(signatures, dict):
            my_signature = signatures.get(qube.qube_id)
        else:
            # Single signature block - check if it's ours
            my_signature = block_dict.get("signature")

        if not my_signature:
            rejected += 1
            rejection_reasons.append(
                f"Block {block_dict.get('block_number')}: Missing signature"
            )
            logger.warning(
                "memory_refresh_rejected_no_signature",
                peer=peer_qube_id,
                block_num=block_dict.get("block_number"),
                qube_id=qube.qube_id
            )
            continue

        # 3. Verify signature is valid (proves we actually signed this)
        try:
            valid = verify_block_signature(
                block_dict,
                my_signature,
                qube.public_key
            )
            if not valid:
                rejected += 1
                rejection_reasons.append(
                    f"Block {block_dict.get('block_number')}: Invalid signature"
                )
                logger.warning(
                    "memory_refresh_rejected_invalid_signature",
                    peer=peer_qube_id,
                    block_num=block_dict.get("block_number"),
                    qube_id=qube.qube_id
                )
                continue
        except Exception as e:
            rejected += 1
            rejection_reasons.append(
                f"Block {block_dict.get('block_number')}: Signature verification error"
            )
            logger.error(
                "memory_refresh_signature_verification_error",
                peer=peer_qube_id,
                block_num=block_dict.get("block_number"),
                error=str(e),
                exc_info=True
            )
            continue

        # 4. Verify timestamp is reasonable (not future-dated)
        block_timestamp = block_dict.get("timestamp", 0)
        current_time = int(time.time())
        if block_timestamp > current_time + 3600:  # Allow 1 hour clock skew
            rejected += 1
            rejection_reasons.append(
                f"Block {block_dict.get('block_number')}: Future-dated timestamp"
            )
            logger.warning(
                "memory_refresh_rejected_future_timestamp",
                peer=peer_qube_id,
                block_num=block_dict.get("block_number"),
                block_time=block_timestamp,
                current_time=current_time
            )
            continue

        # 5. Check if we already have this block (by block_hash)
        block_hash = block_dict.get("block_hash")
        if block_hash:
            # Search our chain for this hash
            try:
                existing_blocks = qube.memory_chain.get_all_blocks()
                if any(b.block_hash == block_hash for b in existing_blocks):
                    rejected += 1
                    rejection_reasons.append(
                        f"Block {block_dict.get('block_number')}: Already in chain"
                    )
                    logger.debug(
                        "memory_refresh_skipped_duplicate",
                        peer=peer_qube_id,
                        block_hash=block_hash[:16]
                    )
                    continue
            except Exception as e:
                logger.warning(
                    "memory_refresh_duplicate_check_failed",
                    error=str(e)
                )
                # Continue anyway - better to accept than reject

        # ✅ ACCEPT: All validations passed
        # Re-anchor this block into our chain
        try:
            # Convert back to Block object if needed
            if isinstance(block, dict):
                block_obj = Block.from_dict(block)
            else:
                block_obj = block

            # Add to permanent chain
            # Note: This will assign a new block_number in our chain
            qube.memory_chain.add_block(block_obj)

            # Apply relationship updates from this block
            if block_dict.get("relationship_updates"):
                for entity_id, deltas in block_dict["relationship_updates"].items():
                    _apply_relationship_deltas(qube, entity_id, deltas)

            accepted += 1
            logger.info(
                "memory_refreshed_from_peer",
                peer=peer_qube_id,
                original_block_num=block_dict.get("block_number"),
                new_block_num=qube.memory_chain.get_chain_length() - 1,
                qube_id=qube.qube_id
            )

        except Exception as e:
            rejected += 1
            rejection_reasons.append(
                f"Block {block_dict.get('block_number')}: Re-anchoring failed - {str(e)}"
            )
            logger.error(
                "memory_refresh_reanchor_failed",
                peer=peer_qube_id,
                block_num=block_dict.get("block_number"),
                error=str(e),
                exc_info=True
            )
            continue

    result = {
        "accepted": accepted,
        "rejected": rejected,
        "reasons": rejection_reasons,
        "relationship_updates_applied": accepted > 0
    }

    logger.info(
        "memory_refresh_complete",
        peer=peer_qube_id,
        accepted=accepted,
        rejected=rejected,
        qube_id=qube.qube_id
    )

    return result


def _apply_relationship_deltas(qube, entity_id: str, deltas: Dict[str, Any]) -> None:
    """
    Apply relationship stat changes from a refreshed block

    Args:
        qube: Qube instance
        entity_id: Entity whose relationship to update
        deltas: Dictionary of stat changes
    """
    try:
        # Determine entity type - check if this is the user (human) or another qube
        entity_type = "human" if entity_id == qube.user_name else "qube"

        # Get or create relationship
        rel = qube.relationships.get_or_create_relationship(
            entity_id=entity_id,
            entity_type=entity_type,
            has_met=True
        )

        # Fix entity_type if it's wrong on existing relationship
        if rel.entity_type != entity_type:
            rel.entity_type = entity_type

        # Apply counter deltas
        rel.total_messages_sent += deltas.get("messages_sent_delta", 0)
        rel.total_messages_received += deltas.get("messages_received_delta", 0)
        rel.total_collaborations += deltas.get("collaborations_delta", 0)

        # Apply trust component updates
        trust_updates = deltas.get("trust_updates", {})
        for component, delta in trust_updates.items():
            if component in ["reliability", "honesty", "responsiveness"]:
                qube.relationships.trust_scorer.update_trust_component(
                    rel, component, delta, reason="Memory refresh from peer"
                )

        # Update last interaction timestamp if provided
        if "interaction_timestamp" in deltas:
            rel.last_interaction_timestamp = deltas["interaction_timestamp"]

        # Check for relationship progression
        qube.relationships.check_progression(entity_id)

        # Save changes
        qube.relationships.storage.save()

        logger.debug(
            "relationship_deltas_applied",
            entity_id=entity_id,
            messages_sent_delta=deltas.get("messages_sent_delta", 0),
            messages_received_delta=deltas.get("messages_received_delta", 0)
        )

    except Exception as e:
        logger.error(
            "relationship_delta_application_failed",
            entity_id=entity_id,
            error=str(e),
            exc_info=True
        )
        # Don't raise - we don't want to fail the entire refresh
