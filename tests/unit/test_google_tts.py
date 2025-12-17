"""
Unit tests for Google Cloud Text-to-Speech integration

Tests the GoogleTTS provider with various voices and configurations.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from audio.tts_engine import GoogleTTS, VoiceConfig
from core.exceptions import AIError


class TestGoogleTTS:
    """Test Google Cloud TTS provider"""

    def test_google_tts_init_with_credentials(self):
        """Test initialization with credentials path"""
        with patch.dict('os.environ', {}, clear=True):
            tts = GoogleTTS(credentials_path="/path/to/credentials.json")
            assert tts.credentials_path == "/path/to/credentials.json"

    def test_google_tts_init_without_credentials(self):
        """Test initialization without credentials (uses env var)"""
        tts = GoogleTTS()
        assert tts.credentials_path is None

    def test_voice_type_detection_neural2(self):
        """Test voice type detection for Neural2 voices"""
        tts = GoogleTTS()
        assert tts._get_voice_type("en-US-Neural2-A") == "neural2"
        assert tts._get_voice_type("en-GB-Neural2-F") == "neural2"

    def test_voice_type_detection_wavenet(self):
        """Test voice type detection for WaveNet voices"""
        tts = GoogleTTS()
        assert tts._get_voice_type("en-US-Wavenet-D") == "wavenet"
        assert tts._get_voice_type("en-AU-Wavenet-B") == "wavenet"

    def test_voice_type_detection_studio(self):
        """Test voice type detection for Studio voices"""
        tts = GoogleTTS()
        assert tts._get_voice_type("en-US-Studio-O") == "studio"
        assert tts._get_voice_type("en-GB-Studio-B") == "studio"

    def test_voice_type_detection_chirp3(self):
        """Test voice type detection for Chirp3 voices"""
        tts = GoogleTTS()
        assert tts._get_voice_type("en-US-Chirp3-A") == "chirp3"
        assert tts._get_voice_type("en-GB-Chirp-B") == "chirp3"

    def test_voice_type_detection_standard(self):
        """Test voice type detection for Standard voices"""
        tts = GoogleTTS()
        assert tts._get_voice_type("en-US-Standard-A") == "standard"

    def test_pricing_configuration(self):
        """Test pricing is correctly configured"""
        assert GoogleTTS.PRICING["standard"] == 4.00
        assert GoogleTTS.PRICING["wavenet"] == 16.00
        assert GoogleTTS.PRICING["neural2"] == 16.00
        assert GoogleTTS.PRICING["studio"] == 160.00
        assert GoogleTTS.PRICING["chirp3"] == 16.00

    def test_free_tier_configuration(self):
        """Test free tier limits"""
        assert GoogleTTS.FREE_TIER["standard"] == 4_000_000
        assert GoogleTTS.FREE_TIER["wavenet"] == 1_000_000

    @pytest.mark.skipif(
        True,
        reason="Requires google-cloud-texttospeech package to be installed"
    )
    @pytest.mark.asyncio
    async def test_synthesize_stream_full_voice_format(self):
        """Test synthesis with full voice format (en-US-Neural2-A)"""
        # This test will be enabled once google-cloud-texttospeech is installed
        pass

    @pytest.mark.skipif(
        True,
        reason="Requires google-cloud-texttospeech package to be installed"
    )
    @pytest.mark.asyncio
    async def test_synthesize_stream_short_voice_format(self):
        """Test synthesis with short voice format (Neural2-A)"""
        # This test will be enabled once google-cloud-texttospeech is installed
        pass

    @pytest.mark.skipif(
        True,
        reason="Requires google-cloud-texttospeech package to be installed"
    )
    @pytest.mark.asyncio
    async def test_synthesize_file(self):
        """Test file synthesis"""
        # This test will be enabled once google-cloud-texttospeech is installed
        pass

    @pytest.mark.skipif(
        True,
        reason="Requires google-cloud-texttospeech package to be installed"
    )
    @pytest.mark.asyncio
    async def test_synthesize_error_handling(self):
        """Test error handling in synthesis"""
        # This test will be enabled once google-cloud-texttospeech is installed
        pass

    def test_popular_voice_examples(self):
        """Test that popular voice IDs are supported"""
        tts = GoogleTTS()

        popular_voices = [
            "en-US-Neural2-A",
            "en-US-Neural2-C",
            "en-US-Neural2-D",
            "en-US-Wavenet-A",
            "en-GB-Neural2-A",
            "en-AU-Neural2-A",
            "en-IN-Neural2-A",
            "en-US-Studio-O",
        ]

        for voice_id in popular_voices:
            voice_type = tts._get_voice_type(voice_id)
            assert voice_type in ["neural2", "wavenet", "studio"]


@pytest.mark.integration
class TestGoogleTTSIntegration:
    """Integration tests for Google TTS (requires credentials)"""

    @pytest.mark.skip(reason="Requires Google Cloud credentials")
    @pytest.mark.asyncio
    async def test_real_synthesis(self):
        """Test real synthesis with Google Cloud API"""
        # This test requires GOOGLE_APPLICATION_CREDENTIALS env var
        tts = GoogleTTS()
        voice_config = VoiceConfig(
            provider="google",
            voice_id="en-US-Neural2-A",
            speed=1.0
        )

        chunks = []
        async for chunk in tts.synthesize_stream("Hello from Google TTS!", voice_config):
            chunks.append(chunk)

        assert len(chunks) > 0
        audio_data = b"".join(chunks)
        assert len(audio_data) > 1000  # Should have substantial audio data

    @pytest.mark.skip(reason="Requires Google Cloud credentials")
    @pytest.mark.asyncio
    async def test_multiple_voices(self):
        """Test multiple voice synthesis"""
        tts = GoogleTTS()

        voices = [
            "en-US-Neural2-A",  # Female
            "en-US-Neural2-D",  # Male
            "en-GB-Neural2-B",  # British Male
        ]

        for voice_id in voices:
            voice_config = VoiceConfig(provider="google", voice_id=voice_id)

            chunks = []
            async for chunk in tts.synthesize_stream(f"Testing voice {voice_id}", voice_config):
                chunks.append(chunk)

            assert len(chunks) > 0
