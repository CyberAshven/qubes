"""
Audio Integration Module - TTS & STT

Provides text-to-speech and speech-to-text capabilities with multiple providers.
From docs/27_Audio_TTS_STT_Integration.md
"""

from audio.audio_manager import AudioManager
from audio.tts_engine import TTSProvider, OpenAITTS, ElevenLabsTTS, PiperTTS, VoiceConfig
from audio.stt_engine import STTProvider, OpenAIWhisper, DeepGramSTT, WhisperCppSTT
from audio.playback import AudioPlayer
from audio.recorder import AudioRecorder
from audio.command_parser import VoiceCommandParser
from audio.hallucination_filter import HallucinationFilter
from audio.cache import AudioCache
from audio.rate_limiter import AudioRateLimiter
from audio.command_security import requires_confirmation, execute_voice_command

__all__ = [
    "AudioManager",
    "VoiceConfig",
    "TTSProvider",
    "OpenAITTS",
    "ElevenLabsTTS",
    "PiperTTS",
    "STTProvider",
    "OpenAIWhisper",
    "DeepGramSTT",
    "WhisperCppSTT",
    "AudioPlayer",
    "AudioRecorder",
    "VoiceCommandParser",
    "HallucinationFilter",
    "AudioCache",
    "AudioRateLimiter",
    "requires_confirmation",
    "execute_voice_command",
]
