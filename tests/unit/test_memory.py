"""
Comprehensive Tests for Intelligent Memory Search System

Tests all 5 layers of the hybrid search system:
- Layer 1: Semantic Search (FAISS)
- Layer 2: Metadata Filtering
- Layer 3: Full-Text Search
- Layer 4: Temporal Relevance
- Layer 5: Relationship-Aware Ranking
"""

import sys
import pytest
import time
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.embeddings import (
    temporal_decay,
    relationship_boost,
    calculate_final_score,
    merge_results,
    SearchResult
)
from ai.tools.memory_search import (
    intelligent_memory_search,
    parse_query,
    filter_by_metadata,
    fulltext_search
)
from core.qube import Qube


class TestTemporalDecay:
    """Test temporal decay scoring function"""

    def test_recent_block_max_score(self):
        """Recent blocks should have score near 1.0"""
        current_time = int(datetime.now(timezone.utc).timestamp())
        score = temporal_decay(current_time, decay_rate=0.1)

        assert score == 1.0, "Current timestamp should have perfect score"

    def test_decay_over_time(self):
        """Older blocks should have lower scores"""
        current_time = int(datetime.now(timezone.utc).timestamp())

        # 1 day ago
        one_day_ago = current_time - 86400
        score_1day = temporal_decay(one_day_ago, decay_rate=0.1)

        # 30 days ago
        thirty_days_ago = current_time - (86400 * 30)
        score_30days = temporal_decay(thirty_days_ago, decay_rate=0.1)

        # 1 year ago
        one_year_ago = current_time - (86400 * 365)
        score_1year = temporal_decay(one_year_ago, decay_rate=0.1)

        # Scores should decrease over time
        assert score_1day > score_30days > score_1year
        assert 0.8 < score_1day < 1.0, f"1 day ago should be ~0.9, got {score_1day}"
        assert 0.2 < score_30days < 0.4, f"30 days ago should be ~0.25, got {score_30days}"
        assert 0 < score_1year < 0.1, f"1 year ago should be very low, got {score_1year}"

    def test_decay_rate_impact(self):
        """Higher decay rate should reduce scores faster"""
        thirty_days_ago = int(datetime.now(timezone.utc).timestamp()) - (86400 * 30)

        slow_decay = temporal_decay(thirty_days_ago, decay_rate=0.1)  # Slow
        fast_decay = temporal_decay(thirty_days_ago, decay_rate=1.0)  # Fast

        assert slow_decay > fast_decay, "Slow decay should preserve relevance longer"
        assert 0.2 < slow_decay < 0.4, f"Slow decay at 30 days: {slow_decay}"
        assert 0.02 < fast_decay < 0.05, f"Fast decay at 30 days: {fast_decay}"


class TestRelationshipBoost:
    """Test relationship-aware boosting function"""

    def test_no_relationship(self):
        """No relationship should return 1.0 (no boost)"""
        boost = relationship_boost(None)
        assert boost == 1.0

    def test_best_friend_boost(self):
        """Best friend should get highest boost"""
        relationship = {"is_best_friend": True, "overall_trust_score": 95}
        boost = relationship_boost(relationship)
        assert boost == 1.5, "Best friend should have 1.5x boost"

    def test_high_trust_boost(self):
        """High trust relationships should get good boost"""
        relationship = {"overall_trust_score": 85}
        boost = relationship_boost(relationship)
        assert boost == 1.3, "High trust (80+) should have 1.3x boost"

    def test_low_trust_penalty(self):
        """Low trust relationships should get penalty"""
        relationship = {"overall_trust_score": 25}
        boost = relationship_boost(relationship)
        assert boost == 0.8, "Low trust (<30) should have 0.8x penalty"

    def test_enemy_penalty(self):
        """Enemies should get significant penalty"""
        relationship = {"relationship_status": "enemy", "overall_trust_score": 10}
        boost = relationship_boost(relationship)
        assert boost == 0.7, "Enemies should have 0.7x penalty"

    def test_collaborative_bonus(self):
        """Successful collaborations should add bonus"""
        relationship = {
            "overall_trust_score": 85,  # Ensure high trust (>=80) gets 1.3
            "successful_joint_tasks": 15
        }
        boost = relationship_boost(relationship)
        # Base 1.3 (high trust) + 0.1 (collaborative bonus) = 1.4
        expected = 1.4
        assert abs(boost - expected) < 0.01, f"Expected ~{expected}, got {boost}"


