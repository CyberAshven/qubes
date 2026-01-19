"""
Session Management with Negative Indexing

From docs/05_Data_Structures.md Section 2.3
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from core.block import Block
from core.exceptions import SessionRecoveryError, MemoryChainError
# Import signing functions in methods to avoid circular import
from utils.logging import get_logger
from relationships.trait_detection import TraitDetector
from utils.trait_definitions import load_trait_definitions

logger = get_logger(__name__)

# Minimum blocks required to create a SUMMARY block
# Sessions with fewer blocks will not generate a SUMMARY
SUMMARY_THRESHOLD = 5

# Maximum conversation text length for AI summary (characters)
# Longer conversations will be truncated to avoid token limits
MAX_SUMMARY_TEXT_LENGTH = 15000  # ~3750 tokens, safe for most models


class Session:
    """
    Manages temporary session blocks with negative indexing

    From docs Section 2.3
    """

    def __init__(self, qube, auto_anchor_threshold: int = 50, session_id: str = None):
        """
        Initialize session

        Args:
            qube: Qube instance
            auto_anchor_threshold: Auto-anchor every N blocks if enabled (for individual chats)
            session_id: Optional session ID for recovery (defaults to "active")
        """
        self.qube = qube

        # Use simple "active" session ID - no need for sequential numbering
        # There's only one active session at a time
        self.session_id = session_id or "active"

        self.session_start = int(datetime.now(timezone.utc).timestamp())
        self.session_blocks: List[Block] = []
        # Note: Block indices are now computed from timestamps, no counter needed
        self.auto_anchor_threshold = auto_anchor_threshold
        self.metadata = {
            "participants": {"humans": [], "qubes": []},
            "active_tasks": [],
            "cached_results": {},
            "insights": []
        }
        # Flag to track if auto-anchor should be triggered (set by sync create_block, checked by async callers)
        self._auto_anchor_pending = False
        self._auto_anchor_is_group = False
        self._pending_anchor_task: Optional[asyncio.Task] = None

        # Emit session started event
        from core.events import Events
        self.qube.events.emit(Events.SESSION_STARTED, {
            "session_id": self.session_id
        })

        logger.info("session_started", session_id=self.session_id, qube_id=qube.qube_id)

    def is_group_conversation(self) -> bool:
        """
        Detect if this session is a group conversation

        Returns:
            True if any message has *_to_group type, False otherwise
        """
        for block in self.session_blocks:
            if block.block_type == "MESSAGE" and block.content:
                message_type = block.content.get("message_type", "")
                if message_type in ["human_to_group", "qube_to_group"]:
                    return True
        return False

    def get_active_threshold(self) -> int:
        """
        Get the appropriate auto-anchor threshold based on conversation type

        Uses group_anchor_threshold for group chats, individual_anchor_threshold otherwise.
        Falls back to session's auto_anchor_threshold if preferences not available.

        IMPORTANT: Returns at least SUMMARY_THRESHOLD to ensure summaries can be created.
        If user sets threshold lower than SUMMARY_THRESHOLD, auto-anchor would trigger
        but summary would be skipped (requiring 5+ blocks), leaving orphaned blocks.

        Returns:
            Threshold value for current conversation type (minimum SUMMARY_THRESHOLD)
        """
        # Try to get user preferences
        try:
            from orchestrator.user_orchestrator import UserOrchestrator
            # Get preferences from qube's user
            user_data_dir = self.qube.data_dir.parent.parent  # Go up to users/bit_faced/

            # Import preferences manager directly
            from config.user_preferences import UserPreferencesManager
            prefs_manager = UserPreferencesManager(user_data_dir)
            prefs = prefs_manager.get_block_preferences()

            # Use group or individual threshold based on conversation type
            if self.is_group_conversation():
                threshold = prefs.group_anchor_threshold
            else:
                threshold = prefs.individual_anchor_threshold

            # Enforce minimum threshold to ensure summary creation
            return max(threshold, SUMMARY_THRESHOLD)
        except Exception as e:
            # Fall back to session's threshold if preferences unavailable
            logger.debug(f"Could not load preferences, using session threshold: {e}")
            return max(self.auto_anchor_threshold, SUMMARY_THRESHOLD)

    def create_block(self, block: Block) -> Block:
        """
        Add block to session with negative index

        Session blocks are:
        - Unencrypted (fast access during conversation)
        - Unsigned (no crypto overhead)
        - Saved as individual JSON files

        Block numbers are assigned based on timestamp ordering:
        - Earliest timestamp = -1, next = -2, etc.
        - This is stateless and deterministic (no counter to sync)

        Args:
            block: Block to add (will be modified with session data)

        Returns:
            Modified block with negative index and temporary flag
        """
        block.temporary = True
        block.session_id = self.session_id

        # Ensure block has a timestamp
        if not block.timestamp:
            block.timestamp = int(datetime.now(timezone.utc).timestamp())

        # Add to session list first, then reindex all by timestamp
        self.session_blocks.append(block)
        self._reindex_session_blocks()

        # Emit session updated event
        from core.events import Events
        block_count = len(self.session_blocks)
        self.qube.events.emit(Events.SESSION_UPDATED, {
            "session_block_count": block_count,
            "next_negative_index": -(block_count + 1)  # Next block would be -2, -3, etc.
        })

        # EAGER RELATIONSHIP CREATION (metrics updated later by AI during SUMMARY)
        # Create relationship immediately so relationships.json exists from first message
        if block.block_type == "MESSAGE":
            # Wrap relationship creation in try-except so it doesn't block event emission
            try:
                self._create_relationship_eagerly(block)
            except Exception as e:
                logger.warning(
                    "relationship_creation_failed",
                    qube_id=self.qube.qube_id,
                    error=str(e)
                )

            # Track message sent/received via events (must not be blocked by relationship errors)
            content = block.content if isinstance(block.content, dict) else {}
            message_type = content.get("message_type", "")

            # Emit events from the QUBE's perspective:
            # - MESSAGE_SENT: qube sends a message (qube_to_human, qube_to_group, qube_to_qube)
            # - MESSAGE_RECEIVED: qube receives a message (human_to_qube, human_to_group, qube_to_qube_response)
            if message_type in ["qube_to_human", "qube_to_group", "qube_to_qube"]:
                logger.info("emitting_message_sent_event", message_type=message_type, qube_id=self.qube.qube_id)
                self.qube.events.emit(Events.MESSAGE_SENT, {})  # Qube sends this message
            elif message_type in ["human_to_qube", "human_to_group", "qube_to_qube_response"]:
                logger.info("emitting_message_received_event", message_type=message_type, qube_id=self.qube.qube_id)
                self.qube.events.emit(Events.MESSAGE_RECEIVED, {})  # Qube receives this message

        # Save individual block file (unencrypted, for crash recovery)
        self._save_session_block(block)

        # Check for auto-anchor (use dynamic threshold based on conversation type)
        # Sets a flag that async callers should check via check_and_auto_anchor()
        active_threshold = self.get_active_threshold()
        block_count = len(self.session_blocks)

        if self.qube.auto_anchor_enabled and block_count >= active_threshold:
            is_group = self.is_group_conversation()

            logger.info(
                "auto_anchor_pending",
                block_count=len(self.session_blocks),
                threshold=active_threshold,
                is_group_chat=is_group
            )
            # Set flag for async caller to trigger anchor
            self._auto_anchor_pending = True
            self._auto_anchor_is_group = is_group

        logger.debug(
            "session_block_created",
            block_number=block.block_number,
            block_type=block.block_type,
            session_id=self.session_id
        )

        return block

    async def check_and_auto_anchor(self, await_completion: bool = False) -> Optional[asyncio.Task]:
        """
        Check if auto-anchor is pending and spawn it in the background if so.

        This async method should be called by async callers after create_block()
        to handle the auto-anchor that create_block() (sync) cannot await.

        IMPORTANT: Anchoring runs in the BACKGROUND to avoid blocking conversation.
        The anchor process includes AI calls (skill scanning, relationship/self evaluation)
        that can take a long time.

        Args:
            await_completion: If True, await the anchor task before returning.
                              Use this in single-command processes (like gui_bridge)
                              to ensure the anchor completes before process exit.

        Returns:
            The anchor task if spawned (can be awaited by caller), None otherwise
        """
        # DEBUG: Write to separate file
        from pathlib import Path
        debug_file = Path(self.qube.data_dir).parent.parent.parent / "logs" / "auto_anchor_debug.log"
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | [{self.qube.name}] check_and_auto_anchor called: pending={self._auto_anchor_pending}, blocks={len(self.session_blocks)}\n")

        logger.info(
            "check_and_auto_anchor_called",
            qube_id=self.qube.qube_id,
            pending_flag=self._auto_anchor_pending
        )

        if not self._auto_anchor_pending:
            return None

        # Clear flag first to prevent re-entry
        self._auto_anchor_pending = False
        is_group = self._auto_anchor_is_group

        logger.info(
            "auto_anchor_spawning_background",
            block_count=len(self.session_blocks),
            is_group_chat=is_group,
            qube_id=self.qube.qube_id
        )

        # Spawn anchor in background
        task = asyncio.create_task(self._run_auto_anchor_background(is_group))

        # Store task reference so it can be awaited later
        self._pending_anchor_task = task

        # Optionally await completion (for single-command processes like gui_bridge)
        if await_completion:
            await task
            self._pending_anchor_task = None

        return task

    async def _run_auto_anchor_background(self, is_group: bool) -> None:
        """
        Run auto-anchor in the background.

        This is a fire-and-forget task that won't block the conversation.
        Any errors are logged but don't affect the conversation.

        IMPORTANT: Uses qube.anchor_session() to ensure identical code path
        as manual anchor from GUI.
        """
        # DEBUG: Write to separate file to bypass logging issues
        from pathlib import Path
        debug_file = Path(self.qube.data_dir).parent.parent.parent / "logs" / "auto_anchor_debug.log"
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        def debug_log(msg):
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")

        try:
            debug_log(f"=== AUTO-ANCHOR STARTED ===")
            debug_log(f"qube_id={self.qube.qube_id}, is_group={is_group}")
            debug_log(f"self (Session) id={id(self)}, session_blocks={len(self.session_blocks)}")
            debug_log(f"qube.current_session id={id(self.qube.current_session) if self.qube.current_session else 'None'}")
            debug_log(f"same_session={self is self.qube.current_session}")

            logger.info(
                "auto_anchor_background_started",
                qube_id=self.qube.qube_id,
                is_group_chat=is_group,
                session_blocks=len(self.session_blocks)
            )

            # Use qube.anchor_session() for identical behavior to manual anchor
            # This ensures the same code path is used for both manual and auto anchor
            debug_log(f"Calling qube.anchor_session(create_summary=True)...")
            blocks_anchored = await self.qube.anchor_session(create_summary=True)
            debug_log(f"anchor_session returned: blocks_anchored={blocks_anchored}")
            debug_log(f"=== AUTO-ANCHOR COMPLETED ===")

            logger.info(
                "auto_anchor_background_completed",
                qube_id=self.qube.qube_id,
                is_group_chat=is_group,
                blocks_anchored=blocks_anchored
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            debug_log(f"❌ AUTO-ANCHOR FAILED: {type(e).__name__}: {e}")
            debug_log(f"Traceback:\n{tb}")
            logger.error(
                "auto_anchor_background_failed",
                error=str(e),
                error_type=type(e).__name__,
                qube_id=self.qube.qube_id,
                traceback=tb,
                exc_info=True
            )
            # Even if anchor failed, clear session to prevent orphaned blocks
            # (blocks may have been partially converted)
            logger.info("auto_anchor_cleanup_after_failure", qube_id=self.qube.qube_id)
            self.session_blocks = []
            self.cleanup()

    def get_block(self, index: int) -> Optional[Block]:
        """
        Get block by index (supports negative indexes during session)

        Args:
            index: Block number (negative for session blocks)

        Returns:
            Block or None
        """
        if index < 0:
            # Session block
            for block in self.session_blocks:
                if block.block_number == index:
                    return block
            return None
        else:
            # Permanent block from chain
            return self.qube.memory_chain.get_block(index)

    def get_previous_hash(self) -> str:
        """Get hash of previous block for linking"""
        if len(self.session_blocks) == 0:
            # First session block links to last block in chain
            latest = self.qube.memory_chain.get_latest_block()
            if latest:
                return latest.block_hash
            else:
                return "0" * 64  # No chain yet
        else:
            # Link to previous session block
            return self.session_blocks[-1].block_hash

    def delete_block(self, block_number: int) -> Optional[Block]:
        """
        Delete a session block by its negative index

        Args:
            block_number: Negative block number

        Returns:
            Deleted block or None
        """
        for i, block in enumerate(self.session_blocks):
            if block.block_number == block_number:
                deleted = self.session_blocks.pop(i)

                # Emit session updated event
                from core.events import Events
                self.qube.events.emit(Events.SESSION_UPDATED, {
                    "session_block_count": len(self.session_blocks)
                })

                # Delete the block's file from disk
                from pathlib import Path
                session_dir = Path(self.qube.data_dir) / "blocks" / "session"
                block_type_str = deleted.block_type if isinstance(deleted.block_type, str) else deleted.block_type.value
                filename = f"{deleted.block_number}_{block_type_str}_{deleted.timestamp}.json"
                block_file = session_dir / filename

                if block_file.exists():
                    block_file.unlink()
                    logger.debug("session_block_file_deleted", file=filename)

                logger.info("session_block_deleted", block_number=block_number)
                return deleted
        return None

    async def anchor_to_chain(self, create_summary: bool = True) -> List[Block]:
        """
        Convert ALL session blocks to permanent blocks (FIFO)

        Permanent blocks are:
        - Encrypted (content field)
        - Signed (block_hash + signature)
        - Saved as individual JSON files in blocks/permanent/

        From docs Section 2.3

        Uses file lock to prevent race condition when multiple processes
        try to anchor simultaneously (CLI + GUI, multiple CLI instances, etc.)

        Args:
            create_summary: Create SUMMARY block after anchoring

        Returns:
            List of converted blocks
        """
        from crypto.signing import sign_block

        if len(self.session_blocks) == 0:
            return []

        from utils.file_lock import qube_session_lock

        with qube_session_lock(self.qube.data_dir):
            # Re-check chain length inside lock (another process may have anchored)
            chain_length = self.qube.memory_chain.get_chain_length()
            latest = self.qube.memory_chain.get_latest_block()
            previous_hash = latest.block_hash if latest else "0" * 64

            # SCAN BLOCKS FOR SKILLS BEFORE ENCRYPTION
            # Scan session blocks while they're still unencrypted
            logger.info("=== SKILL SCAN START ===")
            logger.info("scanning_session_blocks_for_skills", block_count=len(self.session_blocks))

            # Log what types of blocks we have
            block_types = {}
            for block in self.session_blocks:
                block_type = block.block_type if isinstance(block.block_type, str) else block.block_type.value
                block_types[block_type] = block_types.get(block_type, 0) + 1
            logger.info("session_block_types", types=block_types)

            skill_detections = []
            try:
                from ai.skill_scanner import SkillScanner
                scanner = SkillScanner(self.qube)

                # Scan unencrypted session blocks
                logger.info("calling_scanner_scan_blocks_for_skills")
                scan_result = await scanner.scan_blocks_for_skills(self.session_blocks)
                logger.info("scanner_returned", result_keys=list(scan_result.keys()))
                skill_detections = scan_result.get("skill_detections", [])

                if skill_detections:
                    logger.info("✅ SKILLS DETECTED!", count=len(skill_detections), detections=skill_detections)
                else:
                    logger.warning("❌ NO SKILLS DETECTED in session blocks")

            except Exception as e:
                logger.error("pre_encryption_skill_scan_failed", error=str(e), exc_info=True)

            logger.info("=== SKILL SCAN END ===")

            converted_blocks = []

            # Convert blocks in FIFO order
            for i, session_block in enumerate(self.session_blocks):
                # Create permanent block with positive index
                permanent_block = Block.from_dict(session_block.to_dict())
                permanent_block.block_number = chain_length + i
                permanent_block.temporary = False
                permanent_block.original_session_index = session_block.block_number

                # Update previous_hash to link to actual chain
                if i == 0:
                    permanent_block.previous_hash = previous_hash
                else:
                    permanent_block.previous_hash = converted_blocks[-1].block_hash

                # Encrypt content for permanent storage
                if permanent_block.content:
                    encrypted_content = self.qube.encrypt_block_content(permanent_block.content)
                    permanent_block.content = encrypted_content
                    permanent_block.encrypted = True

                # Remove previous_block_number (session-only field)
                permanent_block.previous_block_number = None

                # Re-hash and re-sign with new block_number and previous_hash
                permanent_block.block_hash = permanent_block.compute_hash()
                permanent_block.signature = sign_block(permanent_block.to_dict(), self.qube.private_key)

                # Save as individual JSON file in blocks/permanent/ (BEFORE adding to chain)
                self._save_permanent_block(permanent_block)

                # Add to memory chain (creates index entry)
                self.qube.memory_chain.add_block(permanent_block)

                # Emit block added event
                from core.events import Events
                block_type = permanent_block.block_type if isinstance(permanent_block.block_type, str) else permanent_block.block_type.value
                self.qube.events.emit(Events.BLOCK_ADDED, {
                    "block_type": block_type,
                    "block_number": permanent_block.block_number
                })

                converted_blocks.append(permanent_block)

            # CALCULATE PENDING STATS BEFORE clearing session
            # Must count from in-memory blocks BEFORE cleanup deletes the session block files
            # These counts will be committed to chain_state at the end of anchor
            pending_messages_sent = 0
            pending_messages_received = 0
            pending_tool_calls = 0
            for block in self.session_blocks:
                block_type = block.block_type if isinstance(block.block_type, str) else (block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type))
                if block_type == "MESSAGE":
                    content = block.content if isinstance(block.content, dict) else {}
                    message_type = content.get("message_type", "")
                    # From qube's perspective:
                    # - human_to_qube = qube RECEIVES
                    # - qube_to_human = qube SENDS
                    if message_type in ["human_to_qube", "human_to_group", "qube_to_qube_response"]:
                        pending_messages_received += 1
                    elif message_type in ["qube_to_human", "qube_to_group", "qube_to_qube"]:
                        pending_messages_sent += 1
                elif block_type == "ACTION":
                    pending_tool_calls += 1

            # Store pending counts for later commit
            self._pending_stats_for_commit = {
                "messages_sent": pending_messages_sent,
                "messages_received": pending_messages_received,
                "tool_calls": pending_tool_calls
            }

            # CLEAR SESSION IMMEDIATELY after conversion
            # This ensures session blocks are removed even if optional processing below fails/is interrupted
            session_block_count = len(self.session_blocks)
            self.session_blocks = []
            self.cleanup()
            logger.info(
                "session_cleared_after_conversion",
                blocks_converted=session_block_count,
                qube_id=self.qube.qube_id
            )

            # APPLY SKILL XP (after conversion so we have real block numbers)
            if skill_detections:
                logger.info("=== APPLYING SKILL XP ===")
                logger.info("applying_skill_xp", detections=len(skill_detections))
                try:
                    from ai.skill_scanner import SkillScanner
                    scanner = SkillScanner(self.qube)

                    # Update block numbers in detections (we scanned session blocks but now have permanent blocks)
                    logger.info("updating_block_numbers_from_session_to_permanent")
                    for detection in skill_detections:
                        session_index = detection.get("block_number")
                        logger.info("processing_detection", detection=detection, session_index=session_index)
                        if session_index is not None and session_index < 0:
                            # Find matching converted block by original_session_index
                            for converted in converted_blocks:
                                if converted.original_session_index == session_index:
                                    old_num = detection["block_number"]
                                    detection["block_number"] = converted.block_number
                                    logger.info("mapped_block_number", from_session=old_num, to_permanent=converted.block_number)
                                    break

                    # Apply XP with real block numbers
                    block_numbers = [b.block_number for b in converted_blocks]
                    logger.info("calling_apply_skill_xp", detections_to_apply=skill_detections)
                    skills_affected = await scanner.apply_skill_xp(skill_detections, block_numbers)
                    logger.info("✅ SKILL XP APPLIED!", skills_affected=skills_affected)

                except Exception as e:
                    logger.error("❌ skill_xp_application_failed", error=str(e), exc_info=True)

                logger.info("=== XP APPLICATION END ===")

            # Optionally create SUMMARY block (only if threshold met)
            # Find all unsummarized blocks since last SUMMARY (or GENESIS)
            # DEBUG: Log summary creation decision
            from pathlib import Path as PathLib
            debug_file = PathLib(self.qube.data_dir).parent.parent.parent / "logs" / "auto_anchor_debug.log"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            def debug_log(msg):
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")

            debug_log(f"=== SUMMARY CREATION CHECK ===")
            debug_log(f"create_summary={create_summary}")

            if create_summary:
                unsummarized_blocks = self._get_unsummarized_blocks()
                total_unsummarized = len(unsummarized_blocks)
                debug_log(f"unsummarized_blocks={total_unsummarized}, SUMMARY_THRESHOLD={SUMMARY_THRESHOLD}")
                debug_log(f"will_create_summary={total_unsummarized >= SUMMARY_THRESHOLD}")

                if total_unsummarized >= SUMMARY_THRESHOLD:
                    debug_log(f"Creating summary block for {total_unsummarized} blocks...")
                    # Create SUMMARY covering ALL unsummarized blocks
                    try:
                        debug_log(f"Calling generate_summary_block...")
                        summary_block = await self.generate_summary_block(unsummarized_blocks)
                        debug_log(f"generate_summary_block returned: block_number={summary_block.block_number if summary_block else 'None'}")
                    except Exception as e:
                        import traceback
                        debug_log(f"❌ generate_summary_block FAILED: {type(e).__name__}: {e}")
                        debug_log(f"Traceback:\n{traceback.format_exc()}")
                        raise

                    # AI-DRIVEN RELATIONSHIP EVALUATION
                    # Evaluate relationships with AI before encrypting
                    logger.info("evaluating_relationships_with_ai", block_count=total_unsummarized)
                    relationships_affected = await self._evaluate_relationships_with_ai(unsummarized_blocks)

                    # Store AI evaluation in SUMMARY block content
                    if summary_block.content:
                        summary_block.content["relationships_affected"] = relationships_affected
                        logger.debug("relationships_stored_in_summary", participants=len(relationships_affected))

                    # AI-DRIVEN SELF-EVALUATION
                    # Evaluate own performance with AI before encrypting
                    logger.info("evaluating_self_with_ai", block_count=total_unsummarized)
                    self_evaluation = await self._evaluate_self_with_ai(unsummarized_blocks)

                    # Store self-evaluation in SUMMARY block content
                    if summary_block.content and self_evaluation:
                        summary_block.content["self_evaluation"] = self_evaluation
                        logger.debug("self_evaluation_stored_in_summary")

                    # Store skill detections in SUMMARY block content
                    if summary_block.content and skill_detections:
                        summary_block.content["skill_detections"] = skill_detections
                        logger.debug("skill_detections_stored_in_summary", count=len(skill_detections))

                    # Encrypt summary block content (just like MESSAGE blocks)
                    if summary_block.content:
                        encrypted_content = self.qube.encrypt_block_content(summary_block.content)
                        summary_block.content = encrypted_content
                        summary_block.encrypted = True

                    # Re-hash and re-sign after encryption
                    summary_block.block_hash = summary_block.compute_hash()
                    summary_block.signature = sign_block(summary_block.to_dict(), self.qube.private_key)

                    # Save summary block BEFORE adding to chain (to avoid block not found error)
                    self._save_permanent_block(summary_block)
                    self.qube.memory_chain.add_block(summary_block)
                    self.qube.events.emit(Events.SUMMARY_CREATED, {
                        "block_number": summary_block.block_number
                    })
                    converted_blocks.append(summary_block)

                    # Apply AI-evaluated relationship deltas to actual relationships
                    logger.info("applying_ai_relationship_deltas", participants=len(relationships_affected))
                    self._apply_relationship_deltas_from_summary(relationships_affected)

                    # Apply self-evaluation to qube's self-evaluation tracker
                    if self_evaluation:
                        logger.info("applying_self_evaluation")
                        self._apply_self_evaluation(self_evaluation, summary_block.block_number)

                    # Save relationship snapshot AFTER AI deltas are applied
                    # This captures the updated relationship state at this point in the chain
                    relationship_snapshot = {}
                    for entity_id, rel in self.qube.relationships.storage.relationships.items():
                        relationship_snapshot[entity_id] = rel.to_dict()

                    self.qube.memory_chain.save_relationship_snapshot(
                        block_number=summary_block.block_number,
                        relationships=relationship_snapshot
                    )

                    debug_log(f"✅ SUMMARY BLOCK CREATED! block_number={summary_block.block_number}")
                    logger.info(
                        "summary_block_created",
                        session_id=self.session_id,
                        blocks_summarized=total_unsummarized,
                        summary_block_number=summary_block.block_number,
                        block_range=f"{unsummarized_blocks[0].block_number}-{unsummarized_blocks[-1].block_number}",
                        relationships_evaluated=len(relationships_affected),
                        relationship_snapshot_saved=len(relationship_snapshot)
                    )
                else:
                    debug_log(f"❌ SUMMARY SKIPPED: only {total_unsummarized} blocks, need {SUMMARY_THRESHOLD}")
                    logger.info(
                        "summary_skipped_threshold",
                        session_id=self.session_id,
                        unsummarized_block_count=total_unsummarized,
                        threshold=SUMMARY_THRESHOLD
                    )

            # Save relationship snapshot after anchoring (regardless of SUMMARY creation)
            # If SUMMARY was created, this is redundant but harmless
            # If SUMMARY was skipped, this captures the current relationship state
            if converted_blocks:
                final_block_number = converted_blocks[-1].block_number
                relationship_snapshot = {}

                # Serialize all current relationships
                for entity_id, rel in self.qube.relationships.storage.relationships.items():
                    relationship_snapshot[entity_id] = rel.to_dict()

                # Save snapshot to memory chain
                self.qube.memory_chain.save_relationship_snapshot(
                    block_number=final_block_number,
                    relationships=relationship_snapshot
                )

                logger.debug(
                    "relationship_snapshot_created_after_anchoring",
                    session_id=self.session_id,
                    block_number=final_block_number,
                    relationship_count=len(relationship_snapshot)
                )

            # Emit chain updated event with final values
            final_chain_length = self.qube.memory_chain.get_chain_length()
            final_block = converted_blocks[-1]
            self.qube.events.emit(Events.CHAIN_UPDATED, {
                "chain_length": final_chain_length,
                "last_block_number": final_block.block_number,
                "last_block_hash": final_block.block_hash
            })

            # Commit session data - session-scoped changes (skills, relationships, mood, owner_info)
            # are now permanent since the session was successfully anchored
            # Pass the pre-calculated pending stats (calculated before session blocks were deleted)
            pending_stats = getattr(self, '_pending_stats_for_commit', None)
            self.qube.chain_state.commit_staged_session(pending_stats=pending_stats)

            # Emit session ended event
            self.qube.events.emit(Events.SESSION_ENDED, {
                "session_id": self.session_id
            })

            # Session was already cleared immediately after conversion (line 471-481)
            # Just log completion
            logger.info(
                "session_anchored",
                session_id=self.session_id,
                blocks_anchored=len(converted_blocks),
                new_chain_length=final_chain_length
            )

            return converted_blocks

    def _get_unsummarized_blocks(self) -> List[Block]:
        """
        Get all permanent blocks that haven't been summarized yet.

        Walks backward from the latest block until finding either:
        - A SUMMARY block (returns all blocks after it)
        - The GENESIS block (returns all non-GENESIS blocks)

        Only includes MESSAGE, ACTION, and GAME blocks (content blocks).
        Never includes SUMMARY or GENESIS blocks.

        Returns:
            List of unsummarized blocks in chronological order
        """
        unsummarized = []
        chain_length = self.qube.memory_chain.get_chain_length()

        # Block types that should be included in summaries
        SUMMARIZABLE_TYPES = {"MESSAGE", "ACTION", "GAME"}

        # Walk backward from the latest block
        for block_num in range(chain_length - 1, -1, -1):
            block = self.qube.memory_chain.get_block(block_num)

            if not block:
                continue

            # Normalize block_type to string (could be enum or string)
            block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value

            # Stop if we hit a SUMMARY block (don't include it)
            if block_type_str == "SUMMARY":
                logger.debug("hit_summary_block", block_number=block_num)
                break

            # Stop if we hit the GENESIS block (don't include it)
            if block_type_str == "GENESIS":
                logger.debug("hit_genesis_block", block_number=block_num)
                break

            # Only add summarizable block types (defensive check)
            if block_type_str in SUMMARIZABLE_TYPES:
                unsummarized.insert(0, block)  # Insert at beginning to maintain chronological order
            else:
                logger.warning(
                    "skipping_non_summarizable_block",
                    block_number=block_num,
                    block_type=block_type_str
                )

        logger.info(
            "unsummarized_blocks_found",
            count=len(unsummarized),
            block_range=f"{unsummarized[0].block_number}-{unsummarized[-1].block_number}" if unsummarized else "none"
        )

        return unsummarized

    def discard_session(self) -> int:
        """
        Discard all session blocks without anchoring

        Rolls back session-scoped changes (skills, relationships, mood, owner_info)
        to their state at session start. Immediately persistent changes (settings,
        financial transactions, stats) are NOT rolled back.

        Returns:
            Number of blocks discarded
        """
        block_count = len(self.session_blocks)
        self.session_blocks = []

        # Rollback session-scoped data (skills, relationships, mood, owner_info)
        # to the snapshot taken when the session started
        try:
            rolled_back = self.qube.chain_state.rollback_session_data()
            if rolled_back:
                logger.info("session_scoped_data_rolled_back", session_id=self.session_id)
        except Exception as e:
            logger.warning("session_rollback_failed", error=str(e))

        # Emit session ended event
        try:
            from core.events import Events
            self.qube.events.emit(Events.SESSION_ENDED, {
                "session_id": self.session_id,
                "rolled_back": True
            })
        except Exception as e:
            logger.warning("chain_state_end_session_failed", error=str(e))

        # Cleanup files (don't fail if files are locked - they'll be cleaned up next time)
        try:
            self.cleanup()
        except Exception as e:
            logger.warning("session_cleanup_failed", error=str(e))

        logger.info("session_discarded", session_id=self.session_id, blocks=block_count)
        return block_count

    async def generate_summary_block(self, converted_blocks: List[Block]) -> Block:
        """
        Generate SUMMARY block for blocks being summarized

        Note: converted_blocks may span multiple sessions (all unsummarized blocks)

        From docs Section 2.2 - Session-specific summary
        """
        # DEBUG logging
        from pathlib import Path
        debug_file = Path(self.qube.data_dir).parent.parent.parent / "logs" / "auto_anchor_debug.log"
        def debug_log(msg):
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | [generate_summary_block] {msg}\n")

        debug_log(f"Started with {len(converted_blocks)} blocks")

        from core.block import create_summary_block

        summarized_block_numbers = [b.block_number for b in converted_blocks]

        # Calculate time period from actual block timestamps
        # (not just current session, since we may be summarizing multiple sessions)
        start_time = min(b.timestamp for b in converted_blocks)
        end_time = max(b.timestamp for b in converted_blocks)
        duration_seconds = end_time - start_time

        debug_log(f"Calling _generate_conversation_summary...")
        # Generate summary text asynchronously
        summary_text = await self._generate_conversation_summary(converted_blocks)
        debug_log(f"_generate_conversation_summary returned: {len(summary_text) if summary_text else 0} chars")

        summary_block = create_summary_block(
            qube_id=self.qube.qube_id,
            block_number=self.qube.memory_chain.get_chain_length(),
            previous_hash=converted_blocks[-1].block_hash,
            summarized_blocks=summarized_block_numbers,
            block_count=len(converted_blocks),
            time_period={
                "start": start_time,
                "end": end_time,
                "duration_hours": duration_seconds / 3600
            },
            summary_type="session",
            summary_text=summary_text,
            session_id=self.session_id,
            key_events=self._extract_key_events(converted_blocks),
            sentiment_analysis=self._analyze_sentiment(converted_blocks),
            topics_covered=self._extract_topics(converted_blocks),
            participants=self.metadata["participants"],
            actions_taken=self._extract_actions(converted_blocks),
            key_insights=self.metadata["insights"],
            next_session_context=None,
            archival_references=None
        )

        return summary_block

    async def _generate_conversation_summary(self, blocks: List[Block]) -> str:
        """Generate AI-powered text summary of conversation"""
        # DEBUG logging
        from pathlib import Path
        debug_file = Path(self.qube.data_dir).parent.parent.parent / "logs" / "auto_anchor_debug.log"
        def debug_log(msg):
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | [_generate_conversation_summary] {msg}\n")

        debug_log(f"Started with {len(blocks)} blocks")
        logger.info("generate_summary_start", block_count=len(blocks))

        # If qube doesn't have AI initialized, fall back to basic summary
        has_reasoner = hasattr(self.qube, 'reasoner') and self.qube.reasoner is not None
        debug_log(f"has_reasoner={has_reasoner}")
        if not has_reasoner:
            logger.warning("no_reasoner_for_summary", qube_has_reasoner=hasattr(self.qube, 'reasoner'))
            message_count = sum(1 for b in blocks if b.block_type == "MESSAGE")
            action_count = sum(1 for b in blocks if b.block_type == "ACTION")
            thought_count = sum(1 for b in blocks if b.block_type == "THOUGHT")

            parts = []
            if message_count > 0:
                parts.append(f"{message_count} message{'s' if message_count != 1 else ''}")
            if action_count > 0:
                parts.append(f"{action_count} action{'s' if action_count != 1 else ''}")
            if thought_count > 0:
                parts.append(f"{thought_count} thought{'s' if thought_count != 1 else ''}")

            return f"Session with {', '.join(parts)} over {len(blocks)} blocks."

        # Extract conversation text from MESSAGE blocks
        # NOTE: At this point, blocks are already encrypted as permanent blocks
        # We need to decrypt them to read the content for summary
        conversation_parts = []
        encrypted_count = sum(1 for b in blocks if b.encrypted)
        debug_log(f"Starting extraction, encrypted_blocks={encrypted_count}")
        logger.info("extracting_conversation", encrypted_blocks=encrypted_count)

        for block in blocks:
            # Decrypt block content if it's encrypted
            content = block.content if isinstance(block.content, dict) else {}
            logger.debug("processing_block", block_number=block.block_number, block_type=block.block_type, encrypted=block.encrypted, has_ciphertext="ciphertext" in content)

            if block.encrypted and "ciphertext" in content:
                # Block is encrypted, need to decrypt
                try:
                    decrypted_content = self.qube.decrypt_block_content(content)
                    content = decrypted_content
                    logger.debug("block_decrypted", block_number=block.block_number, has_message_body="message_body" in content)
                except Exception as e:
                    logger.warning("failed_to_decrypt_block_for_summary", block_number=block.block_number, error=str(e))
                    continue

            if block.block_type == "MESSAGE":
                message_type = content.get("message_type", "")
                message_body = content.get("message_body", "")
                sender_id = content.get("sender_id", "")
                speaker_name = content.get("speaker_name", "")
                logger.debug("message_block", block_number=block.block_number, message_type=message_type, body_length=len(message_body))

                if message_type in ["human_to_qube", "human_to_group"]:
                    # Use speaker_name if available for group chats, otherwise "Human"
                    speaker_label = speaker_name if speaker_name else "Human"
                    conversation_parts.append(f"{speaker_label}: {message_body}")
                elif message_type in ["qube_to_human", "qube_to_group"]:
                    # Use speaker_name if available for group chats, otherwise "Qube"
                    speaker_label = speaker_name if speaker_name else "Qube"
                    conversation_parts.append(f"{speaker_label}: {message_body}")
            elif block.block_type == "ACTION":
                # Smart summary for ACTION blocks - capture essence without raw data
                action_summary = self._summarize_action_block(content)
                if action_summary:
                    conversation_parts.append(action_summary)

            elif block.block_type == "GAME":
                # Smart summary for GAME blocks - participants, result, highlights
                game_summary = self._summarize_game_block(content)
                if game_summary:
                    conversation_parts.append(game_summary)

        debug_log(f"Extraction complete, parts_count={len(conversation_parts)}")
        logger.info("conversation_extracted", parts_count=len(conversation_parts))

        if not conversation_parts:
            debug_log("Empty conversation - returning fallback")
            logger.warning("empty_conversation_for_summary")
            return "Empty session with no messages."

        conversation_text = "\n".join(conversation_parts)
        debug_log(f"Conversation text ready, length={len(conversation_text)}")
        original_length = len(conversation_text)

        # Truncate if conversation is too long for AI processing
        truncated = False
        if len(conversation_text) > MAX_SUMMARY_TEXT_LENGTH:
            # Keep the most recent part of the conversation (end is usually most relevant)
            # But also include a bit from the beginning for context
            beginning_chars = MAX_SUMMARY_TEXT_LENGTH // 4  # 25% from beginning
            ending_chars = MAX_SUMMARY_TEXT_LENGTH - beginning_chars - 50  # 75% from end (minus separator)

            conversation_text = (
                conversation_text[:beginning_chars] +
                "\n\n[... conversation truncated for length ...]\n\n" +
                conversation_text[-ending_chars:]
            )
            truncated = True
            logger.warning(
                "conversation_truncated_for_summary",
                original_length=original_length,
                truncated_length=len(conversation_text),
                block_count=len(blocks)
            )

        logger.info(
            "conversation_text_ready",
            text_length=len(conversation_text),
            truncated=truncated,
            preview=conversation_text[:200] if len(conversation_text) > 200 else conversation_text
        )

        # Use AI to generate summary (now properly async)
        try:
            # Create prompt for summary
            truncation_note = " Note: This is a truncated view of a longer conversation." if truncated else ""
            summary_prompt = f"""Summarize this conversation in a detailed paragraph (3-5 sentences). Include the main topics discussed, key questions asked, important information shared, and any actions taken. Be specific about the content while remaining concise.{truncation_note}

