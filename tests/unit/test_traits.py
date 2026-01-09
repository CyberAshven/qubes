"""
Tests for Trait Detection System

Tests:
- TraitDefinition loading from YAML
- TraitScore dataclass serialization
- TraitDetector scoring algorithm
- Trait integration with Relationship
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.trait_definitions import (
    TraitDefinition,
    load_trait_definitions,
    WARNING_TRAITS,
)
from relationships.trait_detection import (
    TraitScore,
    TraitDetector,
    DIFFICULTY_EVIDENCE_MULTIPLIERS,
    DIFFICULTY_GROWTH_RATES,
)


class TestTraitDefinition:
    """Test TraitDefinition class"""

    def test_create_trait_definition(self):
        """Test creating a trait definition"""
        trait = TraitDefinition(
            name="supportive",
            category="social",
            description="Provides help and encouragement",
            icon="🤝",
            color="#22c55e",
            polarity="positive",
            primary_metrics=["support", "empowerment"],
            supporting_metrics=["patience", "understanding"],
            negative_indicators=["dismissiveness"],
            confidence_threshold=65.0,
            evidence_required=3,
            opposite_trait="dismissive",
        )

        assert trait.name == "supportive"
        assert trait.category == "social"
        assert trait.polarity == "positive"
        assert "support" in trait.primary_metrics
        assert trait.confidence_threshold == 65.0
        assert trait.is_warning == False

    def test_warning_trait(self):
        """Test creating a warning trait"""
        trait = TraitDefinition(
            name="manipulative",
            category="warning",
            description="Uses others for personal gain",
            icon="🎭",
            color="#ef4444",
            polarity="warning",
            primary_metrics=["manipulation"],
            is_warning=True,
        )

        assert trait.is_warning == True
        assert trait.polarity == "warning"

    def test_to_dict(self):
        """Test serialization to dict"""
        trait = TraitDefinition(
            name="reliable",
            category="reliability",
            description="Follows through",
            icon="🎯",
            color="#22c55e",
            polarity="positive",
        )

        data = trait.to_dict()

        assert data["name"] == "reliable"
        assert data["category"] == "reliability"
        assert "primary_metrics" in data
        assert "is_warning" in data

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "category": "social",
            "description": "Test trait",
            "icon": "🔵",
            "color": "#000000",
            "polarity": "neutral",
            "primary_metrics": ["engagement"],
            "confidence_threshold": 70.0,
        }

        trait = TraitDefinition.from_dict("test_trait", data)

        assert trait.name == "test_trait"
        assert trait.category == "social"
        assert trait.confidence_threshold == 70.0

    def test_load_trait_definitions(self):
        """Test loading traits from YAML config"""
        traits = load_trait_definitions()

        # Should load traits from config/trait_definitions.yaml
        assert len(traits) > 0

        # Check some expected traits exist
        assert "supportive" in traits or "reliable" in traits or "warm" in traits

    def test_warning_traits_list(self):
        """Test WARNING_TRAITS constant"""
        assert "manipulative" in WARNING_TRAITS
        assert "gaslighting" in WARNING_TRAITS
        assert "toxic" in WARNING_TRAITS


class TestTraitScore:
    """Test TraitScore dataclass"""

    def test_create_trait_score(self):
        """Test creating a trait score"""
        score = TraitScore(
            score=75.5,
            evidence_count=5,
            first_detected=1704067200,
            last_updated=1704153600,
            consistency=85.0,
            volatility=15.0,
            trend="rising",
            source="metric_derived",
            is_confident=True,
        )

        assert score.score == 75.5
        assert score.evidence_count == 5
        assert score.trend == "rising"
        assert score.is_confident == True

    def test_default_values(self):
        """Test default values"""
        score = TraitScore()

        assert score.score == 0.0
        assert score.evidence_count == 0
        assert score.trend == "stable"
        assert score.source == "metric_derived"
        assert score.is_confident == False

    def test_to_dict(self):
        """Test serialization"""
        score = TraitScore(score=60.0, evidence_count=3, trend="stable")
        data = score.to_dict()

        assert data["score"] == 60.0
        assert data["evidence_count"] == 3
        assert "volatility" in data

    def test_from_dict(self):
        """Test deserialization"""
        data = {
            "score": 80.0,
            "evidence_count": 4,
            "first_detected": 1704067200,
            "last_updated": 1704153600,
            "consistency": 90.0,
            "volatility": 10.0,
            "trend": "falling",
            "source": "both",
            "is_confident": True,
        }

        score = TraitScore.from_dict(data)

        assert score.score == 80.0
        assert score.trend == "falling"
        assert score.source == "both"


class TestTraitDetector:
    """Test TraitDetector class"""

    @pytest.fixture
    def mock_relationship(self):
        """Create a mock relationship with metrics"""
        rel = MagicMock()
        # Core Trust Metrics
        rel.honesty = 70
        rel.reliability = 75
        rel.support = 80
        rel.loyalty = 65
        rel.respect = 70
        # Social Metrics - Positive
        rel.friendship = 60
        rel.affection = 50
        rel.engagement = 75
        rel.depth = 65
        rel.humor = 55
        rel.understanding = 70
        rel.compatibility = 65
        rel.admiration = 55
        rel.warmth = 65
        rel.openness = 60
        rel.patience = 70
        rel.empowerment = 55
        rel.responsiveness = 80
        rel.expertise = 60
        # Social Metrics - Negative
        rel.antagonism = 10
        rel.resentment = 5
        rel.annoyance = 15
        rel.distrust = 10
        rel.rivalry = 5
        rel.tension = 10
        rel.manipulation = 5
        rel.dismissiveness = 10
        rel.condescension = 5
        rel.betrayal = 0
        # Behavioral Metrics
        rel.verbosity = 60
        rel.punctuality = 75
        rel.emotional_stability = 70
        rel.directness = 65
        rel.energy_level = 60
        rel.humor_style = 50
        # Trait tracking
        rel.trait_scores = {}
        rel.trait_evolution = []
        return rel

    def test_create_detector_default(self):
        """Test creating detector with defaults"""
        detector = TraitDetector()

        assert detector.difficulty == "long"
        assert detector.trust_personality == "balanced"
        assert len(detector.definitions) > 0

    def test_create_detector_with_difficulty(self):
        """Test detector with different difficulty levels"""
        quick = TraitDetector(difficulty="quick")
        extreme = TraitDetector(difficulty="extreme")

        assert quick.evidence_multiplier == DIFFICULTY_EVIDENCE_MULTIPLIERS["quick"]
        assert extreme.evidence_multiplier == DIFFICULTY_EVIDENCE_MULTIPLIERS["extreme"]
        assert quick.growth_rate > extreme.growth_rate

    def test_calculate_raw_score(self, mock_relationship):
        """Test raw score calculation from metrics"""
        detector = TraitDetector()

        # supportive trait uses support, empowerment, patience, understanding
        if "supportive" in detector.definitions:
            score = detector._calculate_raw_score("supportive", mock_relationship)
            assert 0 <= score <= 100

    def test_detect_traits(self, mock_relationship):
        """Test full trait detection"""
        detector = TraitDetector(difficulty="quick")  # Quick for faster confidence
        evaluation = {"deltas": {}}

        traits = detector.detect_traits(mock_relationship, evaluation)

        # Should detect some traits based on metrics
        assert isinstance(traits, dict)

        # All returned traits should be TraitScore objects
        for name, score in traits.items():
            assert isinstance(score, TraitScore)
            assert 0 <= score.score <= 100

    def test_detect_traits_with_ai_detection(self, mock_relationship):
        """Test trait detection with AI-detected traits"""
        detector = TraitDetector(difficulty="quick")
        evaluation = {"deltas": {}}
        ai_detected = ["supportive", "reliable"]
        ai_evidence = {"supportive": "Very helpful in conversation"}

        traits = detector.detect_traits(
            mock_relationship,
            evaluation,
            ai_detected=ai_detected,
            ai_evidence=ai_evidence,
        )

        # AI-detected traits should get a boost
        if "supportive" in traits:
            assert traits["supportive"].source in ["ai_direct", "both"]

    def test_get_confident_traits(self, mock_relationship):
        """Test getting confident traits"""
        detector = TraitDetector(difficulty="quick")

        # Create some trait scores
        trait_scores = {
            "supportive": TraitScore(score=75, evidence_count=5, is_confident=True),
            "reliable": TraitScore(score=80, evidence_count=4, is_confident=True),
            "verbose": TraitScore(score=45, evidence_count=2, is_confident=False),
        }

        confident = detector.get_confident_traits(trait_scores)

        assert "supportive" in confident
        assert "reliable" in confident
        assert "verbose" not in confident

    def test_get_warning_traits(self, mock_relationship):
        """Test getting warning traits"""
        detector = TraitDetector()

        trait_scores = {
            "manipulative": TraitScore(score=50, evidence_count=2, is_confident=False),
            "supportive": TraitScore(score=80, evidence_count=5, is_confident=True),
        }

        warnings = detector.get_warning_traits(trait_scores)

        # manipulative should show as warning even below threshold (score >= 40)
        assert "manipulative" in warnings
        assert "supportive" not in warnings

    def test_get_trait_changes(self, mock_relationship):
        """Test calculating trait changes"""
        detector = TraitDetector()

        old_traits = {
            "supportive": {"score": 60, "evidence_count": 3},
            "reliable": {"score": 70, "evidence_count": 4},
            "verbose": {"score": 50, "evidence_count": 2},
        }

        new_traits = {
            "supportive": TraitScore(score=75, evidence_count=4),  # Strengthened
            "reliable": TraitScore(score=68, evidence_count=5),   # Stable
            "warm": TraitScore(score=55, evidence_count=1),       # New
            # verbose removed (below threshold)
        }

        changes = detector.get_trait_changes(old_traits, new_traits, threshold=3.0)

        assert "warm" in changes["assigned"]
        assert "supportive" in changes["strengthened"]
        assert "verbose" in changes["removed"]
        assert "reliable" not in changes["strengthened"]  # Only 2 point change

    def test_difficulty_scaling(self, mock_relationship):
        """Test that difficulty affects evidence requirements"""
        quick_detector = TraitDetector(difficulty="quick")
        extreme_detector = TraitDetector(difficulty="extreme")

        if "supportive" in quick_detector.definitions:
            quick_req = quick_detector._get_scaled_evidence_required("supportive")
            extreme_req = extreme_detector._get_scaled_evidence_required("supportive")

            # Extreme should require more evidence
            assert extreme_req > quick_req

    def test_warning_trait_threshold(self):
        """Test that warning traits have higher confidence threshold"""
        detector = TraitDetector()

        if "manipulative" in detector.definitions:
            warning_threshold = detector._get_confidence_threshold("manipulative")
            assert warning_threshold >= 75.0  # Warning traits need higher threshold

        if "supportive" in detector.definitions:
            normal_threshold = detector._get_confidence_threshold("supportive")
            assert normal_threshold < 75.0  # Normal traits have lower threshold


class TestTraitIntegration:
    """Test trait integration with Relationship class"""

    @pytest.fixture
    def temp_qube_dir(self):
        """Create temporary Qube directory"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_relationship_trait_fields(self):
        """Test that Relationship has trait fields"""
        from relationships.relationship import Relationship

        rel = Relationship(entity_id="TEST001", has_met=True)

        # Check trait fields exist
        assert hasattr(rel, 'trait_scores')
        assert hasattr(rel, 'trait_evolution')
        assert hasattr(rel, 'manual_trait_overrides')

        # Check default values
        assert rel.trait_scores == {}
        assert rel.trait_evolution == []
        assert rel.manual_trait_overrides == {}

    def test_relationship_trait_serialization(self):
        """Test trait data persists through serialization"""
        from relationships.relationship import Relationship

        rel = Relationship(entity_id="TEST002", has_met=True)

        # Add trait data
        rel.trait_scores = {
            "supportive": {
                "score": 75.0,
                "evidence_count": 4,
                "first_detected": 1704067200,
                "last_updated": 1704153600,
                "consistency": 85.0,
                "volatility": 15.0,
                "trend": "rising",
                "source": "metric_derived",
                "is_confident": True,
            }
        }
        rel.trait_evolution = [
            {"timestamp": 1704153600, "trait": "supportive", "old_score": 60, "new_score": 75}
        ]
        rel.manual_trait_overrides = {"verbose": False}

        # Serialize
        data = rel.to_dict()

        # Deserialize
        rel2 = Relationship.from_dict(data)

        # Verify trait data persists
        assert "supportive" in rel2.trait_scores
        assert rel2.trait_scores["supportive"]["score"] == 75.0
        assert len(rel2.trait_evolution) == 1
        assert rel2.manual_trait_overrides.get("verbose") == False


class TestTraitDetectorEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_relationship(self):
        """Test detection with minimal relationship data"""
        detector = TraitDetector()

        rel = MagicMock()
        rel.trait_scores = {}
        rel.trait_evolution = []

        # Set all metrics to 0
        for attr in ['honesty', 'reliability', 'support', 'loyalty', 'respect',
                     'friendship', 'affection', 'engagement', 'depth', 'humor',
                     'understanding', 'warmth', 'openness', 'patience', 'empowerment',
                     'responsiveness', 'expertise', 'antagonism', 'resentment',
                     'annoyance', 'distrust', 'manipulation', 'dismissiveness',
                     'condescension', 'betrayal', 'verbosity', 'punctuality',
                     'emotional_stability', 'directness', 'energy_level', 'humor_style']:
            setattr(rel, attr, 0)

        evaluation = {"deltas": {}}
        traits = detector.detect_traits(rel, evaluation)

        # Should return empty or minimal traits (nothing above threshold)
        assert isinstance(traits, dict)

    def test_unknown_trait_name(self):
        """Test handling of unknown trait names"""
        detector = TraitDetector()

        # These should not raise errors
        score = detector._calculate_raw_score("nonexistent_trait", MagicMock())
        assert score == 0.0

        threshold = detector._get_confidence_threshold("nonexistent_trait")
        assert threshold == 65.0  # Default

        evidence = detector._get_scaled_evidence_required("nonexistent_trait")
        assert evidence == 4  # Default

    def test_trait_decay(self):
        """Test trait decay over time"""
        detector = TraitDetector(difficulty="quick")  # 30 day half-life

        old_score = TraitScore(score=80.0, last_updated=0)

        # 30 days = half-life, should decay to ~40
        decayed = detector._apply_decay(old_score, days_since_update=30)
        assert 35 <= decayed <= 45  # ~40 with some tolerance

        # 60 days = 2 half-lives, should decay to ~20
        decayed = detector._apply_decay(old_score, days_since_update=60)
        assert 15 <= decayed <= 25

    def test_volatility_calculation(self):
        """Test volatility calculation from score history"""
        detector = TraitDetector()

        rel = MagicMock()
        rel.trait_evolution = [
            {"trait": "supportive", "new_score": 60},
            {"trait": "supportive", "new_score": 65},
            {"trait": "supportive", "new_score": 70},
            {"trait": "supportive", "new_score": 68},
        ]

        volatility = detector._calculate_volatility("supportive", rel, 72)

        # Low volatility expected (scores are close together)
        assert 0 <= volatility <= 100

    def test_trend_determination(self):
        """Test trend calculation"""
        detector = TraitDetector()

        old_score = TraitScore(score=50)

        assert detector._determine_trend(old_score, 60) == "rising"
        assert detector._determine_trend(old_score, 40) == "falling"
        assert detector._determine_trend(old_score, 52) == "stable"
        assert detector._determine_trend(None, 50) == "stable"
