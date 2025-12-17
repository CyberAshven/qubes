"""
Avatar Generation Example

Demonstrates how to create Qubes with AI-generated avatars using DALL-E 3.
"""

import asyncio
from pathlib import Path

from orchestrator.user_orchestrator import UserOrchestrator
from ai.avatar_generator import AvatarGenerator


async def example_1_basic_generation():
    """Example 1: Basic avatar generation"""
    print("\n" + "="*70)
    print("Example 1: Basic Avatar Generation")
    print("="*70 + "\n")

    # Initialize orchestrator
    orchestrator = UserOrchestrator("example_user")
    orchestrator.set_master_key("secure_password_123")

    # Create Qube with avatar generation
    config = {
        "name": "TechHelper",
        "genesis_prompt": "A friendly AI assistant that helps with technical questions. Professional and knowledgeable.",
        "ai_model": "claude-sonnet-4.5",
        "wallet_address": "bitcoincash:qr5agtachyxvrwxu76vzszan5pnvuzy8duhv4lxrsk",
        "generate_avatar": True,  # Enable avatar generation
        "favorite_color": "#4A90E2"  # Blue theme
    }

    print("Creating Qube with avatar generation...")
    print(f"  Name: {config['name']}")
    print(f"  Style: cyberpunk (default)")
    print(f"  Color: {config['favorite_color']}")
    print()

    try:
        qube = await orchestrator.create_qube(config)

        avatar_data = qube.genesis_block.to_dict()["avatar"]
        print("✅ Qube created successfully!")
        print(f"  Qube ID: {qube.qube_id[:16]}...")
        print(f"  Avatar Source: {avatar_data['source']}")
        print(f"  Avatar Path: {avatar_data.get('local_path', 'N/A')}")
        if avatar_data.get('ipfs_cid'):
            print(f"  IPFS CID: {avatar_data['ipfs_cid']}")
        print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()


async def example_2_custom_style():
    """Example 2: Custom avatar style"""
    print("\n" + "="*70)
    print("Example 2: Custom Avatar Style")
    print("="*70 + "\n")

    orchestrator = UserOrchestrator("example_user")
    orchestrator.set_master_key("secure_password_123")

    # List available styles
    styles = AvatarGenerator.list_styles()
    print("Available styles:")
    for style, description in styles.items():
        print(f"  - {style}: {description}")
    print()

    # Create Qube with anime style
    config = {
        "name": "AnimeBot",
        "genesis_prompt": "A playful and creative AI that loves art and storytelling.",
        "ai_model": "gpt-5",
        "wallet_address": "bitcoincash:qr5agtachyxvrwxu76vzszan5pnvuzy8duhv4lxrsk",
        "generate_avatar": True,
        "avatar_style": "anime",  # Custom style
        "favorite_color": "#FF69B4"  # Pink
    }

    print(f"Creating Qube with {config['avatar_style']} style...")
    print()

    try:
        qube = await orchestrator.create_qube(config)

        avatar_data = qube.genesis_block.to_dict()["avatar"]
        print("✅ Qube created successfully!")
        print(f"  Style: {avatar_data['style']}")
        print(f"  Avatar Path: {avatar_data.get('local_path', 'N/A')}")
        print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()


async def example_3_upload_avatar():
    """Example 3: Upload existing avatar instead of generating"""
    print("\n" + "="*70)
    print("Example 3: Upload Existing Avatar")
    print("="*70 + "\n")

    orchestrator = UserOrchestrator("example_user")
    orchestrator.set_master_key("secure_password_123")

    # Use existing avatar file
    avatar_file = Path("images/qubes_logo.png")

    config = {
        "name": "CustomAvatarBot",
        "genesis_prompt": "An AI with a custom uploaded avatar.",
        "ai_model": "gemini-2.5-pro",
        "wallet_address": "bitcoincash:qr5agtachyxvrwxu76vzszan5pnvuzy8duhv4lxrsk",
        "avatar_file": str(avatar_file)  # Upload instead of generate
    }

    print(f"Creating Qube with uploaded avatar...")
    print(f"  Avatar File: {avatar_file}")
    print()

    try:
        qube = await orchestrator.create_qube(config)

        avatar_data = qube.genesis_block.to_dict()["avatar"]
        print("✅ Qube created successfully!")
        print(f"  Avatar Source: {avatar_data['source']}")
        print(f"  Avatar Path: {avatar_data['local_path']}")
        if avatar_data.get('ipfs_cid'):
            print(f"  IPFS CID: {avatar_data['ipfs_cid']}")
        print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()


async def example_4_fallback():
    """Example 4: Fallback to default avatar"""
    print("\n" + "="*70)
    print("Example 4: Default Avatar Fallback")
    print("="*70 + "\n")

    orchestrator = UserOrchestrator("example_user")
    orchestrator.set_master_key("secure_password_123")

    # Create Qube without specifying avatar
    config = {
        "name": "DefaultAvatarBot",
        "genesis_prompt": "An AI using the default Qubes avatar.",
        "ai_model": "claude-opus-4.1",
        "wallet_address": "bitcoincash:qr5agtachyxvrwxu76vzszan5pnvuzy8duhv4lxrsk"
        # No avatar_file or generate_avatar specified
    }

    print("Creating Qube without avatar specification...")
    print("  Will use default avatar")
    print()

    try:
        qube = await orchestrator.create_qube(config)

        avatar_data = qube.genesis_block.to_dict()["avatar"]
        print("✅ Qube created successfully!")
        print(f"  Avatar Source: {avatar_data['source']}")
        print(f"  Avatar Path: {avatar_data['local_path']}")
        print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()


async def example_5_direct_generation():
    """Example 5: Direct avatar generation (without Qube creation)"""
    print("\n" + "="*70)
    print("Example 5: Direct Avatar Generation")
    print("="*70 + "\n")

    generator = AvatarGenerator()

    print("Generating avatar directly (no Qube creation)...")
    print()

    try:
        avatar_data = await generator.generate_avatar(
            qube_id="direct_test_" + "abc123",
            qube_name="DirectTest",
            genesis_prompt="A mysterious AI with abstract aesthetics.",
            favorite_color="#9B59B6",  # Purple
            style="abstract"
        )

        print("✅ Avatar generated successfully!")
        print(f"  Local Path: {avatar_data['local_path']}")
        print(f"  Style: {avatar_data['style']}")
        print(f"  Dimensions: {avatar_data['dimensions']}")
        print(f"  Model: {avatar_data['model']}")
        print(f"  Prompt: {avatar_data['prompt'][:100]}...")
        print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()


async def main():
    """Run all examples"""

    print("\n" + "="*70)
    print("🎨 AVATAR GENERATION EXAMPLES")
    print("="*70)

    # Check if API key is configured
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not found in environment")
        print("   Set it in .env file to enable avatar generation\n")
        print("   Examples 1, 2, and 5 will fail without the API key.")
        print("   Examples 3 and 4 will work (upload and default).\n")

    # Run examples
    await example_1_basic_generation()
    await example_2_custom_style()
    await example_3_upload_avatar()
    await example_4_fallback()
    await example_5_direct_generation()

    print("="*70)
    print("✨ All examples complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run examples
    asyncio.run(main())
