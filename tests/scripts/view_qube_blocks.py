"""
View Qube Blocks - Inspect Genesis and Memory Blocks

This script loads a Qube and displays all its blocks in a readable format.
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.qube import Qube
from utils.logging import configure_logging


async def view_qube_blocks(qube_identifier: str):
    """View all blocks for a Qube

    Args:
        qube_identifier: Can be either:
            - Qube ID only (e.g., "BDC18592")
            - Name_ID format (e.g., "Alph_BDC18592")
    """

    # Configure logging (minimal output)
    configure_logging(log_level="WARNING", console_output=True)

    print("=" * 80)
    print(f"📦 QUBE BLOCK VIEWER - {qube_identifier}")
    print("=" * 80)

    # Load Qube from storage
    try:
        from storage.lmdb_storage import LMDBStorage
        import glob

        # Try to find the qube directory
        # First check if it's a full name_id format
        db_path = Path(f"data/qubes/{qube_identifier}/lmdb")

        # If not found, try to find it by ID only
        if not db_path.exists():
            # Search for directories ending with the ID
            pattern = f"data/qubes/*_{qube_identifier}/lmdb"
            matches = glob.glob(pattern)

            if matches:
                db_path = Path(matches[0])
                print(f"\n✅ Found Qube at: {db_path.parent.name}")
            elif Path(f"data/qubes/{qube_identifier}/lmdb").exists():
                # Fallback to old format (ID only)
                db_path = Path(f"data/qubes/{qube_identifier}/lmdb")
            else:
                print(f"\n❌ Qube not found. Tried:")
                print(f"   - data/qubes/{qube_identifier}/lmdb")
                print(f"   - data/qubes/*_{qube_identifier}/lmdb")
                return

        storage = LMDBStorage(db_path)

        # Extract qube_id from directory name
        qube_dir_name = db_path.parent.name  # Gets "Alph_F0694273" or "F0694273"
        if '_' in qube_dir_name:
            qube_id = qube_dir_name.split('_')[-1]  # Gets "F0694273" from "Alph_F0694273"
        else:
            qube_id = qube_dir_name  # Fallback for old format (ID only)

        # Get list of blocks
        block_numbers = storage.list_blocks(qube_id)
        if not block_numbers:
            print(f"\n❌ No blocks found for Qube {qube_id}")
            storage.close()
            return

        # Load blocks
        blocks = []
        for block_num in sorted(block_numbers):
            block = storage.read_block(qube_id, block_num)
            blocks.append(block)

        # Get genesis block for metadata
        genesis_block = blocks[0]
        genesis_data = genesis_block.content

        print(f"\n✅ Loaded Qube: {genesis_data.get('qube_name', qube_id)}")
        print(f"   Qube ID: {qube_id}")
        print(f"   AI Model: {genesis_data.get('ai_model', 'N/A')}")
        print(f"   Total Blocks: {len(blocks)}")

    except Exception as e:
        import traceback
        print(f"\n❌ Failed to load Qube: {e}")
        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("📜 MEMORY BLOCKS")
    print("=" * 80)

    for i, block in enumerate(blocks):
        print(f"\n{'─' * 80}")
        print(f"Block #{i}")
        print(f"{'─' * 80}")

        # Block metadata
        print(f"Hash:      {block.block_hash[:16]}...")
        print(f"Prev Hash: {block.previous_hash[:16] if block.previous_hash else 'None (Genesis)'}...")
        print(f"Timestamp: {datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Type:      {block.block_type if isinstance(block.block_type, str) else block.block_type.value}")

        # Parse data
        try:
            data = block.content

            # Genesis block - check top-level fields first
            block_type_str = block.block_type if isinstance(block.block_type, str) else block.block_type.value
            if block_type_str == "GENESIS":
                print(f"\n🌟 GENESIS BLOCK")

                # Genesis uses top-level fields, not content dict
                qube_name = getattr(block, 'qube_name', data.get('qube_name', 'N/A'))
                creator = getattr(block, 'creator', data.get('creator', 'N/A'))
                ai_model = getattr(block, 'ai_model', data.get('ai_model', 'N/A'))
                genesis_prompt = getattr(block, 'genesis_prompt', data.get('genesis_prompt', 'N/A'))
                capabilities = getattr(block, 'capabilities', data.get('capabilities', {}))

                print(f"   Qube Name: {qube_name}")
                print(f"   Creator: {creator}")
                print(f"   AI Model: {ai_model}")
                print(f"   Genesis Prompt:")
                prompt_text = genesis_prompt if genesis_prompt != 'N/A' else 'N/A'
                print(f"   {str(prompt_text)[:200]}...")

                if capabilities:
                    print(f"\n   Capabilities:")
                    for key, value in capabilities.items():
                        print(f"      • {key}: {value}")

                if hasattr(block, 'favorite_color'):
                    print(f"\n   Favorite Color: {block.favorite_color}")
                if hasattr(block, 'home_blockchain'):
                    print(f"   Home Blockchain: {block.home_blockchain}")

            # Message blocks
            elif block_type_str == "MESSAGE":
                # Check for message_body (documented format) or content/role (actual format)
                message_body = data.get('message_body', '')
                message_type = data.get('message_type', '')
                role = data.get('role', 'unknown')
                content = data.get('content', message_body)

                if message_type == "qube_to_human" or role == "assistant":
                    print(f"\n🤖 ASSISTANT MESSAGE")
                elif message_type == "human_to_qube" or role == "user":
                    print(f"\n👤 USER MESSAGE")
                elif role == "system":
                    print(f"\n⚙️  SYSTEM MESSAGE")
                else:
                    print(f"\n💬 MESSAGE")

                if content:
                    print(f"   Content: {content[:500]}{'...' if len(content) > 500 else ''}")
                else:
                    print(f"   Content: [Empty]")

                if message_type:
                    print(f"   Type: {message_type}")
                if data.get('recipient_id'):
                    print(f"   Recipient: {data.get('recipient_id')}")

                if 'tool_calls' in data and data['tool_calls']:
                    print(f"\n   🔧 Tool Calls:")
                    for tc in data['tool_calls']:
                        print(f"      • {tc.get('name', 'unknown')}: {tc.get('parameters', {})}")

            # Observation blocks (tool results)
            elif block_type_str == "OBSERVATION":
                print(f"\n🔧 OBSERVATION (Tool Result)")
                print(f"   Tool: {data.get('tool', 'unknown')}")
                result = data.get('observation', '')
                print(f"   Result: {str(result)[:300]}{'...' if len(str(result)) > 300 else ''}")

            # Memory anchor blocks
            elif block_type_str == "MEMORY_ANCHOR":
                print(f"\n⚓ MEMORY ANCHOR")
                print(f"   Session ID: {data.get('session_id', 'N/A')}")
                print(f"   Blocks Anchored: {data.get('blocks_anchored', 0)}")

            # Generic data
            else:
                print(f"\n📄 DATA:")
                print(f"   {json.dumps(data, indent=2)[:500]}...")

        except Exception as e:
            print(f"\n📄 ERROR PARSING DATA:")
            print(f"   {str(e)}")

        # Signature
        if hasattr(block, 'signature') and block.signature:
            print(f"\nSignature: {block.signature[:32]}...")
        else:
            print("\nSignature: None")

    # Chain integrity check
    print("\n" + "=" * 80)
    print("🔗 CHAIN INTEGRITY CHECK")
    print("=" * 80)

    # Simple integrity check - verify hashes link correctly
    is_valid = True
    for i in range(1, len(blocks)):
        if blocks[i].previous_hash != blocks[i-1].block_hash:
            print(f"❌ Block {i} previous_hash doesn't match Block {i-1} hash")
            is_valid = False

    if is_valid:
        print("✅ Chain is valid - all blocks are properly linked")
    else:
        print("❌ Chain integrity error - some blocks may be corrupted")

    print("\n" + "=" * 80)
    print("📊 STORAGE LOCATION")
    print("=" * 80)
    qube_dir = db_path.parent.name
    print(f"\nQube Directory: data/qubes/{qube_dir}/")
    print(f"   • LMDB Database: data/qubes/{qube_dir}/lmdb/")
    print(f"   • Session Data: data/qubes/{qube_dir}/sessions/")

    # Close storage
    storage.close()
    print("\n✅ Storage closed")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_qube_blocks.py <qube_identifier>")
        print("\nExample:")
        print("  python examples/view_qube_blocks.py BDC18592")
        print("  python examples/view_qube_blocks.py Alph_BDC18592")
        sys.exit(1)

    qube_identifier = sys.argv[1]
    asyncio.run(view_qube_blocks(qube_identifier))
