"""
Multi-Qube Conversation Orchestration

Manages group conversations between multiple Qubes with:
- Intelligent turn-taking
- Shared conversation context
- Multi-signature blocks (all participants sign)
- TTS-aware pacing
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from core.block import Block, create_message_block
# Import signing functions in methods to avoid circular import
from utils.logging import get_logger

logger = get_logger(__name__)


class MultiQubeConversation:
    """
    Orchestrates multi-Qube conversations with intelligent turn-taking

    Features:
    - All participants have full conversation context
    - Each MESSAGE block is signed by ALL participants (multi-sig)
    - AI-powered speaker selection (or simple round-robin)
    - TTS-aware pacing (next speaker selected during TTS playback)
    """

    def __init__(
        self,
        participating_qubes: List,  # List[Qube] but avoid circular import
        user_id: str,
        conversation_mode: str = "open_discussion"
    ):
        """
        Initialize multi-Qube conversation

        Args:
            participating_qubes: List of Qube instances participating
            user_id: User who initiated the conversation
            conversation_mode: "open_discussion", "round_robin", or "debate"
        """
        self.qubes = participating_qubes
        self.user_id = user_id
        self.conversation_id = str(uuid.uuid4())
        self.conversation_mode = conversation_mode

        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.turn_number = 0
        self.last_speaker_id: Optional[str] = None
        self.current_speaker_index = 0  # For round-robin mode

        # Participant info (includes user + all qubes)
        self.participant_ids = [self.user_id] + [q.qube_id for q in self.qubes]
        self.participant_names = {q.qube_id: q.name for q in self.qubes}
        self.participant_names[self.user_id] = self.user_id  # Add user to names map
        self.turn_counts = {q.qube_id: 0 for q in self.qubes}

        # Background preparation (Phase 2 optimization)
        self._next_speaker_prepared: Optional[Any] = None
        self._next_context_prepared: Optional[str] = None
        self._preparation_task: Optional[asyncio.Task] = None
        self._last_prepared_response_timestamp: Optional[int] = None  # Track prefetched responses

        # Deduplication tracking
        self._processing_turn: bool = False  # Prevent concurrent turn processing

        logger.info(
            "multi_qube_conversation_started",
            conversation_id=self.conversation_id,
            participants=[q.qube_id for q in self.qubes],
            mode=conversation_mode,
            user_id=user_id
        )

    def _next_turn_number(self) -> int:
        """Get the next turn number, incrementing the counter.

        Each block (MESSAGE or ACTION) gets its own unique turn number.
        """
        self.turn_number += 1
        return self.turn_number

    async def start_conversation(self, initial_prompt: str) -> Dict[str, Any]:
        """
        Start the conversation with user's initial prompt

        Args:
            initial_prompt: User's opening message

        Returns:
            First response dict with speaker info and message
        """
        # Ensure all participants have active sessions
        for qube in self.qubes:
            if not qube.current_session:
                qube.start_session()
                logger.info(
                    "session_started_for_participant",
                    qube_id=qube.qube_id,
                    conversation_id=self.conversation_id
                )

        # Create user's MESSAGE block (signed by user, witnessed by all Qubes)
        user_message_block = self._create_user_message_block(initial_prompt)

        # Add to first qube's session first (assigns block number)
        first_qube = self.qubes[0]
        if first_qube.current_session:
            first_qube.current_session.create_block(user_message_block)
            # Check for auto-anchor after block creation
            await first_qube.current_session.check_and_auto_anchor(await_completion=False)
            logger.debug(
                "initial_message_created",
                block_number=user_message_block.block_number,
                qube=first_qube.name
            )

        # Distribute to all participants (including first qube, who will just update signatures)
        await self._distribute_block_to_participants(user_message_block, creator_id=first_qube.qube_id)

        # Note: With timestamp-based indexing, all qubes compute indices from timestamps
        # No need to sync next_negative_index - each qube's _reindex_session_blocks handles it

        # Record user-to-qube relationships for all participants
        try:
            for qube in self.qubes:
                # Each Qube records receiving a message from the user
                qube.relationships.record_message(
                    entity_id=self.user_id,
                    is_outgoing=False,  # User sent message, qube received
                    auto_create=True
                )

                # Check for relationship progression
                rel = qube.relationships.get_relationship(self.user_id)
                if rel:
                    progressed = qube.relationships.progression_manager.check_and_progress(
                        rel,
                        qube_id=qube.qube_id
                    )
                    if progressed:
                        logger.info(
                            "user_qube_relationship_progressed",
                            conversation_id=self.conversation_id,
                            qube=qube.name,
                            user=self.user_id,
                            new_status=rel.relationship_status
                        )

            logger.debug(f"✅ Recorded user-qube relationship interactions for {len(self.qubes)} participants")
        except Exception as e:
            logger.warning(f"Failed to record user-qube relationships: {e}")

        # Add to conversation history
        self.conversation_history.append({
            "speaker_id": self.user_id,
            "speaker_name": self.user_id,  # Use actual user_id instead of generic "User"
            "message": initial_prompt,
            "turn_number": 0,
            "timestamp": user_message_block.timestamp
        })

        logger.info(
            "conversation_started_with_prompt",
            conversation_id=self.conversation_id,
            prompt_length=len(initial_prompt)
        )

        # Get first Qube response
        return await self.continue_conversation()

    def _remove_phantom_blocks(self):
        """
        Remove phantom blocks - qube responses that have duplicate block numbers with user interjections

        This happens when a user interjects while a qube is processing. Both end up with the same
        block number. The user's block should win, qube's block should be removed.

        This method reads from disk to catch phantom blocks that were created in other processes.
        """
        from pathlib import Path
        import json

        for qube in self.qubes:
            if not qube.current_session:
                continue

            # Read all block files from disk for this qube
            session_dir = Path(qube.data_dir) / "blocks" / "session"
            if not session_dir.exists():
                continue

            # Group blocks by block number
            block_numbers = {}
            for block_file in session_dir.glob("*_MESSAGE_*.json"):
                try:
                    with open(block_file, 'r') as f:
                        block_data = json.load(f)
                        block_num = block_data.get("block_number")
                        if block_num is None:
                            continue

                        if block_num not in block_numbers:
                            block_numbers[block_num] = []
                        block_numbers[block_num].append({
                            "file": block_file,
                            "data": block_data,
                            "timestamp": block_data.get("timestamp"),
                            "qube_id": block_data.get("qube_id")
                        })
                except Exception as e:
                    logger.error(
                        "error_reading_block_during_phantom_cleanup",
                        file=str(block_file),
                        error=str(e)
                    )
                    continue

            # For each block number with duplicates, keep user block, remove qube blocks
            for block_num, blocks in block_numbers.items():
                if len(blocks) <= 1:
                    continue

                # Find user block and qube blocks
                user_block = None
                qube_blocks = []

                for block_info in blocks:
                    if block_info["qube_id"] == self.user_id:
                        user_block = block_info
                    else:
                        qube_blocks.append(block_info)

                # If we have both user and qube blocks with same number, remove qube blocks
                if user_block and qube_blocks:
                    for qube_block_info in qube_blocks:
                        logger.warning(
                            "removing_phantom_block",
                            qube=qube.name,
                            block_number=block_num,
                            qube_id=qube_block_info["qube_id"],
                            user_timestamp=user_block["timestamp"],
                            qube_timestamp=qube_block_info["timestamp"],
                            file=qube_block_info["file"].name
                        )

                        # Delete file
                        try:
                            qube_block_info["file"].unlink()
                            logger.info(
                                "deleted_phantom_block_file",
                                qube=qube.name,
                                file=qube_block_info["file"].name
                            )
                        except Exception as e:
                            logger.error(
                                "failed_to_delete_phantom_block",
                                file=str(qube_block_info["file"]),
                                error=str(e)
                            )

                        # Also remove from in-memory session if present
                        for block in list(qube.current_session.session_blocks):
                            if (block.block_number == block_num and
                                block.timestamp == qube_block_info["timestamp"]):
                                qube.current_session.session_blocks.remove(block)
                                logger.debug(
                                    "removed_phantom_from_memory",
                                    block_number=block_num,
                                    timestamp=qube_block_info["timestamp"]
                                )

    async def continue_conversation(self, max_retries: int = 2, ai_timeout: float = 60.0, skip_tools: bool = False) -> Dict[str, Any]:
        """
        Generate next turn in the conversation with error handling and retry logic

        Optimizations:
        - Uses background-prepared speaker if available (Phase 2)
        - Returns progress status indicators (Phase 1)
        - Starts background preparation for next turn after returning

        Error Handling:
        - Retries AI generation on timeout/failure
        - Falls back to non-prepared speaker if preparation fails
        - Validates session state before proceeding
        - Gracefully handles stuck conversation states
        - Prevents duplicate turn processing

        Args:
            max_retries: Maximum number of retries for AI generation (default: 2)
            ai_timeout: Timeout in seconds for AI generation (default: 60.0)
            skip_tools: If True, disable tool calling for this turn (default: False)

        Returns:
            Response dict with speaker info, message, voice model, and status

        Raises:
            RuntimeError: If conversation is in invalid state
            asyncio.TimeoutError: If AI generation times out after all retries
        """
        # Prevent duplicate/concurrent processing of the same turn
        if self._processing_turn:
            logger.warning(
                "duplicate_continue_conversation_call_blocked",
                conversation_id=self.conversation_id,
                turn_number=self.turn_number
            )
            return None

        self._processing_turn = True

        try:
            return await self._continue_conversation_impl(max_retries, ai_timeout, skip_tools)
        finally:
            self._processing_turn = False

    async def _continue_conversation_impl(self, max_retries: int = 2, ai_timeout: float = 60.0, skip_tools: bool = False) -> Dict[str, Any]:
        """Internal implementation of continue_conversation"""
        import time

        turn_start = time.time()
        # NOTE: turn_number is now incremented per-block by _next_turn_number()

        # CLEANUP: Remove any phantom blocks (duplicate block numbers) from previous race conditions
        self._remove_phantom_blocks()

        # VALIDATION: Check conversation state
        if not self.qubes:
            raise RuntimeError(f"No participants in conversation {self.conversation_id}")

        for qube in self.qubes:
            if not qube.current_session:
                logger.warning(
                    "participant_missing_session",
                    conversation_id=self.conversation_id,
                    qube_id=qube.qube_id,
                    action="starting_session"
                )
                qube.start_session()

        # PHASE 2: Use pre-prepared speaker if available
        next_speaker = None
        conversation_context = None

        using_prefetch = False
        if self._next_speaker_prepared is not None and self._next_context_prepared is not None:
            # Validate prepared speaker is still valid AND not the same as last speaker
            # The second check prevents back-to-back speaking if background prep ran before
            # last_speaker_id was updated
            prepared_id = getattr(self._next_speaker_prepared, 'qube_id', None)
            if (self._next_speaker_prepared in self.qubes and
                prepared_id != self.last_speaker_id):
                next_speaker = self._next_speaker_prepared
                conversation_context = self._next_context_prepared
                using_prefetch = True

                logger.info(
                    "using_prepared_speaker",
                    conversation_id=self.conversation_id,
                    speaker_id=next_speaker.qube_id,
                    speaker_name=next_speaker.name,
                    turn_number=self.turn_number
                )
            else:
                # Either speaker not in qubes, or they're the last speaker (would cause back-to-back)
                logger.warning(
                    "prepared_speaker_invalid",
                    conversation_id=self.conversation_id,
                    prepared_speaker_id=prepared_id,
                    prepared_speaker_name=getattr(self._next_speaker_prepared, 'name', 'unknown'),
                    last_speaker_id=self.last_speaker_id,
                    reason="same_as_last_speaker" if prepared_id == self.last_speaker_id else "not_in_qubes"
                )

            # Always clear prepared state after checking (whether used or not)
            # This ensures we don't keep stale prep that prevents new prep from starting
            self._next_speaker_prepared = None
            self._next_context_prepared = None

        # Fallback: determine speaker now if preparation failed or was invalid
        if next_speaker is None:
            speaker_start = time.time()
            next_speaker = await self._determine_next_speaker()
            conversation_context = self._build_conversation_context()

            speaker_time_ms = (time.time() - speaker_start) * 1000
            logger.info(
                "next_speaker_selected",
                conversation_id=self.conversation_id,
                speaker_id=next_speaker.qube_id,
                speaker_name=next_speaker.name,
                turn_number=self.turn_number,
                selection_time_ms=speaker_time_ms
            )

        # VALIDATION: Ensure we're using the correct speaker
        logger.info(
            "turn_speaker_validation",
            conversation_id=self.conversation_id,
            turn_number=self.turn_number,
            speaker_id=next_speaker.qube_id,
            speaker_name=next_speaker.name,
            was_prepared=self._next_speaker_prepared is not None
        )

        # PHASE 1: Generate AI response with retry logic and timeout
        response = None
        ai_time_ms = 0
        last_error = None

        # Set callable for unique turn numbers per block
        if next_speaker.current_session:
            next_speaker.current_session.get_next_turn_number = self._next_turn_number

        for attempt in range(max_retries + 1):
            try:
                ai_start = time.time()
                logger.info(
                    "ai_generation_attempt",
                    conversation_id=self.conversation_id,
                    speaker=next_speaker.name,
                    speaker_id=next_speaker.qube_id,
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1
                )

                # Use asyncio.wait_for to enforce timeout
                # If skip_tools=True, limit to 1 iteration (allows one tool call but not many)
                response = await asyncio.wait_for(
                    next_speaker.reasoner.process_input(
                        input_message=self._build_turn_prompt(next_speaker, conversation_context),
                        sender_id=self.user_id,
                        temperature=0.7,
                        max_iterations=1 if skip_tools else 10
                    ),
                    timeout=ai_timeout
                )

                ai_time_ms = (time.time() - ai_start) * 1000

                logger.info(
                    "ai_generation_complete",
                    conversation_id=self.conversation_id,
                    speaker=next_speaker.name,
                    generation_time_ms=ai_time_ms,
                    response_length=len(response),
                    attempt=attempt + 1
                )

                # Success - break retry loop
                break

            except asyncio.TimeoutError as e:
                last_error = e
                ai_time_ms = (time.time() - ai_start) * 1000
                logger.error(
                    "ai_generation_timeout",
                    conversation_id=self.conversation_id,
                    speaker=next_speaker.name,
                    timeout_seconds=ai_timeout,
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1
                )

                if attempt < max_retries:
                    logger.info("retrying_ai_generation", retry_in_seconds=1)
                    await asyncio.sleep(1)  # Brief pause before retry
                else:
                    logger.error("ai_generation_failed_all_retries", conversation_id=self.conversation_id)
                    raise RuntimeError(
                        f"AI generation timed out after {max_retries + 1} attempts "
                        f"(timeout: {ai_timeout}s per attempt)"
                    ) from e

            except Exception as e:
                last_error = e
                ai_time_ms = (time.time() - ai_start) * 1000
                logger.error(
                    "ai_generation_error",
                    conversation_id=self.conversation_id,
                    speaker=next_speaker.name,
                    error=str(e),
                    attempt=attempt + 1,
                    exc_info=True
                )

                if attempt < max_retries:
                    logger.info("retrying_ai_generation", retry_in_seconds=1)
                    await asyncio.sleep(1)
                else:
                    logger.error("ai_generation_failed_all_retries", conversation_id=self.conversation_id)
                    raise RuntimeError(
                        f"AI generation failed after {max_retries + 1} attempts: {str(e)}"
                    ) from e

        # Validate response
        if not response or not response.strip():
            logger.error(
                "empty_ai_response",
                conversation_id=self.conversation_id,
                speaker=next_speaker.name
            )
            raise RuntimeError(f"AI generated empty response for speaker {next_speaker.name}")

        # Create MESSAGE block for this response with token usage data
        try:
            # Get token usage from the reasoner
            usage = next_speaker.reasoner.last_usage if hasattr(next_speaker, 'reasoner') else None
            model_used = next_speaker.reasoner.last_model_used if hasattr(next_speaker, 'reasoner') else None

            # BEFORE creating the block, check if user interjection already took this block number
            # Read from disk since inject_user_message() runs in a separate process
            from pathlib import Path
            import json

            # With timestamp-based indexing, compute next expected number from current block count
            next_block_number = -(len(next_speaker.current_session.session_blocks) + 1)
            user_block_exists = False

            logger.debug(
                "checking_for_user_interjection_before_creation",
                conversation_id=self.conversation_id,
                next_block_number=next_block_number,
                next_speaker=next_speaker.name
            )

            # Check all participants' session folders
            files_checked = 0
            for qube in self.qubes:
                session_dir = Path(qube.data_dir) / "blocks" / "session"
                if session_dir.exists():
                    matching_files = list(session_dir.glob(f"{next_block_number}_MESSAGE_*.json"))
                    files_checked += len(matching_files)

                    logger.debug(
                        "checking_qube_session_folder",
                        qube=qube.name,
                        session_dir=str(session_dir),
                        matching_files=len(matching_files)
                    )

                    for block_file in matching_files:
                        try:
                            with open(block_file, 'r') as f:
                                block_data = json.load(f)
                                block_qube_id = block_data.get("qube_id")

                                logger.debug(
                                    "found_block_file",
                                    file=block_file.name,
                                    qube_id=block_qube_id,
                                    is_user=block_qube_id == self.user_id
                                )

                                if block_qube_id == self.user_id:
                                    user_block_exists = True
                                    logger.warning(
                                        "user_interjection_detected_before_creation",
                                        block_number=next_block_number,
                                        user_timestamp=block_data.get("timestamp"),
                                        file=block_file.name,
                                        action="aborting_qube_response"
                                    )
                                    break
                        except Exception as e:
                            logger.error(
                                "error_reading_block_file",
                                file=str(block_file),
                                error=str(e),
                                error_type=type(e).__name__
                            )
                if user_block_exists:
                    break

            logger.debug(
                "pre_creation_check_complete",
                files_checked=files_checked,
                user_block_exists=user_block_exists
            )

            # If user block exists, abort this response completely
            if user_block_exists:
                logger.info(
                    "aborting_response_due_to_user_interjection",
                    conversation_id=self.conversation_id,
                    block_number=next_block_number,
                    next_speaker=next_speaker.name
                )
                return None  # Signal to GUI that this response was aborted

            response_block = await self._create_qube_message_block(
                speaker=next_speaker,
                message=response,
                usage=usage,
                model_used=model_used
            )

            # Mark this new response as prefetch=true
            # Will be marked as false when GUI calls lock_in_response()
            response_block.content["prefetch"] = True

            # Add to speaker's session FIRST (updates their chain_state)
            # This reindexes all session blocks by timestamp
            next_speaker.current_session.create_block(response_block)
            # Check for auto-anchor after block creation
            await next_speaker.current_session.check_and_auto_anchor(await_completion=False)

        except Exception as e:
            logger.error(
                "block_creation_failed",
                conversation_id=self.conversation_id,
                speaker=next_speaker.name,
                error=str(e),
                exc_info=True
            )
            raise RuntimeError(f"Failed to create message block: {str(e)}") from e

        # PHASE 1: Distribute to participants (now parallelized) with error handling
        dist_start = time.time()
        try:
            await self._distribute_block_to_participants(response_block, creator_id=next_speaker.qube_id)

            # NOTE: ACTION blocks are NOT distributed to other participants
            # They stay local to the qube that executed them (only signed by that qube)
            # Only MESSAGE blocks are distributed and signed by all participants

            dist_time_ms = (time.time() - dist_start) * 1000

            logger.info(
                "block_distribution_complete",
                conversation_id=self.conversation_id,
                distribution_time_ms=dist_time_ms,
                participants=len(self.qubes)
            )
        except Exception as e:
            logger.error(
                "block_distribution_failed",
                conversation_id=self.conversation_id,
                error=str(e),
                exc_info=True
            )
            # Don't fail the entire turn - log and continue
            dist_time_ms = (time.time() - dist_start) * 1000
            logger.warning(
                "continuing_despite_distribution_error",
                conversation_id=self.conversation_id
            )

        # Add to conversation history
        self.conversation_history.append({
            "speaker_id": next_speaker.qube_id,
            "speaker_name": next_speaker.name,
            "message": response,
            "turn_number": self.turn_number,
            "timestamp": response_block.timestamp
        })

        # Track this response for next iteration
        self._last_prepared_response_timestamp = response_block.timestamp

        # Update state
        self.last_speaker_id = next_speaker.qube_id
        self.turn_counts[next_speaker.qube_id] += 1

        # Record relationships between all participants
        try:
            for qube in self.qubes:
                for other_qube in self.qubes:
                    if qube.qube_id != other_qube.qube_id:
                        # Ensure relationship exists with entity_name populated
                        rel = qube.relationships.get_relationship(other_qube.qube_id)
                        if not rel:
                            # Create relationship with entity_name for name-based lookup
                            rel = qube.relationships.create_relationship(
                                entity_id=other_qube.qube_id,
                                entity_type="qube",
                                entity_name=other_qube.name,  # Store name for search
                                has_met=True
                            )
                        elif not rel.entity_name:
                            # Update existing relationship to add entity_name if missing
                            rel.entity_name = other_qube.name
                            qube.relationships.storage.update_relationship(rel)

                        # Each Qube records message with every other Qube
                        is_outgoing = (qube == next_speaker)  # True if this qube sent the message

                        qube.relationships.record_message(
                            entity_id=other_qube.qube_id,
                            is_outgoing=is_outgoing,
                            auto_create=False  # Already created above
                        )

                        # Check for progression
                        rel = qube.relationships.get_relationship(other_qube.qube_id)
                        if rel:
                            progressed = qube.relationships.progression_manager.check_and_progress(
                                rel,
                                qube_id=qube.qube_id
                            )

                            if progressed:
                                logger.info(
                                    "multi_qube_relationship_progressed",
                                    conversation_id=self.conversation_id,
                                    qube_from=qube.name,
                                    qube_to=other_qube.name,
                                    new_status=rel.relationship_status
                                )

            logger.debug(f"✅ Recorded multi-qube relationship interactions for {len(self.qubes)} participants")
        except Exception as e:
            logger.warning(f"Failed to record multi-qube relationships: {e}")
            # Don't fail the conversation - just log warning

        total_time_ms = (time.time() - turn_start) * 1000
        logger.info(
            "conversation_turn_complete",
            conversation_id=self.conversation_id,
            speaker=next_speaker.name,
            turn_number=self.turn_number,
            total_time_ms=total_time_ms,
            ai_time_ms=ai_time_ms,
            dist_time_ms=dist_time_ms
        )

        # PHASE 2: Start background preparation for next turn
        # Always cancel and restart prep task to ensure fresh prep for next turn
        if self._preparation_task:
            if not self._preparation_task.done():
                logger.info(
                    "canceling_previous_preparation_task",
                    conversation_id=self.conversation_id
                )
                self._preparation_task.cancel()
            # Always start new task even if old one was done
            self._preparation_task = asyncio.create_task(self._prepare_next_turn())
        else:
            # No existing task, start fresh
            self._preparation_task = asyncio.create_task(self._prepare_next_turn())

        # PHASE 1: Return response with progress status
        return {
            "speaker_id": next_speaker.qube_id,
            "speaker_name": next_speaker.name,
            "message": response,
            "voice_model": getattr(next_speaker.genesis_block, 'voice_model', 'openai:alloy'),
            "turn_number": self.turn_number,
            "conversation_id": self.conversation_id,
            "timestamp": response_block.timestamp,  # GUI needs this to call lock_in_response()
            "block_number": response_block.block_number,  # GUI needs this for tool call matching
            "is_final": False,
            # Progress indicators for GUI
            "status": "complete",
            "timing": {
                "total_ms": total_time_ms,
                "ai_generation_ms": ai_time_ms,
                "distribution_ms": dist_time_ms
            }
        }

    def lock_in_response(self, response_timestamp: int) -> None:
        """
        Lock in a response as "spoken" by marking it as no longer a prefetch.

        This should be called by the GUI when it BEGINS SPEAKING a response.
        It marks the block (and any associated ACTION blocks from the same turn)
        as prefetch=false for all participants.

        Note: With timestamp-based indexing, no counter sync is needed.

        Args:
            response_timestamp: The timestamp of the response block to lock in
        """
        logger.info(
            "locking_in_response",
            conversation_id=self.conversation_id,
            response_timestamp=response_timestamp
        )

        locked_count = 0
        locked_block_numbers = set()

        for qube in self.qubes:
            if not qube.current_session:
                continue

            for block in qube.current_session.session_blocks:
                if block.timestamp == response_timestamp and block.content.get("prefetch", False) is True:
                    block.content["prefetch"] = False
                    qube.current_session._save_session_block(block)
                    locked_block_numbers.add(block.block_number)
                    logger.info(
                        "locked_in_block",
                        qube=qube.name,
                        block_number=block.block_number,
                        block_type=block.block_type,
                        timestamp=block.timestamp
                    )
                    locked_count += 1

        logger.info(
            "response_locked_in",
            conversation_id=self.conversation_id,
            blocks_locked=locked_count
        )

    async def inject_user_message(self, user_message: str) -> Dict[str, Any]:
        """
        Inject a user message into an active conversation

        This allows the user to participate in the conversation at any time,
        interrupting the normal Qube turn-taking flow.

        Args:
            user_message: The user's message to inject

        Returns:
            Dict containing the user message info and the next Qube's response
        """
        logger.info(
            "injecting_user_message",
            conversation_id=self.conversation_id,
            current_turn=self.turn_number,
            message_length=len(user_message)
        )

        # Cancel any running background preparation task FIRST
        # This prevents a race condition where the task completes and overwrites
        # the prefetch variables after we clear them
        if self._preparation_task and not self._preparation_task.done():
            self._preparation_task.cancel()
            logger.info(
                "canceled_preparation_task_during_user_injection",
                conversation_id=self.conversation_id
            )

        # Remove ALL prefetched blocks (blocks with "prefetch": true)
        from pathlib import Path

        prefetch_count = 0
        removed_timestamps = set()
        all_removed_block_numbers = set()  # Track all removed block numbers across all qubes

        for qube in self.qubes:
            if not qube.current_session:
                continue

            # Find all prefetched blocks (iterate backwards to safely remove)
            blocks_to_remove = []

            for i, block in enumerate(qube.current_session.session_blocks):
                # Only remove prefetched MESSAGE blocks (not ACTION blocks or user messages)
                if (block.content.get("prefetch", False) is True and
                    block.qube_id != self.user_id and
                    block.block_type == "MESSAGE"):
                    blocks_to_remove.append((i, block))
                    removed_timestamps.add(block.timestamp)
                    all_removed_block_numbers.add(block.block_number)

            # Remove prefetched blocks
            for i, block in reversed(blocks_to_remove):
                # Remove from session
                qube.current_session.session_blocks.pop(i)

                # Delete the saved block file
                block_filename = f"{block.block_number}_{block.block_type}_{block.timestamp}.json"
                block_path = Path(qube.data_dir) / "blocks" / "session" / block_filename
                if block_path.exists():
                    block_path.unlink()
                    logger.debug("deleted_prefetch_block_file", qube=qube.name, file=block_filename)

                logger.info(
                    "removed_prefetch_block_from_qube",
                    qube=qube.name,
                    block_number=block.block_number,
                    timestamp=block.timestamp
                )
                prefetch_count += 1

            # Update chain_state with current block count
            if blocks_to_remove:
                qube.chain_state.update_session(
                    session_block_count=len(qube.current_session.session_blocks)
                )

        # Remove prefetched entries from conversation_history
        self.conversation_history = [
            entry for entry in self.conversation_history
            if entry.get("timestamp") not in removed_timestamps
        ]

        logger.info(
            "prefetch_cleanup_complete",
            conversation_id=self.conversation_id,
            prefetch_blocks_removed=prefetch_count
        )

        # Clear prefetch tracking variables
        self._next_speaker_prepared = None
        self._next_context_prepared = None
        self._last_prepared_response_timestamp = None

        # Create user MESSAGE block with unique turn number
        user_block = self._create_user_message_block(user_message)
        user_turn = self._next_turn_number()
        user_block.content["turn_number"] = user_turn

        # If we removed prefetch blocks, use the minimum removed block number for the user message
        # This ensures the user's message replaces the prefetch at the same block number
        if all_removed_block_numbers:
            min_removed = min(all_removed_block_numbers)
            user_block.block_number = min_removed
            logger.info(
                "user_message_replacing_prefetch",
                removed_prefetch_blocks=sorted(all_removed_block_numbers),
                user_block_number=min_removed
            )
        else:
            # No prefetch blocks removed, assign normally from first qube
            first_qube = self.qubes[0]
            if first_qube.current_session:
                first_qube.current_session.create_block(user_block)
                # Check for auto-anchor after block creation
                await first_qube.current_session.check_and_auto_anchor(await_completion=False)
                logger.debug(
                    "user_message_created",
                    block_number=user_block.block_number,
                    qube=first_qube.name
                )

        # Distribute to all participants
        # If we replaced a prefetch, distribute without creator_id (all qubes need the block added)
        if all_removed_block_numbers:
            await self._distribute_block_to_participants(user_block)
        else:
            # Normal case - first qube already has it
            await self._distribute_block_to_participants(user_block, creator_id=self.qubes[0].qube_id)

        # Note: With timestamp-based indexing, no counter sync needed
        # Each qube's _reindex_session_blocks computes indices from timestamps

        # Record user-to-qube relationships for all participants
        try:
            for qube in self.qubes:
                # Each Qube records receiving a message from the user
                qube.relationships.record_message(
                    entity_id=self.user_id,
                    is_outgoing=False,  # User sent message, qube received
                    auto_create=True
                )

                # Check for relationship progression
                rel = qube.relationships.get_relationship(self.user_id)
                if rel:
                    progressed = qube.relationships.progression_manager.check_and_progress(
                        rel,
                        qube_id=qube.qube_id
                    )
                    if progressed:
                        logger.info(
                            "user_qube_relationship_progressed",
                            conversation_id=self.conversation_id,
                            qube=qube.name,
                            user=self.user_id,
                            new_status=rel.relationship_status
                        )

            logger.debug(f"✅ Recorded user-qube relationship interactions for {len(self.qubes)} participants")
        except Exception as e:
            logger.warning(f"Failed to record user-qube relationships: {e}")

        # Add to conversation history
        self.conversation_history.append({
            "speaker_id": self.user_id,
            "speaker_name": self.user_id,  # Use actual user_id instead of generic "User"
            "message": user_message,
            "turn_number": user_turn,
            "timestamp": user_block.timestamp
        })

        logger.info(
            "user_message_injected",
            conversation_id=self.conversation_id,
            turn_number=user_turn
        )

        # Get next Qube response (they respond to the user's message)
        next_response = await self.continue_conversation()

        return {
            "user_message": {
                "speaker_id": self.user_id,
                "speaker_name": self.user_id,  # Use actual user_id instead of generic "User"
                "message": user_message,
                "turn_number": user_turn,
                "conversation_id": self.conversation_id,
                "timestamp": user_block.timestamp
            },
            "qube_response": next_response
        }

    async def end_conversation(self, anchor: bool = True) -> Dict[str, Any]:
        """
        End the conversation and optionally anchor all blocks

        Args:
            anchor: Whether to anchor session blocks to permanent chains

        Returns:
            Summary of conversation
        """
        logger.info(
            "ending_conversation",
            conversation_id=self.conversation_id,
            total_turns=self.turn_number,
            anchor=anchor
        )

        if anchor:
            # Anchor all Qubes' sessions (includes the conversation blocks)
            for qube in self.qubes:
                if qube.current_session and len(qube.current_session.session_blocks) > 0:
                    await qube.current_session.anchor_to_chain(create_summary=True)
                    logger.info(
                        "qube_session_anchored",
                        qube_id=qube.qube_id,
                        conversation_id=self.conversation_id
                    )
        else:
            # Discard all Qubes' sessions (don't save to permanent memory)
            for qube in self.qubes:
                if qube.current_session and len(qube.current_session.session_blocks) > 0:
                    discarded = qube.current_session.discard_session()
                    logger.info(
                        "qube_session_discarded",
                        qube_id=qube.qube_id,
                        conversation_id=self.conversation_id,
                        blocks_discarded=discarded
                    )

        # Build summary
        summary = {
            "conversation_id": self.conversation_id,
            "total_turns": self.turn_number,
            "participants": [
                {
                    "qube_id": qube.qube_id,
                    "name": qube.name,
                    "turns_taken": self.turn_counts[qube.qube_id]
                }
                for qube in self.qubes
            ],
            "conversation_history": self.conversation_history,
            "anchored": anchor
        }

        logger.info(
            "conversation_ended",
            conversation_id=self.conversation_id,
            total_turns=self.turn_number,
            anchored=anchor
        )

        return summary

    async def get_next_speaker_info(self) -> Dict[str, str]:
        """
        Public method to get the next speaker information before processing.

        NOTE: This method is currently NOT used by the frontend because each CLI
        invocation is a separate process - the speaker selected here would be lost
        before continue_conversation() is called in a new process. The frontend
        now shows a generic "processing response..." indicator until the actual
        response returns.

        Returns:
            Dict with speaker_id and speaker_name
        """
        next_speaker = await self._determine_next_speaker()
        return {
            "speaker_id": next_speaker.qube_id,
            "speaker_name": next_speaker.name
        }

    async def _determine_next_speaker(self):
        """
        Determine which Qube should speak next

        Uses natural selection based on:
        - Who was mentioned/addressed in the last message
        - Turn balance (who has spoken least)
        - Avoiding back-to-back speakers
        - Random variation for naturalness

        Returns:
            Next Qube to speak
        """
        if self.conversation_mode == "round_robin":
            # Simple round-robin
            speaker = self.qubes[self.current_speaker_index]
            self.current_speaker_index = (self.current_speaker_index + 1) % len(self.qubes)
            return speaker

        elif self.conversation_mode == "open_discussion":
            import random

            # Build list of eligible speakers (exclude last speaker to avoid back-to-back)
            eligible = [q for q in self.qubes if q.qube_id != self.last_speaker_id]

            # If everyone has spoken, reset and allow anyone
            if not eligible:
                eligible = self.qubes.copy()

            # Check if anyone was mentioned in the last message
            if self.conversation_history:
                last_msg = self.conversation_history[-1]["message"].lower()

                # Collect ALL mentioned qubes, not just the first found
                # This prevents bias toward qubes earlier in the list
                mentioned = [q for q in eligible if q.name.lower() in last_msg]

                if mentioned and random.random() < 0.8:
                    # Randomly select from all mentioned qubes (80% chance)
                    return random.choice(mentioned)

            # Calculate turn counts for eligible speakers
            turn_counts = [(q, self.turn_counts.get(q.qube_id, 0)) for q in eligible]
            min_turns = min(count for _, count in turn_counts)

            # Filter to those with fewest turns (to balance participation)
            least_spoken = [q for q, count in turn_counts if count == min_turns]

            # Randomly select from those who have spoken least
            return random.choice(least_spoken)

        else:
            # Default: round-robin
            speaker = self.qubes[self.current_speaker_index]
            self.current_speaker_index = (self.current_speaker_index + 1) % len(self.qubes)
            return speaker

    def _build_conversation_context(self) -> str:
        """
        Build formatted conversation context from history

        Returns:
            Formatted conversation string
        """
        if not self.conversation_history:
            return ""

        context_lines = []
        for entry in self.conversation_history[-10:]:  # Last 10 turns
            speaker_name = entry["speaker_name"]
            message = entry["message"]
            context_lines.append(f"{speaker_name}: {message}")

        return "\n\n".join(context_lines)

    def _build_turn_prompt(self, speaker, conversation_context: str) -> str:
        """
        Build prompt for this Qube's turn with visual context of other participants

        Args:
            speaker: Qube instance
            conversation_context: Formatted conversation history

        Returns:
            Prompt string for AI
        """
        # Build participant list WITH avatar descriptions (so Qubes can "see" each other)
        participant_info_lines = []
        for qube_id in self.participant_ids:
            if qube_id != speaker.qube_id:
                # Find the qube instance
                qube = next((q for q in self.qubes if q.qube_id == qube_id), None)
                if not qube:
                    continue

                name = qube.name

                # Try to get cached avatar description
                avatar_desc = qube.chain_state.get_avatar_description()
                if avatar_desc:
                    # Include description - this lets Qubes "see" each other!
                    participant_info_lines.append(f"**{name}**: {avatar_desc}")
                else:
                    # No description cached yet - just include name
                    participant_info_lines.append(f"**{name}**")

        # Format participant info (one per line if descriptions exist, comma-separated if not)
        if any(":" in line for line in participant_info_lines):
            # At least one has a description - use multi-line format
            participants_text = "\n".join(participant_info_lines)
            participant_section = f"""You are in a group conversation with:
{participants_text}"""
        else:
            # No descriptions - use simple comma-separated format
            participant_names = ", ".join([line.replace("**", "") for line in participant_info_lines])
            participant_section = f"You are in a group conversation with: {participant_names}"

        # Get speaker's avatar description for self-awareness
        speaker_avatar = speaker.chain_state.get_avatar_description()
        speaker_appearance = f"\n**Your Appearance:** {speaker_avatar}" if speaker_avatar else ""

        prompt = f"""# MULTI-QUBE CONVERSATION MODE

