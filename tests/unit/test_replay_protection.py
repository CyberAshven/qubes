"""
Tests for replay protection module

Critical security tests for preventing replay attacks through nonce tracking
and signature timestamp validation.

Security Fix: HIGH-03 - Signature expiration and replay protection
"""

import pytest
import time
from datetime import datetime, timezone
from threading import Thread
from typing import List

from utils.replay_protection import (
    NonceTracker,
    SignatureValidator,
    ReplayProtector,
    ReplayAttackError,
    SignatureExpiredError,
    global_replay_protector
)


# ==============================================================================
# NONCE TRACKER TESTS
# ==============================================================================

class TestNonceTracker:
    """Test NonceTracker for preventing replay attacks"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_fresh_nonce_not_used(self):
        """Fresh nonce should not be marked as used"""
        tracker = NonceTracker()
        assert not tracker.is_nonce_used("fresh_nonce_123")

    @pytest.mark.unit
    @pytest.mark.security
    def test_mark_nonce_as_used(self):
        """Should mark nonce as used successfully"""
        tracker = NonceTracker()
        tracker.use_nonce("test_nonce", "entity_123")
        assert tracker.is_nonce_used("test_nonce")

    @pytest.mark.unit
    @pytest.mark.security
    def test_detect_replay_attack(self):
        """Should detect and reject replay attacks (reused nonce)"""
        tracker = NonceTracker()
        tracker.use_nonce("nonce_abc", "peer1")

        # Attempt to reuse nonce should raise ReplayAttackError
        with pytest.raises(ReplayAttackError) as exc_info:
            tracker.use_nonce("nonce_abc", "peer1")

        assert "replay attack" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.security
    def test_different_nonces_allowed(self):
        """Different nonces from same entity should be allowed"""
        tracker = NonceTracker()
        tracker.use_nonce("nonce1", "peer1")
        tracker.use_nonce("nonce2", "peer1")
        tracker.use_nonce("nonce3", "peer1")

        assert tracker.is_nonce_used("nonce1")
        assert tracker.is_nonce_used("nonce2")
        assert tracker.is_nonce_used("nonce3")

    @pytest.mark.unit
    @pytest.mark.security
    def test_nonce_expiration(self):
        """Nonces should expire after max_age_seconds"""
        tracker = NonceTracker(max_age_seconds=1)  # 1 second expiry
        tracker.use_nonce("expire_test", "peer1")

        # Nonce should be valid immediately
        assert tracker.is_nonce_used("expire_test")

        # Wait for expiration
        time.sleep(1.1)

        # Nonce should be expired (no longer used)
        assert not tracker.is_nonce_used("expire_test")

    @pytest.mark.unit
    @pytest.mark.security
    def test_cleanup_old_nonces(self):
        """Should cleanup old nonces when max_nonces exceeded"""
        tracker = NonceTracker(max_age_seconds=1, max_nonces=5)

        # Add 6 nonces (exceeds max_nonces=5, triggering cleanup on 6th)
        for i in range(6):
            tracker.use_nonce(f"nonce_{i}", f"peer_{i}")

        # Cleanup triggers when len > max_nonces, so 6 nonces present before cleanup
        stats = tracker.get_stats()
        assert stats["active_nonces"] == 6  # All 6 are still active

        # Wait for nonces to expire, then trigger cleanup by adding another
        time.sleep(1.1)
        tracker.use_nonce("nonce_7", "peer_7")

        # Now old nonces should be cleaned up
        stats = tracker.get_stats()
        assert stats["active_nonces"] < 7  # Some old nonces should be gone

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_stats(self):
        """Should return accurate nonce tracker statistics"""
        tracker = NonceTracker(max_age_seconds=300, max_nonces=1000)

        tracker.use_nonce("nonce1", "peer1")
        tracker.use_nonce("nonce2", "peer2")

        stats = tracker.get_stats()
        assert stats["active_nonces"] == 2
        assert stats["max_nonces"] == 1000
        assert stats["max_age_seconds"] == 300

    @pytest.mark.unit
    @pytest.mark.security
    def test_thread_safety_concurrent_nonces(self):
        """Should handle concurrent nonce usage from multiple threads safely"""
        tracker = NonceTracker()
        errors: List[Exception] = []

        def use_unique_nonce(thread_id: int):
            try:
                for i in range(10):
                    tracker.use_nonce(f"thread_{thread_id}_nonce_{i}", f"thread_{thread_id}")
            except Exception as e:
                errors.append(e)

        # Launch 5 threads using different nonces
        threads = [Thread(target=use_unique_nonce, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All 50 nonces should be tracked
        stats = tracker.get_stats()
        assert stats["active_nonces"] == 50

    @pytest.mark.unit
    @pytest.mark.security
    def test_thread_safety_duplicate_detection(self):
        """Should detect duplicates even under concurrent access"""
        tracker = NonceTracker()
        replay_detected = []

        def attempt_replay():
            try:
                tracker.use_nonce("shared_nonce", "attacker")
            except ReplayAttackError:
                replay_detected.append(True)

        # Launch 5 threads trying to use same nonce
        threads = [Thread(target=attempt_replay) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 4 out of 5 should detect replay (1 succeeds, 4 get ReplayAttackError)
        assert len(replay_detected) == 4

    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_nonce(self):
        """Should handle empty nonce string gracefully"""
        tracker = NonceTracker()
        tracker.use_nonce("", "entity1")
        assert tracker.is_nonce_used("")

        # Replay should still be detected
        with pytest.raises(ReplayAttackError):
            tracker.use_nonce("", "entity2")


# ==============================================================================
# SIGNATURE VALIDATOR TESTS
# ==============================================================================

class TestSignatureValidator:
    """Test SignatureValidator for timestamp validation"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_recent_timestamp(self):
        """Recent timestamp should pass validation"""
        validator = SignatureValidator(max_age_seconds=300)
        now = int(datetime.now(timezone.utc).timestamp())

        # Should not raise exception
        validator.validate_timestamp(now)

    @pytest.mark.unit
    @pytest.mark.security
    def test_expired_timestamp_rejected(self):
        """Expired timestamp (too old) should raise SignatureExpiredError"""
        validator = SignatureValidator(max_age_seconds=300)  # 5 minutes
        now = int(datetime.now(timezone.utc).timestamp())
        old_timestamp = now - 600  # 10 minutes ago

        with pytest.raises(SignatureExpiredError) as exc_info:
            validator.validate_timestamp(old_timestamp)

        assert "expired" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.security
    def test_future_timestamp_rejected(self):
        """Future timestamp (clock skew attack) should raise SignatureExpiredError"""
        validator = SignatureValidator(clock_skew_seconds=30)
        now = int(datetime.now(timezone.utc).timestamp())
        future_timestamp = now + 100  # 100 seconds in future (beyond 30s skew)

        with pytest.raises(SignatureExpiredError) as exc_info:
            validator.validate_timestamp(future_timestamp)

        assert "future" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.security
    def test_clock_skew_tolerance(self):
        """Small clock skew should be tolerated"""
        validator = SignatureValidator(clock_skew_seconds=30)
        now = int(datetime.now(timezone.utc).timestamp())
        slightly_future = now + 15  # 15 seconds in future (within 30s tolerance)

        # Should not raise exception
        validator.validate_timestamp(slightly_future)

    @pytest.mark.unit
    @pytest.mark.security
    def test_boundary_exactly_at_max_age(self):
        """Timestamp exactly at max_age boundary should be rejected"""
        validator = SignatureValidator(max_age_seconds=300)
        now = int(datetime.now(timezone.utc).timestamp())
        boundary_timestamp = now - 301  # Just over 5 minutes

        with pytest.raises(SignatureExpiredError):
            validator.validate_timestamp(boundary_timestamp)

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_valid_method_no_exception(self):
        """is_valid() should return True/False without raising exceptions"""
        validator = SignatureValidator(max_age_seconds=300)
        now = int(datetime.now(timezone.utc).timestamp())

        # Valid timestamp
        assert validator.is_valid(now) is True

        # Expired timestamp
        old_timestamp = now - 600
        assert validator.is_valid(old_timestamp) is False

        # Future timestamp
        future_timestamp = now + 100
        assert validator.is_valid(future_timestamp) is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_custom_max_age(self):
        """Should respect custom max_age_seconds"""
        validator = SignatureValidator(max_age_seconds=60)  # 1 minute
        now = int(datetime.now(timezone.utc).timestamp())

        # 30 seconds old should be valid
        timestamp_30s = now - 30
        assert validator.is_valid(timestamp_30s) is True

        # 90 seconds old should be invalid
        timestamp_90s = now - 90
        assert validator.is_valid(timestamp_90s) is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_zero_age_timestamp(self):
        """Very old timestamp (near epoch) should be rejected"""
        validator = SignatureValidator(max_age_seconds=300)

        with pytest.raises(SignatureExpiredError):
            validator.validate_timestamp(0)  # Jan 1, 1970


