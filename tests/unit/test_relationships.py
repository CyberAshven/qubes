"""
Tests for Relationship System (Phase 5)

Tests:
- Relationship creation and storage
- Trust scoring with different profiles
- Relationship progression
- Best friend designation
- Shared experiences
- Third-party reputation
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from relationships import (
    Relationship,
    RelationshipStorage,
    TrustScorer,
    RelationshipProgressionManager,
    SocialDynamicsManager
)


@pytest.fixture
def temp_qube_dir():
    """Create temporary Qube directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def social_manager(temp_qube_dir):
    """Create SocialDynamicsManager for testing"""
    return SocialDynamicsManager(temp_qube_dir)


class TestRelationship:
    """Test Relationship class"""

    def test_create_unmet_relationship(self):
        """Test creating an unmet relationship"""
        rel = Relationship(
            entity_id="TEST123",
            entity_type="qube",
            has_met=False
        )

        assert rel.entity_id == "TEST123"
        assert rel.entity_type == "qube"
        assert rel.has_met == False
        assert rel.relationship_status == "unmet"
        assert rel.first_contact_timestamp is None
        assert rel.overall_trust_score == 50  # Neutral start

    def test_create_met_relationship(self):
        """Test creating a relationship where entities have met"""
        rel = Relationship(
            entity_id="TEST456",
            entity_type="qube",
            has_met=True
        )

        assert rel.has_met == True
        assert rel.relationship_status == "stranger"
        assert rel.first_contact_timestamp is not None

    def test_mark_as_met(self):
        """Test marking unmet relationship as met"""
        rel = Relationship(
            entity_id="TEST789",
            has_met=False
        )

        assert rel.relationship_status == "unmet"

        rel.mark_as_met(block_number=42)

        assert rel.has_met == True
        assert rel.first_contact_block == 42
        assert rel.relationship_status == "stranger"

    def test_progress_status(self):
        """Test relationship status progression"""
        rel = Relationship("TEST001", has_met=True)

        assert rel.relationship_status == "stranger"
        assert len(rel.relationship_progression) == 1

        rel.progress_status("acquaintance")

        assert rel.relationship_status == "acquaintance"
        assert len(rel.relationship_progression) == 2
        assert rel.relationship_progression[-1]["status"] == "acquaintance"

    def test_add_shared_experience(self):
        """Test adding shared experiences"""
        rel = Relationship("TEST002", has_met=True)

        rel.add_shared_experience(
            event="Collaborated on research",
            sentiment="positive",
            details={"project": "AI ethics"}
        )

        assert len(rel.shared_experiences) == 1
        assert rel.shared_experiences[0]["event"] == "Collaborated on research"
        assert rel.shared_experiences[0]["sentiment"] == "positive"

    def test_update_expertise(self):
        """Test updating expertise scores"""
        rel = Relationship("TEST003", has_met=True)

        rel.update_expertise("web_research", 85.5)
        rel.update_expertise("data_analysis", 72.0)

        assert rel.expertise_scores["web_research"] == 85.5
        assert rel.expertise_scores["data_analysis"] == 72.0

    def test_add_third_party_opinion(self):
        """Test adding third-party reputation"""
        rel = Relationship("TEST004", has_met=False)

        rel.add_third_party_opinion(
            observer_id="OBSERVER1",
            trust_score=75.0,
            relationship_type="friend"
        )

        assert "OBSERVER1" in rel.third_party_reputation
        assert rel.third_party_reputation["OBSERVER1"]["trust_score"] == 75.0

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization"""
        rel = Relationship(
            entity_id="TEST005",
            entity_type="human",
            public_key="0xPUBKEY123",
            has_met=True
        )
        rel.reliability_score = 85.0
        rel.update_expertise("coding", 90.0)

        # Serialize
        data = rel.to_dict()

        # Deserialize
        rel2 = Relationship.from_dict(data)

        assert rel2.entity_id == rel.entity_id
        assert rel2.entity_type == rel.entity_type
        assert rel2.public_key == rel.public_key
        assert rel2.reliability_score == 85.0
        assert rel2.expertise_scores["coding"] == 90.0


class TestRelationshipStorage:
    """Test RelationshipStorage class"""

    def test_create_and_load(self, temp_qube_dir):
        """Test creating and loading relationships"""
        storage = RelationshipStorage(temp_qube_dir)

        # Create relationship
        rel = storage.create_relationship(
            entity_id="STORE001",
            entity_type="qube",
            has_met=True
        )

        assert rel.entity_id == "STORE001"
        assert len(storage.get_all_relationships()) == 1

        # Save and reload
        storage.save()
        storage2 = RelationshipStorage(temp_qube_dir)

        assert len(storage2.get_all_relationships()) == 1
        loaded_rel = storage2.get_relationship("STORE001")
        assert loaded_rel is not None
        assert loaded_rel.entity_id == "STORE001"

    def test_get_relationships_by_status(self, temp_qube_dir):
        """Test filtering by status"""
        storage = RelationshipStorage(temp_qube_dir)

        rel1 = storage.create_relationship("REL001", has_met=False)
        rel2 = storage.create_relationship("REL002", has_met=True)
        rel3 = storage.create_relationship("REL003", has_met=True)
        rel3.progress_status("friend")
        storage.update_relationship(rel3)

        unmet = storage.get_relationships_by_status("unmet")
        strangers = storage.get_relationships_by_status("stranger")
        friends = storage.get_relationships_by_status("friend")

        assert len(unmet) == 1
        assert len(strangers) == 1
        assert len(friends) == 1

    def test_best_friend_management(self, temp_qube_dir):
        """Test best friend retrieval"""
        storage = RelationshipStorage(temp_qube_dir)

        rel = storage.create_relationship("BEST001", has_met=True)
        rel.is_best_friend = True
        storage.update_relationship(rel)

        best = storage.get_best_friend()
        assert best is not None
        assert best.entity_id == "BEST001"


class TestTrustScorer:
    """Test TrustScorer class"""

    def test_calculate_trust_score_default(self):
        """Test trust score calculation with default weights"""
        scorer = TrustScorer()
        rel = Relationship("TRUST001", has_met=True)

        rel.reliability_score = 80
        rel.honesty_score = 90
        rel.responsiveness_score = 70
        rel.update_expertise("coding", 85)

        score = scorer.calculate_trust_score(rel)

        # Should be weighted average
        assert 70 <= score <= 90
        assert isinstance(score, float)

    def test_calculate_trust_score_with_profile(self):
        """Test trust score with different profiles"""
        scorer = TrustScorer()
        rel = Relationship("TRUST002", has_met=True)

        rel.reliability_score = 80
        rel.honesty_score = 60
        rel.responsiveness_score = 90
        rel.update_expertise("research", 95)

        # Analytical profile (weights expertise high)
        analytical_score = scorer.calculate_trust_score(rel, profile="analytical")

        # Social profile (weights responsiveness high)
        social_score = scorer.calculate_trust_score(rel, profile="social")

        # Scores should differ based on profile
        assert analytical_score != social_score

    def test_apply_penalties(self):
        """Test penalty application"""
        scorer = TrustScorer()
        rel = Relationship("TRUST003", has_met=True)

        rel.reliability_score = 80
        rel.honesty_score = 80
        rel.responsiveness_score = 80

        base_score = scorer.calculate_trust_score(rel)

        # Add warnings
        rel.warnings_received = 2

        penalized_score = scorer.calculate_trust_score(rel)

        assert penalized_score < base_score
        assert penalized_score == base_score - 10  # 2 warnings * 5 points each

    def test_update_trust_component(self):
        """Test updating individual trust components"""
        scorer = TrustScorer()
        rel = Relationship("TRUST004", has_met=True)

        assert rel.reliability_score == 50  # Default

        scorer.update_trust_component(rel, "reliability", 20.0)
        assert rel.reliability_score == 70.0

        scorer.update_trust_component(rel, "reliability", -30.0)
        assert rel.reliability_score == 40.0

        # Test clamping
        scorer.update_trust_component(rel, "reliability", 100.0)
        assert rel.reliability_score == 100.0  # Clamped to max

    def test_update_reliability_from_task(self):
        """Test reliability updates from task outcomes"""
        scorer = TrustScorer()
        rel = Relationship("TRUST005", has_met=True)

        initial = rel.reliability_score

        # Successful task
        scorer.update_reliability(rel, task_succeeded=True, importance=1.0)
        assert rel.reliability_score > initial

        # Failed task
        scorer.update_reliability(rel, task_succeeded=False, importance=1.0)
        # Should decrease more than it increased
        assert rel.reliability_score < initial


class TestRelationshipProgression:
    """Test RelationshipProgressionManager"""

    def test_automatic_progression(self):
        """Test automatic progression based on trust and interactions"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        rel = Relationship("PROG001", has_met=True)
        rel.total_messages_sent = 10
        rel.total_messages_received = 10
        rel.reliability_score = 70
        rel.honesty_score = 70
        rel.responsiveness_score = 70

        # Should progress to acquaintance (threshold: 40 trust, 5 interactions)
        progressed = progression.check_and_progress(rel)

        assert progressed == True
        assert rel.relationship_status == "acquaintance"

    def test_friend_requires_collaboration(self):
        """Test that friend status requires collaboration"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        rel = Relationship("PROG002", has_met=True)
        rel.total_messages_sent = 20
        rel.total_messages_received = 20
        rel.reliability_score = 80
        rel.honesty_score = 80
        rel.responsiveness_score = 80
        rel.overall_trust_score = 80

        # High trust but no collaboration
        progressed = progression.check_and_progress(rel)

        # Should not reach friend status
        assert rel.relationship_status != "friend"

        # Add collaboration
        rel.successful_joint_tasks = 1
        progressed = progression.check_and_progress(rel)

        # Now should reach friend
        assert rel.relationship_status == "friend"

    def test_best_friend_designation(self):
        """Test manual best friend designation"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        rel = Relationship("PROG003", has_met=True)
        rel.total_messages_sent = 100
        rel.total_messages_received = 100
        rel.overall_trust_score = 95

        success = progression.designate_best_friend(rel)

        assert success == True
        assert rel.is_best_friend == True
        assert rel.relationship_status == "best_friend"

    def test_best_friend_demotion(self):
        """Test demoting existing best friend"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        # Create first best friend
        rel1 = Relationship("PROG004", has_met=True)
        rel1.total_messages_sent = 100
        rel1.total_messages_received = 100
        rel1.overall_trust_score = 95
        progression.designate_best_friend(rel1)

        # Create second best friend (should demote first)
        rel2 = Relationship("PROG005", has_met=True)
        rel2.total_messages_sent = 100
        rel2.total_messages_received = 100
        rel2.overall_trust_score = 98

        progression.designate_best_friend(rel2, current_best_friend=rel1)

        assert rel1.is_best_friend == False
        assert rel1.relationship_status == "close_friend"
        assert rel2.is_best_friend == True
        assert rel2.relationship_status == "best_friend"

    def test_handle_interaction(self):
        """Test interaction recording"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        rel = Relationship("PROG006", has_met=False)

        # First interaction
        progression.handle_interaction(rel, is_outgoing=True)

        assert rel.has_met == True
        assert rel.total_messages_sent == 1
        assert rel.relationship_status == "stranger"

        # More interactions
        for _ in range(10):
            progression.handle_interaction(rel, is_outgoing=False)

        assert rel.total_messages_received == 10

    def test_handle_collaboration_outcome(self):
        """Test collaboration outcome recording"""
        scorer = TrustScorer()
        progression = RelationshipProgressionManager(scorer)

        rel = Relationship("PROG007", has_met=True)

        # Successful collaboration
        progression.handle_collaboration_outcome(rel, succeeded=True, importance=1.5)

        assert rel.successful_joint_tasks == 1
        assert rel.total_collaborations == 1
        assert len(rel.shared_experiences) == 1
        assert rel.shared_experiences[0]["sentiment"] == "positive"

        # Failed collaboration
        progression.handle_collaboration_outcome(rel, succeeded=False, importance=1.0)

        assert rel.failed_joint_tasks == 1
        assert rel.total_collaborations == 2
        assert len(rel.shared_experiences) == 2
        assert rel.shared_experiences[1]["sentiment"] == "negative"


