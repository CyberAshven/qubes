"""
Tests for Audio Integration (Phase 7)

Tests TTS, STT, voice command parsing, and audio utilities.
From docs/27_Audio_TTS_STT_Integration.md Section 11
"""

import pytest
import os
from pathlib import Path

from audio import (
    VoiceConfig,
    AudioManager,
    VoiceCommandParser,
    HallucinationFilter,
    AudioCache,
    AudioRateLimiter,
)
from audio.command_security import requires_confirmation, is_command_allowed


class TestVoiceCommandParser:
    """Test voice command parsing"""

    def test_create_qube_command(self):
        """Test 'create qube' command parsing"""
        parser = VoiceCommandParser()

        command = parser.parse("create a new qube named assistant")

        assert command is not None
        assert command["action"] == "create_qube"
        assert command["args"]["name"] == "assistant"

    def test_list_qubes_command(self):
        """Test 'list qubes' command parsing"""
        parser = VoiceCommandParser()

        command = parser.parse("list all qubes")

        assert command["action"] == "list_qubes"
        assert command["args"] == {}

    def test_switch_qube_command(self):
        """Test 'switch to' command parsing"""
        parser = VoiceCommandParser()

        command = parser.parse("talk to test qube")
        assert command["action"] == "switch_qube"
        assert command["args"]["name"] == "test"

    def test_send_message_command(self):
        """Test message sending"""
        parser = VoiceCommandParser()

        command = parser.parse("send message hello world")
        assert command["action"] == "send_message"
        assert command["args"]["message"] == "hello world"

    def test_fallback_to_message(self):
        """Test unknown command falls back to message"""
        parser = VoiceCommandParser()

        command = parser.parse("this is just a random message")
        assert command["action"] == "send_message"
        assert command["args"]["message"] == "this is just a random message"

    def test_command_validation(self):
        """Test command validation"""
        parser = VoiceCommandParser()

        # Valid qube name
        valid_command = {"action": "create_qube", "args": {"name": "validname"}}
        assert parser.validate_command(valid_command) is True

        # Invalid qube name (too short)
        invalid_command = {"action": "create_qube", "args": {"name": "ab"}}
        assert parser.validate_command(invalid_command) is False

    def test_get_help_text(self):
        """Test help text generation"""
        parser = VoiceCommandParser()
        help_text = parser.get_help_text()

        assert "Create a new Qube" in help_text
        assert "List all Qubes" in help_text
        assert "Send message" in help_text


class TestHallucinationFilter:
    """Test STT hallucination detection"""

    def test_detects_low_confidence(self):
        """Test low confidence detection"""
        filter = HallucinationFilter()

        assert filter.is_likely_hallucination("Valid text", confidence=0.5) is True
        assert filter.is_likely_hallucination("Valid text", confidence=0.95) is False

    def test_detects_common_phrases(self):
        """Test known hallucination phrases"""
        filter = HallucinationFilter()

        assert filter.is_likely_hallucination("thank you for watching!", confidence=0.9) is True
        assert filter.is_likely_hallucination("please subscribe", confidence=0.9) is True
        assert filter.is_likely_hallucination("valid command", confidence=0.9) is False

    def test_detects_too_short(self):
        """Test minimum length filter"""
        filter = HallucinationFilter()

        assert filter.is_likely_hallucination("ab", confidence=0.9) is True
        assert filter.is_likely_hallucination("hello world", confidence=0.9) is False

    def test_filter_text(self):
        """Test text filtering"""
        filter = HallucinationFilter()

        assert filter.filter_text("hello world", confidence=0.95) == "hello world"
        assert filter.filter_text("ab", confidence=0.95) is None
        assert filter.filter_text("thank you for watching", confidence=0.95) is None


