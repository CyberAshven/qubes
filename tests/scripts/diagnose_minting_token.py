"""
Diagnose Platform Minting Token Setup

Checks if the minting token is accessible to the platform.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    print("=" * 70)
    print("🔍 DIAGNOSING PLATFORM MINTING TOKEN SETUP")
    print("=" * 70)
    print()

    # 1. Check config file exists
    config_path = Path("data/platform/minting_token.json")
    if not config_path.exists():
        print("❌ Config file not found: data/platform/minting_token.json")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    print("✅ Minting token configuration loaded")
    print(f"   Category ID: {config['category_id']}")
    print(f"   Genesis TX:  {config['genesis_txid']}")
    print(f"   Network:     {config['network']}")
    print()

    # 2. Check platform key
    platform_wif = os.getenv("PLATFORM_BCH_MINTING_KEY")
    if not platform_wif:
        print("❌ PLATFORM_BCH_MINTING_KEY not set in .env")
        return

    print("✅ Platform minting key found in .env")
    print()

    # 3. Check key and addresses
    try:
        from bitcash import Key

        key = Key(platform_wif)

        print("📬 Platform Addresses:")
        print(f"   Legacy:     {key.address}")
        print(f"   CashToken:  {key.cashtoken_address}")
        print()

        # 4. Check balance
        print("💰 Checking balance...")
        try:
            balance = key.get_balance()
            if isinstance(balance, str):
                balance = int(balance)
            balance_bch = balance / 100000000

            print(f"   Balance: {balance_bch:.8f} BCH ({balance:,} satoshis)")
            print()

        except Exception as e:
            print(f"   ⚠️  Could not fetch balance: {e}")
            print()

        # 5. Check UTXOs
        print("🔍 Checking UTXOs...")
        try:
            unspents = key.get_unspents()
            print(f"   Total UTXOs: {len(unspents)}")

            if len(unspents) == 0:
                print()
                print("⚠️  WARNING: No UTXOs found!")
                print("   This means:")
                print("   1. Either the wallet has no BCH, OR")
                print("   2. The minting token was sent to a DIFFERENT address")
                print()
                print("🔍 TROUBLESHOOTING:")
                print()
                print("   Check in Electron Cash:")
                print(f"   1. What address holds the minting token?")
                print(f"   2. Does it match the platform address?")
                print(f"      Platform (legacy):    {key.address}")
                print(f"      Platform (CashToken): {key.cashtoken_address}")
                print()
                print("   If the addresses don't match:")
                print("   - Send the minting token to the platform address")
                print("   - OR update PLATFORM_BCH_MINTING_KEY to match the token holder")
                print()
                return

            print()
            print("📦 UTXO Details:")
            for i, utxo in enumerate(unspents, 1):
                print(f"\n   UTXO #{i}:")
                print(f"     Amount:   {utxo.amount} satoshis")
                print(f"     TX:       {utxo.txid[:16]}...")

                # Check for token attributes
                if hasattr(utxo, 'token_category'):
                    print(f"     ✅ Has token!")
                    print(f"     Category: {utxo.token_category}")
                    if hasattr(utxo, 'nft_capability'):
                        print(f"     Capability: {utxo.nft_capability}")
                    if hasattr(utxo, 'nft_commitment'):
                        print(f"     Commitment: {utxo.nft_commitment[:16]}...")

                    # Check if this is our minting token
                    if utxo.token_category == config['category_id']:
                        if hasattr(utxo, 'nft_capability') and utxo.nft_capability == 'minting':
                            print()
                            print("     🎉 THIS IS THE PLATFORM MINTING TOKEN!")
                        else:
                            print("     ⚠️  Category matches but not a minting token")
                    else:
                        print(f"     ⚠️  Different category (not our minting token)")
                else:
                    print(f"     Regular BCH (no token)")

            print()

        except Exception as e:
            print(f"   ⚠️  Error fetching UTXOs: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error loading private key: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)
    print("🏁 DIAGNOSIS COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