class TestSocialDynamicsManager:
    """Test SocialDynamicsManager integration"""

    def test_create_and_get_relationship(self, social_manager):
        """Test relationship creation and retrieval"""
        rel = social_manager.create_relationship(
            entity_id="SOCIAL001",
            entity_type="qube",
            has_met=True
        )

        assert rel.entity_id == "SOCIAL001"

        retrieved = social_manager.get_relationship("SOCIAL001")
        assert retrieved is not None
        assert retrieved.entity_id == "SOCIAL001"

    def test_record_message(self, social_manager):
        """Test message recording with auto-creation"""
        rel = social_manager.record_message(
            entity_id="SOCIAL002",
            is_outgoing=True,
            auto_create=True
        )

        assert rel.entity_id == "SOCIAL002"
        assert rel.total_messages_sent == 1
        assert rel.has_met == True

    def test_record_collaboration(self, social_manager):
        """Test collaboration recording"""
        # Create relationship first
        social_manager.create_relationship("SOCIAL003", has_met=True)

        rel = social_manager.record_collaboration(
            entity_id="SOCIAL003",
            succeeded=True,
            importance=2.0
        )

        assert rel.successful_joint_tasks == 1
        assert rel.total_collaborations == 1

    def test_calculate_trust_score(self, social_manager):
        """Test trust score calculation"""
        rel = social_manager.create_relationship("SOCIAL004", has_met=True)
        rel.reliability_score = 85
        rel.honesty_score = 90
        rel.responsiveness_score = 80
        social_manager.storage.update_relationship(rel)

        score = social_manager.calculate_trust_score("SOCIAL004")

        assert 70 <= score <= 95
        assert rel.overall_trust_score == score

    def test_get_friends(self, social_manager):
        """Test getting all friend-level relationships"""
        # Create mix of relationships
        rel1 = social_manager.create_relationship("SOCIAL005", has_met=False)
        rel2 = social_manager.create_relationship("SOCIAL006", has_met=True)
        rel3 = social_manager.create_relationship("SOCIAL007", has_met=True)
        rel3.progress_status("friend")
        social_manager.storage.update_relationship(rel3)

        friends = social_manager.get_friends()

        assert len(friends) == 1
        assert friends[0].entity_id == "SOCIAL007"

    def test_get_relationship_stats(self, social_manager):
        """Test relationship statistics"""
        # Create various relationships
        social_manager.create_relationship("STAT001", has_met=False)
        social_manager.create_relationship("STAT002", has_met=True)
        rel3 = social_manager.create_relationship("STAT003", has_met=True)
        rel3.progress_status("friend")
        social_manager.storage.update_relationship(rel3)

        stats = social_manager.get_relationship_stats()

        assert stats["total_relationships"] == 3
        assert stats["status_breakdown"]["unmet"] == 1
        assert stats["status_breakdown"]["stranger"] == 1
        assert stats["status_breakdown"]["friend"] == 1

    def test_add_third_party_opinion(self, social_manager):
        """Test third-party reputation"""
        # Create relationship (can be unmet)
        rel = social_manager.get_or_create_relationship("SOCIAL008", has_met=False)

        social_manager.add_third_party_opinion(
            subject_id="SOCIAL008",
            observer_id="OBSERVER123",
            trust_score=85.0,
            relationship_type="friend"
        )

        rel = social_manager.get_relationship("SOCIAL008")
        assert "OBSERVER123" in rel.third_party_reputation
        assert rel.third_party_reputation["OBSERVER123"]["trust_score"] == 85.0

    def test_persistence(self, temp_qube_dir):
        """Test that relationships persist across manager instances"""
        # Create manager and relationships
        manager1 = SocialDynamicsManager(temp_qube_dir)
        manager1.create_relationship("PERSIST001", has_met=True)
        manager1.record_message("PERSIST001", is_outgoing=True)

        # Create new manager instance
        manager2 = SocialDynamicsManager(temp_qube_dir)

        rel = manager2.get_relationship("PERSIST001")
        assert rel is not None
        assert rel.total_messages_sent == 1
