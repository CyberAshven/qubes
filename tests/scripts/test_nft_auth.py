#!/usr/bin/env python
"""
Test NFT Authentication Flow

Tests the complete authentication flow:
1. Create a test Qube with keypair
2. Register it (simulate minting)
3. Create authentication challenge
4. Sign challenge with Qube's private key
5. Verify the signature
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crypto.keys import generate_key_pair, serialize_public_key, derive_qube_id
from blockchain.nft_auth import (
    NFTAuthenticator,
    AuthChallenge,
    sign_challenge,
    authenticate_qube
)
from blockchain.registry import QubeNFTRegistry


async def test_nft_authentication():
    """Test the complete NFT authentication flow"""

    print("\n" + "=" * 70)
    print("NFT AUTHENTICATION TEST")
    print("=" * 70)

    # Step 1: Generate a test keypair
    print("\n[1] Generating test keypair...")
    private_key, public_key = generate_key_pair()
    public_key_hex = serialize_public_key(public_key)
    qube_id = derive_qube_id(public_key)

    print(f"    Qube ID: {qube_id}")
    print(f"    Public Key: {public_key_hex[:32]}...")

    # Step 2: Register Qube in registry (simulate minting)
    print("\n[2] Registering Qube in NFT registry...")
    registry = QubeNFTRegistry()

    # Create mock NFT registration
    mock_category_id = "test_" + qube_id.lower() + "_" + "0" * 48
    mock_mint_txid = "0" * 64

    registry.register_nft(
        qube_id=qube_id,
        category_id=mock_category_id,
        mint_txid=mock_mint_txid,
        recipient_address="bitcoincash:qtest123456789",
        commitment="test_commitment",
        network="testnet"
    )

    print(f"    Registered with category: {mock_category_id[:32]}...")

    # Step 3: Create mock BCMR with public key
    print("\n[3] Creating mock BCMR metadata...")
    import json
    from datetime import datetime, timezone

    bcmr_dir = Path("data/blockchain/bcmr")
    bcmr_dir.mkdir(parents=True, exist_ok=True)

    revision_time = datetime.now(timezone.utc).isoformat() + "Z"
    bcmr_metadata = {
        "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
        "version": {"major": 1, "minor": 0, "patch": 0},
        "latestRevision": revision_time,
        "registryIdentity": {
            "name": "Test Registry"
        },
        "identities": {
            mock_category_id: {
                revision_time: {
                    "name": f"Test Qube {qube_id}",
                    "extensions": {
                        "commitment_data": {
                            "qube_id": qube_id,
                            "creator_public_key": public_key_hex,
                            "genesis_block_hash": "test_hash",
                            "birth_timestamp": int(datetime.now(timezone.utc).timestamp())
                        }
                    }
                }
            }
        }
    }

    bcmr_path = bcmr_dir / f"{mock_category_id}.json"
    with open(bcmr_path, 'w') as f:
        json.dump(bcmr_metadata, f, indent=2)

    print(f"    BCMR saved to: {bcmr_path}")

    # Step 4: Create authentication challenge
    print("\n[4] Creating authentication challenge...")
    authenticator = NFTAuthenticator(registry=registry)

    try:
        challenge = authenticator.create_challenge(qube_id)
        print(f"    Challenge ID: {challenge.challenge_id}")
        print(f"    Nonce: {challenge.nonce[:32]}...")
        print(f"    Expires in: {challenge.expires_at - challenge.timestamp}s")
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

    # Step 5: Sign the challenge
    print("\n[5] Signing challenge with Qube's private key...")
    signature_hex = sign_challenge(challenge.to_dict(), private_key)
    print(f"    Signature: {signature_hex[:64]}...")

    # Step 6: Verify the signature
    print("\n[6] Verifying signed challenge...")
    result = await authenticator.verify_challenge_response(
        challenge.challenge_id,
        signature_hex
    )

    print(f"    Authenticated: {result.authenticated}")
    print(f"    Qube ID: {result.qube_id}")
    print(f"    Public Key Match: {result.public_key == public_key_hex if result.public_key else 'N/A'}")
    print(f"    NFT Verified: {result.nft_verified}")

    if result.error:
        print(f"    Error: {result.error}")

    # Step 7: Test with wrong signature
    print("\n[7] Testing with WRONG signature (should fail)...")
    wrong_challenge = authenticator.create_challenge(qube_id)

    # Generate different keypair for wrong signature
    wrong_private_key, _ = generate_key_pair()
    wrong_signature = sign_challenge(wrong_challenge.to_dict(), wrong_private_key)

    wrong_result = await authenticator.verify_challenge_response(
        wrong_challenge.challenge_id,
        wrong_signature
    )

    print(f"    Authenticated: {wrong_result.authenticated}")
    print(f"    Error: {wrong_result.error}")

    if wrong_result.authenticated:
        print("    WARNING: Wrong signature was accepted!")
        return False

    # Cleanup
    print("\n[8] Cleaning up...")
    bcmr_path.unlink(missing_ok=True)
    print("    Test files removed")

    # Summary
    print("\n" + "=" * 70)
    if result.authenticated and not wrong_result.authenticated:
        print("SUCCESS: NFT Authentication test passed!")
        print("=" * 70)
        return True
    else:
        print("FAILED: NFT Authentication test failed!")
        print("=" * 70)
        return False


async def test_convenience_function():
    """Test the authenticate_qube convenience function"""

    print("\n" + "=" * 70)
    print("CONVENIENCE FUNCTION TEST")
    print("=" * 70)

    # Generate keypair
    private_key, public_key = generate_key_pair()
    public_key_hex = serialize_public_key(public_key)
    qube_id = derive_qube_id(public_key)

    print(f"\nQube ID: {qube_id}")

    # Register
    registry = QubeNFTRegistry()
    mock_category_id = "conv_" + qube_id.lower() + "_" + "0" * 48

    registry.register_nft(
        qube_id=qube_id,
        category_id=mock_category_id,
        mint_txid="0" * 64,
        recipient_address="bitcoincash:qtest",
        commitment="test",
        network="testnet"
    )

    # Create BCMR
    import json
    from datetime import datetime, timezone

    bcmr_dir = Path("data/blockchain/bcmr")
    bcmr_dir.mkdir(parents=True, exist_ok=True)

    revision_time = datetime.now(timezone.utc).isoformat() + "Z"
    bcmr_metadata = {
        "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
        "latestRevision": revision_time,
        "identities": {
            mock_category_id: {
                revision_time: {
                    "extensions": {
                        "commitment_data": {
                            "qube_id": qube_id,
                            "creator_public_key": public_key_hex
                        }
                    }
                }
            }
        }
    }

    bcmr_path = bcmr_dir / f"{mock_category_id}.json"
    with open(bcmr_path, 'w') as f:
        json.dump(bcmr_metadata, f, indent=2)

    # Test authenticate_qube function
    print("\nCalling authenticate_qube()...")
    result = await authenticate_qube(qube_id, private_key)

    print(f"Result: {result.to_dict()}")

    # Cleanup
    bcmr_path.unlink(missing_ok=True)

    if result.authenticated:
        print("\nSUCCESS: Convenience function works!")
        return True
    else:
        print(f"\nFAILED: {result.error}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("QUBES NFT AUTHENTICATION TEST SUITE")
    print("=" * 70)

    # Run tests
    test1_passed = asyncio.run(test_nft_authentication())
    test2_passed = asyncio.run(test_convenience_function())

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  NFT Authentication Flow: {'PASS' if test1_passed else 'FAIL'}")
    print(f"  Convenience Function:    {'PASS' if test2_passed else 'FAIL'}")
    print("=" * 70)

    sys.exit(0 if test1_passed and test2_passed else 1)
