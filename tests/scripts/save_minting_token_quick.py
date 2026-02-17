"""
Save Platform Minting Token Configuration (Quick Version)

INSTRUCTIONS:
1. Replace YOUR_TRANSACTION_ID_HERE below with your actual Transaction ID
2. Run: python save_minting_token_quick.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# ============================================================================
# PASTE YOUR IDs HERE:
# ============================================================================
TRANSACTION_ID = "YOUR_TRANSACTION_ID_HERE"
CATEGORY_ID = "YOUR_CATEGORY_ID_HERE"
# ============================================================================

def main():
    print("=" * 70)
    print("💾 SAVING PLATFORM MINTING TOKEN CONFIGURATION")
    print("=" * 70)
    print()

    # Get IDs
    txid = TRANSACTION_ID.strip()
    category_id = CATEGORY_ID.strip()

    if len(txid) != 64:
        print(f"⚠️  Warning: Transaction ID should be 64 characters (got {len(txid)})")

    if len(category_id) != 64:
        print(f"⚠️  Warning: Category ID should be 64 characters (got {len(category_id)})")

    print(f"Transaction ID: {txid}")
    print(f"Category ID:    {category_id}")
    print()

    # Create configuration
    config = {
        "category_id": category_id,  # Use the actual category ID from Electron Cash
        "genesis_txid": txid,
        "commitment": "e6b252264c1dd45553d9b05d1e37c26b55d9cca3c41c0ca0bb4ae54ed1995827",
        "network": "mainnet",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Save to file
    config_dir = Path("data/platform")
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "minting_token.json"

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

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
    print(f"   TX:       https://blockchair.com/bitcoin-cash/transaction/{txid}")
    print(f"   Category: https://www.tokenexplorer.cash/token/{category_id}")
    print()
    print("=" * 70)
    print("🎉 PLATFORM IS READY TO MINT QUBE NFTs!")
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
