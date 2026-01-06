"""
Memory Block Data Structure - Exact Documentation Implementation

8 block types as specified in docs/05_Data_Structures.md Section 2.2
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from utils.logging import get_logger

logger = get_logger(__name__)


class BlockType(str, Enum):
    """Memory block types - exactly as documented"""
    GENESIS = "GENESIS"
    THOUGHT = "THOUGHT"
    ACTION = "ACTION"
    OBSERVATION = "OBSERVATION"
    MESSAGE = "MESSAGE"
    DECISION = "DECISION"
    MEMORY_ANCHOR = "MEMORY_ANCHOR"
    COLLABORATIVE_MEMORY = "COLLABORATIVE_MEMORY"
    SUMMARY = "SUMMARY"
    GAME = "GAME"


class Block(BaseModel):
    """
    Memory block matching documentation structure exactly

    From docs/05_Data_Structures.md Section 2.2
    """
    block_type: BlockType
    block_number: int
    qube_id: str  # Required for all blocks
    timestamp: Optional[int] = None  # Timestamp in seconds (Unix epoch)
    content: Optional[Dict[str, Any]] = None  # Optional for backward compatibility with legacy blocks
    encrypted: bool = True
    temporary: bool = False  # For session blocks
    session_id: Optional[str] = None  # If temporary
    original_session_index: Optional[int] = None  # After anchoring
    previous_block_number: Optional[int] = None  # For session blocks (simple reference, no hash)
    previous_hash: Optional[str] = None  # For permanent blocks (cryptographic link)
    block_hash: Optional[str] = None  # Only for permanent blocks
    signature: Optional[str] = None  # Only for permanent blocks (single signer)

    # Multi-party signatures for collaborative blocks (GAME, COLLABORATIVE_MEMORY, etc.)
    # Each entry: {"qube_id": "...", "public_key": "...", "signature": "..."}
    # All participants sign the content_hash (not block_hash, since chain metadata differs)
    participant_signatures: Optional[List[Dict[str, str]]] = None
    content_hash: Optional[str] = None  # Hash of just the content (signed by all participants)

    # Token usage tracking (for blocks generated with AI)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_used: Optional[str] = None
    estimated_cost_usd: Optional[float] = None

    # Relationship tracking (for asymmetric anchoring)
    relationship_updates: Optional[Dict[str, Dict[str, Any]]] = None

    # GENESIS specific additional fields
    qube_name: Optional[str] = None
    creator: Optional[str] = None
    public_key: Optional[str] = None
    birth_timestamp: Optional[int] = None
    genesis_prompt: Optional[str] = None
    genesis_prompt_encrypted: Optional[bool] = None
    ai_model: Optional[str] = None
    voice_model: Optional[str] = None
    avatar: Optional[Dict[str, Any]] = None
    favorite_color: Optional[str] = None
    home_blockchain: Optional[str] = None
    nft_contract: Optional[str] = None
    nft_token_id: Optional[str] = None
    capabilities: Optional[Dict[str, bool]] = None
    default_trust_level: Optional[int] = None
    merkle_root: Optional[str] = None

    # NFT minting fields (populated after minting)
    nft_category_id: Optional[str] = None
    mint_txid: Optional[str] = None
    bcmr_uri: Optional[str] = None
    commitment: Optional[str] = None

    class Config:
        use_enum_values = True

    def __init__(self, **data):
        # Set timestamp to current time if not provided
        if 'timestamp' not in data or data.get('timestamp') is None:
            data['timestamp'] = int(datetime.now(timezone.utc).timestamp())
        super().__init__(**data)

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of block (excludes signature fields)"""
        # Import here to avoid circular import (crypto.signing -> core.exceptions -> core.block)
        from crypto.signing import hash_block
        return hash_block(self.model_dump(exclude={
            "block_hash", "signature", "participant_signatures", "content_hash"
        }))

    def compute_content_hash(self) -> str:
        """
        Compute hash of just the content (for multi-party signing).

        This excludes chain-specific metadata (block_number, previous_hash, qube_id)
        so all participants can sign the same content even though their chain
        positions differ.

        Used for GAME blocks and other collaborative blocks.
        """
        from crypto.signing import hash_block
        if self.content is None:
            return hash_block({})
        # Hash just the content - this is what all participants sign
        return hash_block(self.content)

    def add_participant_signature(
        self,
        qube_id: str,
        public_key_hex: str,
        private_key
    ) -> None:
        """
        Add a participant's signature to this block.

        Signs the content_hash (not block_hash) so signature is valid
        across different chains.

        Args:
            qube_id: ID of the signing Qube
            public_key_hex: Hex-encoded public key
            private_key: ECDSA private key for signing
        """
        from crypto.signing import sign_message

        # Ensure content_hash is computed
        if not self.content_hash:
            self.content_hash = self.compute_content_hash()

        # Sign the content hash (sign_message takes private_key first)
        signature = sign_message(private_key, self.content_hash)

        # Initialize list if needed
        if self.participant_signatures is None:
            self.participant_signatures = []

        # Add signature (avoid duplicates)
        existing_ids = [s["qube_id"] for s in self.participant_signatures]
        if qube_id not in existing_ids:
            self.participant_signatures.append({
                "qube_id": qube_id,
                "public_key": public_key_hex,
                "signature": signature
            })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        """Create Block from dictionary"""
        # Set timestamp to current time if not provided
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = int(datetime.now(timezone.utc).timestamp())
        return cls(**data)


