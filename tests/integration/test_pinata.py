"""
Quick test of Pinata IPFS integration
"""
import asyncio
import os
from dotenv import load_dotenv
from blockchain.ipfs import IPFSUploader

async def test_pinata():
    # Load environment variables
    load_dotenv()

    print("=" * 70)
    print("🧪 TESTING PINATA IPFS INTEGRATION")
    print("=" * 70)
    print()

    # Check if credentials are loaded
    api_key = os.getenv("PINATA_API_KEY")

    if not api_key:
        print("❌ PINATA_API_KEY (JWT token) not found in .env file")
        print("   Get your JWT from: https://app.pinata.cloud/developers/api-keys")
        return

    print(f"✅ Found PINATA_API_KEY (JWT): {api_key[:30]}...")
    print()

    # Create uploader with Pinata enabled
    uploader = IPFSUploader(use_pinata=True)

    # Test metadata (sample BCMR)
    test_metadata = {
        "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
        "version": {"major": 1, "minor": 0, "patch": 0},
        "latestRevision": "2025-10-04T00:00:00.000Z",
        "registryIdentity": {
            "name": "Qubes Network",
            "description": "Test upload from Qubes blockchain integration"
        },
        "test": {
            "message": "This is a test BCMR upload to Pinata",
            "timestamp": "2025-10-04T17:30:00Z",
            "purpose": "Verifying Phase 4 blockchain integration"
        }
    }

    print("📤 Uploading test BCMR metadata to Pinata...")
    print()

    try:
        ipfs_uri = await uploader.upload_bcmr(test_metadata, pin=True)

        if ipfs_uri:
            cid = ipfs_uri.replace("ipfs://", "")

            print()
            print("=" * 70)
            print("✅ SUCCESS! PINATA UPLOAD COMPLETED")
            print("=" * 70)
            print()
            print(f"📍 IPFS URI:     {ipfs_uri}")
            print(f"🔗 CID:          {cid}")
            print()
            print("🌐 Access your file at:")
            print(f"   Pinata Gateway:    https://gateway.pinata.cloud/ipfs/{cid}")
            print(f"   IPFS.io Gateway:   https://ipfs.io/ipfs/{cid}")
            print(f"   Cloudflare IPFS:   https://cloudflare-ipfs.com/ipfs/{cid}")
            print()
            print("💡 Tip: It may take 1-2 minutes to propagate across IPFS gateways")
            print()
            print("🎉 Your Pinata integration is working perfectly!")
            print()

            return True
        else:
            print()
            print("=" * 70)
            print("❌ UPLOAD FAILED")
            print("=" * 70)
            print()
            print("The upload returned None. Check the logs above for errors.")
            print()
            return False

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR DURING UPLOAD")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("1. Invalid API credentials")
        print("2. No internet connection")
        print("3. Pinata service is down")
        print("4. API key doesn't have 'pinJSONToIPFS' permission")
        print()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pinata())

    if success:
        print("✅ Test passed! Ready for production use.")
    else:
        print("❌ Test failed. Please check the errors above.")
