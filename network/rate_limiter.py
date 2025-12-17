"""
Rate Limiting and DoS Prevention

Implements rate limiting and DoS protection for P2P network operations.
Protects against spam, flooding, and resource exhaustion attacks.
"""

import time
from typing import Dict, Optional, Tuple
from collections import deque
from datetime import datetime, timezone, timedelta

from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter

    Implements token bucket algorithm for smooth rate limiting.
    """

    def __init__(
        self,
        rate: float,
        capacity: int,
        name: str = "default"
    ):
        """
        Initialize rate limiter

        Args:
            rate: Tokens per second
            capacity: Maximum token bucket capacity
            name: Limiter name for logging
        """
        self.rate = rate
        self.capacity = capacity
        self.name = name

        self.tokens = float(capacity)
        self.last_update = time.time()

        logger.debug(
            "rate_limiter_initialized",
            name=name,
            rate=rate,
            capacity=capacity
        )

    def allow(self, tokens: int = 1) -> bool:
        """
        Check if action is allowed

        Args:
            tokens: Number of tokens required

        Returns:
            True if action is allowed
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        logger.debug(
            "rate_limit_exceeded",
            name=self.name,
            tokens_available=self.tokens,
            tokens_required=tokens
        )

        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)

        self.last_update = now

    def get_stats(self) -> Dict[str, float]:
        """Get rate limiter statistics"""
        self._refill()
        return {
            "name": self.name,
            "tokens_available": self.tokens,
            "capacity": self.capacity,
            "rate_per_second": self.rate
        }


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter

    Tracks requests in a sliding time window.
    More accurate than fixed windows but uses more memory.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        name: str = "sliding_window"
    ):
        """
        Initialize sliding window rate limiter

        Args:
            max_requests: Maximum requests in window
            window_seconds: Window size in seconds
            name: Limiter name for logging
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name

        # Store timestamps of recent requests
        self.requests: deque = deque()

        logger.debug(
            "sliding_window_limiter_initialized",
            name=name,
            max_requests=max_requests,
            window_seconds=window_seconds
        )

    def allow(self) -> bool:
        """
        Check if request is allowed

        Returns:
            True if request is allowed
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Remove old requests outside window
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True

        logger.debug(
            "sliding_window_limit_exceeded",
            name=self.name,
            requests_in_window=len(self.requests),
            max_requests=self.max_requests
        )

        return False

    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics"""
        # Clean old requests
        now = time.time()
        window_start = now - self.window_seconds

        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

        return {
            "name": self.name,
            "requests_in_window": len(self.requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds
        }


class NetworkRateLimiter:
    """
    Network-wide rate limiting and DoS prevention

    Implements multiple rate limiters for different operations:
    - Per-Qube message rate limiting
    - Per-Qube handshake rate limiting
    - Network-wide connection limiting
    - Bandwidth limiting
    """

    def __init__(
        self,
        messages_per_qube_per_minute: int = 60,
        handshakes_per_qube_per_hour: int = 20,
        max_concurrent_connections: int = 100,
        discovery_announcements_per_hour: int = 10
    ):
        """
        Initialize network rate limiter

        Args:
            messages_per_qube_per_minute: Max messages per Qube per minute
            handshakes_per_qube_per_hour: Max handshakes per Qube per hour
            max_concurrent_connections: Max concurrent connections
            discovery_announcements_per_hour: Max discovery announcements per hour
        """
        self.messages_per_qube_per_minute = messages_per_qube_per_minute
        self.handshakes_per_qube_per_hour = handshakes_per_qube_per_hour
        self.max_concurrent_connections = max_concurrent_connections

        # Per-Qube rate limiters
        self.qube_message_limiters: Dict[str, SlidingWindowRateLimiter] = {}
        self.qube_handshake_limiters: Dict[str, SlidingWindowRateLimiter] = {}

        # Global rate limiters
        self.discovery_limiter = SlidingWindowRateLimiter(
            max_requests=discovery_announcements_per_hour,
            window_seconds=3600,
            name="discovery"
        )

        # Connection tracking
        self.active_connections: Dict[str, int] = {}

        # Blocklist (temporary blocks for misbehaving Qubes)
        self.blocklist: Dict[str, datetime] = {}
        self.block_duration_seconds = 3600  # 1 hour

        logger.info(
            "network_rate_limiter_initialized",
            messages_per_qube_per_minute=messages_per_qube_per_minute,
            handshakes_per_qube_per_hour=handshakes_per_qube_per_hour
        )

    def allow_message(self, qube_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if message from Qube is allowed

        Args:
            qube_id: Source Qube ID

        Returns:
            Tuple of (allowed, reason)
        """
        # Check blocklist
        if self._is_blocked(qube_id):
            return False, "qube_blocked"

        # Get or create limiter for this Qube
        if qube_id not in self.qube_message_limiters:
            self.qube_message_limiters[qube_id] = SlidingWindowRateLimiter(
                max_requests=self.messages_per_qube_per_minute,
                window_seconds=60,
                name=f"messages_{qube_id[:8]}"
            )

        limiter = self.qube_message_limiters[qube_id]

        if limiter.allow():
            MetricsRecorder.record_p2p_event("message_allowed", qube_id)
            return True, None
        else:
            logger.warning(
                "message_rate_limit_exceeded",
                qube_id=qube_id,
                limit=self.messages_per_qube_per_minute
            )
            MetricsRecorder.record_p2p_event("message_rate_limited", qube_id)
            return False, "rate_limit_exceeded"

    def allow_handshake(self, qube_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if handshake from Qube is allowed

        Args:
            qube_id: Source Qube ID

        Returns:
            Tuple of (allowed, reason)
        """
        # Check blocklist
        if self._is_blocked(qube_id):
            return False, "qube_blocked"

        # Get or create limiter for this Qube
        if qube_id not in self.qube_handshake_limiters:
            self.qube_handshake_limiters[qube_id] = SlidingWindowRateLimiter(
                max_requests=self.handshakes_per_qube_per_hour,
                window_seconds=3600,
                name=f"handshakes_{qube_id[:8]}"
            )

        limiter = self.qube_handshake_limiters[qube_id]

        if limiter.allow():
            MetricsRecorder.record_p2p_event("handshake_allowed", qube_id)
            return True, None
        else:
            logger.warning(
                "handshake_rate_limit_exceeded",
                qube_id=qube_id,
                limit=self.handshakes_per_qube_per_hour
            )
            MetricsRecorder.record_p2p_event("handshake_rate_limited", qube_id)
            return False, "rate_limit_exceeded"

    def allow_discovery_announcement(self) -> Tuple[bool, Optional[str]]:
        """
        Check if discovery announcement is allowed

        Returns:
            Tuple of (allowed, reason)
        """
        if self.discovery_limiter.allow():
            return True, None
        else:
            logger.warning("discovery_announcement_rate_limited")
            return False, "rate_limit_exceeded"

    def allow_connection(self, qube_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if new connection is allowed

        Args:
            qube_id: Source Qube ID

        Returns:
            Tuple of (allowed, reason)
        """
        # Check blocklist
        if self._is_blocked(qube_id):
            return False, "qube_blocked"

        # Check total connections
        total_connections = sum(self.active_connections.values())

        if total_connections >= self.max_concurrent_connections:
            logger.warning(
                "max_connections_reached",
                total=total_connections,
                max=self.max_concurrent_connections
            )
            return False, "max_connections_reached"

        return True, None

    def register_connection(self, qube_id: str) -> None:
        """
        Register new active connection

        Args:
            qube_id: Connected Qube ID
        """
        self.active_connections[qube_id] = self.active_connections.get(qube_id, 0) + 1
        logger.debug(
            "connection_registered",
            qube_id=qube_id,
            connections=self.active_connections[qube_id]
        )

    def unregister_connection(self, qube_id: str) -> None:
        """
        Unregister active connection

        Args:
            qube_id: Disconnected Qube ID
        """
        if qube_id in self.active_connections:
            self.active_connections[qube_id] -= 1
            if self.active_connections[qube_id] <= 0:
                del self.active_connections[qube_id]

            logger.debug(
                "connection_unregistered",
                qube_id=qube_id,
                remaining_connections=self.active_connections.get(qube_id, 0)
            )

    def block_qube(self, qube_id: str, duration_seconds: Optional[int] = None) -> None:
        """
        Temporarily block Qube

        Args:
            qube_id: Qube ID to block
            duration_seconds: Block duration (defaults to 1 hour)
        """
        duration = duration_seconds or self.block_duration_seconds
        unblock_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

        self.blocklist[qube_id] = unblock_time

        logger.warning(
            "qube_blocked",
            qube_id=qube_id,
            duration_seconds=duration,
            unblock_time=unblock_time.isoformat()
        )

        MetricsRecorder.record_p2p_event("qube_blocked", qube_id)

    def unblock_qube(self, qube_id: str) -> None:
        """
        Manually unblock Qube

        Args:
            qube_id: Qube ID to unblock
        """
        if qube_id in self.blocklist:
            del self.blocklist[qube_id]
            logger.info("qube_unblocked", qube_id=qube_id)

    def _is_blocked(self, qube_id: str) -> bool:
        """
        Check if Qube is blocked

        Args:
            qube_id: Qube ID to check

        Returns:
            True if blocked
        """
        if qube_id not in self.blocklist:
            return False

        unblock_time = self.blocklist[qube_id]

        # Check if block expired
        if datetime.now(timezone.utc) >= unblock_time:
            del self.blocklist[qube_id]
            logger.info("qube_auto_unblocked", qube_id=qube_id)
            return False

        return True

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            "total_active_connections": sum(self.active_connections.values()),
            "max_concurrent_connections": self.max_concurrent_connections,
            "blocked_qubes": len(self.blocklist),
            "message_limiters": len(self.qube_message_limiters),
            "handshake_limiters": len(self.qube_handshake_limiters),
            "discovery_stats": self.discovery_limiter.get_stats()
        }

    def cleanup_expired_limiters(self) -> None:
        """Remove expired rate limiters to save memory"""
        # Clean message limiters
        expired_message = []
        for qube_id, limiter in self.qube_message_limiters.items():
            stats = limiter.get_stats()
            if stats["requests_in_window"] == 0:
                expired_message.append(qube_id)

        for qube_id in expired_message:
            del self.qube_message_limiters[qube_id]

        # Clean handshake limiters
        expired_handshake = []
        for qube_id, limiter in self.qube_handshake_limiters.items():
            stats = limiter.get_stats()
            if stats["requests_in_window"] == 0:
                expired_handshake.append(qube_id)

        for qube_id in expired_handshake:
            del self.qube_handshake_limiters[qube_id]

        if expired_message or expired_handshake:
            logger.debug(
                "expired_limiters_cleaned",
                message_limiters_removed=len(expired_message),
                handshake_limiters_removed=len(expired_handshake)
            )
