#!/usr/bin/env python3
"""
Quick diagnostic script to check minting status directly from the API.
Usage: python tests/scripts/check_minting_status.py <registration_id>
"""

import asyncio
import sys
import json

# Add project root to path
sys.path.insert(0, '.')

async def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/scripts/check_minting_status.py <registration_id>")
        print("\nExample: python tests/scripts/check_minting_status.py reg_625c5a5e5de213583eb1a15e")
        sys.exit(1)

    registration_id = sys.argv[1]

    from blockchain.minting_api import MintingAPIClient

    print(f"Checking status for: {registration_id}")
    print("-" * 50)

    async with MintingAPIClient() as api_client:
        status = await api_client.get_status(registration_id)
        print(json.dumps(status, indent=2))

        if status.get("status") == "complete":
            print("\n✅ NFT minting is COMPLETE!")
            print(f"   Category ID: {status.get('category_id', 'N/A')}")
            print(f"   Mint TX: {status.get('mint_txid', 'N/A')}")
            print(f"   BCMR CID: {status.get('bcmr_ipfs_cid', 'N/A')}")
        elif status.get("status") == "paid":
            print("\n⏳ Payment received, minting in progress...")
        elif status.get("status") == "minting":
            print("\n⏳ NFT minting in progress...")
        elif status.get("status") == "failed":
            print(f"\n❌ Minting FAILED: {status.get('error_message', 'Unknown error')}")
        else:
            print(f"\n⏸️  Status: {status.get('status', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