class TestAudioCache:
    """Test audio caching"""

    def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = AudioCache()
        voice_config = VoiceConfig(provider="openai", voice_id="alloy", speed=1.0)

        key1 = cache.get_cache_key("hello world", voice_config)
        key2 = cache.get_cache_key("hello world", voice_config)
        key3 = cache.get_cache_key("goodbye world", voice_config)

        # Same input = same key
        assert key1 == key2

        # Different input = different key
        assert key1 != key3

    def test_cache_miss(self):
        """Test cache miss"""
        cache = AudioCache()
        voice_config = VoiceConfig(provider="openai", voice_id="alloy", speed=1.0)

        # Should miss (not cached yet)
        result = cache.get("not cached text", voice_config)
        assert result is None

    def test_get_stats(self):
        """Test cache statistics"""
        cache = AudioCache()
        stats = cache.get_stats()

        assert "file_count" in stats
        assert "total_size_mb" in stats
        assert "max_size_mb" in stats
        assert "utilization_percent" in stats


class TestAudioRateLimiter:
    """Test rate limiting and quota tracking"""

    def test_tts_quota_check(self):
        """Test TTS quota checking"""
        limiter = AudioRateLimiter()

        # Small text - should pass
        assert limiter.check_tts_quota("user1", "hello" * 10, "elevenlabs") is True

        # Exceed quota
        large_text = "x" * 31000
        assert limiter.check_tts_quota("user2", large_text, "elevenlabs") is False

    def test_stt_quota_check(self):
        """Test STT quota checking"""
        limiter = AudioRateLimiter()

        # Short duration - should pass
        assert limiter.check_stt_quota("user1", 60) is True  # 60 seconds

        # Exceed quota
        assert limiter.check_stt_quota("user2", 7200) is False  # 2 hours > 60 min limit

    def test_premium_bypass(self):
        """Test premium users bypass quotas"""
        limiter = AudioRateLimiter()

        large_text = "x" * 100000
        assert limiter.check_tts_quota("premium_user", large_text, "elevenlabs", premium=True) is True

        long_duration = 10000
        assert limiter.check_stt_quota("premium_user", long_duration, premium=True) is True

    def test_usage_stats(self):
        """Test usage statistics"""
        limiter = AudioRateLimiter()

        limiter.check_tts_quota("user1", "hello" * 100, "elevenlabs")
        limiter.check_stt_quota("user1", 120)

        stats = limiter.get_usage_stats("user1")

        assert stats["user_id"] == "user1"
        assert stats["tts_chars_used"] > 0
        assert stats["stt_minutes_used"] > 0
        assert "tts_percent_used" in stats
        assert "stt_percent_used" in stats


class TestCommandSecurity:
    """Test command security functions"""

    def test_destructive_actions(self):
        """Test destructive action detection"""
        delete_command = {"action": "delete_qube", "args": {"name": "test"}}
        create_command = {"action": "create_qube", "args": {"name": "test"}}

        assert requires_confirmation(delete_command) is True
        assert requires_confirmation(create_command) is False

    def test_command_whitelist(self):
        """Test command whitelist"""
        valid_command = {"action": "create_qube", "args": {"name": "test"}}
        invalid_command = {"action": "hack_system", "args": {}}

        assert is_command_allowed(valid_command) is True
        assert is_command_allowed(invalid_command) is False


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
class TestAudioManagerIntegration:
    """Integration tests for AudioManager (requires API keys)"""

    @pytest.mark.asyncio
    async def test_audio_manager_initialization(self):
        """Test AudioManager initialization"""
        manager = AudioManager()

        assert "openai" in manager.tts_providers or "piper" in manager.tts_providers
        assert "openai" in manager.stt_providers or "whisper_cpp" in manager.stt_providers
        assert manager.cache is not None
        assert manager.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_get_usage_stats(self):
        """Test usage statistics retrieval"""
        manager = AudioManager()
        stats = manager.get_usage_stats("test_user")

        assert "user_id" in stats
        assert "tts_chars_used" in stats
        assert "stt_minutes_used" in stats

    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """Test cache statistics retrieval"""
        manager = AudioManager()
        stats = manager.get_cache_stats()

        assert "file_count" in stats
        assert "total_size_mb" in stats


# Fixtures for test audio files
@pytest.fixture
def test_audio_file():
    """Create a test audio file"""
    # This would need to create a valid WAV file for testing
    # For now, we'll skip actual audio file tests
    pytest.skip("Test audio files not implemented yet")


@pytest.fixture
def mock_voice_config():
    """Mock voice configuration"""
    return VoiceConfig(
        provider="openai",
        voice_id="alloy",
        speed=1.0
    )
