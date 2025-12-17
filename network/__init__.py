"""
P2P Network Module

Implements peer-to-peer networking for Qube-to-Qube communication.

Two approaches are supported:
1. Server-orchestrated (NodeClient) - via qube.cash WebSocket relay
2. Direct P2P (QubeP2PNode) - via libp2p for advanced users

From docs/08_P2P_Network_Discovery.md Section 5
"""

# Server-orchestrated P2P (recommended)
from network.node_client import NodeClient, create_node_client, PendingIntroduction, Connection

# Direct libp2p P2P (advanced)
from network.p2p_node import QubeP2PNode, start_qube_network
from network.messaging import QubeMessage, EncryptedSession
from network.handshake import QubeHandshake
from network.qube_messenger import QubeMessenger, create_qube_messenger
from network.discovery.dht import DHTDiscovery
from network.discovery.resolver import discover_qube

__all__ = [
    # Server-orchestrated
    "NodeClient",
    "create_node_client",
    "PendingIntroduction",
    "Connection",
    # Direct P2P
    "QubeP2PNode",
    "start_qube_network",
    "QubeMessage",
    "EncryptedSession",
    "QubeHandshake",
    "QubeMessenger",
    "create_qube_messenger",
    "DHTDiscovery",
    "discover_qube"
]
