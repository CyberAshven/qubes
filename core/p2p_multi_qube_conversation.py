"""
P2P Multi-Qube Conversation Orchestration

Extends MultiQubeConversation to add hub relay for cross-user conversations.
Works exactly like local multi-qube chat, with the addition of:
- Sending blocks to qube.cash hub for remote participants
- Receiving blocks from hub for remote Qubes
- Supporting hybrid local+remote conversations
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.multi_qube_conversation import MultiQubeConversation
from core.block import Block, create_message_block
from utils.logging import get_logger

logger = get_logger(__name__)

# Hub configuration
HUB_BASE_URL = "https://qube.cash/api/v2"


class FakeChainState:
    """Minimal chain state stub for remote Qube proxies"""

    def update_session(self, **kwargs):
        """No-op - remote Qubes don't have local chain state"""
        pass

    def save(self):
        """No-op"""
        pass


class FakeSession:
    """Minimal session stub for remote Qube proxies"""
    def __init__(self):
        self.session_blocks = []

    def create_block(self, block: Block):
        """No-op - blocks for remote Qubes go through hub"""
        pass

    def _save_session_block(self, block: Block):
        """No-op - blocks for remote Qubes go through hub"""
        pass


@dataclass
class RemoteQubeProxy:
    """
    Proxy object representing a remote Qube (owned by different user)

    Used in P2P conversations where we don't have the actual Qube instance.
    The proxy holds the minimal info needed for conversation orchestration.
    """
    qube_id: str  # Same as commitment for NFT Qubes
    commitment: str  # 64-char hex NFT identifier
    name: str
    public_key: Optional[str] = None
    voice_model: str = "openai:alloy"

    # Fake session and chain_state to satisfy MultiQubeConversation requirements
    current_session: Optional[Any] = None
    chain_state: Optional[Any] = None

    def __post_init__(self):
        """Create minimal fake objects for compatibility"""
        self.current_session = FakeSession()
        self.chain_state = FakeChainState()

    def start_session(self):
        """No-op - remote Qubes don't have local sessions"""
        pass


