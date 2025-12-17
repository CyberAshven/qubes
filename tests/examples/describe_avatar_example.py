"""
Example: Describe Qube Avatar Using Vision AI

This example demonstrates how to use the describe_my_appearance() method
to have a qube describe their avatar using vision AI in real-time.
"""

import asyncio
from pathlib import Path
from orchestrator import QubeOrchestrator


async def main():
    """Demonstrate avatar description functionality"""

    # Initialize orchestrator
    data_dir = Path("data")
    orchestrator = QubeOrchestrator(data_dir=data_dir)

    # Set username (replace with your actual username)
    username = "bit_faced"

    # List available qubes
    qubes = orchestrator.list_qubes_for_user(username)

    if not qubes:
        print(f"No qubes found for user '{username}'")
        print("Please create a qube first using create_qube_simple.py or create_qube_complete.py")
        return

    print(f"Found {len(qubes)} qube(s) for user '{username}':")
    for i, qube_info in enumerate(qubes, 1):
        print(f"{i}. {qube_info['qube_name']} (ID: {qube_info['qube_id'][:8]}...)")

    # Select first qube (or prompt user to choose)
    selected_qube_info = qubes[0]
    qube_id = selected_qube_info['qube_id']

    print(f"\nLoading qube: {selected_qube_info['qube_name']}")

    # Load the qube (you'll need to provide API keys)
    # For this example, we'll assume you have API keys configured
    api_keys = {
        "anthropic": "your-anthropic-key-here",  # Replace with actual key
        # or "openai": "your-openai-key-here",
        # or "google": "your-google-key-here"
    }

    try:
        qube = await orchestrator.load_qube(username, qube_id)

        # Initialize AI with your API keys
        qube.init_ai(api_keys)

        print(f"\nGenerating avatar description for {qube.name}...")
        print("This may take a few seconds...\n")

        # Call the new describe_my_appearance method
        description = await qube.describe_my_appearance()

        print("=" * 60)
        print(f"{qube.name}'s Self-Description:")
        print("=" * 60)
        print(description)
        print("=" * 60)

        # You can also specify a different vision model:
        # description = await qube.describe_my_appearance(model_override="gpt-4o")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        if 'qube' in locals():
            qube.close()


if __name__ == "__main__":
    print("Qube Avatar Description Example")
    print("=" * 60)

    asyncio.run(main())
