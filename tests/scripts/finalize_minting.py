#!/usr/bin/env python3
"""
Manually finalize a qube after minting is complete on the server.
Usage: python tests/scripts/finalize_minting.py <registration_id> <password>
"""

import asyncio
import sys
import json
import os

# Add project root to path
sys.path.insert(0, '.')

async def main():
    if len(sys.argv) < 3:
        print("Usage: python tests/scripts/finalize_minting.py <registration_id> <password>")
        print("\nExample: python tests/scripts/finalize_minting.py reg_625c5a5e5de213583eb1a15e mypassword")
        sys.exit(1)

    registration_id = sys.argv[1]
    password = sys.argv[2]

    from blockchain.minting_api import MintingAPIClient
    from orchestrator.user_orchestrator import UserOrchestrator
    from pathlib import Path

    # Get user ID from environment or default
    user_id = os.getenv("QUBES_USER_ID", "default_user")
    data_dir = Path(os.getenv("QUBES_DATA_DIR", "data")) / "users" / user_id

    print(f"Registration ID: {registration_id}")
    print(f"User ID: {user_id}")
    print(f"Data dir: {data_dir}")
    print("-" * 50)

    # First, check status from API
    print("\n1. Checking status from minting API...")
    async with MintingAPIClient() as api_client:
        status = await api_client.get_status(registration_id)

    if status.get("status") != "complete":
        print(f"❌ Minting is not complete yet. Status: {status.get('status')}")
        sys.exit(1)

    print("✅ Minting is complete on server")
    print(f"   Category ID: {status.get('category_id')}")
    print(f"   Mint TX: {status.get('mint_txid')}")

    qube_id = status.get("qube_id")
    category_id = status.get("category_id")
    mint_txid = status.get("mint_txid")
    bcmr_ipfs_cid = status.get("bcmr_ipfs_cid")
    avatar_ipfs_cid = status.get("avatar_ipfs_cid")
    commitment = status.get("commitment")
    recipient_address = status.get("recipient_address")

    # Initialize orchestrator
    print("\n2. Initializing orchestrator...")
    orchestrator = UserOrchestrator(user_id=user_id, data_dir=data_dir.parent.parent)
    orchestrator.set_master_key(password)

    # Load qube from disk
    print("\n3. Loading qube from disk...")
    await orchestrator.load_qubes()

    qube = orchestrator.qubes.get(qube_id)
    if not qube:
        print(f"❌ Qube {qube_id} not found in memory")
        # List available qubes
        print(f"   Available qubes: {list(orchestrator.qubes.keys())}")
        sys.exit(1)

    print(f"✅ Found qube: {qube.name} ({qube.qube_id})")
    print(f"   Current NFT status: {qube.genesis_block.nft_category_id}")

    if qube.genesis_block.nft_category_id != "pending_minting":
        print("ℹ️  Qube is already finalized!")
        sys.exit(0)

    # Build mint info
    mint_info = {
        "category_id": category_id,
        "mint_txid": mint_txid,
        "bcmr_ipfs_cid": bcmr_ipfs_cid,
        "avatar_ipfs_cid": avatar_ipfs_cid,
        "recipient_address": recipient_address,
        "commitment": commitment,
    }

    print("\n4. Finalizing qube with NFT data...")
    print(f"   Category ID: {category_id[:16]}...")
    print(f"   Mint TX: {mint_txid[:16]}...")

    await orchestrator._finalize_minted_qube(registration_id, mint_info)

    print("\n✅ Qube finalized successfully!")
    print(f"   NFT Category: {qube.genesis_block.nft_category_id[:16]}...")

    # Verify
    print("\n5. Verifying finalization...")
    qube_dir = data_dir / "qubes" / f"{qube.name}_{qube.qube_id}"
    nft_metadata_path = qube_dir / "chain" / "nft_metadata.json"

    if nft_metadata_path.exists():
        with open(nft_metadata_path) as f:
            nft_data = json.load(f)
        print("✅ nft_metadata.json created:")
        print(json.dumps(nft_data, indent=2))
    else:
        print("⚠️  nft_metadata.json not found (might be in different location)")

    print("\n🎉 Done! You can now close the minting dialog and refresh the qube list.")

if __name__ == "__main__":
    asyncio.run(main())