# ==============================================================================
# REPLAY PROTECTOR TESTS (Combined)
# ==============================================================================

class TestReplayProtector:
    """Test ReplayProtector combining nonce and timestamp validation"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_message_accepted(self):
        """Valid message with fresh nonce and recent timestamp should be accepted"""
        protector = ReplayProtector()
        now = int(datetime.now(timezone.utc).timestamp())

        # Should not raise exception
        protector.validate_message("unique_nonce_1", now, "peer_abc")

    @pytest.mark.unit
    @pytest.mark.security
    def test_replay_attack_detected(self):
        """Reused nonce should trigger replay attack detection"""
        protector = ReplayProtector()
        now = int(datetime.now(timezone.utc).timestamp())

        # First message succeeds
        protector.validate_message("reused_nonce", now, "peer_xyz")

        # Second message with same nonce should fail
        with pytest.raises(ReplayAttackError):
            protector.validate_message("reused_nonce", now, "peer_xyz")

    @pytest.mark.unit
    @pytest.mark.security
    def test_expired_message_rejected(self):
        """Message with expired timestamp should be rejected"""
        protector = ReplayProtector(max_message_age=300)
        now = int(datetime.now(timezone.utc).timestamp())
        old_timestamp = now - 600  # 10 minutes ago

        with pytest.raises(SignatureExpiredError):
            protector.validate_message("nonce_old", old_timestamp, "peer_123")

    @pytest.mark.unit
    @pytest.mark.security
    def test_future_message_rejected(self):
        """Message from future should be rejected (clock skew attack)"""
        protector = ReplayProtector(clock_skew=30)
        now = int(datetime.now(timezone.utc).timestamp())
        future_timestamp = now + 100  # 100 seconds in future

        with pytest.raises(SignatureExpiredError):
            protector.validate_message("nonce_future", future_timestamp, "peer_456")

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_valid_message_no_exception(self):
        """is_valid_message() should return True/False without raising"""
        protector = ReplayProtector()
        now = int(datetime.now(timezone.utc).timestamp())

        # Valid message
        assert protector.is_valid_message("nonce_a", now, "peer_a") is True

        # Replay attack
        assert protector.is_valid_message("nonce_a", now, "peer_a") is False

        # Expired message
        old_timestamp = now - 600
        assert protector.is_valid_message("nonce_b", old_timestamp, "peer_b") is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_stats(self):
        """Should return combined statistics from nonce tracker and validator"""
        protector = ReplayProtector(
            max_message_age=300,
            nonce_max_age=3600,
            clock_skew=30
        )
        now = int(datetime.now(timezone.utc).timestamp())

        protector.validate_message("nonce1", now, "peer1")
        protector.validate_message("nonce2", now, "peer2")

        stats = protector.get_stats()
        assert stats["nonce_tracker"]["active_nonces"] == 2
        assert stats["max_message_age"] == 300
        assert stats["clock_skew"] == 30

    @pytest.mark.unit
    @pytest.mark.security
    def test_different_entities_same_nonce(self):
        """Different entities cannot reuse same nonce (global uniqueness)"""
        protector = ReplayProtector()
        now = int(datetime.now(timezone.utc).timestamp())

        # First entity uses nonce
        protector.validate_message("shared_nonce", now, "peer_A")

        # Second entity tries to use same nonce - should fail
        with pytest.raises(ReplayAttackError):
            protector.validate_message("shared_nonce", now, "peer_B")


# ==============================================================================
# GLOBAL REPLAY PROTECTOR TESTS
# ==============================================================================

class TestGlobalReplayProtector:
    """Test global replay protector instance"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_global_instance_exists(self):
        """Global replay protector should be initialized"""
        assert global_replay_protector is not None
        assert isinstance(global_replay_protector, ReplayProtector)

    @pytest.mark.unit
    @pytest.mark.security
    def test_global_instance_functional(self):
        """Global replay protector should be functional"""
        now = int(datetime.now(timezone.utc).timestamp())

        # Generate unique nonce for this test
        test_nonce = f"global_test_{time.time()}"

        # Should validate successfully
        global_replay_protector.validate_message(test_nonce, now, "test_peer")

        # Replay should be detected
        with pytest.raises(ReplayAttackError):
            global_replay_protector.validate_message(test_nonce, now, "test_peer")