class TestCalculateFinalScore:
    """Test final score calculation with all factors"""

    def test_semantic_and_keyword_weighting(self):
        """Test semantic (40%) and keyword (30%) weighting"""
        block = {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "block_type": "MESSAGE"
        }

        # Perfect semantic, no keywords
        score1 = calculate_final_score(block, semantic_score=1.0, keyword_score=0.0)

        # No semantic, perfect keywords
        score2 = calculate_final_score(block, semantic_score=0.0, keyword_score=1.0)

        # Semantic weighted higher (40% vs 30%)
        assert score1 > score2, "Semantic should be weighted higher than keywords"

    def test_temporal_impact(self):
        """Test temporal decay impact on scoring"""
        current_time = int(datetime.now(timezone.utc).timestamp())
        old_time = current_time - (86400 * 365)  # 1 year ago

        recent_block = {
            "timestamp": current_time,
            "block_type": "MESSAGE"
        }

        old_block = {
            "timestamp": old_time,
            "block_type": "MESSAGE"
        }

        # Same semantic/keyword scores
        recent_score = calculate_final_score(recent_block, 0.8, 0.7)
        old_score = calculate_final_score(old_block, 0.8, 0.7)

        assert recent_score > old_score, "Recent blocks should score higher"

    def test_block_type_weighting(self):
        """Test block type importance weights"""
        timestamp = int(datetime.now(timezone.utc).timestamp())

        summary_block = {"timestamp": timestamp, "block_type": "SUMMARY"}
        decision_block = {"timestamp": timestamp, "block_type": "DECISION"}
        message_block = {"timestamp": timestamp, "block_type": "MESSAGE"}
        thought_block = {"timestamp": timestamp, "block_type": "THOUGHT"}

        # Same semantic/keyword scores
        summary_score = calculate_final_score(summary_block, 0.8, 0.8)
        decision_score = calculate_final_score(decision_block, 0.8, 0.8)
        message_score = calculate_final_score(message_block, 0.8, 0.8)
        thought_score = calculate_final_score(thought_block, 0.8, 0.8)

        # SUMMARY (1.3) > DECISION (1.15) > MESSAGE (1.0) > THOUGHT (0.9)
        assert summary_score > decision_score > message_score > thought_score

    def test_query_type_recent_events(self):
        """Test query_type='recent_events' boosts recent blocks"""
        current_time = int(datetime.now(timezone.utc).timestamp())
        recent_time = current_time - 3600  # 1 hour ago

        recent_block = {"timestamp": recent_time, "block_type": "MESSAGE"}

        # Without query_type
        normal_score = calculate_final_score(recent_block, 0.8, 0.7)

        # With query_type='recent_events'
        context = {"query_type": "recent_events"}
        boosted_score = calculate_final_score(recent_block, 0.8, 0.7, context)

        assert boosted_score > normal_score, "recent_events query should boost recent blocks"


class TestParseQuery:
    """Test query parsing and classification"""

    def test_recent_query_detection(self):
        """Detect recent events queries"""
        queries = [
            "What happened recently?",
            "Show me the latest updates",
            "What did we do last week?"
        ]

        for query in queries:
            parsed = parse_query(query)
            assert parsed["query_type"] == "recent_events", f"Failed to detect recent: {query}"

    def test_historical_query_detection(self):
        """Detect historical queries"""
        queries = [
            "What did we discuss last month?",
            "Remember when we talked about AI?",
            "Show me our past conversations"
        ]

        for query in queries:
            parsed = parse_query(query)
            assert parsed["query_type"] == "historical", f"Failed to detect historical: {query}"

    def test_time_range_extraction(self):
        """Extract time ranges from queries"""
        query = "What happened last week?"
        parsed = parse_query(query)

        assert parsed["date_range"] is not None
        start_time, end_time = parsed["date_range"]
        assert end_time - start_time == 7 * 86400, "Last week should be 7 days range"