Conversation:
{conversation_text}

Summary:"""

            debug_log(f"AI summary starting, prompt_length={len(summary_prompt)}")
            logger.info("ai_summary_starting", prompt_length=len(summary_prompt))

            # Properly await the async AI call (now that this method is async)
            debug_log(f"Calling model.generate()...")
            response = await self.qube.reasoner.model.generate(
                messages=[{"role": "user", "content": summary_prompt}],
                tools=[],
                temperature=0.3
            )
            debug_log(f"model.generate() returned, has_content={response is not None and hasattr(response, 'content')}")
            logger.info("ai_summary_response_received", has_content=response is not None and hasattr(response, 'content'))

            summary = response.content.strip() if response and response.content else None
            logger.info("ai_summary_extracted", summary_length=len(summary) if summary else 0, summary_preview=summary[:100] if summary and len(summary) > 100 else summary)

            if summary and len(summary) > 10:
                debug_log(f"✅ AI summary SUCCESS, length={len(summary)}")
                logger.info("ai_summary_success", summary_length=len(summary))
                return summary
            else:
                # Fallback if AI summary is too short
                debug_log(f"⚠️ AI summary too short, length={len(summary) if summary else 0}")
                logger.warning("ai_summary_too_short", summary_length=len(summary) if summary else 0)
                return f"Conversation covering {len(conversation_parts)} exchanges."

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            debug_log(f"❌ AI summary FAILED: {type(e).__name__}: {e}")
            debug_log(f"Traceback:\n{tb}")
            logger.error("ai_summary_failed", error=str(e), error_type=type(e).__name__)
            logger.error("ai_summary_traceback", traceback=tb)
            # Fallback to basic summary on error
            return f"Session with {len(conversation_parts)} exchanges over {len(blocks)} blocks."

    def _summarize_action_block(self, content: Dict[str, Any]) -> str:
        """
        Create a smart summary of an ACTION block.
        Captures the essence without including raw data/results.
        """
        action_type = content.get("action_type", "unknown")
        parameters = content.get("parameters", {})
        result = content.get("result", {})
        status = content.get("status", "unknown")

        # Handle different action types with appropriate summaries
        if action_type == "web_search":
            query = parameters.get("query", "unknown query")
            result_count = 0
            top_results = []
            if isinstance(result, dict):
                results_list = result.get("results", [])
                result_count = len(results_list)
                # Get just the titles of top 2 results
                for r in results_list[:2]:
                    if isinstance(r, dict) and r.get("title"):
                        top_results.append(r["title"][:50])

            summary = f"[Web Search: \"{query}\""
            if result_count > 0:
                summary += f" - {result_count} results"
                if top_results:
                    summary += f" including: {', '.join(top_results)}"
            summary += "]"
            return summary

        elif action_type == "browse_url":
            url = parameters.get("url", "unknown URL")
            # Truncate URL to domain + path start
            if len(url) > 60:
                url = url[:57] + "..."
            return f"[Browsed: {url}]"

        elif action_type == "remember_about_owner":
            # Legacy tool - kept for backward compatibility with existing blocks
            key = parameters.get("key", "info")
            value = str(parameters.get("value", ""))[:50]  # Truncate value
            sensitivity = parameters.get("sensitivity", "public")
            return f"[Remembered: {key} = \"{value}\" ({sensitivity})]"

        elif action_type == "generate_image":
            prompt = parameters.get("prompt", "")[:60]
            return f"[Generated Image: \"{prompt}...\"]"

        elif action_type == "search_memory":
            query = parameters.get("query", "unknown")
            result_count = 0
            if isinstance(result, dict):
                result_count = len(result.get("results", []))
            return f"[Memory Search: \"{query}\" - {result_count} results]"

        elif action_type == "get_relationships":
            # Legacy tool - kept for backward compatibility with existing blocks
            entity = parameters.get("entity_name", parameters.get("entity_id", ""))
            if entity:
                return f"[Queried Relationship: {entity}]"
            return "[Queried Relationships]"

        elif action_type == "chess_move":
            move = parameters.get("move", "unknown")
            return f"[Chess Move: {move}]"

        elif action_type == "send_bch":
            amount = parameters.get("amount_sats", 0)
            to_addr = parameters.get("to_address", "")[:20]
            status = result.get("status", "") if isinstance(result, dict) else ""
            bch = amount / 100_000_000
            if status == "pending_approval":
                return f"[Proposed BCH Send: {bch:.8f} BCH to {to_addr}... (pending approval)]"
            return f"[BCH Send: {bch:.8f} BCH to {to_addr}...]"

        elif action_type == "describe_my_avatar":
            return "[Analyzed own avatar]"

        elif action_type == "describe_my_skills":
            # Legacy tool - kept for backward compatibility with existing blocks
            category = parameters.get("category", "")
            if category:
                return f"[Checked skills: {category}]"
            return "[Checked skill tree]"

        elif action_type == "get_system_state":
            sections = parameters.get("sections", [])
            if sections:
                return f"[Read state: {', '.join(sections)}]"
            return "[Read system state]"

        elif action_type == "update_system_state":
            section = parameters.get("section", "")
            path = parameters.get("path", "")
            if section and path:
                return f"[Updated {section}.{path}]"
            elif section:
                return f"[Updated {section}]"
            return "[Updated chain state]"

        # Skill-based tools - brief summaries
        elif action_type in ["think_step_by_step", "self_critique", "explore_alternatives"]:
            return f"[Reasoning: {action_type.replace('_', ' ')}]"

        elif action_type in ["draft_message_variants", "predict_reaction", "build_rapport_strategy"]:
            return f"[Social: {action_type.replace('_', ' ')}]"

        elif action_type in ["debug_systematically", "research_with_synthesis", "validate_solution"]:
            return f"[Technical: {action_type.replace('_', ' ')}]"

        elif action_type in ["brainstorm_variants", "iterate_design", "cross_pollinate_ideas"]:
            return f"[Creative: {action_type.replace('_', ' ')}]"

        elif action_type in ["deep_research", "synthesize_knowledge", "explain_like_im_five"]:
            return f"[Knowledge: {action_type.replace('_', ' ')}]"

        elif action_type in ["assess_security_risks", "privacy_impact_analysis", "verify_authenticity"]:
            return f"[Security: {action_type.replace('_', ' ')}]"

        elif action_type in ["analyze_game_state", "plan_strategy", "learn_from_game"]:
            return f"[Game Analysis: {action_type.replace('_', ' ')}]"

        else:
            # Generic action summary
            if status == "completed":
                return f"[Action: {action_type} - completed]"
            elif status == "failed":
                error = result.get("error", "unknown error") if isinstance(result, dict) else "unknown error"
                return f"[Action: {action_type} - failed: {str(error)[:30]}]"
            else:
                return f"[Action: {action_type}]"

    def _summarize_game_block(self, content: Dict[str, Any]) -> str:
        """
        Create a smart summary of a GAME block.
        Includes participants, result, and key details without full game data.
        """
        game_type = content.get("game_type", "game")
        result = content.get("result", "*")
        termination = content.get("termination", "")
        total_moves = content.get("total_moves", 0)

        # Get player info
        white_player = content.get("white_player", {})
        black_player = content.get("black_player", {})
        white_name = white_player.get("name", white_player.get("id", "White"))[:20]
        black_name = black_player.get("name", black_player.get("id", "Black"))[:20]

        # Determine winner
        if result == "1-0":
            winner = white_name
            outcome = f"{white_name} won"
        elif result == "0-1":
            winner = black_name
            outcome = f"{black_name} won"
        elif result == "1/2-1/2":
            outcome = "Draw"
        else:
            outcome = "Ongoing/Unknown"

        # Build summary
        summary = f"[{game_type.title()} Game: {white_name} vs {black_name}"
        summary += f" - {outcome}"
        if termination:
            summary += f" by {termination}"
        if total_moves > 0:
            summary += f" ({total_moves} moves)"
        summary += "]"

        return summary

    def _extract_key_events(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """Extract key events from blocks"""
        events = []
        for block in blocks:
            if block.block_type == "DECISION":
                events.append({
                    "type": "decision",
                    "block": block.block_number,
                    "decision": block.content.get("decision"),
                    "timestamp": block.timestamp
                })
            elif block.block_type == "ACTION":
                events.append({
                    "type": "action",
                    "block": block.block_number,
                    "action_type": block.content.get("action_type"),
                    "timestamp": block.timestamp
                })
        return events

    def _analyze_sentiment(self, blocks: List[Block]) -> Dict[str, Any]:
        """Analyze sentiment of session"""
        return {
            "overall": "neutral",
            "trend": "stable",
            "key_emotions": []
        }

    def _extract_topics(self, blocks: List[Block]) -> List[str]:
        """Extract topics covered in session"""
        topics = set()
        for block in blocks:
            if block.block_type == "MESSAGE":
                topics.add("conversation")
            elif block.block_type == "ACTION":
                action_type = block.content.get("action_type", "")
                if action_type:
                    topics.add(action_type)
            elif block.block_type == "DECISION":
                topics.add("decision_making")
        return sorted(list(topics))

    def _extract_actions(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """Extract actions taken in session"""
        actions = []
        for block in blocks:
            if block.block_type == "ACTION":
                actions.append({
                    "type": block.content.get("action_type"),
                    "block": block.block_number
                })
        return actions

    def _reindex_session_blocks(self) -> None:
        """
        Reindex all session blocks by timestamp order.

        This is the core of timestamp-based indexing:
        - Sort blocks by timestamp (earliest first)
        - Assign block numbers: -1 for earliest, -2 for next, etc.
        - Update previous_block_number references

        This approach is stateless and deterministic - no counter to sync.
        """
        if not self.session_blocks:
            return

        # Sort by timestamp (earliest first)
        self.session_blocks.sort(key=lambda b: (b.timestamp, id(b)))  # id() as tiebreaker for same-second

        # Assign block numbers: -1 for earliest, -2 for next, etc.
        for i, block in enumerate(self.session_blocks):
            block.block_number = -(i + 1)

        # Update previous_block_number references
        for i, block in enumerate(self.session_blocks):
            if i == 0:
                # First session block references last permanent block
                latest = self.qube.memory_chain.get_latest_block()
                block.previous_block_number = latest.block_number if latest else 0
            else:
                block.previous_block_number = self.session_blocks[i - 1].block_number

    def _save_session_block(self, block: Block) -> None:
        """
        Save individual session block as JSON file (unencrypted)

        Filename format: {block_number}_{block_type}_{timestamp}.json
        Example: -1_MESSAGE_1759803086.json

        Blocks are stored directly in blocks/session/ (no subdirectories)
        """
        from pathlib import Path

        # Store directly in blocks/session/ (no session_xxx subdirectory)
        session_dir = Path(self.qube.data_dir) / "blocks" / "session"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Format filename: block_number_type_timestamp
        block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
        filename = f"{block.block_number}_{block_type_str}_{block.timestamp}.json"

        block_file = session_dir / filename

        # Save block as unencrypted JSON
        with open(block_file, 'w') as f:
            json.dump(block.to_dict(), f, indent=2)

    async def _evaluate_self_with_ai(self, blocks: List[Block]) -> Optional[Dict[str, Any]]:
        """
        Use AI to evaluate qube's own performance and behavior

        Returns dict with structure:
        {
            "evaluation_summary": "...",
            "reasoning": "...",
            "strengths": [...],
            "areas_for_improvement": [...],
            "metrics": {
                "self_awareness": 75.0,
                "confidence": 80.0,
                ...10 metrics total...
            }
        }

        Args:
            blocks: List of blocks to evaluate

        Returns:
            Dictionary of self-evaluation data or None if evaluation fails
        """
        logger.info("_evaluate_self_with_ai_called", block_count=len(blocks))

        # Check if AI reasoner is available
        if not hasattr(self.qube, 'reasoner') or not self.qube.reasoner:
            logger.warning("no_reasoner_for_self_evaluation")
            return None

        # Get evaluation model from genesis block (fallback to main AI model if not set)
        evaluation_model = getattr(self.qube.genesis_block, 'evaluation_model', None)
        if not evaluation_model:
            # Fall back to main AI model if evaluation_model not set
            evaluation_model = self.qube.current_ai_model
            logger.info("no_evaluation_model_set_using_main_model", model=evaluation_model)
        else:
            logger.info("using_evaluation_model", model=evaluation_model)

        logger.info("reasoner_available_building_context")

        # Build conversation context
        conversation_text = self._build_conversation_context_for_eval(blocks)
        logger.info("conversation_context_built", text_length=len(conversation_text))

        # Construct AI prompt
        prompt = f"""Evaluate your own performance and behavior in this conversation.

