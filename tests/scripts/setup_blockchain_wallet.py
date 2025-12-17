"""
Blockchain Wallet Setup Helper

Helps you configure your BCH wallet for Qubes NFT minting.
"""

import os
from pathlib import Path

def main():
    print("=" * 70)
    print("🔐 QUBES BLOCKCHAIN WALLET SETUP")
    print("=" * 70)
    print()
    print("This script will help you configure your Bitcoin Cash wallet")
    print("for minting Qube NFTs.")
    print()
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("   - Your private key controls your BCH funds")
    print("   - Never share your private key with anyone")
    print("   - For testing, use chipnet (testnet) instead of mainnet")
    print()

    # Check current configuration
    env_file = Path(".env")

    print("Current configuration:")
    print()

    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()

            if "PLATFORM_BCH_MINTING_KEY=" in content and not content.split("PLATFORM_BCH_MINTING_KEY=")[1].startswith("#"):
                # Key is configured
                key_line = [l for l in content.split('\n') if l.startswith('PLATFORM_BCH_MINTING_KEY=')][0]
                key_value = key_line.split('=')[1].strip()

                if key_value and key_value != "...":
                    print(f"✅ BCH Private Key: Configured ({key_value[:10]}...)")
                else:
                    print("❌ BCH Private Key: Not configured")
            else:
                print("❌ BCH Private Key: Not configured (commented out)")

            if "BCH_NETWORK=" in content and not content.split("BCH_NETWORK=")[1].startswith("#"):
                network_line = [l for l in content.split('\n') if l.startswith('BCH_NETWORK=')][0]
                network = network_line.split('=')[1].strip().split()[0]
                print(f"✅ Network: {network}")
            else:
                print("❌ Network: Not configured (commented out)")
    else:
        print("❌ .env file not found")
        return

    print()
    print("-" * 70)
    print()
    print("What would you like to do?")
    print()
    print("1. Generate a NEW chipnet (testnet) wallet for safe testing")
    print("2. Use my existing Electron wallet (MAINNET - real BCH)")
    print("3. Show me how to get testnet BCH for testing")
    print("4. Exit")
    print()

    choice = input("Enter your choice (1-4): ").strip()

    if choice == "1":
        generate_chipnet_wallet()
    elif choice == "2":
        configure_mainnet_wallet()
    elif choice == "3":
        show_testnet_faucet_info()
    elif choice == "4":
        print("\n👋 Exiting...")
    else:
        print("\n❌ Invalid choice")

def generate_chipnet_wallet():
    """Generate a new chipnet (testnet) wallet"""
    print()
    print("=" * 70)
    print("🆕 GENERATING CHIPNET TEST WALLET")
    print("=" * 70)
    print()

    try:
        from bitcash import Key

        # Generate new key
        key = Key()

        print("✅ New chipnet wallet generated!")
        print()
        print("📋 SAVE THESE CREDENTIALS SECURELY:")
        print()
        print(f"Private Key (WIF):  {key.to_wif()}")
        print(f"Address:            {key.address}")
        print()
        print("⚠️  This is a NEW wallet with 0 BCH. You'll need testnet BCH to mint NFTs.")
        print("   Use option 3 to get free testnet BCH from a faucet.")
        print()

        # Ask if they want to save to .env
        save = input("Save this key to .env file? (yes/no): ").strip().lower()

        if save in ['yes', 'y']:
            update_env_file(key.to_wif(), "chipnet")
            print()
            print("✅ Configuration saved to .env")
            print()
            print("Next steps:")
            print("1. Get testnet BCH from faucet (option 3)")
            print("2. Initialize platform: python -m blockchain.platform_init --network chipnet")
            print("3. Mint your first Qube NFT!")

    except ImportError:
        print("❌ bitcash library not installed")
        print("   Install it: pip install bitcash")

