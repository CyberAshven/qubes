"""
Discovery Module

Implements multiple discovery mechanisms for finding Qubes on the network.
From docs/08_P2P_Network_Discovery.md Section 5.2
"""

from network.discovery.dht import DHTDiscovery
from network.discovery.resolver import discover_qube
from network.discovery.gossip import GossipProtocol, gossip_known_qubes
from network.discovery.manual import introduce_qubes, handle_introduction

__all__ = [
    "DHTDiscovery",
    "discover_qube",
    "GossipProtocol",
    "gossip_known_qubes",
    "introduce_qubes",
    "handle_introduction"
]
