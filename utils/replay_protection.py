"""
Replay Protection & Signature Expiration

Prevents replay attacks by tracking used nonces and enforcing signature expiration.

Security Fix: HIGH-03 - Signature expiration and replay protection
"""

import time
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Set, Optional, Dict
from threading import Lock, RLock

from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class ReplayAttackError(QubesError):
    """Raised when replay attack is detected"""
    pass


class SignatureExpiredError(QubesError):
    """Raised when signature has expired"""
    pass


class NonceTracker:
    """
    Track used nonces to prevent replay attacks

    Thread-safe implementation with automatic cleanup of old nonces.

    Args:
        max_age_seconds: How long to remember nonces (default: 1 hour)
        max_nonces: Maximum nonces to track (default: 10,000)

    Example:
        >>> tracker = NonceTracker()
        >>> tracker.use_nonce("abc123", "peer_xyz")
        >>> tracker.is_nonce_used("abc123")
        True
    """

    def __init__(
        self,
        max_age_seconds: int = 3600,  # 1 hour
        max_nonces: int = 10000
    ):
        self.max_age_seconds = max_age_seconds
        self.max_nonces = max_nonces

        # Store nonces with timestamps: nonce -> (timestamp, entity_id)
        self.nonces: Dict[str, tuple[float, str]] = {}

        # Track nonces in order for cleanup
        self.nonce_queue: deque = deque()

        # Thread safety
        self.lock = RLock()  # Use RLock for reentrant locking (use_nonce calls is_nonce_used)

        logger.debug(
            "nonce_tracker_initialized",
            max_age_seconds=max_age_seconds,
            max_nonces=max_nonces
        )

    def is_nonce_used(self, nonce: str) -> bool:
        """
        Check if nonce has been used before

        Args:
            nonce: Nonce to check

        Returns:
            True if nonce has been used, False otherwise
        """
        with self.lock:
            # Check if nonce exists and is still valid
            if nonce in self.nonces:
                timestamp, _ = self.nonces[nonce]
                if time.time() - timestamp < self.max_age_seconds:
                    return True
                else:
                    # Nonce expired, remove it
                    del self.nonces[nonce]

            return False

    def use_nonce(self, nonce: str, entity_id: str) -> None:
        """
        Mark nonce as used

        Args:
            nonce: Nonce to mark as used
            entity_id: Entity that used this nonce

        Raises:
            ReplayAttackError: If nonce was already used
        """
        with self.lock:
            # Check for replay
            if self.is_nonce_used(nonce):
                logger.warning(
                    "replay_attack_detected",
                    nonce=nonce[:16] + "...",
                    entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id
                )
                raise ReplayAttackError(
                    f"Replay attack detected: nonce already used",
                    context={"nonce": nonce[:16] + "...", "entity_id": entity_id}
                )

            # Mark as used
            now = time.time()
            self.nonces[nonce] = (now, entity_id)
            self.nonce_queue.append((nonce, now))

            logger.debug(
                "nonce_marked_used",
                nonce=nonce[:16] + "...",
                entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id
            )

            # Cleanup if too many nonces
            if len(self.nonces) > self.max_nonces:
                self._cleanup_old_nonces()

    def _cleanup_old_nonces(self) -> int:
        """
        Remove old nonces to prevent memory bloat

        Returns:
            Number of nonces cleaned up
        """
        now = time.time()
        cutoff = now - self.max_age_seconds
        cleaned = 0

        # Remove from front of queue (oldest nonces)
        while self.nonce_queue and self.nonce_queue[0][1] < cutoff:
            nonce, _ = self.nonce_queue.popleft()
            if nonce in self.nonces:
                del self.nonces[nonce]
                cleaned += 1

        if cleaned > 0:
            logger.debug("nonces_cleaned_up", count=cleaned)

        return cleaned

    def get_stats(self) -> Dict[str, int]:
        """Get nonce tracker statistics"""
        with self.lock:
            return {
                "active_nonces": len(self.nonces),
                "max_nonces": self.max_nonces,
                "max_age_seconds": self.max_age_seconds
            }


