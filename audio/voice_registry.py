"""
Voice Registry

Registry of available TTS voices across all providers.
Follows the pattern of ai/model_registry.py for consistency.
"""

from typing import Dict, Any, Optional, List
from utils.logging import get_logger

logger = get_logger(__name__)


class VoiceRegistry:
    """
    Registry of available TTS voices across providers.

    Supports OpenAI, Gemini, ElevenLabs, Google Cloud, Piper, and Kokoro.
    """

    # Voice definitions with provider, characteristics, and metadata
    VOICES: Dict[str, Dict[str, Any]] = {
        # =====================================================================
        # OpenAI TTS Voices (tts-1, tts-1-hd models)
        # =====================================================================
        "alloy": {
            "provider": "openai",
            "name": "Alloy",
            "gender": "neutral",
            "description": "Neutral and balanced, versatile for many use cases",
            "characteristics": ["neutral", "balanced", "clear"],
        },
        "echo": {
            "provider": "openai",
            "name": "Echo",
            "gender": "male",
            "description": "Warm and engaging, good for storytelling",
            "characteristics": ["warm", "engaging", "friendly"],
        },
        "fable": {
            "provider": "openai",
            "name": "Fable",
            "gender": "neutral",
            "description": "Expressive and dramatic, great for narratives",
            "characteristics": ["expressive", "dramatic", "theatrical"],
        },
        "onyx": {
            "provider": "openai",
            "name": "Onyx",
            "gender": "male",
            "description": "Deep and authoritative, professional tone",
            "characteristics": ["deep", "authoritative", "professional"],
        },
        "nova": {
            "provider": "openai",
            "name": "Nova",
            "gender": "female",
            "description": "Friendly and upbeat, energetic delivery",
            "characteristics": ["friendly", "upbeat", "energetic"],
        },
        "shimmer": {
            "provider": "openai",
            "name": "Shimmer",
            "gender": "female",
            "description": "Clear and gentle, soft-spoken",
            "characteristics": ["clear", "gentle", "soft"],
        },

        # =====================================================================
        # Gemini TTS Voices (gemini-2.5-flash-preview-tts)
        # =====================================================================
        "Puck": {
            "provider": "gemini",
            "name": "Puck",
            "gender": "neutral",
            "description": "Upbeat and playful",
            "characteristics": ["upbeat", "playful", "energetic"],
        },
        "Charon": {
            "provider": "gemini",
            "name": "Charon",
            "gender": "neutral",
            "description": "Informative and clear",
            "characteristics": ["informative", "clear", "educational"],
        },
        "Kore": {
            "provider": "gemini",
            "name": "Kore",
            "gender": "female",
            "description": "Calm and soothing",
            "characteristics": ["calm", "soothing", "relaxed"],
        },
        "Fenrir": {
            "provider": "gemini",
            "name": "Fenrir",
            "gender": "male",
            "description": "Authoritative and commanding",
            "characteristics": ["authoritative", "commanding", "strong"],
        },
        "Aoede": {
            "provider": "gemini",
            "name": "Aoede",
            "gender": "female",
            "description": "Expressive and musical",
            "characteristics": ["expressive", "musical", "artistic"],
        },
        "Zephyr": {
            "provider": "gemini",
            "name": "Zephyr",
            "gender": "neutral",
            "description": "Bright and airy",
            "characteristics": ["bright", "airy", "light"],
        },

        # =====================================================================
        # ElevenLabs Voices (common presets - actual availability depends on account)
        # =====================================================================
        "Rachel": {
            "provider": "elevenlabs",
            "name": "Rachel",
            "gender": "female",
            "description": "Young female, calm and composed",
            "characteristics": ["calm", "composed", "young"],
        },
        "Domi": {
            "provider": "elevenlabs",
            "name": "Domi",
            "gender": "female",
            "description": "Young female, strong and confident",
            "characteristics": ["strong", "confident", "assertive"],
        },
        "Bella": {
            "provider": "elevenlabs",
            "name": "Bella",
            "gender": "female",
            "description": "Young female, soft and gentle",
            "characteristics": ["soft", "gentle", "warm"],
        },
        "Antoni": {
            "provider": "elevenlabs",
            "name": "Antoni",
            "gender": "male",
            "description": "Young male, well-rounded and natural",
            "characteristics": ["natural", "well-rounded", "conversational"],
        },
        "Josh": {
            "provider": "elevenlabs",
            "name": "Josh",
            "gender": "male",
            "description": "Young male, deep and resonant",
            "characteristics": ["deep", "resonant", "warm"],
        },
        "Arnold": {
            "provider": "elevenlabs",
            "name": "Arnold",
            "gender": "male",
            "description": "Middle-aged male, crisp and clear",
            "characteristics": ["crisp", "clear", "professional"],
        },
        "Adam": {
            "provider": "elevenlabs",
            "name": "Adam",
            "gender": "male",
            "description": "Middle-aged male, deep and authoritative",
            "characteristics": ["deep", "authoritative", "mature"],
        },
        "Sam": {
            "provider": "elevenlabs",
            "name": "Sam",
            "gender": "male",
            "description": "Young male, raspy and unique",
            "characteristics": ["raspy", "unique", "distinctive"],
        },

        # =====================================================================
        # Piper Voices (local, offline TTS)
        # =====================================================================
        "en_US-lessac-medium": {
            "provider": "piper",
            "name": "Lessac",
            "gender": "neutral",
            "description": "US English, medium quality, balanced",
            "characteristics": ["balanced", "clear", "neutral"],
            "language": "en_US",
        },
        "en_US-libritts-high": {
            "provider": "piper",
            "name": "LibriTTS",
            "gender": "neutral",
            "description": "US English, high quality, natural",
            "characteristics": ["natural", "high-quality", "clear"],
            "language": "en_US",
        },
        "en_GB-alba-medium": {
            "provider": "piper",
            "name": "Alba",
            "gender": "female",
            "description": "British English, medium quality",
            "characteristics": ["british", "clear", "professional"],
            "language": "en_GB",
        },
    }

    @classmethod
    def get_voice(cls, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get voice info by ID.

        Args:
            voice_id: Voice identifier

        Returns:
            Voice info dict or None if not found
        """
        return cls.VOICES.get(voice_id)

    @classmethod
    def is_valid_voice(cls, voice_id: str) -> bool:
        """Check if a voice ID is valid across all providers (registry, Kokoro, custom)."""
        if voice_id in cls.VOICES:
            return True
        # Kokoro voices follow the pattern: {lang}{gender}_{name} (e.g., af_heart, bm_george)
        try:
            from audio.kokoro_tts import KokoroTTSProvider
            for voices in KokoroTTSProvider.VOICES.values():
                if voice_id in voices:
                    return True
        except ImportError:
            pass
        # Custom and Qwen3 voices are user-defined — always valid
        if voice_id.startswith(("custom:", "qwen3:", "qwen:")):
            return True
        return False

    @classmethod
    def list_voices(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available voices."""
        return cls.VOICES.copy()

    @classmethod
    def list_by_provider(cls, provider: str) -> Dict[str, Dict[str, Any]]:
        """
        Get voices for a specific provider.

        Args:
            provider: Provider name (openai, gemini, elevenlabs, piper)

        Returns:
            Dict of voice_id -> voice_info for that provider
        """
        return {
            voice_id: info
            for voice_id, info in cls.VOICES.items()
            if info["provider"] == provider
        }

    @classmethod
    def list_by_characteristic(cls, characteristic: str) -> Dict[str, Dict[str, Any]]:
        """
        Get voices with a specific characteristic.

        Args:
            characteristic: Characteristic to search for (e.g., "warm", "calm")

        Returns:
            Dict of matching voices
        """
        return {
            voice_id: info
            for voice_id, info in cls.VOICES.items()
            if characteristic.lower() in [c.lower() for c in info.get("characteristics", [])]
        }

    @classmethod
    def list_by_gender(cls, gender: str) -> Dict[str, Dict[str, Any]]:
        """
        Get voices by gender.

        Args:
            gender: "male", "female", or "neutral"

        Returns:
            Dict of matching voices
        """
        return {
            voice_id: info
            for voice_id, info in cls.VOICES.items()
            if info.get("gender", "").lower() == gender.lower()
        }

    @classmethod
    def get_providers(cls) -> List[str]:
        """Get list of all providers with voices."""
        return list(set(info["provider"] for info in cls.VOICES.values()))

    @classmethod
    def get_default_voice(cls, provider: str = "openai") -> str:
        """
        Get the default voice for a provider.

        Args:
            provider: Provider name

        Returns:
            Default voice_id for that provider
        """
        defaults = {
            "openai": "alloy",
            "gemini": "Puck",
            "elevenlabs": "Rachel",
            "piper": "en_US-lessac-medium",
        }
        return defaults.get(provider, "alloy")


# Module-level convenience function
def get_available_voices() -> Dict[str, Dict[str, Any]]:
    """
    Get all available TTS voices.

    Convenience function that delegates to VoiceRegistry.

    Returns:
        Dict mapping voice_id to voice info
    """
    return VoiceRegistry.list_voices()
