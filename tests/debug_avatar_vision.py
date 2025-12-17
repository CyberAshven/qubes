"""
Debug Avatar Vision - Test vision API directly

This script directly tests the vision API integration to verify
that images are being sent and processed correctly.
"""

import asyncio
from pathlib import Path
import sys


async def test_vision():
    """Test vision API with Anastasia's avatar"""

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from orchestrator.user_orchestrator import UserOrchestrator

    # Initialize orchestrator
    data_dir = Path("data")
    orchestrator = UserOrchestrator(data_dir=data_dir)

    username = "bit_faced"

    # Find Anastasia
    qubes = orchestrator.list_qubes_for_user(username)
    anastasia = None

    for qube_info in qubes:
        if qube_info['qube_name'] == 'Anastasia':
            anastasia = qube_info
            break

    if not anastasia:
        print("❌ Anastasia not found!")
        return

    print(f"✅ Found Anastasia (ID: {anastasia['qube_id'][:8]}...)")

    # Load qube
    qube = await orchestrator.load_qube(username, anastasia['qube_id'])

    # Check if avatar exists
    avatar_path = qube.data_dir / "chain" / f"avatar_{qube.qube_id}.png"
    print(f"\n📁 Avatar path: {avatar_path}")
    print(f"   Exists: {avatar_path.exists()}")

    if not avatar_path.exists():
        print("❌ Avatar file not found!")
        qube.close()
        return

    # Check API keys
    print(f"\n🔑 Checking API keys...")

    # You'll need to provide your actual API key here
    api_keys = {
        "anthropic": input("Enter Anthropic API key (or press Enter to skip): ").strip(),
    }

    # Remove empty keys
    api_keys = {k: v for k, v in api_keys.items() if v}

    if not api_keys:
        print("❌ No API keys provided!")
        qube.close()
        return

    print(f"✅ API keys configured for: {list(api_keys.keys())}")

    # Initialize AI
    qube.init_ai(api_keys)
    print("✅ AI initialized")

    # Test the describe_my_appearance method
    print("\n" + "="*60)
    print("🎨 Calling describe_my_appearance()...")
    print("="*60)

    try:
        description = await qube.describe_my_appearance()

        print("\n✅ SUCCESS! Got description:")
        print("="*60)
        print(description)
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        qube.close()


if __name__ == "__main__":
    asyncio.run(test_vision())
