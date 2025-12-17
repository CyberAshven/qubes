"""
Test Real NFT Minting on Bitcoin Cash Mainnet

This script performs a REAL NFT mint using the platform minting token.
It will create an actual transaction on Bitcoin Cash mainnet.
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

# Mock Qube class for testing
class MockQube:
    """Mock Qube for testing NFT minting"""

    def __init__(self):
        self.qube_id = "TEST0001"
        self.name = "Test Qube - First NFT"
        self.genesis_block = {
            "block_hash": "0000000000000000000000000000000000000000000000000000000000000001",
            "creator": "test_creator_key",
            "birth_timestamp": "2025-10-04T18:30:00Z",
            "genesis_prompt": "This is a test Qube for verifying NFT minting on mainnet.",
            "ai_model": "claude-sonnet-4.5"
        }
        self.avatar_ipfs_uri = ""


def main():
    print("=" * 70)
    print("🧪 TESTING REAL NFT MINTING ON MAINNET")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will create a REAL transaction on Bitcoin Cash mainnet!")
    print("   It will use a small amount of BCH (~0.0001 BCH fee)")
    print()

    # Check minting token exists
    config_path = Path("data/platform/minting_token.json")
    if not config_path.exists():
        print("❌ Platform minting token not configured!")
        print("   Run: python save_minting_token_quick.py")
        return

    # Load config
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)

    print("✅ Minting token configuration loaded:")
    print(f"   Category ID: {config['category_id']}")
    print(f"   Network:     {config['network']}")
    print()

    # Check for minting key
    minting_key = os.getenv("PLATFORM_BCH_MINTING_KEY")
    if not minting_key:
        print("❌ PLATFORM_BCH_MINTING_KEY not found in .env")
        return

    print("✅ Minting key found")
    print()

    # Use platform cashtoken address as recipient
    from bitcash import Key
    key = Key(minting_key)
    recipient = key.cashtoken_address  # Use cashtoken address format (starts with 'z')
    print(f"✅ Using platform CashToken address as recipient: {recipient}")

    print()
    print("=" * 70)
    print("🔨 MINTING NFT...")
    print("=" * 70)
    print()

    # Create mock Qube
    test_qube = MockQube()

    print(f"📦 Test Qube Details:")
    print(f"   ID:   {test_qube.qube_id}")
    print(f"   Name: {test_qube.name}")
    print()

    # Import blockchain manager
    try:
        from blockchain.manager import BlockchainManager

        # Create manager
        manager = BlockchainManager(network=config['network'])

        # Mint NFT
        print("🔨 Creating NFT on blockchain...")
        import asyncio

        async def mint():
            result = await manager.mint_qube_nft(
                qube=test_qube,
                recipient_address=recipient,
                upload_to_ipfs=False  # Skip IPFS for quick test
            )
            return result

        result = asyncio.run(mint())

        print()
        print("=" * 70)
        print("✅ NFT MINTED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print(f"📋 Mint Results:")
        print(f"   Qube ID:     {result['qube_id']}")
        print(f"   Category ID: {result['category_id']}")
        print(f"   Mint TX:     {result['mint_txid']}")
        print(f"   Recipient:   {result['recipient_address']}")
        print(f"   Network:     {result['network']}")
        print()
        print("🌐 View on blockchain explorer:")
        print(f"   TX:       https://blockchair.com/bitcoin-cash/transaction/{result['mint_txid']}")
        print(f"   Category: https://www.tokenexplorer.cash/token/{result['category_id']}")
        print()
        print("✅ NFT registry updated!")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR DURING MINTING")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
