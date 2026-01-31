"""
Tests for Skill Definitions

Tests category structure, Finance category, and category renames.

Phase 0: Foundation Tests
"""

import pytest
from utils.skill_definitions import generate_all_skills


# ==============================================================================
# CATEGORY RENAME TESTS
# ==============================================================================

class TestCategoryRenames:
    """Test that category IDs use new names"""

    @pytest.fixture
    def all_skills(self):
        """Generate all skills once for test reuse"""
        return generate_all_skills()

    @pytest.mark.unit
    def test_new_category_ids_exist(self, all_skills):
        """Verify new category IDs are present"""
        categories = set(s["category"] for s in all_skills)

        assert "memory_recall" in categories, "memory_recall category missing"
        assert "board_games" in categories, "board_games category missing"
        assert "coding" in categories, "coding category missing"
        assert "finance" in categories, "finance category missing"

    @pytest.mark.unit
    def test_old_category_ids_removed(self, all_skills):
        """Verify old category IDs are NOT present"""
        categories = set(s["category"] for s in all_skills)

        assert "knowledge_domains" not in categories, "Old 'knowledge_domains' ID still exists"
        assert "games" not in categories, "Old 'games' ID still exists"
        assert "technical_expertise" not in categories, "Old 'technical_expertise' ID still exists"

    @pytest.mark.unit
    def test_all_eight_categories_exist(self, all_skills):
        """Verify all 8 categories exist"""
        categories = set(s["category"] for s in all_skills)

        expected_categories = {
            "ai_reasoning",
            "social_intelligence",
            "coding",
            "creative_expression",
            "memory_recall",
            "security_privacy",
            "board_games",
            "finance",
        }

        assert categories == expected_categories, f"Categories mismatch: {categories}"


# ==============================================================================
# FINANCE CATEGORY TESTS
# ==============================================================================

class TestFinanceCategory:
    """Test the Finance category has all required skills"""

    @pytest.fixture
    def finance_skills(self):
        """Get only Finance category skills"""
        all_skills = generate_all_skills()
        return [s for s in all_skills if s["category"] == "finance"]

    @pytest.mark.unit
    def test_finance_skill_count(self, finance_skills):
        """Verify Finance has exactly 14 skills (1 sun + 5 planets + 8 moons)"""
        assert len(finance_skills) == 14, f"Expected 14 finance skills, got {len(finance_skills)}"

    @pytest.mark.unit
    def test_finance_hierarchy(self, finance_skills):
        """Verify Finance has correct hierarchy"""
        suns = [s for s in finance_skills if s["nodeType"] == "sun"]
        planets = [s for s in finance_skills if s["nodeType"] == "planet"]
        moons = [s for s in finance_skills if s["nodeType"] == "moon"]

        assert len(suns) == 1, f"Expected 1 sun, got {len(suns)}"
        assert len(planets) == 5, f"Expected 5 planets, got {len(planets)}"
        assert len(moons) == 8, f"Expected 8 moons, got {len(moons)}"

    @pytest.mark.unit
    def test_finance_sun_exists(self, finance_skills):
        """Verify Finance sun skill exists with correct ID"""
        suns = [s for s in finance_skills if s["nodeType"] == "sun"]
        assert len(suns) == 1
        assert suns[0]["id"] == "finance"
        assert suns[0]["name"] == "Finance"

    @pytest.mark.unit
    def test_finance_planets_exist(self, finance_skills):
        """Verify all Finance planets exist"""
        planets = [s for s in finance_skills if s["nodeType"] == "planet"]
        planet_ids = {s["id"] for s in planets}

        expected_planets = {
            "transaction_mastery",
            "wallet_management",
            "market_awareness",
            "savings_strategies",
            "token_knowledge",
        }

        assert planet_ids == expected_planets, f"Planets mismatch: {planet_ids}"

    @pytest.mark.unit
    def test_finance_moons_exist(self, finance_skills):
        """Verify all Finance moons exist"""
        moons = [s for s in finance_skills if s["nodeType"] == "moon"]
        moon_ids = {s["id"] for s in moons}

        expected_moons = {
            "fee_optimization",
            "transaction_tracking",
            "balance_monitoring",
            "multisig_operations",
            "price_alerts",
            "trend_analysis",
            "dollar_cost_averaging",
            "cashtoken_operations",
        }

        assert moon_ids == expected_moons, f"Moons mismatch: {moon_ids}"

    @pytest.mark.unit
    def test_finance_parent_relationships(self, finance_skills):
        """Verify Finance skills have correct parent relationships"""
        skill_map = {s["id"]: s for s in finance_skills}

        # Planets should have finance as parent
        for s in finance_skills:
            if s["nodeType"] == "planet":
                assert s["parentSkill"] == "finance", f"Planet {s['id']} has wrong parent"

        # Moons should have a planet as parent
        planet_ids = {s["id"] for s in finance_skills if s["nodeType"] == "planet"}
        for s in finance_skills:
            if s["nodeType"] == "moon":
                assert s["parentSkill"] in planet_ids, f"Moon {s['id']} has invalid parent {s['parentSkill']}"


# ==============================================================================
# SUN TOOL REWARD TESTS
# ==============================================================================

class TestSunToolRewards:
    """Test that each Sun has a tool reward"""

    @pytest.fixture
    def sun_skills(self):
        """Get only Sun skills"""
        all_skills = generate_all_skills()
        return [s for s in all_skills if s["nodeType"] == "sun"]

    @pytest.mark.unit
    def test_all_suns_have_tool_rewards(self, sun_skills):
        """Verify each sun has a toolCallReward"""
        for sun in sun_skills:
            assert "toolCallReward" in sun, f"Sun {sun['id']} missing toolCallReward"
            assert sun["toolCallReward"] is not None, f"Sun {sun['id']} has null toolCallReward"
            assert sun["toolCallReward"] != "", f"Sun {sun['id']} has empty toolCallReward"

    @pytest.mark.unit
    def test_finance_sun_tool_reward(self, sun_skills):
        """Verify Finance sun has send_bch as tool reward"""
        finance_sun = next((s for s in sun_skills if s["id"] == "finance"), None)
        assert finance_sun is not None, "Finance sun not found"
        assert finance_sun["toolCallReward"] == "send_bch", f"Finance sun has wrong tool: {finance_sun['toolCallReward']}"
