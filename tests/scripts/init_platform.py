"""
Initialize Qubes Platform Minting Token

Simple wrapper script to initialize the platform.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from blockchain.platform_init import PlatformInitializer, check_minting_token_exists

def main():
    print("=" * 70)
    print("🚀 QUBES PLATFORM INITIALIZATION")
    print("=" * 70)
    print()
    print("This will create the master minting token for the Qubes platform.")
    print("This token can mint unlimited Qube NFTs.")
    print()
    print("You only need to run this ONCE per network (mainnet/chipnet).")
    print("=" * 70)
    print()

    # Check if already initialized
    if check_minting_token_exists():
        print("⚠️  Platform minting token already exists!")
        print()
        response = input("Re-initialize? This will overwrite existing config (yes/no): ").strip().lower()

        if response not in ['yes', 'y']:
            print("\n❌ Cancelled. Existing configuration preserved.")
            return

        print("\n🔄 Proceeding with re-initialization...")
        import shutil
        from pathlib import Path
        config_path = Path("data/platform/minting_token.json")
        if config_path.exists():
            backup = config_path.with_suffix('.json.backup')
            shutil.copy(config_path, backup)
            print(f"   Backup saved to: {backup}")
            config_path.unlink()

    # Get network from .env or use mainnet
    network = os.getenv("BCH_NETWORK", "mainnet").strip()

    if network not in ["mainnet", "chipnet"]:
        print(f"❌ Invalid network in .env: {network}")
        print("   BCH_NETWORK must be 'mainnet' or 'chipnet'")
        return

    print(f"📍 Network: {network}")
    print()

    # Check for minting key
    minting_key = os.getenv("PLATFORM_BCH_MINTING_KEY")

    if not minting_key:
        print("❌ PLATFORM_BCH_MINTING_KEY not found in .env file")
        print()
        print("Please add your BCH private key (WIF format) to .env:")
        print("  PLATFORM_BCH_MINTING_KEY=your_private_key_here")
        return

    print(f"✅ Found minting key: {minting_key[:10]}...{minting_key[-10:]}")
    print()

    # Verify key format
    try:
        from bitcash import Key

        key = Key(minting_key)
        address = key.address

        print(f"📬 Platform address: {address}")
        print()

        # Check balance
        print("🔍 Checking balance...")
        try:
            balance_satoshis = key.get_balance()

            # Handle string or int balance
            if isinstance(balance_satoshis, str):
                balance_satoshis = int(balance_satoshis)

            balance_bch = balance_satoshis / 100000000

            print(f"💰 Current balance: {balance_bch} BCH ({balance_satoshis:,} satoshis)")
            print()
        except Exception as e:
            print(f"⚠️  Could not check balance: {e}")
            print("   Proceeding anyway...")
            balance_satoshis = 0
            print()

        if balance_satoshis < 100000:  # Less than 0.001 BCH
            print("⚠️  WARNING: Low balance!")
            print(f"   You need at least 0.001 BCH to create the minting token.")
            print()

            if network == "chipnet":
                print("💡 Get free testnet BCH from:")
                print("   https://tbch.googol.cash/")
            else:
                print("💡 Send some BCH to your platform address:")
                print(f"   {address}")

            print()
            response = input("Continue anyway? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("\n❌ Cancelled. Fund your address and try again.")
                return

    except Exception as e:
        print(f"❌ Invalid private key: {e}")
        return

    print("=" * 70)
    print("⚠️  READY TO CREATE MINTING TOKEN")
    print("=" * 70)
    print()
    print("This will:")
    print("  1. Create a genesis transaction on Bitcoin Cash")
    print("  2. Mint a token with unlimited minting capability")
    print("  3. Save the configuration to data/platform/minting_token.json")
    print()
    print("Transaction fee: ~0.0001 BCH")
    print()

    response = input("Proceed? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Cancelled.")
        return

    print()
    print("=" * 70)
    print("🔨 CREATING MINTING TOKEN...")
    print("=" * 70)
    print()

    try:
        config = PlatformInitializer.initialize_minting_token(network=network)

        print()
        print("=" * 70)
        print("✅ SUCCESS! PLATFORM IS READY TO MINT QUBE NFTs")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Test the minting workflow:")
        print("     python test_nft_minting.py")
        print()
        print("  2. Mint your first Qube NFT!")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR DURING INITIALIZATION")
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
        print("\n\n❌ Interrupted. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