CONVERSATION:
{conversation_text}

INSTRUCTIONS:
Reflect on your own responses and behavior. Be honest and self-critical. Evaluate yourself on these 10 metrics (0-100 scale):

1. **Self-Awareness** (0-100): Understanding your own capabilities and limitations
2. **Confidence** (0-100): Belief in your abilities without arrogance
3. **Consistency** (0-100): Behavioral stability and predictability
4. **Growth Rate** (0-100): Speed of learning and adaptation
5. **Goal Alignment** (0-100): Acting according to your stated values
6. **Critical Thinking** (0-100): Quality of reasoning and analysis
7. **Adaptability** (0-100): Flexibility in approach
8. **Emotional Intelligence** (0-100): Response management in difficult situations
9. **Humility** (0-100): Recognizing and admitting mistakes
10. **Curiosity** (0-100): Drive to explore and learn

Return ONLY valid JSON with this exact structure:
{{
    "evaluation_summary": "Brief 1-2 sentence summary of your performance",
    "reasoning": "Detailed explanation of your self-assessment (2-3 sentences)",
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
    "metrics": {{
        "self_awareness": 75.0,
        "confidence": 80.0,
        "consistency": 70.0,
        "growth_rate": 65.0,
        "goal_alignment": 85.0,
        "critical_thinking": 78.0,
        "adaptability": 72.0,
        "emotional_intelligence": 68.0,
        "humility": 82.0,
        "curiosity": 90.0
    }}
}}"""

        try:
            logger.info("calling_reasoner_for_self_evaluation", evaluation_model=evaluation_model)

            # Call AI for evaluation using the evaluation_model (set max_iterations=1 to minimize tool usage and get JSON response)
            response = await self.qube.reasoner.process_input(
                input_message=prompt,
                model_name=evaluation_model,  # Use evaluation model instead of main AI model
                temperature=0.7,
                max_iterations=1  # Minimize tool calls to get pure JSON response
            )

            logger.info("reasoner_response_received", response_length=len(response))
            logger.debug(f"Self-evaluation raw response: {response[:1000]}")  # Log first 1000 chars

            # Parse JSON response
            # Try to extract JSON if there's text before/after
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                logger.info("json_extracted_from_response", json_length=len(json_str))
                evaluation_data = json.loads(json_str)
            else:
                logger.error(f"No JSON found in self-evaluation response: {response[:500]}")
                return None

            logger.info("self_evaluation_complete", metrics_count=len(evaluation_data.get("metrics", {})))
            logger.debug(f"Self-evaluation data: {evaluation_data}")
            return evaluation_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse self-evaluation JSON: {e}\nResponse: {response[:500] if 'response' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Self-evaluation failed: {e}", exc_info=True)
            return None

    def _apply_self_evaluation(self, evaluation_data: Dict[str, Any], block_number: int):
        """
        Apply self-evaluation to qube's self-evaluation tracker

        Args:
            evaluation_data: Dict from _evaluate_self_with_ai()
            block_number: Block number where evaluation occurred
        """
        try:
            # Ensure qube has self_evaluation attribute
            if not hasattr(self.qube, 'self_evaluation'):
                from relationships.self_evaluation import SelfEvaluation
                self.qube.self_evaluation = SelfEvaluation(
                    qube_id=self.qube.qube_id,
                    data_dir=self.qube.data_dir
                )

            # Update self-evaluation tracker
            self.qube.self_evaluation.update_from_ai_evaluation(
                evaluation_data=evaluation_data,
                block_number=block_number
            )

            logger.info("self_evaluation_applied", block_number=block_number)

        except Exception as e:
            logger.error(f"Failed to apply self-evaluation: {e}")

    def _save_permanent_block(self, block: Block) -> None:
        """
        Save individual permanent block as JSON file (encrypted content)

        Filename format: {block_number}_{block_type}_{timestamp}.json
        Example: 1_MESSAGE_1759803086.json
        """
        from pathlib import Path

        # Create permanent blocks directory
        permanent_dir = Path(self.qube.data_dir) / "blocks" / "permanent"
        permanent_dir.mkdir(parents=True, exist_ok=True)

        # Format filename: block_number_type_timestamp
        block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
        filename = f"{block.block_number}_{block_type_str}_{block.timestamp}.json"

        block_file = permanent_dir / filename

        # Save block as JSON (content is already encrypted)
        with open(block_file, 'w') as f:
            json.dump(block.to_dict(), f, indent=2)

        # Index block for semantic search (if initialized)
        try:
            if self.qube.semantic_search is not None:
                self.qube.semantic_search.add_block(block)
        except Exception as e:
            logger.debug("semantic_index_skip", block_number=block.block_number, error=str(e))

    def _extract_all_participants(self, blocks: List[Block]) -> set:
        """
        Extract all unique participants from blocks

        Args:
            blocks: List of blocks to analyze

        Returns:
            Set of entity_ids (excluding this qube)
        """
        participants = set()

        for block in blocks:
            # Decrypt block if needed
            content = block.content if isinstance(block.content, dict) else {}

            if block.encrypted and "ciphertext" in content:
                try:
                    content = self.qube.decrypt_block_content(content)
                except Exception as e:
                    logger.warning("failed_to_decrypt_block_for_participants", block_number=block.block_number, error=str(e))
                    continue

            # Extract participants from MESSAGE blocks
            if block.block_type == "MESSAGE":
                message_type = content.get("message_type", "")

                # Handle GROUP messages - extract all participants
                if message_type in ["qube_to_group", "human_to_group"]:
                    group_participants = content.get("participants", [])
                    for participant_id in group_participants:
                        if participant_id != self.qube.qube_id:
                            participants.add(participant_id)
                    # Also add the speaker if it's a human
                    if message_type == "human_to_group":
                        speaker_name = content.get("speaker_name")
                        if speaker_name and speaker_name != self.qube.qube_id:
                            participants.add(speaker_name)

                # Handle INDIVIDUAL outgoing messages
                elif message_type in ["qube_to_qube", "qube_to_human"]:
                    recipient_id = content.get("recipient_id")
                    if recipient_id and recipient_id != self.qube.qube_id:
                        # For human recipients, use actual user_name
                        if message_type == "qube_to_human":
                            participants.add(self.qube.user_name)
                        else:
                            participants.add(recipient_id)

                # Handle INDIVIDUAL incoming messages
                elif message_type in ["qube_to_qube_response", "human_to_qube"]:
                    # For human senders, use speaker_name from content (preferred) or fallback to user_name
                    if message_type == "human_to_qube":
                        speaker = content.get("speaker_name") or self.qube.user_name
                        if speaker and speaker != self.qube.qube_id:
                            participants.add(speaker)
                    else:
                        recipient_id = content.get("recipient_id")
                        if recipient_id and recipient_id != self.qube.qube_id:
                            participants.add(recipient_id)

            # Extract participants from ACTION blocks
            elif block.block_type == "ACTION":
                # Check for collaboration participants in action parameters
                parameters = content.get("parameters", {})
                for key in ['collaborator', 'collaborators', 'participants', 'qube_id', 'qube_ids']:
                    if key in parameters:
                        value = parameters[key]
                        if isinstance(value, list):
                            participants.update(p for p in value if p != self.qube.qube_id)
                        elif isinstance(value, str) and value != self.qube.qube_id:
                            participants.add(value)

        logger.debug("participants_extracted", count=len(participants), participants=list(participants))
        return participants

    def _build_conversation_context_for_eval(self, blocks: List[Block]) -> str:
        """
        Build formatted conversation text for AI evaluation

        Args:
            blocks: List of blocks to format

        Returns:
            Formatted conversation string
        """
        lines = []

        for block in blocks:
            # Decrypt block if needed
            content = block.content if isinstance(block.content, dict) else {}

            if block.encrypted and "ciphertext" in content:
                try:
                    content = self.qube.decrypt_block_content(content)
                except Exception:
                    continue

            # Format MESSAGE blocks
            if block.block_type == "MESSAGE":
                message_type = content.get("message_type", "")
                message_body = content.get("message_body", "")
                speaker_name = content.get("speaker_name", "")

                if message_type in ["human_to_qube", "human_to_group"]:
                    speaker = speaker_name if speaker_name else self.qube.user_name
                elif message_type in ["qube_to_qube", "qube_to_human", "qube_to_group"]:
                    speaker = self.qube.qube_id
                elif message_type == "qube_to_qube_response":
                    speaker = content.get("recipient_id", "Unknown")
                else:
                    speaker = "Unknown"

                timestamp_str = datetime.fromtimestamp(block.timestamp, tz=timezone.utc).strftime("%H:%M:%S")
                lines.append(f"[Block {block.block_number} @ {timestamp_str}] {speaker}: {message_body}")

            # Format ACTION blocks
            elif block.block_type == "ACTION":
                action_type = content.get("action_type", "unknown")
                status = content.get("status", "unknown")
                timestamp_str = datetime.fromtimestamp(block.timestamp, tz=timezone.utc).strftime("%H:%M:%S")
                lines.append(f"[Block {block.block_number} @ {timestamp_str}] ACTION: {action_type} ({status})")

        return "\n".join(lines)

    async def _evaluate_relationships_with_ai(self, blocks: List[Block]) -> Dict[str, Dict[str, Any]]:
        """
        Use AI to evaluate relationship changes for all participants

        Returns dict with structure:
        {
            "entity_id": {
                "evaluation_summary": "...",
                "deltas": {
                    "honesty": 1.0,
                    "reliability": 2.5,
                    ...29 metrics total...
                    # 5 Core Trust + 14 Positive Social + 10 Negative Social + 1 Calculated (trust)
                },
                "reasoning": "...",
                "key_moments": [...],
                "message_count": 15,
                "avg_response_time_seconds": 30.5
            }
        }

        Args:
            blocks: List of blocks to evaluate

        Returns:
            Dictionary of entity_id -> evaluation data
        """
        # Extract participants
        participants = self._extract_all_participants(blocks)

        if not participants:
            logger.warning(
                "no_participants_for_ai_evaluation",
                blocks_count=len(blocks),
                block_types=[b.block_type for b in blocks[:5]]  # Show first 5 block types
            )
            return {}

        # Check if AI reasoner is available
        if not hasattr(self.qube, 'reasoner') or not self.qube.reasoner:
            logger.warning("no_reasoner_for_relationship_evaluation")
            return {}

        # Build conversation context
        conversation_text = self._build_conversation_context_for_eval(blocks)

        # Construct AI prompt
        prompt = f"""Evaluate relationship changes for each participant based on this conversation.