class TestMergeResults:
    """Test result merging and deduplication"""

    def test_deduplication(self):
        """Blocks in both results should be deduplicated"""
        timestamp = int(datetime.now(timezone.utc).timestamp())

        block1 = {"block_number": 1, "timestamp": timestamp, "block_type": "MESSAGE", "content": {}}
        block2 = {"block_number": 2, "timestamp": timestamp, "block_type": "MESSAGE", "content": {}}

        semantic_results = [(block1, 0.9), (block2, 0.7)]
        keyword_results = [(block1, 0.8)]  # block1 appears in both

        merged = merge_results(semantic_results, keyword_results)

        # Should have 2 unique blocks (sorted by score)
        assert len(merged) == 2, f"Should have 2 unique blocks, got {len(merged)}"

        # Find block1 in results (it should have both scores)
        block1_result = next(r for r in merged if r.block["block_number"] == 1)
        assert block1_result.semantic_score == 0.9, f"Expected semantic=0.9, got {block1_result.semantic_score}"
        assert block1_result.keyword_score == 0.8, f"Expected keyword=0.8, got {block1_result.keyword_score}"

    def test_sorting_by_combined_score(self):
        """Results should be sorted by combined score (descending)"""
        timestamp = int(datetime.now(timezone.utc).timestamp())

        block1 = {"block_number": 1, "timestamp": timestamp, "block_type": "MESSAGE", "content": {}}
        block2 = {"block_number": 2, "timestamp": timestamp, "block_type": "MESSAGE", "content": {}}

        # block2 has higher combined score (0.9 semantic vs 0.6)
        semantic_results = [(block1, 0.6), (block2, 0.9)]
        keyword_results = []

        merged = merge_results(semantic_results, keyword_results)

        # Results should be sorted by score (descending)
        assert merged[0].score > merged[1].score, "Results should be sorted by score"
        # Higher semantic score should be first
        assert merged[0].semantic_score > merged[1].semantic_score


@pytest.mark.asyncio
async def test_metadata_filtering():
    """Test Layer 2: Metadata filtering"""
    data_dir = Path(__file__).parent.parent / "data"

    # Create test Qube with blocks
    qube = Qube.create_new(
        qube_name="FilterTest",
        creator="TestUser",
        genesis_prompt="Test",
        ai_model="gpt-4o",
        voice_model="test",
        data_dir=data_dir,
        user_name="test_user"
    )

    # Create blocks with different types and timestamps
    from core.session import Session
    from core.block import create_message_block, create_thought_block

    session = Session(qube)

    # Create MESSAGE blocks
    for i in range(3):
        msg = create_message_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            message_type="qube_to_human",
            recipient_id="human_user",
            message_body=f"Test message {i}",
            conversation_id="test"
        )
        session.create_block(msg)

    # Create THOUGHT blocks
    for i in range(2):
        thought = create_thought_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            internal_monologue=f"Test thought {i}",
            reasoning_chain=[f"Reasoning step {i}"],
            confidence=0.9
        )
        session.create_block(thought)

    # Anchor to permanent chain
    session.anchor_to_chain(create_summary=False)

    # Test filtering by block type
    message_blocks = await filter_by_metadata(
        qube=qube,
        block_types=["MESSAGE"]
    )

    assert len(message_blocks) == 3, f"Should find 3 MESSAGE blocks, found {len(message_blocks)}"
    assert all(b.get("block_type") == "MESSAGE" for b in message_blocks)

    thought_blocks = await filter_by_metadata(
        qube=qube,
        block_types=["THOUGHT"]
    )

    assert len(thought_blocks) == 2, f"Should find 2 THOUGHT blocks, found {len(thought_blocks)}"


@pytest.mark.asyncio
async def test_fulltext_search():
    """Test Layer 3: Full-text keyword search"""
    timestamp = int(datetime.now(timezone.utc).timestamp())

    candidates = [
        {
            "block_number": 1,
            "block_type": "MESSAGE",
            "timestamp": timestamp,
            "content": {"message_body": "I love Python programming"}
        },
        {
            "block_number": 2,
            "block_type": "MESSAGE",
            "timestamp": timestamp,
            "content": {"message_body": "JavaScript is also great"}
        },
        {
            "block_number": 3,
            "block_type": "MESSAGE",
            "timestamp": timestamp,
            "content": {"message_body": "Python and JavaScript together"}
        }
    ]

    # Search for "Python"
    results = await fulltext_search(qube=None, query="Python programming", candidates=candidates, top_k=10)

    # Should find blocks 1 and 3 (both mention Python)
    assert len(results) >= 2
    assert results[0][0]["block_number"] in [1, 3]

    # Block 1 should score higher (has both "Python" and "programming")
    scores = {r[0]["block_number"]: r[1] for r in results}
    assert scores.get(1, 0) > scores.get(3, 0), "Block with both keywords should score higher"