# =============================================================================
# GENESIS BLOCK
# =============================================================================

def create_genesis_block(
    qube_id: str,
    qube_name: str,
    creator: str,
    public_key: str,
    genesis_prompt: str,
    ai_model: str,
    voice_model: str,
    avatar: Dict[str, Any],
    favorite_color: str = "#4A90E2",
    home_blockchain: str = "bitcoin_cash",
    genesis_prompt_encrypted: bool = False,
    capabilities: Optional[Dict[str, bool]] = None,
    default_trust_level: int = 50,
    nft_contract: Optional[str] = None,
    nft_token_id: Optional[str] = None
) -> Block:
    """
    Create genesis block exactly as documented

    From docs Section 2.1
    """
    birth_timestamp = int(datetime.now(timezone.utc).timestamp())

    if capabilities is None:
        capabilities = {
            "web_search": True,
            "image_generation": True,
            "image_processing": True,
            "tts": True,
            "stt": True,
            "code_execution": False
        }

    block = Block(
        block_type=BlockType.GENESIS,
        block_number=0,
        qube_id=qube_id,
        qube_name=qube_name,
        creator=creator,
        public_key=public_key,
        birth_timestamp=birth_timestamp,
        genesis_prompt=genesis_prompt,
        genesis_prompt_encrypted=genesis_prompt_encrypted,
        ai_model=ai_model,
        voice_model=voice_model,
        avatar=avatar,
        favorite_color=favorite_color,
        home_blockchain=home_blockchain,
        nft_contract=nft_contract,
        nft_token_id=nft_token_id,
        capabilities=capabilities,
        default_trust_level=default_trust_level,
        merkle_root=None,
        previous_hash="0" * 64,
        content={},  # Genesis uses top-level fields, not content
        encrypted=False,
        temporary=False
    )

    block.block_hash = block.compute_hash()

    logger.info("genesis_block_created", qube_id=qube_id, block_hash=block.block_hash[:16])

    return block


# =============================================================================
# THOUGHT BLOCK
# =============================================================================