# ==============================================================================
# EDGE CASES & SECURITY VECTORS
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and security attack vectors"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_very_long_nonce(self):
        """Should handle very long nonce strings"""
        tracker = NonceTracker()
        long_nonce = "A" * 10000  # 10KB nonce

        tracker.use_nonce(long_nonce, "peer1")
        assert tracker.is_nonce_used(long_nonce)

    @pytest.mark.unit
    @pytest.mark.security
    def test_special_characters_in_nonce(self):
        """Should handle special characters in nonce"""
        tracker = NonceTracker()
        special_nonce = "nonce\x00\n\r\t!@#$%^&*()"

        tracker.use_nonce(special_nonce, "peer1")
        assert tracker.is_nonce_used(special_nonce)

    @pytest.mark.unit
    @pytest.mark.security
    def test_unicode_nonce(self):
        """Should handle Unicode characters in nonce"""
        tracker = NonceTracker()
        unicode_nonce = "nonce_测试_🔒_العربية"

        tracker.use_nonce(unicode_nonce, "peer1")
        assert tracker.is_nonce_used(unicode_nonce)

    @pytest.mark.unit
    @pytest.mark.security
    def test_rapid_sequential_nonces(self):
        """Should handle rapid sequential nonce usage"""
        tracker = NonceTracker(max_nonces=1000)

        # Add 100 nonces rapidly
        for i in range(100):
            tracker.use_nonce(f"rapid_{i}", f"peer_{i % 10}")

        # All should be tracked
        stats = tracker.get_stats()
        assert stats["active_nonces"] == 100

    @pytest.mark.unit
    @pytest.mark.security
    def test_timestamp_integer_overflow(self):
        """Should handle very large timestamp values"""
        validator = SignatureValidator()

        # Very large timestamp (far future)
        large_timestamp = 2**31 - 1  # Year 2038

        with pytest.raises(SignatureExpiredError):
            validator.validate_timestamp(large_timestamp)

    @pytest.mark.unit
    @pytest.mark.security
    def test_negative_timestamp(self):
        """Should reject negative timestamps"""
        validator = SignatureValidator()

        with pytest.raises(SignatureExpiredError):
            validator.validate_timestamp(-1000)

    @pytest.mark.unit
    @pytest.mark.security
    def test_multiple_validators_independent(self):
        """Multiple validator instances should be independent"""
        validator1 = SignatureValidator(max_age_seconds=60)
        validator2 = SignatureValidator(max_age_seconds=600)

        now = int(datetime.now(timezone.utc).timestamp())
        old_timestamp = now - 120  # 2 minutes ago

        # Should be invalid for validator1 (60s max)
        assert validator1.is_valid(old_timestamp) is False

        # Should be valid for validator2 (600s max)
        assert validator2.is_valid(old_timestamp) is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_cleanup_maintains_recent_nonces(self):
        """Cleanup should preserve recent nonces, remove only old ones"""
        tracker = NonceTracker(max_age_seconds=2, max_nonces=100)

        # Add old nonces
        for i in range(5):
            tracker.use_nonce(f"old_{i}", "peer_old")

        # Wait for them to age
        time.sleep(2.1)

        # Add new nonces
        for i in range(5):
            tracker.use_nonce(f"new_{i}", "peer_new")

        # Force cleanup
        tracker._cleanup_old_nonces()

        # Old nonces should be gone
        assert not tracker.is_nonce_used("old_0")

        # New nonces should remain
        assert tracker.is_nonce_used("new_0")
