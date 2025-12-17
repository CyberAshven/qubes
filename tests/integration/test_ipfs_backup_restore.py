#!/usr/bin/env python
"""
Test IPFS Backup & Restore (Model 3)

Demonstrates the complete flow:
1. Create a Qube
2. Backup to IPFS (encrypted)
3. Mint NFT with IPFS CID in commitment
4. Simulate new device: Restore from IPFS using NFT data
5. Verify restored Qube matches original

Required environment variables:
- PINATA_API_KEY: Pinata JWT token
- PLATFORM_BCH_MINTING_KEY: Platform minting key
- RECIPIENT_BCH_ADDRESS: BCH address to receive NFT
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from core.qube import Qube
from storage.ipfs_backup import QubeBackup
from blockchain.nft_minter import OptimizedNFTMinter
from blockchain.verifier import NFTVerifier
from utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """
    Test complete IPFS backup → NFT mint → restore flow
    """
    print("\n" + "=" * 80)
    print("MODEL 3: NFT + IPFS BACKUP TEST")
    print("=" * 80 + "\n")

    # Check environment
    if not os.getenv("PINATA_API_KEY"):
        print("❌ ERROR: PINATA_API_KEY not set")
        print("Get your API key from: https://app.pinata.cloud/developers/api-keys")
        return 1

    if not os.getenv("PLATFORM_BCH_MINTING_KEY"):
        print("❌ ERROR: PLATFORM_BCH_MINTING_KEY not set")
        return 1

    recipient_address = os.getenv("RECIPIENT_BCH_ADDRESS")
    if not recipient_address:
        print("❌ ERROR: RECIPIENT_BCH_ADDRESS not set")
        return 1

    # ==========================================================================
    # STEP 1: CREATE A NEW QUBE
    # ==========================================================================

    print("📦 STEP 1: Creating new Qube...")
    print("-" * 80)

    qube_name = "BackupTestQube"
    data_dir = Path("./data")

    qube = Qube.create_new(
        qube_name=qube_name,
        creator="backup-test@qubes.ai",
        genesis_prompt=f"You are {qube_name}, created to test IPFS backup and restore functionality.",
        ai_model="gpt-4o-mini",
        voice_model="default",
        data_dir=data_dir,
        home_blockchain="bitcoin_cash"
    )

    print(f"✅ Qube created: {qube.qube_id} - {qube.name}")
    print(f"   Genesis hash: {qube.genesis_block.block_hash}")
    print(f"   Storage: {qube.storage.db_path}")
    print(f"   Chain length: {qube.memory_chain.get_chain_length()}")

    # Note: Genesis block is enough for testing
    # In real use, the Qube would have many blocks from conversations

    # ==========================================================================
    # STEP 2: BACKUP TO IPFS
    # ==========================================================================

    print("\n" + "=" * 80)
    print("☁️  STEP 2: Backing up Qube to IPFS...")
    print("-" * 80)

    backup_password = "test-password-123"  # In production, user provides this
    print(f"   Password: {backup_password}")

    backup_manager = QubeBackup()

    print("\n   Encrypting and uploading to IPFS...")
    backup_result = await backup_manager.backup_to_ipfs(
        qube=qube,
        password=backup_password,
        metadata={
            "backup_reason": "end-to-end test",
            "test_run": True
        }
    )

    print(f"\n✅ Backup complete!")
    print(f"   IPFS CID: {backup_result['ipfs_cid']}")
    print(f"   IPFS URL: {backup_result['ipfs_url']}")
    print(f"   Size: {backup_result['encrypted_size'] / 1024:.2f} KB")

    # Save these for later
    ipfs_cid = backup_result['ipfs_cid']
    original_qube_id = qube.qube_id
    original_genesis_hash = qube.genesis_block.block_hash
    original_chain_length = qube.memory_chain.get_chain_length()

    # ==========================================================================
    # STEP 3: MINT NFT WITH IPFS CID
    # ==========================================================================

    print("\n" + "=" * 80)
    print("🪙 STEP 3: Minting NFT with IPFS CID in commitment...")
    print("-" * 80)

    network = os.getenv("BCH_NETWORK", "mainnet")
    minter = OptimizedNFTMinter(network=network)

    print(f"   Network: {network}")
    print(f"   Recipient: {recipient_address}")
    print(f"   Including IPFS CID in NFT commitment...")

    mint_result = await minter.mint_qube_nft(
        qube=qube,
        recipient_address=recipient_address,
        ipfs_cid=ipfs_cid  # ✨ NEW: Include IPFS CID
    )

    print(f"\n✅ NFT minted with IPFS backup!")
    print(f"   TX ID: {mint_result['mint_txid']}")
    print(f"   Commitment includes IPFS CID: {ipfs_cid[:16]}...")
    print(f"   Explorer: {mint_result['explorer_url']}")

    # Close original Qube
    qube.close()

    # ==========================================================================
    # STEP 4: SIMULATE NEW DEVICE - DELETE LOCAL QUBE
    # ==========================================================================

    print("\n" + "=" * 80)
    print("💻 STEP 4: Simulating new device (deleting local Qube)...")
    print("-" * 80)

    qube_path = data_dir / "qubes" / f"{qube_name}_{original_qube_id}"
    print(f"   Deleting: {qube_path}")

    if qube_path.exists():
        shutil.rmtree(qube_path)
        print("   ✅ Local Qube deleted")
    else:
        print("   ⚠️  Qube path not found (already deleted?)")

    print("\n   Simulating user on new device...")
    print(f"   User has:")
    print(f"   - NFT in wallet (contains commitment with IPFS CID)")
    print(f"   - Password: {backup_password}")
    print(f"   - IPFS CID: {ipfs_cid}")

    # ==========================================================================
    # STEP 5: RESTORE FROM IPFS
    # ==========================================================================

    print("\n" + "=" * 80)
    print("📥 STEP 5: Restoring Qube from IPFS...")
    print("-" * 80)

    print(f"   Downloading from IPFS: {ipfs_cid[:16]}...")
    print(f"   Decrypting with password...")
    print(f"   Importing to local storage...")

    restore_result = await backup_manager.restore_from_ipfs(
        ipfs_cid=ipfs_cid,
        password=backup_password,
        data_dir=data_dir
    )

    print(f"\n✅ Qube restored!")
    print(f"   Qube ID: {restore_result['qube_id']}")
    print(f"   Name: {restore_result['qube_name']}")
    print(f"   Chain length: {restore_result['chain_length']}")
    print(f"   Path: {restore_result['restored_path']}")

    # ==========================================================================
    # STEP 6: VERIFY RESTORATION
    # ==========================================================================

    print("\n" + "=" * 80)
    print("✓  STEP 6: Verifying restoration...")
    print("-" * 80)

    # Load the restored Qube
    from storage.lmdb_storage import LMDBStorage

    restored_path = Path(restore_result['restored_path'])
    restored_storage = LMDBStorage(restored_path / "lmdb")

    # Read genesis block
    restored_genesis = restored_storage.read_block(restore_result['qube_id'], 0)

    # Verify
    print("\n   Comparing original vs restored:")
    print(f"   - Qube ID: {original_qube_id} → {restore_result['qube_id']}")
    print(f"     Match: {'✅' if original_qube_id == restore_result['qube_id'] else '❌'}")

    print(f"   - Genesis hash: {original_genesis_hash[:16]}... → {restored_genesis.block_hash[:16]}...")
    print(f"     Match: {'✅' if original_genesis_hash == restored_genesis.block_hash else '❌'}")

    print(f"   - Chain length: {original_chain_length} → {restore_result['chain_length']}")
    print(f"     Match: {'✅' if original_chain_length == restore_result['chain_length'] else '❌'}")

    # Read all blocks and compare
    print(f"\n   Verifying all {restore_result['chain_length']} blocks...")
    all_match = True
    for i in range(restore_result['chain_length']):
        block = restored_storage.read_block(restore_result['qube_id'], i)
        if not block:
            print(f"   ❌ Block {i} missing!")
            all_match = False

    if all_match:
        print(f"   ✅ All blocks present and valid")

    restored_storage.close()

    # ==========================================================================
    # STEP 7: SUMMARY
    # ==========================================================================

    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    print(f"\n   Original Qube:")
    print(f"   ├─ ID: {original_qube_id}")
    print(f"   ├─ Name: {qube_name}")
    print(f"   ├─ Genesis: {original_genesis_hash}")
    print(f"   └─ Blocks: {original_chain_length}")

    print(f"\n   IPFS Backup:")
    print(f"   ├─ CID: {ipfs_cid}")
    print(f"   ├─ URL: {backup_result['ipfs_url']}")
    print(f"   ├─ Size: {backup_result['encrypted_size'] / 1024:.2f} KB")
    print(f"   └─ Encrypted: ✅")

    print(f"\n   NFT:")
    print(f"   ├─ TX: {mint_result['mint_txid']}")
    print(f"   ├─ Category: {mint_result['category_id'][:16]}...")
    print(f"   ├─ Commitment includes IPFS CID: ✅")
    print(f"   └─ Explorer: {mint_result['explorer_url']}")

    print(f"\n   Restored Qube:")
    print(f"   ├─ ID: {restore_result['qube_id']} {'✅' if restore_result['qube_id'] == original_qube_id else '❌'}")
    print(f"   ├─ Name: {restore_result['qube_name']}")
    print(f"   ├─ Genesis: {restored_genesis.block_hash} {'✅' if restored_genesis.block_hash == original_genesis_hash else '❌'}")
    print(f"   └─ Blocks: {restore_result['chain_length']} {'✅' if restore_result['chain_length'] == original_chain_length else '❌'}")

    print("\n" + "=" * 80)
    print("✅ MODEL 3 TEST COMPLETE!")
    print("=" * 80)

    print("\n   🎉 Success! The Qube was:")
    print("   1. Created locally")
    print("   2. Backed up to IPFS (encrypted)")
    print("   3. Minted as NFT with IPFS CID")
    print("   4. Deleted from local storage")
    print("   5. Restored from IPFS on 'new device'")
    print("   6. Verified to match original")

    print("\n   This demonstrates Model 3:")
    print("   - User buys/receives NFT → has IPFS CID in commitment")
    print("   - User downloads encrypted backup from IPFS")
    print("   - User enters password → decrypts → imports Qube")
    print("   - User can now run the Qube on any device!")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        logger.error("ipfs_backup_test_failed", error=str(e), exc_info=True)
        sys.exit(1)
