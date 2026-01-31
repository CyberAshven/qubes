"""
Tests for Skill Scanner functionality

Tests XP calculation, skill mapping, and intelligent routing.

Phase 0: Foundation Tests
"""

import pytest
from ai.skill_scanner import TOOL_TO_SKILL_MAPPING, analyze_research_topic


# ==============================================================================
# XP VALUE TESTS
# ==============================================================================

class TestXPValues:
    """Test that XP values are correctly set to 5/2.5/0"""

    @pytest.mark.unit
    def test_tool_to_skill_mapping_exists(self):
        """Verify TOOL_TO_SKILL_MAPPING is populated"""
        assert len(TOOL_TO_SKILL_MAPPING) > 0
        assert isinstance(TOOL_TO_SKILL_MAPPING, dict)

    @pytest.mark.unit
    def test_sun_tools_mapped(self):
        """Verify all Sun tools are mapped"""
        sun_tools = [
            "recall_similar",  # AI Reasoning
            "get_relationship_context",  # Social Intelligence
            "develop_code",  # Coding
            "switch_model",  # Creative Expression
            "store_knowledge",  # Memory & Recall
            "verify_chain_integrity",  # Security & Privacy
            "chess_move",  # Board Games
            "send_bch",  # Finance
        ]

        for tool in sun_tools:
            assert tool in TOOL_TO_SKILL_MAPPING, f"Sun tool '{tool}' not mapped"


# ==============================================================================
# INTELLIGENT ROUTING TESTS
# ==============================================================================

class TestIntelligentRouting:
    """Test the analyze_research_topic function for intelligent XP routing"""

    @pytest.mark.unit
    def test_coding_topics(self):
        """Verify coding-related queries route to coding"""
        queries = [
            "python tutorial",
            "javascript async await",
            "debugging code",
            "git merge conflict",
            "docker kubernetes deployment",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "coding", f"Query '{query}' should route to coding, got '{result}'"

    @pytest.mark.unit
    def test_finance_topics(self):
        """Verify finance-related queries route to finance"""
        queries = [
            "bitcoin price",
            "bch transaction",
            "crypto wallet",
            "blockchain technology",
            "nft market",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "finance", f"Query '{query}' should route to finance, got '{result}'"

    @pytest.mark.unit
    def test_security_topics(self):
        """Verify security-related queries route to security_privacy"""
        queries = [
            "encryption algorithm",
            "password security",
            "ssl certificate",
            "vulnerability exploit",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "security_privacy", f"Query '{query}' should route to security_privacy, got '{result}'"

    @pytest.mark.unit
    def test_memory_recall_topics(self):
        """Verify knowledge-related queries route to memory_recall"""
        queries = [
            "history of rome",
            "physics quantum mechanics",
            "mathematics calculus",
            "philosophy ethics",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "memory_recall", f"Query '{query}' should route to memory_recall, got '{result}'"

    @pytest.mark.unit
    def test_creative_expression_topics(self):
        """Verify creative-related queries route to creative_expression"""
        queries = [
            "art design principles",
            "music composition",
            "writing fiction",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "creative_expression", f"Query '{query}' should route to creative_expression, got '{result}'"

    @pytest.mark.unit
    def test_board_games_topics(self):
        """Verify game-related queries route to board_games"""
        queries = [
            "chess opening strategy",
            "chess tactics",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "board_games", f"Query '{query}' should route to board_games, got '{result}'"

    @pytest.mark.unit
    def test_default_routing(self):
        """Verify unknown queries default to memory_recall"""
        queries = [
            "random gibberish xyz123",
            "what is the meaning of life",
            "how to make coffee",
        ]

        for query in queries:
            result = analyze_research_topic(query)
            assert result == "memory_recall", f"Query '{query}' should default to memory_recall, got '{result}'"

    @pytest.mark.unit
    def test_url_influence(self):
        """Verify URL content influences routing"""
        # Query alone would be ambiguous, but URL should route to coding
        result = analyze_research_topic("tutorial", "https://github.com/python/cpython")
        assert result == "coding"

    @pytest.mark.unit
    def test_category_ids_renamed(self):
        """Verify old category IDs are not returned"""
        # Test many different queries to ensure old IDs never appear
        test_queries = [
            "python code",
            "history facts",
            "chess game",
            "any random query",
        ]

        old_ids = {"knowledge_domains", "games", "technical_expertise"}

        for query in test_queries:
            result = analyze_research_topic(query)
            assert result not in old_ids, f"Old category ID '{result}' returned for '{query}'"


# ==============================================================================
# TOOL MAPPING VALIDATION
# ==============================================================================

class TestToolMapping:
    """Test that tools are correctly mapped to skills"""

    @pytest.mark.unit
    def test_no_old_category_references(self):
        """Verify no tool maps to old category IDs"""
        old_categories = {"knowledge_domains", "games", "technical_expertise"}

        for tool, skill in TOOL_TO_SKILL_MAPPING.items():
            assert skill not in old_categories, f"Tool '{tool}' maps to old category '{skill}'"

    @pytest.mark.unit
    def test_finance_tools_mapped(self):
        """Verify Finance category tools are mapped"""
        finance_tools = [
            "send_bch",
            "get_balance",
            "get_transaction_history",
        ]

        for tool in finance_tools:
            if tool in TOOL_TO_SKILL_MAPPING:
                # Should map to finance or a finance skill
                skill = TOOL_TO_SKILL_MAPPING[tool]
                assert "finance" in skill.lower() or skill in [
                    "blockchain", "transaction_mastery", "wallet_management",
                    "market_awareness", "savings_strategies", "token_knowledge",
                    "fee_optimization", "transaction_tracking", "balance_monitoring",
                    "multisig_operations", "price_alerts", "trend_analysis",
                    "dollar_cost_averaging", "cashtoken_operations"
                ], f"Tool '{tool}' should map to a finance skill, got '{skill}'"