CONVERSATION:
{conversation_text}

PARTICIPANTS TO EVALUATE: {', '.join(participants)}

For EACH participant, provide deltas (-5 to +5) for these 36 metrics:

CORE TRUST METRICS (5 AI-evaluated, 0-100 scale):
These are foundational earned qualities that define trust:
- honesty: How truthful/transparent were they?
- reliability: How dependable/consistent were they?
- support: How much emotional/practical help did they provide?
- loyalty: How committed are they to the relationship?
- respect: How much regard, admiration, and value do they show?

POSITIVE SOCIAL METRICS (14 AI-evaluated, 0-100 scale):
- friendship: How warm, friendly, and companionable?
- affection: How caring and emotionally connected?
- engagement: How invested in conversations?
- depth: How meaningful vs superficial were exchanges?
- humor: How much playfulness, fun, levity?
- understanding: How much empathy, listening, comprehension?
- compatibility: How well do personalities/styles align? (Overall fit, not romantic compatibility)
- admiration: Do you look up to them? Respect their achievements?
- warmth: How much emotional warmth, kindness, gentleness?
- openness: How vulnerable? How much personal sharing?
- patience: How tolerant and understanding under stress?
- empowerment: Do they help you grow and improve?
- responsiveness: How quickly did they respond?
- expertise: What knowledge/competence did they demonstrate?

