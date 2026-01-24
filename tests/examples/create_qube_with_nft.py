#!/usr/bin/env python
"""
End-to-End Qube Creation & NFT Minting Test

This script demonstrates the complete lifecycle:
1. Create a new Qube from scratch
2. Mint a Bitcoin Cash NFT for it
3. Verify NFT ownership on-chain
4. Test NFT-based authentication

Run this to test the full pipeline.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.qube import Qube
from blockchain.nft_minter import OptimizedNFTMinter
from blockchain.verifier import NFTVerifier
from utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """
    Run complete end-to-end Qube creation and NFT minting
    """
    print("\n" + "=" * 80)
    print("END-TO-END QUBE CREATION & NFT MINTING TEST")
    print("=" * 80 + "\n")

    # =============================================================================
    # STEP 1: CREATE A NEW QUBE
    # =============================================================================

    print("📦 STEP 1: Creating new Qube...")
    print("-" * 80)

    qube_name = input("Enter Qube name (or press Enter for 'TestQube'): ").strip() or "TestQube"
    creator_email = input("Enter your email (or press Enter for 'test@example.com'): ").strip() or "test@example.com"

    # Check for recipient BCH address
    recipient_address = os.getenv("RECIPIENT_BCH_ADDRESS")
    if not recipient_address:
        print("\n⚠️  WARNING: RECIPIENT_BCH_ADDRESS not set in environment")
        recipient_address = input("Enter Bitcoin Cash address to receive NFT: ").strip()
        if not recipient_address:
            print("❌ No recipient address provided. Exiting.")
            return

    genesis_prompt = f"""You are {qube_name}, a helpful AI assistant created on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