def create_thought_block(
    qube_id: str,
    block_number: int,
    previous_hash: Optional[str] = None,
    previous_block_number: Optional[int] = None,
    internal_monologue: str = "",
    reasoning_chain: Optional[List[str]] = None,
    confidence: float = 0.9,
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create THOUGHT block

    From docs Section 2.2

    Session blocks (temporary=True):
    - Use previous_block_number (not previous_hash)
    - No block_hash computed
    - No signature

    Permanent blocks (temporary=False):
    - Use previous_hash (not previous_block_number)
    - block_hash computed
    - Signature required (added later)
    """
    block = Block(
        block_type=BlockType.THOUGHT,
        qube_id=qube_id,
        block_number=block_number,
        content={
            "internal_monologue": internal_monologue,
            "reasoning_chain": reasoning_chain or [],
            "confidence": confidence
        },
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=previous_block_number if temporary else None
    )

    # Only compute hash for permanent blocks
    if not temporary:
        block.block_hash = block.compute_hash()

    return block


# =============================================================================
# ACTION BLOCK
# =============================================================================

def create_action_block(
    qube_id: str,
    block_number: int,
    previous_hash: Optional[str] = None,
    previous_block_number: Optional[int] = None,
    action_type: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    initiated_by: str = "self",
    cost_estimate: float = 0.0,
    result: Optional[Dict[str, Any]] = None,
    status: str = "pending",
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create ACTION block

    From docs Section 2.2

    ACTION blocks now include the result directly (OBSERVATION blocks removed).

    Session blocks (temporary=True):
    - Use previous_block_number (not previous_hash)
    - No block_hash computed
    - No signature

    Permanent blocks (temporary=False):
    - Use previous_hash (not previous_block_number)
    - block_hash computed
    - Signature required (added later)
    """
    block = Block(
        block_type=BlockType.ACTION,
        qube_id=qube_id,
        block_number=block_number,
        content={
            "action_type": action_type,
            "parameters": parameters or {},
            "initiated_by": initiated_by,
            "cost_estimate": cost_estimate,
            "status": status,
            "result": result
        },
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=previous_block_number if temporary else None
    )

    # Only compute hash for permanent blocks
    if not temporary:
        block.block_hash = block.compute_hash()

    return block


# =============================================================================
# OBSERVATION BLOCK (DEPRECATED)
# =============================================================================

def create_observation_block(
    qube_id: str,
    block_number: int,
    previous_hash: Optional[str] = None,
    previous_block_number: Optional[int] = None,
    observation_source: str = "",
    observation_data: Any = None,
    related_action_block: int = 0,
    reliability_score: float = 0.9,
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create OBSERVATION block

    DEPRECATED: OBSERVATION blocks are no longer used. Tool results are now
    included directly in ACTION blocks via the 'result' field.

    This function is kept for backward compatibility only.

    From docs Section 2.2

    Session blocks (temporary=True):
    - Use previous_block_number (not previous_hash)
    - No block_hash computed
    - No signature

    Permanent blocks (temporary=False):
    - Use previous_hash (not previous_block_number)
    - block_hash computed
    - Signature required (added later)
    """
    block = Block(
        block_type=BlockType.OBSERVATION,
        qube_id=qube_id,
        block_number=block_number,
        content={
            "observation_source": observation_source,
            "observation_data": observation_data,
            "related_action_block": related_action_block,
            "reliability_score": reliability_score
        },
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=previous_block_number if temporary else None
    )

    # Only compute hash for permanent blocks
    if not temporary:
        block.block_hash = block.compute_hash()

    return block


# =============================================================================
# MESSAGE BLOCK
# =============================================================================

def create_message_block(
    qube_id: str,
    block_number: int,
    previous_hash: Optional[str] = None,  # Only for permanent blocks
    previous_block_number: Optional[int] = None,  # Only for session blocks
    message_type: str = "qube_to_human",  # "qube_to_qube", "qube_to_human", "human_to_qube", "qube_to_group", "human_to_group"
    recipient_id: str = "",
    sender_id: Optional[str] = None,  # For multi-Qube conversations
    message_body: str = "",
    conversation_id: str = "",
    requires_response: bool = False,
    message_encrypted_for_recipient: Optional[str] = None,
    temporary: bool = False,
    session_id: Optional[str] = None,
    # Multi-Qube conversation fields
    participants: Optional[List[str]] = None,
    turn_number: Optional[int] = None,
    speaker_id: Optional[str] = None,
    speaker_name: Optional[str] = None,
    participant_signatures: Optional[Dict[str, str]] = None,
    # Token usage tracking (for AI-generated messages)
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    model_used: Optional[str] = None,
    estimated_cost_usd: Optional[float] = None
) -> Block:
    """
    Create MESSAGE block

    From docs Section 2.2

    Enhanced for multi-Qube conversations:
    - participants: List of all Qube IDs in group conversation
    - turn_number: Turn number in conversation
    - speaker_id: ID of the Qube/user who sent this message
    - speaker_name: Name of the speaker
    - participant_signatures: Dict of qube_id -> signature (multi-sig attestation)

    Session blocks (temporary=True):
    - Use previous_block_number (not previous_hash)
    - No block_hash computed
    - No signature

    Permanent blocks (temporary=False):
    - Use previous_hash (not previous_block_number)
    - block_hash computed
    - Signature required (added later)
    """
    content = {
        "message_type": message_type,
        "recipient_id": recipient_id,
        "message_body": message_body,
        "message_encrypted_for_recipient": message_encrypted_for_recipient,
        "conversation_id": conversation_id,
        "requires_response": requires_response
    }

    # Add sender_id if provided
    if sender_id:
        content["sender_id"] = sender_id

    # Add multi-Qube conversation fields if provided
    if participants:
        content["participants"] = participants
    if turn_number is not None:
        content["turn_number"] = turn_number
    if speaker_id:
        content["speaker_id"] = speaker_id
    if speaker_name:
        content["speaker_name"] = speaker_name
    if participant_signatures:
        content["participant_signatures"] = participant_signatures

    block = Block(
        block_type=BlockType.MESSAGE,
        qube_id=qube_id,
        block_number=block_number,
        content=content,
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=previous_block_number if temporary else None,
        # Token usage tracking (stored outside encrypted content)
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        model_used=model_used,
        estimated_cost_usd=estimated_cost_usd
    )

    # Only compute hash for permanent blocks
    if not temporary:
        block.block_hash = block.compute_hash()

    return block


# =============================================================================
# DECISION BLOCK
# =============================================================================

def create_decision_block(
    qube_id: str,
    block_number: int,
    previous_hash: Optional[str] = None,
    previous_block_number: Optional[int] = None,
    decision: str = "",
    from_value: Any = None,
    to_value: Any = None,
    reasoning: str = "",
    impact_assessment: str = "",
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create DECISION block

    From docs Section 2.2

    Session blocks (temporary=True):
    - Use previous_block_number (not previous_hash)
    - No block_hash computed
    - No signature

    Permanent blocks (temporary=False):
    - Use previous_hash (not previous_block_number)
    - block_hash computed
    - Signature required (added later)
    """
    block = Block(
        block_type=BlockType.DECISION,
        block_number=block_number,
        qube_id=qube_id,
        content={
            "decision": decision,
            "from_value": from_value,
            "to_value": to_value,
            "reasoning": reasoning,
            "impact_assessment": impact_assessment
        },
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash if not temporary else None,
        previous_block_number=previous_block_number if temporary else None
    )

    # Only compute hash for permanent blocks
    if not temporary:
        block.block_hash = block.compute_hash()

    return block


# =============================================================================
# MEMORY_ANCHOR BLOCK
# =============================================================================

def create_memory_anchor_block(
    qube_id: str,
    block_number: int,
    previous_hash: str,
    merkle_root: str,
    block_range: List[int],
    total_blocks: int,
    anchor_type: str = "periodic",  # "periodic", "manual", or "significant_event"
    zk_proof: Optional[str] = None
) -> Block:
    """
    Create MEMORY_ANCHOR block

    From docs Section 2.2
    Never encrypted (public for verification)
    """
    block = Block(
        block_type=BlockType.MEMORY_ANCHOR,
        qube_id=qube_id,
        block_number=block_number,
        content={
            "merkle_root": merkle_root,
            "block_range": block_range,
            "total_blocks": total_blocks,
            "anchor_type": anchor_type,
            "zk_proof": zk_proof
        },
        encrypted=False,  # Anchors are public
        temporary=False,  # Never temporary
        previous_hash=previous_hash,
        merkle_root=merkle_root
    )

    block.block_hash = block.compute_hash()

    logger.info(
        "memory_anchor_created",
        block_number=block_number,
        merkle_root=merkle_root[:16],
        block_range=block_range
    )

    return block


# =============================================================================
# COLLABORATIVE_MEMORY BLOCK
# =============================================================================

def create_collaborative_memory_block(
    qube_id: str,
    block_number: int,
    previous_hash: str,
    event_description: str,
    participants: List[str],
    shared_data_hash: str,
    contribution_weights: Dict[str, float],
    signatures: Dict[str, str],
    temporary: bool = False,
    session_id: Optional[str] = None
) -> Block:
    """
    Create COLLABORATIVE_MEMORY block

    From docs Section 2.2
    Multi-sig required

    Args:
        qube_id: Qube ID creating this block
        block_number: Block number
        previous_hash: Hash of previous block
        event_description: Description of collaborative event
        participants: List of participant Qube IDs
        shared_data_hash: Hash of shared outcome/data
        contribution_weights: Contribution % by each participant
        signatures: Dict of qube_id -> signature for multi-sig validation
        temporary: Whether this is a session block
        session_id: Session ID if temporary
    """
    block = Block(
        block_type=BlockType.COLLABORATIVE_MEMORY,
        block_number=block_number,
        qube_id=qube_id,
        content={
            "event_description": event_description,
            "participants": participants,
            "shared_data_hash": shared_data_hash,
            "contribution_weights": contribution_weights
        },
        encrypted=True,
        temporary=temporary,
        session_id=session_id,
        previous_hash=previous_hash
    )

    # Add signatures from all participants
    block_dict = block.to_dict()
    block_dict["signatures"] = signatures
    block_dict["multi_sig_valid"] = len(signatures) == len(participants)

    block.block_hash = block.compute_hash()
    return block


# =============================================================================
# SUMMARY BLOCK
# =============================================================================

def create_summary_block(
    qube_id: str,
    block_number: int,
    previous_hash: str,
    summarized_blocks: List[int],
    block_count: int,
    time_period: Dict[str, Any],
    summary_text: str,
    summary_type: str = "periodic",  # "periodic", "session", or "manual"
    key_events: Optional[List[Dict[str, Any]]] = None,
    sentiment_analysis: Optional[Dict[str, Any]] = None,
    topics_covered: Optional[List[str]] = None,
    relationships_affected: Optional[Dict[str, Dict[str, str]]] = None,
    archival_references: Optional[Dict[str, str]] = None,
    session_id: Optional[str] = None,
    participants: Optional[Dict[str, List[str]]] = None,
    actions_taken: Optional[List[Dict[str, Any]]] = None,
    key_insights: Optional[List[str]] = None,
    next_session_context: Optional[str] = None
) -> Block:
    """
    Create SUMMARY block

    From docs Section 2.2
    Can summarize any range of permanent blocks
    """
    content = {
        "summarized_blocks": summarized_blocks,
        "block_count": block_count,
        "time_period": time_period,
        "summary_type": summary_type,
        "summary_text": summary_text
    }

    # Optional fields
    if key_events:
        content["key_events"] = key_events
    if sentiment_analysis:
        content["sentiment_analysis"] = sentiment_analysis
    if topics_covered:
        content["topics_covered"] = topics_covered
    if relationships_affected:
        content["relationships_affected"] = relationships_affected
    if archival_references:
        content["archival_references"] = archival_references
    if session_id:
        content["session_id"] = session_id
    if participants:
        content["participants"] = participants
    if actions_taken:
        content["actions_taken"] = actions_taken
    if key_insights:
        content["key_insights"] = key_insights
    if next_session_context:
        content["next_session_context"] = next_session_context

    block = Block(
        block_type=BlockType.SUMMARY,
        qube_id=qube_id,
        block_number=block_number,
        content=content,
        encrypted=True,
        temporary=False,  # Summaries are always permanent
        previous_hash=previous_hash
    )

    block.block_hash = block.compute_hash()
    return block


def create_game_block(
    qube_id: str,
    block_number: int,
    previous_hash: str,
    game_id: str,
    game_type: str,
    white_player: Dict[str, Any],
    black_player: Dict[str, Any],
    result: str,
    termination: str,
    total_moves: int,
    pgn: str,
    duration_seconds: int,
    xp_earned: int,
    key_moments: Optional[List[Dict[str, Any]]] = None,
    chat_log: Optional[List[Dict[str, Any]]] = None
) -> Block:
    """
    Create GAME block for completed games

    From docs - Games section
    GAME blocks are permanent records of completed games.
    Similar to SUMMARY blocks, they capture the outcome of a game session.

    Args:
        qube_id: Qube identifier
        block_number: Block number in chain
        previous_hash: Hash of previous block (permanent only)
        game_id: Unique game identifier
        game_type: Type of game (e.g., "chess")
        white_player: {"id": "...", "type": "human|qube"}
        black_player: {"id": "...", "type": "human|qube"}
        result: Game result ("1-0", "0-1", "1/2-1/2", "*")
        termination: How game ended ("checkmate", "resignation", etc.)
        total_moves: Total number of moves played
        pgn: Complete game in PGN format
        duration_seconds: Game duration
        xp_earned: XP awarded for this game
        key_moments: Optional list of significant moves with reasoning
        chat_log: Optional in-game chat messages

    Returns:
        GAME block (permanent, never temporary, unencrypted for verification)
    """
    content = {
        "game_id": game_id,
        "game_type": game_type,
        "white_player": white_player,
        "black_player": black_player,
        "result": result,
        "termination": termination,
        "total_moves": total_moves,
        "pgn": pgn,
        "duration_seconds": duration_seconds,
        "xp_earned": xp_earned
    }

    # Optional fields
    if key_moments:
        content["key_moments"] = key_moments
    if chat_log:
        content["chat_log"] = chat_log

    block = Block(
        block_type=BlockType.GAME,
        qube_id=qube_id,
        block_number=block_number,
        content=content,
        encrypted=False,  # GAME blocks are PUBLIC - enables signature verification by third parties
        temporary=False,  # Games are always permanent
        previous_hash=previous_hash
    )

    block.block_hash = block.compute_hash()
    return block