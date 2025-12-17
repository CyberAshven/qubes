#!/usr/bin/env python3
"""Test script to verify ACTION block decryption"""
import asyncio
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.user_orchestrator import UserOrchestrator


@pytest.mark.asyncio
@pytest.mark.skip(reason="Interactive test requiring password input")
async def test_block_decryption():
    """Test decryption of MESSAGE and ACTION blocks"""
    # Create orchestrator
    orchestrator = UserOrchestrator(user_id="bit_faced")

    # Set master key with password (you'll need to enter this)
    password = input("Enter password for bit_faced: ")
    orchestrator.set_master_key(password)

    # Load Alph (qube_id AC6EA9C4)
    qube_id = "AC6EA9C4"
    await orchestrator.load_qube(qube_id)
    qube = orchestrator.qubes[qube_id]

    print(f"\n✅ Loaded qube: {qube.name} ({qube_id})")
    print(f"📊 Total permanent blocks: {len(qube.memory_chain.block_index)}")

    # Test decryption of blocks 10 (MESSAGE) and 11 (ACTION)
    for block_num in [10, 11]:
        print(f"\n{'='*60}")
        print(f"Testing Block #{block_num}")
        print(f"{'='*60}")

        # Load block from file
        block = qube.memory_chain.get_block(block_num)
        block_data = block.to_dict()

        print(f"Block type: {block_data.get('block_type')}")
        print(f"Encrypted: {block_data.get('encrypted')}")

        content = block_data.get('content', {})
        print(f"Content type: {type(content)}")
        print(f"Has ciphertext: {'ciphertext' in content}")

        if isinstance(content, dict) and 'ciphertext' in content:
            print("\n🔐 Block content is ENCRYPTED, attempting decryption...")
            try:
                decrypted = qube.decrypt_block_content(content)
                print(f"✅ Decryption SUCCESSFUL!")
                print(f"Decrypted content keys: {list(decrypted.keys())}")
                print(f"Decrypted content preview: {str(decrypted)[:200]}...")
            except Exception as e:
                print(f"❌ Decryption FAILED: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("🔓 Block content is NOT encrypted")
            print(f"Content: {content}")


if __name__ == "__main__":
    asyncio.run(test_block_decryption())