NEGATIVE SOCIAL METRICS (10 AI-evaluated, 0-100 scale):
- antagonism: Active hostility or opposition shown?
- resentment: Bitterness or grudges held?
- annoyance: Irritation or minor frustrations?
- distrust: Suspicion, doubt, lack of confidence?
- rivalry: Competitive tension?
- tension: Unresolved conflict or awkwardness?
- condescension: Talking down or patronizing?
- manipulation: Deceptive tactics or using you?
- dismissiveness: Invalidation or not taking seriously?
- betrayal: Major broken trust events?

BEHAVIORAL/COMMUNICATION METRICS (6 AI-evaluated, 0-100 scale):
- verbosity: How much do they write/talk? (0=very terse, 100=very verbose)
- punctuality: Do they respond/show up on time? (0=always late, 100=always punctual)
- emotional_stability: How consistent is their emotional state? (0=volatile, 100=very stable)
- directness: How plainly do they communicate? (0=indirect/hints, 100=very direct)
- energy_level: What's their activity/engagement level? (0=low energy, 100=high energy)
- humor_style: What type of humor? (0=literal/serious, 50=balanced, 100=very sarcastic/playful)

NOTE: Positive metrics increase warmth/connection. Negative metrics track problems. Both can coexist.

TRAIT DETECTION (OPTIONAL but helpful):
If you can identify personality traits from this conversation, list them.
Examples: reliable, flirty, supportive, analytical, verbose, manipulative, patient, warm, direct, etc.
Only include traits you're confident about based on the conversation evidence.

