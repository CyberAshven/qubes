"""
WebSocket Server for Real-Time Relationship Updates

Broadcasts relationship changes to connected GUI clients in real-time.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets library not installed. Real-time updates disabled.")


class RelationshipWebSocketServer:
    """
    WebSocket server for broadcasting relationship updates

    Broadcasts events:
    - relationship_updated: When trust scores or stats change
    - relationship_progressed: When status changes (stranger → friend, etc.)
    - best_friend_changed: When best friend is designated/demoted
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize WebSocket server

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.server_task = None
        self.loop = None
        self.thread = None
        self.running = False

        logger.info(f"WebSocket server initialized on {host}:{port}")

    async def register(self, websocket: WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a client connection"""
        await self.register(websocket)
        try:
            # Send initial connection confirmation
            await websocket.send(json.dumps({
                "type": "connection_established",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to relationship updates"
            }))

            # Keep connection alive and handle incoming messages (if any)
            async for message in websocket:
                # Echo back for debugging (optional)
                logger.debug(f"Received message from client: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """
        Broadcast an event to all connected clients

        Args:
            event_type: Type of event (relationship_updated, relationship_progressed, etc.)
            data: Event data to broadcast
        """
        if not self.clients:
            return

        message = json.dumps({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

        # Send to all connected clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)

        # Clean up disconnected clients
        for client in disconnected_clients:
            await self.unregister(client)

        logger.debug(f"Broadcasted {event_type} to {len(self.clients)} clients")

    async def start_server(self):
        """Start the WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot start WebSocket server: websockets library not installed")
            return

        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port
            )
            self.running = True
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

            # Keep server running
            await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"WebSocket server error: {e}", exc_info=True)
            self.running = False

    def start(self):
        """Start the WebSocket server in a background thread"""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("WebSocket server disabled: websockets library not installed")
            return

        def run_server():
            """Run the server in a new event loop"""
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start_server())

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        logger.info("WebSocket server thread started")

    def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            logger.info("WebSocket server stopped")
        self.running = False

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]):
        """
        Synchronously broadcast an event (thread-safe)

        Args:
            event_type: Type of event
            data: Event data
        """
        if not self.running or not self.loop:
            return

        # Schedule the broadcast in the server's event loop
        asyncio.run_coroutine_threadsafe(
            self.broadcast(event_type, data),
            self.loop
        )


# Global server instance
_ws_server: Optional[RelationshipWebSocketServer] = None


def get_ws_server() -> Optional[RelationshipWebSocketServer]:
    """Get the global WebSocket server instance"""
    global _ws_server

    # Check if WebSocket is enabled in global settings
    try:
        from config.global_settings import get_global_settings
        settings = get_global_settings()
        if not settings.is_websocket_enabled():
            return None
    except Exception:
        pass

    if _ws_server is None and WEBSOCKETS_AVAILABLE:
        _ws_server = RelationshipWebSocketServer()
        _ws_server.start()

    return _ws_server


def broadcast_relationship_update(
    qube_id: str,
    entity_id: str,
    relationship_data: Dict[str, Any]
):
    """
    Broadcast a relationship update event

    Args:
        qube_id: ID of the qube whose relationship changed
        entity_id: ID of the entity in the relationship
        relationship_data: Updated relationship data
    """
    server = get_ws_server()
    if server:
        server.broadcast_sync("relationship_updated", {
            "qube_id": qube_id,
            "entity_id": entity_id,
            "relationship": relationship_data
        })


def broadcast_relationship_progression(
    qube_id: str,
    entity_id: str,
    old_status: str,
    new_status: str,
    trust_score: float
):
    """
    Broadcast a relationship status progression event

    Args:
        qube_id: ID of the qube whose relationship progressed
        entity_id: ID of the entity in the relationship
        old_status: Previous relationship status
        new_status: New relationship status
        trust_score: Current trust score
    """
    server = get_ws_server()
    if server:
        server.broadcast_sync("relationship_progressed", {
            "qube_id": qube_id,
            "entity_id": entity_id,
            "old_status": old_status,
            "new_status": new_status,
            "trust_score": trust_score
        })


def broadcast_best_friend_changed(
    qube_id: str,
    old_best_friend: Optional[str],
    new_best_friend: str
):
    """
    Broadcast a best friend change event

    Args:
        qube_id: ID of the qube
        old_best_friend: Previous best friend entity ID (if any)
        new_best_friend: New best friend entity ID
    """
    server = get_ws_server()
    if server:
        server.broadcast_sync("best_friend_changed", {
            "qube_id": qube_id,
            "old_best_friend": old_best_friend,
            "new_best_friend": new_best_friend
        })
