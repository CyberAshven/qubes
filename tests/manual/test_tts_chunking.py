"""
Test script for TTS chunking functionality

Tests:
1. Short message (< 4000 chars) → 1 chunk
2. Medium message (4000-8000 chars) → 2 chunks
3. Long message (> 8000 chars) → 3+ chunks
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from audio.audio_manager import AudioManager, chunk_text_for_tts


async def test_tts_chunking():
    """Test TTS generation with various message lengths"""

    # Create test data directory
    test_dir = project_root / "data" / "test_tts_chunks"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Initialize audio manager with test directory
    config = {
        "openai_api_key": None,  # Will skip actual TTS generation
    }

    audio_manager = AudioManager(config=config, qube_data_dir=test_dir)

    print("=" * 60)
    print("TTS CHUNKING TEST")
    print("=" * 60)

    # Test cases
    test_cases = [
        {
            "name": "Short message",
            "text": "This is a short test message. " * 50,  # ~1500 chars
            "expected_chunks": 1
        },
        {
            "name": "Medium message",
            "text": "This is a sentence for testing. " * 150,  # ~4800 chars
            "expected_chunks": 2
        },
        {
            "name": "Long message",
            "text": "This is a longer sentence for chunking tests. " * 300,  # ~14100 chars
            "expected_chunks": 4
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 60)

        text = test_case["text"]
        expected_chunks = test_case["expected_chunks"]

        print(f"Text length: {len(text)} chars")
        print(f"Expected chunks: {expected_chunks}")

        # Test chunking logic (without actual TTS generation)
        chunks = chunk_text_for_tts(text, max_chars=4000)
        actual_chunks = len(chunks)

        print(f"Actual chunks: {actual_chunks}")

        # Verify chunk sizes
        for j, chunk in enumerate(chunks, 1):
            chunk_len = len(chunk)
            status = "✅" if chunk_len <= 4000 else "❌"
            print(f"  Chunk {j}: {chunk_len} chars {status}")

        # Check if matches expected
        if actual_chunks == expected_chunks:
            print(f"✅ PASS: Got {actual_chunks} chunks as expected")
        else:
            print(f"❌ FAIL: Expected {expected_chunks}, got {actual_chunks}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

    # Test filename generation logic
    print("\n" + "=" * 60)
    print("FILENAME GENERATION TEST")
    print("=" * 60)

    block_number = -15
    extension = "mp3"

    # Single chunk
    print(f"\nSingle chunk (block {block_number}):")
    filename = f"audio_block_{block_number}.{extension}"
    print(f"  {filename}")

    # Multiple chunks
    print(f"\nMultiple chunks (block {block_number}, 3 chunks):")
    for chunk_idx in range(1, 4):
        filename = f"audio_block_{block_number}_chunk_{chunk_idx}.{extension}"
        print(f"  {filename}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tts_chunking())
