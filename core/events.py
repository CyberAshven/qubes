"""
Chain State Event System

Event-driven architecture for chain_state modifications.
All state changes flow through events, providing:
- Single entry point for all state changes
- Audit logging of every modification
- Push notifications to subscribers (GUI)
- Clear contract of what can change state

Usage:
    # Emit an event (this updates chain_state and notifies subscribers)
    qube.events.emit(Events.TRANSACTION_SENT, {
        "txid": "abc123",
        "amount_satoshis": 10000,
        "to_address": "bitcoincash:qr..."
    })

    # Subscribe to events (e.g., GUI)
    qube.events.subscribe(my_callback)
"""

from enum import Enum
from typing import Dict, Any, List, Callable, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import time

from utils.logging import get_logger

if TYPE_CHECKING:
    from core.chain_state import ChainState

logger = get_logger(__name__)


class Events(str, Enum):
    """
    All events that can modify chain_state.

    Naming convention: NOUN_VERB (e.g., TRANSACTION_SENT, SESSION_STARTED)
    """

    # =========================================================================
    # FINANCIAL EVENTS
    # =========================================================================
    TRANSACTION_SENT = "transaction_sent"
    TRANSACTION_RECEIVED = "transaction_received"
    TRANSACTION_CONFIRMED = "transaction_confirmed"
    PENDING_TX_CREATED = "pending_tx_created"
    PENDING_TX_APPROVED = "pending_tx_approved"
    PENDING_TX_REJECTED = "pending_tx_rejected"
    PENDING_TX_EXPIRED = "pending_tx_expired"
    WALLET_SYNCED = "wallet_synced"
    BALANCE_UPDATED = "balance_updated"

    # =========================================================================
    # SESSION EVENTS
    # =========================================================================
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    SESSION_UPDATED = "session_updated"
    MESSAGE_SENT = "message_sent"          # Qube sends (qube_to_human, qube_to_group, qube_to_qube)
    MESSAGE_RECEIVED = "message_received"  # Qube receives (human_to_qube, human_to_group, qube_to_qube_response)

    # =========================================================================
    # CHAIN EVENTS
    # =========================================================================
    BLOCK_ADDED = "block_added"
    CHAIN_UPDATED = "chain_updated"
    ANCHOR_CREATED = "anchor_created"
    SUMMARY_CREATED = "summary_created"

    # =========================================================================
    # STATS EVENTS
    # =========================================================================
    TOKENS_USED = "tokens_used"
    API_CALL_MADE = "api_call_made"
    TOOL_CALLED = "tool_called"

    # =========================================================================
    # SETTINGS EVENTS
    # =========================================================================
    SETTINGS_UPDATED = "settings_updated"
    MODEL_CHANGED = "model_changed"
    MODEL_LOCKED = "model_locked"
    MODEL_UNLOCKED = "model_unlocked"
    MODEL_PREFERENCE_SET = "model_preference_set"
    AUTO_ANCHOR_UPDATED = "auto_anchor_updated"
    REVOLVER_MODE_TOGGLED = "revolver_mode_toggled"
    AUTONOMOUS_MODE_TOGGLED = "autonomous_mode_toggled"
    TTS_TOGGLED = "tts_toggled"
    VOICE_MODEL_CHANGED = "voice_model_changed"
    VISUALIZER_TOGGLED = "visualizer_toggled"

    # =========================================================================
    # RUNTIME EVENTS
    # =========================================================================
    RUNTIME_UPDATED = "runtime_updated"
    WENT_ONLINE = "went_online"
    WENT_OFFLINE = "went_offline"

    # =========================================================================
    # IDENTITY EVENTS
    # =========================================================================
    AVATAR_UPDATED = "avatar_updated"

    # =========================================================================
    # RELATIONSHIP EVENTS
    # =========================================================================
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_UPDATED = "relationship_updated"
    TRUST_SCORE_CHANGED = "trust_score_changed"

    # =========================================================================
    # SKILLS EVENTS
    # =========================================================================
    SKILL_UNLOCKED = "skill_unlocked"
    XP_GAINED = "xp_gained"
    SKILLS_UPDATED = "skills_updated"

    # =========================================================================
    # MOOD EVENTS
    # =========================================================================
    MOOD_CHANGED = "mood_changed"
    ENERGY_CHANGED = "energy_changed"
    STRESS_CHANGED = "stress_changed"

    # =========================================================================
    # OWNER EVENTS
    # =========================================================================
    OWNER_INFO_UPDATED = "owner_info_updated"

    # =========================================================================
    # CLEARANCE EVENTS
    # =========================================================================
    CLEARANCE_PROFILE_SET = "clearance_profile_set"
    CLEARANCE_TAG_SET = "clearance_tag_set"

    # =========================================================================
    # GENERIC EVENTS
    # =========================================================================
    SECTION_UPDATED = "section_updated"


