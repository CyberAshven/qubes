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
        # OpenAI TTS Voices
        # alloy-shimmer: available on tts-1, tts-1-hd, and gpt-4o-mini-tts
        # ballad-cedar: gpt-4o-mini-tts only
        # =====================================================================
        "alloy": {
            "provider": "openai",
            "name": "Alloy",
            "gender": "female",
            "description": "Neutral and balanced, versatile for many use cases",
            "characteristics": ["neutral", "balanced", "clear"],
        },
        "ash": {
            "provider": "openai",
            "name": "Ash",
            "gender": "male",
            "description": "Conversational and versatile",
            "characteristics": ["conversational", "versatile", "warm"],
        },
        "coral": {
            "provider": "openai",
            "name": "Coral",
            "gender": "female",
            "description": "Warm and friendly, natural delivery",
            "characteristics": ["warm", "friendly", "natural"],
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
            "gender": "male",
            "description": "Expressive and dramatic, great for narratives",
            "characteristics": ["expressive", "dramatic", "theatrical"],
        },
        "nova": {
            "provider": "openai",
            "name": "Nova",
            "gender": "female",
            "description": "Friendly and upbeat, energetic delivery",
            "characteristics": ["friendly", "upbeat", "energetic"],
        },
        "onyx": {
            "provider": "openai",
            "name": "Onyx",
            "gender": "male",
            "description": "Deep and authoritative, professional tone",
            "characteristics": ["deep", "authoritative", "professional"],
        },
        "sage": {
            "provider": "openai",
            "name": "Sage",
            "gender": "female",
            "description": "Calm and thoughtful, professional tone",
            "characteristics": ["calm", "thoughtful", "professional"],
        },
        "shimmer": {
            "provider": "openai",
            "name": "Shimmer",
            "gender": "female",
            "description": "Clear and gentle, soft-spoken",
            "characteristics": ["clear", "gentle", "soft"],
        },
        # gpt-4o-mini-tts exclusive voices
        "ballad": {
            "provider": "openai",
            "name": "Ballad",
            "gender": "male",
            "description": "Warm and melodic, storytelling voice",
            "characteristics": ["warm", "melodic", "storytelling"],
            "tts_model": "gpt-4o-mini-tts",
        },
        "verse": {
            "provider": "openai",
            "name": "Verse",
            "gender": "male",
            "description": "Measured and poetic, calm delivery",
            "characteristics": ["measured", "poetic", "calm"],
            "tts_model": "gpt-4o-mini-tts",
        },
        "marin": {
            "provider": "openai",
            "name": "Marin",
            "gender": "female",
            "description": "Bright and clear, recommended for quality",
            "characteristics": ["bright", "clear", "natural"],
            "tts_model": "gpt-4o-mini-tts",
        },
        "cedar": {
            "provider": "openai",
            "name": "Cedar",
            "gender": "male",
            "description": "Rich and grounded, natural feel",
            "characteristics": ["rich", "grounded", "natural"],
            "tts_model": "gpt-4o-mini-tts",
        },

        # =====================================================================
        # Gemini TTS Voices (gemini-2.5-flash-preview-tts) — 30 voices
        # =====================================================================
        "Achernar": {"provider": "gemini", "name": "Achernar", "gender": "male", "description": "Warm and clear", "characteristics": ["warm", "clear"]},
        "Achird": {"provider": "gemini", "name": "Achird", "gender": "female", "description": "Friendly and bright", "characteristics": ["friendly", "bright"]},
        "Algenib": {"provider": "gemini", "name": "Algenib", "gender": "male", "description": "Confident and steady", "characteristics": ["confident", "steady"]},
        "Algieba": {"provider": "gemini", "name": "Algieba", "gender": "female", "description": "Smooth and engaging", "characteristics": ["smooth", "engaging"]},
        "Alnilam": {"provider": "gemini", "name": "Alnilam", "gender": "male", "description": "Resonant and strong", "characteristics": ["resonant", "strong"]},
        "Aoede": {"provider": "gemini", "name": "Aoede", "gender": "female", "description": "Expressive and musical", "characteristics": ["expressive", "musical"]},
        "Autonoe": {"provider": "gemini", "name": "Autonoe", "gender": "female", "description": "Gentle and thoughtful", "characteristics": ["gentle", "thoughtful"]},
        "Callirrhoe": {"provider": "gemini", "name": "Callirrhoe", "gender": "female", "description": "Elegant and poised", "characteristics": ["elegant", "poised"]},
        "Charon": {"provider": "gemini", "name": "Charon", "gender": "male", "description": "Informative and clear", "characteristics": ["informative", "clear"]},
        "Despina": {"provider": "gemini", "name": "Despina", "gender": "female", "description": "Lively and energetic", "characteristics": ["lively", "energetic"]},
        "Enceladus": {"provider": "gemini", "name": "Enceladus", "gender": "female", "description": "Calm and measured", "characteristics": ["calm", "measured"]},
        "Erinome": {"provider": "gemini", "name": "Erinome", "gender": "female", "description": "Warm and natural", "characteristics": ["warm", "natural"]},
        "Fenrir": {"provider": "gemini", "name": "Fenrir", "gender": "male", "description": "Authoritative and commanding", "characteristics": ["authoritative", "commanding"]},
        "Gacrux": {"provider": "gemini", "name": "Gacrux", "gender": "male", "description": "Deep and mature", "characteristics": ["deep", "mature"]},
        "Iapetus": {"provider": "gemini", "name": "Iapetus", "gender": "male", "description": "Clear and precise", "characteristics": ["clear", "precise"]},
        "Kore": {"provider": "gemini", "name": "Kore", "gender": "female", "description": "Calm and soothing", "characteristics": ["calm", "soothing"]},
        "Laomedeia": {"provider": "gemini", "name": "Laomedeia", "gender": "female", "description": "Soft and melodic", "characteristics": ["soft", "melodic"]},
        "Leda": {"provider": "gemini", "name": "Leda", "gender": "female", "description": "Light and airy", "characteristics": ["light", "airy"]},
        "Orus": {"provider": "gemini", "name": "Orus", "gender": "male", "description": "Steady and reliable", "characteristics": ["steady", "reliable"]},
        "Puck": {"provider": "gemini", "name": "Puck", "gender": "male", "description": "Upbeat and playful", "characteristics": ["upbeat", "playful"]},
        "Pulcherrima": {"provider": "gemini", "name": "Pulcherrima", "gender": "female", "description": "Rich and beautiful", "characteristics": ["rich", "beautiful"]},
        "Rasalgethi": {"provider": "gemini", "name": "Rasalgethi", "gender": "male", "description": "Warm and resonant", "characteristics": ["warm", "resonant"]},
        "Sadachbia": {"provider": "gemini", "name": "Sadachbia", "gender": "male", "description": "Friendly and open", "characteristics": ["friendly", "open"]},
        "Sadaltager": {"provider": "gemini", "name": "Sadaltager", "gender": "male", "description": "Calm and grounded", "characteristics": ["calm", "grounded"]},
        "Schedar": {"provider": "gemini", "name": "Schedar", "gender": "female", "description": "Professional and polished", "characteristics": ["professional", "polished"]},
        "Sulafat": {"provider": "gemini", "name": "Sulafat", "gender": "female", "description": "Bright and cheerful", "characteristics": ["bright", "cheerful"]},
        "Umbriel": {"provider": "gemini", "name": "Umbriel", "gender": "male", "description": "Mysterious and deep", "characteristics": ["mysterious", "deep"]},
        "Vindemiatrix": {"provider": "gemini", "name": "Vindemiatrix", "gender": "female", "description": "Graceful and elegant", "characteristics": ["graceful", "elegant"]},
        "Zephyr": {"provider": "gemini", "name": "Zephyr", "gender": "male", "description": "Bright and airy", "characteristics": ["bright", "airy"]},
        "Zubenelgenubi": {"provider": "gemini", "name": "Zubenelgenubi", "gender": "female", "description": "Unique and distinctive", "characteristics": ["unique", "distinctive"]},

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