def configure_mainnet_wallet():
    """Configure existing mainnet wallet"""
    print()
    print("=" * 70)
    print("⚠️  MAINNET WALLET CONFIGURATION")
    print("=" * 70)
    print()
    print("🚨 WARNING: You are about to configure a MAINNET wallet")
    print("   - This wallet controls REAL Bitcoin Cash")
    print("   - Minting NFTs will cost real BCH (transaction fees)")
    print("   - Make sure you understand the risks")
    print()
    print("For testing, we STRONGLY recommend using chipnet (option 1) instead.")
    print()

    confirm = input("Are you sure you want to use mainnet? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("\n👍 Good choice! Returning to menu...")
        return

    print()
    print("Your Electron wallet private key should be in WIF format.")
    print("It starts with 'K', 'L', or '5' (compressed/uncompressed).")
    print()
    print("Where to find it in Electron Cash:")
    print("1. Wallet menu → Private keys → Export")
    print("2. Or: Right-click address → Private key → Copy")
    print()

    wif_key = input("Enter your WIF private key: ").strip()

    if not wif_key:
        print("\n❌ No key entered")
        return

    # Basic validation
    if not (wif_key.startswith('K') or wif_key.startswith('L') or wif_key.startswith('5')):
        print("\n⚠️  Warning: This doesn't look like a valid WIF key")
        print("   WIF keys start with K, L, or 5")

        proceed = input("Continue anyway? (yes/no): ").strip().lower()
        if proceed not in ['yes', 'y']:
            return

    update_env_file(wif_key, "mainnet")

    print()
    print("✅ Mainnet wallet configured!")
    print()
    print("⚠️  SECURITY REMINDER:")
    print("   - Never commit .env to git")
    print("   - Never share your private key")
    print("   - Consider using a dedicated wallet for minting")
    print()
    print("Next steps:")
    print("1. Initialize platform: python -m blockchain.platform_init --network mainnet")
    print("2. Mint Qube NFTs on mainnet (costs real BCH)")

def show_testnet_faucet_info():
    """Show info about getting testnet BCH"""
    print()
    print("=" * 70)
    print("🚰 GETTING TESTNET BCH (FREE)")
    print("=" * 70)
    print()
    print("Testnet BCH is free and used for testing. Get it from faucets:")
    print()
    print("📍 Chipnet (BCH Testnet4) Faucets:")
    print()
    print("1. Chaingraph Faucet:")
    print("   https://faucet.fullstack.cash/")
    print("   → Enter your chipnet address")
    print("   → Receive 0.01 BCH instantly")
    print()
    print("2. Bitcoin.com Testnet Faucet:")
    print("   https://faucet.bitcoin.com/")
    print("   → Switch to 'Testnet4'")
    print("   → Enter address, solve captcha")
    print()
    print("3. Ask in Telegram:")
    print("   t.me/bchchannel")
    print("   → Post your chipnet address")
    print("   → Community members often help")
    print()
    print("💡 Tips:")
    print("   - 0.01 tBCH is enough for ~100 NFT mints")
    print("   - Testnet transactions work exactly like mainnet")
    print("   - Perfect for testing before going to production")
    print()
    input("Press Enter to continue...")

def update_env_file(wif_key: str, network: str):
    """Update .env file with wallet configuration"""
    env_file = Path(".env")

    if not env_file.exists():
        print("❌ .env file not found")
        return

    with open(env_file, 'r') as f:
        lines = f.readlines()

    # Find and update the BCH configuration section
    updated = False
    network_updated = False

    for i, line in enumerate(lines):
        if line.strip().startswith("# PLATFORM_BCH_MINTING_KEY=") or line.strip().startswith("PLATFORM_BCH_MINTING_KEY="):
            lines[i] = f"PLATFORM_BCH_MINTING_KEY={wif_key}\n"
            updated = True
        elif line.strip().startswith("# BCH_NETWORK=") or line.strip().startswith("BCH_NETWORK="):
            lines[i] = f"BCH_NETWORK={network}\n"
            network_updated = True

    if updated and network_updated:
        with open(env_file, 'w') as f:
            f.writelines(lines)
    else:
        print("⚠️  Warning: Could not find configuration lines in .env")
        print("   Please manually add:")
        print(f"   PLATFORM_BCH_MINTING_KEY={wif_key}")
        print(f"   BCH_NETWORK={network}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
