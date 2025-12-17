"""
Rate Limiter for DoS Protection

Provides rate limiting for P2P messages, API calls, and other operations
to prevent denial-of-service attacks.

Security Fix: HIGH-01 - P2P rate limiting
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from threading import Lock

from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class RateLimitExceededError(QubesError):
    """Raised when rate limit is exceeded"""
    pass


class RateLimiter:
    """
    Token bucket rate limiter with sliding window

    Thread-safe implementation for concurrent access.

    Args:
        max_requests: Maximum requests allowed in time window
        window_seconds: Time window in seconds
        burst_size: Optional burst allowance (defaults to max_requests)

    Example:
        >>> limiter = RateLimiter(max_requests=10, window_seconds=60)
        >>> if limiter.check("peer_id_123"):
        ...     # Process request
        ...     pass
        ... else:
        ...     # Rate limit exceeded
        ...     raise RateLimitExceededError("Too many requests")
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        burst_size: Optional[int] = None
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_requests

        # Track request timestamps per entity
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())

        # Thread safety
        self.lock = Lock()

        logger.debug(
            "rate_limiter_initialized",
            max_requests=max_requests,
            window_seconds=window_seconds,
            burst_size=self.burst_size
        )

    def check(self, entity_id: str) -> bool:
        """
        Check if request is allowed for entity

        Args:
            entity_id: Identifier for the entity (peer ID, user ID, etc.)

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Get request history for this entity
            request_history = self.requests[entity_id]

            # Remove old requests outside time window
            while request_history and request_history[0] < cutoff:
                request_history.popleft()

            # Check if limit exceeded
            if len(request_history) >= self.max_requests:
                logger.warning(
                    "rate_limit_exceeded",
                    entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id,
                    requests=len(request_history),
                    limit=self.max_requests,
                    window=self.window_seconds
                )
                return False

            # Allow request and record timestamp
            request_history.append(now)

            logger.debug(
                "rate_limit_check_passed",
                entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id,
                requests=len(request_history),
                limit=self.max_requests
            )

            return True

    def check_or_raise(self, entity_id: str) -> None:
        """
        Check rate limit and raise exception if exceeded

        Args:
            entity_id: Identifier for the entity

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if not self.check(entity_id):
            raise RateLimitExceededError(
                f"Rate limit exceeded for {entity_id}. "
                f"Max {self.max_requests} requests per {self.window_seconds} seconds.",
                context={
                    "entity_id": entity_id,
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds
                }
            )

    def get_stats(self, entity_id: str) -> Dict[str, int]:
        """
        Get rate limit statistics for entity

        Args:
            entity_id: Identifier for the entity

        Returns:
            Dict with request count and remaining quota
        """
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds

            request_history = self.requests[entity_id]

            # Clean old requests
            while request_history and request_history[0] < cutoff:
                request_history.popleft()

            return {
                "requests_made": len(request_history),
                "requests_remaining": max(0, self.max_requests - len(request_history)),
                "limit": self.max_requests,
                "window_seconds": self.window_seconds,
                "reset_in_seconds": int(self.window_seconds - (now - request_history[0])) if request_history else self.window_seconds
            }

    def reset(self, entity_id: Optional[str] = None) -> None:
        """
        Reset rate limit counter

        Args:
            entity_id: Optional entity ID to reset. If None, reset all.
        """
        with self.lock:
            if entity_id:
                if entity_id in self.requests:
                    del self.requests[entity_id]
                    logger.info("rate_limit_reset", entity_id=entity_id)
            else:
                self.requests.clear()
                logger.info("rate_limits_reset_all")

    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up entries that haven't been accessed recently

        Args:
            max_age_seconds: Remove entries older than this (default: 1 hour)

        Returns:
            Number of entries cleaned up
        """
        with self.lock:
            now = time.time()
            cutoff = now - max_age_seconds

            to_remove = []
            for entity_id, request_history in self.requests.items():
                # If last request is older than max_age, remove entire entry
                if request_history and request_history[-1] < cutoff:
                    to_remove.append(entity_id)

            for entity_id in to_remove:
                del self.requests[entity_id]

            if to_remove:
                logger.debug("rate_limiter_cleanup", removed=len(to_remove))

            return len(to_remove)


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on entity behavior

    Trusted entities get higher limits, suspicious entities get lower limits.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        trust_multiplier: float = 2.0,
        penalty_multiplier: float = 0.5
    ):
        super().__init__(max_requests, window_seconds)

        self.base_max_requests = max_requests
        self.trust_multiplier = trust_multiplier
        self.penalty_multiplier = penalty_multiplier

        # Track trust scores (0.0 to 1.0)
        self.trust_scores: Dict[str, float] = defaultdict(lambda: 0.5)

        logger.debug("adaptive_rate_limiter_initialized")

    def set_trust_score(self, entity_id: str, trust_score: float) -> None:
        """
        Set trust score for entity (0.0 to 1.0)

        Args:
            entity_id: Identifier for the entity
            trust_score: Trust score between 0.0 (untrusted) and 1.0 (fully trusted)
        """
        trust_score = max(0.0, min(1.0, trust_score))  # Clamp to [0, 1]

        with self.lock:
            self.trust_scores[entity_id] = trust_score

            logger.debug(
                "trust_score_updated",
                entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id,
                trust_score=trust_score
            )

    def check(self, entity_id: str) -> bool:
        """
        Check if request is allowed, considering trust score

        Args:
            entity_id: Identifier for the entity

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        with self.lock:
            trust_score = self.trust_scores[entity_id]

            # Adjust limit based on trust
            if trust_score > 0.7:
                # Trusted entity - higher limit
                adjusted_limit = int(self.base_max_requests * self.trust_multiplier)
            elif trust_score < 0.3:
                # Suspicious entity - lower limit
                adjusted_limit = int(self.base_max_requests * self.penalty_multiplier)
            else:
                # Normal entity
                adjusted_limit = self.base_max_requests

            # Temporarily adjust limit for this check
            original_limit = self.max_requests
            self.max_requests = adjusted_limit

            # Perform check
            result = super().check(entity_id)

            # Restore original limit
            self.max_requests = original_limit

            return result


# ==============================================================================
# GLOBAL RATE LIMITERS (for convenience)
# ==============================================================================

# P2P message rate limiter (10 messages per minute per peer)
p2p_message_limiter = RateLimiter(max_requests=10, window_seconds=60)

# P2P handshake rate limiter (5 handshakes per hour per peer)
p2p_handshake_limiter = RateLimiter(max_requests=5, window_seconds=3600)

# API call rate limiter (100 calls per minute)
api_call_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Block creation rate limiter (50 blocks per minute)
block_creation_limiter = RateLimiter(max_requests=50, window_seconds=60)


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Test rate limiter
    limiter = RateLimiter(max_requests=3, window_seconds=1)

    print("Testing rate limiter...")

    # First 3 requests should pass
    for i in range(3):
        assert limiter.check("test_entity")
        print(f"Request {i+1}: Allowed")

    # 4th request should fail
    assert not limiter.check("test_entity")
    print("Request 4: Rate limited (as expected)")

    # Wait for window to reset
    time.sleep(1.1)

    # Should allow again
    assert limiter.check("test_entity")
    print("Request 5 (after reset): Allowed")

    # Test stats
    stats = limiter.get_stats("test_entity")
    print(f"\nRate limit stats: {stats}")

    print("\nAll rate limiter tests passed!")
