"""
Manual test for Gemini TTS integration

Run this script to test Gemini TTS with your Google API key.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from audio.audio_manager import AudioManager
from audio.tts_engine import VoiceConfig


async def test_gemini_tts():
    """Test Gemini TTS provider"""

    print("🎤 Testing Gemini TTS Integration")
    print("=" * 50)

    # Initialize audio manager
    audio = AudioManager()

    # Check available providers
    print(f"\nAvailable TTS providers: {list(audio.tts_providers.keys())}")

    if "gemini" not in audio.tts_providers:
        print("❌ Gemini TTS not initialized!")
        print("   Check that GOOGLE_API_KEY is set in .env")
        return

    print("✅ Gemini TTS provider initialized!")

    # Test voices
    test_voices = [
        ("Puck", "Upbeat voice"),
        ("Charon", "Informative voice"),
        ("Kore", "Calm voice"),
        ("Zephyr", "Bright voice"),
    ]

    print(f"\n🎵 Testing {len(test_voices)} Gemini voices:")
    print("-" * 50)

    for voice_name, description in test_voices:
        print(f"\n  Testing: {voice_name} ({description})")

        voice_config = VoiceConfig(
            provider="gemini",
            voice_id=voice_name
        )

        test_text = f"Hello! I'm {voice_name}, testing the Gemini text to speech API."

        try:
            # Generate speech file
            output_path = Path(f"test_output_{voice_name.lower()}.wav")

            print(f"  Generating speech...")
            result = await audio.generate_speech_file(
                text=test_text,
                voice_model=voice_name,
                provider="gemini"
            )

            print(f"  ✅ Success! Audio saved to: {result}")
            print(f"     File size: {result.stat().st_size:,} bytes")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("✅ Gemini TTS test complete!")
    print("\nAvailable voices:")
    print("  - Puck (Upbeat)")
    print("  - Charon (Informative)")
    print("  - Kore (Calm)")
    print("  - Fenrir (Authoritative)")
    print("  - Aoede (Expressive)")
    print("  - Zephyr (Bright)")
    print("  ... and 24 more voices available!")


async def test_gemini_streaming():
    """Test Gemini TTS streaming"""

    print("\n🎵 Testing Gemini TTS Streaming")
    print("=" * 50)

    audio = AudioManager()

    voice_config = VoiceConfig(
        provider="gemini",
        voice_id="Puck"
    )

    text = "This is a streaming test for Gemini text to speech. The audio should play as it's being generated!"

    try:
        print("Playing audio (streaming)...")
        await audio.speak(text, voice_config)
        print("✅ Streaming playback complete!")

    except Exception as e:
        print(f"❌ Streaming error: {e}")


if __name__ == "__main__":
    print("\n" + "🤖 Qubes - Gemini TTS Test Suite".center(50) + "\n")

    # Check if API key is configured
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not found in environment!")
        print("   Please add it to your .env file")
        exit(1)

    # Run tests
    asyncio.run(test_gemini_tts())

    # Uncomment to test streaming:
    # asyncio.run(test_gemini_streaming())

    print("\n✨ All tests complete!\n")