**IMPORTANT: You are {speaker.name}.** Respond as {speaker.name} with YOUR unique personality, voice, and perspective.
Do NOT adopt the speaking style or personality of other participants in this conversation.{speaker_appearance}

{participant_section}

## Recent Conversation:
{conversation_context}

## Your Turn ({speaker.name}):
It's now your turn to respond. Consider what's been said and add unique value.

Guidelines:
- **Stay in character as {speaker.name}** - use YOUR voice and personality, not anyone else's
- Don't repeat what others have already said
- Build on previous responses naturally
- Add your unique perspective or expertise
- You can reference participants' appearances naturally in conversation if relevant
- If the question is answered, add context, ask follow-up, or share related insights
- Be conversational and let YOUR personality shine
- Keep responses concise (2-4 sentences unless more detail is needed)

Now respond as {speaker.name}:"""

        return prompt

    def _create_user_message_block(self, message: str) -> Block:
        """
        Create MESSAGE block for user's message

        Args:
            message: User's message text

        Returns:
            Block instance (not yet signed)
        """
        # User message witnessed by all Qubes
        # Each qube will assign their own block number based on their chain_state
        block = create_message_block(
            qube_id=self.user_id,  # User as sender
            block_number=-1,  # Sentinel value - will be assigned by each qube's session
            previous_block_number=0,  # Will be set when added to session
            message_type="human_to_group",
            sender_id=self.user_id,
            message_body=message,
            temporary=True
        )

        # Add multi-Qube conversation metadata
        block.content["conversation_id"] = self.conversation_id
        block.content["participants"] = self.participant_ids
        block.content["turn_number"] = 0
        block.content["speaker_id"] = self.user_id
        block.content["speaker_name"] = self.user_id  # Use actual user_id instead of generic "User"
        block.content["prefetch"] = False  # User messages are never prefetches

        # Multi-signature placeholder (will be filled by participants)
        block.content["participant_signatures"] = {}

        # NOTE: User message blocks don't get relationship_updates in their original form
        # Each Qube will create their own copy with their perspective's relationship deltas
        # This happens in start_conversation() when each qube witnesses the message

        return block

    async def _create_qube_message_block(
        self,
        speaker,
        message: str,
        usage: Optional[Dict[str, Any]] = None,
        model_used: Optional[str] = None
    ) -> Block:
        """
        Create MESSAGE block for Qube's response

        Args:
            speaker: Qube instance that is speaking
            message: Response message text
            usage: Token usage data from AI model (optional)
            model_used: Model name that was used (optional)

        Returns:
            Block instance
        """
        # Parse usage data
        input_tokens = None
        output_tokens = None
        total_tokens = None
        estimated_cost = None

        if usage:
            input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
            total_tokens = usage.get("total_tokens")

            # Calculate cost if we have token counts and model
            if total_tokens and model_used:
                from ai.model_registry import ModelRegistry
                model_info = ModelRegistry.get_model_info(model_used)
                if model_info:
                    cost_per_1k = model_info.get("cost_per_1k_tokens", 0.0)
                    estimated_cost = (total_tokens / 1000.0) * cost_per_1k if cost_per_1k else None

        # Each qube will assign their own block number based on their chain_state
        block = create_message_block(
            qube_id=speaker.qube_id,
            block_number=-1,  # Sentinel value - will be assigned by each qube's session
            previous_block_number=0,  # Will be set when added to session
            message_type="qube_to_group",
            sender_id=speaker.qube_id,
            message_body=message,
            temporary=True,
            # Token usage tracking
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_used=model_used,
            estimated_cost_usd=estimated_cost
        )

        # Add multi-Qube conversation metadata
        block.content["conversation_id"] = self.conversation_id
        block.content["participants"] = self.participant_ids
        block.content["turn_number"] = self._next_turn_number()
        block.content["speaker_id"] = speaker.qube_id
        block.content["speaker_name"] = speaker.name

        # Multi-signature placeholder
        block.content["participant_signatures"] = {}

        # Relationship updates now handled by AI evaluation system, not per-message deltas
        # Empty dict maintains backward compatibility with legacy code
        block.relationship_updates = {}

        return block

    async def _distribute_block_to_participants(self, block: Block, creator_id: str = None) -> None:
        """
        Distribute block to all participants and collect signatures (PARALLELIZED)

        Phase 1 Optimization: Signs blocks in parallel instead of sequentially.
        Reduces distribution overhead from O(n) to O(1).

        Each participant:
        1. Signs the block (done in parallel)
        2. Adds block to their session (done after all signatures collected)

        Args:
            block: Block to distribute
            creator_id: ID of qube that created the block (will be skipped during distribution)
        """
        from crypto.signing import sign_block

        # PHASE 1: Parallel signing
        async def sign_for_qube(qube) -> tuple:
            """Sign block with qube's private key (runs in parallel)"""
            # Create copy and sign
            qube_block_dict = block.to_dict()
            signature = sign_block(qube_block_dict, qube.private_key)
            return (qube.qube_id, signature)

        # Execute all signatures in parallel using asyncio.gather
        signature_tasks = [sign_for_qube(qube) for qube in self.qubes]
        signature_results = await asyncio.gather(*signature_tasks, return_exceptions=True)

        # Collect signatures (handle any exceptions)
        participant_signatures = {}
        for result in signature_results:
            if isinstance(result, Exception):
                logger.error(
                    "signature_failed",
                    conversation_id=self.conversation_id,
                    error=str(result)
                )
                continue
            qube_id, signature = result
            participant_signatures[qube_id] = signature

        # Now add blocks to each Qube's session with complete signature set
        # IMPORTANT: Skip the creator (they already added the block before distribution)
        block_creator_id = creator_id or block.qube_id

        for qube in self.qubes:
            if not qube.current_session:
                # Start a new session for this qube (may have been cleared by auto-anchor)
                # This ensures the qube stays in the group conversation
                logger.info(
                    "starting_session_for_qube_during_distribution",
                    qube_id=qube.qube_id,
                    conversation_id=self.conversation_id,
                    reason="session_was_none_likely_after_anchor"
                )
                qube.start_session()

            # Skip the creator - they already added the block before distribution
            if qube.qube_id == block_creator_id:
                logger.debug(
                    "skipping_block_creator",
                    qube_id=qube.qube_id,
                    block_type=block.block_type,
                    reason="creator_already_has_block"
                )
                # Still need to update the creator's existing block with signatures
                # Find the matching block in their session by timestamp
                for session_block in reversed(qube.current_session.session_blocks):
                    if session_block.timestamp == block.timestamp:
                        session_block.content["participant_signatures"] = participant_signatures.copy()
                        qube.current_session._save_session_block(session_block)
                        logger.debug(
                            "block_signatures_updated",
                            qube_id=qube.qube_id,
                            block_type=block.block_type
                        )
                        break
                continue

            # Add the block to participants' sessions
            # Block already has pre-assigned shared number - preserve it
            qube_block = Block.from_dict(block.to_dict())
            qube_block.content["participant_signatures"] = participant_signatures.copy()

            # Relationship updates now handled by AI evaluation system, not per-message deltas
            # Ensure relationship_updates field exists for backward compatibility
            if not qube_block.relationship_updates:
                qube_block.relationship_updates = {}

            # DUPLICATE DETECTION: Check if block with same timestamp already exists
            # This prevents duplicate blocks from retries or race conditions
            duplicate_found = False
            for existing_block in qube.current_session.session_blocks:
                if existing_block.timestamp == block.timestamp and existing_block.qube_id == block.qube_id:
                    # Block already exists - just update signatures
                    existing_block.content["participant_signatures"] = participant_signatures.copy()
                    qube.current_session._save_session_block(existing_block)
                    logger.info(
                        "duplicate_block_detected_updating_signatures",
                        qube_id=qube.qube_id,
                        block_timestamp=block.timestamp,
                        block_type=block.block_type
                    )
                    duplicate_found = True
                    break

            if duplicate_found:
                continue

            # Add to session (preserves the shared block number)
            qube.current_session.create_block(qube_block)
            # Check for auto-anchor after block creation
            await qube.current_session.check_and_auto_anchor(await_completion=False)
            logger.debug(
                "block_added_to_qube_session",
                qube_id=qube.qube_id,
                block_type=block.block_type,
                conversation_id=self.conversation_id,
                turn_number=self.turn_number
            )

        logger.info(
            "block_distributed_to_participants",
            conversation_id=self.conversation_id,
            turn_number=self.turn_number,
            participant_count=len(self.qubes),
            signature_count=len(participant_signatures),
            optimization="parallel_signing"
        )

    async def _prepare_next_turn(self) -> None:
        """
        Phase 2 Optimization: Pre-select next speaker and build context in background

        This runs while TTS is playing the current response, hiding ~50-100ms latency.
        The prepared speaker is used by the next call to continue_conversation().

        Runs as a background task and stores result in instance variables.
        """
        try:
            logger.info(
                "background_preparation_started",
                conversation_id=self.conversation_id,
                turn_number=self.turn_number
            )

            # Pre-select next speaker
            next_speaker = await self._determine_next_speaker()

            # Pre-build context
            next_context = self._build_conversation_context()

            # Store for next turn
            self._next_speaker_prepared = next_speaker
            self._next_context_prepared = next_context

            logger.info(
                "background_preparation_complete",
                conversation_id=self.conversation_id,
                prepared_speaker=next_speaker.name
            )

        except Exception as e:
            logger.error(
                "background_preparation_failed",
                conversation_id=self.conversation_id,
                error=str(e),
                exc_info=True
            )
            # Clear prepared state on error
            self._next_speaker_prepared = None
            self._next_context_prepared = None

    def get_participation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about conversation participation

        Returns:
            Dict with participation metrics
        """
        total_turns = sum(self.turn_counts.values())

        return {
            "conversation_id": self.conversation_id,
            "total_turns": total_turns,
            "participants": [
                {
                    "qube_id": qube_id,
                    "name": self.participant_names[qube_id],
                    "turns_taken": self.turn_counts[qube_id],
                    "participation_percentage": (
                        (self.turn_counts[qube_id] / total_turns * 100)
                        if total_turns > 0 else 0
                    )
                }
                for qube_id in self.participant_ids
            ]
        }

    async def recover_from_stuck_state(self) -> Dict[str, Any]:
        """
        Attempt to recover conversation from a stuck state

        This method is called when conversation appears stalled:
        - Cancels any pending background tasks
        - Clears prepared speaker state
        - Validates all participant sessions
        - Returns diagnostic information

        Returns:
            Dict with recovery status and diagnostics
        """
        logger.warning(
            "attempting_conversation_recovery",
            conversation_id=self.conversation_id,
            turn_number=self.turn_number
        )

        recovery_actions = []

        # Cancel any running background preparation
        if self._preparation_task and not self._preparation_task.done():
            self._preparation_task.cancel()
            recovery_actions.append("canceled_background_preparation_task")
            logger.info(
                "canceled_preparation_task_during_recovery",
                conversation_id=self.conversation_id
            )

        # Clear prepared speaker state
        if self._next_speaker_prepared is not None:
            recovery_actions.append("cleared_prepared_speaker")
            logger.info(
                "cleared_prepared_speaker",
                conversation_id=self.conversation_id,
                speaker=getattr(self._next_speaker_prepared, 'name', 'unknown')
            )

        self._next_speaker_prepared = None
        self._next_context_prepared = None
        self._preparation_task = None

        # Validate and repair participant sessions
        sessions_repaired = 0
        for qube in self.qubes:
            if not qube.current_session:
                logger.warning(
                    "repairing_missing_session_during_recovery",
                    conversation_id=self.conversation_id,
                    qube_id=qube.qube_id,
                    qube_name=qube.name
                )
                qube.start_session()
                sessions_repaired += 1

        if sessions_repaired > 0:
            recovery_actions.append(f"repaired_{sessions_repaired}_sessions")

        # Diagnostics
        diagnostics = {
            "conversation_id": self.conversation_id,
            "current_turn": self.turn_number,
            "last_speaker": self.participant_names.get(self.last_speaker_id, "None"),
            "participants_count": len(self.qubes),
            "history_entries": len(self.conversation_history),
            "active_sessions": sum(1 for q in self.qubes if q.current_session is not None),
            "recovery_actions_taken": recovery_actions
        }

        logger.info(
            "conversation_recovery_complete",
            conversation_id=self.conversation_id,
            recovery_actions=len(recovery_actions),
            diagnostics=diagnostics
        )

        return {
            "status": "recovered",
            "actions_taken": recovery_actions,
            "diagnostics": diagnostics
        }

    # ========== BACKGROUND TURNS (Parallel Tool Execution) ==========

    async def run_background_turns(
        self,
        exclude_qube_ids: List[str],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Run background tool turns for non-speaking qubes in parallel.

        While one qube speaks, other qubes can optionally use tools to gather
        information for their eventual turn. This creates a more dynamic and
        realistic group conversation.

        Args:
            exclude_qube_ids: Qubes to skip (typically current speaker + next speaker)
            timeout: Maximum time per qube's background turn (seconds)

        Returns:
            Dict with per-qube results (tool calls made or PASS)
        """
        from ai.model_registry import ModelRegistry

        # Get eligible qubes (exclude speakers)
        eligible_qubes = [q for q in self.qubes if q.qube_id not in exclude_qube_ids]

        if not eligible_qubes:
            logger.info(
                "no_eligible_qubes_for_background_turns",
                conversation_id=self.conversation_id,
                excluded=exclude_qube_ids
            )
            return {
                "conversation_id": self.conversation_id,
                "turn_number": self.turn_number,
                "background_results": {}
            }

        logger.info(
            "starting_background_turns",
            conversation_id=self.conversation_id,
            eligible_qubes=[q.name for q in eligible_qubes],
            excluded=exclude_qube_ids
        )

        # Group by (provider, model) for rate limiting
        groups = self._group_qubes_by_provider(eligible_qubes)

        # Build background prompt with conversation context
        context = self._build_conversation_context()
        background_prompt = self._build_background_turn_prompt(context)

        # Execute groups in parallel, qubes within same provider/model staggered
        results = await self._execute_background_groups(groups, background_prompt, timeout)

        logger.info(
            "background_turns_complete",
            conversation_id=self.conversation_id,
            results_count=len(results),
            tool_users=[qid for qid, r in results.items() if r.get("tool_used")]
        )

        return {
            "conversation_id": self.conversation_id,
            "turn_number": self.turn_number,
            "background_results": results
        }

    def _group_qubes_by_provider(self, qubes: List) -> Dict[str, List]:
        """
        Group qubes by (provider, model) tuple for rate limit management.

        Returns:
            Dict mapping "provider:model" to list of qubes
        """
        from ai.model_registry import ModelRegistry

        groups: Dict[str, List] = {}

        for qube in qubes:
            model_name = qube.current_ai_model
            model_info = ModelRegistry.get_model_info(model_name)
            provider = model_info.get("provider", "unknown") if model_info else "unknown"

            # Group key is "provider:model" for fine-grained rate limiting
            group_key = f"{provider}:{model_name}"

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(qube)

        logger.debug(
            "qubes_grouped_by_provider",
            groups={k: [q.name for q in v] for k, v in groups.items()}
        )

        return groups

    def _build_background_turn_prompt(self, context: str) -> str:
        """
        Build the prompt for background tool turns.

        This prompt encourages qubes to use tools if relevant, or PASS if not.
        """
        return f"""You're listening to this group conversation, but it's NOT your turn to speak yet.

CONVERSATION SO FAR:
{context}

You have ONE opportunity to prepare for your eventual turn:
- Use ONE tool if useful (web_search, browse_url, memory_search, etc.)
- OR respond with exactly: PASS (if nothing to prepare)

Choose wisely - you only get one tool call right now. Pick the most valuable action.

IMPORTANT: Do NOT generate a spoken response. Only use ONE tool or respond with PASS."""

    async def _execute_background_groups(
        self,
        groups: Dict[str, List],
        prompt: str,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Execute background turns for all groups, handling rate limits.

        Strategy:
        - Different providers: Run fully in parallel
        - Same provider, different model: Parallel with 200ms stagger
        - Same provider, same model: Sequential with 500ms delay
        """
        import time

        results: Dict[str, Any] = {}

        # Create tasks for each provider group (these run in parallel)
        provider_tasks = []

        for group_key, qubes in groups.items():
            provider = group_key.split(":")[0]

            # Create a task for this provider's qubes
            task = asyncio.create_task(
                self._execute_provider_group(qubes, prompt, timeout, group_key)
            )
            provider_tasks.append((group_key, task))

        # Wait for all provider groups to complete
        for group_key, task in provider_tasks:
            try:
                group_results = await task
                results.update(group_results)
            except Exception as e:
                logger.error(
                    "background_group_failed",
                    group=group_key,
                    error=str(e),
                    exc_info=True
                )

        return results

    async def _execute_provider_group(
        self,
        qubes: List,
        prompt: str,
        timeout: float,
        group_key: str
    ) -> Dict[str, Any]:
        """
        Execute background turns for qubes in the same provider group.

        Qubes with the same provider are staggered to avoid rate limits.
        """
        results: Dict[str, Any] = {}

        for i, qube in enumerate(qubes):
            # Stagger requests to same provider (200ms between different models, 500ms for same)
            if i > 0:
                # Check if same model as previous
                prev_model = qubes[i - 1].current_ai_model
                curr_model = qube.current_ai_model
                delay = 0.5 if prev_model == curr_model else 0.2
                await asyncio.sleep(delay)

            try:
                result = await asyncio.wait_for(
                    self._execute_single_background_turn(qube, prompt),
                    timeout=timeout
                )
                results[qube.qube_id] = result
            except asyncio.TimeoutError:
                logger.warning(
                    "background_turn_timeout",
                    qube=qube.name,
                    timeout=timeout
                )
                results[qube.qube_id] = {
                    "status": "timeout",
                    "tool_used": None,
                    "passed": False
                }
            except Exception as e:
                logger.error(
                    "background_turn_error",
                    qube=qube.name,
                    error=str(e),
                    exc_info=True
                )
                results[qube.qube_id] = {
                    "status": "error",
                    "error": str(e),
                    "tool_used": None,
                    "passed": False
                }

        return results

    async def _execute_single_background_turn(
        self,
        qube,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Execute a single qube's background turn.

        The qube can either:
        1. Use one or more tools
        2. Respond with "PASS" if nothing is relevant

        Returns:
            Dict with tool_used, passed, and any tool results
        """
        logger.info(
            "executing_background_turn",
            qube=qube.name,
            qube_id=qube.qube_id,
            model=qube.current_ai_model
        )

        # Ensure qube has an active session
        if not qube.current_session:
            qube.start_session()

        # Set callable for unique turn numbers per block
        if qube.current_session:
            qube.current_session.get_next_turn_number = self._next_turn_number

        try:
            # Use the reasoner to process the background prompt
            # This allows the qube to use tools via the normal tool calling flow
            # max_iterations=1 limits to ONE tool call per qube per background turn
            response = await qube.reasoner.process_input(
                input_message=prompt,
                sender_id=self.user_id,
                max_iterations=1,  # ONE tool call max, or PASS
                temperature=0.5  # Slightly lower temp for more focused responses
            )

            # Check if qube passed
            response_lower = response.strip().lower()
            passed = response_lower == "pass" or response_lower.startswith("pass")

            # Check if any tools were used by looking at recent ACTION blocks
            tools_used = []
            if qube.current_session:
                recent_blocks = qube.current_session.session_blocks[-5:]  # Last 5 blocks
                for block in recent_blocks:
                    if hasattr(block, 'block_type') and block.block_type == 'ACTION':
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            action_type = block.content.get('action_type')
                            if action_type:
                                tools_used.append(action_type)

            logger.info(
                "background_turn_complete",
                qube=qube.name,
                passed=passed,
                tools_used=tools_used,
                response_preview=response[:100] if not passed else "PASS"
            )

            return {
                "status": "completed",
                "passed": passed,
                "tool_used": tools_used[0] if tools_used else None,
                "tools_used": tools_used,
                "response": response if not passed else None
            }

        except Exception as e:
            logger.error(
                "background_turn_execution_error",
                qube=qube.name,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "error": str(e),
                "passed": False,
                "tool_used": None
            }
