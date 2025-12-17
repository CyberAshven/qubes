"""
Save Platform Minting Token Configuration

Run this after creating the minting token in Electron Cash.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

def main():
    print("=" * 70)
    print("💾 SAVE PLATFORM MINTING TOKEN CONFIGURATION")
    print("=" * 70)
    print()
    print("Enter the details from Electron Cash:")
    print()

    # Get transaction/category ID
    txid = input("Transaction ID (also the Category ID): ").strip()

    if not txid:
        print("❌ Transaction ID is required!")
        return

    # Validate it looks like a txid (64 hex chars)
    if len(txid) != 64:
        print(f"⚠️  Warning: Transaction ID should be 64 characters (got {len(txid)})")
        print("   Make sure you copied the full transaction ID")
        proceed = input("Continue anyway? (yes/no): ").strip().lower()
        if proceed not in ['yes', 'y']:
            return

    print()
    print(f"✅ Category ID: {txid}")
    print()

    # Optional: Get commitment if they added one
    commitment_input = input("Commitment (hex) - press Enter to skip: ").strip()

    commitment = commitment_input if commitment_input else "e6b252264c1dd45553d9b05d1e37c26b55d9cca3c41c0ca0bb4ae54ed1995827"

    # Create configuration
    config = {
        "category_id": txid,
        "genesis_txid": txid,
        "commitment": commitment,
        "network": "mainnet",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Save to file
    config_dir = Path("data/platform")
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "minting_token.json"

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print()
    print("=" * 70)
    print("✅ CONFIGURATION SAVED!")
    print("=" * 70)
    print()
    print(f"📁 Location: {config_file}")
    print()
    print("📋 Configuration:")
    print(json.dumps(config, indent=2))
    print()
    print("🌐 View your transaction:")
    print(f"   https://blockchair.com/bitcoin-cash/transaction/{txid}")
    print()
    print("=" * 70)
    print("✅ PLATFORM IS READY TO MINT QUBE NFTs!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. python test_nft_minting.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
