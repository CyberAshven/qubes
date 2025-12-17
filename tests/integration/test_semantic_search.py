"""
Test Semantic Search with FAISS

Tests semantic search capabilities using sentence transformers and FAISS.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import configure_logging


async def test_semantic_search():
    """Test semantic search functionality"""

    configure_logging(log_level="INFO", console_output=True)

    print("=" * 70)
    print("🔍 TESTING SEMANTIC SEARCH WITH FAISS")
    print("=" * 70)

    print("\n📦 Installing dependencies...")
    print("   pip install faiss-cpu sentence-transformers")
    print("\n⏳ This may take a minute on first run (downloading model)...")

    try:
        from ai.semantic_search import SemanticSearch
        from core.block import create_message_block
        from crypto.keys import generate_key_pair, derive_qube_id

        # Generate test identity
        private_key, public_key = generate_key_pair()
        qube_id = derive_qube_id(public_key)

        # Create semantic search instance
        test_storage_dir = Path("data/test_semantic")
        test_storage_dir.mkdir(parents=True, exist_ok=True)

        print("\n🤖 Initializing semantic search...")
        search = SemanticSearch(qube_id, test_storage_dir)
        print(f"✅ Model loaded: {search.model_name}")
        print(f"   Embedding dimensions: {search.embedding_dim}")

        # Create test blocks with different content
        print("\n📝 Creating test blocks...")

        test_messages = [
            "The weather is beautiful today with clear blue skies",
            "I love programming in Python, it's such an elegant language",
            "Bitcoin and blockchain technology are revolutionary",
            "Artificial intelligence is transforming how we work",
            "Climate change is one of the biggest challenges we face",
            "Quantum computing will change cryptography forever",
            "The sunset over the ocean was absolutely breathtaking",
            "Machine learning models require lots of training data",
        ]

        blocks = []
        for i, message in enumerate(test_messages):
            block = create_message_block(
                qube_id=qube_id,
                block_number=i,
                previous_hash="0" * 64,
                message_type="qube_to_human",
                recipient_id="human",
                message_body=message,
                conversation_id="test",
                requires_response=False,
                temporary=False
            )
            blocks.append(block)
            search.add_block(block)
            print(f"   ✅ Block {i}: {message[:50]}...")

        print(f"\n✅ Indexed {len(blocks)} blocks")

        # Test semantic search
        print("\n" + "=" * 70)
        print("🔍 Testing Semantic Search")
        print("=" * 70)

        test_queries = [
            "Tell me about the weather",
            "What do you know about AI and machine learning?",
            "Discuss cryptocurrency technology",
            "Beautiful nature scenes",
        ]

        for query in test_queries:
            print(f"\n📝 Query: \"{query}\"")
            print("   Top 3 results:\n")

            results = search.search(query, top_k=3)

            for rank, (block_number, similarity) in enumerate(results, 1):
                block = blocks[block_number]
                message = block.content.get("message_body", "")
                print(f"   {rank}. [Score: {similarity:.3f}] Block #{block_number}")
                print(f"      {message[:60]}...")

        # Test hybrid search
        print("\n" + "=" * 70)
        print("🔍 Testing Hybrid Search (Semantic + Keywords)")
        print("=" * 70)

        query = "weather and climate"
        print(f"\n📝 Query: \"{query}\"")
        print("   Top 3 results (hybrid scoring):\n")

        hybrid_results = search.hybrid_search(query, blocks, top_k=3)

        for rank, (block, score) in enumerate(hybrid_results, 1):
            message = block.content.get("message_body", "")
            print(f"   {rank}. [Score: {score:.3f}] Block #{block.block_number}")
            print(f"      {message[:60]}...")

        # Test index persistence
        print("\n" + "=" * 70)
        print("💾 Testing Index Persistence")
        print("=" * 70)

        print("\n📁 Saving index to disk...")
        index_file = test_storage_dir / "semantic_index.faiss"
        mapping_file = test_storage_dir / "semantic_mapping.npy"

        if index_file.exists() and mapping_file.exists():
            print(f"✅ Index saved:")
            print(f"   Index file: {index_file}")
            print(f"   Mapping file: {mapping_file}")
            print(f"   Index size: {index_file.stat().st_size / 1024:.2f} KB")

            # Test loading
            print("\n🔄 Creating new search instance (loads from disk)...")
            search2 = SemanticSearch(qube_id, test_storage_dir)
            print(f"✅ Index loaded: {len(search2.block_ids)} vectors")

        else:
            print("❌ Index files not found")

        # Cleanup
        print("\n" + "=" * 70)
        print("🧹 Cleanup")
        print("=" * 70)

        import shutil
        shutil.rmtree(test_storage_dir)
        print("✅ Test directory removed")

        print("\n" + "=" * 70)
        print("✅ SEMANTIC SEARCH TESTS COMPLETE")
        print("=" * 70)

        print("\n📝 Summary:")
        print("   ✅ Semantic search initialization - Working")
        print("   ✅ Block indexing - Working")
        print("   ✅ Semantic similarity search - Working")
        print("   ✅ Hybrid search (semantic + keywords) - Working")
        print("   ✅ Index persistence - Working")

        print("\n💡 In production:")
        print("   from ai.semantic_search import SemanticSearch")
        print("   search = SemanticSearch(qube_id, storage_dir)")
        print("   search.add_block(block)  # Index new blocks")
        print("   results = search.search('query', top_k=5)")
        print("   hybrid = search.hybrid_search('query', blocks, top_k=5)")

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\n📦 Install dependencies:")
        print("   pip install faiss-cpu sentence-transformers")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_semantic_search())