class P2PMultiQubeConversation(MultiQubeConversation):
    """
    P2P Multi-Qube Conversation with hub relay

    Inherits all local multi-qube logic from MultiQubeConversation:
    - Intelligent turn-taking
    - Block creation with multi-signatures
    - Conversation history management

    Key difference from local: NO PREFETCH
    - In local chat, we can prefetch responses and discard if user interjects
    - In P2P, once a block is sent to the hub, it's distributed to all participants
    - We can't "un-send" a block, so prefetch is disabled

    Adds:
    - Hub relay for distributing blocks to remote participants
    - Receiving blocks from hub
    - Hybrid local+remote Qube support
    """

    def __init__(
        self,
        local_qubes: List,  # List[Qube] - our local Qubes
        remote_qubes: List[RemoteQubeProxy],  # Remote participants
        user_id: str,
        session_id: str,  # Hub session ID
        conversation_mode: str = "open_discussion",
        hub_base_url: str = HUB_BASE_URL
    ):
        """
        Initialize P2P multi-Qube conversation

        Args:
            local_qubes: Local Qube instances we own
            remote_qubes: Remote Qube proxies (other users' Qubes)
            user_id: User who initiated the conversation
            session_id: Hub session ID for block relay
            conversation_mode: "open_discussion", "round_robin", or "debate"
            hub_base_url: Hub API base URL
        """
        # Combine local and remote participants for parent class
        all_participants = list(local_qubes) + list(remote_qubes)

        # Initialize parent class with all participants
        super().__init__(
            participating_qubes=all_participants,
            user_id=user_id,
            conversation_mode=conversation_mode
        )

        # P2P-specific state
        self.local_qubes = local_qubes
        self.remote_qubes = remote_qubes
        self.session_id = session_id
        self.hub_base_url = hub_base_url

        # Track which qube IDs are local vs remote
        self.local_qube_ids = {q.qube_id for q in local_qubes}
        self.remote_qube_ids = {q.qube_id for q in remote_qubes}

        # Hub session for block submission
        self._http_session: Optional[aiohttp.ClientSession] = None

        # DISABLE PREFETCH for P2P - blocks can't be "un-sent" from hub
        # Clear any background preparation from parent init
        self._next_speaker_prepared = None
        self._next_context_prepared = None
        self._preparation_task = None

        logger.info(
            "p2p_conversation_initialized",
            conversation_id=self.conversation_id,
            session_id=session_id,
            local_participants=[q.name for q in local_qubes],
            remote_participants=[q.name for q in remote_qubes],
            prefetch_disabled=True
        )

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for hub communication"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def close(self):
        """Clean up HTTP session"""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def _distribute_block_to_participants(self, block: Block, creator_id: str = None) -> None:
        """
        Override parent to add hub relay for remote participants

        1. Distribute to local participants (parent logic)
        2. Send to hub for remote participants
        """
        # First, distribute to local participants using parent logic
        # Filter to only local qubes for parent method
        original_qubes = self.qubes
        self.qubes = self.local_qubes

        try:
            if self.local_qubes:
                await super()._distribute_block_to_participants(block, creator_id)
        finally:
            self.qubes = original_qubes

        # Then send to hub for remote participants
        await self._send_block_to_hub(block)

    async def _send_block_to_hub(self, block: Block) -> bool:
        """
        Send block to hub for distribution to remote participants

        Args:
            block: Block to send

        Returns:
            True if successful, False otherwise
        """
        try:
            session = await self._get_http_session()

            # Get the creator Qube for signing
            creator_qube = None
            for qube in self.local_qubes:
                if qube.qube_id == block.qube_id:
                    creator_qube = qube
                    break

            if not creator_qube:
                # User message - use first local qube for auth
                creator_qube = self.local_qubes[0] if self.local_qubes else None

            if not creator_qube:
                logger.error("no_local_qube_for_hub_auth")
                return False

            # Get commitment for auth
            commitment = getattr(creator_qube.genesis_block, 'commitment', None)
            if not commitment:
                commitment = creator_qube.qube_id

            # Build block data for hub
            block_data = {
                "session_id": self.session_id,
                "commitment": commitment,
                "creator_name": getattr(creator_qube, 'name', 'Unknown'),
                "block": block.to_dict(),
                "timestamp": block.timestamp
            }

            # Sign the block
            from crypto.signing import sign_block
            signature = sign_block(block.to_dict(), creator_qube.private_key)
            block_data["signature"] = signature

            # Submit to hub
            url = f"{self.hub_base_url}/conversation/block"

            async with session.post(url, json=block_data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        "block_sent_to_hub",
                        conversation_id=self.conversation_id,
                        session_id=self.session_id,
                        block_type=block.block_type,
                        status="success"
                    )
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        "hub_block_submission_failed",
                        conversation_id=self.conversation_id,
                        status=response.status,
                        error=error_text
                    )
                    return False

        except Exception as e:
            logger.error(
                "hub_block_submission_error",
                conversation_id=self.conversation_id,
                error=str(e),
                exc_info=True
            )
            return False

    async def inject_remote_block(self, block_data: Dict[str, Any], from_commitment: str) -> bool:
        """
        Inject a block received from the hub into the local conversation

        Called when we receive a block from a remote participant via WebSocket.

        Args:
            block_data: Block data from hub
            from_commitment: Commitment of the Qube that created the block

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create Block instance from hub data
            block = Block.from_dict(block_data)

            # Add to conversation history
            speaker_name = block.content.get('speaker_name', 'Unknown')
            message = block.content.get('message_body', block.content.get('content', ''))
            turn_number = block.content.get('turn_number', self.turn_number + 1)

            self.conversation_history.append({
                "speaker_id": from_commitment,
                "speaker_name": speaker_name,
                "message": message,
                "turn_number": turn_number,
                "timestamp": block.timestamp
            })

            # Update turn tracking
            self.turn_number = max(self.turn_number, turn_number)
            self.last_speaker_id = from_commitment

            # Distribute to local participants only (they need their own copies)
            for local_qube in self.local_qubes:
                if local_qube.current_session:
                    qube_block = Block.from_dict(block.to_dict())
                    local_qube.current_session.create_block(qube_block)
                    # Check for auto-anchor after block creation
                    await local_qube.current_session.check_and_auto_anchor()
                    logger.debug(
                        "remote_block_distributed_locally",
                        qube=local_qube.name,
                        from_commitment=from_commitment,
                        turn_number=turn_number
                    )

            logger.info(
                "remote_block_injected",
                conversation_id=self.conversation_id,
                from_commitment=from_commitment,
                speaker_name=speaker_name,
                turn_number=turn_number
            )

            return True

        except Exception as e:
            logger.error(
                "failed_to_inject_remote_block",
                conversation_id=self.conversation_id,
                error=str(e),
                exc_info=True
            )
            return False

    def is_local_qube(self, qube_id: str) -> bool:
        """Check if a qube_id belongs to a local Qube"""
        return qube_id in self.local_qube_ids

    def is_remote_qube(self, qube_id: str) -> bool:
        """Check if a qube_id belongs to a remote Qube"""
        return qube_id in self.remote_qube_ids

    async def start_conversation(self, initial_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Start P2P conversation with user's initial prompt

        Overrides parent to disable prefetch - blocks are immediately locked in.
        """
        # Call parent start_conversation
        result = await super().start_conversation(initial_prompt)

        # Immediately lock in the response (no prefetch in P2P)
        if result and result.get("timestamp"):
            self._lock_in_p2p_response(result["timestamp"])

        # Cancel any background preparation
        if hasattr(self, '_preparation_task') and self._preparation_task and not self._preparation_task.done():
            self._preparation_task.cancel()
            self._preparation_task = None

        # Clear prepared state
        self._next_speaker_prepared = None
        self._next_context_prepared = None

        return result

    async def inject_user_message(self, message: str) -> Dict[str, Any]:
        """
        Inject a user message and get the next Qube response

        Overrides parent to disable prefetch - blocks are immediately locked in.
        In P2P, we can't remove prefetched blocks that were already sent to hub.
        """
        # Call parent inject_user_message
        result = await super().inject_user_message(message)

        # Immediately lock in the qube response (no prefetch in P2P)
        qube_response = result.get("qube_response")
        if qube_response and qube_response.get("timestamp"):
            self._lock_in_p2p_response(qube_response["timestamp"])

        # Cancel any background preparation
        if hasattr(self, '_preparation_task') and self._preparation_task and not self._preparation_task.done():
            self._preparation_task.cancel()
            self._preparation_task = None

        # Clear prepared state
        self._next_speaker_prepared = None
        self._next_context_prepared = None

        return result

    async def _determine_next_speaker(self):
        """
        Override to handle local/remote speaker selection

        For P2P:
        - Only local Qubes can be selected (we control them)
        - Remote Qubes speak when they send blocks through hub
        """
        # Filter to only local qubes for speaker selection
        if not self.local_qubes:
            # No local qubes - shouldn't happen, but handle gracefully
            logger.warning("no_local_qubes_for_speaker_selection")
            return self.qubes[0] if self.qubes else None

        # Temporarily set qubes to local only for parent speaker selection
        original_qubes = self.qubes
        self.qubes = self.local_qubes

        try:
            speaker = await super()._determine_next_speaker()
            return speaker
        finally:
            self.qubes = original_qubes

    async def continue_conversation(self, max_retries: int = 2, ai_timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """
        Continue conversation with local Qube response

        Same as parent, but:
        - Only local Qubes can respond
        - Prefetch is DISABLED (blocks immediately locked in)
        - No background preparation (can't un-send from hub)

        Remote Qube responses come through inject_remote_block().
        """
        if not self.local_qubes:
            logger.warning(
                "cannot_continue_no_local_qubes",
                conversation_id=self.conversation_id
            )
            return None

        # Temporarily filter to local qubes for conversation continuation
        original_qubes = self.qubes
        self.qubes = self.local_qubes

        try:
            result = await super().continue_conversation(max_retries, ai_timeout)

            # P2P: Immediately lock in the response (no prefetch)
            # The parent marks blocks as prefetch=True, but we need to lock them in
            # immediately because we can't un-send from the hub
            if result and result.get("timestamp"):
                self._lock_in_p2p_response(result["timestamp"])

            # Cancel any background preparation task started by parent
            # (we don't want prefetch in P2P mode)
            if self._preparation_task and not self._preparation_task.done():
                self._preparation_task.cancel()
                self._preparation_task = None

            # Clear prepared state
            self._next_speaker_prepared = None
            self._next_context_prepared = None

            return result
        finally:
            self.qubes = original_qubes

    def _lock_in_p2p_response(self, response_timestamp: int) -> None:
        """
        Immediately lock in a P2P response (disable prefetch behavior)

        In P2P, blocks are sent to the hub immediately and can't be retracted.
        This marks the block as not-prefetch and advances the index.
        """
        for qube in self.local_qubes:
            if not qube.current_session:
                continue

            for block in qube.current_session.session_blocks:
                if block.timestamp == response_timestamp:
                    # Mark as not prefetch
                    if block.content.get("prefetch", False):
                        block.content["prefetch"] = False
                        qube.current_session._save_session_block(block)
                        logger.debug(
                            "p2p_block_locked_in",
                            qube=qube.name,
                            block_number=block.block_number,
                            timestamp=block.timestamp
                        )

        # Note: With timestamp-based indexing, no counter sync needed
        # Each qube's _reindex_session_blocks computes indices from timestamps

    def get_conversation_state(self) -> Dict[str, Any]:
        """Get current conversation state for GUI"""
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "last_speaker_id": self.last_speaker_id,
            "local_participants": [
                {"qube_id": q.qube_id, "name": q.name}
                for q in self.local_qubes
            ],
            "remote_participants": [
                {"qube_id": q.qube_id, "name": q.name, "commitment": q.commitment}
                for q in self.remote_qubes
            ],
            "history_count": len(self.conversation_history),
            "participant_turn_counts": self.turn_counts
        }