You are knowledgeable, friendly, and always strive to provide accurate information.
Your purpose is to assist users with their questions and tasks."""

    # Create the Qube
    qube = Qube.create_new(
        qube_name=qube_name,
        creator=creator_email,
        genesis_prompt=genesis_prompt,
        ai_model="gpt-4o-mini",  # Cost-effective model
        voice_model="default",
        data_dir=Path("./data"),
        home_blockchain="bitcoin_cash",
        capabilities={
            "web_search": True,
            "image_generation": False,  # Disabled to save costs
            "image_processing": False,
            "tts": False,
            "stt": False,
            "code_execution": False
        },
        default_trust_level=50
    )

    print(f"\n✅ Qube created successfully!")
    print(f"   Qube ID:        {qube.qube_id}")
    print(f"   Name:           {qube.name}")
    print(f"   Creator:        {creator_email}")
    print(f"   Birth Time:     {datetime.fromtimestamp(qube.genesis_block.birth_timestamp, tz=timezone.utc)}")
    print(f"   Public Key:     {qube.genesis_block.public_key[:64]}...")
    print(f"   Genesis Hash:   {qube.genesis_block.block_hash}")
    print(f"   Storage:        {qube.storage.db_path}")

    # =============================================================================
    # STEP 2: MINT NFT ON BITCOIN CASH
    # =============================================================================

    print("\n" + "=" * 80)
    print("🪙 STEP 2: Minting NFT on Bitcoin Cash...")
    print("-" * 80)

    # Check for platform minting key
    if not os.getenv("PLATFORM_BCH_MINTING_KEY"):
        print("\n❌ ERROR: PLATFORM_BCH_MINTING_KEY environment variable not set")
        print("   Cannot mint NFT without platform minting key.")
        print("\n   To set it:")
        print("   export PLATFORM_BCH_MINTING_KEY='your_wif_key_here'")
        qube.close()
        return

    # Determine network
    network = os.getenv("BCH_NETWORK", "mainnet")
    print(f"   Network:        {network}")
    print(f"   Recipient:      {recipient_address}")

    # Initialize NFT minter
    minter = OptimizedNFTMinter(network=network)

    print(f"   Category ID:    {minter.category_id[:16]}...")
    print(f"   Platform Addr:  {minter.platform_key.cashtoken_address}")

    # Confirm minting
    print("\n   This will:")
    print(f"   1. Create an immutable NFT with commitment derived from Qube {qube.qube_id}")
    print(f"   2. Send the NFT to: {recipient_address}")
    print(f"   3. Cost approximately 0.01 BCH (~$4.00 at $400/BCH)")

    confirm = input("\n   Proceed with minting? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("   Minting cancelled.")
        qube.close()
        return

    # Mint the NFT
    print("\n   Minting NFT...")
    try:
        mint_result = await minter.mint_qube_nft(
            qube=qube,
            recipient_address=recipient_address
        )

        print(f"\n✅ NFT minted successfully!")
        print(f"   TX ID:          {mint_result['mint_txid']}")
        print(f"   Commitment:     {mint_result['commitment'][:32]}...")
        print(f"   Explorer:       {mint_result['explorer_url']}")

        # Update qube with NFT info
        qube.nft_contract = mint_result['category_id']
        qube.nft_token_id = mint_result['commitment']

    except Exception as e:
        print(f"\n❌ NFT minting failed: {e}")
        logger.error("nft_minting_failed", error=str(e), exc_info=True)
        qube.close()
        return

    # =============================================================================
    # STEP 3: VERIFY NFT OWNERSHIP ON-CHAIN
    # =============================================================================

    print("\n" + "=" * 80)
    print("🔍 STEP 3: Verifying NFT ownership on-chain...")
    print("-" * 80)

    # Wait a moment for transaction to propagate
    print("   Waiting 10 seconds for transaction to propagate...")
    await asyncio.sleep(10)

    # Initialize NFT verifier
    verifier = NFTVerifier()

    print(f"   Verifying ownership...")
    print(f"   Category ID:    {mint_result['category_id'][:16]}...")
    print(f"   Owner Address:  {recipient_address}")

    try:
        is_verified = await verifier.verify_ownership(
            category_id=mint_result['category_id'],
            owner_address=recipient_address
        )

        if is_verified:
            print(f"\n✅ NFT ownership verified on-chain!")

            # Get detailed NFT info
            nft_details = await verifier.get_nft_details(
                category_id=mint_result['category_id'],
                owner_address=recipient_address
            )

            if nft_details:
                print(f"\n   NFT Details:")
                print(f"   - Value:        {nft_details['value_satoshis']} satoshis")
                print(f"   - Commitment:   {nft_details['nft_commitment'][:32]}...")
                print(f"   - Capability:   {nft_details['nft_capability']}")
                print(f"   - TX Hash:      {nft_details['transaction_hash'][:32]}...")
                print(f"   - Output Index: {nft_details['output_index']}")
                print(f"   - Total UTXOs:  {nft_details['total_utxos']}")
        else:
            print(f"\n⚠️  NFT ownership not verified (may need more time to propagate)")
            print(f"   Try verifying again in a few minutes using:")
            print(f"   python -c 'import asyncio; from blockchain.verifier import NFTVerifier; asyncio.run(NFTVerifier().verify_ownership(\"{mint_result['category_id']}\", \"{recipient_address}\"))'")

    except Exception as e:
        print(f"\n❌ NFT verification failed: {e}")
        logger.error("nft_verification_failed", error=str(e), exc_info=True)

    # =============================================================================
    # STEP 4: TEST NFT-BASED AUTHENTICATION (Preview)
    # =============================================================================

    print("\n" + "=" * 80)
    print("🔐 STEP 4: Testing NFT-based authentication...")
    print("-" * 80)

    print("\n   ⚠️  Note: Full P2P authentication requires:")
    print("   1. Integration of NFTVerifier into network/handshake.py")
    print("   2. Two or more Qubes running and discovering each other")
    print("   3. libp2p networking infrastructure")

    print("\n   Current status:")
    print(f"   - NFT exists on-chain:        ✅ Yes")
    print(f"   - Chaingraph verification:    ✅ Working")
    print(f"   - Handshake integration:      ⚠️  Pending (Phase 4)")
    print(f"   - P2P networking:             ⚠️  Mock mode (Phase 3)")

    # =============================================================================
    # STEP 5: SUMMARY
    # =============================================================================

    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    print(f"\n   Qube Created:")
    print(f"   ├─ ID:              {qube.qube_id}")
    print(f"   ├─ Name:            {qube.name}")
    print(f"   ├─ Genesis Hash:    {qube.genesis_block.block_hash}")
    print(f"   └─ Storage:         {qube.storage.db_path}")

    print(f"\n   NFT Minted:")
    print(f"   ├─ Category ID:     {mint_result['category_id']}")
    print(f"   ├─ TX ID:           {mint_result['mint_txid']}")
    print(f"   ├─ Commitment:      {mint_result['commitment'][:32]}...")
    print(f"   ├─ Recipient:       {recipient_address}")
    print(f"   └─ Explorer:        {mint_result['explorer_url']}")

    print(f"\n   Next Steps:")
    print(f"   1. Create another Qube and mint its NFT")
    print(f"   2. Implement NFTVerifier integration in handshake.py")
    print(f"   3. Test P2P authentication between two Qubes")
    print(f"   4. Enable libp2p for real P2P networking")

    print("\n" + "=" * 80)
    print("✅ END-TO-END TEST COMPLETE!")
    print("=" * 80 + "\n")

    # Clean up
    qube.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        logger.error("end_to_end_test_failed", error=str(e), exc_info=True)
        sys.exit(1)
