"""
Live Qube Test with Real API Keys

Tests the complete AI integration with real models:
- Creates a Qube with real API keys from .env
- Processes messages with AI reasoning
- Uses tools (web search, image generation)
- Shows the full reasoning loop
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.qube import Qube
from utils.logging import configure_logging


async def test_live_qube():
    """Test Qube with real API keys"""

    # Load API keys from .env
    load_dotenv()

    api_keys = {}

    if os.getenv("OPENAI_API_KEY"):
        api_keys["openai"] = os.getenv("OPENAI_API_KEY")
        print("✅ OpenAI API key loaded")

    if os.getenv("ANTHROPIC_API_KEY"):
        api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
        print("✅ Anthropic API key loaded")

    if os.getenv("GOOGLE_API_KEY"):
        api_keys["google"] = os.getenv("GOOGLE_API_KEY")
        print("✅ Google API key loaded")

    if os.getenv("PERPLEXITY_API_KEY"):
        api_keys["perplexity"] = os.getenv("PERPLEXITY_API_KEY")
        print("✅ Perplexity API key loaded")

    if not api_keys:
        print("❌ No API keys found in .env file")
        print("Please add at least OPENAI_API_KEY to your .env file")
        return

    print(f"\n📊 Loaded {len(api_keys)} API key(s)")
    print("=" * 70)

    # Configure logging
    configure_logging(log_level="INFO", console_output=True)

    # Create a test Qube with real configuration
    print("\n🔧 Creating Qube...")
    qube = Qube.create_new(
        qube_name="Athena",
        creator="test_user",
        genesis_prompt="""You are Athena, a helpful AI assistant with expertise in technology and blockchain.
You are knowledgeable, friendly, and always provide accurate information.
When asked questions, you can use tools like web search to get the latest information.""",
        ai_model="gpt-4o-mini",  # Fast and cost-effective
        voice_model="alloy",  # OpenAI TTS voice
        data_dir=Path("./data"),
        favorite_color="#4A90E2",
        capabilities={
            "web_search": True,
            "image_generation": True,
            "image_processing": True,
            "tts": True,
            "stt": True,
            "code_execution": False
        },
        api_keys=api_keys  # Initialize AI immediately
    )

    print(f"✅ Qube created: {qube.qube_id} - {qube.genesis_block.qube_name}")
    print(f"   Model: {qube.current_ai_model}")
    print(f"   AI Ready: {qube.reasoner is not None}")
    print(f"   Tools Available: {len(qube.tool_registry.tools)}")
    print("=" * 70)

    # Test 1: Simple conversation
    print("\n📝 TEST 1: Simple Conversation")
    print("-" * 70)

    try:
        response1 = await qube.process_message(
            "Hello! What's your name and what can you help me with?"
        )
        print(f"\n🤖 Athena: {response1}\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Question requiring reasoning
    print("\n🧠 TEST 2: Reasoning Question")
    print("-" * 70)

    try:
        response2 = await qube.process_message(
            "What's 2+2? Then explain why this basic math is important."
        )
        print(f"\n🤖 Athena: {response2}\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Web search (if Perplexity key available)
    if "perplexity" in api_keys:
        print("\n🔍 TEST 3: Web Search")
        print("-" * 70)

        try:
            response3 = await qube.process_message(
                "What's the latest news about Bitcoin Cash? Use web search to find current information."
            )
            print(f"\n🤖 Athena: {response3}\n")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("\n⏭️  TEST 3: Skipped (no Perplexity API key)")

    # Test 4: Memory search
    print("\n🧠 TEST 4: Memory Search")
    print("-" * 70)

    try:
        # First, anchor the session to make messages searchable
        qube.anchor_session()
        print("   Session anchored to permanent memory")

        # Now search memory
        response4 = await qube.process_message(
            "What did we talk about earlier? Search your memory."
        )
        print(f"\n🤖 Athena: {response4}\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Show memory stats
    print("\n📊 MEMORY STATISTICS")
    print("=" * 70)
    stats = qube.get_memory_stats()
    print(f"Qube ID: {stats['qube_id']}")
    print(f"Qube Name: {stats['qube_name']}")
    print(f"AI Model: {stats['ai_model']}")
    print(f"Permanent Blocks: {stats['permanent_blocks']}")
    print(f"Session Blocks: {stats['session_blocks']}")
    print(f"Total Blocks: {stats['total_blocks']}")

    # Show recent blocks
    print(f"\n📜 RECENT BLOCKS (last 5):")
    print("-" * 70)
    chain_length = qube.memory_chain.get_chain_length()
    start = max(0, chain_length - 5)

    for i in range(start, chain_length):
        block = qube.memory_chain.get_block(i)
        print(f"{i}. {block.block_type} - {block.timestamp}")
        if block.block_type == "MESSAGE":
            msg_type = block.content.get("message_type", "")
            msg_body = block.content.get("message_body", "")[:50]
            print(f"   {msg_type}: {msg_body}...")
        elif block.block_type == "THOUGHT":
            monologue = block.content.get("internal_monologue", "")[:50]
            print(f"   Thought: {monologue}...")
        elif block.block_type == "SUMMARY":
            summary = block.content.get("summary_text", "")[:50]
            print(f"   Summary: {summary}...")

    # Cleanup
    print("\n" + "=" * 70)
    print("🧹 Cleaning up...")
    qube.close()
    print("✅ Test complete!")


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 LIVE QUBE TEST WITH REAL API KEYS")
    print("=" * 70)

    asyncio.run(test_live_qube())
