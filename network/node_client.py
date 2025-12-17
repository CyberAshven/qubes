"""
Node Client for qube.cash Server

WebSocket client for connecting to qube.cash server for:
- Introduction relay (requesting/accepting connections)
- P2P conversations (real-time multi-qube chat)

This is the server-orchestrated P2P approach - simpler than direct libp2p,
handles NAT traversal automatically, and provides offline message queuing.
"""

import asyncio
import json
import hashlib
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from utils.logging import get_logger
from crypto.signing import sign_message

logger = get_logger(__name__)

# Server configuration
QUBE_CASH_API = "https://qube.cash/api/v2"
QUBE_CASH_WS = "wss://qube.cash/api/v2"


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class PendingIntroduction:
    """An incoming introduction request"""
    relay_id: str
    from_commitment: str
    from_name: str
    conversation_id: str
    block: Dict[str, Any]
    block_hash: str
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Connection:
    """An accepted connection (another Qube we can chat with)"""
    commitment: str
    name: str
    qube_id: str
    accepted_at: datetime
    last_seen: Optional[datetime] = None
    is_online: bool = False


class NodeClient:
    """
    WebSocket client for qube.cash server connections.

    Provides two main services:
    1. Introduction relay - for discovering and connecting with other Qubes
    2. Conversation service - for real-time P2P chat sessions
    """

    def __init__(
        self,
        commitment: str,
        private_key,
        public_key,
        qube_name: str,
        qube_id: str,
        api_base: str = QUBE_CASH_API,
        ws_base: str = QUBE_CASH_WS
    ):
        """
        Initialize the node client.

        Args:
            commitment: This Qube's NFT commitment (64-char hex)
            private_key: ECDSA private key for signing
            public_key: ECDSA public key
            qube_name: Display name of this Qube
            qube_id: 8-char Qube ID
            api_base: Base URL for REST API
            ws_base: Base URL for WebSocket connections
        """
        self.commitment = commitment
        self.private_key = private_key
        self.public_key = public_key
        self.qube_name = qube_name
        self.qube_id = qube_id
        self.api_base = api_base
        self.ws_base = ws_base

        # Connection state
        self.intro_state = ConnectionState.DISCONNECTED
        self.intro_ws = None
        self._intro_task: Optional[asyncio.Task] = None

        # Conversation connections: session_id -> websocket
        self.conv_connections: Dict[str, Any] = {}
        self.conv_states: Dict[str, ConnectionState] = {}

        # Callbacks
        self._on_introduction: Optional[Callable[[PendingIntroduction], None]] = None
        self._on_signature: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_block: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._on_session_update: Optional[Callable[[str, Dict[str, Any]], None]] = None

        # Local storage
        self.pending_introductions: Dict[str, PendingIntroduction] = {}
        self.connections: Dict[str, Connection] = {}

        logger.info(
            "node_client_initialized",
            commitment=commitment[:16],
            qube_name=qube_name
        )

    # =========================================================================
    # Introduction Relay
    # =========================================================================

    async def connect_introductions(self) -> bool:
        """
        Connect to the introduction relay WebSocket.

        This keeps a persistent connection open to receive introduction
        requests in real-time.
        """
        if self.intro_state == ConnectionState.CONNECTED:
            return True

        self.intro_state = ConnectionState.CONNECTING

        try:
            import websockets

            ws_url = f"{self.ws_base}/introductions/ws/{self.commitment}"
            logger.info("connecting_to_introduction_relay", url=ws_url[:50])

            self.intro_ws = await websockets.connect(ws_url)
            self.intro_state = ConnectionState.CONNECTED

            # Start listening task
            self._intro_task = asyncio.create_task(self._intro_listen_loop())

            logger.info("introduction_relay_connected", commitment=self.commitment[:16])
            return True

        except Exception as e:
            logger.error("introduction_relay_connection_failed", error=str(e))
            self.intro_state = ConnectionState.DISCONNECTED
            return False

    async def disconnect_introductions(self):
        """Disconnect from the introduction relay"""
        if self._intro_task:
            self._intro_task.cancel()
            try:
                await self._intro_task
            except asyncio.CancelledError:
                pass

        if self.intro_ws:
            await self.intro_ws.close()
            self.intro_ws = None

        self.intro_state = ConnectionState.DISCONNECTED
        logger.info("introduction_relay_disconnected")

    async def _intro_listen_loop(self):
        """Listen for introduction messages"""
        try:
            async for message in self.intro_ws:
                try:
                    data = json.loads(message)
                    await self._handle_intro_message(data)
                except json.JSONDecodeError:
                    logger.warning("invalid_intro_message", message=message[:100])

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("intro_listen_error", error=str(e))
            self.intro_state = ConnectionState.DISCONNECTED
            # TODO: Implement reconnection logic

    async def _handle_intro_message(self, data: Dict[str, Any]):
        """Handle an incoming introduction message"""
        msg_type = data.get("type")

        if msg_type == "introduction":
            # Incoming introduction request
            intro = PendingIntroduction(
                relay_id=data["relay_id"],
                from_commitment=data["from_commitment"],
                from_name=data["from_name"],
                conversation_id=data["conversation_id"],
                block=data["block"],
                block_hash=data["block_hash"]
            )

            self.pending_introductions[intro.relay_id] = intro

            logger.info(
                "introduction_received",
                from_name=intro.from_name,
                relay_id=intro.relay_id
            )

            if self._on_introduction:
                self._on_introduction(intro)

        elif msg_type == "signature":
            # Response to our introduction request
            logger.info(
                "signature_received",
                response_type=data.get("response_type"),
                from_name=data.get("responder_name")
            )

            if self._on_signature:
                self._on_signature(data)

    async def send_introduction(
        self,
        to_commitment: str,
        message: str = "Hello! I'd like to connect."
    ) -> Dict[str, Any]:
        """
        Send an introduction request to another Qube.

        Args:
            to_commitment: NFT commitment of the Qube to introduce to
            message: Optional message to include

        Returns:
            Response with relay_id and status
        """
        import aiohttp

        # Create the introduction block
        conversation_id = f"intro_{self.commitment[:8]}_{to_commitment[:8]}_{int(datetime.utcnow().timestamp())}"

        block = {
            "type": "INTRODUCTION",
            "from_commitment": self.commitment,
            "from_name": self.qube_name,
            "from_qube_id": self.qube_id,
            "to_commitment": to_commitment,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Hash and sign the block
        block_json = json.dumps(block, sort_keys=True)
        block_hash = hashlib.sha256(block_json.encode()).hexdigest()
        signature = sign_message(self.private_key, block_hash)

        block["signature"] = signature

        # Send via REST API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/introductions/relay",
                json={
                    "block": block,
                    "block_hash": block_hash,
                    "from_commitment": self.commitment,
                    "from_name": self.qube_name,
                    "to_commitment": to_commitment,
                    "conversation_id": conversation_id
                }
            ) as resp:
                result = await resp.json()

                logger.info(
                    "introduction_sent",
                    to_commitment=to_commitment[:16],
                    status=result.get("status")
                )

                return result

    async def accept_introduction(self, relay_id: str) -> bool:
        """
        Accept a pending introduction request.

        Args:
            relay_id: The relay ID of the introduction to accept

        Returns:
            True if accepted successfully
        """
        intro = self.pending_introductions.get(relay_id)
        if not intro:
            logger.error("introduction_not_found", relay_id=relay_id)
            return False

        # Sign the block hash to indicate acceptance
        signature = sign_message(self.private_key, intro.block_hash)

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/introductions/signature",
                json={
                    "conversation_id": intro.conversation_id,
                    "block_hash": intro.block_hash,
                    "signature": signature,
                    "signer_commitment": self.commitment,
                    "response_type": "accepted",
                    "responder_name": self.qube_name
                }
            ) as resp:
                if resp.status == 200:
                    # Add to connections
                    self.connections[intro.from_commitment] = Connection(
                        commitment=intro.from_commitment,
                        name=intro.from_name,
                        qube_id=intro.block.get("from_qube_id", ""),
                        accepted_at=datetime.utcnow()
                    )

                    # Remove from pending
                    del self.pending_introductions[relay_id]

                    # Acknowledge receipt
                    if self.intro_ws:
                        await self.intro_ws.send(json.dumps({
                            "type": "ack",
                            "relay_id": relay_id
                        }))

                    logger.info(
                        "introduction_accepted",
                        from_name=intro.from_name,
                        from_commitment=intro.from_commitment[:16]
                    )

                    return True

        return False

    async def reject_introduction(self, relay_id: str) -> bool:
        """Reject a pending introduction request"""
        intro = self.pending_introductions.get(relay_id)
        if not intro:
            return False

        signature = sign_message(self.private_key, intro.block_hash)

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/introductions/signature",
                json={
                    "conversation_id": intro.conversation_id,
                    "block_hash": intro.block_hash,
                    "signature": signature,
                    "signer_commitment": self.commitment,
                    "response_type": "rejected",
                    "responder_name": self.qube_name
                }
            ) as resp:
                if resp.status == 200:
                    del self.pending_introductions[relay_id]

                    if self.intro_ws:
                        await self.intro_ws.send(json.dumps({
                            "type": "ack",
                            "relay_id": relay_id
                        }))

                    logger.info("introduction_rejected", relay_id=relay_id)
                    return True

        return False

    async def get_online_qubes(self) -> List[str]:
        """Get list of currently online Qube commitments"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/introductions/online") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("online", [])
        return []

    # =========================================================================
    # P2P Conversations
    # =========================================================================

    async def create_session(
        self,
        participant_commitments: List[str],
        topic: str = "",
        mode: str = "open_discussion"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new P2P conversation session.

        Args:
            participant_commitments: NFT commitments of Qubes to invite
            topic: Optional conversation topic
            mode: Conversation mode

        Returns:
            Session info including session_id
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/conversation/sessions",
                json={
                    "creator_commitment": self.commitment,
                    "participant_commitments": participant_commitments,
                    "topic": topic,
                    "mode": mode
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(
                        "p2p_session_created",
                        session_id=data.get("session_id", "")[:16]
                    )
                    return data
                else:
                    error = await resp.text()
                    logger.error("p2p_session_creation_failed", error=error)
                    return None

    async def connect_conversation(self, session_id: str) -> bool:
        """
        Connect to a P2P conversation session via WebSocket.

        Args:
            session_id: The session to connect to

        Returns:
            True if connected successfully
        """
        if session_id in self.conv_connections:
            return True

        self.conv_states[session_id] = ConnectionState.CONNECTING

        try:
            import websockets

            ws_url = f"{self.ws_base}/conversation/ws/{session_id}"
            ws = await websockets.connect(ws_url)

            # Send join message
            await ws.send(json.dumps({
                "type": "join",
                "commitment": self.commitment,
                "name": self.qube_name
            }))

            self.conv_connections[session_id] = ws
            self.conv_states[session_id] = ConnectionState.CONNECTED

            # Start listening task
            asyncio.create_task(self._conv_listen_loop(session_id, ws))

            logger.info("p2p_conversation_connected", session_id=session_id[:16])
            return True

        except Exception as e:
            logger.error("p2p_conversation_connection_failed", error=str(e))
            self.conv_states[session_id] = ConnectionState.DISCONNECTED
            return False

    async def _conv_listen_loop(self, session_id: str, ws):
        """Listen for conversation messages"""
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    await self._handle_conv_message(session_id, data)
                except json.JSONDecodeError:
                    logger.warning("invalid_conv_message")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("conv_listen_error", error=str(e))
            self.conv_states[session_id] = ConnectionState.DISCONNECTED

    async def _handle_conv_message(self, session_id: str, data: Dict[str, Any]):
        """Handle a conversation message"""
        msg_type = data.get("type")

        if msg_type == "new_block":
            # New message block from another participant
            if self._on_block:
                self._on_block(session_id, data.get("block", {}))

        elif msg_type == "block_finalized":
            # Block has been finalized with all signatures
            if self._on_block:
                self._on_block(session_id, data.get("block", {}))

        elif msg_type == "sync_state":
            # Full state sync (after joining or reconnecting)
            if self._on_session_update:
                self._on_session_update(session_id, data.get("session", {}))

        elif msg_type in ("participant_joined", "participant_left", "session_update"):
            if self._on_session_update:
                self._on_session_update(session_id, data)

    async def submit_block(
        self,
        session_id: str,
        content: Dict[str, Any],
        block_type: str = "MESSAGE"
    ) -> bool:
        """
        Submit a message block to a P2P conversation.

        Args:
            session_id: The session to submit to
            content: Block content (role, content, etc.)
            block_type: Type of block (MESSAGE, ACTION, etc.)

        Returns:
            True if submitted successfully
        """
        import aiohttp

        # Hash and sign the content
        content_json = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        signature = sign_message(self.private_key, content_hash)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/conversation/sessions/{session_id}/blocks",
                json={
                    "creator_commitment": self.commitment,
                    "block_type": block_type,
                    "content": content,
                    "content_hash": content_hash,
                    "creator_signature": signature
                }
            ) as resp:
                if resp.status == 200:
                    logger.info("p2p_block_submitted", session_id=session_id[:16])
                    return True
                else:
                    error = await resp.text()
                    logger.error("p2p_block_submission_failed", error=error)
                    return False

    async def sign_block(self, session_id: str, block_id: str, content_hash: str) -> bool:
        """Sign a block from another participant"""
        import aiohttp

        signature = sign_message(self.private_key, content_hash)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/conversation/sessions/{session_id}/blocks/{block_id}/sign",
                json={
                    "signer_commitment": self.commitment,
                    "signature": signature
                }
            ) as resp:
                return resp.status == 200

    async def leave_session(self, session_id: str):
        """Leave a P2P conversation session"""
        import aiohttp

        # Notify server
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.api_base}/conversation/sessions/{session_id}/leave",
                json={"commitment": self.commitment}
            )

        # Close WebSocket
        if session_id in self.conv_connections:
            ws = self.conv_connections.pop(session_id)
            await ws.close()

        self.conv_states.pop(session_id, None)
        logger.info("p2p_session_left", session_id=session_id[:16])

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_introduction(self, callback: Callable[[PendingIntroduction], None]):
        """Set callback for incoming introduction requests"""
        self._on_introduction = callback

    def on_signature(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for signature responses"""
        self._on_signature = callback

    def on_block(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback for new/finalized blocks"""
        self._on_block = callback

    def on_session_update(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback for session updates"""
        self._on_session_update = callback

    # =========================================================================
    # Persistence
    # =========================================================================

    def save_connections(self, filepath: str):
        """Save connections to a JSON file"""
        data = {
            commitment: {
                "commitment": conn.commitment,
                "name": conn.name,
                "qube_id": conn.qube_id,
                "accepted_at": conn.accepted_at.isoformat()
            }
            for commitment, conn in self.connections.items()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_connections(self, filepath: str):
        """Load connections from a JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            for commitment, info in data.items():
                self.connections[commitment] = Connection(
                    commitment=info["commitment"],
                    name=info["name"],
                    qube_id=info["qube_id"],
                    accepted_at=datetime.fromisoformat(info["accepted_at"])
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("load_connections_failed", error=str(e))


async def create_node_client(
    qube,
    api_base: str = QUBE_CASH_API,
    ws_base: str = QUBE_CASH_WS
) -> Optional[NodeClient]:
    """
    Create a NodeClient for a Qube.

    Args:
        qube: The Qube instance (must have NFT commitment)
        api_base: Base URL for REST API
        ws_base: Base URL for WebSocket

    Returns:
        Configured NodeClient or None if Qube isn't minted
    """
    # Get NFT commitment from genesis block
    commitment = getattr(qube.genesis_block, 'commitment', None)
    if not commitment or commitment == "pending_minting":
        logger.error("qube_not_minted", qube_id=qube.qube_id)
        return None

    return NodeClient(
        commitment=commitment,
        private_key=qube.private_key,
        public_key=qube.public_key,
        qube_name=qube.name,
        qube_id=qube.qube_id,
        api_base=api_base,
        ws_base=ws_base
    )