class ChainStateEvent:
    """
    Represents a single event that modifies chain_state.

    Attributes:
        event_type: The type of event (from Events enum)
        payload: Event-specific data
        timestamp: When the event occurred (Unix timestamp)
        source: Where the event originated (backend, gui, sync, etc.)
    """

    def __init__(
        self,
        event_type: Events,
        payload: Dict[str, Any],
        source: str = "backend"
    ):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = int(datetime.now(timezone.utc).timestamp())
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source
        }

    def __repr__(self):
        return f"ChainStateEvent({self.event_type.value}, source={self.source})"


# Type alias for event callbacks
EventCallback = Callable[[ChainStateEvent], None]


class ChainStateEventBus:
    """
    Central event bus for all chain_state modifications.

    Responsibilities:
    1. Receive events from any part of the system
    2. Log events for audit trail
    3. Dispatch to appropriate chain_state handler
    4. Notify subscribers (GUI, etc.)

    Usage:
        event_bus = ChainStateEventBus(chain_state)

        # Subscribe to events
        event_bus.subscribe(lambda e: print(f"Event: {e.event_type}"))

        # Emit events
        event_bus.emit(Events.TRANSACTION_SENT, {"txid": "abc", "amount": 1000})
    """

    def __init__(self, chain_state: "ChainState"):
        self.chain_state = chain_state
        self._subscribers: List[EventCallback] = []
        self._event_log: List[ChainStateEvent] = []  # Recent events for debugging
        self._max_log_size = 100

    def subscribe(self, callback: EventCallback) -> None:
        """Subscribe to all events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            logger.debug("event_subscriber_added", total=len(self._subscribers))

    def unsubscribe(self, callback: EventCallback) -> None:
        """Unsubscribe from events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.debug("event_subscriber_removed", total=len(self._subscribers))

    def emit(
        self,
        event_type: Events,
        payload: Dict[str, Any],
        source: str = "backend"
    ) -> ChainStateEvent:
        """
        Emit an event to update chain_state and notify subscribers.

        Args:
            event_type: The type of event
            payload: Event-specific data
            source: Origin of the event (backend, gui, sync, etc.)

        Returns:
            The created ChainStateEvent
        """
        event = ChainStateEvent(event_type, payload, source)

        # 1. Log the event
        logger.info(
            "chain_state_event",
            event_type=event_type.value,
            source=source,
            payload_keys=list(payload.keys())
        )

        # 2. Add to event log (for debugging)
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # 3. Handle the event (update chain_state)
        try:
            self._handle_event(event)
        except Exception as e:
            logger.error(
                "event_handler_failed",
                event_type=event_type.value,
                error=str(e),
                exc_info=True
            )
            raise

        # 4. Notify subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.warning(
                    "event_subscriber_error",
                    event_type=event_type.value,
                    error=str(e)
                )

        return event

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent events for debugging."""
        return [e.to_dict() for e in self._event_log[-limit:]]

    def _handle_event(self, event: ChainStateEvent) -> None:
        """
        Dispatch event to appropriate chain_state handler.

        This is the ONLY place where chain_state should be modified.
        """
        cs = self.chain_state
        payload = event.payload

        # =====================================================================
        # FINANCIAL HANDLERS
        # =====================================================================
        if event.event_type == Events.TRANSACTION_SENT:
            cs.add_transaction({
                "txid": payload.get("txid"),
                "direction": "sent",
                "to_address": payload.get("to_address"),
                "amount_satoshis": payload.get("amount_satoshis"),
                "amount_bch": payload.get("amount_satoshis", 0) / 100_000_000,
                "fee": payload.get("fee", 0),
                "memo": payload.get("memo"),
                "timestamp": event.timestamp,
                "status": payload.get("status", "broadcast"),
                "auto_approved": payload.get("auto_approved", False)
            })

        elif event.event_type == Events.TRANSACTION_RECEIVED:
            cs.add_transaction({
                "txid": payload.get("txid"),
                "direction": "received",
                "from_address": payload.get("from_address"),
                "amount_satoshis": payload.get("amount_satoshis"),
                "amount_bch": payload.get("amount_satoshis", 0) / 100_000_000,
                "timestamp": event.timestamp,
                "status": payload.get("status", "confirmed"),
                "confirmations": payload.get("confirmations", 0)
            })

        elif event.event_type == Events.PENDING_TX_CREATED:
            cs.add_pending_transaction(payload)

        elif event.event_type in (Events.PENDING_TX_APPROVED, Events.PENDING_TX_REJECTED, Events.PENDING_TX_EXPIRED):
            tx_id = payload.get("tx_id")
            if tx_id:
                cs.remove_pending_transaction(tx_id)
            # If approved, the TRANSACTION_SENT event should follow

        elif event.event_type == Events.WALLET_SYNCED:
            cs.update_wallet(
                balance_satoshis=payload.get("balance_satoshis"),
                balance_bch=payload.get("balance_satoshis", 0) / 100_000_000,
                last_sync=event.timestamp,
                utxo_count=payload.get("utxo_count")
            )

        elif event.event_type == Events.BALANCE_UPDATED:
            cs.update_wallet(
                balance_satoshis=payload.get("balance_satoshis"),
                balance_bch=payload.get("balance_satoshis", 0) / 100_000_000,
                unconfirmed_satoshis=payload.get("unconfirmed_satoshis")
            )

        # =====================================================================
        # SESSION HANDLERS
        # =====================================================================
        elif event.event_type == Events.SESSION_STARTED:
            cs.start_session(payload.get("session_id"))

        elif event.event_type == Events.SESSION_ENDED:
            cs.end_session()

        elif event.event_type == Events.SESSION_UPDATED:
            cs.update_session(**payload)

        elif event.event_type == Events.MESSAGE_SENT:
            cs.increment_message_sent()
            # Always update last_message_at
            session_update = payload.get("session_update", {})
            session_update["last_message_at"] = event.timestamp
            cs.update_session(**session_update)

        elif event.event_type == Events.MESSAGE_RECEIVED:
            cs.increment_message_received()
            # Always update last_message_at
            session_update = payload.get("session_update", {})
            session_update["last_message_at"] = event.timestamp
            cs.update_session(**session_update)

        # =====================================================================
        # CHAIN HANDLERS
        # =====================================================================
        elif event.event_type == Events.BLOCK_ADDED:
            block_type = payload.get("block_type", "MESSAGE")
            is_session_block = payload.get("is_session_block", False)
            cs.increment_block_count(block_type, is_session_block=is_session_block)
            if payload.get("chain_update"):
                cs.update_chain(**payload.get("chain_update"))

        elif event.event_type == Events.CHAIN_UPDATED:
            cs.update_chain(**payload)

        elif event.event_type == Events.ANCHOR_CREATED:
            cs.increment_anchor()
            if payload.get("chain_update"):
                cs.update_chain(**payload.get("chain_update"))

        elif event.event_type == Events.SUMMARY_CREATED:
            cs.increment_block_count("SUMMARY")
            if payload.get("chain_update"):
                cs.update_chain(**payload.get("chain_update"))

        # =====================================================================
        # STATS HANDLERS
        # =====================================================================
        elif event.event_type == Events.TOKENS_USED:
            # Compute total tokens from input + output
            input_tokens = payload.get("input_tokens", 0) or 0
            output_tokens = payload.get("output_tokens", 0) or 0
            total_tokens = input_tokens + output_tokens
            cs.add_tokens(
                model=payload.get("model"),
                tokens=total_tokens,
                cost=payload.get("cost", 0.0) or 0.0
            )
            # Also update session's context_window_used
            session = cs.state.get("session", {})
            current_context = session.get("context_window_used", 0)
            cs.update_session(context_window_used=current_context + total_tokens)

        elif event.event_type == Events.API_CALL_MADE:
            # Skip updating runtime model for internal calls (e.g., self-evaluation)
            # to avoid overwriting the user-facing model
            if not payload.get("is_internal", False):
                cs.record_api_call(
                    model=payload.get("model"),
                    provider=payload.get("provider")
                )

        elif event.event_type == Events.TOOL_CALLED:
            tool_name = payload.get("tool_name")
            if tool_name:
                cs.increment_tool_call(tool_name)

        # =====================================================================
        # SETTINGS HANDLERS
        # =====================================================================
        elif event.event_type == Events.SETTINGS_UPDATED:
            from_gui = event.source == "gui"
            cs.update_settings(payload.get("settings", {}), from_gui=from_gui)

        elif event.event_type == Events.MODEL_CHANGED:
            cs.set_current_model_override(payload.get("model"))

        elif event.event_type == Events.MODEL_PREFERENCE_SET:
            cs.set_model_preference(
                task_type=payload.get("task_type"),
                model=payload.get("model"),
                reason=payload.get("reason")
            )

        elif event.event_type == Events.AUTO_ANCHOR_UPDATED:
            cs.set_auto_anchor(
                individual_enabled=payload.get("individual_enabled"),
                individual_threshold=payload.get("individual_threshold"),
                group_enabled=payload.get("group_enabled"),
                group_threshold=payload.get("group_threshold")
            )

        # =====================================================================
        # RUNTIME HANDLERS
        # =====================================================================
        elif event.event_type == Events.RUNTIME_UPDATED:
            cs.update_runtime(**payload)

        elif event.event_type == Events.WENT_ONLINE:
            cs.update_runtime(is_online=True)

        elif event.event_type == Events.WENT_OFFLINE:
            cs.update_runtime(is_online=False)

        # =====================================================================
        # IDENTITY HANDLERS
        # =====================================================================
        elif event.event_type == Events.AVATAR_UPDATED:
            cs.set_avatar_description(payload.get("description"))

        # =====================================================================
        # RELATIONSHIP HANDLERS
        # =====================================================================
        elif event.event_type in (Events.RELATIONSHIP_CREATED, Events.RELATIONSHIP_UPDATED, Events.TRUST_SCORE_CHANGED):
            cs.update_relationships(payload.get("data", {}))

        # =====================================================================
        # SKILLS HANDLERS
        # =====================================================================
        elif event.event_type == Events.SKILLS_UPDATED:
            # Direct skills section update
            cs.state["skills"] = payload.get("skills_data", {})
            cs._save()

        elif event.event_type == Events.SKILL_UNLOCKED:
            skill_name = payload.get("skill_name")
            if skill_name:
                skills = cs.state.setdefault("skills", {"unlocked": []})
                if skill_name not in skills.get("unlocked", []):
                    skills.setdefault("unlocked", []).append(skill_name)
                    cs._save()

        elif event.event_type == Events.XP_GAINED:
            xp_amount = payload.get("amount", 0)
            skills = cs.state.setdefault("skills", {"total_xp": 0})
            skills["total_xp"] = skills.get("total_xp", 0) + xp_amount
            skills["last_xp_gain"] = event.timestamp
            cs._save()

        # =====================================================================
        # MOOD HANDLERS
        # =====================================================================
        elif event.event_type == Events.MOOD_CHANGED:
            cs.update_mood(
                mood=payload.get("mood"),
                energy_level=payload.get("energy_level"),
                stress_level=payload.get("stress_level")
            )

        # =====================================================================
        # OWNER HANDLERS
        # =====================================================================
        elif event.event_type == Events.OWNER_INFO_UPDATED:
            cs.set_owner_field(
                field_name=payload.get("field_name"),
                value=payload.get("value")
            )

        # =====================================================================
        # CLEARANCE HANDLERS
        # =====================================================================
        elif event.event_type == Events.CLEARANCE_PROFILE_SET:
            cs.set_custom_profile(
                name=payload.get("name"),
                profile_data=payload.get("profile_data")
            )

        elif event.event_type == Events.CLEARANCE_TAG_SET:
            cs.set_custom_tag(
                name=payload.get("name"),
                tag_data=payload.get("tag_data")
            )

        # =====================================================================
        # GENERIC HANDLERS
        # =====================================================================
        elif event.event_type == Events.SECTION_UPDATED:
            cs.update_section(
                section=payload.get("section"),
                data=payload.get("data"),
                merge=payload.get("merge", True)
            )

        else:
            logger.warning(
                "unhandled_event_type",
                event=event.event_type.value
            )