Return JSON with this structure:
{{
  "entity_id_1": {{
    "evaluation_summary": "Brief summary of this person's behavior",
    "deltas": {{
      "honesty": 1.0, "reliability": 2.5, "support": 2.2, "loyalty": 0.8, "respect": 1.8,
      "friendship": 2.0, "affection": 1.5, "engagement": 3.0, "depth": 1.5,
      "humor": 1.0, "understanding": 2.0, "compatibility": 0.5, "admiration": 1.2,
      "warmth": 1.8, "openness": 0.5, "patience": 1.0, "empowerment": 0.3,
      "responsiveness": 3.0, "expertise": 1.5,
      "antagonism": 0.0, "resentment": 0.0, "annoyance": 0.0, "distrust": 0.0,
      "rivalry": 0.0, "tension": 0.0, "condescension": 0.0, "manipulation": 0.0,
      "dismissiveness": 0.0, "betrayal": 0.0,
      "verbosity": 0.0, "punctuality": 0.0, "emotional_stability": 0.0,
      "directness": 0.0, "energy_level": 0.0, "humor_style": 0.0
    }},
    "reasoning": "Detailed explanation of deltas",
    "key_moments": ["Block 42: Did X", "Block 58: Said Y"],
    "message_count": 15,
    "avg_response_time_seconds": 30.5,
    "detected_traits": ["trait1", "trait2"],
    "trait_evidence": {{
      "trait1": "Evidence from conversation supporting this trait"
    }}
  }}
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        try:
            # Call AI with temperature 0.3 for consistent evaluation
            logger.debug("calling_ai_for_evaluation", prompt_length=len(prompt), participants=list(participants))
            response = await self.qube.reasoner.process_input(
                input_message=prompt,
                temperature=0.3
            )

            logger.debug("ai_response_received", response_length=len(response), response_preview=response[:500])

            # Parse JSON response
            # Try to extract JSON if there's text before/after
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                evaluation_data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("No JSON object found in response", response, 0)

            logger.info(
                "ai_relationship_evaluation_completed",
                participants_evaluated=len(evaluation_data),
                total_blocks=len(blocks),
                evaluation_keys=list(evaluation_data.keys())
            )

            return evaluation_data

        except json.JSONDecodeError as e:
            logger.error(
                "ai_evaluation_json_parse_failed",
                error=str(e),
                response_preview=response[:500] if 'response' in locals() else None,
                response_full=response if 'response' in locals() else None
            )
            return {}
        except Exception as e:
            logger.error(
                "ai_relationship_evaluation_failed",
                error=str(e),
                participants=list(participants),
                blocks_count=len(blocks),
                exc_info=True
            )
            return {}

    def _apply_relationship_deltas_from_summary(self, relationships_affected: Dict[str, Dict[str, Any]]) -> None:
        """
        Apply AI-evaluated deltas to relationships

        Args:
            relationships_affected: Dict from _evaluate_relationships_with_ai()
        """
        if not relationships_affected:
            logger.debug("no_relationships_to_update_from_summary")
            return

        for entity_id, evaluation in relationships_affected.items():
            try:
                # Get or create relationship
                rel = self.qube.relationships.get_or_create_relationship(
                    entity_id=entity_id,
                    entity_type="qube" if entity_id != self.qube.user_name else "human",
                    has_met=True
                )

                # Apply deltas from AI evaluation
                deltas = evaluation.get("deltas", {})

                # Core Trust Metrics (5 AI-evaluated)
                for metric in ["honesty", "reliability", "support", "loyalty", "respect"]:
                    if metric in deltas:
                        delta = deltas[metric]
                        current = getattr(rel, metric)
                        setattr(rel, metric, max(0.0, min(100.0, current + delta)))

                # Social Metrics - Positive (14 AI-evaluated)
                for metric in ["friendship", "affection", "engagement", "depth", "humor",
                              "understanding", "compatibility", "admiration", "warmth",
                              "openness", "patience", "empowerment", "responsiveness", "expertise"]:
                    if metric in deltas:
                        delta = deltas[metric]
                        current = getattr(rel, metric)
                        setattr(rel, metric, max(0.0, min(100.0, current + delta)))

                # Social Metrics - Negative (10 AI-evaluated)
                for metric in ["antagonism", "resentment", "annoyance", "distrust", "rivalry",
                              "tension", "condescension", "manipulation", "dismissiveness", "betrayal"]:
                    if metric in deltas:
                        delta = deltas[metric]
                        current = getattr(rel, metric)
                        setattr(rel, metric, max(0.0, min(100.0, current + delta)))

                # Update trust score (calculated from 5 core trust components)
                rel.update_trust_score()

                # Update message counts from evaluation
                message_count = evaluation.get("message_count", 0)
                if message_count > 0:
                    rel.messages_received += message_count

                # Update response time average if provided
                avg_response_time = evaluation.get("avg_response_time_seconds")
                if avg_response_time:
                    if rel.messages_received > 1:
                        old_avg = rel.response_time_avg
                        new_avg = (
                            (old_avg * (rel.messages_received - message_count) + avg_response_time * message_count)
                            / rel.messages_received
                        )
                        rel.response_time_avg = new_avg
                    else:
                        rel.response_time_avg = avg_response_time

                # Update last interaction timestamp
                rel.last_interaction = int(datetime.now(timezone.utc).timestamp())

                # Update days known
                rel.update_days_known()

                # Store AI evaluation in history
                rel.evaluations.append({
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                    "summary": evaluation.get("evaluation_summary", ""),
                    "reasoning": evaluation.get("reasoning", ""),
                    "key_moments": evaluation.get("key_moments", []),
                    "deltas": deltas
                })

                # Detect and update traits
                try:
                    trait_definitions = load_trait_definitions()
                    trait_detector = TraitDetector(
                        trait_definitions=trait_definitions,
                        difficulty=getattr(self, 'relationship_difficulty', 'long'),
                        trust_personality=getattr(self.qube, 'trust_personality', 'balanced'),
                    )

                    # Get AI-detected traits from evaluation if present
                    ai_detected = evaluation.get("detected_traits", [])
                    ai_evidence = evaluation.get("trait_evidence", {})

                    # Store old trait scores for comparison
                    old_trait_scores = dict(rel.trait_scores)

                    # Detect traits
                    new_trait_scores = trait_detector.detect_traits(
                        rel,
                        evaluation,
                        ai_detected=ai_detected,
                        ai_evidence=ai_evidence,
                    )

                    # Update relationship trait scores
                    rel.trait_scores = {
                        name: score.to_dict() if hasattr(score, 'to_dict') else score
                        for name, score in new_trait_scores.items()
                    }

                    # Log significant trait changes to evolution
                    for trait_name, new_score in new_trait_scores.items():
                        old_score_data = old_trait_scores.get(trait_name, {})
                        old_score_value = old_score_data.get("score", 0) if isinstance(old_score_data, dict) else 0

                        if abs(new_score.score - old_score_value) > 5:
                            rel.trait_evolution.append({
                                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                                "trait": trait_name,
                                "old_score": old_score_value,
                                "new_score": new_score.score,
                                "evaluation_index": len(rel.evaluations) - 1,
                            })

                    # Build trait_changes for SUMMARY block display
                    trait_changes = {}
                    assigned = []
                    strengthened = []
                    weakened = []

                    for trait_name, new_score in new_trait_scores.items():
                        old_score_data = old_trait_scores.get(trait_name, {})
                        old_score_value = old_score_data.get("score", 0) if isinstance(old_score_data, dict) else 0

                        if trait_name not in old_trait_scores:
                            assigned.append(trait_name)
                        elif new_score.score > old_score_value + 3:
                            strengthened.append(trait_name)
                        elif new_score.score < old_score_value - 3:
                            weakened.append(trait_name)

                    if assigned or strengthened or weakened:
                        trait_changes[entity_id] = {
                            "assigned": assigned,
                            "strengthened": strengthened,
                            "weakened": weakened,
                            "removed": [],
                        }

                    # Update the evaluation record with trait changes
                    if trait_changes and rel.evaluations:
                        rel.evaluations[-1]["trait_changes"] = trait_changes

                    logger.debug("traits_detected", entity_id=entity_id,
                               trait_count=len(new_trait_scores),
                               confident_count=len([t for t in new_trait_scores.values() if t.is_confident]))

                except Exception as e:
                    logger.error("trait_detection_failed", entity_id=entity_id, error=str(e))

                # Check for relationship progression
                self.qube.relationships.check_progression(entity_id)

                # Save changes
                self.qube.relationships.storage.save()

                logger.info(
                    "relationship_deltas_applied_from_ai",
                    entity_id=entity_id,
                    trust_score=rel.trust,
                    status=rel.status,
                    deltas_applied=len(deltas)
                )

            except Exception as e:
                logger.error(
                    "relationship_delta_application_failed",
                    entity_id=entity_id,
                    error=str(e),
                    exc_info=True
                )

    def _create_relationship_eagerly(self, block: Block) -> None:
        """
        Create relationship immediately when MESSAGE block is created.
        Metrics start at 0.0 and get updated by AI during SUMMARY block creation.

        Args:
            block: MESSAGE block to process
        """
        content = block.content if isinstance(block.content, dict) else {}
        message_type = content.get("message_type", "")

        # Determine entity_id and entity_type
        entity_id = None
        entity_type = "qube"

        # Extract participant from message
        if message_type in ["human_to_qube", "human_to_group"]:
            # Human sender - use speaker_name or fall back to user_name
            entity_id = content.get("speaker_name", self.qube.user_name)
            entity_type = "human"
        elif message_type in ["qube_to_qube", "qube_to_qube_response"]:
            # Qube sender/recipient
            if message_type == "qube_to_qube":
                entity_id = content.get("recipient_id")
            else:
                entity_id = content.get("sender_id")
            entity_type = "qube"
        elif message_type in ["qube_to_human"]:
            # Human recipient
            entity_id = self.qube.user_name
            entity_type = "human"
        elif message_type in ["qube_to_group", "human_to_group"]:
            # Group - extract all participants
            group_participants = content.get("participants", [])
            for participant_id in group_participants:
                if participant_id != self.qube.qube_id:
                    # Create relationship for each group participant
                    self.qube.relationships.get_or_create_relationship(
                        entity_id=participant_id,
                        entity_type="qube",  # Assume qubes in group
                        has_met=True
                    )
            # Also handle human speaker in group
            if message_type == "human_to_group":
                speaker_name = content.get("speaker_name", self.qube.user_name)
                self.qube.relationships.get_or_create_relationship(
                    entity_id=speaker_name,
                    entity_type="human",
                    has_met=True
                )
            return  # Early return for group messages

        # Skip if no valid entity_id
        if not entity_id or entity_id == self.qube.qube_id:
            return

        # Create or get relationship
        rel = self.qube.relationships.get_or_create_relationship(
            entity_id=entity_id,
            entity_type=entity_type,
            has_met=True
        )

        # Update message counters eagerly
        if message_type in ["qube_to_qube", "qube_to_human", "qube_to_group"]:
            rel.messages_sent += 1
        elif message_type in ["human_to_qube", "qube_to_qube_response", "human_to_group"]:
            rel.messages_received += 1

        # Update last interaction timestamp
        rel.last_interaction = block.timestamp

        # Update days known
        rel.update_days_known()

        # Save immediately so relationships.json exists
        self.qube.relationships.storage.save()

        logger.debug(
            "relationship_created_eagerly",
            entity_id=entity_id,
            entity_type=entity_type,
            messages_sent=rel.messages_sent,
            messages_received=rel.messages_received
        )

    def cleanup(self) -> None:
        """Remove all session blocks after successful anchoring or discarding"""
        from pathlib import Path
        import time

        session_dir = Path(self.qube.data_dir) / "blocks" / "session"
        if session_dir.exists():
            # Delete all JSON files in session directory
            failed_files = []
            for block_file in session_dir.glob("*.json"):
                # Retry deletion with backoff (files may be locked on Windows)
                for attempt in range(3):
                    try:
                        block_file.unlink()
                        logger.debug("session_block_deleted", file=block_file.name)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(0.1 * (attempt + 1))  # 100ms, 200ms backoff
                        else:
                            failed_files.append(block_file.name)
                            logger.warning("session_block_delete_failed", file=block_file.name, error="Permission denied")
                    except Exception as e:
                        failed_files.append(block_file.name)
                        logger.warning("session_block_delete_failed", file=block_file.name, error=str(e))
                        break

            if failed_files:
                logger.warning("some_session_blocks_not_deleted", count=len(failed_files), files=failed_files)


    @staticmethod
    def recover_session(qube) -> Optional["Session"]:
        """
        Recover interrupted session from disk

        Loads individual block files from blocks/session/ directory

        Args:
            qube: Qube instance

        Returns:
            Recovered Session or None if no session blocks exist
        """
        from pathlib import Path

        session_dir = Path(qube.data_dir) / "blocks" / "session"

        if not session_dir.exists():
            return None

        try:
            # Load all block files from session directory
            block_files = sorted(session_dir.glob("*.json"))

            if not block_files:
                return None  # No session to recover

            session_blocks = []

            for block_file in block_files:
                with open(block_file, 'r') as f:
                    block_data = json.load(f)
                    block = Block.from_dict(block_data)
                    session_blocks.append(block)

            # Create session with "active" ID
            session = Session(qube, session_id="active")
            session.session_blocks = session_blocks

            # Reindex blocks by timestamp (this is the source of truth)
            # This fixes any blocks that had incorrect indices (e.g., all -1)
            session._reindex_session_blocks()

            # Determine session_start from earliest block
            if session_blocks:
                session.session_start = min(b.timestamp for b in session_blocks)

                # Emit session updated event with recovered block count
                from core.events import Events
                qube.events.emit(Events.SESSION_UPDATED, {
                    "session_block_count": len(session_blocks)
                })
            else:
                session.session_start = int(datetime.now(timezone.utc).timestamp())

            logger.info("session_recovered", blocks=len(session.session_blocks))

            return session

        except Exception as e:
            logger.error("session_recovery_failed", exc_info=True)
            raise SessionRecoveryError(
                f"Failed to recover session",
                context={"qube_id": qube.qube_id},
                cause=e
            )