class SignatureValidator:
    """
    Validate signature timestamps to prevent replay attacks

    Args:
        max_age_seconds: Maximum age of signature to accept (default: 5 minutes)
        clock_skew_seconds: Allow for clock differences (default: 30 seconds)

    Example:
        >>> validator = SignatureValidator(max_age_seconds=300)
        >>> timestamp = int(datetime.now(timezone.utc).timestamp())
        >>> validator.validate_timestamp(timestamp)  # OK
        >>> validator.validate_timestamp(timestamp - 600)  # Raises SignatureExpiredError
    """

    def __init__(
        self,
        max_age_seconds: int = 300,  # 5 minutes
        clock_skew_seconds: int = 30  # 30 seconds
    ):
        self.max_age_seconds = max_age_seconds
        self.clock_skew_seconds = clock_skew_seconds

        logger.debug(
            "signature_validator_initialized",
            max_age_seconds=max_age_seconds,
            clock_skew_seconds=clock_skew_seconds
        )

    def validate_timestamp(self, timestamp: int) -> None:
        """
        Validate signature timestamp

        Args:
            timestamp: Unix timestamp from signature

        Raises:
            SignatureExpiredError: If signature is expired or from future
        """
        now = int(datetime.now(timezone.utc).timestamp())

        # Check if signature is too old
        age = now - timestamp
        if age > self.max_age_seconds:
            logger.warning(
                "signature_expired",
                age_seconds=age,
                max_age=self.max_age_seconds
            )
            raise SignatureExpiredError(
                f"Signature expired. Age: {age}s, Max: {self.max_age_seconds}s",
                context={
                    "age_seconds": age,
                    "max_age_seconds": self.max_age_seconds,
                    "timestamp": timestamp
                }
            )

        # Check if signature is from future (possible clock skew or attack)
        if timestamp > now + self.clock_skew_seconds:
            logger.warning(
                "signature_from_future",
                future_seconds=timestamp - now
            )
            raise SignatureExpiredError(
                f"Signature from future detected. Possible clock skew or replay attack.",
                context={
                    "timestamp": timestamp,
                    "current_time": now,
                    "difference": timestamp - now
                }
            )

        logger.debug("signature_timestamp_valid", age_seconds=age)

    def is_valid(self, timestamp: int) -> bool:
        """
        Check if timestamp is valid without raising exception

        Args:
            timestamp: Unix timestamp to check

        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate_timestamp(timestamp)
            return True
        except SignatureExpiredError:
            return False


class ReplayProtector:
    """
    Combined replay protection using nonce tracking and timestamp validation

    Args:
        max_message_age: Maximum age of messages to accept (default: 5 minutes)
        nonce_max_age: How long to remember nonces (default: 1 hour)
        clock_skew: Allow for clock differences (default: 30 seconds)

    Example:
        >>> protector = ReplayProtector()
        >>> timestamp = int(datetime.now(timezone.utc).timestamp())
        >>> protector.validate_message("nonce123", timestamp, "peer_xyz")  # OK
        >>> protector.validate_message("nonce123", timestamp, "peer_xyz")  # Raises ReplayAttackError
    """

    def __init__(
        self,
        max_message_age: int = 300,  # 5 minutes
        nonce_max_age: int = 3600,  # 1 hour
        clock_skew: int = 30  # 30 seconds
    ):
        self.nonce_tracker = NonceTracker(max_age_seconds=nonce_max_age)
        self.signature_validator = SignatureValidator(
            max_age_seconds=max_message_age,
            clock_skew_seconds=clock_skew
        )

        logger.debug("replay_protector_initialized")

    def validate_message(
        self,
        nonce: str,
        timestamp: int,
        entity_id: str
    ) -> None:
        """
        Validate message against replay attacks

        Args:
            nonce: Message nonce
            timestamp: Message timestamp
            entity_id: Entity sending the message

        Raises:
            SignatureExpiredError: If message is too old or from future
            ReplayAttackError: If nonce was already used
        """
        # Validate timestamp first (fail fast if message is expired)
        self.signature_validator.validate_timestamp(timestamp)

        # Check and mark nonce as used
        self.nonce_tracker.use_nonce(nonce, entity_id)

        logger.debug(
            "message_validated",
            entity_id=entity_id[:16] + "..." if len(entity_id) > 16 else entity_id,
            nonce=nonce[:16] + "..."
        )

    def is_valid_message(
        self,
        nonce: str,
        timestamp: int,
        entity_id: str
    ) -> bool:
        """
        Check if message is valid without raising exception

        Args:
            nonce: Message nonce
            timestamp: Message timestamp
            entity_id: Entity sending the message

        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate_message(nonce, timestamp, entity_id)
            return True
        except (SignatureExpiredError, ReplayAttackError):
            return False

    def get_stats(self) -> Dict[str, any]:
        """Get replay protection statistics"""
        return {
            "nonce_tracker": self.nonce_tracker.get_stats(),
            "max_message_age": self.signature_validator.max_age_seconds,
            "clock_skew": self.signature_validator.clock_skew_seconds
        }


# ==============================================================================
# GLOBAL REPLAY PROTECTOR (for convenience)
# ==============================================================================

# Global replay protector for P2P messages
global_replay_protector = ReplayProtector(
    max_message_age=300,  # 5 minutes
    nonce_max_age=3600,   # 1 hour
    clock_skew=30          # 30 seconds
)


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    print("Testing replay protection...")

    # Test nonce tracker
    tracker = NonceTracker()

    nonce1 = "abc123"
    tracker.use_nonce(nonce1, "peer1")
    print(f"Nonce {nonce1} marked as used")

    assert tracker.is_nonce_used(nonce1)
    print(f"Nonce {nonce1} is correctly marked as used")

    # Test replay detection
    try:
        tracker.use_nonce(nonce1, "peer1")
        assert False, "Should have detected replay"
    except ReplayAttackError:
        print("Replay attack correctly detected!")

    # Test timestamp validation
    validator = SignatureValidator(max_age_seconds=300)

    now = int(datetime.now(timezone.utc).timestamp())
    validator.validate_timestamp(now)
    print(f"Current timestamp validated")

    # Test expired signature
    try:
        old_timestamp = now - 600  # 10 minutes ago
        validator.validate_timestamp(old_timestamp)
        assert False, "Should have detected expired signature"
    except SignatureExpiredError:
        print("Expired signature correctly detected!")

    # Test combined replay protector
    protector = ReplayProtector()

    nonce2 = "xyz789"
    timestamp = int(datetime.now(timezone.utc).timestamp())
    protector.validate_message(nonce2, timestamp, "peer2")
    print(f"Message with nonce {nonce2} validated")

    # Test replay with same nonce
    try:
        protector.validate_message(nonce2, timestamp, "peer2")
        assert False, "Should have detected replay"
    except ReplayAttackError:
        print("Replay correctly detected by combined protector!")

    print("\nAll replay protection tests passed!")