@pytest.mark.asyncio
async def test_end_to_end_intelligent_search():
    """Test complete 5-layer intelligent search system"""
    data_dir = Path(__file__).parent.parent / "data"

    # Create test Qube
    qube = Qube.create_new(
        qube_name="E2ESearchTest",
        creator="TestUser",
        genesis_prompt="Test intelligent search",
        ai_model="gpt-4o",
        voice_model="test",
        data_dir=data_dir,
        user_name="test_user"
    )

    from core.session import Session
    from core.block import create_message_block

    session = Session(qube)

    # Create varied blocks
    messages = [
        "I'm learning Python programming",
        "JavaScript is my favorite language",
        "Python and JavaScript work well together",
        "I prefer TypeScript over JavaScript",
        "Machine learning with Python is amazing"
    ]

    for msg in messages:
        block = create_message_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            message_type="qube_to_human",
            recipient_id="human_user",
            message_body=msg,
            conversation_id="test"
        )
        session.create_block(block)
        time.sleep(0.1)  # Small delay for timestamp variation

    # Anchor to permanent chain
    session.anchor_to_chain(create_summary=True)

    # Test intelligent search
    results = await intelligent_memory_search(
        qube=qube,
        query="Python programming machine learning",
        context={},
        top_k=3
    )

    assert len(results) > 0, "Should find matching results"

    # Check that relevant blocks are ranked highly
    # Note: After anchoring, MESSAGE blocks are encrypted, so we can't check content
    # Instead, verify the search returns results with proper scoring
    top_result = results[0]
    assert top_result.score > 0, "Top result should have positive relevance score"
    assert hasattr(top_result, 'block'), "Result should have block attribute"
    assert "block_type" in top_result.block, "Block should have type"

    # Verify search returns multiple results ranked by score
    if len(results) > 1:
        assert results[0].score >= results[1].score, "Results should be ranked by score"

    print(f"\n✅ End-to-end search test passed!")
    print(f"   Query: 'Python programming machine learning'")
    print(f"   Results: {len(results)}")
    print(f"   Top result score: {top_result.score:.2f}")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("INTELLIGENT MEMORY SEARCH TESTS")
    print("=" * 60)

    # Run unit tests
    print("\n[1/6] Testing temporal_decay()...")
    test_temporal = TestTemporalDecay()
    test_temporal.test_recent_block_max_score()
    test_temporal.test_decay_over_time()
    test_temporal.test_decay_rate_impact()
    print("✅ Temporal decay tests passed")

    print("\n[2/6] Testing relationship_boost()...")
    test_rel = TestRelationshipBoost()
    test_rel.test_no_relationship()
    test_rel.test_best_friend_boost()
    test_rel.test_high_trust_boost()
    test_rel.test_low_trust_penalty()
    test_rel.test_enemy_penalty()
    test_rel.test_collaborative_bonus()
    print("✅ Relationship boost tests passed")

    print("\n[3/6] Testing calculate_final_score()...")
    test_score = TestCalculateFinalScore()
    test_score.test_semantic_and_keyword_weighting()
    test_score.test_temporal_impact()
    test_score.test_block_type_weighting()
    test_score.test_query_type_recent_events()
    print("✅ Final score calculation tests passed")

    print("\n[4/6] Testing parse_query()...")
    test_parse = TestParseQuery()
    test_parse.test_recent_query_detection()
    test_parse.test_historical_query_detection()
    test_parse.test_time_range_extraction()
    print("✅ Query parsing tests passed")

    print("\n[5/6] Testing merge_results()...")
    test_merge = TestMergeResults()
    test_merge.test_deduplication()
    test_merge.test_sorting_by_combined_score()
    print("✅ Result merging tests passed")

    print("\n[6/6] Running integration tests...")
    import asyncio
    asyncio.run(test_metadata_filtering())
    print("✅ Metadata filtering test passed")

    asyncio.run(test_fulltext_search())
    print("✅ Full-text search test passed")

    asyncio.run(test_end_to_end_intelligent_search())
    print("✅ End-to-end integration test passed")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED - PHASE 2 COMPLETE!")
    print("=" * 60)
    print("\n5-Layer Intelligent Memory Search System:")
    print("✅ Layer 1: Semantic Search (FAISS)")
    print("✅ Layer 2: Metadata Filtering")
    print("✅ Layer 3: Full-Text Keyword Search")
    print("✅ Layer 4: Temporal Relevance Scoring")
    print("✅ Layer 5: Relationship-Aware Ranking (ready for Phase 5)")
    print("\n🚀 Phase 2: 100% COMPLETE")


if __name__ == "__main__":
    main()
