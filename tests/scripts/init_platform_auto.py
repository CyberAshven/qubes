"""
Initialize Qubes Platform Minting Token (Auto-approve)

Non-interactive version for automated initialization.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Import after loading env
from blockchain.platform_init import PlatformInitializer, check_minting_token_exists

def main():
    print("=" * 70)
    print("🚀 QUBES PLATFORM INITIALIZATION (AUTO)")
    print("=" * 70)
    print()

    # Check if already initialized
    if check_minting_token_exists():
        print("⚠️  Platform minting token already exists!")
        print("   Located at: data/platform/minting_token.json")
        print()
        print("   To re-initialize, delete that file first.")
        return

    # Get network from .env
    network = os.getenv("BCH_NETWORK", "mainnet").strip()

    if network not in ["mainnet", "chipnet"]:
        print(f"❌ Invalid network in .env: {network}")
        return

    print(f"📍 Network: {network}")

    # Check for minting key
    minting_key = os.getenv("PLATFORM_BCH_MINTING_KEY")

    if not minting_key:
        print("❌ PLATFORM_BCH_MINTING_KEY not found in .env")
        return

    print(f"✅ Minting key: {minting_key[:10]}...{minting_key[-10:]}")

    # Verify key and check balance
    try:
        from bitcash import Key

        key = Key(minting_key)
        address = key.address

        print(f"📬 Address: {address}")

        # Check balance
        try:
            balance_satoshis = key.get_balance()
            if isinstance(balance_satoshis, str):
                balance_satoshis = int(balance_satoshis)

            balance_bch = balance_satoshis / 100000000
            print(f"💰 Balance: {balance_bch} BCH ({balance_satoshis:,} satoshis)")

            if balance_satoshis < 100000:
                print()
                print("⚠️  WARNING: Balance is low!")
                print(f"   Recommended: At least 0.001 BCH for minting token creation")

        except Exception as e:
            print(f"⚠️  Could not verify balance: {e}")

    except Exception as e:
        print(f"❌ Invalid private key: {e}")
        return

    print()
    print("=" * 70)
    print("🔨 CREATING PLATFORM MINTING TOKEN...")
    print("=" * 70)
    print()

    try:
        config = PlatformInitializer.initialize_minting_token(network=network)

        print()
        print("=" * 70)
        print("✅ SUCCESS! PLATFORM INITIALIZED")
        print("=" * 70)
        print()
        print(f"Category ID: {config['category_id']}")
        print(f"Genesis TX:  {config['genesis_txid']}")
        print()
        print(f"🌐 View transaction:")
        print(f"   https://blockchair.com/bitcoin-cash/transaction/{config['genesis_txid']}")
        print()
        print("✅ Platform is ready to mint Qube NFTs!")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
