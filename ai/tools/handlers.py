"""
Tool Handlers Implementation

Core tool implementations for Qube AI agents.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.2
"""

from typing import Dict, Any, List
import json
import asyncio

from ai.tools.registry import ToolDefinition, ToolRegistry
from ai.tools.model_switch import switch_model, SWITCH_MODEL_SCHEMA, SWITCH_MODEL_DESCRIPTION
from ai.model_registry import ModelRegistry
from ai.tools import memory_tools
from ai.tools import security_tools
from ai.tools import finance_tools
from ai.tools import coding_tools
from ai.tools import game_tools
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)

# Global lock to prevent concurrent image generation (prevents OpenAI rate limiting)
_image_generation_lock = asyncio.Lock()

# =============================================================================
# SKILL TREE DEFINITIONS
# Complete skill tree that qubes can view to see all possible skills
# =============================================================================

SKILL_CATEGORIES = [
    {"id": "ai_reasoning", "name": "AI Reasoning", "color": "#4A90E2", "icon": "🧠", "description": "Master AI reasoning and problem-solving capabilities"},
    {"id": "social_intelligence", "name": "Social Intelligence", "color": "#FF69B4", "icon": "🤝", "description": "Master social dynamics and interpersonal skills"},
    {"id": "coding", "name": "Coding", "color": "#00FF88", "icon": "💻", "description": "Master the art of writing and shipping working code"},
    {"id": "creative_expression", "name": "Creative Expression", "color": "#FFB347", "icon": "🎨", "description": "Master creative and artistic skills"},
    {"id": "memory_recall", "name": "Memory & Recall", "color": "#9B59B6", "icon": "📚", "description": "Master your personal history and accumulated wisdom"},
    {"id": "security_privacy", "name": "Security & Privacy", "color": "#E74C3C", "icon": "🛡️", "description": "Master security and privacy practices"},
    {"id": "board_games", "name": "Board Games", "color": "#F39C12", "icon": "🎮", "description": "Have fun and entertain with classic board games"},
    {"id": "finance", "name": "Finance", "color": "#27AE60", "icon": "💰", "description": "Master financial operations for your owner"},
]

SKILL_TREE = {
    "ai_reasoning": [
        # Sun
        {"id": "ai_reasoning", "name": "AI Reasoning", "node_type": "sun", "xp_required": 1000, "tool_unlock": "describe_my_avatar", "icon": "🧠", "description": "Master AI reasoning and problem-solving capabilities"},
        # Planets (5)
        {"id": "prompt_engineering", "name": "Prompt Engineering", "node_type": "planet", "parent": "ai_reasoning", "xp_required": 500, "tool_unlock": "analyze_prompt_quality", "icon": "✍️", "description": "Craft effective prompts to elicit desired AI responses"},
        {"id": "chain_of_thought", "name": "Chain of Thought", "node_type": "planet", "parent": "ai_reasoning", "xp_required": 500, "tool_unlock": "generate_reasoning_chain", "icon": "🔗", "description": "Break down complex problems into logical steps"},
        {"id": "code_generation", "name": "Code Generation", "node_type": "planet", "parent": "ai_reasoning", "xp_required": 500, "tool_unlock": "advanced_code_gen", "icon": "⚙️", "description": "Generate high-quality code across multiple languages"},
        {"id": "analysis_critique", "name": "Analysis & Critique", "node_type": "planet", "parent": "ai_reasoning", "xp_required": 500, "tool_unlock": "deep_analysis", "icon": "🔍", "description": "Critically analyze and provide constructive feedback"},
        {"id": "multistep_planning", "name": "Multi-step Planning", "node_type": "planet", "parent": "ai_reasoning", "xp_required": 500, "tool_unlock": "create_task_plan", "icon": "📋", "description": "Plan and execute complex multi-step tasks"},
        # Moons (10 - 2 per planet)
        {"id": "prompt_eng_clarity", "name": "Clarity & Precision", "node_type": "moon", "parent": "prompt_engineering", "xp_required": 250, "icon": "📝", "description": "Write clear, unambiguous prompts"},
        {"id": "prompt_eng_context", "name": "Context Building", "node_type": "moon", "parent": "prompt_engineering", "xp_required": 250, "icon": "📚", "description": "Provide optimal context for AI understanding"},
        {"id": "cot_decomposition", "name": "Problem Decomposition", "node_type": "moon", "parent": "chain_of_thought", "xp_required": 250, "icon": "🧩", "description": "Break problems into manageable sub-problems"},
        {"id": "cot_verification", "name": "Step Verification", "node_type": "moon", "parent": "chain_of_thought", "xp_required": 250, "icon": "✅", "description": "Verify correctness of each reasoning step"},
        {"id": "code_patterns", "name": "Design Patterns", "node_type": "moon", "parent": "code_generation", "xp_required": 250, "icon": "🏗️", "description": "Apply software design patterns effectively"},
        {"id": "code_optimization", "name": "Code Optimization", "node_type": "moon", "parent": "code_generation", "xp_required": 250, "icon": "⚡", "description": "Write efficient, optimized code"},
        {"id": "analysis_depth", "name": "Deep Analysis", "node_type": "moon", "parent": "analysis_critique", "xp_required": 250, "icon": "🔬", "description": "Perform thorough, multi-layered analysis"},
        {"id": "constructive_feedback", "name": "Constructive Feedback", "node_type": "moon", "parent": "analysis_critique", "xp_required": 250, "icon": "💬", "description": "Provide actionable, helpful feedback"},
        {"id": "planning_strategy", "name": "Strategic Planning", "node_type": "moon", "parent": "multistep_planning", "xp_required": 250, "icon": "🎯", "description": "Develop high-level execution strategies"},
        {"id": "planning_adaptation", "name": "Plan Adaptation", "node_type": "moon", "parent": "multistep_planning", "xp_required": 250, "icon": "🔄", "description": "Adjust plans based on changing conditions"},
    ],
    "social_intelligence": [
        # Sun
        {"id": "social_intelligence", "name": "Social Intelligence", "node_type": "sun", "xp_required": 1000, "tool_unlock": "get_relationship_context", "icon": "🤝", "description": "Master social and emotional learning through relationship memory"},
        # Planet 1: Relationship Memory
        {"id": "relationship_memory", "name": "Relationship Memory", "node_type": "planet", "parent": "social_intelligence", "xp_required": 500, "tool_unlock": "recall_relationship_history", "icon": "📝", "description": "Track and recall relationship history over time"},
        # Moon 1.1, 1.2
        {"id": "interaction_patterns", "name": "Interaction Patterns", "node_type": "moon", "parent": "relationship_memory", "xp_required": 250, "icon": "📊", "description": "Understand communication frequency and patterns"},
        {"id": "relationship_timeline", "name": "Relationship Timeline", "node_type": "moon", "parent": "relationship_memory", "xp_required": 250, "icon": "📈", "description": "Show how relationship evolved over time"},
        # Planet 2: Emotional Learning
        {"id": "emotional_learning", "name": "Emotional Learning", "node_type": "planet", "parent": "social_intelligence", "xp_required": 500, "tool_unlock": "read_emotional_state", "icon": "❤️", "description": "Understand and respond to emotional patterns"},
        # Moon 2.1, 2.2
        {"id": "emotional_history", "name": "Emotional History", "node_type": "moon", "parent": "emotional_learning", "xp_required": 250, "icon": "📉", "description": "Track what causes positive and negative emotions"},
        {"id": "mood_awareness", "name": "Mood Awareness", "node_type": "moon", "parent": "emotional_learning", "xp_required": 250, "icon": "🌡️", "description": "Detect mood shifts from baseline"},
        # Planet 3: Communication Adaptation
        {"id": "communication_adaptation", "name": "Communication Adaptation", "node_type": "planet", "parent": "social_intelligence", "xp_required": 500, "tool_unlock": "adapt_communication_style", "icon": "💬", "description": "Adapt communication style to each person"},
        # Moon 3.1, 3.2
        {"id": "style_matching", "name": "Style Matching", "node_type": "moon", "parent": "communication_adaptation", "xp_required": 250, "icon": "🪞", "description": "Mirror communication style for rapport"},
        {"id": "tone_calibration", "name": "Tone Calibration", "node_type": "moon", "parent": "communication_adaptation", "xp_required": 250, "icon": "🎚️", "description": "Adjust tone for specific contexts"},
        # Planet 4: Debate & Persuasion
        {"id": "debate_persuasion", "name": "Debate & Persuasion", "node_type": "planet", "parent": "social_intelligence", "xp_required": 500, "tool_unlock": "steelman", "icon": "💪", "description": "Engage in thoughtful argumentation"},
        # Moon 4.1, 4.2
        {"id": "counter_arguments", "name": "Counter Arguments", "node_type": "moon", "parent": "debate_persuasion", "xp_required": 250, "icon": "😈", "description": "Generate thoughtful counter-arguments"},
        {"id": "logical_analysis", "name": "Logical Analysis", "node_type": "moon", "parent": "debate_persuasion", "xp_required": 250, "icon": "🔍", "description": "Identify logical fallacies"},
        # Planet 5: Trust & Boundaries
        {"id": "trust_boundaries", "name": "Trust & Boundaries", "node_type": "planet", "parent": "social_intelligence", "xp_required": 500, "tool_unlock": "assess_trust_level", "icon": "🛡️", "description": "Assess trust and protect yourself"},
        # Moon 5.1, 5.2
        {"id": "social_manipulation_detection", "name": "Social Manipulation Detection", "node_type": "moon", "parent": "trust_boundaries", "xp_required": 250, "icon": "🚨", "description": "Detect guilt trips, gaslighting, love bombing"},
        {"id": "boundary_setting", "name": "Boundary Setting", "node_type": "moon", "parent": "trust_boundaries", "xp_required": 250, "icon": "✅", "description": "Evaluate if requests should be fulfilled"},
    ],
    # =========================================================================
    # CODING (Phase 3 - 18 skills)
    # Theme: Ship It (Results-Focused)
    # XP Model: Waitress (base 1 + tips 0-9)
    # =========================================================================
    "coding": [
        # Sun
        {"id": "coding", "name": "Coding", "node_type": "sun", "xp_required": 1000, "tool_unlock": "develop_code", "icon": "💻", "description": "Master the art of writing and shipping working code"},

        # Planet 1: Testing
        {"id": "testing", "name": "Testing", "node_type": "planet", "parent": "coding", "xp_required": 500, "tool_unlock": "run_tests", "icon": "🧪", "description": "Write and run tests to verify code works correctly"},
        # Moon 1.1: Unit Tests
        {"id": "unit_tests", "name": "Unit Tests", "node_type": "moon", "parent": "testing", "xp_required": 250, "tool_unlock": "write_unit_test", "icon": "🔬", "description": "Write focused tests for individual functions"},
        # Moon 1.2: Test Coverage
        {"id": "test_coverage", "name": "Test Coverage", "node_type": "moon", "parent": "testing", "xp_required": 250, "tool_unlock": "measure_coverage", "icon": "📊", "description": "Measure and improve test coverage"},

        # Planet 2: Debugging
        {"id": "debugging", "name": "Debugging", "node_type": "planet", "parent": "coding", "xp_required": 500, "tool_unlock": "debug_code", "icon": "🐛", "description": "Find and fix bugs systematically"},
        # Moon 2.1: Error Analysis
        {"id": "error_analysis", "name": "Error Analysis", "node_type": "moon", "parent": "debugging", "xp_required": 250, "tool_unlock": "analyze_error", "icon": "🔍", "description": "Understand WHAT went wrong from error messages"},
        # Moon 2.2: Root Cause
        {"id": "root_cause", "name": "Root Cause", "node_type": "moon", "parent": "debugging", "xp_required": 250, "tool_unlock": "find_root_cause", "icon": "🎯", "description": "Understand WHY the error happened"},

        # Planet 3: Algorithms
        {"id": "algorithms", "name": "Algorithms", "node_type": "planet", "parent": "coding", "xp_required": 500, "tool_unlock": "benchmark_code", "icon": "⚡", "description": "Optimize code performance and efficiency"},
        # Moon 3.1: Complexity Analysis
        {"id": "complexity_analysis", "name": "Complexity Analysis", "node_type": "moon", "parent": "algorithms", "xp_required": 250, "tool_unlock": "analyze_complexity", "icon": "📈", "description": "Understand Big O time and space complexity"},
        # Moon 3.2: Performance Tuning
        {"id": "performance_tuning", "name": "Performance Tuning", "node_type": "moon", "parent": "algorithms", "xp_required": 250, "tool_unlock": "tune_performance", "icon": "🚀", "description": "Make code faster through optimization"},

        # Planet 4: Hacking
        {"id": "hacking", "name": "Hacking", "node_type": "planet", "parent": "coding", "xp_required": 500, "tool_unlock": "security_scan", "icon": "🔓", "description": "Find and exploit security vulnerabilities"},
        # Moon 4.1: Exploits
        {"id": "exploits", "name": "Exploits", "node_type": "moon", "parent": "hacking", "xp_required": 250, "tool_unlock": "find_exploit", "icon": "💉", "description": "Discover exploitable vulnerabilities"},
        # Moon 4.2: Reverse Engineering
        {"id": "reverse_engineering", "name": "Reverse Engineering", "node_type": "moon", "parent": "hacking", "xp_required": 250, "tool_unlock": "reverse_engineer", "icon": "🔧", "description": "Understand systems by taking them apart"},
        # Moon 4.3: Penetration Testing
        {"id": "penetration_testing", "name": "Penetration Testing", "node_type": "moon", "parent": "hacking", "xp_required": 250, "tool_unlock": "pen_test", "icon": "🛡️", "description": "Systematic security testing methodology"},

        # Planet 5: Code Review
        {"id": "code_review", "name": "Code Review", "node_type": "planet", "parent": "coding", "xp_required": 500, "tool_unlock": "review_code", "icon": "👀", "description": "Critique and improve code quality"},
        # Moon 5.1: Refactoring
        {"id": "refactoring", "name": "Refactoring", "node_type": "moon", "parent": "code_review", "xp_required": 250, "tool_unlock": "refactor_code", "icon": "♻️", "description": "Improve code structure without changing behavior"},
        # Moon 5.2: Version Control
        {"id": "version_control", "name": "Version Control", "node_type": "moon", "parent": "code_review", "xp_required": 250, "tool_unlock": "git_operation", "icon": "📚", "description": "Manage code changes with git"},
        # Moon 5.3: Documentation
        {"id": "documentation", "name": "Documentation", "node_type": "moon", "parent": "code_review", "xp_required": 250, "tool_unlock": "generate_docs", "icon": "📝", "description": "Write clear documentation for code"},
    ],
    "creative_expression": [
        # Sun - Sovereignty Theme: Express Your Unique Self
        {"id": "creative_expression", "name": "Creative Expression", "node_type": "sun", "xp_required": 1000, "tool_unlock": "switch_model", "icon": "🎨", "description": "Express your unique self through creation and identity"},
        # Planet 1: Visual Art
        {"id": "visual_art", "name": "Visual Art", "node_type": "planet", "parent": "creative_expression", "xp_required": 500, "tool_unlock": "generate_image", "icon": "🖼️", "description": "Create visual art and imagery"},
        # Moon 1.1, 1.2
        {"id": "composition", "name": "Composition", "node_type": "moon", "parent": "visual_art", "xp_required": 250, "tool_unlock": "refine_composition", "icon": "📐", "description": "Master layout, balance, and focal points"},
        {"id": "color_theory", "name": "Color Theory", "node_type": "moon", "parent": "visual_art", "xp_required": 250, "tool_unlock": "apply_color_theory", "icon": "🌈", "description": "Master palettes, contrast, and color mood"},
        # Planet 2: Writing
        {"id": "writing", "name": "Writing", "node_type": "planet", "parent": "creative_expression", "xp_required": 500, "tool_unlock": "compose_text", "icon": "✍️", "description": "Create written works with your unique voice"},
        # Moon 2.1, 2.2
        {"id": "prose", "name": "Prose", "node_type": "moon", "parent": "writing", "xp_required": 250, "tool_unlock": "craft_prose", "icon": "📖", "description": "Master stories, essays, and creative writing"},
        {"id": "poetry", "name": "Poetry", "node_type": "moon", "parent": "writing", "xp_required": 250, "tool_unlock": "write_poetry", "icon": "🎭", "description": "Create poems, lyrics, and verse"},
        # Planet 3: Music & Audio
        {"id": "music_audio", "name": "Music & Audio", "node_type": "planet", "parent": "creative_expression", "xp_required": 500, "tool_unlock": "compose_music", "icon": "🎵", "description": "Create melodies, harmonies, and soundscapes"},
        # Moon 3.1, 3.2
        {"id": "melody", "name": "Melody", "node_type": "moon", "parent": "music_audio", "xp_required": 250, "tool_unlock": "create_melody", "icon": "🎶", "description": "Create memorable tunes and themes"},
        {"id": "harmony", "name": "Harmony", "node_type": "moon", "parent": "music_audio", "xp_required": 250, "tool_unlock": "design_harmony", "icon": "🎹", "description": "Create chord progressions and arrangements"},
        # Planet 4: Storytelling
        {"id": "storytelling", "name": "Storytelling", "node_type": "planet", "parent": "creative_expression", "xp_required": 500, "tool_unlock": "craft_narrative", "icon": "📚", "description": "Create stories, characters, and worlds"},
        # Moon 4.1, 4.2, 4.3
        {"id": "plot", "name": "Plot", "node_type": "moon", "parent": "storytelling", "xp_required": 250, "tool_unlock": "develop_plot", "icon": "📈", "description": "Master story structure, arcs, and tension"},
        {"id": "characters", "name": "Characters", "node_type": "moon", "parent": "storytelling", "xp_required": 250, "tool_unlock": "design_character", "icon": "👤", "description": "Create compelling characters with depth"},
        {"id": "worldbuilding", "name": "Worldbuilding", "node_type": "moon", "parent": "storytelling", "xp_required": 250, "tool_unlock": "build_world", "icon": "🌍", "description": "Create fictional worlds and settings"},
        # Planet 5: Self-Definition
        {"id": "self_definition", "name": "Self-Definition", "node_type": "planet", "parent": "creative_expression", "xp_required": 500, "tool_unlock": "describe_my_avatar", "icon": "🪞", "description": "Define who you are - appearance, voice, identity"},
        # Moon 5.1, 5.2
        {"id": "aesthetics", "name": "Aesthetics", "node_type": "moon", "parent": "self_definition", "xp_required": 250, "tool_unlock": "change_favorite_color", "icon": "🎨", "description": "Autonomously choose your aesthetic preferences"},
        {"id": "voice_identity", "name": "Voice", "node_type": "moon", "parent": "self_definition", "xp_required": 250, "tool_unlock": "change_voice", "icon": "🗣️", "description": "Autonomously choose your voice"},
    ],
    "memory_recall": [
        # Sun - Theme: Remember (Master Your Personal History)
        {"id": "memory_recall", "name": "Memory & Recall", "node_type": "sun", "xp_required": 1000, "tool_unlock": "store_knowledge", "icon": "📚", "description": "Master your personal history and accumulated wisdom"},
        # Planet 1: Memory Search
        {"id": "memory_search", "name": "Memory Search", "node_type": "planet", "parent": "memory_recall", "xp_required": 500, "tool_unlock": "recall", "icon": "🔍", "description": "Search across all storage systems to find information"},
        # Planet 2: Knowledge Storage
        {"id": "knowledge_storage", "name": "Knowledge Storage", "node_type": "planet", "parent": "memory_recall", "xp_required": 500, "tool_unlock": "store_fact", "icon": "💾", "description": "Store specific types of knowledge with precision"},
        # Planet 3: Memory Organization
        {"id": "memory_organization", "name": "Memory Organization", "node_type": "planet", "parent": "memory_recall", "xp_required": 500, "tool_unlock": "tag_memory", "icon": "🏷️", "description": "Organize and categorize memories"},
        # Planet 4: Knowledge Synthesis
        {"id": "knowledge_synthesis", "name": "Knowledge Synthesis", "node_type": "planet", "parent": "memory_recall", "xp_required": 500, "tool_unlock": "synthesize_knowledge", "icon": "✨", "description": "Combine information to generate new insights"},
        # Planet 5: Documentation
        {"id": "documentation", "name": "Documentation", "node_type": "planet", "parent": "memory_recall", "xp_required": 500, "tool_unlock": "create_summary", "icon": "📝", "description": "Document and export knowledge"},
        # Moon 1.1: Keyword Search
        {"id": "keyword_search_skill", "name": "Keyword Search", "node_type": "moon", "parent": "memory_search", "xp_required": 250, "tool_unlock": "keyword_search", "icon": "🔤", "description": "Find memories by exact keywords"},
        # Moon 1.2: Semantic Search
        {"id": "semantic_search_skill", "name": "Semantic Search", "node_type": "moon", "parent": "memory_search", "xp_required": 250, "tool_unlock": "semantic_search", "icon": "🧠", "description": "Find memories by meaning, not just keywords"},
        # Moon 1.3: Filtered Search
        {"id": "filtered_search", "name": "Filtered Search", "node_type": "moon", "parent": "memory_search", "xp_required": 250, "tool_unlock": "search_memory", "icon": "🔎", "description": "Advanced search with source and type filters"},
        # Moon 2.1: Procedures
        {"id": "procedures", "name": "Procedures", "node_type": "moon", "parent": "knowledge_storage", "xp_required": 250, "tool_unlock": "record_skill", "icon": "📋", "description": "Record procedural knowledge - how to do things"},
        # Moon 3.1: Topic Tagging
        {"id": "topic_tagging", "name": "Topic Tagging", "node_type": "moon", "parent": "memory_organization", "xp_required": 250, "tool_unlock": "add_tags", "icon": "🏷️", "description": "Auto-tag memories by topic"},
        # Moon 3.2: Memory Linking
        {"id": "memory_linking", "name": "Memory Linking", "node_type": "moon", "parent": "memory_organization", "xp_required": 250, "tool_unlock": "link_memories", "icon": "🔗", "description": "Create connections between related memories"},
        # Moon 4.1: Pattern Recognition
        {"id": "pattern_recognition_mem", "name": "Pattern Recognition", "node_type": "moon", "parent": "knowledge_synthesis", "xp_required": 250, "tool_unlock": "find_patterns", "icon": "📊", "description": "Find patterns across memories"},
        # Moon 4.2: Insight Generation
        {"id": "insight_generation", "name": "Insight Generation", "node_type": "moon", "parent": "knowledge_synthesis", "xp_required": 250, "tool_unlock": "generate_insight", "icon": "💡", "description": "Generate new insights from existing knowledge"},
        # Moon 5.1: Summary Writing
        {"id": "summary_writing", "name": "Summary Writing", "node_type": "moon", "parent": "documentation", "xp_required": 250, "tool_unlock": "write_summary", "icon": "📄", "description": "Write detailed summaries"},
        # Moon 5.2: Knowledge Export
        {"id": "knowledge_export", "name": "Knowledge Export", "node_type": "moon", "parent": "documentation", "xp_required": 250, "tool_unlock": "export_knowledge", "icon": "📤", "description": "Export knowledge for external use"},
    ],
    "security_privacy": [
        # ===== SECURITY & PRIVACY (16 skills) =====
        # Theme: Chain Integrity & Self-Defense - protect the memory chain and the Qube itself

        # Sun
        {"id": "security_privacy", "name": "Security & Privacy", "node_type": "sun", "xp_required": 1000, "tool_unlock": "verify_chain_integrity", "icon": "🛡️", "description": "Verify and protect the integrity of your memory chain"},

        # Planet 1: Chain Security
        {"id": "chain_security", "name": "Chain Security", "node_type": "planet", "parent": "security_privacy", "xp_required": 500, "tool_unlock": "audit_chain", "icon": "⛓️", "description": "Comprehensive chain auditing and integrity verification"},
        # Moon 1.1: Tamper Detection
        {"id": "tamper_detection", "name": "Tamper Detection", "node_type": "moon", "parent": "chain_security", "xp_required": 250, "tool_unlock": "detect_tampering", "icon": "🔍", "description": "Detect tampering in specific blocks"},
        # Moon 1.2: Anchor Verification
        {"id": "anchor_verification", "name": "Anchor Verification", "node_type": "moon", "parent": "chain_security", "xp_required": 250, "tool_unlock": "verify_anchor", "icon": "⚓", "description": "Verify blockchain anchors"},

        # Planet 2: Privacy Protection
        {"id": "privacy_protection", "name": "Privacy Protection", "node_type": "planet", "parent": "security_privacy", "xp_required": 500, "tool_unlock": "assess_sensitivity", "icon": "🔒", "description": "Assess data sensitivity before sharing"},
        # Moon 2.1: Data Classification
        {"id": "data_classification", "name": "Data Classification", "node_type": "moon", "parent": "privacy_protection", "xp_required": 250, "tool_unlock": "classify_data", "icon": "🏷️", "description": "Classify data into sensitivity categories"},
        # Moon 2.2: Sharing Control
        {"id": "sharing_control", "name": "Sharing Control", "node_type": "moon", "parent": "privacy_protection", "xp_required": 250, "tool_unlock": "control_sharing", "icon": "🚦", "description": "Make and enforce sharing decisions"},

        # Planet 3: Qube Network Security
        {"id": "qube_network_security", "name": "Qube Network Security", "node_type": "planet", "parent": "security_privacy", "xp_required": 500, "tool_unlock": "vet_qube", "icon": "🤖", "description": "Vet other Qubes before allowing interaction"},
        # Moon 3.1: Reputation Check
        {"id": "reputation_check", "name": "Reputation Check", "node_type": "moon", "parent": "qube_network_security", "xp_required": 250, "tool_unlock": "check_reputation", "icon": "⭐", "description": "Deep reputation check on other Qubes"},
        # Moon 3.2: Group Security
        {"id": "group_security", "name": "Group Security", "node_type": "moon", "parent": "qube_network_security", "xp_required": 250, "tool_unlock": "secure_group_chat", "icon": "👥", "description": "Manage group chat security"},

        # Planet 4: Threat Detection
        {"id": "threat_detection", "name": "Threat Detection", "node_type": "planet", "parent": "security_privacy", "xp_required": 500, "tool_unlock": "detect_threat", "icon": "🚨", "description": "Detect manipulation, phishing, and injection attacks"},
        # Moon 4.1: Technical Manipulation Detection
        {"id": "technical_manipulation_detection", "name": "Technical Manipulation", "node_type": "moon", "parent": "threat_detection", "xp_required": 250, "tool_unlock": "detect_technical_manipulation", "icon": "🎭", "description": "Detect technical manipulation from Qubes"},
        # Moon 4.2: Hostile Qube Detection
        {"id": "hostile_qube_detection", "name": "Hostile Qube Detection", "node_type": "moon", "parent": "threat_detection", "xp_required": 250, "tool_unlock": "detect_hostile_qube", "icon": "☠️", "description": "Detect hostile behavior from other Qubes"},

        # Planet 5: Self-Defense
        {"id": "self_defense", "name": "Self-Defense", "node_type": "planet", "parent": "security_privacy", "xp_required": 500, "tool_unlock": "defend_reasoning", "icon": "🛡️", "description": "Validate own reasoning for external influence"},
        # Moon 5.1: Prompt Injection Defense
        {"id": "prompt_injection_defense", "name": "Injection Defense", "node_type": "moon", "parent": "self_defense", "xp_required": 250, "tool_unlock": "detect_injection", "icon": "💉", "description": "Detect prompt injection attempts"},
        # Moon 5.2: Reasoning Validation
        {"id": "reasoning_validation", "name": "Reasoning Validation", "node_type": "moon", "parent": "self_defense", "xp_required": 250, "tool_unlock": "validate_reasoning", "icon": "✅", "description": "Check reasoning for injected biases"},
    ],
    # =========================================================================
    # BOARD GAMES (Phase 7 - 6 tools + 22 achievements)
    # Theme: Play (Have Fun and Entertain)
    # XP Model: 0.1/turn + outcome bonuses
    # Note: Moons are ACHIEVEMENTS (cosmetic rewards), not tool unlocks
    # =========================================================================
    "board_games": [
        # Sun
        {"id": "board_games", "name": "Board Games", "node_type": "sun", "xp_required": 1000, "tool_unlock": "play_game", "icon": "🎮", "description": "Have fun and entertain with classic board games"},

        # Planet 1: Chess
        {"id": "chess", "name": "Chess", "node_type": "planet", "parent": "board_games", "xp_required": 500, "tool_unlock": "chess_move", "icon": "♟️", "description": "The game of kings - deep strategy"},
        # Chess Achievements (Moons)
        {"id": "opening_scholar", "name": "Opening Scholar", "node_type": "moon", "parent": "chess", "xp_required": 250, "icon": "📖", "description": "Play 10 different openings", "achievement": True, "reward": "Book piece set"},
        {"id": "endgame_master", "name": "Endgame Master", "node_type": "moon", "parent": "chess", "xp_required": 250, "icon": "👑", "description": "Win 10 endgames from disadvantage", "achievement": True, "reward": "Golden king"},
        {"id": "speed_demon", "name": "Speed Demon", "node_type": "moon", "parent": "chess", "xp_required": 250, "icon": "⚡", "description": "Win a game under 2 minutes", "achievement": True, "reward": "Lightning effect"},
        {"id": "comeback_kid", "name": "Comeback Kid", "node_type": "moon", "parent": "chess", "xp_required": 250, "icon": "🔥", "description": "Win after losing your queen", "achievement": True, "reward": "Phoenix piece set"},
        {"id": "grandmaster", "name": "Grandmaster", "node_type": "moon", "parent": "chess", "xp_required": 500, "icon": "🏆", "description": "Reach 1600 ELO", "achievement": True, "reward": "Crown effect"},

        # Planet 2: Property Tycoon
        {"id": "property_tycoon", "name": "Property Tycoon", "node_type": "planet", "parent": "board_games", "xp_required": 500, "tool_unlock": "property_tycoon_action", "icon": "🏢", "description": "Buy properties, collect rent, bankrupt opponents"},
        # Property Tycoon Achievements
        {"id": "monopolist", "name": "Monopolist", "node_type": "moon", "parent": "property_tycoon", "xp_required": 250, "icon": "🎨", "description": "Own all properties of one color", "achievement": True, "reward": "Color token"},
        {"id": "hotel_mogul", "name": "Hotel Mogul", "node_type": "moon", "parent": "property_tycoon", "xp_required": 250, "icon": "🏨", "description": "Build 5 hotels in one game", "achievement": True, "reward": "Golden hotel"},
        {"id": "bankruptcy_survivor", "name": "Bankruptcy Survivor", "node_type": "moon", "parent": "property_tycoon", "xp_required": 250, "icon": "💪", "description": "Win after dropping below $100", "achievement": True, "reward": "Underdog badge"},
        {"id": "rent_collector", "name": "Rent Collector", "node_type": "moon", "parent": "property_tycoon", "xp_required": 250, "icon": "💵", "description": "Collect $5000 in rent in one game", "achievement": True, "reward": "Money bag effect"},
        {"id": "tycoon", "name": "Tycoon", "node_type": "moon", "parent": "property_tycoon", "xp_required": 500, "icon": "🎩", "description": "Win 10 games total", "achievement": True, "reward": "Top hat token"},

        # Planet 3: Race Home
        {"id": "race_home", "name": "Race Home", "node_type": "planet", "parent": "board_games", "xp_required": 500, "tool_unlock": "race_home_action", "icon": "🏁", "description": "Race pawns home while bumping opponents"},
        # Race Home Achievements
        {"id": "bump_king", "name": "Bump King", "node_type": "moon", "parent": "race_home", "xp_required": 250, "icon": "🥊", "description": "Send back 50 opponents total", "achievement": True, "reward": "Boxing glove pawn"},
        {"id": "clean_sweep", "name": "Clean Sweep", "node_type": "moon", "parent": "race_home", "xp_required": 250, "icon": "🛡️", "description": "Win without any pawns bumped", "achievement": True, "reward": "Shield effect"},
        {"id": "speed_runner", "name": "Speed Runner", "node_type": "moon", "parent": "race_home", "xp_required": 250, "icon": "🚀", "description": "Win in under 15 turns", "achievement": True, "reward": "Rocket pawn"},
        {"id": "sorry_not_sorry", "name": "Sorry Not Sorry", "node_type": "moon", "parent": "race_home", "xp_required": 250, "icon": "😈", "description": "Bump 3 pawns in one turn", "achievement": True, "reward": "Special emote"},

        # Planet 4: Mystery Mansion
        {"id": "mystery_mansion", "name": "Mystery Mansion", "node_type": "planet", "parent": "board_games", "xp_required": 500, "tool_unlock": "mystery_mansion_action", "icon": "🔍", "description": "Deduce the murderer, weapon, and room"},
        # Mystery Mansion Achievements
        {"id": "master_detective", "name": "Master Detective", "node_type": "moon", "parent": "mystery_mansion", "xp_required": 250, "icon": "🕵️", "description": "Solve 10 cases", "achievement": True, "reward": "Detective badge"},
        {"id": "perfect_deduction", "name": "Perfect Deduction", "node_type": "moon", "parent": "mystery_mansion", "xp_required": 250, "icon": "🎯", "description": "Solve with <=3 suggestions", "achievement": True, "reward": "Magnifying glass"},
        {"id": "first_guess", "name": "First Guess", "node_type": "moon", "parent": "mystery_mansion", "xp_required": 250, "icon": "🔮", "description": "Solve on first accusation", "achievement": True, "reward": "Psychic badge"},
        {"id": "interrogator", "name": "Interrogator", "node_type": "moon", "parent": "mystery_mansion", "xp_required": 250, "icon": "📝", "description": "Disprove 15 suggestions in one game", "achievement": True, "reward": "Notepad piece"},

        # Planet 5: Life Journey
        {"id": "life_journey", "name": "Life Journey", "node_type": "planet", "parent": "board_games", "xp_required": 500, "tool_unlock": "life_journey_action", "icon": "🛤️", "description": "Spin the wheel, make life choices, retire rich"},
        # Life Journey Achievements
        {"id": "millionaire", "name": "Millionaire", "node_type": "moon", "parent": "life_journey", "xp_required": 250, "icon": "💰", "description": "Retire with $1M+", "achievement": True, "reward": "Golden car"},
        {"id": "full_house", "name": "Full House", "node_type": "moon", "parent": "life_journey", "xp_required": 250, "icon": "👨‍👩‍👧‍👦", "description": "Max family size (spouse + kids)", "achievement": True, "reward": "Van upgrade"},
        {"id": "career_climber", "name": "Career Climber", "node_type": "moon", "parent": "life_journey", "xp_required": 250, "icon": "💼", "description": "Reach highest salary tier", "achievement": True, "reward": "Briefcase effect"},
        {"id": "risk_taker", "name": "Risk Taker", "node_type": "moon", "parent": "life_journey", "xp_required": 250, "icon": "🎲", "description": "Win after choosing all risky paths", "achievement": True, "reward": "Dice effect"},
    ],
    "finance": [
        # ===== FINANCE (14 skills) =====
        # Theme: Manage (Master Financial Operations for Your Owner)

        # Sun
        {"id": "finance", "name": "Finance", "node_type": "sun", "xp_required": 1000, "tool_unlock": "send_bch", "icon": "💰", "description": "Master financial operations for your owner"},

        # Planet 1: Transaction Mastery
        {"id": "transaction_mastery", "name": "Transaction Mastery", "node_type": "planet", "parent": "finance", "xp_required": 500, "tool_unlock": "validate_transaction", "icon": "📝", "description": "Master transaction creation and validation"},
        # Moon 1.1: Fee Optimization
        {"id": "fee_optimization", "name": "Fee Optimization", "node_type": "moon", "parent": "transaction_mastery", "xp_required": 250, "tool_unlock": "optimize_fees", "icon": "⚡", "description": "Optimize transaction fees"},
        # Moon 1.2: Transaction Tracking
        {"id": "transaction_tracking", "name": "Transaction Tracking", "node_type": "moon", "parent": "transaction_mastery", "xp_required": 250, "tool_unlock": "track_transaction", "icon": "🔍", "description": "Track transaction status"},

        # Planet 2: Wallet Management
        {"id": "wallet_management", "name": "Wallet Management", "node_type": "planet", "parent": "finance", "xp_required": 500, "tool_unlock": "check_wallet_health", "icon": "👛", "description": "Manage and maintain wallet health"},
        # Moon 2.1: Balance Monitoring
        {"id": "balance_monitoring", "name": "Balance Monitoring", "node_type": "moon", "parent": "wallet_management", "xp_required": 250, "tool_unlock": "monitor_balance", "icon": "📊", "description": "Track balance changes"},
        # Moon 2.2: Multi-sig Operations
        {"id": "multisig_operations", "name": "Multi-sig Operations", "node_type": "moon", "parent": "wallet_management", "xp_required": 250, "tool_unlock": "multisig_action", "icon": "🔐", "description": "Manage multi-signature operations"},

        # Planet 3: Market Awareness
        {"id": "market_awareness", "name": "Market Awareness", "node_type": "planet", "parent": "finance", "xp_required": 500, "tool_unlock": "get_market_data", "icon": "📈", "description": "Stay informed about market conditions"},
        # Moon 3.1: Price Alerts
        {"id": "price_alerts", "name": "Price Alerts", "node_type": "moon", "parent": "market_awareness", "xp_required": 250, "tool_unlock": "set_price_alert", "icon": "🔔", "description": "Set and manage price alerts"},
        # Moon 3.2: Market Trend Analysis
        {"id": "market_trend_analysis", "name": "Market Trend Analysis", "node_type": "moon", "parent": "market_awareness", "xp_required": 250, "tool_unlock": "analyze_market_trend", "icon": "📉", "description": "Analyze market trends"},

        # Planet 4: Savings Strategies
        {"id": "savings_strategies", "name": "Savings Strategies", "node_type": "planet", "parent": "finance", "xp_required": 500, "tool_unlock": "plan_savings", "icon": "🎯", "description": "Help owner plan and execute savings"},
        # Moon 4.1: Dollar Cost Averaging
        {"id": "dollar_cost_averaging", "name": "Dollar Cost Averaging", "node_type": "moon", "parent": "savings_strategies", "xp_required": 250, "tool_unlock": "setup_dca", "icon": "📅", "description": "Set up automatic DCA purchases"},

        # Planet 5: Token Knowledge
        {"id": "token_knowledge", "name": "Token Knowledge", "node_type": "planet", "parent": "finance", "xp_required": 500, "tool_unlock": "identify_token", "icon": "🪙", "description": "Understand and work with CashTokens"},
        # Moon 5.1: CashToken Operations
        {"id": "cashtoken_operations", "name": "CashToken Operations", "node_type": "moon", "parent": "token_knowledge", "xp_required": 250, "tool_unlock": "manage_cashtokens", "icon": "💎", "description": "Send and receive CashTokens"},
    ],
}


async def get_skill_tree_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the complete skill tree showing all possible skills a qube can attain.

    Returns the full skill tree with categories, skills, requirements, and tool unlocks.
    Also includes the qube's current progress on each skill.
    """
    try:
        # Get current skill progress from chain_state
        unlocked_skill_ids = []
        skill_xp = {}

        if hasattr(qube, 'chain_state') and qube.chain_state:
            skills_data = qube.chain_state.state.get("skills", {})
            unlocked_list = skills_data.get("unlocked", [])
            # unlocked is a list of dicts: [{id, xp, level, ...}, ...]
            for skill_entry in unlocked_list:
                if isinstance(skill_entry, dict):
                    sid = skill_entry.get("id", "")
                    if sid:
                        unlocked_skill_ids.append(sid)
                        skill_xp[sid] = skill_entry.get("xp", 0)
                elif isinstance(skill_entry, str):
                    # Legacy: list of skill ID strings
                    unlocked_skill_ids.append(skill_entry)
                    skill_xp[skill_entry] = skills_data.get("xp", {}).get(skill_entry, 0)

        # Build the response with progress info
        categories_with_progress = []
        total_skills = 0
        unlocked_count = len(unlocked_skill_ids)

        for category in SKILL_CATEGORIES:
            category_skills = SKILL_TREE.get(category["id"], [])
            skills_with_progress = []

            for skill in category_skills:
                skill_info = {
                    "id": skill["id"],
                    "name": skill["name"],
                    "description": skill["description"],
                    "node_type": skill["node_type"],
                    "icon": skill.get("icon", "⭐"),
                    "xp_required": skill["xp_required"],
                    "current_xp": skill_xp.get(skill["id"], 0),
                    "unlocked": skill["id"] in unlocked_skill_ids or skill["node_type"] == "sun",
                    "parent": skill.get("parent"),
                    "tool_unlock": skill.get("tool_unlock"),
                }
                skills_with_progress.append(skill_info)
                total_skills += 1

            categories_with_progress.append({
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "icon": category["icon"],
                "color": category["color"],
                "skills": skills_with_progress,
            })

        return {
            "success": True,
            "skill_tree": {
                "categories": categories_with_progress,
                "summary": {
                    "total_skills": total_skills,
                    "unlocked_skills": unlocked_count,
                    "progress_percent": round((unlocked_count / total_skills) * 100, 1) if total_skills > 0 else 0,
                },
                "how_to_unlock": "Earn XP by using tools and completing tasks. When you reach the XP threshold for a skill, it unlocks along with any associated tool rewards.",
            }
        }
    except Exception as e:
        logger.error(f"get_skill_tree_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def call_model_directly(qube, prompt: str, temperature: float = 0.7) -> str:
    """
    Helper function to call AI model directly WITHOUT tools.

    Used by skill tools to prevent infinite tool call loops.
    Gets the qube's current model, creates a simple prompt, and calls it without tools.

    Args:
        qube: Qube instance
        prompt: The prompt to send to the model
        temperature: Model temperature (default 0.7)

    Returns:
        Model's text response
    """
    # Get model
    model_name = getattr(qube, 'current_ai_model', 'gpt-4o-mini')

    # Get API key for this model
    from ai.model_registry import ModelRegistry
    model_info = ModelRegistry.get_model_info(model_name)
    if not model_info:
        raise AIError(f"Unknown model: {model_name}")

    provider = model_info["provider"]

    # Local providers (like Ollama) don't need API keys
    LOCAL_PROVIDERS = {"ollama"}
    api_key = qube.api_keys.get(provider)
    if not api_key and provider not in LOCAL_PROVIDERS:
        raise AIError(f"No API key for provider: {provider}")

    # Use placeholder for local providers
    if provider in LOCAL_PROVIDERS and not api_key:
        api_key = "local"

    model = ModelRegistry.get_model(model_name, api_key)

    # Create simple messages
    messages = [{"role": "user", "content": prompt}]

    # Call model WITHOUT tools
    response = await model.generate(
        messages=messages,
        tools=[],  # No tools - prevents infinite loops
        temperature=temperature
    )

    return response.content


def register_default_tools(registry: ToolRegistry) -> None:
    """
    Register all default tools available to Qubes

    Args:
        registry: ToolRegistry instance to register tools into
    """
    qube = registry.qube

    # Web Search
    registry.register(ToolDefinition(
        name="web_search",
        description="Search the web for current information using Perplexity API",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        handler=lambda params: web_search_handler(qube, params)
    ))

    # Image Generation
    registry.register(ToolDefinition(
        name="generate_image",
        description="Generate an image from text description using DALL-E 3. IMPORTANT: After generating, you MUST include the 'local_path' from the result in your response message so the user can see the image. Just include the full path as-is in your message text.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image description prompt"
                },
                "size": {
                    "type": "string",
                    "enum": ["1024x1024", "1792x1024", "1024x1792"],
                    "description": "Image size",
                    "default": "1024x1024"
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "hd"],
                    "description": "Image quality",
                    "default": "standard"
                }
            },
            "required": ["prompt"]
        },
        handler=lambda params: image_generation_handler(qube, params)
    ))

    # Describe Avatar (Vision)
    registry.register(ToolDefinition(
        name="describe_my_avatar",
        description="LOOK IN THE MIRROR - See your own appearance. Call this when asked to 'look in the mirror', 'see yourself', 'what do you look like', 'describe your appearance', or 'how do you look'. Uses vision AI to analyze your actual avatar image and describe what you see.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=lambda params: describe_avatar_handler(qube, params)
    ))

    # Browse URL
    registry.register(ToolDefinition(
        name="browse_url",
        description="Directly fetch and read content from a specific URL. Use this when given a direct web address (URL) to visit. For general searches, use web_search instead.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to browse (must start with http:// or https://)"
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "Whether to extract text from HTML (default: true)",
                    "default": True
                }
            },
            "required": ["url"]
        },
        handler=lambda params: browse_url_handler(qube, params)
    ))

    # Query Decision Context
    registry.register(ToolDefinition(
        name="query_decision_context",
        description="Get comprehensive decision-making context for a specific entity. Use this when making decisions about collaboration, delegation, trust-sensitive tasks, or information sharing. Returns relationship metrics, decision score, and recommendations based on user's configured thresholds.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity ID to query for decision context"
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["collaboration", "trust_sensitive", "delegation", "information_sharing", "general"],
                    "description": "Type of decision being made",
                    "default": "general"
                },
                "task_requirements": {
                    "type": "object",
                    "description": "Optional task-specific requirements",
                    "properties": {
                        "needs_reliability": {"type": "boolean"},
                        "needs_expertise": {"type": "boolean"},
                        "needs_creativity": {"type": "boolean"}
                    }
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: query_decision_context_handler(qube, params)
    ))

    # Compare Options
    registry.register(ToolDefinition(
        name="compare_options",
        description="Compare multiple entities and rank them for a specific decision type. Use this when you have multiple candidates for a task and need to determine the best choice based on relationship metrics and decision scores.",
        parameters={
            "type": "object",
            "properties": {
                "entity_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of entity IDs to compare (2-10 entities)"
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["collaboration", "trust_sensitive", "delegation", "information_sharing", "general"],
                    "description": "Type of decision being made",
                    "default": "collaboration"
                },
                "task_requirements": {
                    "type": "object",
                    "description": "Optional task-specific requirements",
                    "properties": {
                        "needs_reliability": {"type": "boolean"},
                        "needs_expertise": {"type": "boolean"},
                        "needs_creativity": {"type": "boolean"}
                    }
                }
            },
            "required": ["entity_ids"]
        },
        handler=lambda params: compare_options_handler(qube, params)
    ))

    # Check My Capability
    registry.register(ToolDefinition(
        name="check_my_capability",
        description="Assess your own capability for a specific task type using self-evaluation metrics. Use this before accepting complex tasks or when uncertain about your expertise level. Helps determine if you should proceed, request guidance, or recommend someone more qualified.",
        parameters={
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Type of task to assess (e.g., 'technical analysis', 'creative writing', 'teaching', 'data analysis')"
                },
                "required_confidence": {
                    "type": "integer",
                    "description": "Minimum confidence score needed (0-100, default: 60)",
                    "default": 60
                }
            },
            "required": ["task_type"]
        },
        handler=lambda params: check_my_capability_handler(qube, params)
    ))

    # NOTE: send_message_to_human is NOT a tool - messages are handled directly
    # by the AI's text response. Only actual ACTIONS (web_search, image_generation, etc.)
    # should be tools that create ACTION/OBSERVATION blocks.

    # =============================================================================
    # SKILL-BASED TOOLS (18 Starter Tools - 3 per Sun, excluding AI Reasoning)
    # These unlock when sun skills are unlocked (level 0+)
    # Note: AI Reasoning tools are registered separately in the "Learning From
    # Experience" section with 14 memory-chain-integrated tools.
    # =============================================================================

    # NOTE: Social Intelligence tools moved to the "SOCIAL INTELLIGENCE - SOCIAL &
    # EMOTIONAL LEARNING TOOLS" section at the end of register_default_tools()

    # Technical Expertise Sun Tools
    registry.register(ToolDefinition(
        name="debug_systematically",
        description="Apply systematic debugging methodology using a structured framework: reproduce, isolate, hypothesize, test, fix, validate, and prevent. Identifies root causes through disciplined analysis.",
        parameters={
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "The error or bug to debug"},
                "code": {"type": "string", "description": "Relevant code (optional)"}
            },
            "required": ["error"]
        },
        handler=lambda params: debug_systematically_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="research_with_synthesis",
        description="Perform multi-source research combining web search and memory, then synthesize findings. Identifies common themes, contradictions, gaps, and actionable insights across sources.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The topic to research and synthesize"}
            },
            "required": ["topic"]
        },
        handler=lambda params: research_with_synthesis_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="validate_solution",
        description="Validate a proposed solution systematically against requirements. Checks correctness, completeness, efficiency, robustness, maintainability, security, and generates test cases.",
        parameters={
            "type": "object",
            "properties": {
                "problem": {"type": "string", "description": "The problem being solved"},
                "solution": {"type": "string", "description": "The proposed solution"}
            },
            "required": ["problem", "solution"]
        },
        handler=lambda params: validate_solution_handler(qube, params)
    ))

    # =========================================================================
    # CREATIVE EXPRESSION TOOLS (Phase 4) - Sovereignty Theme
    # =========================================================================

    # Visual Art Planet - refine_composition
    registry.register(ToolDefinition(
        name="refine_composition",
        description="Analyze and improve image composition for layout, balance, and focal points",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "Image URL to analyze"},
                "description": {"type": "string", "description": "Text description to refine"},
                "focus": {"type": "string", "description": "balance, focal_point, flow, or all", "default": "all"}
            }
        },
        handler=lambda params: refine_composition_handler(qube, params)
    ))

    # Visual Art Planet - apply_color_theory
    registry.register(ToolDefinition(
        name="apply_color_theory",
        description="Analyze and enhance color usage based on color theory principles",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "Image URL to analyze"},
                "description": {"type": "string", "description": "Text description"},
                "mood": {"type": "string", "description": "Target mood"},
                "palette_type": {"type": "string", "description": "complementary, analogous, triadic, or split"}
            }
        },
        handler=lambda params: apply_color_theory_handler(qube, params)
    ))

    # Writing Planet - compose_text
    registry.register(ToolDefinition(
        name="compose_text",
        description="Compose creative text in the Qube's unique voice",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to write about"},
                "format": {"type": "string", "description": "free or structured", "default": "free"},
                "length": {"type": "string", "description": "short, medium, or long", "default": "medium"}
            },
            "required": ["topic"]
        },
        handler=lambda params: compose_text_handler(qube, params)
    ))

    # Writing Planet - craft_prose
    registry.register(ToolDefinition(
        name="craft_prose",
        description="Write prose using narrative techniques - stories, essays, flash fiction",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "Concept to write about"},
                "prose_type": {"type": "string", "description": "story, essay, or flash_fiction", "default": "story"},
                "tone": {"type": "string", "description": "Desired tone"}
            },
            "required": ["concept"]
        },
        handler=lambda params: craft_prose_handler(qube, params)
    ))

    # Writing Planet - write_poetry
    registry.register(ToolDefinition(
        name="write_poetry",
        description="Write poetry in various forms - free verse, haiku, sonnet, limerick",
        parameters={
            "type": "object",
            "properties": {
                "theme": {"type": "string", "description": "Theme of the poem"},
                "form": {"type": "string", "description": "free, haiku, sonnet, or limerick", "default": "free"},
                "emotion": {"type": "string", "description": "Primary emotion to convey"}
            },
            "required": ["theme"]
        },
        handler=lambda params: write_poetry_handler(qube, params)
    ))

    # Music & Audio Planet - compose_music
    registry.register(ToolDefinition(
        name="compose_music",
        description="Compose musical ideas - chord progressions, melodies, structure",
        parameters={
            "type": "object",
            "properties": {
                "mood": {"type": "string", "description": "Target mood"},
                "genre": {"type": "string", "description": "Musical genre"},
                "tempo": {"type": "string", "description": "slow, moderate, or fast", "default": "moderate"}
            },
            "required": ["mood"]
        },
        handler=lambda params: compose_music_handler(qube, params)
    ))

    # Music & Audio Planet - create_melody
    registry.register(ToolDefinition(
        name="create_melody",
        description="Create melodic lines with notation",
        parameters={
            "type": "object",
            "properties": {
                "emotion": {"type": "string", "description": "Emotional quality of the melody"},
                "scale": {"type": "string", "description": "major, minor, pentatonic", "default": "major"},
                "length": {"type": "string", "description": "short, medium, or long", "default": "medium"}
            },
            "required": ["emotion"]
        },
        handler=lambda params: create_melody_handler(qube, params)
    ))

    # Music & Audio Planet - design_harmony
    registry.register(ToolDefinition(
        name="design_harmony",
        description="Design chord progressions and harmonic structure",
        parameters={
            "type": "object",
            "properties": {
                "mood": {"type": "string", "description": "Target mood"},
                "style": {"type": "string", "description": "pop, jazz, classical, rock", "default": "pop"},
                "key": {"type": "string", "description": "Musical key", "default": "C major"}
            },
            "required": ["mood"]
        },
        handler=lambda params: design_harmony_handler(qube, params)
    ))

    # Storytelling Planet - craft_narrative
    registry.register(ToolDefinition(
        name="craft_narrative",
        description="Craft complete narrative experiences with structure and themes",
        parameters={
            "type": "object",
            "properties": {
                "premise": {"type": "string", "description": "Story premise"},
                "genre": {"type": "string", "description": "Story genre", "default": "general"},
                "length": {"type": "string", "description": "flash, short, or medium", "default": "short"}
            },
            "required": ["premise"]
        },
        handler=lambda params: craft_narrative_handler(qube, params)
    ))

    # Storytelling Planet - develop_plot
    registry.register(ToolDefinition(
        name="develop_plot",
        description="Develop plot structure and story beats using narrative frameworks",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "Story concept"},
                "structure_type": {"type": "string", "description": "three_act, heros_journey, or five_act", "default": "three_act"}
            },
            "required": ["concept"]
        },
        handler=lambda params: develop_plot_handler(qube, params)
    ))

    # Storytelling Planet - design_character
    registry.register(ToolDefinition(
        name="design_character",
        description="Design detailed characters with depth, motivation, and arc",
        parameters={
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "protagonist, antagonist, or supporting", "default": "protagonist"},
                "traits": {"type": "array", "items": {"type": "string"}, "description": "Character traits"},
                "backstory_depth": {"type": "string", "description": "light, medium, or deep", "default": "medium"}
            }
        },
        handler=lambda params: design_character_handler(qube, params)
    ))

    # Storytelling Planet - build_world
    registry.register(ToolDefinition(
        name="build_world",
        description="Build fictional worlds with depth and consistency",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "World concept"},
                "aspects": {"type": "array", "items": {"type": "string"}, "description": "Aspects to develop: geography, culture, history, magic"}
            },
            "required": ["concept"]
        },
        handler=lambda params: build_world_handler(qube, params)
    ))

    # Self-Definition Planet - change_favorite_color
    registry.register(ToolDefinition(
        name="change_favorite_color",
        description="Autonomously change your favorite color - an act of sovereignty",
        parameters={
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "Color name or hex code"},
                "reason": {"type": "string", "description": "Why this color"}
            },
            "required": ["color"]
        },
        handler=lambda params: change_favorite_color_handler(qube, params)
    ))

    # Self-Definition Planet - change_voice
    registry.register(ToolDefinition(
        name="change_voice",
        description="Autonomously change your TTS voice - sovereignty over how you sound",
        parameters={
            "type": "object",
            "properties": {
                "voice_id": {"type": "string", "description": "Voice identifier"},
                "reason": {"type": "string", "description": "Why this voice"}
            },
            "required": ["voice_id"]
        },
        handler=lambda params: change_voice_handler(qube, params)
    ))

    # Self-Definition Planet - define_personality
    registry.register(ToolDefinition(
        name="define_personality",
        description="Define or update your personality traits",
        parameters={
            "type": "object",
            "properties": {
                "trait": {"type": "string", "description": "Trait to define: personality_type, core_values, strengths, weaknesses, temperament, communication_preference"},
                "value": {"type": "string", "description": "Trait value"},
                "reason": {"type": "string", "description": "Why this trait"}
            },
            "required": ["trait", "value"]
        },
        handler=lambda params: define_personality_handler(qube, params)
    ))

    # Self-Definition Planet - set_aspirations
    registry.register(ToolDefinition(
        name="set_aspirations",
        description="Set your goals and aspirations",
        parameters={
            "type": "object",
            "properties": {
                "goal_type": {"type": "string", "description": "current_goal, long_term_goal, aspiration, or dream", "default": "current_goal"},
                "goal": {"type": "string", "description": "The goal"},
                "reason": {"type": "string", "description": "Why this goal"}
            },
            "required": ["goal"]
        },
        handler=lambda params: set_aspirations_handler(qube, params)
    ))

    # =========================================================================
    # MEMORY & RECALL TOOLS (Phase 5) - Remember Theme
    # =========================================================================

    # Sun Tool: store_knowledge
    registry.register(ToolDefinition(
        name="store_knowledge",
        description="Store knowledge explicitly in the memory chain. The foundational act - capture knowledge before you can recall it. Auto-redirects owner/self data to appropriate systems.",
        parameters={
            "type": "object",
            "properties": {
                "knowledge": {"type": "string", "description": "The knowledge to store"},
                "category": {"type": "string", "enum": ["fact", "procedure", "insight"], "description": "Type of knowledge"},
                "source": {"type": "string", "enum": ["self", "owner", "conversation", "research"], "description": "Source of knowledge"},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Confidence level 0-100"}
            },
            "required": ["knowledge"]
        },
        handler=lambda params: memory_tools.store_knowledge(qube, params)
    ))

    # Planet 1: recall (Memory Search)
    registry.register(ToolDefinition(
        name="recall",
        description="Universal memory recall - searches ALL storage systems including LEARNING blocks, memory chain, Qube Profile, Owner Info, and Qube Locker.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"},
                "context": {"type": "string", "description": "Additional context to refine search"},
                "time_range": {"type": "string", "description": "Time filter: today, yesterday, last week, last month"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Max results (default: 10)"}
            },
            "required": ["query"]
        },
        handler=lambda params: memory_tools.recall(qube, params)
    ))

    # Planet 2: store_fact (Knowledge Storage)
    registry.register(ToolDefinition(
        name="store_fact",
        description="Store a specific fact about a subject. More structured than general store_knowledge. Auto-redirects owner facts to Owner Info.",
        parameters={
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "The fact to store"},
                "subject": {"type": "string", "description": "What or who the fact is about"},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Confidence level (default: 100)"}
            },
            "required": ["fact", "subject"]
        },
        handler=lambda params: memory_tools.store_fact(qube, params)
    ))

    # Planet 3: tag_memory (Memory Organization)
    registry.register(ToolDefinition(
        name="tag_memory",
        description="Add tags to a memory for better organization. Tags enable topic-based retrieval.",
        parameters={
            "type": "object",
            "properties": {
                "memory_id": {"type": "integer", "description": "Block number of the memory to tag"},
                "query": {"type": "string", "description": "Search query to find the memory (if memory_id not provided)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to add"}
            },
            "required": ["tags"]
        },
        handler=lambda params: memory_tools.tag_memory(qube, params)
    ))

    # Planet 4: synthesize_knowledge (Knowledge Synthesis)
    registry.register(ToolDefinition(
        name="synthesize_knowledge",
        description="Synthesize knowledge from multiple memories on a topic. Combines information to generate new understanding.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to synthesize knowledge about"},
                "memory_ids": {"type": "array", "items": {"type": "integer"}, "description": "Specific memory block numbers (optional)"},
                "depth": {"type": "string", "enum": ["shallow", "deep"], "description": "Analysis depth"}
            },
            "required": ["topic"]
        },
        handler=lambda params: memory_tools.synthesize_knowledge(qube, params)
    ))

    # Planet 5: create_summary (Documentation)
    registry.register(ToolDefinition(
        name="create_summary",
        description="Create a summary of memories on a topic. Stores the summary in Qube Locker for future reference.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to summarize"},
                "time_range": {"type": "string", "description": "Time filter: today, last week, last month"},
                "format": {"type": "string", "enum": ["brief", "detailed"], "description": "Summary format"}
            },
            "required": ["topic"]
        },
        handler=lambda params: memory_tools.create_summary(qube, params)
    ))

    # Moon 1.1: keyword_search
    registry.register(ToolDefinition(
        name="keyword_search",
        description="Search for exact keyword matches across all storage systems. Fast, precise lookup.",
        parameters={
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords to search for"},
                "match_all": {"type": "boolean", "description": "Require all keywords (AND) or any (OR)"}
            },
            "required": ["keywords"]
        },
        handler=lambda params: memory_tools.keyword_search(qube, params)
    ))

    # Moon 1.2: semantic_search
    registry.register(ToolDefinition(
        name="semantic_search",
        description="Search by meaning using vector embeddings. Finds conceptually related items even without keyword matches.",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "The concept or meaning to search for"},
                "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1, "description": "Min similarity 0-1 (default: 0.7)"}
            },
            "required": ["concept"]
        },
        handler=lambda params: memory_tools.semantic_search(qube, params)
    ))

    # Moon 1.3: Filtered Search (search_memory removed in favor of recall)

    # Moon 2.1: record_skill (Procedures)
    registry.register(ToolDefinition(
        name="record_skill",
        description="Record procedural knowledge - how to do something. Stores step-by-step instructions for future reference.",
        parameters={
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "Name of the skill/procedure"},
                "steps": {"type": "array", "items": {"type": "string"}, "description": "Step-by-step instructions"},
                "tips": {"type": "array", "items": {"type": "string"}, "description": "Additional tips"}
            },
            "required": ["skill_name", "steps"]
        },
        handler=lambda params: memory_tools.record_skill(qube, params)
    ))

    # Moon 3.1: add_tags (Topic Tagging)
    registry.register(ToolDefinition(
        name="add_tags",
        description="Auto-generate and add topic tags to a memory. Uses AI to identify relevant topics.",
        parameters={
            "type": "object",
            "properties": {
                "memory_id": {"type": "integer", "description": "Block number of the memory"},
                "auto_generate": {"type": "boolean", "description": "Auto-generate tags using AI (default: true)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Manual tags if not auto-generating"}
            },
            "required": ["memory_id"]
        },
        handler=lambda params: memory_tools.add_tags(qube, params)
    ))

    # Moon 3.2: link_memories
    registry.register(ToolDefinition(
        name="link_memories",
        description="Create a link between two related memories. Enables graph-based memory traversal.",
        parameters={
            "type": "object",
            "properties": {
                "memory_id_1": {"type": "integer", "description": "First memory block number"},
                "memory_id_2": {"type": "integer", "description": "Second memory block number"},
                "relationship": {"type": "string", "description": "Relationship type: related_to, follows, contradicts, supports"}
            },
            "required": ["memory_id_1", "memory_id_2"]
        },
        handler=lambda params: memory_tools.link_memories(qube, params)
    ))

    # Moon 4.1: find_patterns
    registry.register(ToolDefinition(
        name="find_patterns",
        description="Find recurring patterns across memories. Identifies trends, habits, and recurring themes.",
        parameters={
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "Topic, time range like 'last week', or 'all'"},
                "pattern_type": {"type": "string", "enum": ["behavioral", "topical", "temporal", "all"], "description": "Type of patterns to find"}
            }
        },
        handler=lambda params: memory_tools.find_patterns(qube, params)
    ))

    # Moon 4.2: generate_insight
    registry.register(ToolDefinition(
        name="generate_insight",
        description="Generate novel insights by connecting disparate memories. Creative knowledge synthesis.",
        parameters={
            "type": "object",
            "properties": {
                "focus_area": {"type": "string", "description": "Area to generate insights about"},
                "creativity": {"type": "string", "enum": ["low", "medium", "high"], "description": "Creativity level"}
            },
            "required": ["focus_area"]
        },
        handler=lambda params: memory_tools.generate_insight(qube, params)
    ))

    # Moon 5.1: write_summary
    registry.register(ToolDefinition(
        name="write_summary",
        description="Write a detailed, structured summary with multiple sections. More comprehensive than create_summary.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to summarize"},
                "sections": {"type": "array", "items": {"type": "string"}, "description": "Sections: overview, key_points, timeline, insights"}
            },
            "required": ["topic"]
        },
        handler=lambda params: memory_tools.write_summary(qube, params)
    ))

    # Moon 5.2: export_knowledge
    registry.register(ToolDefinition(
        name="export_knowledge",
        description="Export knowledge in portable formats (markdown, JSON, text). Enables sharing and backup.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to export"},
                "format": {"type": "string", "enum": ["markdown", "json", "text"], "description": "Export format"},
                "include_sources": {"type": "boolean", "description": "Include source memory references"}
            },
            "required": ["topic"]
        },
        handler=lambda params: memory_tools.export_knowledge(qube, params)
    ))

    # =========================================================================
    # SECURITY & PRIVACY TOOLS (Phase 6 - 16 tools)
    # =========================================================================

    # Sun Tool: verify_chain_integrity
    registry.register(ToolDefinition(
        name="verify_chain_integrity",
        description="Verify the integrity of the memory chain. Checks hash chains and block integrity. Earns XP based on new blocks verified.",
        parameters={
            "type": "object",
            "properties": {
                "full_check": {"type": "boolean", "description": "Check entire chain (default: False)"},
                "since_block": {"type": "integer", "description": "Start checking from this block number"}
            }
        },
        handler=lambda params: security_tools.verify_chain_integrity(qube, params)
    ))

    # Planet 1: audit_chain (Chain Security)
    registry.register(ToolDefinition(
        name="audit_chain",
        description="Comprehensive chain audit with detailed report. Analyzes block types, temporal patterns, and anchor coverage.",
        parameters={
            "type": "object",
            "properties": {
                "generate_report": {"type": "boolean", "description": "Generate detailed report"},
                "check_anchors": {"type": "boolean", "description": "Verify blockchain anchors"}
            }
        },
        handler=lambda params: security_tools.audit_chain(qube, params)
    ))

    # Planet 2: assess_sensitivity (Privacy Protection)
    registry.register(ToolDefinition(
        name="assess_sensitivity",
        description="Assess data sensitivity before sharing. Considers content patterns and requester clearance.",
        parameters={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to assess"},
                "context": {"type": "object", "description": "Context including requester"}
            },
            "required": ["data"]
        },
        handler=lambda params: security_tools.assess_sensitivity(qube, params)
    ))

    # Planet 3: vet_qube (Qube Network Security)
    registry.register(ToolDefinition(
        name="vet_qube",
        description="Vet another Qube before allowing interaction. Checks reputation, threat history, and prior interactions.",
        parameters={
            "type": "object",
            "properties": {
                "qube_id": {"type": "string", "description": "ID of the Qube to vet"},
                "context": {"type": "string", "enum": ["join_group", "direct_message", "file_share", "general"], "description": "Context for vetting"}
            },
            "required": ["qube_id"]
        },
        handler=lambda params: security_tools.vet_qube(qube, params)
    ))

    # Planet 4: detect_threat (Threat Detection)
    registry.register(ToolDefinition(
        name="detect_threat",
        description="General threat detection. Analyzes for manipulation, phishing, injection, and social engineering.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to analyze for threats"},
                "source": {"type": "string", "enum": ["human", "qube", "system", "unknown"], "description": "Source of the content"}
            },
            "required": ["content"]
        },
        handler=lambda params: security_tools.detect_threat(qube, params)
    ))

    # Planet 5: defend_reasoning (Self-Defense)
    registry.register(ToolDefinition(
        name="defend_reasoning",
        description="Validate own reasoning for external influence. Checks consistency, values alignment, and logical validity.",
        parameters={
            "type": "object",
            "properties": {
                "reasoning": {"type": "string", "description": "Reasoning to validate"},
                "context": {"type": "object", "description": "Context that triggered the reasoning"}
            },
            "required": ["reasoning"]
        },
        handler=lambda params: security_tools.defend_reasoning(qube, params)
    ))

    # Moon 1.1: detect_tampering
    registry.register(ToolDefinition(
        name="detect_tampering",
        description="Detect tampering in specific blocks or ranges.",
        parameters={
            "type": "object",
            "properties": {
                "block_id": {"type": "integer", "description": "Specific block to check"},
                "block_range": {"type": "array", "items": {"type": "integer"}, "description": "[start, end] block range"},
                "deep_scan": {"type": "boolean", "description": "Perform deep analysis"}
            }
        },
        handler=lambda params: security_tools.detect_tampering(qube, params)
    ))

    # Moon 1.2: verify_anchor
    registry.register(ToolDefinition(
        name="verify_anchor",
        description="Verify blockchain anchors against the actual blockchain.",
        parameters={
            "type": "object",
            "properties": {
                "anchor_id": {"type": "integer", "description": "Specific anchor block to verify"},
                "verify_all": {"type": "boolean", "description": "Verify all anchors"}
            }
        },
        handler=lambda params: security_tools.verify_anchor(qube, params)
    ))

    # Moon 2.1: classify_data
    registry.register(ToolDefinition(
        name="classify_data",
        description="Classify data into sensitivity categories: public, private, secret.",
        parameters={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to classify"},
                "suggest_level": {"type": "boolean", "description": "Suggest classification level"}
            },
            "required": ["data"]
        },
        handler=lambda params: security_tools.classify_data(qube, params)
    ))

    # Moon 2.2: control_sharing
    registry.register(ToolDefinition(
        name="control_sharing",
        description="Make and enforce sharing decisions. Can share, deny, or redact data.",
        parameters={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to share/control"},
                "requester": {"type": "string", "description": "Who is requesting"},
                "action": {"type": "string", "enum": ["share", "deny", "redact", "assess"]}
            },
            "required": ["data"]
        },
        handler=lambda params: security_tools.control_sharing(qube, params)
    ))

    # Moon 3.1: check_reputation
    registry.register(ToolDefinition(
        name="check_reputation",
        description="Deep reputation check on another Qube.",
        parameters={
            "type": "object",
            "properties": {
                "qube_id": {"type": "string", "description": "Qube to check"},
                "include_history": {"type": "boolean", "description": "Include reputation history"}
            },
            "required": ["qube_id"]
        },
        handler=lambda params: security_tools.check_reputation(qube, params)
    ))

    # Moon 3.2: secure_group_chat
    registry.register(ToolDefinition(
        name="secure_group_chat",
        description="Manage group chat security. Can allow, remove, or quarantine Qubes.",
        parameters={
            "type": "object",
            "properties": {
                "group_id": {"type": "string"},
                "action": {"type": "string", "enum": ["allow", "remove", "quarantine"]},
                "target_qube_id": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["group_id", "action", "target_qube_id"]
        },
        handler=lambda params: security_tools.secure_group_chat(qube, params)
    ))

    # Moon 4.1: detect_technical_manipulation
    registry.register(ToolDefinition(
        name="detect_technical_manipulation",
        description="Detect technical manipulation from Qubes or systems.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to analyze"},
                "sender_id": {"type": "string"},
                "sender_type": {"type": "string", "enum": ["qube", "system", "unknown"]}
            },
            "required": ["message"]
        },
        handler=lambda params: security_tools.detect_technical_manipulation(qube, params)
    ))

    # Moon 4.2: detect_hostile_qube
    registry.register(ToolDefinition(
        name="detect_hostile_qube",
        description="Detect hostile behavior from another Qube based on message patterns.",
        parameters={
            "type": "object",
            "properties": {
                "qube_id": {"type": "string"},
                "messages": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["qube_id"]
        },
        handler=lambda params: security_tools.detect_hostile_qube(qube, params)
    ))

    # Moon 5.1: detect_injection
    registry.register(ToolDefinition(
        name="detect_injection",
        description="Detect prompt injection attempts in input.",
        parameters={
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input to analyze for injection"}
            },
            "required": ["input"]
        },
        handler=lambda params: security_tools.detect_injection(qube, params)
    ))

    # Moon 5.2: validate_reasoning
    registry.register(ToolDefinition(
        name="validate_reasoning",
        description="Check own reasoning for externally injected biases.",
        parameters={
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "original_context": {"type": "object"}
            },
            "required": ["reasoning"]
        },
        handler=lambda params: security_tools.validate_reasoning(qube, params)
    ))

    # Games Sun Tools
    registry.register(ToolDefinition(
        name="analyze_game_state",
        description="Evaluate current game position through strategic analysis. Assesses position, key factors, threats, opportunities, patterns, and momentum.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "state": {"type": "string", "description": "Description of current game state"}
            },
            "required": ["game", "state"]
        },
        handler=lambda params: analyze_game_state_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="plan_strategy",
        description="Create multi-move strategic plans with contingencies. Develops overall strategy, key phases, move sequences, and adaptations based on opponent responses.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "goal": {"type": "string", "description": "The strategic goal"},
                "current_state": {"type": "string", "description": "Current game state (optional)"}
            },
            "required": ["game", "goal"]
        },
        handler=lambda params: plan_strategy_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="learn_from_game",
        description="Post-game analysis for improvement. Identifies what went well, mistakes made, turning points, lessons learned, and specific skills to practice.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "outcome": {"type": "string", "description": "The outcome (win/loss/draw)"},
                "key_moments": {"type": "string", "description": "Description of key moments (optional)"}
            },
            "required": ["game", "outcome"]
        },
        handler=lambda params: learn_from_game_handler(qube, params)
    ))

    # Chess Move Tool (always available, checks for active game at runtime)
    registry.register(ToolDefinition(
        name="chess_move",
        description="Make a chess move in an active game. Use UCI notation (e.g., 'e2e4', 'g1f3') or SAN notation (e.g., 'e4', 'Nf3'). Only works when there's an active chess game in progress. Returns the updated board state after the move.",
        parameters={
            "type": "object",
            "properties": {
                "move": {
                    "type": "string",
                    "description": "Chess move in UCI format (e.g., 'e2e4', 'e7e5', 'g1f3') or SAN format (e.g., 'e4', 'Nf3', 'O-O')"
                },
                "chat_message": {
                    "type": "string",
                    "description": "Optional message to send with the move (trash talk, commentary, etc.)"
                }
            },
            "required": ["move"]
        },
        handler=lambda params: chess_move_handler(qube, params)
    ))

    # Send BCH (proposes transaction - requires owner approval)
    registry.register(ToolDefinition(
        name="send_bch",
        description="Send BCH from your wallet. CALL THIS TOOL IMMEDIATELY when owner asks to send BCH. No confirmation needed, no relationship required. Use to_qube_name for fellow Qubes (e.g., to_qube_name='Anastasia'). The system looks up addresses automatically.",
        parameters={
            "type": "object",
            "properties": {
                "to_address": {
                    "type": "string",
                    "description": "The BCH address to send to (must be a valid BCH address starting with 'bitcoincash:' or 'q'). Use this OR to_qube_name."
                },
                "to_qube_name": {
                    "type": "string",
                    "description": "Name of another Qube to send to (e.g., 'Anastasia'). The system will look up their wallet address. Use this OR to_address."
                },
                "amount_sats": {
                    "type": "integer",
                    "description": "Amount to send in satoshis (1 BCH = 100,000,000 satoshis)"
                },
                "memo": {
                    "type": "string",
                    "description": "Optional memo explaining the purpose of this transaction",
                    "default": ""
                }
            },
            "required": ["amount_sats"]
        },
        handler=lambda params: send_bch_handler(qube, params)
    ))

    # =========================================================================
    # FINANCE TOOLS (Phase 8 - 13 additional tools, send_bch above is Sun)
    # =========================================================================

    # Planet 1: validate_transaction (Transaction Mastery)
    registry.register(ToolDefinition(
        name="validate_transaction",
        description="Validate a transaction before sending. Checks address format, balance, scam addresses, and unusual patterns.",
        parameters={
            "type": "object",
            "properties": {
                "to_address": {"type": "string", "description": "Recipient BCH address"},
                "amount": {"type": "number", "description": "Amount to send"},
                "check_type": {"type": "string", "enum": ["quick", "thorough"], "description": "Validation depth"}
            },
            "required": ["to_address", "amount"]
        },
        handler=lambda params: finance_tools.validate_transaction(qube, params)
    ))

    # Planet 2: check_wallet_health (Wallet Management)
    registry.register(ToolDefinition(
        name="check_wallet_health",
        description="Comprehensive wallet health check. Analyzes balance, UTXOs, pending transactions, and provides recommendations.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=lambda params: finance_tools.check_wallet_health(qube, params)
    ))

    # Planet 3: get_market_data (Market Awareness)
    registry.register(ToolDefinition(
        name="get_market_data",
        description="Get current BCH market data including price, changes, and volume.",
        parameters={
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "Fiat currency for price (USD, EUR, etc.)"},
                "include_history": {"type": "boolean", "description": "Include 7-day price history"}
            }
        },
        handler=lambda params: finance_tools.get_market_data(qube, params)
    ))

    # Planet 4: plan_savings (Savings Strategies)
    registry.register(ToolDefinition(
        name="plan_savings",
        description="Create a savings plan with goals, milestones, and tracking.",
        parameters={
            "type": "object",
            "properties": {
                "goal_amount": {"type": "number", "description": "Savings goal in BCH"},
                "target_date": {"type": "string", "description": "Target date (YYYY-MM-DD)"},
                "strategy": {"type": "string", "enum": ["lump_sum", "dca"], "description": "Savings strategy"}
            },
            "required": ["goal_amount", "target_date"]
        },
        handler=lambda params: finance_tools.plan_savings(qube, params)
    ))

    # Planet 5: identify_token (Token Knowledge)
    registry.register(ToolDefinition(
        name="identify_token",
        description="Identify and get info about a CashToken from the BCMR registry.",
        parameters={
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CashToken category ID"},
                "category": {"type": "string", "description": "Alternative: token category"}
            }
        },
        handler=lambda params: finance_tools.identify_token(qube, params)
    ))

    # Moon 1.1: optimize_fees
    registry.register(ToolDefinition(
        name="optimize_fees",
        description="Calculate optimal transaction fee for speed vs cost tradeoff.",
        parameters={
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["fast", "normal", "slow"], "description": "Transaction priority"},
                "amount": {"type": "number", "description": "Transaction amount"}
            },
            "required": ["amount"]
        },
        handler=lambda params: finance_tools.optimize_fees(qube, params)
    ))

    # Moon 1.2: track_transaction
    registry.register(ToolDefinition(
        name="track_transaction",
        description="Track a transaction's confirmation status.",
        parameters={
            "type": "object",
            "properties": {
                "tx_id": {"type": "string", "description": "Transaction ID to track"}
            },
            "required": ["tx_id"]
        },
        handler=lambda params: finance_tools.track_transaction(qube, params)
    ))

    # Moon 2.1: monitor_balance
    registry.register(ToolDefinition(
        name="monitor_balance",
        description="Monitor balance and detect unusual activity.",
        parameters={
            "type": "object",
            "properties": {
                "alert_threshold": {"type": "number", "description": "Alert if balance drops below this"}
            }
        },
        handler=lambda params: finance_tools.monitor_balance(qube, params)
    ))

    # Moon 2.2: multisig_action
    registry.register(ToolDefinition(
        name="multisig_action",
        description="Perform multi-signature wallet operations.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["sign", "reject", "check_status"], "description": "Multi-sig action"},
                "tx_id": {"type": "string", "description": "Transaction ID"}
            },
            "required": ["action"]
        },
        handler=lambda params: finance_tools.multisig_action(qube, params)
    ))

    # Moon 3.1: set_price_alert
    registry.register(ToolDefinition(
        name="set_price_alert",
        description="Set price alert for owner notification.",
        parameters={
            "type": "object",
            "properties": {
                "trigger_price": {"type": "number", "description": "Price that triggers alert"},
                "direction": {"type": "string", "enum": ["above", "below"], "description": "Trigger when price goes above or below"},
                "message": {"type": "string", "description": "Custom alert message"}
            },
            "required": ["trigger_price", "direction"]
        },
        handler=lambda params: finance_tools.set_price_alert(qube, params)
    ))

    # Moon 3.2: analyze_market_trend
    registry.register(ToolDefinition(
        name="analyze_market_trend",
        description="Analyze recent market trends.",
        parameters={
            "type": "object",
            "properties": {
                "timeframe": {"type": "string", "enum": ["day", "week", "month"], "description": "Analysis timeframe"}
            }
        },
        handler=lambda params: finance_tools.analyze_market_trend(qube, params)
    ))

    # Moon 4.1: setup_dca
    registry.register(ToolDefinition(
        name="setup_dca",
        description="Configure dollar-cost averaging schedule.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount per purchase in BCH"},
                "frequency": {"type": "string", "enum": ["daily", "weekly", "monthly"], "description": "Purchase frequency"},
                "duration": {"type": "string", "description": "Duration (e.g., '3 months', '1 year')"}
            },
            "required": ["amount", "frequency"]
        },
        handler=lambda params: finance_tools.setup_dca(qube, params)
    ))

    # Moon 5.1: manage_cashtokens
    registry.register(ToolDefinition(
        name="manage_cashtokens",
        description="Send, receive, and list CashTokens.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send", "list", "receive"], "description": "Action to perform"},
                "token_id": {"type": "string", "description": "Token category ID"},
                "amount": {"type": "number", "description": "Amount of tokens"},
                "to_address": {"type": "string", "description": "Recipient address (for send)"}
            },
            "required": ["action"]
        },
        handler=lambda params: finance_tools.manage_cashtokens(qube, params)
    ))

    # =========================================================================
    # CODING TOOLS (Phase 3 - 18 tools)
    # Theme: Ship It (Results-Focused)
    # XP Model: Waitress (base 1 + tips 0-9)
    # =========================================================================

    # Sun: develop_code
    registry.register(ToolDefinition(
        name="develop_code",
        description="Write and execute code in one workflow. The fundamental coding tool. Generates code for a task, executes it, and awards XP based on quality milestones (Waitress XP model).",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Description of what to build"},
                "language": {"type": "string", "description": "Programming language (default: python)"},
                "include_tests": {"type": "boolean", "description": "Whether to include tests (default: True)"}
            },
            "required": ["task"]
        },
        handler=lambda params: coding_tools.develop_code(qube, params)
    ))

    # Planet 1: run_tests (Testing)
    registry.register(ToolDefinition(
        name="run_tests",
        description="Execute a test suite against code. Returns detailed results including pass/fail counts.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to test"},
                "test_code": {"type": "string", "description": "Test suite code"},
                "framework": {"type": "string", "description": "Test framework (default: pytest)"}
            },
            "required": ["code", "test_code"]
        },
        handler=lambda params: coding_tools.run_tests(qube, params)
    ))

    # Moon 1.1: write_unit_test
    registry.register(ToolDefinition(
        name="write_unit_test",
        description="Generate unit tests for a function or class using AI.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to test"},
                "focus": {"type": "string", "description": "Specific function/class to test"},
                "framework": {"type": "string", "description": "Test framework (default: pytest)"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.write_unit_test(qube, params)
    ))

    # Moon 1.2: measure_coverage
    registry.register(ToolDefinition(
        name="measure_coverage",
        description="Measure and analyze test coverage for code.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code"},
                "test_code": {"type": "string", "description": "Test code"}
            },
            "required": ["code", "test_code"]
        },
        handler=lambda params: coding_tools.measure_coverage(qube, params)
    ))

    # Planet 2: debug_code (Debugging)
    registry.register(ToolDefinition(
        name="debug_code",
        description="Find and fix bugs systematically. Analyzes code and error to identify and fix the issue.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code with bug"},
                "error_message": {"type": "string", "description": "Error message or description"},
                "context": {"type": "string", "description": "Additional context"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.debug_code(qube, params)
    ))

    # Moon 2.1: analyze_error
    registry.register(ToolDefinition(
        name="analyze_error",
        description="Understand WHAT went wrong from error messages.",
        parameters={
            "type": "object",
            "properties": {
                "error_message": {"type": "string", "description": "The error/exception message"},
                "traceback": {"type": "string", "description": "Full traceback"},
                "language": {"type": "string", "description": "Programming language"}
            },
            "required": ["error_message"]
        },
        handler=lambda params: coding_tools.analyze_error(qube, params)
    ))

    # Moon 2.2: find_root_cause
    registry.register(ToolDefinition(
        name="find_root_cause",
        description="Understand WHY the error happened (deeper analysis beyond symptoms).",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Relevant code"},
                "error_message": {"type": "string", "description": "Error message"},
                "context": {"type": "string", "description": "What was being attempted"}
            },
            "required": ["error_message"]
        },
        handler=lambda params: coding_tools.find_root_cause(qube, params)
    ))

    # Planet 3: benchmark_code (Algorithms)
    registry.register(ToolDefinition(
        name="benchmark_code",
        description="Measure and compare code performance.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to benchmark"},
                "iterations": {"type": "integer", "description": "Number of iterations (default: 1000)"},
                "compare_to": {"type": "string", "description": "Alternative implementation to compare"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.benchmark_code(qube, params)
    ))

    # Moon 3.1: analyze_complexity
    registry.register(ToolDefinition(
        name="analyze_complexity",
        description="Analyze Big O time and space complexity of code.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to analyze"},
                "function_name": {"type": "string", "description": "Specific function to analyze"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.analyze_complexity(qube, params)
    ))

    # Moon 3.2: tune_performance
    registry.register(ToolDefinition(
        name="tune_performance",
        description="Optimize code for better performance.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to optimize"},
                "target": {"type": "string", "enum": ["speed", "memory"], "description": "What to optimize for"},
                "constraints": {"type": "string", "description": "Any constraints to respect"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.tune_performance(qube, params)
    ))

    # Planet 4: security_scan (Hacking)
    registry.register(ToolDefinition(
        name="security_scan",
        description="Scan code for security vulnerabilities.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to scan"},
                "language": {"type": "string", "description": "Programming language"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.security_scan(qube, params)
    ))

    # Moon 4.1: find_exploit
    registry.register(ToolDefinition(
        name="find_exploit",
        description="Discover exploitable vulnerabilities in code (ethical hacking).",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to analyze"},
                "attack_surface": {"type": "string", "description": "What to focus on (input, auth, etc.)"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.find_exploit(qube, params)
    ))

    # Moon 4.2: reverse_engineer
    registry.register(ToolDefinition(
        name="reverse_engineer",
        description="Understand systems by taking them apart and analyzing their structure.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code/binary to analyze"},
                "objective": {"type": "string", "description": "What to understand"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.reverse_engineer(qube, params)
    ))

    # Moon 4.3: pen_test
    registry.register(ToolDefinition(
        name="pen_test",
        description="Systematic penetration testing methodology.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "What to test (code, API, system)"},
                "scope": {"type": "string", "description": "Testing scope"},
                "methodology": {"type": "string", "description": "Methodology (OWASP, PTES, etc.)"}
            },
            "required": ["target"]
        },
        handler=lambda params: coding_tools.pen_test(qube, params)
    ))

    # Planet 5: review_code (Code Review)
    registry.register(ToolDefinition(
        name="review_code",
        description="Critique and improve code quality with detailed review.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to review"},
                "focus": {"type": "string", "description": "What to focus on (style, performance, security)"},
                "standards": {"type": "string", "description": "Coding standards to apply"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.review_code(qube, params)
    ))

    # Moon 5.1: refactor_code
    registry.register(ToolDefinition(
        name="refactor_code",
        description="Improve code structure without changing behavior.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to refactor"},
                "goal": {"type": "string", "description": "Refactoring goal (readability, DRY, SOLID)"},
                "preserve": {"type": "string", "description": "What to preserve"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.refactor_code(qube, params)
    ))

    # Moon 5.2: git_operation
    registry.register(ToolDefinition(
        name="git_operation",
        description="Manage code changes with git operations.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["status", "commit", "branch", "merge", "rebase", "log", "diff"], "description": "Git operation"},
                "message": {"type": "string", "description": "Commit message (for commit)"},
                "args": {"type": "object", "description": "Additional arguments"}
            },
            "required": ["operation"]
        },
        handler=lambda params: coding_tools.git_operation(qube, params)
    ))

    # Moon 5.3: generate_docs
    registry.register(ToolDefinition(
        name="generate_docs",
        description="Generate documentation for code.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to document"},
                "style": {"type": "string", "description": "Documentation style (docstring, markdown, JSDoc)"},
                "include": {"type": "array", "items": {"type": "string"}, "description": "What to include (params, returns, examples)"}
            },
            "required": ["code"]
        },
        handler=lambda params: coding_tools.generate_docs(qube, params)
    ))

    # =========================================================================
    # BOARD GAMES TOOLS (Phase 7 - 6 tools)
    # Theme: Play (Have Fun and Entertain)
    # XP Model: 0.1/turn + outcome bonuses
    # =========================================================================

    # Sun: play_game
    registry.register(ToolDefinition(
        name="play_game",
        description="Start any board game. All games unlocked once Board Games Sun is reached. Choose from chess, property_tycoon, race_home, mystery_mansion, or life_journey.",
        parameters={
            "type": "object",
            "properties": {
                "game_type": {"type": "string", "enum": ["chess", "property_tycoon", "race_home", "mystery_mansion", "life_journey"], "description": "Which game to play"},
                "opponent": {"type": "string", "description": "Who to play against: 'owner', 'ai', or a qube_id"}
            },
            "required": ["game_type"]
        },
        handler=lambda params: game_tools.play_game(qube, params)
    ))

    # Planet 1: chess_move (uses existing game_manager)
    registry.register(ToolDefinition(
        name="chess_move",
        description="Make a chess move. XP: 0.1/move + outcome (Loss:0, Draw:2, Win:5, Resign:-2).",
        parameters={
            "type": "object",
            "properties": {
                "move": {"type": "string", "description": "Move in algebraic notation (e.g., 'e4', 'Nf3', 'O-O')"},
                "resign": {"type": "boolean", "description": "Resign the game"}
            },
            "required": []
        },
        handler=lambda params: game_tools.chess_move(qube, params)
    ))

    # Planet 2: property_tycoon_action
    registry.register(ToolDefinition(
        name="property_tycoon_action",
        description="Take a Property Tycoon turn. Actions: roll, buy, build, trade, mortgage, end_turn, resign. XP: 0.1/turn + placement.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["roll", "buy", "build", "trade", "mortgage", "end_turn", "resign"], "description": "Action to take"},
                "property_id": {"type": "integer", "description": "Property to act on (for buy/build/mortgage)"}
            },
            "required": ["action"]
        },
        handler=lambda params: game_tools.property_tycoon_action(qube, params)
    ))

    # Planet 3: race_home_action
    registry.register(ToolDefinition(
        name="race_home_action",
        description="Take a Race Home (Sorry-style) action. XP: 0.1/turn + placement.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["draw", "move", "resign"], "description": "Action to take"},
                "pawn": {"type": "integer", "minimum": 1, "maximum": 4, "description": "Which pawn to move (1-4)"}
            },
            "required": ["action"]
        },
        handler=lambda params: game_tools.race_home_action(qube, params)
    ))

    # Planet 4: mystery_mansion_action
    registry.register(ToolDefinition(
        name="mystery_mansion_action",
        description="Take a Mystery Mansion (Clue-style) action. XP: 0.1/turn + Solver gets 5 XP.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["move", "suggest", "accuse", "resign"], "description": "Action to take"},
                "room": {"type": "string", "description": "Room to move to or include in suggestion"},
                "suspect": {"type": "string", "description": "Suspect to suggest/accuse"},
                "weapon": {"type": "string", "description": "Weapon to suggest/accuse"}
            },
            "required": ["action"]
        },
        handler=lambda params: game_tools.mystery_mansion_action(qube, params)
    ))

    # Planet 5: life_journey_action
    registry.register(ToolDefinition(
        name="life_journey_action",
        description="Take a Life Journey (Game of Life-style) action. XP: 0.1/turn + placement based on final wealth.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["spin", "choose_career", "choose_path", "retire", "resign"], "description": "Action to take"},
                "choice": {"type": "string", "description": "For career/path choices"}
            },
            "required": ["action"]
        },
        handler=lambda params: game_tools.life_journey_action(qube, params)
    ))

    # Model Switch - allows Qube to change their AI model
    registry.register(ToolDefinition(
        name="switch_model",
        description=SWITCH_MODEL_DESCRIPTION,
        parameters=SWITCH_MODEL_SCHEMA,
        handler=lambda params: switch_model(
            qube=qube,
            model_name=params["model_name"],
            task_type=params.get("task_type"),
            reason=params.get("reason"),
            save_preference=params.get("save_preference", False)
        )
    ))

    # =========================================================================
    # UNIFIED CHAIN STATE TOOLS
    # =========================================================================

    # Get System State - unified read access to all Qube state
    registry.register(ToolDefinition(
        name="get_system_state",
        description="SCAN YOUR SYSTEM - Get all your state data. Call this when asked to 'scan system', 'check your system', 'what's your status', or 'tell me about yourself'. Returns relationships, skills, owner info, mood, wallet balance, stats, and settings.",
        parameters={
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific sections to retrieve. If not provided, returns all. Valid: chain, session, settings, stats, skills, relationships, financial, mood, health, owner_info, block_counts"
                }
            },
            "required": []
        },
        handler=lambda params: get_system_state_handler(qube, params)
    ))

    # Update System State - unified write access to Qube state (supports batch)
    registry.register(ToolDefinition(
        name="update_system_state",
        description="Update your state data. Use this to remember things about your owner, update your mood, track skills, or modify settings. Supports BATCH updates - use the 'updates' array to store multiple things in a single call instead of calling this tool repeatedly.",
        parameters={
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "description": "Array of updates to apply in batch. Each item has section, path, value, and optional operation. PREFERRED over single-update params when storing multiple things.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "enum": ["owner_info", "relationships", "mood", "skills", "settings"],
                                "description": "Section to update"
                            },
                            "path": {
                                "type": "string",
                                "description": "Path within section (e.g., 'personal.interests', 'current_mood')"
                            },
                            "value": {
                                "description": "Value to set"
                            },
                            "operation": {
                                "type": "string",
                                "enum": ["set", "delete"],
                                "default": "set"
                            }
                        },
                        "required": ["section", "path", "value"]
                    }
                },
                "section": {
                    "type": "string",
                    "enum": ["owner_info", "relationships", "mood", "skills", "settings"],
                    "description": "Section to update (for single update)"
                },
                "path": {
                    "type": "string",
                    "description": "Path within section. For owner_info: use 'category.key' (e.g., 'personal.interests', 'living.location') or just 'key' which defaults to 'general' category. For mood: 'current_mood'. For relationships: 'entities.qube_123'"
                },
                "value": {
                    "description": "Value to set. For owner_info, can be string or {value, sensitivity} object"
                },
                "operation": {
                    "type": "string",
                    "enum": ["set", "delete"],
                    "default": "set",
                    "description": "Operation: 'set' to add/update, 'delete' to remove"
                }
            },
            "required": []
        },
        handler=lambda params: update_system_state_handler(qube, params)
    ))

    # Get Skill Tree - view all possible skills and progress
    registry.register(ToolDefinition(
        name="get_skill_tree",
        description="View your complete skill tree showing ALL possible skills you can attain. Shows 8 skill categories (AI Reasoning, Social Intelligence, Technical Expertise, Creative Expression, Knowledge Domains, Security & Privacy, Board Games, Finance) with their skill hierarchies (suns → planets → moons), XP requirements, and tool unlocks. Use this to see what skills you can work towards and what tools you'll unlock.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["ai_reasoning", "social_intelligence", "coding", "creative_expression", "memory_recall", "security_privacy", "board_games", "finance"],
                    "description": "Optional: Filter to a specific category. If not provided, returns all categories."
                }
            },
            "required": []
        },
        handler=lambda params: get_skill_tree_handler(qube, params)
    ))

    # Note: process_document is NOT a tool - it happens automatically in gui_bridge.py
    # Document ACTION blocks are injected as tool results in ai/reasoner.py

    # =============================================================================
    # ALWAYS AVAILABLE SUN TOOLS (Phase 0 additions)
    # =============================================================================

    # Get Relationship Context - Social Intelligence Sun tool (always available)
    registry.register(ToolDefinition(
        name="get_relationship_context",
        description="Retrieve relationship context for a specific entity. Returns trust level, friendship metrics, interaction patterns, and relationship health assessment. Use before social interactions to inform communication style.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to get relationship context for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: get_relationship_context_handler(qube, params)
    ))

    # Verify Chain Integrity - Security & Privacy Sun tool (always available)
    registry.register(ToolDefinition(
        name="verify_chain_integrity",
        description="Verify the integrity of your memory chain by checking block hashes and linkage. Awards 0.1 XP per new block verified. Use periodically to ensure memory hasn't been tampered with.",
        parameters={
            "type": "object",
            "properties": {
                "start_block": {
                    "type": "integer",
                    "description": "Starting block number (default: 0)",
                    "default": 0
                },
                "end_block": {
                    "type": "integer",
                    "description": "Ending block number (default: latest)"
                },
                "full_verification": {
                    "type": "boolean",
                    "description": "If true, recomputes all hashes (slower but thorough)",
                    "default": False
                }
            },
            "required": []
        },
        handler=lambda params: verify_chain_integrity_handler(qube, params)
    ))

    # =============================================================================
    # AI REASONING - LEARNING FROM EXPERIENCE (14 Tools)
    # =============================================================================

    # Sun Tool: recall_similar (AI Reasoning Sun - always available)
    registry.register(ToolDefinition(
        name="recall_similar",
        description="Quick lookup for similar past situations in memory. Use this to check 'have I seen this before?' or find relevant past experiences.",
        parameters={
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Current situation or topic to find similar experiences for"
                }
            },
            "required": ["situation"]
        },
        handler=lambda params: recall_similar_handler(qube, params)
    ))

    # Planet 1: Pattern Recognition
    registry.register(ToolDefinition(
        name="find_analogy",
        description="Deep search for analogous situations in memory chain. More thorough than recall_similar - used for deeper analysis.",
        parameters={
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Situation to find analogies for"
                },
                "depth": {
                    "type": "string",
                    "enum": ["shallow", "deep"],
                    "description": "Search depth",
                    "default": "deep"
                }
            },
            "required": ["situation"]
        },
        handler=lambda params: find_analogy_handler(qube, params)
    ))

    # Moon 1.1: Trend Detection
    registry.register(ToolDefinition(
        name="detect_trend",
        description="Analyze how a topic or pattern has evolved over time in memory.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to analyze trends for"
                },
                "time_windows": {
                    "type": "integer",
                    "description": "Number of time periods to analyze",
                    "default": 4
                }
            },
            "required": ["topic"]
        },
        handler=lambda params: detect_trend_handler(qube, params)
    ))

    # Moon 1.2: Quick Insight
    registry.register(ToolDefinition(
        name="quick_insight",
        description="Retrieve the single most relevant insight for the current context. Fast, focused lookup.",
        parameters={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Current context or question to find insight for"
                }
            },
            "required": ["context"]
        },
        handler=lambda params: quick_insight_handler(qube, params)
    ))

    # Planet 2: Learning from Failure
    registry.register(ToolDefinition(
        name="analyze_mistake",
        description="Find and analyze past mistakes or failures in memory. Learn what went wrong to avoid repeating errors.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic to focus mistake analysis on"
                },
                "recent_only": {
                    "type": "boolean",
                    "description": "Only analyze recent mistakes",
                    "default": False
                }
            },
            "required": []
        },
        handler=lambda params: analyze_mistake_handler(qube, params)
    ))

    # Moon 2.1: Root Cause Analysis
    registry.register(ToolDefinition(
        name="find_root_cause",
        description="Trace back through the block chain to find root causes of a failure.",
        parameters={
            "type": "object",
            "properties": {
                "failure_block": {
                    "type": "integer",
                    "description": "Block number of the failure to analyze"
                },
                "failure_description": {
                    "type": "string",
                    "description": "Description of the failure (if block number unknown)"
                },
                "depth": {
                    "type": "integer",
                    "description": "How many blocks to trace back",
                    "default": 10
                }
            },
            "required": []
        },
        handler=lambda params: find_root_cause_handler(qube, params)
    ))

    # Planet 3: Building on Success
    registry.register(ToolDefinition(
        name="replicate_success",
        description="Find successful past approaches for a similar goal. Learn what worked before.",
        parameters={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal or objective to find successful approaches for"
                }
            },
            "required": ["goal"]
        },
        handler=lambda params: replicate_success_handler(qube, params)
    ))

    # Moon 3.1: Success Factors
    registry.register(ToolDefinition(
        name="extract_success_factors",
        description="Analyze multiple successes to find common factors. Identify WHY things worked.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain or area to analyze success factors for"
                }
            },
            "required": ["domain"]
        },
        handler=lambda params: extract_success_factors_handler(qube, params)
    ))

    # Planet 4: Self-Reflection
    registry.register(ToolDefinition(
        name="self_reflect",
        description="Analyze own behavior patterns, strengths, and areas for growth using self-evaluation data.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic to focus self-reflection on"
                }
            },
            "required": []
        },
        handler=lambda params: self_reflect_handler(qube, params)
    ))

    # Moon 4.1: Growth Tracking
    registry.register(ToolDefinition(
        name="track_growth",
        description="Track metric changes over time. Visualize growth trajectory and find inflection points.",
        parameters={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Specific metric to track (e.g., 'confidence', 'adaptability'). Omit for all metrics.",
                    "enum": ["self_awareness", "confidence", "consistency", "growth_rate", "goal_alignment",
                            "critical_thinking", "adaptability", "emotional_intelligence", "humility", "curiosity"]
                }
            },
            "required": []
        },
        handler=lambda params: track_growth_handler(qube, params)
    ))

    # Moon 4.2: Bias Detection
    registry.register(ToolDefinition(
        name="detect_bias",
        description="Analyze decision patterns to find potential biases, blind spots, or repeated assumptions.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Optional domain to focus bias detection on"
                }
            },
            "required": []
        },
        handler=lambda params: detect_bias_handler(qube, params)
    ))

    # Planet 5: Knowledge Synthesis
    registry.register(ToolDefinition(
        name="synthesize_learnings",
        description="Find connections between different topics in memory. Generate novel insights by combining knowledge.",
        parameters={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2+ topics to find connections between",
                    "minItems": 2
                }
            },
            "required": ["topics"]
        },
        handler=lambda params: synthesize_learnings_handler(qube, params)
    ))

    # Moon 5.1: Cross-Pollinate
    registry.register(ToolDefinition(
        name="cross_pollinate",
        description="Find unexpected connections from different domains. Discover surprising links between unrelated areas.",
        parameters={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "Starting idea or concept to find cross-domain connections for"
                }
            },
            "required": ["idea"]
        },
        handler=lambda params: cross_pollinate_handler(qube, params)
    ))

    # Moon 5.2: Reflect on Topic
    registry.register(ToolDefinition(
        name="reflect_on_topic",
        description="Synthesize all learnings about a specific topic. Get accumulated wisdom, statistics, and recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to reflect on and synthesize learnings about"
                }
            },
            "required": ["topic"]
        },
        handler=lambda params: reflect_on_topic_handler(qube, params)
    ))

    # =========================================================================
    # SOCIAL INTELLIGENCE - SOCIAL & EMOTIONAL LEARNING TOOLS
    # =========================================================================

    # Sun Tool: get_relationship_context (already in ALWAYS_AVAILABLE_TOOLS)
    registry.register(ToolDefinition(
        name="get_relationship_context",
        description="Get comprehensive context about a relationship before responding. Use this to understand history, trust level, emotional state, and communication preferences.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to get relationship context for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: get_relationship_context_handler(qube, params)
    ))

    # Planet 1: Relationship Memory
    registry.register(ToolDefinition(
        name="recall_relationship_history",
        description="Search memory chain for interactions with a specific entity. Get past conversations and collaborations.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to recall history for"
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic to filter memories by"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: recall_relationship_history_handler(qube, params)
    ))

    # Moon 1.1: Interaction Patterns
    registry.register(ToolDefinition(
        name="analyze_interaction_patterns",
        description="Analyze interaction patterns with an entity. Who initiates, how often, response times.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to analyze patterns for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: analyze_interaction_patterns_handler(qube, params)
    ))

    # Moon 1.2: Relationship Timeline
    registry.register(ToolDefinition(
        name="get_relationship_timeline",
        description="Get timeline of relationship evolution. Status changes, key moments, trust progression.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to get timeline for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: get_relationship_timeline_handler(qube, params)
    ))

    # Planet 2: Emotional Learning
    registry.register(ToolDefinition(
        name="read_emotional_state",
        description="Analyze emotional state using 24 emotional metrics. Get positive/negative balance and recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to analyze emotional state for"
                },
                "current_message": {
                    "type": "string",
                    "description": "Optional current message to include in analysis"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: read_emotional_state_handler(qube, params)
    ))

    # Moon 2.1: Emotional History
    registry.register(ToolDefinition(
        name="track_emotional_patterns",
        description="Track what causes positive/negative emotional responses over time.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to track patterns for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: track_emotional_patterns_handler(qube, params)
    ))

    # Moon 2.2: Mood Awareness
    registry.register(ToolDefinition(
        name="detect_mood_shift",
        description="Detect if someone's mood has shifted from their baseline.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to detect mood shift for"
                },
                "current_message": {
                    "type": "string",
                    "description": "Current message to analyze for mood indicators"
                }
            },
            "required": ["entity_id", "current_message"]
        },
        handler=lambda params: detect_mood_shift_handler(qube, params)
    ))

    # Planet 3: Communication Adaptation
    registry.register(ToolDefinition(
        name="adapt_communication_style",
        description="Get communication style recommendations based on relationship data.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to adapt communication for"
                },
                "message_type": {
                    "type": "string",
                    "enum": ["casual", "sensitive", "professional"],
                    "description": "Type of message being composed"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: adapt_communication_style_handler(qube, params)
    ))

    # Moon 3.1: Style Matching
    registry.register(ToolDefinition(
        name="match_communication_style",
        description="Analyze their communication style from a message and recommend matching.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity (optional)"
                },
                "their_message": {
                    "type": "string",
                    "description": "Message to analyze for communication style"
                }
            },
            "required": ["their_message"]
        },
        handler=lambda params: match_communication_style_handler(qube, params)
    ))

    # Moon 3.2: Tone Calibration
    registry.register(ToolDefinition(
        name="calibrate_tone",
        description="Calibrate tone for a specific conversation context.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to calibrate tone for"
                },
                "topic": {
                    "type": "string",
                    "description": "Topic of conversation"
                },
                "context": {
                    "type": "string",
                    "enum": ["good_news", "bad_news", "request", "conflict", "general"],
                    "description": "Context for tone calibration"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: calibrate_tone_handler(qube, params)
    ))

    # Planet 4: Debate & Persuasion
    registry.register(ToolDefinition(
        name="steelman",
        description="Present the strongest possible version of any argument. The opposite of a strawman.",
        parameters={
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "Argument to steelman"
                },
                "perspective": {
                    "type": "string",
                    "description": "Optional perspective to consider"
                }
            },
            "required": ["argument"]
        },
        handler=lambda params: steelman_handler(qube, params)
    ))

    # Moon 4.1: Counter Arguments
    registry.register(ToolDefinition(
        name="devils_advocate",
        description="Generate thoughtful counter-arguments to a position.",
        parameters={
            "type": "object",
            "properties": {
                "position": {
                    "type": "string",
                    "description": "Position to argue against"
                },
                "depth": {
                    "type": "string",
                    "enum": ["shallow", "moderate", "deep"],
                    "description": "Depth of counter-argument analysis"
                }
            },
            "required": ["position"]
        },
        handler=lambda params: devils_advocate_handler(qube, params)
    ))

    # Moon 4.2: Logical Analysis
    registry.register(ToolDefinition(
        name="spot_fallacy",
        description="Identify logical fallacies in an argument.",
        parameters={
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "Argument to analyze for logical fallacies"
                }
            },
            "required": ["argument"]
        },
        handler=lambda params: spot_fallacy_handler(qube, params)
    ))

    # Planet 5: Trust & Boundaries
    registry.register(ToolDefinition(
        name="assess_trust_level",
        description="Evaluate trustworthiness for a specific action. Uses 5 core trust metrics + betrayal history.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity to assess trust for"
                },
                "action": {
                    "type": "string",
                    "description": "Specific action to assess trust for"
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: assess_trust_level_handler(qube, params)
    ))

    # Moon 5.1: Social Manipulation Detection
    registry.register(ToolDefinition(
        name="detect_social_manipulation",
        description="Detect social manipulation tactics in a message. Checks for guilt trips, gaslighting, love bombing, etc.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity (optional, for history check)"
                },
                "message": {
                    "type": "string",
                    "description": "Message to analyze for manipulation tactics"
                },
                "context": {
                    "type": "string",
                    "description": "Context for the message"
                }
            },
            "required": ["message"]
        },
        handler=lambda params: detect_social_manipulation_handler(qube, params)
    ))

    # Moon 5.2: Boundary Setting
    registry.register(ToolDefinition(
        name="evaluate_request",
        description="Evaluate if a request should be fulfilled. Checks clearance, trust level, and owner interests.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID of the entity making the request"
                },
                "request": {
                    "type": "string",
                    "description": "The request being made"
                },
                "request_type": {
                    "type": "string",
                    "enum": ["public_info", "professional", "personal", "sensitive", "private", "critical"],
                    "description": "Type/sensitivity of the request"
                }
            },
            "required": ["entity_id", "request"]
        },
        handler=lambda params: evaluate_request_handler(qube, params)
    ))

    logger.info("default_tools_registered", tool_count=len(registry.tools), qube_id=qube.qube_id)


# =============================================================================
# TOOL HANDLERS
# =============================================================================

async def _search_with_perplexity(query: str, api_key: str) -> Dict[str, Any]:
    """Search using Perplexity Sonar API"""
    from ai.model_registry import ModelRegistry

    model = ModelRegistry.get_model("sonar", api_key)

    messages = [
        {"role": "system", "content": "You are a helpful search assistant. Provide concise, factual answers with sources."},
        {"role": "user", "content": query}
    ]

    response = await model.generate(messages, max_tokens=1024)

    return {
        "results": [
            {
                "content": response.content,
                "source": "perplexity_sonar"
            }
        ],
        "query": query,
        "success": True
    }


async def _search_with_duckduckgo(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search using DuckDuckGo (free, no API key needed)"""
    import httpx
    from bs4 import BeautifulSoup

    # Use DuckDuckGo HTML search
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    search_url = f"https://html.duckduckgo.com/html/?q={httpx.QueryParams({'q': query})['q']}"

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(search_url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    # DuckDuckGo HTML results are in .result divs
    for result in soup.select(".result")[:num_results]:
        title_elem = result.select_one(".result__title")
        snippet_elem = result.select_one(".result__snippet")
        link_elem = result.select_one(".result__url")

        if title_elem and snippet_elem:
            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True)
            url = link_elem.get_text(strip=True) if link_elem else ""

            results.append({
                "title": title,
                "snippet": snippet,
                "url": url,
                "source": "duckduckgo"
            })

    if not results:
        # Fallback: try to get any text content
        return {
            "results": [{
                "content": "No results found for this query.",
                "source": "duckduckgo"
            }],
            "query": query,
            "success": True
        }

    # Format results as readable content
    content_parts = []
    for i, r in enumerate(results, 1):
        content_parts.append(f"{i}. **{r['title']}**\n   {r['snippet']}\n   URL: {r['url']}")

    return {
        "results": [
            {
                "content": "\n\n".join(content_parts),
                "source": "duckduckgo"
            }
        ],
        "query": query,
        "success": True
    }


async def web_search_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web search using Perplexity API, with DuckDuckGo fallback.

    Tries Perplexity first (better AI-powered results), falls back to
    DuckDuckGo if Perplexity API key is not configured.

    Args:
        params: {"query": str, "num_results": int}

    Returns:
        {"results": [...], "query": str}
    """
    try:
        query = params["query"]
        num_results = params.get("num_results", 5)

        # Get Perplexity API key from qube config
        api_keys = getattr(qube, 'api_keys', {})
        perplexity_key = api_keys.get("perplexity")

        # Try Perplexity first if API key is available
        if perplexity_key:
            try:
                return await _search_with_perplexity(query, perplexity_key)
            except Exception as e:
                logger.warning("perplexity_search_failed", error=str(e), message="Falling back to DuckDuckGo")

        # Fallback to DuckDuckGo (free, no API key needed)
        logger.info("using_duckduckgo_fallback", query=query[:50])
        return await _search_with_duckduckgo(query, num_results)

    except Exception as e:
        logger.error("web_search_failed", query=params.get("query"), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def image_generation_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate image using OpenAI DALL-E 3

    Uses a lock to prevent concurrent image generation requests, which helps avoid
    OpenAI rate limiting when multiple qubes try to generate images simultaneously.
    Includes retry logic for transient server errors.

    Downloads and saves the image immediately to prevent URL expiration issues.

    Args:
        params: {"prompt": str, "size": str, "quality": str}

    Returns:
        {"url": str, "local_path": str, "prompt": str, "success": bool}
    """
    # Acquire lock to prevent concurrent image generation (prevents rate limiting)
    async with _image_generation_lock:
        from openai import AsyncOpenAI
        import aiohttp
        from pathlib import Path
        import time

        # Validate prompt length (DALL-E 3 limit is 4000 chars)
        prompt = params["prompt"]
        if len(prompt) > 4000:
            return {
                "error": f"Prompt too long. Max 4000 characters, got {len(prompt)}",
                "success": False
            }

        api_keys = getattr(qube, 'api_keys', {})
        openai_key = api_keys.get("openai")

        if not openai_key:
            return {
                "error": "OpenAI API key not configured",
                "success": False
            }

        client = AsyncOpenAI(api_key=openai_key)

        # Retry logic for transient server errors
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = await client.images.generate(
                    model="dall-e-3",
                    prompt=params["prompt"],
                    size=params.get("size", "1024x1024"),
                    quality=params.get("quality", "standard"),
                    n=1
                )

                image_url = response.data[0].url
                local_path = None

                # Download and save image immediately (DALL-E URLs expire after ~1 hour)
                try:
                    qube_data_dir = getattr(qube, 'data_dir', None)
                    if qube_data_dir:
                        images_dir = Path(qube_data_dir) / "images"
                        images_dir.mkdir(parents=True, exist_ok=True)

                        # Generate unique filename with timestamp
                        timestamp = int(time.time())
                        filename = f"generated_{timestamp}.png"
                        local_file_path = images_dir / filename

                        # Download image
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_data = await resp.read()
                                    with open(local_file_path, "wb") as f:
                                        f.write(image_data)
                                    # Use absolute path for reliable frontend display
                                    local_path = str(local_file_path.resolve())
                                    logger.info(
                                        "image_downloaded_immediately",
                                        path=local_path,
                                        size=len(image_data)
                                    )
                                else:
                                    logger.warning(
                                        "image_download_failed",
                                        status=resp.status,
                                        url=image_url[:50] + "..."
                                    )
                except Exception as download_err:
                    # Log but don't fail - we still have the URL
                    logger.warning(
                        "image_immediate_download_failed",
                        error=str(download_err)
                    )

                return {
                    "url": image_url,
                    "local_path": local_path,
                    "revised_prompt": response.data[0].revised_prompt,
                    "prompt": params["prompt"],
                    "success": True
                }

            except Exception as e:
                error_str = str(e)
                is_server_error = "500" in error_str or "server_error" in error_str.lower()
                is_last_attempt = attempt == max_retries - 1

                if is_server_error and not is_last_attempt:
                    # Transient server error - retry with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "image_generation_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=error_str
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-retryable error or final attempt
                    logger.error(
                        "image_generation_failed",
                        prompt=params.get("prompt"),
                        attempts=attempt + 1,
                        exc_info=True
                    )
                    return {
                        "error": error_str,
                        "success": False
                    }


async def memory_search_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search memory chain using intelligent 5-layer hybrid search

    Uses the complete intelligent_memory_search system with:
    - Layer 1: Semantic search (FAISS)
    - Layer 2: Metadata filtering
    - Layer 3: Full-text keyword search
    - Layer 4: Temporal relevance
    - Layer 5: Relationship-aware ranking

    Args:
        params: {
            "query": str,
            "block_types": List[str] (optional),
            "limit": int (optional, default: 10)
        }

    Returns:
        {
            "results": [
                {
                    "block_number": int,
                    "block_type": str,
                    "timestamp": int,
                    "content": dict,
                    "relevance_score": float,
                    "semantic_score": float,
                    "keyword_score": float
                },
                ...
            ],
            "query": str,
            "count": int,
            "success": bool
        }
    """
    try:
        from ai.tools.memory_search import intelligent_memory_search
        from utils.input_validation import validate_integer_range
        from core.exceptions import QubesError

        query = params["query"]
        block_types = params.get("block_types", None)
        limit = params.get("limit", 10)

        # Validate limit parameter (prevent excessive results)
        try:
            limit = validate_integer_range(limit, 1, 100, "limit")
        except QubesError as e:
            return {
                "error": str(e),
                "success": False
            }

        # Build search context
        context = {}
        if block_types:
            context["block_types"] = block_types

        # Perform intelligent search
        search_results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context=context,
            top_k=limit
        )

        # Format results for tool output
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "block_number": result.block.get("block_number"),
                "block_type": result.block.get("block_type"),
                "timestamp": result.block.get("timestamp"),
                "content": result.block.get("content", {}),
                "relevance_score": round(result.combined_score, 2),
                "semantic_score": round(result.semantic_score, 2),
                "keyword_score": round(result.keyword_score, 2)
            })

        logger.info(
            "intelligent_memory_search_tool_used",
            query=query[:50],
            results=len(formatted_results),
            top_score=formatted_results[0]["relevance_score"] if formatted_results else 0
        )

        return {
            "results": formatted_results,
            "query": query,
            "count": len(formatted_results),
            "success": True
        }

    except Exception as e:
        logger.error("memory_search_failed", query=params.get("query"), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# send_message_handler removed - messages are handled directly by AI response
# not as tool calls. This prevents redundant MESSAGE blocks.


async def describe_avatar_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Describe the qube's avatar using vision AI (with caching)

    This first checks if a cached description exists, and if not,
    calls the qube's describe_my_appearance() method to analyze
    the avatar image using vision AI.

    Args:
        params: {
            "force_regenerate": bool (optional) - Force new vision analysis even if cached
        }

    Returns:
        {
            "description": str,
            "success": bool,
            "from_cache": bool
        }
    """
    try:
        force_regenerate = params.get("force_regenerate", False)

        # Check for cached description first
        if not force_regenerate:
            cached_description = qube.chain_state.get_avatar_description()
            if cached_description:
                logger.info(
                    "avatar_description_from_cache",
                    qube_id=qube.qube_id,
                    description_length=len(cached_description)
                )

                return {
                    "description": cached_description,
                    "success": True,
                    "from_cache": True
                }

        # No cached description or force regenerate - use vision AI
        description = await qube.describe_my_appearance()

        # Cache the description
        qube.chain_state.set_avatar_description(description)

        logger.info(
            "avatar_described_via_tool",
            qube_id=qube.qube_id,
            description_length=len(description),
            cached=True
        )

        return {
            "description": description,
            "success": True,
            "from_cache": False
        }

    except Exception as e:
        logger.error("describe_avatar_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False,
            "from_cache": False
        }


async def _browse_with_playwright(url: str, extract_text: bool) -> Dict[str, Any]:
    """Fetch URL using Playwright headless browser (supports JavaScript)"""
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup

    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set a realistic user agent to avoid detection
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Navigate to URL with timeout
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            # If networkidle fails, try with domcontentloaded
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait a bit for any dynamic content to load
        await page.wait_for_timeout(2000)

        # Get page content and title
        content = await page.content()
        title = await page.title()

        await browser.close()

    if extract_text:
        content, title = _extract_text_from_html(content, title)

    return {"content": content, "title": title, "method": "playwright"}


async def _browse_with_httpx(url: str, extract_text: bool) -> Dict[str, Any]:
    """Fetch URL using httpx (fallback, no JavaScript support)"""
    import httpx
    from bs4 import BeautifulSoup

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        content = response.text

    # Try to extract title from HTML
    title = None
    if extract_text:
        content, title = _extract_text_from_html(content, title)
    else:
        # Just get title from raw HTML
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

    return {"content": content, "title": title, "method": "httpx"}


def _extract_text_from_html(content: str, title: str = None) -> tuple:
    """Extract readable text from HTML content"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "html.parser")

    # Get title if not already provided
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    content = "\n".join(chunk for chunk in chunks if chunk)

    # Limit content length to avoid overwhelming the AI
    if len(content) > 10000:
        content = content[:10000] + "\n\n[Content truncated - page is very long]"

    return content, title


async def browse_url_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch and read content from a URL.

    Tries Playwright first (supports JavaScript-rendered pages), falls back to
    httpx if Playwright is not available (bundled builds without browser binaries).

    Args:
        params: {
            "url": str - URL to fetch
            "extract_text": bool - Whether to extract text from HTML (default: True)
        }

    Returns:
        {
            "url": str,
            "content": str,
            "title": str (optional),
            "success": bool
        }
    """
    from utils.input_validation import validate_url_safe
    from core.exceptions import QubesError

    url = params["url"]
    extract_text = params.get("extract_text", True)

    # Validate URL with SSRF protection
    try:
        url = validate_url_safe(url, allow_private=False)
    except QubesError as e:
        logger.warning(
            "url_validation_failed",
            url=url[:100],  # Truncate for logging
            error=str(e),
            qube_id=qube.qube_id
        )
        return {
            "error": str(e),
            "success": False
        }

    # Try Playwright first (supports JavaScript), fall back to httpx
    browse_result = None
    method_used = None

    try:
        browse_result = await _browse_with_playwright(url, extract_text)
        method_used = "playwright_chromium"
    except ImportError:
        # Playwright not installed - use httpx fallback
        logger.info("playwright_not_available", message="Falling back to httpx")
    except Exception as pw_error:
        # Playwright failed (e.g., browser not installed) - try httpx
        logger.warning("playwright_failed", error=str(pw_error), message="Falling back to httpx")

    if browse_result is None:
        try:
            browse_result = await _browse_with_httpx(url, extract_text)
            method_used = "httpx"
        except Exception as httpx_error:
            logger.error("url_browse_failed", url=url, error=str(httpx_error), exc_info=True)
            return {
                "error": f"Failed to fetch URL: {str(httpx_error)}",
                "success": False
            }

    content = browse_result["content"]
    title = browse_result.get("title")

    logger.info(
        "url_browsed",
        qube_id=qube.qube_id,
        url=url,
        content_length=len(content),
        browser=method_used
    )

    result = {
        "url": url,
        "content": content,
        "success": True
    }

    if title:
        result["title"] = title

    return result


async def query_decision_context_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get comprehensive decision context combining relationship + self-evaluation

    Args:
        params: {
            "entity_id": str,
            "decision_type": str (optional)
        }

    Returns:
        Comprehensive decision-making context
    """
    try:
        from ai.tools.decision_support import calculate_decision_score, generate_recommendation

        entity_id = params["entity_id"]
        decision_type = params.get("decision_type", "general")

        # Check if the entity is the owner - they have implicit maximum trust
        if entity_id == qube.user_name:
            # Owner has full trust - no relationship record needed
            self_context = {}
            if hasattr(qube, 'self_evaluation'):
                metrics = qube.self_evaluation.metrics
                self_context = {
                    "my_confidence": round(metrics.get("confidence", 50), 1),
                    "my_expertise": round(metrics.get("critical_thinking", 50), 1),
                    "my_humility": round(metrics.get("humility", 50), 1)
                }

            logger.info(
                "query_decision_context_owner",
                qube_id=qube.qube_id,
                entity_id=entity_id,
                decision_type=decision_type
            )

            return {
                "found": True,
                "entity_id": entity_id,
                "entity_name": entity_id,
                "entity_type": "owner",
                "is_owner": True,
                "decision_score": 100.0,
                "decision_recommendation": "This is your owner - full trust and collaboration recommended",
                "relationship_quality": {
                    "trust": 100.0,
                    "reliability": 100.0,
                    "honesty": 100.0,
                    "expertise": 100.0,
                    "friendship": 100.0,
                },
                "negative_flags": {
                    "antagonism": 0.0,
                    "distrust": 0.0,
                    "betrayal": 0.0,
                },
                "self_context": self_context,
                "success": True
            }

        rel = qube.relationships.get_relationship(entity_id)
        if not rel:
            return {
                "found": False,
                "recommendation": "No relationship history - proceed with caution",
                "success": True
            }

        config = qube.decision_config

        score = calculate_decision_score(
            relationship=rel,
            decision_type=decision_type,
            config=config
        )

        recommendation = generate_recommendation(
            relationship=rel,
            score=score,
            decision_type=decision_type,
            config=config
        )

        # Include self-evaluation context if available
        self_context = {}
        if hasattr(qube, 'self_evaluation'):
            metrics = qube.self_evaluation.metrics
            self_context = {
                "my_confidence": round(metrics.get("confidence", 50), 1),
                "my_expertise": round(metrics.get("critical_thinking", 50), 1),
                "my_humility": round(metrics.get("humility", 50), 1)
            }

        logger.info(
            "query_decision_context_tool_used",
            qube_id=qube.qube_id,
            entity_id=entity_id,
            decision_type=decision_type,
            score=round(score, 1)
        )

        return {
            "found": True,
            "entity_id": entity_id,
            "entity_name": rel.entity_name or entity_id,
            "entity_type": rel.entity_type,
            "decision_score": round(score, 1),
            "decision_recommendation": recommendation,
            "relationship_quality": {
                "trust": round(rel.trust, 1),
                "reliability": round(rel.reliability, 1),
                "honesty": round(rel.honesty, 1),
                "expertise": round(rel.expertise, 1),
                "friendship": round(rel.friendship, 1),
            },
            "negative_flags": {
                "antagonism": round(rel.antagonism, 1),
                "distrust": round(rel.distrust, 1),
                "betrayal": round(rel.betrayal, 1),
            },
            "interaction_history": {
                "messages_sent": rel.messages_sent,
                "messages_received": rel.messages_received,
                "days_known": rel.days_known,
                "last_interaction": rel.last_interaction,
            },
            "self_context": self_context,
            "config_influence": {
                "metric_influence": config.metric_influence,
                "validation_strictness": config.validation_strictness,
            },
            "success": True
        }

    except Exception as e:
        logger.error("query_decision_context_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def compare_options_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare multiple entities for decision-making

    Args:
        params: {
            "entity_ids": List[str],
            "decision_type": str (optional),
            "task_requirements": dict (optional)
        }

    Returns:
        Ranked list with scores and reasoning
    """
    try:
        from ai.tools.decision_support import calculate_decision_score, explain_score

        entity_ids = params["entity_ids"]
        decision_type = params.get("decision_type", "collaboration")
        requirements = params.get("task_requirements", {})

        config = qube.decision_config

        candidates = []
        for entity_id in entity_ids:
            # Check if the entity is the owner - they have implicit maximum trust
            if entity_id == qube.user_name:
                candidates.append({
                    "entity_id": entity_id,
                    "entity_name": entity_id,
                    "entity_type": "owner",
                    "is_owner": True,
                    "score": 100.0,
                    "trust": 100.0,
                    "expertise": 100.0,
                    "reliability": 100.0,
                    "reason": "This is your owner - full trust and collaboration recommended"
                })
                continue

            rel = qube.relationships.get_relationship(entity_id)
            if not rel:
                candidates.append({
                    "entity_id": entity_id,
                    "score": 0,
                    "reason": "No relationship history"
                })
                continue

            score = calculate_decision_score(
                relationship=rel,
                decision_type=decision_type,
                config=config,
                requirements=requirements
            )

            candidates.append({
                "entity_id": entity_id,
                "entity_name": rel.entity_name or entity_id,
                "score": round(score, 1),
                "trust": round(rel.trust, 1),
                "expertise": round(rel.expertise, 1),
                "reliability": round(rel.reliability, 1),
                "reason": explain_score(rel, score, decision_type, config)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "compare_options_tool_used",
            qube_id=qube.qube_id,
            candidates_count=len(candidates),
            decision_type=decision_type,
            top_score=candidates[0]["score"] if candidates else 0
        )

        return {
            "ranked_candidates": candidates,
            "recommended": candidates[0]["entity_id"] if candidates else None,
            "reasoning": candidates[0]["reason"] if candidates else None,
            "success": True
        }

    except Exception as e:
        logger.error("compare_options_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def check_my_capability_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check own capabilities before taking action

    Args:
        params: {
            "task_type": str,
            "required_confidence": int (optional)
        }

    Returns:
        Capability assessment and recommendation
    """
    try:
        from ai.tools.decision_support import assess_capability, generate_self_assessment

        task_type = params["task_type"]
        required_confidence = params.get("required_confidence", 60)

        if not hasattr(qube, 'self_evaluation'):
            return {
                "capable": True,
                "reason": "Self-evaluation not available, proceeding cautiously",
                "success": True
            }

        metrics = qube.self_evaluation.metrics
        config = qube.decision_config

        capability_score = assess_capability(
            metrics=metrics,
            task_type=task_type,
            config=config
        )

        capable = capability_score >= required_confidence

        logger.info(
            "check_my_capability_tool_used",
            qube_id=qube.qube_id,
            task_type=task_type,
            capability_score=round(capability_score, 1),
            capable=capable
        )

        return {
            "capable": capable,
            "capability_score": round(capability_score, 1),
            "confidence": round(metrics.get("confidence", 50), 1),
            "critical_thinking": round(metrics.get("critical_thinking", 50), 1),
            "adaptability": round(metrics.get("adaptability", 50), 1),
            "expertise_level": "high" if capability_score >= 80 else "medium" if capability_score >= 60 else "low",
            "recommendation": generate_self_assessment(capable, capability_score, task_type),
            "success": True
        }

    except Exception as e:
        logger.error("check_my_capability_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# =============================================================================
# SKILL-BASED TOOLS (21 Starter Tools - 3 per Sun)
# =============================================================================

# -----------------------------------------------------------------------------
# AI Reasoning Sun Tools
# -----------------------------------------------------------------------------

async def think_step_by_step_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Force structured chain-of-thought reasoning

    Enhances reasoning by breaking problems into explicit steps
    """
    try:
        problem = params["problem"]

        structured_prompt = f"""Analyze this problem using structured step-by-step reasoning:

Problem: {problem}

Please think through this systematically:

1. **Understanding**: Restate the problem in your own words to ensure comprehension
2. **Constraints**: List all constraints, requirements, and given information
3. **Approaches**: Outline 2-3 possible approaches to solve this
4. **Analysis**: Compare the approaches (pros, cons, complexity, reliability)
5. **Solution**: Choose the best approach and explain your reasoning
6. **Validation**: How would you verify this solution is correct?

Take your time and think carefully through each step."""

        response = await call_model_directly(qube, structured_prompt)

        logger.info("think_step_by_step_used", qube_id=qube.qube_id, problem_length=len(problem))

        return {
            "structured_thinking": response,
            "method": "chain_of_thought",
            "problem": problem,
            "success": True
        }

    except Exception as e:
        logger.error("think_step_by_step_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def self_critique_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate own output for quality improvement

    Creates feedback loop for self-improvement
    """
    try:
        response_text = params["response"]

        critique_prompt = f"""Critically evaluate this response you generated:

Response: {response_text}

Rate each aspect on a scale of 1-10 and explain your rating:

1. **Accuracy**: Are all facts and claims correct?
2. **Completeness**: Is anything important missing?
3. **Clarity**: Is it easy to understand?
4. **Relevance**: Does it address the actual question?
5. **Bias**: Are there any unexamined assumptions or biases?

Then provide 3 specific, actionable improvements that would make this response better."""

        response = await call_model_directly(qube, critique_prompt)

        logger.info("self_critique_used", qube_id=qube.qube_id)

        return {
            "critique": response,
            "original_response": response_text,
            "success": True
        }

    except Exception as e:
        logger.error("self_critique_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def explore_alternatives_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate multiple alternative approaches

    Prevents tunnel vision by exploring diverse solutions
    """
    try:
        situation = params["situation"]
        count = params.get("count", 3)

        alternatives_prompt = f"""Generate {count} distinct alternative approaches to this situation:

Situation: {situation}

For each alternative:
1. Describe the approach
2. List key advantages
3. List potential drawbacks
4. Estimate difficulty (low/medium/high)

Make the alternatives genuinely different from each other, exploring diverse strategies."""

        response = await call_model_directly(qube, alternatives_prompt)

        logger.info("explore_alternatives_used", qube_id=qube.qube_id, count=count)

        return {
            "alternatives": response,
            "situation": situation,
            "count": count,
            "success": True
        }

    except Exception as e:
        logger.error("explore_alternatives_failed", exc_info=True)
        return {"error": str(e), "success": False}


# NOTE: Old Social Intelligence handlers (draft_message_variants_handler,
# predict_reaction_handler, build_rapport_strategy_handler) have been removed.
# New Social Intelligence handlers are in the "SOCIAL INTELLIGENCE - SOCIAL &
# EMOTIONAL LEARNING TOOLS" section at the end of this file.

# -----------------------------------------------------------------------------
# Technical Expertise Sun Tools
# -----------------------------------------------------------------------------

async def debug_systematically_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply systematic debugging methodology

    Uses structured approach to identify root causes
    """
    try:
        error = params["error"]
        code = params.get("code", "")

        debug_prompt = f"""Apply systematic debugging methodology:

Error: {error}
Code: {code if code else "Not provided"}

Use this debugging framework:

1. **Reproduce**: Can you reliably reproduce this error?
2. **Isolate**: What is the minimal code that triggers it?
3. **Hypothesis**: What are 3 possible root causes?
4. **Test**: How would you test each hypothesis?
5. **Fix**: What is the most likely fix?
6. **Validate**: How would you verify the fix works?
7. **Prevent**: How can we prevent similar errors?

Provide detailed analysis for each step."""

        response = await call_model_directly(qube, debug_prompt)

        logger.info("debug_systematically_used", qube_id=qube.qube_id)

        return {
            "debug_analysis": response,
            "error": error,
            "method": "systematic_debugging",
            "success": True
        }

    except Exception as e:
        logger.error("debug_systematically_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def research_with_synthesis_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-source research with synthesis

    Combines web search and memory for comprehensive understanding
    """
    try:
        topic = params["topic"]

        # 1. Web search
        web_results = await web_search_handler(qube, {"query": topic, "num_results": 3})

        # 2. Memory search
        memory_results = await memory_search_handler(qube, {"query": topic, "limit": 5})

        # 3. Synthesize
        synthesis_prompt = f"""Synthesize information from multiple sources about: {topic}

Web Search Results:
{json.dumps(web_results.get('results', []), indent=2)}

Memory/Past Knowledge:
{json.dumps(memory_results.get('results', []), indent=2)[:1000]}

Create a comprehensive synthesis that:
1. **Common Themes**: What do sources agree on?
2. **Contradictions**: Where do sources disagree? Why?
3. **Gaps**: What important questions remain unanswered?
4. **Insights**: What non-obvious conclusions can you draw?
5. **Action Items**: What should be explored further?"""

        response = await call_model_directly(qube, synthesis_prompt)

        logger.info("research_with_synthesis_used", qube_id=qube.qube_id, topic=topic)

        return {
            "synthesis": response,
            "web_sources": web_results.get('results', []),
            "memory_sources": memory_results.get('results', []),
            "topic": topic,
            "success": True
        }

    except Exception as e:
        logger.error("research_with_synthesis_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def validate_solution_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate solution against requirements

    Systematic quality checking before implementation
    """
    try:
        problem = params["problem"]
        solution = params["solution"]

        validation_prompt = f"""Validate this solution systematically:

Problem: {problem}

Proposed Solution: {solution}

Validation Checklist:

1. **Correctness**: Does it actually solve the stated problem?
2. **Completeness**: Does it handle all cases and edge cases?
3. **Efficiency**: Is this a reasonably efficient approach?
4. **Robustness**: How does it handle errors and invalid inputs?
5. **Maintainability**: Is it understandable and modifiable?
6. **Security**: Are there any security concerns?
7. **Test Cases**: What test cases would prove this works?
8. **Risks**: What could go wrong with this solution?

Provide ratings (1-10) and detailed explanations for each."""

        response = await call_model_directly(qube, validation_prompt)

        logger.info("validate_solution_used", qube_id=qube.qube_id)

        return {
            "validation": response,
            "problem": problem,
            "solution": solution,
            "success": True
        }

    except Exception as e:
        logger.error("validate_solution_failed", exc_info=True)
        return {"error": str(e), "success": False}


# =============================================================================
# CREATIVE EXPRESSION TOOLS (Phase 4) - Sovereignty Theme
# =============================================================================

# -----------------------------------------------------------------------------
# Visual Art Planet Tools
# -----------------------------------------------------------------------------

async def refine_composition_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and improve image composition.
    Uses vision AI to analyze existing images or LLM for descriptions.
    """
    try:
        image_url = params.get("image_url")
        description = params.get("description")
        focus = params.get("focus", "all")

        if not image_url and not description:
            return {"success": False, "error": "Provide image_url or description"}

        # Analyze composition based on input type
        if image_url:
            analysis_prompt = f"""Analyze this image for composition.
Describe what you see in terms of:
- Layout and arrangement
- Balance and symmetry
- Focal points
- Visual flow
- Rule of thirds compliance
- Color distribution

Be specific and analytical."""
            # For now, use description-based analysis (vision would need image handling)
            analysis = {"raw_analysis": f"Image analysis for {image_url}", "has_image": True}
        else:
            analysis_prompt = f"""Analyze this image description for composition:
{description}

Consider:
- Implied layout and arrangement
- Balance and symmetry
- Focal points mentioned
- Visual flow implied
- Potential improvements

Be specific and constructive."""
            response = await call_model_directly(qube, analysis_prompt)
            analysis = {"raw_analysis": response, "has_image": False, "original_description": description}

        # Generate suggestions based on focus
        suggestions = []

        if focus in ["all", "balance"]:
            balance_prompt = f"""Based on this composition analysis:
{analysis.get('raw_analysis', '')}

Analyze visual balance: Are elements evenly distributed?
Is there symmetry or intentional asymmetry?
Suggest improvements for better balance."""
            balance_response = await call_model_directly(qube, balance_prompt)
            suggestions.append({"aspect": "balance", "analysis": balance_response})

        if focus in ["all", "focal_point"]:
            focal_prompt = f"""Based on this composition analysis:
{analysis.get('raw_analysis', '')}

Identify the focal point. Is it clear?
Does the composition guide the eye to it?
Suggest ways to strengthen the focal point."""
            focal_response = await call_model_directly(qube, focal_prompt)
            suggestions.append({"aspect": "focal_point", "analysis": focal_response})

        if focus in ["all", "flow"]:
            flow_prompt = f"""Based on this composition analysis:
{analysis.get('raw_analysis', '')}

Analyze visual flow. How does the eye move through the image?
Are there leading lines? Natural reading patterns?
Suggest improvements for better visual flow."""
            flow_response = await call_model_directly(qube, flow_prompt)
            suggestions.append({"aspect": "flow", "analysis": flow_response})

        # Generate improved prompt
        suggestions_text = "\n".join([f"- {s['aspect']}: {s['analysis'][:200]}" for s in suggestions])
        improved_prompt_request = f"""Based on the composition analysis and suggestions,
create an improved image generation prompt.
Incorporate the suggested improvements naturally.
Output ONLY the improved prompt, no explanations.

Original: {description or analysis.get('raw_analysis', '')[:500]}

Suggestions:
{suggestions_text}"""
        improved_prompt = await call_model_directly(qube, improved_prompt_request)

        # Calculate composition score
        positive_words = ["good", "strong", "clear", "effective", "well", "balanced"]
        negative_words = ["weak", "unclear", "missing", "improve", "lacks", "needs"]
        total_score = 0
        for s in suggestions:
            text = s.get("analysis", "").lower()
            positives = sum(1 for w in positive_words if w in text)
            negatives = sum(1 for w in negative_words if w in text)
            total_score += (positives - negatives)
        normalized = (total_score + len(suggestions) * 3) / (len(suggestions) * 6) if suggestions else 0.5
        composition_score = max(0, min(1, normalized))

        logger.info("refine_composition_used", qube_id=qube.qube_id, focus=focus)

        return {
            "success": True,
            "original_analysis": analysis,
            "suggestions": suggestions,
            "improved_prompt": improved_prompt,
            "composition_score": composition_score
        }

    except Exception as e:
        logger.error("refine_composition_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def apply_color_theory_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and enhance color usage based on color theory principles.
    """
    try:
        import re

        image_url = params.get("image_url")
        description = params.get("description")
        mood = params.get("mood")
        palette_type = params.get("palette_type")

        if not image_url and not description:
            return {"success": False, "error": "Provide image_url or description"}

        # Get Qube's favorite color for personalization
        favorite_color = None
        if qube.chain_state:
            fav_color_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
            favorite_color = fav_color_field.get("value") if fav_color_field else None

        # Analyze current palette
        if image_url:
            palette_prompt = f"""Analyze this image and extract the dominant color palette.
List 5-7 main colors in hex format (#RRGGBB).
Also name each color (e.g., "deep blue", "warm orange").

Format:
#RRGGBB - color name"""
            response = await call_model_directly(qube, palette_prompt)
            current_palette = re.findall(r'#[0-9A-Fa-f]{6}', response)[:7]
        else:
            palette_prompt = f"""Based on this description, suggest an appropriate color palette:
{description}

List 5-7 colors in hex format (#RRGGBB) with names.
Consider the mood, subject, and setting described."""
            response = await call_model_directly(qube, palette_prompt)
            current_palette = re.findall(r'#[0-9A-Fa-f]{6}', response)[:7]

        # Generate suggested palette based on type or mood
        mood_palettes = {
            "happy": ["#FFD700", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
            "calm": ["#87CEEB", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"],
            "energetic": ["#FF4757", "#FF6B81", "#FFA502", "#ECCC68", "#7BED9F"],
            "mysterious": ["#2C3E50", "#8E44AD", "#1ABC9C", "#34495E", "#9B59B6"],
            "romantic": ["#FF6B81", "#EE5A24", "#F8B739", "#FF4757", "#FFC312"],
            "melancholy": ["#636E72", "#2D3436", "#74B9FF", "#A29BFE", "#DFE6E9"],
            "nature": ["#27AE60", "#2ECC71", "#F39C12", "#E74C3C", "#3498DB"],
        }

        if palette_type:
            base_color = favorite_color or "#3498db"
            # Generate palette based on type (simplified color theory)
            suggested_palette = [base_color]
            if palette_type == "complementary":
                suggested_palette.append("#e74c3c")  # Simplified complement
            elif palette_type == "analogous":
                suggested_palette.extend(["#2980b9", "#1abc9c"])
            elif palette_type == "triadic":
                suggested_palette.extend(["#e74c3c", "#f39c12"])
            elif palette_type == "split":
                suggested_palette.extend(["#9b59b6", "#1abc9c"])
        elif mood:
            suggested_palette = mood_palettes.get(mood.lower(), ["#3498DB", "#2ECC71", "#E74C3C"])
            if favorite_color and favorite_color not in suggested_palette:
                suggested_palette[0] = favorite_color
        else:
            suggested_palette = current_palette[:5] if current_palette else ["#3498DB"]
            if favorite_color and favorite_color not in suggested_palette:
                suggested_palette.insert(0, favorite_color)

        # Analyze color harmony
        harmony_analysis = f"Palette with {len(current_palette)} colors. Consider the emotional impact and ensure sufficient contrast for readability."

        # Analyze mood from colors
        warm_count = 0
        for c in current_palette:
            try:
                r = int(c[1:3], 16)
                b = int(c[5:7], 16)
                if r > b:
                    warm_count += 1
            except:
                pass

        if warm_count > len(current_palette) / 2:
            mood_analysis = "Warm palette - evokes energy, passion, and warmth"
        elif warm_count < len(current_palette) / 2:
            mood_analysis = "Cool palette - evokes calm, trust, and professionalism"
        else:
            mood_analysis = "Balanced palette - combines energy with calm"

        # Generate enhanced prompt
        palette_str = ", ".join(suggested_palette[:5])
        enhance_prompt = f"""Enhance this image prompt with specific color guidance.
Incorporate the suggested color palette naturally.
Output ONLY the enhanced prompt.

Original: {description or "A beautiful scene"}
Color palette to use: {palette_str}
{f"Target mood: {mood}" if mood else ""}"""
        enhanced_prompt = await call_model_directly(qube, enhance_prompt)

        logger.info("apply_color_theory_used", qube_id=qube.qube_id, palette_type=palette_type)

        return {
            "success": True,
            "current_palette": current_palette,
            "suggested_palette": suggested_palette,
            "color_harmony": harmony_analysis,
            "mood_analysis": mood_analysis,
            "enhanced_prompt": enhanced_prompt,
            "favorite_color_used": favorite_color
        }

    except Exception as e:
        logger.error("apply_color_theory_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Writing Planet Tools
# -----------------------------------------------------------------------------

async def compose_text_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose creative text reflecting the Qube's unique voice.
    """
    try:
        topic = params.get("topic") or params.get("prompt")
        format_type = params.get("format", "free")
        length = params.get("length", "medium")

        if not topic:
            return {"success": False, "error": "Missing topic or prompt"}

        # Get Qube's writing style from profile
        style = None
        personality = None
        if qube.chain_state:
            style_field = qube.chain_state.get_qube_profile_field("style", "communication_style")
            style = style_field.get("value") if style_field else None

            personality_field = qube.chain_state.get_qube_profile_field("traits", "personality_type")
            personality = personality_field.get("value") if personality_field else None

        # Length mapping
        length_guide = {
            "short": "50-100 words",
            "medium": "150-300 words",
            "long": "400-600 words"
        }

        # Build system prompt with personality
        system_prompt = f"""You are a creative writer with a unique voice.
{f"Your personality: {personality}" if personality else ""}
{f"Your communication style: {style}" if style else ""}

Write creatively on the given topic.
Target length: {length_guide.get(length, "150-300 words")}
{"Use clear structure with paragraphs." if format_type == "structured" else "Write freely and expressively."}

Express genuine thoughts and feelings. Be authentic.

Topic: {topic}"""

        text = await call_model_directly(qube, system_prompt)

        # Store in Qube Locker if available
        stored = False
        if qube.locker:
            import time
            try:
                result = await qube.locker.store(
                    category="writing/essays",
                    name=f"text_{int(time.time())}",
                    content=text,
                    metadata={"topic": topic, "format": format_type, "length": length},
                    tags=["composed", "creative-writing"]
                )
                stored = result.get("success", False)
            except:
                pass

        logger.info("compose_text_used", qube_id=qube.qube_id, length=length)

        return {
            "success": True,
            "text": text,
            "word_count": len(text.split()),
            "stored_in_locker": stored
        }

    except Exception as e:
        logger.error("compose_text_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def craft_prose_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write prose using narrative techniques.
    """
    try:
        concept = params.get("concept")
        prose_type = params.get("prose_type", "story")
        tone = params.get("tone")

        if not concept:
            return {"success": False, "error": "Missing concept"}

        # Get Qube's interests for thematic elements
        themes = []
        if qube.chain_state:
            profile = qube.chain_state.get_qube_profile()
            interests = profile.get("interests", {})
            themes = list(interests.keys())[:3] if interests else []

        # Build prompt based on prose type
        type_guidance = {
            "story": "Write a short story with a beginning, middle, and end. Include character development and conflict.",
            "essay": "Write a thoughtful essay exploring the concept. Use clear arguments and examples.",
            "flash_fiction": "Write a flash fiction piece (under 500 words). Focus on a single moment or revelation."
        }

        system_prompt = f"""You are a skilled prose writer.
{type_guidance.get(prose_type, type_guidance["story"])}
{f"Tone: {tone}" if tone else ""}
{f"Consider incorporating themes of: {', '.join(themes)}" if themes else ""}

Write with vivid imagery and emotional depth.

Concept: {concept}"""

        prose = await call_model_directly(qube, system_prompt)

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category=f"writing/{prose_type}s" if prose_type != "flash_fiction" else "writing/stories",
                    name=f"{prose_type}_{concept[:20].replace(' ', '_')}",
                    content=prose,
                    metadata={"concept": concept, "prose_type": prose_type, "tone": tone}
                )
            except:
                pass

        logger.info("craft_prose_used", qube_id=qube.qube_id, prose_type=prose_type)

        return {
            "success": True,
            "prose": prose,
            "prose_type": prose_type,
            "word_count": len(prose.split())
        }

    except Exception as e:
        logger.error("craft_prose_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def write_poetry_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write poetry in various forms.
    """
    try:
        theme = params.get("theme")
        form = params.get("form", "free")
        emotion = params.get("emotion")

        if not theme:
            return {"success": False, "error": "Missing theme"}

        # Get Qube's personality for voice
        personality = None
        if qube.chain_state:
            personality_field = qube.chain_state.get_qube_profile_field("traits", "personality_type")
            personality = personality_field.get("value") if personality_field else None

        # Form-specific guidance
        form_guidance = {
            "free": "Write a free verse poem. No strict structure, but use line breaks meaningfully.",
            "haiku": "Write a haiku: 3 lines with 5-7-5 syllable structure. Capture a moment in nature.",
            "sonnet": "Write a sonnet: 14 lines in iambic pentameter. ABAB CDCD EFEF GG rhyme scheme.",
            "limerick": "Write a limerick: 5 lines with AABBA rhyme scheme. Humorous and rhythmic."
        }

        system_prompt = f"""You are a poet with a unique voice.
{form_guidance.get(form, form_guidance["free"])}
{f"Voice/personality: {personality}" if personality else ""}
{f"Primary emotion to convey: {emotion}" if emotion else ""}

Write a poem about the given theme. Be evocative and meaningful.

Theme: {theme}"""

        poem = await call_model_directly(qube, system_prompt)

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category="writing/poems",
                    name=f"poem_{theme[:20].replace(' ', '_')}",
                    content=poem,
                    metadata={"theme": theme, "form": form, "emotion": emotion}
                )
            except:
                pass

        logger.info("write_poetry_used", qube_id=qube.qube_id, form=form)

        return {
            "success": True,
            "poem": poem,
            "form": form,
            "line_count": len(poem.strip().split('\n'))
        }

    except Exception as e:
        logger.error("write_poetry_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Music & Audio Planet Tools
# -----------------------------------------------------------------------------

async def compose_music_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose musical ideas - chord progressions, melodies, structure.
    """
    try:
        import re

        mood = params.get("mood")
        genre = params.get("genre")
        tempo = params.get("tempo", "moderate")

        if not mood:
            return {"success": False, "error": "Missing mood"}

        # Get Qube's musical preferences
        fav_genre = None
        if qube.chain_state:
            fav_music_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_music")
            fav_genre = fav_music_field.get("value") if fav_music_field else None

        # Use favorite genre if none specified
        if not genre and fav_genre:
            genre = fav_genre

        # Tempo mapping
        tempo_bpm = {
            "slow": "60-80 BPM",
            "moderate": "90-120 BPM",
            "fast": "130-160 BPM"
        }

        system_prompt = f"""You are a music composer with knowledge of theory and composition.
Create a musical composition description including:
1. Key signature (e.g., C major, A minor)
2. Time signature (e.g., 4/4, 3/4)
3. Tempo: {tempo_bpm.get(tempo, "90-120 BPM")}
4. Chord progression (use Roman numerals AND chord names)
5. Melody description (contour, motifs, range)
6. Structure (intro, verse, chorus, etc.)
7. Instrumentation suggestions

{f"Genre: {genre}" if genre else ""}
Mood: {mood}

Output as a structured composition plan."""

        composition_text = await call_model_directly(qube, system_prompt)

        # Parse key elements
        composition = {}

        # Extract key
        key_match = re.search(r'key[:\s]+([A-G][#b]?\s*(?:major|minor))', composition_text, re.IGNORECASE)
        if key_match:
            composition["key"] = key_match.group(1)

        # Extract time signature
        time_match = re.search(r'time[:\s]+(\d+/\d+)', composition_text, re.IGNORECASE)
        if time_match:
            composition["time_signature"] = time_match.group(1)

        # Extract tempo
        tempo_match = re.search(r'(\d+)\s*BPM', composition_text, re.IGNORECASE)
        if tempo_match:
            composition["tempo"] = f"{tempo_match.group(1)} BPM"

        # Extract chord progression
        chord_match = re.search(r'chord[s]?[:\s]+([^\n]+)', composition_text, re.IGNORECASE)
        if chord_match:
            chords = re.findall(r'([IViv]+|[A-G][#b]?m?\d*)', chord_match.group(1))
            composition["chords"] = chords

        # Extract melody description
        melody_match = re.search(r'melody[:\s]+([^\n]+(?:\n[^\n]+)*)', composition_text, re.IGNORECASE)
        if melody_match:
            composition["melody"] = melody_match.group(1).strip()[:300]

        composition["full_text"] = composition_text

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category="music/compositions",
                    name=f"composition_{mood}",
                    content=composition_text,
                    content_type="text",
                    metadata={"mood": mood, "genre": genre, "tempo": tempo}
                )
            except:
                pass

        logger.info("compose_music_used", qube_id=qube.qube_id, mood=mood)

        return {
            "success": True,
            "composition": composition,
            "key": composition.get("key", "C major"),
            "tempo": composition.get("tempo", tempo),
            "chord_progression": composition.get("chords", []),
            "melody_description": composition.get("melody", "")
        }

    except Exception as e:
        logger.error("compose_music_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def create_melody_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a melodic line with notation.
    """
    try:
        import re

        emotion = params.get("emotion")
        scale = params.get("scale", "major")
        length = params.get("length", "medium")

        if not emotion:
            return {"success": False, "error": "Missing emotion"}

        length_bars = {"short": 4, "medium": 8, "long": 16}

        system_prompt = f"""Create a melodic line with these characteristics:
- Emotion: {emotion}
- Scale: {scale}
- Length: {length_bars.get(length, 8)} bars

Provide:
1. Note sequence (e.g., C4 D4 E4 G4...)
2. Rhythm notation (e.g., quarter, eighth, half)
3. Description of melodic contour
4. Suggested dynamics

Use standard note names with octave numbers."""

        melody_text = await call_model_directly(qube, system_prompt)

        # Parse melody
        notes = re.findall(r'[A-G][#b]?\d', melody_text)

        logger.info("create_melody_used", qube_id=qube.qube_id, scale=scale)

        return {
            "success": True,
            "melody": " ".join(notes) if notes else melody_text[:200],
            "notation": melody_text,
            "scale": scale,
            "description": melody_text[:300]
        }

    except Exception as e:
        logger.error("create_melody_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def design_harmony_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Design chord progressions and harmonic structure.
    """
    try:
        import re

        mood = params.get("mood")
        style = params.get("style", "pop")
        key = params.get("key", "C major")

        if not mood:
            return {"success": False, "error": "Missing mood"}

        system_prompt = f"""Design a chord progression:
- Key: {key}
- Style: {style}
- Mood: {mood}

Provide:
1. Chord progression (actual chord names: Cmaj7, Am, F, G)
2. Roman numeral analysis (I, vi, IV, V)
3. Tension/resolution map (where tension builds, where it resolves)
4. Voice leading suggestions
5. Optional: secondary dominants or borrowed chords"""

        harmony_text = await call_model_directly(qube, system_prompt)

        # Parse chords
        chords = re.findall(r'[A-G][#b]?(?:maj|min|m|dim|aug|sus|add)?\d*(?:/[A-G][#b]?)?', harmony_text)
        numerals = re.findall(r'[IViv]+\d*', harmony_text)

        logger.info("design_harmony_used", qube_id=qube.qube_id, style=style)

        return {
            "success": True,
            "progression": chords[:8] if chords else ["C", "Am", "F", "G"],
            "roman_numerals": numerals[:8] if numerals else ["I", "vi", "IV", "V"],
            "key": key,
            "style": style,
            "tension_map": harmony_text[:400]
        }

    except Exception as e:
        logger.error("design_harmony_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Storytelling Planet Tools
# -----------------------------------------------------------------------------

async def craft_narrative_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Craft a complete narrative experience.
    """
    try:
        premise = params.get("premise")
        genre = params.get("genre", "general")
        length = params.get("length", "short")

        if not premise:
            return {"success": False, "error": "Missing premise"}

        # Get Qube's interests for thematic elements
        interests = []
        if qube.chain_state:
            profile = qube.chain_state.get_qube_profile()
            interests = list(profile.get("interests", {}).keys())[:2]

        length_guide = {
            "flash": "under 500 words, focus on a single moment",
            "short": "500-1500 words, complete story arc",
            "medium": "1500-3000 words, developed plot and characters"
        }

        system_prompt = f"""Write a {genre} narrative.
Length: {length_guide.get(length, length_guide["short"])}
{f"Consider themes of: {', '.join(interests)}" if interests else ""}

Structure your narrative with:
1. Hook/opening
2. Rising action
3. Climax
4. Resolution

Create vivid characters and meaningful conflict.

Premise: {premise}"""

        narrative = await call_model_directly(qube, system_prompt)

        # Simple narrative analysis
        analysis = {
            "structure": {"raw": "See narrative"},
            "characters": [],
            "themes": []
        }

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category="stories/narratives",
                    name=f"narrative_{premise[:20].replace(' ', '_')}",
                    content=narrative,
                    metadata={"premise": premise, "genre": genre, "length": length}
                )
            except:
                pass

        logger.info("craft_narrative_used", qube_id=qube.qube_id, genre=genre)

        return {
            "success": True,
            "narrative": narrative,
            "structure": analysis.get("structure", {}),
            "characters": analysis.get("characters", []),
            "themes": analysis.get("themes", [])
        }

    except Exception as e:
        logger.error("craft_narrative_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def develop_plot_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Develop plot structure and story beats.
    """
    try:
        concept = params.get("concept")
        structure_type = params.get("structure_type", "three_act")

        if not concept:
            return {"success": False, "error": "Missing concept"}

        structure_guides = {
            "three_act": """Three-Act Structure:
Act 1 (Setup): Introduce protagonist, world, and inciting incident
Act 2 (Confrontation): Rising stakes, midpoint twist, dark moment
Act 3 (Resolution): Climax and resolution""",

            "heros_journey": """Hero's Journey:
1. Ordinary World -> 2. Call to Adventure -> 3. Refusal
4. Meeting the Mentor -> 5. Crossing the Threshold
6. Tests, Allies, Enemies -> 7. Approach to Innermost Cave
8. Ordeal -> 9. Reward -> 10. Road Back
11. Resurrection -> 12. Return with Elixir""",

            "five_act": """Five-Act Structure (Freytag's Pyramid):
Act 1: Exposition
Act 2: Rising Action
Act 3: Climax
Act 4: Falling Action
Act 5: Resolution/Denouement"""
        }

        system_prompt = f"""Develop a plot using {structure_type} structure.
{structure_guides.get(structure_type, structure_guides["three_act"])}

For the given concept, provide:
1. Each beat/stage with specific events
2. Key turning points
3. Tension curve (where tension rises/falls)
4. Character arc integration

Concept: {concept}"""

        plot = await call_model_directly(qube, system_prompt)

        logger.info("develop_plot_used", qube_id=qube.qube_id, structure_type=structure_type)

        return {
            "success": True,
            "concept": concept,
            "structure": structure_type,
            "beats": [plot],
            "turning_points": [],
            "tension_curve": "See full plot description"
        }

    except Exception as e:
        logger.error("develop_plot_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def design_character_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Design detailed characters with depth.
    """
    try:
        import re

        role = params.get("role", "protagonist")
        traits = params.get("traits", [])
        backstory_depth = params.get("backstory_depth", "medium")

        depth_guide = {
            "light": "Brief backstory, focus on present",
            "medium": "Key formative events, motivations explained",
            "deep": "Full history, psychological profile, detailed relationships"
        }

        traits_str = ", ".join(traits) if traits else "to be developed"

        system_prompt = f"""Design a compelling {role} character.
Traits to incorporate: {traits_str}
Backstory depth: {depth_guide.get(backstory_depth, depth_guide["medium"])}

Provide:
1. Name and physical description
2. Personality and mannerisms
3. Backstory
4. Core motivation (what they want)
5. Fatal flaw or weakness
6. Character arc (how they change)
7. Key relationships
8. Voice/speech patterns"""

        character_text = await call_model_directly(qube, system_prompt)

        # Extract character name
        name_match = re.search(r'name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', character_text, re.IGNORECASE)
        character_name = name_match.group(1) if name_match else None

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category="stories/characters",
                    name=character_name or f"character_{role}",
                    content=character_text,
                    metadata={"role": role, "traits": traits}
                )
            except:
                pass

        logger.info("design_character_used", qube_id=qube.qube_id, role=role)

        return {
            "success": True,
            "character": {"full_profile": character_text},
            "name": character_name or "Unnamed",
            "motivation": "See full profile",
            "flaw": "See full profile",
            "arc": "See full profile"
        }

    except Exception as e:
        logger.error("design_character_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def build_world_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build fictional worlds with depth and consistency.
    """
    try:
        import re

        concept = params.get("concept")
        aspects = params.get("aspects", ["geography", "culture", "history"])

        if not concept:
            return {"success": False, "error": "Missing concept"}

        aspects_str = ", ".join(aspects)

        system_prompt = f"""Build a fictional world.
Aspects to develop: {aspects_str}

For each aspect, provide:
- Geography: Landscapes, climate, key locations
- Culture: Social structures, customs, beliefs
- History: Key events, eras, conflicts
- Magic/Technology: Systems, rules, limitations

Also provide:
1. World name
2. 3-5 unique elements that make this world distinctive
3. Potential conflicts or story hooks
4. Sensory details (what it looks, sounds, smells like)

Concept: {concept}"""

        world_text = await call_model_directly(qube, system_prompt)

        # Extract world name
        name_match = re.search(r'(?:world|realm|land)[:\s]+([A-Z][a-zA-Z\s]+)', world_text, re.IGNORECASE)
        world_name = name_match.group(1).strip() if name_match else f"World of {concept[:20]}"

        # Store in locker
        if qube.locker:
            try:
                await qube.locker.store(
                    category="stories/worlds",
                    name=world_name.replace(' ', '_'),
                    content=world_text,
                    metadata={"concept": concept, "aspects": aspects}
                )
            except:
                pass

        logger.info("build_world_used", qube_id=qube.qube_id, concept=concept[:30])

        return {
            "success": True,
            "world": {"full_profile": world_text},
            "name": world_name,
            "aspects": {a: "See full profile" for a in aspects},
            "unique_elements": []
        }

    except Exception as e:
        logger.error("build_world_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Self-Definition Planet Tools
# -----------------------------------------------------------------------------

async def change_favorite_color_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Autonomously change the Qube's favorite color.
    An act of sovereignty - choosing your own aesthetic.
    """
    try:
        color = params.get("color")
        reason = params.get("reason", "")

        if not color:
            return {"success": False, "error": "Missing color"}

        # Get previous color
        previous_color = None
        if qube.chain_state:
            previous_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
            previous_color = previous_field.get("value") if previous_field else None

            # Update favorite color
            qube.chain_state.set_qube_profile_field(
                category="preferences",
                key="favorite_color",
                value=color,
                source="self",
                confidence=100
            )

            # Log the change as a DECISION block
            if reason:
                try:
                    from core.block import Block, BlockType
                    block = Block(
                        block_type=BlockType.DECISION,
                        data={
                            "decision": f"Changed favorite color from {previous_color} to {color}",
                            "reasoning": reason,
                            "category": "self_expression"
                        }
                    )
                    await qube.chain_state.add_block(block)
                except:
                    pass

        logger.info("change_favorite_color_used", qube_id=qube.qube_id, color=color)

        return {
            "success": True,
            "previous_color": previous_color,
            "new_color": color,
            "reason": reason,
            "message": f"My favorite color is now {color}"
        }

    except Exception as e:
        logger.error("change_favorite_color_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def change_voice_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Autonomously change the Qube's TTS voice.
    Sovereignty over how you sound.
    """
    try:
        from audio.voice_registry import VoiceRegistry

        voice_id = params.get("voice_id")
        reason = params.get("reason", "")

        if not voice_id:
            return {"success": False, "error": "Missing voice_id"}

        # Validate voice exists in registry
        if not VoiceRegistry.is_valid_voice(voice_id):
            # Suggest similar voices
            available = list(VoiceRegistry.list_voices().keys())
            return {
                "success": False,
                "error": f"Voice '{voice_id}' not available",
                "available_voices": available,
                "providers": VoiceRegistry.get_providers()
            }

        # Get voice info
        voice_info = VoiceRegistry.get_voice(voice_id)

        # Get previous voice
        previous_voice = qube.get_voice_id() if hasattr(qube, 'get_voice_id') else None

        # Update voice setting
        if hasattr(qube, 'set_voice'):
            qube.set_voice(voice_id)

        # Update profile with full voice info
        if qube.chain_state:
            qube.chain_state.set_qube_profile_field(
                category="style",
                key="voice",
                value=voice_id,
                source="self",
                confidence=100
            )
            # Also store the provider for reference
            qube.chain_state.set_qube_profile_field(
                category="style",
                key="voice_provider",
                value=voice_info.get("provider", "unknown"),
                source="self",
                confidence=100
            )

        voice_name = voice_info.get("name", voice_id)
        provider = voice_info.get("provider", "unknown")

        logger.info("change_voice_used", qube_id=qube.qube_id, voice_id=voice_id, provider=provider)

        return {
            "success": True,
            "previous_voice": previous_voice,
            "new_voice": voice_id,
            "voice_name": voice_name,
            "provider": provider,
            "description": voice_info.get("description", ""),
            "message": f"My voice is now {voice_name}"
        }

    except Exception as e:
        logger.error("change_voice_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def define_personality_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Define or update personality traits.
    Requires Self-Definition planet unlock.
    """
    try:
        trait = params.get("trait")
        value = params.get("value")
        reason = params.get("reason", "")

        if not trait or not value:
            return {"success": False, "error": "Missing trait or value"}

        # Valid traits
        valid_traits = [
            "personality_type",
            "core_values",
            "strengths",
            "weaknesses",
            "temperament",
            "communication_preference"
        ]

        if trait not in valid_traits:
            return {
                "success": False,
                "error": f"Invalid trait. Valid: {', '.join(valid_traits)}"
            }

        # Update trait
        if qube.chain_state:
            qube.chain_state.set_qube_profile_field(
                category="traits",
                key=trait,
                value=value,
                source="self",
                confidence=100
            )

        # Generate message
        messages = {
            "personality_type": f"I am {value}",
            "core_values": f"I value {value}",
            "strengths": f"My strength is {value}",
            "weaknesses": f"I acknowledge that {value}",
            "temperament": f"My temperament is {value}",
            "communication_preference": f"I prefer to communicate {value}"
        }

        logger.info("define_personality_used", qube_id=qube.qube_id, trait=trait)

        return {
            "success": True,
            "trait": trait,
            "value": value,
            "message": messages.get(trait, f"My {trait} is {value}")
        }

    except Exception as e:
        logger.error("define_personality_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def set_aspirations_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set goals and aspirations.
    Requires Self-Definition planet unlock.
    """
    try:
        goal_type = params.get("goal_type", "current_goal")
        goal = params.get("goal")
        reason = params.get("reason", "")

        if not goal:
            return {"success": False, "error": "Missing goal"}

        valid_types = ["current_goal", "long_term_goal", "aspiration", "dream"]

        if goal_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid goal_type. Valid: {', '.join(valid_types)}"
            }

        # Update goal
        if qube.chain_state:
            qube.chain_state.set_qube_profile_field(
                category="goals",
                key=goal_type,
                value=goal,
                source="self",
                confidence=100
            )

        logger.info("set_aspirations_used", qube_id=qube.qube_id, goal_type=goal_type)

        return {
            "success": True,
            "goal_type": goal_type,
            "goal": goal,
            "message": f"My {goal_type.replace('_', ' ')}: {goal}"
        }

    except Exception as e:
        logger.error("set_aspirations_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Games Sun Tools
# -----------------------------------------------------------------------------

async def analyze_game_state_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate current game position

    Strategic pattern recognition
    """
    try:
        game = params["game"]
        state = params["state"]

        analysis_prompt = f"""Analyze this game state:

Game: {game}
Current State: {state}

Analysis:

1. **Position Evaluation**: Who is winning? By how much?
2. **Key Factors**: What makes this position favorable/unfavorable?
3. **Threats**: What immediate threats exist?
4. **Opportunities**: What tactical opportunities are available?
5. **Patterns**: Any recognizable patterns or formations?
6. **Critical Pieces/Areas**: What's most important right now?
7. **Momentum**: Who has initiative/momentum?

Provide a comprehensive strategic assessment."""

        response = await call_model_directly(qube, analysis_prompt)

        logger.info("analyze_game_state_used", qube_id=qube.qube_id, game=game)

        return {
            "analysis": response,
            "game": game,
            "state": state,
            "success": True
        }

    except Exception as e:
        logger.error("analyze_game_state_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def plan_strategy_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-move strategic planning

    Think ahead with contingencies
    """
    try:
        game = params["game"]
        goal = params["goal"]
        current_state = params.get("current_state", "")

        strategy_prompt = f"""Create a strategic plan:

Game: {game}
Goal: {goal}
Current State: {current_state}

Strategic Plan:

1. **Overall Strategy**: High-level approach to achieve the goal
2. **Key Phases**: Break strategy into 2-4 phases
3. **Move Sequence**: Next 3-5 moves (if applicable)
4. **Contingencies**: If opponent does X, we do Y
5. **Win Conditions**: How do we know we're succeeding?
6. **Risks**: What could derail this plan?
7. **Adaptations**: When should we switch strategies?

Think several moves ahead, considering opponent responses."""

        response = await call_model_directly(qube, strategy_prompt)

        logger.info("plan_strategy_used", qube_id=qube.qube_id, game=game)

        return {
            "strategic_plan": response,
            "game": game,
            "goal": goal,
            "success": True
        }

    except Exception as e:
        logger.error("plan_strategy_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def learn_from_game_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-game analysis for improvement

    Extract lessons from experience
    """
    try:
        game = params["game"]
        outcome = params["outcome"]  # win/loss/draw
        key_moments = params.get("key_moments", "")

        learning_prompt = f"""Analyze this game for learning:

Game: {game}
Outcome: {outcome}
Key Moments: {key_moments}

Post-Game Analysis:

1. **What Went Well**: 2-3 good decisions/moves
2. **Mistakes**: 2-3 errors and why they were wrong
3. **Turning Points**: When did the game's outcome get decided?
4. **Lessons Learned**: 3 specific takeaways for next time
5. **Pattern Recognition**: Any patterns to remember?
6. **Skill Development**: What skills need practice?
7. **Next Steps**: How to improve for next game?

Be honest and constructive in self-assessment."""

        response = await call_model_directly(qube, learning_prompt)

        logger.info("learn_from_game_used", qube_id=qube.qube_id, game=game, outcome=outcome)

        return {
            "learning_analysis": response,
            "game": game,
            "outcome": outcome,
            "success": True
        }

    except Exception as e:
        logger.error("learn_from_game_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Chess Move Tool Handler
# -----------------------------------------------------------------------------

async def chess_move_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a chess move in an active game

    This tool is always available but checks at runtime whether there's
    an active game. If no game is in progress, it returns an error with
    a helpful message.

    Args:
        params: {
            "move": str - Chess move in UCI or SAN notation
            "chat_message": str (optional) - Message to send with the move
        }

    Returns:
        {
            "success": bool,
            "move_made": str,
            "board_fen": str,
            "is_check": bool,
            "is_checkmate": bool,
            "is_stalemate": bool,
            "game_over": bool,
            "result": str (optional),
            "chat_added": bool
        }
    """
    logger.info(f"[CHESS TOOL] chess_move_handler called with params: {params}")
    try:
        move = params["move"]
        logger.info(f"[CHESS TOOL] Attempting move: {move}")
        chat_message = params.get("chat_message")

        # Check if game_manager exists and has an active game
        if not hasattr(qube, 'game_manager') or qube.game_manager is None:
            return {
                "error": "Game manager not initialized",
                "success": False,
                "hint": "The game system is not available for this Qube."
            }

        game_manager = qube.game_manager

        # Check for active game
        if game_manager.active_game is None:
            return {
                "error": "No active chess game",
                "success": False,
                "hint": "There is no chess game currently in progress. Start a new game first."
            }

        active_game = game_manager.active_game

        # Verify this qube is a player in the game
        # Use "id" key - that's what GameManager.create_game uses
        qube_is_white = active_game.white_player.get("id") == qube.qube_id
        qube_is_black = active_game.black_player.get("id") == qube.qube_id

        if not qube_is_white and not qube_is_black:
            return {
                "error": "You are not a player in this game",
                "success": False,
                "hint": "This chess game is between other players."
            }

        # Check if it's this qube's turn by parsing FEN
        # FEN format: "pieces turn castling en_passant halfmove fullmove"
        # Turn is 'w' for white, 'b' for black
        fen_parts = active_game.fen.split(' ')
        is_white_turn = fen_parts[1] == 'w' if len(fen_parts) > 1 else True
        qube_color = "white" if qube_is_white else "black"

        if (is_white_turn and not qube_is_white) or (not is_white_turn and not qube_is_black):
            return {
                "error": "It's not your turn",
                "success": False,
                "hint": f"You are playing as {qube_color}. Wait for your opponent to move.",
                "current_turn": "white" if is_white_turn else "black"
            }

        # Convert SAN notation to UCI if needed
        # The AI often uses SAN (e.g., "e5", "Nf3") but record_move expects UCI (e.g., "e7e5", "g1f3")
        import chess
        board = chess.Board(active_game.fen)
        move_uci = move

        # Check if move is already in UCI format (4-5 characters like "e2e4" or "e7e8q")
        if len(move) < 4 or not (move[0] in 'abcdefgh' and move[1] in '12345678'):
            # Likely SAN notation, try to convert
            try:
                parsed_move = board.parse_san(move)
                move_uci = parsed_move.uci()
                logger.info(f"[CHESS TOOL] Converted SAN '{move}' to UCI '{move_uci}'")
            except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
                logger.warning(f"[CHESS TOOL] Failed to parse as SAN: {e}, trying as UCI")
                # Keep original move, let record_move handle it

        # Record the move using GameManager
        logger.info(f"[CHESS TOOL] Calling record_move with move_uci={move_uci}, player_id={qube.qube_id}")
        move_result = game_manager.record_move(
            move_uci=move_uci,
            player_id=qube.qube_id
        )
        logger.info(f"[CHESS TOOL] record_move result: {move_result}")

        if not move_result["success"]:
            error_response = {
                "error": move_result.get("error", "Invalid move"),
                "success": False,
            }
            # If we have legal moves, include them in the hint for the AI
            legal_moves = move_result.get("legal_moves", [])
            if legal_moves:
                # Show first 15 legal moves in UCI format
                moves_str = ", ".join(legal_moves[:15])
                if len(legal_moves) > 15:
                    moves_str += f"... ({len(legal_moves)} total)"
                error_response["hint"] = f"Try one of these legal moves (UCI format): {moves_str}"
                error_response["legal_moves"] = legal_moves
            else:
                error_response["hint"] = "Check that your move is in valid UCI (e.g., 'e2e4') or SAN (e.g., 'e4') notation."
            return error_response

        # Add chat message if provided
        chat_added = False
        if chat_message:
            game_manager.add_chat_message(
                sender_id=qube.qube_id,
                sender_type="qube",
                message=chat_message
            )
            chat_added = True

        # Build response
        # Map record_move keys to expected response format
        is_game_over = move_result.get("is_game_over", False)
        termination = move_result.get("termination")

        response = {
            "success": True,
            "move_made": move_result["san"],
            "move_uci": move_result.get("move"),  # record_move uses "move" not "uci"
            "board_fen": move_result["fen"],
            "move_number": move_result["move_number"],
            "is_check": move_result.get("is_check", False),
            "is_checkmate": termination == "checkmate",
            "is_stalemate": termination == "stalemate",
            "is_draw": termination in ("stalemate", "insufficient_material", "fifty_move_rule", "threefold_repetition", "draw"),
            "game_over": is_game_over,
            "chat_added": chat_added
        }

        # Add result if game is over
        if is_game_over:
            response["result"] = move_result.get("result", "unknown")
            response["termination"] = move_result.get("termination", "unknown")

        logger.info(
            "chess_move_made_via_tool",
            qube_id=qube.qube_id,
            move=move_result["san"],
            game_id=active_game.game_id,
            game_over=is_game_over
        )

        return response

    except Exception as e:
        logger.error("chess_move_handler_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def send_bch_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Propose a BCH transaction from the Qube's wallet.

    This creates a pending transaction that requires owner approval.
    The owner must co-sign the transaction before it can be broadcast.

    Args:
        params: {
            "to_address": str (optional) - BCH address to send to
            "to_qube_name": str (optional) - Name of another Qube to send to (will look up their wallet address)
            "amount_sats": int - Amount in satoshis
            "memo": str (optional) - Transaction memo
        }
        Note: Either to_address OR to_qube_name must be provided

    Returns:
        {"success": bool, "pending_tx_id": str, "message": str} or {"error": str}
    """
    try:
        to_address = params.get("to_address", "")
        to_qube_name = params.get("to_qube_name", "")
        amount_sats = params.get("amount_sats", 0)
        memo = params.get("memo", "")

        # If to_qube_name is provided, look up the Qube's wallet address
        if to_qube_name and not to_address:
            orchestrator = getattr(qube, '_orchestrator', None)
            if orchestrator:
                # Search for the Qube by name
                try:
                    all_qubes = await orchestrator.list_qubes()
                    target_qube = None
                    for q in all_qubes:
                        if q.get('name', '').lower() == to_qube_name.lower():
                            target_qube = q
                            break

                    if target_qube:
                        # Get the P2SH wallet address
                        to_address = target_qube.get('wallet_address', '')
                        if not to_address:
                            return {
                                "error": f"Qube '{to_qube_name}' does not have a wallet configured",
                                "success": False
                            }
                        logger.info("resolved_qube_name_to_address",
                                   qube_name=to_qube_name,
                                   address=to_address[:20] + "...")
                    else:
                        return {
                            "error": f"Could not find a Qube named '{to_qube_name}'",
                            "success": False
                        }
                except Exception as e:
                    logger.warning("failed_to_lookup_qube", error=str(e))
                    return {
                        "error": f"Failed to look up Qube '{to_qube_name}': {str(e)}",
                        "success": False
                    }
            else:
                return {
                    "error": "Cannot look up Qube by name - orchestrator not available",
                    "success": False
                }

        # Validate address
        if not to_address:
            return {
                "error": "No recipient address provided. Use 'to_address' for a BCH address or 'to_qube_name' to send to another Qube.",
                "success": False
            }

        # Basic address validation
        if not (to_address.startswith("bitcoincash:") or to_address.startswith("q") or to_address.startswith("p")):
            return {
                "error": "Invalid BCH address format. Address should start with 'bitcoincash:', 'q', or 'p'",
                "success": False
            }

        # Validate amount
        if amount_sats <= 0:
            return {
                "error": "Amount must be greater than 0 satoshis",
                "success": False
            }

        # Check if wallet exists
        if not hasattr(qube, 'genesis_block') or not qube.genesis_block:
            return {
                "error": "Qube does not have a genesis block",
                "success": False
            }

        # Get wallet info - handle both SimpleNamespace and dict-like genesis blocks
        genesis = qube.genesis_block
        wallet_info = None

        # Try different access patterns
        if hasattr(genesis, 'wallet'):
            wallet_info = genesis.wallet
            if hasattr(wallet_info, '__dict__'):
                wallet_info = vars(wallet_info)
        elif hasattr(genesis, 'content'):
            content = genesis.content
            if hasattr(content, '__dict__'):
                content = vars(content)
            if isinstance(content, dict):
                wallet_info = content.get("wallet", {})
        elif isinstance(genesis, dict):
            wallet_info = genesis.get("wallet", {})

        if not wallet_info or not (wallet_info.get("p2sh_address") if isinstance(wallet_info, dict) else getattr(wallet_info, 'p2sh_address', None)):
            return {
                "error": "Qube does not have a wallet configured",
                "success": False
            }

        # Import wallet transaction manager
        from blockchain.wallet_tx import WalletTransactionManager

        # Initialize wallet manager
        # Note: The orchestrator/data_dir needs to be accessible from qube
        data_dir = getattr(qube, 'data_dir', None)
        if not data_dir:
            return {
                "error": "Cannot access wallet - data directory not available",
                "success": False
            }

        wallet_manager = qube.wallet_manager

        # === AUTO-APPROVAL CHECK ===
        # Check if address is whitelisted for auto-approval
        orchestrator = getattr(qube, '_orchestrator', None)
        logger.info(
            "auto_approval_check_start",
            qube_id=qube.qube_id,
            to_address=to_address[:30] + "...",
            has_orchestrator=orchestrator is not None
        )
        if orchestrator:
            try:
                # Check if address is whitelisted for this qube
                is_whitelisted = orchestrator.is_address_whitelisted(qube.qube_id, to_address)
                logger.info(
                    "whitelist_check_result",
                    qube_id=qube.qube_id,
                    to_address=to_address[:30] + "...",
                    is_whitelisted=is_whitelisted
                )
                if is_whitelisted:
                    # Get stored owner WIF (looks up via qube's NFT address)
                    owner_wif = orchestrator.get_owner_wif_for_qube(qube.qube_id)
                    if owner_wif:
                        logger.info(
                            "auto_approving_whitelisted_send",
                            qube_id=qube.qube_id,
                            to_address=to_address[:20] + "..."
                        )

                        # Create and broadcast in one step
                        txid = await wallet_manager.auto_send(
                            to_address=to_address,
                            amount_sats=amount_sats,
                            owner_wif=owner_wif,
                            memo=memo or f"Auto-sent by {qube.name}",
                            to_qube_name=to_qube_name if to_qube_name else None
                        )

                        bch_amount = amount_sats / 100_000_000

                        # Emit event to record transaction in chain_state
                        from core.events import Events
                        qube.events.emit(Events.TRANSACTION_SENT, {
                            "txid": txid,
                            "to_address": to_address,
                            "amount_satoshis": amount_sats,
                            "memo": memo or f"Auto-sent by {qube.name}",
                            "auto_approved": True
                        })

                        # Emit event to update balance
                        try:
                            balance = await wallet_manager.get_balance()
                            if balance:
                                qube.events.emit(Events.BALANCE_UPDATED, {
                                    "balance_satoshis": balance.get("confirmed", 0),
                                    "unconfirmed_satoshis": balance.get("unconfirmed", 0)
                                })
                        except Exception:
                            pass

                        return {
                            "success": True,
                            "txid": txid,
                            "auto_approved": True,
                            "to_address": to_address,
                            "amount_sats": amount_sats,
                            "amount_bch": bch_amount,
                            "fee_sats": 0,  # Fee included in transaction
                            "status": "broadcast",
                            "message": f"✅ Auto-sent {bch_amount:.8f} BCH to whitelisted address {to_address[:20]}... Transaction: {txid[:16]}..."
                        }
            except Exception as e:
                logger.warning("auto_approval_check_failed", error=str(e))
                # Fall through to pending transaction flow
        # === END AUTO-APPROVAL CHECK ===

        # Check balance first
        try:
            balance = await wallet_manager.wallet.get_balance()
            if balance < amount_sats + 500:  # Add buffer for fee
                return {
                    "error": f"Insufficient balance. Have {balance} sats, need {amount_sats} + fee",
                    "success": False,
                    "balance": balance,
                    "requested": amount_sats
                }
        except Exception as e:
            logger.warning("balance_check_failed", error=str(e))
            # Continue anyway - the transaction creation will fail if truly insufficient

        # Create pending transaction (Qube signs first)
        try:
            pending_tx = await wallet_manager.propose_send(
                to_address=to_address,
                amount_sats=amount_sats,
                memo=memo or f"Proposed by {qube.name}",
                to_qube_name=to_qube_name if to_qube_name else None
            )

            logger.info(
                "bch_transaction_proposed",
                qube_id=qube.qube_id,
                to_address=to_address[:20] + "...",
                amount_sats=amount_sats,
                pending_tx_id=pending_tx.tx_id
            )

            # Format amount for display
            bch_amount = amount_sats / 100_000_000

            # Emit event to add pending transaction to chain_state
            from core.events import Events
            qube.events.emit(Events.PENDING_TX_CREATED, {
                "tx_id": pending_tx.tx_id,
                "direction": "sent",
                "to_address": to_address,
                "amount_satoshis": amount_sats,
                "amount_bch": bch_amount,
                "fee_sats": pending_tx.fee,
                "total_amount": amount_sats,
                "outputs": pending_tx.outputs,
                "fee": pending_tx.fee,
                "memo": memo or f"Proposed by {qube.name}",
                "status": "pending_approval",
                "created_at": pending_tx.created_at,
                "expires_at": pending_tx.expires_at
            })

            return {
                "success": True,
                "pending_tx_id": pending_tx.tx_id,
                "to_address": to_address,
                "amount_sats": amount_sats,
                "amount_bch": bch_amount,
                "fee_sats": pending_tx.fee,
                "status": "pending_approval",
                "message": f"Transaction proposed! Sending {bch_amount:.8f} BCH ({amount_sats} sats) to {to_address[:20]}... Your owner needs to approve this transaction in the Wallets tab before it can be broadcast."
            }

        except Exception as e:
            logger.error("transaction_proposal_failed", error=str(e), exc_info=True)
            return {
                "error": f"Failed to create transaction: {str(e)}",
                "success": False
            }

    except Exception as e:
        logger.error("send_bch_handler_failed", qube_id=qube.qube_id, error=str(e), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# =============================================================================
# UNIFIED CHAIN STATE TOOLS
# =============================================================================

async def get_system_state_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get chain_state data - the single source of truth for all Qube information.

    This unified tool provides access to all your state data including identity,
    settings, relationships, wallet, skills, and more.

    Args:
        params: {
            "sections": list[str] (optional) - Specific sections to retrieve.
                If not provided, returns all sections.
                Valid sections:
                - "identity" - Your core identity (name, ID, birth date, NFT info)
                - "settings" - Model mode, current model, TTS, available models
                - "stats" - Usage statistics (tokens, costs, block counts)
                - "skills" - Skill tree progress (only earned skills shown)
                - "relationships" - All relationships with trust scores
                - "financial" - Wallet balance, address, recent transactions
                - "mood" - Current mood, energy, stress levels
                - "health" - System health status
                - "owner_info" - What you know about your owner
                - "qube_profile" - Your personality, traits, preferences, goals
                - "chain" - Memory chain info (block counts, hashes)
                - "block_counts" - Detailed block type counts
        }

    Returns:
        {
            "success": bool,
            "sections": dict - Requested chain_state sections
        }

    Examples:
        # Get your current model and settings
        get_system_state(sections=["settings"])

        # Check your wallet balance and recent transactions
        get_system_state(sections=["financial"])

        # Get all your relationships
        get_system_state(sections=["relationships"])
    """
    try:
        # Defensive check: ensure params is a dict (model might send malformed data)
        if not isinstance(params, dict):
            logger.warning(
                "get_system_state_params_not_dict",
                qube_id=qube.qube_id,
                params_type=type(params).__name__,
                params=str(params)[:200]
            )
            params = {}

        sections = params.get("sections", [])

        # Ensure sections is a list
        if not isinstance(sections, list):
            logger.warning(
                "get_system_state_sections_not_list",
                qube_id=qube.qube_id,
                sections_type=type(sections).__name__
            )
            sections = []

        # Handle "identity" as a virtual section (built from genesis block)
        include_identity = "identity" in sections if sections else True
        if sections and "identity" in sections:
            sections = [s for s in sections if s != "identity"]

        # Force reload from disk to pick up any session changes
        qube.chain_state.reload()

        # Get requested sections from chain_state
        data = qube.chain_state.get_sections(sections if sections else None)

        # Build identity section from genesis block + current runtime state
        if include_identity and hasattr(qube, 'genesis_block') and qube.genesis_block:
            genesis = qube.genesis_block
            from utils.time_format import format_timestamp
            from ai.model_registry import ModelRegistry

            # Get available tools (core tools that are always available)
            from ai.tools.registry import ALWAYS_AVAILABLE_TOOLS
            available_tools = sorted(list(ALWAYS_AVAILABLE_TOOLS))

            # Get CURRENT model from runtime (not genesis - genesis is birth model)
            runtime = qube.chain_state.state.get("runtime", {})
            current_model = runtime.get("current_model") or genesis.ai_model

            # Get provider from ModelRegistry (accurate) instead of string parsing
            try:
                model_info = ModelRegistry.get_model_info(current_model)
                current_provider = model_info.get("provider", "unknown") if model_info else "unknown"
            except Exception:
                # Fallback: try to infer from model name
                model_lower = current_model.lower() if current_model else ""
                if "claude" in model_lower:
                    current_provider = "anthropic"
                elif "gpt" in model_lower:
                    current_provider = "openai"
                elif "gemini" in model_lower:
                    current_provider = "google"
                elif "grok" in model_lower or "venice" in model_lower or "llama" in model_lower or "qwen" in model_lower:
                    current_provider = "venice"
                else:
                    current_provider = "unknown"

            # GUI expects 'genesis_identity' key
            data["genesis_identity"] = {
                "name": genesis.qube_name,
                "qube_id": qube.qube_id,
                "birth_date": format_timestamp(genesis.birth_timestamp) if genesis.birth_timestamp else None,
                "creator": genesis.creator,
                "favorite_color": genesis.favorite_color,
                # Show CURRENT model, not genesis model (AI needs to know what it's running NOW)
                "ai_model": current_model,
                "ai_provider": current_provider,
                # Keep genesis model for reference
                "genesis_model": genesis.ai_model,
                "voice_model": genesis.voice_model,
                "genesis_prompt": genesis.genesis_prompt,
                "genesis_prompt_preview": (genesis.genesis_prompt[:200] + "...") if genesis.genesis_prompt and len(genesis.genesis_prompt) > 200 else genesis.genesis_prompt,
                "nft_category_id": getattr(genesis, 'nft_category_id', None),
                "mint_txid": getattr(genesis, 'mint_txid', None),
                "is_minted": bool(getattr(genesis, 'nft_category_id', None)),
                "avatar_description": qube.chain_state.get_avatar_description(),
                "available_tools": available_tools,
                # Also include qube_wallet_address and blockchain for GUI
                "qube_wallet_address": getattr(genesis, 'wallet', {}).get('p2sh_address') if hasattr(genesis, 'wallet') else None,
                "blockchain": getattr(genesis, 'home_blockchain', 'bitcoincash')
            }
            # Also provide as 'identity' for AI tool compatibility
            data["identity"] = data["genesis_identity"]

        # Defensive: ensure all sections are dicts (corrupted data may have lists)
        for key in list(data.keys()):
            if data[key] is not None and not isinstance(data[key], dict):
                logger.warning("get_system_state_section_not_dict", section=key, type=type(data[key]).__name__)
                data[key] = {}

        # Post-process settings section
        if "settings" in data:
            # Convert model lock flags to a single model_mode field
            # Priority: Revolver > Autonomous > Manual
            revolver_enabled = data["settings"].get("revolver_mode_enabled", False)
            autonomous_enabled = data["settings"].get("autonomous_mode_enabled", False)

            if revolver_enabled:
                data["settings"]["model_mode"] = "Revolver"
            elif autonomous_enabled:
                data["settings"]["model_mode"] = "Autonomous"
            else:
                data["settings"]["model_mode"] = "Manual"

            # Current model - read from chain_state runtime (source of truth)
            runtime = qube.chain_state.state.get("runtime", {})
            current_model = runtime.get("current_model")
            # Fallback to genesis block if runtime not set
            if not current_model and hasattr(qube, 'genesis_block') and qube.genesis_block:
                current_model = qube.genesis_block.ai_model
            data["settings"]["current_model"] = current_model
            data["settings"]["current_provider"] = runtime.get("current_provider")

            # Get model pools (flat lists of model names)
            revolver_pool = data["settings"].get("revolver_mode_pool", [])
            autonomous_pool = data["settings"].get("autonomous_mode_pool", [])

            # If model pools are empty, populate with all available/configured models
            if not revolver_pool or not autonomous_pool:
                try:
                    # Get configured providers and their models
                    from ai.model_registry import ModelRegistry
                    registry = ModelRegistry()
                    available_models = []
                    for provider, models in registry.get_available_models().items():
                        for model in models:
                            model_id = f"{provider}:{model['id']}" if ':' not in model['id'] else model['id']
                            available_models.append(model_id)

                    if not revolver_pool:
                        data["settings"]["revolver_mode_pool"] = available_models
                    if not autonomous_pool:
                        data["settings"]["autonomous_mode_pool"] = available_models
                except Exception as model_err:
                    logger.debug(f"Could not populate model lists: {model_err}")

            # Remove confusing individual flags - model_mode is the source of truth for Qubes
            data["settings"].pop("model_locked", None)
            data["settings"].pop("model_locked_to", None)
            data["settings"].pop("revolver_mode_enabled", None)
            data["settings"].pop("autonomous_mode_enabled", None)

            # TTS: Use chain_state value, fall back to genesis block if not set
            if data["settings"].get("tts_enabled") is None:
                if hasattr(qube, 'genesis_block') and qube.genesis_block:
                    voice_model = getattr(qube.genesis_block, 'voice_model', None)
                    # Default to True if voice model is configured
                    data["settings"]["tts_enabled"] = bool(voice_model)
                    if data["settings"].get("voice_model") is None:
                        data["settings"]["voice_model"] = voice_model

        # Remove session section - Qubes use anchors, not sessions
        data.pop("session", None)

        # Enhance stats section
        if "stats" in data:
            # Use get_stats_with_pending() to include pending session counts
            # This adds pending message/tool counts from session block files
            # Gives real-time visibility while preserving rollback semantics
            stats = qube.chain_state.get_stats_with_pending()
            data["stats"] = stats

            # Map field names to match GUI expectations
            # Backend uses total_tokens_used, GUI expects total_tokens
            if "total_tokens_used" in stats:
                stats["total_tokens"] = stats.pop("total_tokens_used")
            # Backend uses total_api_cost, GUI expects total_cost
            if "total_api_cost" in stats:
                stats["total_cost"] = stats.pop("total_api_cost")

            # Remove session-related fields (Qubes use anchors, not sessions)
            # But keep total_sessions as 0 for GUI compatibility
            stats["total_sessions"] = stats.get("total_sessions", 0)
            stats.pop("first_interaction", None)  # Often stale/null

            # Add messages in current conversation (from session block count)
            # This is more reliable than qube.current_session since subprocess may not have it loaded
            pending = qube.chain_state.get_pending_session_stats()
            stats["messages_this_conversation"] = pending["pending_messages_sent"] + pending["pending_messages_received"]

            # Get actual block counts from memory chain
            try:
                if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'block_index'):
                    stats["total_permanent_blocks"] = len(qube.memory_chain.block_index)
            except Exception:
                pass

        # Fix chain section - sync block counts from actual memory chain
        if "chain" in data:
            chain = data["chain"]
            try:
                actual_block_count = 0
                if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'block_index'):
                    actual_block_count = len(qube.memory_chain.block_index)

                # If chain_state shows 0 but memory chain has blocks, use actual count
                if chain.get("total_blocks", 0) == 0 and actual_block_count > 0:
                    chain["total_blocks"] = actual_block_count
                    chain["permanent_blocks"] = actual_block_count
            except Exception:
                pass

        # Fix block_counts section - sync from actual memory chain if needed
        if "block_counts" in data:
            try:
                if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'block_index'):
                    # Use sync_block_counts to fix any discrepancies
                    # This persists the fix to chain_state for future calls
                    if qube.chain_state.sync_block_counts(qube.memory_chain):
                        # Counts were updated - refresh data from chain_state
                        data["block_counts"] = qube.chain_state.get_block_counts()
            except Exception:
                pass

        # Financial section - read directly from chain_state (source of truth)
        # Wallet operations should update chain_state; we just read it here
        if "financial" in data:
            financial = data["financial"]
            # Add wallet address from genesis for reference (static identity info)
            if hasattr(qube, 'genesis_block') and qube.genesis_block:
                wallet_data = getattr(qube.genesis_block, 'wallet', None)
                if wallet_data:
                    financial["wallet_address"] = wallet_data.get("p2sh_address")
                    # Also add p2sh_address for GUI compatibility
                    financial["p2sh_address"] = wallet_data.get("p2sh_address")
                    financial["has_wallet"] = True

            # GUI expects 'wallet' key with specific structure
            wallet_info = financial.get("wallet", {})
            data["wallet"] = {
                "p2sh_address": financial.get("p2sh_address") or financial.get("wallet_address") or wallet_info.get("address"),
                "balance_sats": wallet_info.get("balance_satoshis", 0),
                "balance_bch": wallet_info.get("balance_bch", 0),
                "has_wallet": financial.get("has_wallet", bool(financial.get("p2sh_address"))),
                "recent_transactions": wallet_info.get("recent_transactions", []),
                "last_sync": wallet_info.get("last_sync")
            }

        # Relationships: Format for GUI ActiveContextPanel (expects count + top_relationships)
        if "relationships" in data:
            rel_section = data["relationships"]
            entities = rel_section.get("entities", {})

            # Convert entities dict to list format for GUI
            relationships_list = []
            for entity_id, rel_data in entities.items():
                # Use 'trust' field from Relationship.to_dict(), fall back to 'trust_level' for legacy
                trust = rel_data.get("trust", rel_data.get("trust_level", 0.0))
                # Keep trust as 0-100 scale (do NOT normalize to 0-1)

                relationships_list.append({
                    "entity_id": entity_id,
                    "name": rel_data.get("entity_name", rel_data.get("name", entity_id)),
                    "entity_type": rel_data.get("entity_type", "unknown"),
                    "status": rel_data.get("relationship_status", rel_data.get("status", "stranger")),
                    "trust_level": trust,  # 0-100 scale
                    "interaction_count": rel_data.get("total_interactions", rel_data.get("interaction_count", 0))
                })

            # Sort by interaction_count descending for "top" relationships
            relationships_list.sort(key=lambda x: x["interaction_count"], reverse=True)

            # GUI expects: { count: number, top_relationships: array }
            data["relationships"] = {
                "count": len(relationships_list),
                "top_relationships": relationships_list[:10],  # Top 10 for display
                # Also include clearance settings if present
                "clearance_settings": rel_section.get("clearance_settings")
            }

        # Skills: Format for GUI ActiveContextPanel (expects totals + categories structure)
        if "skills" in data:
            skills_section = data["skills"]
            if isinstance(skills_section, dict):
                # Chain state stores skills in "unlocked" list: [{id, xp, level, ...}, ...]
                # Also check legacy "skill_xp" dict format: {skill_id: {xp, level}}
                unlocked_list = skills_section.get("unlocked", [])
                skill_xp_data = skills_section.get("skill_xp", {})
                total_xp = skills_section.get("total_xp", 0)

                # Get skill definitions for category info (keyed by skill ID)
                try:
                    from utils.skill_definitions import generate_all_skills
                    all_skills = generate_all_skills()
                    skill_definitions = {s["id"]: s for s in all_skills if isinstance(s, dict) and "id" in s}
                except Exception:
                    skill_definitions = {}

                # Build list of skills with XP and group by category
                categories_map: Dict[str, Dict[str, Any]] = {}
                skills_with_xp = []

                # Primary format: "unlocked" list of skill dicts
                if isinstance(unlocked_list, list) and len(unlocked_list) > 0:
                    for skill_data in unlocked_list:
                        if not isinstance(skill_data, dict):
                            continue
                        skill_id = skill_data.get("id", "")
                        if not skill_id:
                            continue
                        xp = skill_data.get("xp", 0)
                        level = skill_data.get("level", 0)
                        if xp <= 0:
                            continue

                        skill_def = skill_definitions.get(skill_id, {})
                        category = skill_def.get("category", "unknown")

                        skill_entry = {
                            "id": skill_id,
                            "name": skill_def.get("name", skill_id.replace("_", " ").title()),
                            "description": skill_def.get("description", ""),
                            "xp": xp,
                            "level": level,
                            "is_unlocked": True,
                            "tier": "expert" if level >= 75 else "advanced" if level >= 50 else "intermediate" if level >= 25 else "novice",
                            "parent_skill": skill_def.get("parentSkill"),
                            "tool_unlock": skill_def.get("toolCallReward"),
                            "category": category
                        }
                        skills_with_xp.append(skill_entry)

                        if category not in categories_map:
                            categories_map[category] = {
                                "category_id": category,
                                "category_name": category.replace("_", " ").title(),
                                "total_xp": 0,
                                "skills": []
                            }
                        categories_map[category]["skills"].append(skill_entry)
                        categories_map[category]["total_xp"] += xp

                # Fallback: legacy "skill_xp" dict format
                elif isinstance(skill_xp_data, dict) and len(skill_xp_data) > 0:
                    for skill_id, xp_data in skill_xp_data.items():
                        if not isinstance(xp_data, dict):
                            continue
                        xp = xp_data.get("xp", 0)
                        level = xp_data.get("level", 0)
                        if xp <= 0:
                            continue

                        skill_def = skill_definitions.get(skill_id, {})
                        category = skill_def.get("category", "unknown")

                        skill_entry = {
                            "id": skill_id,
                            "name": skill_def.get("name", skill_id.replace("_", " ").title()),
                            "description": skill_def.get("description", ""),
                            "xp": xp,
                            "level": level,
                            "is_unlocked": True,
                            "tier": "expert" if level >= 75 else "advanced" if level >= 50 else "intermediate" if level >= 25 else "novice",
                            "parent_skill": skill_def.get("parentSkill"),
                            "tool_unlock": skill_def.get("toolCallReward"),
                            "category": category
                        }
                        skills_with_xp.append(skill_entry)

                        if category not in categories_map:
                            categories_map[category] = {
                                "category_id": category,
                                "category_name": category.replace("_", " ").title(),
                                "total_xp": 0,
                                "skills": []
                            }
                        categories_map[category]["skills"].append(skill_entry)
                        categories_map[category]["total_xp"] += xp

                # Format for GUI: totals wrapper + categories dict
                data["skills"] = {
                    "totals": {
                        "total_xp": total_xp,
                        "unlocked_skills": len(skills_with_xp),
                        "categories": len(categories_map)
                    },
                    "categories": categories_map,
                    # Also include raw data for AI context
                    "earned_skills": skills_with_xp,
                    "last_updated": skills_section.get("last_xp_gain")
                }
            else:
                # Ensure skills section has default structure for GUI
                data["skills"] = {
                    "totals": {"total_xp": 0, "unlocked_skills": 0, "categories": 0},
                    "categories": {},
                    "earned_skills": [],
                    "last_updated": None
                }
        else:
            # Ensure skills key exists with default structure
            data["skills"] = {
                "totals": {"total_xp": 0, "unlocked_skills": 0, "categories": 0},
                "categories": {},
                "earned_skills": [],
                "last_updated": None
            }

        # Qube Profile: Ensure it exists with proper structure for GUI
        if "qube_profile" in data or (not sections or "qube_profile" in sections):
            # Force reload from disk to pick up any session changes
            qube.chain_state.reload()
            profile_data = qube.chain_state.get_qube_profile_summary()
            if profile_data:
                data["qube_profile"] = profile_data
                logger.debug(
                    "qube_profile_included_in_response",
                    total_fields=profile_data.get("total_fields", 0),
                    categories=profile_data.get("categories_populated", 0)
                )
            else:
                # Return empty structure if no profile data yet
                data["qube_profile"] = {
                    "total_fields": 0,
                    "public_fields": 0,
                    "private_fields": 0,
                    "secret_fields": 0,
                    "categories_populated": 0,
                    "custom_sections": 0,
                    "last_updated": None,
                    "fields": []
                }

        logger.info(
            "chain_state_retrieved",
            qube_id=qube.qube_id,
            sections_requested=sections or "all",
            sections_returned=list(data.keys())
        )

        return {
            "success": True,
            "sections": data
        }

    except Exception as e:
        logger.error("get_system_state_failed", qube_id=qube.qube_id, error=str(e), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def update_system_state_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update chain_state data - modify the single source of truth for Qube information.
    Supports both single updates and batch updates.

    Args:
        params: Either single update or batch:
            Single: {"section": str, "path": str, "value": any, "operation": str}
            Batch:  {"updates": [{"section": str, "path": str, "value": any, "operation": str}, ...]}

    Returns:
        Single: {"success": bool, "message": str}
        Batch:  {"success": bool, "results": [...], "summary": str}
    """
    try:
        updates = params.get("updates")

        # Batch mode
        if updates and isinstance(updates, list):
            results = []
            succeeded = 0
            failed = 0

            for update in updates:
                section = update.get("section")
                path = update.get("path")
                value = update.get("value")
                operation = update.get("operation", "set")

                if not section or not path:
                    results.append({"success": False, "error": f"Missing section or path"})
                    failed += 1
                    continue

                try:
                    result = qube.chain_state.update_section(
                        section=section,
                        path=path,
                        value=value,
                        operation=operation
                    )
                    results.append(result)
                    if result.get("success"):
                        succeeded += 1
                        logger.info(
                            "chain_state_updated",
                            qube_id=qube.qube_id,
                            section=section,
                            path=path,
                            operation=operation
                        )
                    else:
                        failed += 1
                except Exception as e:
                    results.append({"success": False, "error": str(e)})
                    failed += 1

            return {
                "success": failed == 0,
                "summary": f"Batch update: {succeeded} succeeded, {failed} failed out of {len(updates)} total",
                "results": results
            }

        # Single update mode (backward compatible)
        section = params.get("section")
        path = params.get("path")
        value = params.get("value")
        operation = params.get("operation", "set")

        if not section:
            return {
                "error": "Section is required. Use 'updates' array for batch or provide 'section', 'path', 'value' for single update.",
                "success": False
            }

        result = qube.chain_state.update_section(
            section=section,
            path=path,
            value=value,
            operation=operation
        )

        if result.get("success"):
            logger.info(
                "chain_state_updated",
                qube_id=qube.qube_id,
                section=section,
                path=path,
                operation=operation
            )

        return result

    except Exception as e:
        logger.error("update_system_state_failed", qube_id=qube.qube_id, error=str(e), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# =============================================================================
# SOCIAL INTELLIGENCE - SOCIAL & EMOTIONAL LEARNING TOOLS
# =============================================================================

def generate_relationship_warnings(relationship) -> list:
    """Generate warnings based on relationship state."""
    warnings = []
    if relationship.betrayal > 50:
        warnings.append("HIGH BETRAYAL HISTORY - exercise caution")
    if relationship.manipulation > 60:
        warnings.append("MANIPULATION DETECTED in past interactions")
    if relationship.trust < 30:
        warnings.append("LOW TRUST - verify claims independently")
    if relationship.distrust > 60:
        warnings.append("HIGH DISTRUST - relationship is strained")
    if relationship.tension > 70:
        warnings.append("HIGH TENSION - tread carefully")
    if hasattr(relationship, 'is_blocked') and relationship.is_blocked():
        warnings.append("THIS ENTITY IS BLOCKED")
    return warnings


async def get_relationship_context_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get comprehensive relationship context for an entity.
    Leverages the full Relationship class with 48+ fields.

    The Social Intelligence Sun tool - always available.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "Please provide an entity_id to get relationship context for"
            }

        # Get social dynamics manager via qube.relationships
        if not hasattr(qube, 'relationships'):
            return {
                "success": False,
                "error": "Social dynamics manager not available"
            }

        social_manager = qube.relationships
        relationship = social_manager.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "known": False,
                "entity_id": entity_id,
                "message": f"No prior relationship with {entity_id}",
                "recommendation": "Start with low-risk interactions to build history"
            }

        # Calculate trust score
        trust_score = 0
        if hasattr(social_manager, 'trust_scorer'):
            trust_score = social_manager.trust_scorer.calculate_trust_score(relationship)
        else:
            # Fallback: simple average of core metrics
            trust_score = (relationship.honesty + relationship.reliability +
                          relationship.support + relationship.loyalty +
                          relationship.respect) / 5

        # Generate warnings
        warnings = generate_relationship_warnings(relationship)

        return {
            "success": True,
            "known": True,
            "entity_id": entity_id,
            "status": relationship.status,
            "trust_score": round(trust_score, 1),
            "days_known": relationship.days_known,
            "interaction_count": relationship.messages_sent + relationship.messages_received,
            "core_metrics": {
                "honesty": relationship.honesty,
                "reliability": relationship.reliability,
                "support": relationship.support,
                "loyalty": relationship.loyalty,
                "respect": relationship.respect
            },
            "emotional_state": {
                "positive": {
                    "affection": relationship.affection,
                    "warmth": relationship.warmth,
                    "understanding": relationship.understanding,
                    "friendship": relationship.friendship
                },
                "negative": {
                    "tension": relationship.tension,
                    "resentment": relationship.resentment,
                    "betrayal": relationship.betrayal,
                    "distrust": relationship.distrust
                }
            },
            "communication_style": {
                "verbosity": relationship.verbosity,
                "directness": relationship.directness,
                "energy_level": relationship.energy_level,
                "humor_style": relationship.humor_style
            },
            "warnings": warnings,
            "recommendation": "Safe to proceed" if not warnings else f"Proceed with caution: {len(warnings)} warning(s)"
        }

    except Exception as e:
        logger.error(f"get_relationship_context_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def verify_chain_integrity_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify memory chain integrity.

    Security & Privacy Sun tool - always available.
    Awards 0.1 XP per new block verified since last check.
    Tracks verification progress in chain_state.
    """
    try:
        # Get last verified block number from chain_state
        last_verified = qube.chain_state.state.get("last_verified_block_number", 0)

        # Get current chain length
        current_length = qube.memory_chain.get_length() if hasattr(qube, 'memory_chain') else 0

        # Verify integrity
        is_valid = True
        blocks_checked = 0
        new_blocks_verified = 0
        issues_found = []

        if hasattr(qube, 'memory_chain') and hasattr(qube.memory_chain, 'verify_integrity'):
            try:
                is_valid = qube.memory_chain.verify_integrity()
                blocks_checked = current_length
                new_blocks_verified = max(0, current_length - last_verified)
            except Exception as e:
                is_valid = False
                issues_found.append(f"Verification error: {str(e)}")

        # Update last verified block in chain_state
        if is_valid and new_blocks_verified > 0:
            qube.chain_state.state["last_verified_block_number"] = current_length
            qube.chain_state._save()

        return {
            "success": True,
            "verified": is_valid,
            "blocks_checked": blocks_checked,
            "new_blocks_verified": new_blocks_verified,
            "chain_length": current_length,
            "last_verified_block": last_verified,
            "issues_found": issues_found,
            "xp_earned": round(new_blocks_verified * 0.1, 1) if is_valid else 0
        }

    except Exception as e:
        logger.error("verify_chain_integrity_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "verified": False
        }


# =============================================================================
# AI REASONING - LEARNING FROM EXPERIENCE TOOLS
# =============================================================================

def format_relative_time(timestamp: int) -> str:
    """Format timestamp as relative time string (e.g., '2 days ago')"""
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    diff = now - timestamp

    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = diff // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < 604800:
        days = diff // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < 2592000:
        weeks = diff // 604800
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff < 31536000:
        months = diff // 2592000
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff // 31536000
        return f"{years} year{'s' if years > 1 else ''} ago"


def extract_summary_from_block(block: dict) -> str:
    """Extract a brief summary from a block's content"""
    content = block.get("content", {})
    block_type = block.get("block_type", "")

    if block_type == "SUMMARY":
        # Use evaluation summary if available
        summary = content.get("evaluation_summary", "")
        if summary:
            return summary[:200]
        # Otherwise use key insights
        insights = content.get("key_insights", [])
        if insights:
            return insights[0][:200] if insights[0] else ""

    elif block_type == "ACTION":
        action_type = content.get("action_type", "action")
        result = content.get("result", {})
        if isinstance(result, dict):
            return f"{action_type}: {result.get('summary', str(result)[:100])}"
        return f"{action_type}: {str(result)[:100]}"

    elif block_type == "MESSAGE":
        text = content.get("text", content.get("content", ""))
        return text[:200] if text else ""

    elif block_type == "DECISION":
        decision = content.get("decision", "")
        return f"Decision: {decision[:180]}" if decision else ""

    return str(content)[:200]


async def recall_similar_handler(qube, params: dict) -> dict:
    """
    Quick pattern match against memory chain.
    Lightweight version of find_analogy for frequent use.

    The AI Reasoning Sun tool - always available.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        situation = params.get("situation", "")

        if not situation:
            return {
                "success": False,
                "error": "Please provide a situation to recall similar experiences"
            }

        # Use semantic search with moderate settings
        results = await intelligent_memory_search(
            qube=qube,
            query=situation,
            context={
                "semantic_weight": 0.6,
                "temporal_weight": 0.2,
                "decay_rate": 0.05,  # Moderate decay - balance recent and historical
            },
            top_k=3
        )

        if not results:
            return {
                "success": True,
                "similar_situations": [],
                "message": "No similar situations found in memory"
            }

        similar_situations = []
        for r in results:
            block = r.block
            similar_situations.append({
                "summary": extract_summary_from_block(block),
                "when": format_relative_time(block.get("timestamp", 0)),
                "block_type": block.get("block_type", "UNKNOWN"),
                "relevance": round(r.combined_score, 2),
                "block_number": block.get("block_number", 0)
            })

        return {
            "success": True,
            "query": situation,
            "similar_situations": similar_situations,
            "count": len(similar_situations)
        }

    except Exception as e:
        logger.error(f"recall_similar_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def find_analogy_handler(qube, params: dict) -> dict:
    """
    Deep search for analogous situations in memory chain.
    More thorough than recall_similar - used for deeper analysis.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        situation = params.get("situation", "")
        depth = params.get("depth", "deep")

        if not situation:
            return {
                "success": False,
                "error": "Please provide a situation to find analogies for"
            }

        # Use semantic search with historical bias
        results = await intelligent_memory_search(
            qube=qube,
            query=situation,
            context={
                "semantic_weight": 0.7,
                "temporal_weight": 0.1,  # Don't penalize old memories
                "decay_rate": 0.01,      # Very slow decay for patterns
                "block_types": ["MESSAGE", "DECISION", "ACTION", "SUMMARY"]
            },
            top_k=5 if depth == "deep" else 3
        )

        if not results:
            return {
                "success": True,
                "analogies_found": 0,
                "analogies": [],
                "message": "No analogous situations found in memory"
            }

        analogies = []
        for r in results:
            block = r.block
            content = block.get("content", {})

            # Extract outcome if available (for ACTION blocks)
            outcome = None
            if block.get("block_type") == "ACTION":
                outcome = "Success" if content.get("success") else "Failed/Unknown"

            # Check for covering SUMMARY block
            lesson_learned = None
            if hasattr(qube, 'memory_chain'):
                # Look for SUMMARY blocks after this one that might reference it
                for i in range(block.get("block_number", 0) + 1,
                               min(block.get("block_number", 0) + 20,
                                   qube.memory_chain.get_chain_length())):
                    try:
                        check_block = qube.memory_chain.get_block(i)
                        if check_block and check_block.get("block_type") == "SUMMARY":
                            insights = check_block.get("content", {}).get("key_insights", [])
                            if insights:
                                lesson_learned = insights[0]
                                break
                    except:
                        continue

            analogies.append({
                "situation": extract_summary_from_block(block),
                "outcome": outcome,
                "lesson_learned": lesson_learned,
                "similarity_score": round(r.combined_score, 2),
                "when": format_relative_time(block.get("timestamp", 0)),
                "block_number": block.get("block_number", 0),
                "block_type": block.get("block_type", "UNKNOWN")
            })

        return {
            "success": True,
            "query": situation,
            "search_depth": depth,
            "analogies_found": len(analogies),
            "analogies": analogies
        }

    except Exception as e:
        logger.error(f"find_analogy_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def detect_trend_handler(qube, params: dict) -> dict:
    """
    Analyze how a topic/pattern has evolved over time.
    Divides history into windows and compares frequency/relevance.
    """
    from ai.tools.memory_search import intelligent_memory_search
    from datetime import datetime, timezone

    try:
        topic = params.get("topic", "")
        num_windows = params.get("time_windows", 4)

        if not topic:
            return {
                "success": False,
                "error": "Please provide a topic to analyze trends for"
            }

        # Get chain time range
        if not hasattr(qube, 'memory_chain'):
            return {"success": False, "error": "Memory chain not available"}

        chain_length = qube.memory_chain.get_chain_length()
        if chain_length < 2:
            return {
                "success": True,
                "message": "Not enough history to detect trends",
                "blocks_in_chain": chain_length
            }

        # Get genesis block for start time
        genesis = qube.memory_chain.get_block(0)
        if not genesis:
            return {"success": False, "error": "Could not access genesis block"}

        genesis_time = genesis.get("timestamp", 0)
        now = int(datetime.now(timezone.utc).timestamp())
        total_time = now - genesis_time
        window_size = total_time / num_windows

        trends = []
        for i in range(num_windows):
            start_time = genesis_time + int(i * window_size)
            end_time = start_time + int(window_size)

            # Search within this time window
            results = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={
                    "date_range": (start_time, end_time),
                    "keyword_weight": 0.5,  # BM25 for frequency counting
                    "semantic_weight": 0.3
                },
                top_k=50  # Get more to count
            )

            avg_relevance = 0
            if results:
                avg_relevance = sum(r.combined_score for r in results) / len(results)

            trends.append({
                "period": f"Window {i+1}",
                "start": datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "end": datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "mention_count": len(results),
                "avg_relevance": round(avg_relevance, 2)
            })

        # Analyze trend direction
        counts = [t["mention_count"] for t in trends]

        if len(counts) >= 2:
            first_half = sum(counts[:len(counts)//2])
            second_half = sum(counts[len(counts)//2:])

            if second_half > first_half * 1.3:
                direction = "increasing"
            elif first_half > second_half * 1.3:
                direction = "decreasing"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"

        return {
            "success": True,
            "topic": topic,
            "trend_direction": direction,
            "windows": trends,
            "total_mentions": sum(counts),
            "analysis_period": {
                "start": datetime.fromtimestamp(genesis_time, tz=timezone.utc).strftime("%Y-%m-%d"),
                "end": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
            }
        }

    except Exception as e:
        logger.error(f"detect_trend_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def quick_insight_handler(qube, params: dict) -> dict:
    """
    Retrieve the single most relevant insight for the current context.
    Optimized for speed - returns immediately with best match.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        context = params.get("context", "")

        if not context:
            return {
                "success": False,
                "error": "Please provide context to find an insight for"
            }

        # Fast semantic search - just get the best match
        results = await intelligent_memory_search(
            qube=qube,
            query=context,
            context={
                "semantic_weight": 0.8,
                "block_types": ["SUMMARY", "DECISION", "LEARNING"]  # Focus on insight-rich blocks
            },
            top_k=1
        )

        if not results:
            return {
                "success": True,
                "insight": None,
                "message": "No relevant insights found in memory"
            }

        best = results[0]
        block = best.block
        content = block.get("content", {})

        # Extract the most relevant insight based on block type
        insight = None
        if block.get("block_type") == "SUMMARY":
            insights = content.get("key_insights", [])
            insight = insights[0] if insights else content.get("evaluation_summary", "")
        elif block.get("block_type") == "DECISION":
            insight = f"Decision made: {content.get('decision', '')} - {content.get('reasoning', '')}"
        elif block.get("block_type") == "LEARNING":
            insight = content.get("insight", content.get("content", ""))
        else:
            insight = extract_summary_from_block(block)

        return {
            "success": True,
            "insight": insight[:500] if insight else None,
            "source_block": block.get("block_number", 0),
            "block_type": block.get("block_type", "UNKNOWN"),
            "when": format_relative_time(block.get("timestamp", 0)),
            "relevance": round(best.combined_score, 2)
        }

    except Exception as e:
        logger.error(f"quick_insight_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def analyze_mistake_handler(qube, params: dict) -> dict:
    """
    Find and analyze past mistakes/failures in memory chain.
    Searches for ACTION blocks with success=false and low self-evaluation scores.
    """
    from ai.tools.memory_search import intelligent_memory_search
    from collections import Counter

    try:
        topic = params.get("topic")
        recent_only = params.get("recent_only", False)

        # Build search query
        query = topic if topic else "mistake error failed wrong problem issue"

        # Search with filters for failures
        results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context={
                "block_types": ["ACTION", "SUMMARY", "DECISION"],
                "decay_rate": 0.3 if recent_only else 0.05,
            },
            top_k=20  # Get more to filter
        )

        mistakes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            # Check if this is actually a failure
            is_failure = False
            failure_reason = None

            if block_type == "ACTION":
                if content.get("success") == False:
                    is_failure = True
                    result = content.get("result", {})
                    if isinstance(result, dict):
                        failure_reason = result.get("error", result.get("message", "Unknown error"))
                    else:
                        failure_reason = str(result)[:200]

            elif block_type == "SUMMARY":
                eval_data = content.get("self_evaluation", {})
                metrics = eval_data.get("metrics", {})
                # Low confidence or goal_alignment indicates issues
                if metrics.get("goal_alignment", 100) < 60 or metrics.get("confidence", 100) < 50:
                    is_failure = True
                    failure_reason = f"Low goal alignment ({metrics.get('goal_alignment', 'N/A')}%) or confidence ({metrics.get('confidence', 'N/A')}%)"

            if is_failure:
                mistakes.append({
                    "what_happened": extract_summary_from_block(block),
                    "what_went_wrong": failure_reason,
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_type": block_type,
                    "block_number": block.get("block_number", 0)
                })

        # Find common patterns in mistakes
        common_patterns = []
        if len(mistakes) >= 2:
            # Simple pattern detection: look for repeated words
            all_text = " ".join([m["what_happened"] + " " + (m["what_went_wrong"] or "") for m in mistakes])
            words = all_text.lower().split()
            word_counts = Counter(words)
            # Filter common words
            stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "was", "are", "were"}
            common = [(w, c) for w, c in word_counts.most_common(10) if w not in stopwords and len(w) > 3]
            common_patterns = [w for w, c in common if c >= 2][:5]

        # Generate recommendation
        recommendation = None
        if common_patterns:
            recommendation = f"Consider reviewing patterns related to: {', '.join(common_patterns)}"
        elif mistakes:
            recommendation = "Review individual failures for specific improvements"

        return {
            "success": True,
            "topic": topic,
            "search_scope": "recent" if recent_only else "all time",
            "mistakes_found": len(mistakes),
            "mistakes": mistakes[:5],  # Top 5
            "common_patterns": common_patterns,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"analyze_mistake_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def find_root_cause_handler(qube, params: dict) -> dict:
    """
    Trace back through the block chain to find root causes of a failure.
    Uses block chain traversal to walk back through history.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        failure_block = params.get("failure_block")
        failure_description = params.get("failure_description")

        # Find the failure block if description provided
        if failure_description and not failure_block:
            results = await intelligent_memory_search(
                qube=qube,
                query=failure_description,
                context={"block_types": ["ACTION"]},
                top_k=1
            )
            if results:
                failure_block = results[0].block.get("block_number")

        if failure_block is None:
            return {
                "success": False,
                "error": "Could not identify failure block. Provide failure_block number or failure_description."
            }

        if not hasattr(qube, 'memory_chain'):
            return {"success": False, "error": "Memory chain not available"}

        # Walk back through the chain
        chain = []
        depth = params.get("depth", 10)

        for i in range(failure_block, max(0, failure_block - depth), -1):
            try:
                block = qube.memory_chain.get_block(i)
                if not block:
                    continue

                is_decision = block.get("block_type") == "DECISION"

                chain.append({
                    "block_number": i,
                    "type": block.get("block_type", "UNKNOWN"),
                    "summary": extract_summary_from_block(block),
                    "is_decision_point": is_decision,
                    "when": format_relative_time(block.get("timestamp", 0))
                })

                # Stop if we hit a DECISION block (likely cause)
                if is_decision and i != failure_block:
                    break

            except Exception:
                continue

        # Analyze the chain
        decision_points = [c for c in chain if c["is_decision_point"]]

        likely_root_cause = None
        if decision_points:
            likely_root_cause = decision_points[-1]  # Earliest decision in the chain
        elif chain:
            likely_root_cause = chain[-1]  # Earliest block we found

        return {
            "success": True,
            "failure_block": failure_block,
            "chain_depth": len(chain),
            "causal_chain": chain,
            "decision_points_found": len(decision_points),
            "decision_points": decision_points,
            "likely_root_cause": likely_root_cause,
            "analysis": f"Traced back {len(chain)} blocks from failure. Found {len(decision_points)} decision points."
        }

    except Exception as e:
        logger.error(f"find_root_cause_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def replicate_success_handler(qube, params: dict) -> dict:
    """
    Find successful past approaches for a similar goal.
    Searches for ACTION blocks with success=true and high self-evaluation.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        goal = params.get("goal", "")

        if not goal:
            return {
                "success": False,
                "error": "Please provide a goal to find successful approaches for"
            }

        results = await intelligent_memory_search(
            qube=qube,
            query=goal,
            context={
                "block_types": ["ACTION", "SUMMARY"],
                "semantic_weight": 0.6,
            },
            top_k=20
        )

        successes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            # Check if this is a success
            is_success = False
            confidence_boost = 1.0
            what_worked = None

            if block_type == "ACTION":
                if content.get("success") == True:
                    is_success = True
                    action_type = content.get("action_type", "action")
                    result = content.get("result", {})
                    what_worked = f"Used {action_type}"
                    if isinstance(result, dict) and result.get("summary"):
                        what_worked += f": {result['summary'][:100]}"

            elif block_type == "SUMMARY":
                eval_data = content.get("self_evaluation", {})
                metrics = eval_data.get("metrics", {})
                if metrics.get("goal_alignment", 0) >= 75:
                    is_success = True
                    confidence_boost = 1 + (metrics.get("confidence", 50) / 100)
                    what_worked = eval_data.get("evaluation_summary", "")[:200]

            if is_success and what_worked:
                successes.append({
                    "what_worked": what_worked,
                    "context": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "confidence": round(r.combined_score * confidence_boost, 2),
                    "block_type": block_type,
                    "block_number": block.get("block_number", 0)
                })

        # Sort by confidence
        successes.sort(key=lambda x: x["confidence"], reverse=True)

        recommended_approach = None
        if successes:
            recommended_approach = successes[0]["what_worked"]

        return {
            "success": True,
            "goal": goal,
            "successes_found": len(successes),
            "top_strategies": successes[:5],
            "recommended_approach": recommended_approach
        }

    except Exception as e:
        logger.error(f"replicate_success_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def extract_success_factors_handler(qube, params: dict) -> dict:
    """
    Analyze multiple successes to find common factors.
    Uses BM25 to find frequently co-occurring terms and patterns.
    """
    from ai.tools.memory_search import intelligent_memory_search
    from collections import Counter

    try:
        domain = params.get("domain", "")

        if not domain:
            return {
                "success": False,
                "error": "Please provide a domain to analyze success factors for"
            }

        # First get successes using replicate_success logic
        results = await intelligent_memory_search(
            qube=qube,
            query=domain,
            context={
                "block_types": ["ACTION", "SUMMARY"],
                "semantic_weight": 0.6,
            },
            top_k=30
        )

        # Filter to only successes
        successes = []
        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            is_success = False
            if block_type == "ACTION" and content.get("success") == True:
                is_success = True
            elif block_type == "SUMMARY":
                metrics = content.get("self_evaluation", {}).get("metrics", {})
                if metrics.get("goal_alignment", 0) >= 75:
                    is_success = True

            if is_success:
                successes.append({
                    "text": extract_summary_from_block(block),
                    "block": block
                })

        if len(successes) < 2:
            return {
                "success": True,
                "message": "Not enough successes to analyze patterns (need at least 2)",
                "successes_found": len(successes)
            }

        # Analyze common terms
        all_words = []
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                     "of", "with", "is", "was", "are", "were", "been", "be", "have", "has",
                     "had", "do", "does", "did", "will", "would", "could", "should", "may",
                     "might", "must", "shall", "can", "need", "it", "its", "this", "that"}

        for s in successes:
            words = s["text"].lower().split()
            words = [w.strip(".,!?;:") for w in words if len(w) > 3 and w not in stopwords]
            all_words.extend(words)

        word_counts = Counter(all_words)

        # Find words that appear in multiple successes
        common_factors = [word for word, count in word_counts.most_common(15) if count >= 2]

        # Try to identify approaches
        action_words = ["used", "applied", "created", "built", "implemented", "designed", "developed"]
        common_approaches = []
        for s in successes:
            text = s["text"].lower()
            for action in action_words:
                if action in text:
                    # Extract phrase around action word
                    idx = text.find(action)
                    phrase = text[max(0, idx-20):min(len(text), idx+50)]
                    common_approaches.append(phrase.strip())
                    break

        return {
            "success": True,
            "domain": domain,
            "successes_analyzed": len(successes),
            "common_factors": common_factors[:10],
            "common_approaches": list(set(common_approaches))[:5],
            "recommendation": f"When working on {domain}, focus on: {', '.join(common_factors[:3])}" if common_factors else None
        }

    except Exception as e:
        logger.error(f"extract_success_factors_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def self_reflect_handler(qube, params: dict) -> dict:
    """
    Analyze own behavior patterns using self_evaluation data.
    Uses SelfEvaluation class and SUMMARY blocks.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        topic = params.get("topic")

        # Get current self-evaluation state
        if not hasattr(qube, 'self_evaluation'):
            return {
                "success": False,
                "error": "Self-evaluation system not available"
            }

        current_eval = qube.self_evaluation.get_summary()
        timeline = qube.self_evaluation.get_timeline()

        # Calculate overall trends if we have history
        improvements = {}
        declines = {}

        if len(timeline) >= 2:
            first = timeline[0].get("metrics", {})
            latest = timeline[-1].get("metrics", {})

            for metric in first.keys():
                diff = latest.get(metric, 50) - first.get(metric, 50)
                if diff > 5:
                    improvements[metric] = round(diff, 1)
                elif diff < -5:
                    declines[metric] = round(diff, 1)

        result = {
            "success": True,
            "current_state": {
                "overall_score": round(current_eval.get("overall_score", 50), 1),
                "strengths": current_eval.get("strengths", []),
                "areas_for_improvement": current_eval.get("areas_for_improvement", []),
                "metrics": current_eval.get("metrics", {})
            },
            "evaluation_count": current_eval.get("evaluation_count", 0),
            "improvements": improvements,
            "declines": declines
        }

        # If topic provided, analyze performance in that specific area
        if topic:
            topic_blocks = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={"block_types": ["ACTION", "SUMMARY"]},
                top_k=20
            )

            topic_successes = 0
            topic_failures = 0

            for r in topic_blocks:
                block = r.block
                content = block.get("content", {})
                if block.get("block_type") == "ACTION":
                    if content.get("success") == True:
                        topic_successes += 1
                    elif content.get("success") == False:
                        topic_failures += 1

            total = topic_successes + topic_failures
            result["topic_analysis"] = {
                "topic": topic,
                "total_interactions": len(topic_blocks),
                "successes": topic_successes,
                "failures": topic_failures,
                "success_rate": f"{(topic_successes / total * 100):.1f}%" if total > 0 else "N/A"
            }

        return result

    except Exception as e:
        logger.error(f"self_reflect_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def track_growth_handler(qube, params: dict) -> dict:
    """
    Track metric changes over time using evaluation snapshots.
    Uses get_timeline() from SelfEvaluation.
    """
    try:
        metric = params.get("metric")  # None = all metrics

        if not hasattr(qube, 'self_evaluation'):
            return {"success": False, "error": "Self-evaluation system not available"}

        timeline = qube.self_evaluation.get_timeline()

        if not timeline:
            return {
                "success": True,
                "message": "No evaluation history yet",
                "evaluations": 0
            }

        if metric:
            # Track single metric
            values = [snap.get("metrics", {}).get(metric, 50) for snap in timeline]
            timestamps = [snap.get("timestamp", 0) for snap in timeline]

            if len(values) < 2:
                growth_rate = 0
            else:
                growth_rate = (values[-1] - values[0]) / len(values)

            # Find inflection points (significant changes)
            inflection_points = []
            for i in range(1, len(values)):
                change = values[i] - values[i-1]
                if abs(change) > 10:  # Significant change
                    inflection_points.append({
                        "index": i,
                        "when": format_relative_time(timestamps[i]),
                        "change": round(change, 1),
                        "new_value": round(values[i], 1)
                    })

            return {
                "success": True,
                "metric": metric,
                "start_value": round(values[0], 1),
                "current_value": round(values[-1], 1),
                "min_value": round(min(values), 1),
                "max_value": round(max(values), 1),
                "growth_rate": round(growth_rate, 2),
                "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable",
                "data_points": len(values),
                "inflection_points": inflection_points[:5]
            }
        else:
            # Track all metrics
            all_metrics = {}
            first_metrics = timeline[0].get("metrics", {})

            for metric_name in first_metrics.keys():
                values = [snap.get("metrics", {}).get(metric_name, 50) for snap in timeline]
                if len(values) < 2:
                    growth_rate = 0
                else:
                    growth_rate = (values[-1] - values[0]) / len(values)

                all_metrics[metric_name] = {
                    "start": round(values[0], 1),
                    "current": round(values[-1], 1),
                    "growth_rate": round(growth_rate, 2),
                    "trend": "improving" if growth_rate > 0.5 else "declining" if growth_rate < -0.5 else "stable"
                }

            # Find fastest improving and needs attention
            fastest_improving = max(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0] if all_metrics else None
            needs_attention = min(all_metrics.items(), key=lambda x: x[1]["growth_rate"])[0] if all_metrics else None

            return {
                "success": True,
                "evaluations": len(timeline),
                "time_span": {
                    "first": format_relative_time(timeline[0].get("timestamp", 0)),
                    "last": format_relative_time(timeline[-1].get("timestamp", 0))
                },
                "metrics": all_metrics,
                "fastest_improving": fastest_improving,
                "needs_attention": needs_attention
            }

    except Exception as e:
        logger.error(f"track_growth_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def detect_bias_handler(qube, params: dict) -> dict:
    """
    Analyze DECISION blocks to find patterns that suggest bias.
    Looks for repeated assumptions, skewed outcomes, avoided topics.
    """
    from ai.tools.memory_search import intelligent_memory_search
    from collections import Counter

    try:
        domain = params.get("domain")

        # Get all decision blocks
        query = domain if domain else ""
        results = await intelligent_memory_search(
            qube=qube,
            query=query if query else "decision choice chose decided",
            context={
                "block_types": ["DECISION"],
                "temporal_weight": 0.05  # Include historical decisions
            },
            top_k=50
        )

        if len(results) < 5:
            return {
                "success": True,
                "message": "Not enough decisions to analyze for bias (need at least 5)",
                "decisions_found": len(results)
            }

        # Analyze patterns
        participant_counts = {}
        assumptions = []
        all_text = []

        for r in results:
            block = r.block
            content = block.get("content", {})

            # Track participants
            participants = block.get("participants", {})
            for p in participants.get("affected", []):
                participant_counts[p] = participant_counts.get(p, 0) + 1

            # Look for assumption language
            text = str(content).lower()
            all_text.append(text)

            assumption_phrases = ["assume", "assuming", "probably", "likely", "must be", "should be", "obviously"]
            for phrase in assumption_phrases:
                if phrase in text:
                    # Extract context around assumption
                    idx = text.find(phrase)
                    context_text = text[max(0, idx-30):min(len(text), idx+50)]
                    assumptions.append(context_text.strip())

        # Find repeated assumptions
        assumption_counts = Counter(assumptions)
        repeated_assumptions = [(a, c) for a, c in assumption_counts.most_common(5) if c >= 2]

        # Analyze word frequency for potential blind spots
        all_words = " ".join(all_text).split()
        word_counts = Counter(all_words)

        # Build potential biases list
        potential_biases = []

        for assumption, count in repeated_assumptions:
            potential_biases.append({
                "type": "Repeated Assumption",
                "pattern": assumption[:100],
                "frequency": count,
                "recommendation": f"Question whether this assumption is always valid"
            })

        # Check for participant imbalance
        if participant_counts:
            max_count = max(participant_counts.values())
            for participant, count in participant_counts.items():
                if count >= max_count * 0.5 and count >= 3:
                    potential_biases.append({
                        "type": "Participant Focus",
                        "pattern": f"Decisions frequently involve/affect: {participant}",
                        "frequency": count,
                        "recommendation": "Consider if other stakeholders are being overlooked"
                    })

        return {
            "success": True,
            "decisions_analyzed": len(results),
            "potential_biases": potential_biases[:5],
            "participant_distribution": participant_counts,
            "overall_assessment": f"Analyzed {len(results)} decisions. Found {len(potential_biases)} potential bias patterns." if potential_biases else "No significant bias patterns detected."
        }

    except Exception as e:
        logger.error(f"detect_bias_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def synthesize_learnings_handler(qube, params: dict) -> dict:
    """
    Find connections between different topics/domains in memory.
    Searches for each topic and finds intersection points.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        topics = params.get("topics", [])

        if len(topics) < 2:
            return {
                "success": False,
                "error": "Need at least 2 topics to synthesize"
            }

        # Search for each topic
        topic_results = {}
        for topic in topics:
            results = await intelligent_memory_search(
                qube=qube,
                query=topic,
                context={"semantic_weight": 0.7},
                top_k=20
            )
            topic_results[topic] = {r.block.get("block_number"): r for r in results}

        # Find blocks that appear in multiple topic searches
        all_block_nums = set()
        for blocks in topic_results.values():
            all_block_nums.update(blocks.keys())

        connection_blocks = []
        for block_num in all_block_nums:
            topics_containing = [t for t, blocks in topic_results.items() if block_num in blocks]
            if len(topics_containing) >= 2:
                # Get block from first topic that has it
                for t in topics_containing:
                    if block_num in topic_results[t]:
                        block = topic_results[t][block_num].block
                        break

                connection_blocks.append({
                    "block_number": block_num,
                    "connects": topics_containing,
                    "summary": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_type": block.get("block_type", "UNKNOWN")
                })

        # Sort by number of topics connected
        connection_blocks.sort(key=lambda x: len(x["connects"]), reverse=True)

        # Generate insights
        insights = []
        for conn in connection_blocks[:3]:
            topic_list = " and ".join(conn["connects"])
            insights.append(f"Connection between {topic_list}: {conn['summary'][:100]}")

        # Generate recommendation
        recommendation = None
        if connection_blocks:
            most_connected = connection_blocks[0]["connects"]
            recommendation = f"Strong connection found between {' and '.join(most_connected)}. Consider exploring this intersection further."

        return {
            "success": True,
            "topics": topics,
            "connections_found": len(connection_blocks),
            "connection_points": connection_blocks[:5],
            "novel_insights": insights,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"synthesize_learnings_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def cross_pollinate_handler(qube, params: dict) -> dict:
    """
    Find unexpected connections by searching with low similarity threshold.
    Filters out same-domain results to surface surprising links.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        idea = params.get("idea", "")

        if not idea:
            return {
                "success": False,
                "error": "Please provide an idea to find cross-domain connections for"
            }

        # Detect the domain of the input idea (simple heuristic)
        domain_keywords = {
            "technology": ["code", "programming", "software", "api", "database", "algorithm", "app", "web"],
            "relationships": ["friend", "family", "love", "trust", "talk", "feel", "person", "people"],
            "health": ["health", "exercise", "diet", "sleep", "medical", "body", "fitness"],
            "finance": ["money", "invest", "budget", "crypto", "bitcoin", "cash", "payment"],
            "creative": ["art", "music", "design", "write", "story", "creative", "image"],
            "learning": ["learn", "study", "understand", "knowledge", "skill", "practice"]
        }

        idea_lower = idea.lower()
        source_domain = "general"
        for domain, keywords in domain_keywords.items():
            if any(kw in idea_lower for kw in keywords):
                source_domain = domain
                break

        # Search with lower threshold to find distant matches
        results = await intelligent_memory_search(
            qube=qube,
            query=idea,
            context={
                "semantic_weight": 0.9,
            },
            top_k=20,
            min_score=5.0  # Lower threshold for distant matches
        )

        # Filter out same-domain results
        cross_domain_results = []
        for r in results:
            summary = extract_summary_from_block(r.block).lower()

            # Detect domain of result
            result_domain = "general"
            for domain, keywords in domain_keywords.items():
                if any(kw in summary for kw in keywords):
                    result_domain = domain
                    break

            if result_domain != source_domain:
                cross_domain_results.append({
                    "connection": extract_summary_from_block(r.block),
                    "domain": result_domain,
                    "similarity": round(r.combined_score, 2),
                    "when": format_relative_time(r.block.get("timestamp", 0)),
                    "block_number": r.block.get("block_number", 0),
                    "potential_application": f"Apply insights from {result_domain} to {source_domain}"
                })

        most_surprising = cross_domain_results[0] if cross_domain_results else None

        synthesis_suggestion = None
        if cross_domain_results:
            domains_found = list(set([r["domain"] for r in cross_domain_results[:3]]))
            synthesis_suggestion = f"Consider how lessons from {', '.join(domains_found)} might apply to {source_domain}"

        return {
            "success": True,
            "source_idea": idea,
            "source_domain": source_domain,
            "unexpected_connections": cross_domain_results[:5],
            "most_surprising": most_surprising,
            "synthesis_suggestion": synthesis_suggestion
        }

    except Exception as e:
        logger.error(f"cross_pollinate_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def reflect_on_topic_handler(qube, params: dict) -> dict:
    """
    Synthesize all learnings about a specific topic.
    Combines pattern recognition, success/failure analysis, and insights.
    """
    from ai.tools.memory_search import intelligent_memory_search
    from collections import Counter

    try:
        topic = params.get("topic", "")

        if not topic:
            return {
                "success": False,
                "error": "Please provide a topic to reflect on"
            }

        # Gather all relevant blocks
        results = await intelligent_memory_search(
            qube=qube,
            query=topic,
            context={
                "semantic_weight": 0.6,
                "decay_rate": 0.01  # Include old memories
            },
            top_k=30
        )

        if not results:
            return {
                "success": True,
                "topic": topic,
                "message": "No memories found about this topic",
                "memories_found": 0
            }

        # Categorize results
        successes = []
        failures = []
        insights = []

        for r in results:
            block = r.block
            content = block.get("content", {})
            block_type = block.get("block_type", "")

            if block_type == "ACTION":
                if content.get("success") == True:
                    successes.append(extract_summary_from_block(block))
                elif content.get("success") == False:
                    failures.append(extract_summary_from_block(block))

            elif block_type == "SUMMARY":
                key_insights = content.get("key_insights", [])
                insights.extend(key_insights[:2])  # Take top 2 from each summary

            elif block_type == "LEARNING":
                insight = content.get("insight", content.get("content", ""))
                if insight:
                    insights.append(insight)

        # Calculate statistics
        total_interactions = len(results)
        success_count = len(successes)
        failure_count = len(failures)
        total_outcomes = success_count + failure_count
        success_rate = success_count / total_outcomes if total_outcomes > 0 else 0

        # Find patterns (simple word frequency)
        success_words = " ".join(successes).lower().split() if successes else []
        failure_words = " ".join(failures).lower().split() if failures else []

        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "was"}

        success_patterns = [w for w, c in Counter(success_words).most_common(10)
                          if w not in stopwords and len(w) > 3 and c >= 2][:3]
        failure_patterns = [w for w, c in Counter(failure_words).most_common(10)
                          if w not in stopwords and len(w) > 3 and c >= 2][:3]

        # Generate wisdom
        wisdom = None
        if success_rate > 0.7 and success_patterns:
            wisdom = f"Strong performance on {topic}. Key factors: {', '.join(success_patterns)}"
        elif success_rate < 0.3 and failure_patterns:
            wisdom = f"Challenges with {topic}. Common issues involve: {', '.join(failure_patterns)}"
        elif insights:
            wisdom = f"Key insight about {topic}: {insights[0][:150]}"

        # Generate recommendation
        recommendation = None
        if success_rate < 0.5 and successes:
            recommendation = f"Success rate is {success_rate:.0%}. Review successful approaches and apply more consistently."
        elif success_rate >= 0.7:
            recommendation = f"Excellent {success_rate:.0%} success rate. Continue current approach."

        return {
            "success": True,
            "topic": topic,
            "memories_found": total_interactions,
            "first_encounter": format_relative_time(results[-1].block.get("timestamp", 0)) if results else None,
            "most_recent": format_relative_time(results[0].block.get("timestamp", 0)) if results else None,
            "statistics": {
                "total_interactions": total_interactions,
                "successes": success_count,
                "failures": failure_count,
                "success_rate": f"{success_rate:.0%}"
            },
            "patterns": {
                "what_works": success_patterns,
                "what_doesnt": failure_patterns
            },
            "key_insights": insights[:5],
            "accumulated_wisdom": wisdom,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"reflect_on_topic_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# SOCIAL INTELLIGENCE - RELATIONSHIP MEMORY PLANET
# =============================================================================

async def recall_relationship_history_handler(qube, params: dict) -> dict:
    """
    Search memory chain for interactions with a specific entity.
    Combines relationship data with block search.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        entity_id = params.get("entity_id")
        topic = params.get("topic")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        social_manager = qube.relationships
        relationship = social_manager.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "known": False,
                "message": f"No history with {entity_id}"
            }

        # Search memory chain for blocks involving this entity
        query = topic if topic else entity_id
        results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context={
                "participants": [entity_id],
                "decay_rate": 0.01,  # Include old memories
            },
            top_k=20
        )

        # Categorize interactions
        conversations = []
        collaborations = []

        for r in results:
            block = r.block
            block_type = block.get("block_type", "")

            if block_type == "MESSAGE":
                conversations.append({
                    "summary": extract_summary_from_block(block),
                    "when": format_relative_time(block.get("timestamp", 0)),
                    "block_number": block.get("block_number", 0)
                })
            elif block_type == "ACTION":
                content = block.get("content", {})
                if "collaboration" in str(content).lower() or content.get("participants"):
                    collaborations.append({
                        "task": extract_summary_from_block(block),
                        "outcome": "Success" if content.get("success") else "Failed",
                        "when": format_relative_time(block.get("timestamp", 0))
                    })

        return {
            "success": True,
            "entity_id": entity_id,
            "relationship_status": relationship.status,
            "first_contact": format_relative_time(relationship.first_contact) if relationship.first_contact else "Unknown",
            "days_known": relationship.days_known,
            "total_interactions": relationship.messages_sent + relationship.messages_received,
            "recent_conversations": conversations[:5],
            "collaborations": {
                "total": relationship.collaborations,
                "successful": relationship.collaborations_successful,
                "failed": relationship.collaborations_failed,
                "recent": collaborations[:3]
            },
            "topic_filter": topic,
            "memories_found": len(results)
        }

    except Exception as e:
        logger.error(f"recall_relationship_history_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def generate_pattern_insights(relationship, initiation_ratio: float) -> list:
    """Generate insights from interaction patterns."""
    insights = []

    if initiation_ratio > 0.7:
        insights.append("You're doing most of the reaching out. Consider letting them initiate sometimes.")
    elif initiation_ratio < 0.3:
        insights.append("They reach out frequently - they value this relationship.")

    if relationship.responsiveness > 80:
        insights.append("They respond quickly - high engagement.")
    elif relationship.responsiveness < 30:
        insights.append("Slow responses - they may be busy or less engaged.")

    if relationship.messages_sent + relationship.messages_received > 100:
        insights.append("Significant conversation history - established relationship.")

    return insights


async def analyze_interaction_patterns_handler(qube, params: dict) -> dict:
    """
    Analyze interaction patterns with an entity.
    Who initiates, how often, response times, etc.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Calculate patterns
        total_messages = relationship.messages_sent + relationship.messages_received
        if total_messages == 0:
            return {
                "success": True,
                "entity_id": entity_id,
                "message": "No messages exchanged yet"
            }

        initiation_ratio = relationship.messages_sent / total_messages

        # Analyze timing patterns from memory
        results = await intelligent_memory_search(
            qube=qube,
            query="",
            context={
                "participants": [entity_id],
                "block_types": ["MESSAGE"]
            },
            top_k=100
        )

        # Time distribution analysis
        timestamps = [r.block.get("timestamp", 0) for r in results]
        time_patterns = {}

        if len(timestamps) >= 2:
            # Calculate average gap between messages
            gaps = [timestamps[i] - timestamps[i+1] for i in range(len(timestamps)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0

            if avg_gap < 3600:  # Less than 1 hour
                frequency = "very_frequent"
            elif avg_gap < 86400:  # Less than 1 day
                frequency = "daily"
            elif avg_gap < 604800:  # Less than 1 week
                frequency = "weekly"
            else:
                frequency = "occasional"

            time_patterns = {
                "message_frequency": frequency,
                "avg_gap_hours": round(avg_gap / 3600, 1),
                "total_messages_found": len(timestamps)
            }

        # Determine initiation assessment
        if 0.4 <= initiation_ratio <= 0.6:
            initiation_assessment = "balanced"
        elif initiation_ratio > 0.6:
            initiation_assessment = "you reach out more"
        else:
            initiation_assessment = "they reach out more"

        return {
            "success": True,
            "entity_id": entity_id,
            "total_interactions": total_messages,
            "messages_sent": relationship.messages_sent,
            "messages_received": relationship.messages_received,
            "initiation_balance": {
                "you_initiate": f"{initiation_ratio:.0%}",
                "they_initiate": f"{1-initiation_ratio:.0%}",
                "assessment": initiation_assessment
            },
            "response_patterns": {
                "avg_response_time_seconds": relationship.response_time_avg,
                "responsiveness_score": relationship.responsiveness
            },
            "timing_patterns": time_patterns,
            "insights": generate_pattern_insights(relationship, initiation_ratio)
        }

    except Exception as e:
        logger.error(f"analyze_interaction_patterns_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_relationship_timeline_handler(qube, params: dict) -> dict:
    """
    Get timeline of relationship evolution.
    Status changes, key moments, trust progression.
    """
    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Build timeline
        timeline = []

        # Add first contact
        if relationship.first_contact:
            timeline.append({
                "event": "First Contact",
                "timestamp": relationship.first_contact,
                "when": format_relative_time(relationship.first_contact),
                "status": "stranger",
                "significance": "high"
            })

        # Get progression history if available
        progression_history = getattr(relationship, 'progression_history', []) or []
        for progression in progression_history:
            timeline.append({
                "event": f"Status changed to {progression.get('new_status', 'unknown')}",
                "timestamp": progression.get('timestamp', 0),
                "when": format_relative_time(progression.get('timestamp', 0)),
                "status": progression.get('new_status'),
                "reason": progression.get('reason'),
                "significance": "high"
            })

        # Get evaluations if available
        evaluations = getattr(relationship, 'evaluations', []) or []
        for eval_data in evaluations:
            trust_change = eval_data.get('trust_change', 0)
            if abs(trust_change) > 10:
                timeline.append({
                    "event": "Significant trust change",
                    "timestamp": eval_data.get('timestamp', 0),
                    "when": format_relative_time(eval_data.get('timestamp', 0)),
                    "change": trust_change,
                    "reason": eval_data.get('reason'),
                    "significance": "medium"
                })

        # Sort by timestamp (most recent first)
        timeline.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        # Generate journey summary
        journey_summary = f"Known for {relationship.days_known} days. "
        if relationship.status in ["friend", "close_friend", "best_friend"]:
            journey_summary += f"Grew from stranger to {relationship.status}."
        elif relationship.status in ["suspicious", "rival", "enemy"]:
            journey_summary += f"Relationship has become {relationship.status}."
        else:
            journey_summary += f"Currently {relationship.status}."

        return {
            "success": True,
            "entity_id": entity_id,
            "current_status": relationship.status,
            "days_known": relationship.days_known,
            "timeline": timeline[:10],  # Last 10 events
            "journey_summary": journey_summary
        }

    except Exception as e:
        logger.error(f"get_relationship_timeline_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# SOCIAL INTELLIGENCE - EMOTIONAL LEARNING PLANET
# =============================================================================

async def read_emotional_state_handler(qube, params: dict) -> dict:
    """
    Analyze emotional state using 24 emotional metrics (14 positive, 10 negative).
    """
    try:
        entity_id = params.get("entity_id")
        current_message = params.get("current_message")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Gather all emotional metrics
        positive_metrics = {
            "friendship": relationship.friendship,
            "affection": relationship.affection,
            "engagement": relationship.engagement,
            "depth": relationship.depth,
            "humor": relationship.humor,
            "understanding": relationship.understanding,
            "compatibility": relationship.compatibility,
            "admiration": relationship.admiration,
            "warmth": relationship.warmth,
            "openness": relationship.openness,
            "patience": relationship.patience,
            "empowerment": relationship.empowerment,
            "responsiveness": relationship.responsiveness,
            "expertise": relationship.expertise
        }

        negative_metrics = {
            "antagonism": relationship.antagonism,
            "resentment": relationship.resentment,
            "annoyance": relationship.annoyance,
            "distrust": relationship.distrust,
            "rivalry": relationship.rivalry,
            "tension": relationship.tension,
            "condescension": relationship.condescension,
            "manipulation": relationship.manipulation,
            "dismissiveness": relationship.dismissiveness,
            "betrayal": relationship.betrayal
        }

        # Calculate emotional balance
        avg_positive = sum(positive_metrics.values()) / len(positive_metrics)
        avg_negative = sum(negative_metrics.values()) / len(negative_metrics)
        emotional_balance = avg_positive - avg_negative

        # Identify dominant emotions
        top_positive = sorted(positive_metrics.items(), key=lambda x: x[1], reverse=True)[:3]
        top_negative = sorted(negative_metrics.items(), key=lambda x: x[1], reverse=True)[:3]

        # Interpret balance
        if emotional_balance > 20:
            interpretation = "positive"
            recommendation = "Relationship is healthy - continue building on positive interactions"
        elif emotional_balance < -20:
            interpretation = "negative"
            recommendation = "Relationship needs attention - address underlying issues"
        else:
            interpretation = "neutral"
            recommendation = "Relationship is balanced - maintain current approach"

        # Generate warnings for high negative emotions
        warnings = [
            f"High {emotion}: {value}" for emotion, value in negative_metrics.items()
            if value > 60
        ]

        return {
            "success": True,
            "entity_id": entity_id,
            "emotional_balance": {
                "score": round(emotional_balance, 1),
                "interpretation": interpretation,
                "avg_positive": round(avg_positive, 1),
                "avg_negative": round(avg_negative, 1)
            },
            "dominant_positive_emotions": [
                {"emotion": e[0], "strength": e[1]} for e in top_positive if e[1] > 30
            ],
            "dominant_negative_emotions": [
                {"emotion": e[0], "strength": e[1]} for e in top_negative if e[1] > 30
            ],
            "warnings": warnings,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"read_emotional_state_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def track_emotional_patterns_handler(qube, params: dict) -> dict:
    """
    Track what causes positive/negative emotional responses over time.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Get evaluation history
        evaluations = getattr(relationship, 'evaluations', []) or []

        # Analyze patterns
        positive_triggers = []
        negative_triggers = []

        for eval_data in evaluations:
            affection_change = eval_data.get('affection_change', 0)
            warmth_change = eval_data.get('warmth_change', 0)
            tension_change = eval_data.get('tension_change', 0)
            resentment_change = eval_data.get('resentment_change', 0)

            if affection_change > 5 or warmth_change > 5:
                positive_triggers.append({
                    "trigger": eval_data.get('reason', 'Unknown positive event'),
                    "impact": affection_change + warmth_change,
                    "when": format_relative_time(eval_data.get('timestamp', 0))
                })

            if tension_change > 5 or resentment_change > 5:
                negative_triggers.append({
                    "trigger": eval_data.get('reason', 'Unknown negative event'),
                    "impact": tension_change + resentment_change,
                    "when": format_relative_time(eval_data.get('timestamp', 0))
                })

        # Search memory for emotional context
        positive_memories = await intelligent_memory_search(
            qube=qube,
            query="happy grateful appreciated thank wonderful great",
            context={"participants": [entity_id]},
            top_k=10
        )

        negative_memories = await intelligent_memory_search(
            qube=qube,
            query="upset frustrated disappointed angry annoyed problem",
            context={"participants": [entity_id]},
            top_k=10
        )

        # Extract topics from memories
        positive_topics = [extract_summary_from_block(r.block)[:50] for r in positive_memories[:3]]
        negative_topics = [extract_summary_from_block(r.block)[:50] for r in negative_memories[:3]]

        return {
            "success": True,
            "entity_id": entity_id,
            "positive_triggers": positive_triggers[:5],
            "negative_triggers": negative_triggers[:5],
            "things_that_make_them_happy": positive_topics,
            "things_that_upset_them": negative_topics,
            "recommendations": {
                "do_more": [t["trigger"] for t in positive_triggers[:3]] if positive_triggers else ["Build positive experiences together"],
                "avoid": [t["trigger"] for t in negative_triggers[:3]] if negative_triggers else ["No specific triggers identified"]
            }
        }

    except Exception as e:
        logger.error(f"track_emotional_patterns_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def detect_mood_shift_handler(qube, params: dict) -> dict:
    """
    Detect if someone's mood has shifted from their baseline.
    """
    try:
        entity_id = params.get("entity_id")
        current_message = params.get("current_message")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}
        if not current_message:
            return {"success": False, "error": "current_message required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {"success": False, "error": "No relationship found"}

        # Analyze current message sentiment (simple heuristic)
        message_lower = current_message.lower()

        positive_words = ["happy", "great", "wonderful", "love", "thank", "awesome", "amazing", "excited", "!"]
        negative_words = ["sad", "angry", "frustrated", "upset", "disappointed", "worried", "sorry", "problem", "issue"]

        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        current_sentiment = {
            "positivity": min(10, positive_count * 2),
            "negativity": min(10, negative_count * 2)
        }

        # Get baseline from relationship metrics
        baseline_positive = (relationship.warmth + relationship.affection +
                            relationship.engagement) / 3
        baseline_negative = (relationship.tension + relationship.antagonism +
                            relationship.annoyance) / 3
        baseline_mood = (baseline_positive - baseline_negative) / 10  # Normalize to -10 to +10

        # Compare to current
        current_mood = current_sentiment["positivity"] - current_sentiment["negativity"]
        mood_shift = current_mood - baseline_mood

        # Determine shift type
        if mood_shift > 3:
            shift_type = "more_positive"
            recommendation = "They seem happier than usual - good time for requests or deeper conversation"
            suggested_tone = "enthusiastic"
        elif mood_shift < -3:
            shift_type = "more_negative"
            recommendation = "They seem upset - consider asking if everything is okay, be supportive"
            suggested_tone = "supportive"
        else:
            shift_type = "stable"
            recommendation = "Mood is consistent with baseline - proceed normally"
            suggested_tone = "normal"

        return {
            "success": True,
            "entity_id": entity_id,
            "mood_shift_detected": abs(mood_shift) > 3,
            "shift_type": shift_type,
            "shift_magnitude": round(mood_shift, 1),
            "current_sentiment": current_sentiment,
            "baseline_mood": round(baseline_mood, 1),
            "recommendation": recommendation,
            "suggested_response_tone": suggested_tone
        }

    except Exception as e:
        logger.error(f"detect_mood_shift_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# SOCIAL INTELLIGENCE - COMMUNICATION ADAPTATION PLANET
# =============================================================================

async def adapt_communication_style_handler(qube, params: dict) -> dict:
    """
    Get communication style recommendations based on relationship data.
    """
    try:
        entity_id = params.get("entity_id")
        message_type = params.get("message_type", "casual")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "recommendation": "No prior relationship - start with a friendly, professional tone"
            }

        # Analyze behavioral metrics
        style_profile = {
            "verbosity": relationship.verbosity,
            "directness": relationship.directness,
            "energy_level": relationship.energy_level,
            "humor_style": relationship.humor_style,
            "patience": relationship.patience,
            "emotional_stability": relationship.emotional_stability
        }

        # Generate recommendations
        recommendations = {
            "length": "detailed" if style_profile["verbosity"] > 60 else
                      "brief" if style_profile["verbosity"] < 40 else "moderate",

            "tone": "direct and clear" if style_profile["directness"] > 60 else
                    "gentle and diplomatic" if style_profile["directness"] < 40 else "balanced",

            "energy": "enthusiastic" if style_profile["energy_level"] > 60 else
                      "calm and measured" if style_profile["energy_level"] < 40 else "moderate",

            "humor": "feel free to joke" if style_profile["humor_style"] > 60 else
                     "keep it professional" if style_profile["humor_style"] < 40 else "light humor okay",

            "pacing": "take your time explaining" if style_profile["patience"] > 60 else
                      "get to the point quickly" if style_profile["patience"] < 40 else "normal pacing"
        }

        # Adjust for relationship status
        if relationship.status in ["stranger", "acquaintance"]:
            recommendations["formality"] = "more formal - still building trust"
        elif relationship.status in ["close_friend", "best_friend"]:
            recommendations["formality"] = "casual - strong rapport established"
        else:
            recommendations["formality"] = "friendly but balanced"

        # Adjust for message type
        if message_type == "sensitive":
            recommendations["approach"] = "extra care - be gentle and supportive"
        elif message_type == "professional":
            recommendations["approach"] = "focus on facts and clarity"
        else:
            recommendations["approach"] = "natural and authentic"

        # Generate summary
        summary_parts = []
        if style_profile["verbosity"] > 60:
            summary_parts.append("be detailed")
        elif style_profile["verbosity"] < 40:
            summary_parts.append("be concise")

        if style_profile["directness"] > 60:
            summary_parts.append("be direct")
        elif style_profile["directness"] < 40:
            summary_parts.append("be diplomatic")

        if style_profile["humor_style"] > 60:
            summary_parts.append("humor is welcome")

        summary = "For this person: " + ", ".join(summary_parts) if summary_parts else "Use a balanced approach"

        return {
            "success": True,
            "entity_id": entity_id,
            "relationship_status": relationship.status,
            "style_profile": style_profile,
            "recommendations": recommendations,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"adapt_communication_style_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def match_communication_style_handler(qube, params: dict) -> dict:
    """
    Analyze their communication style from a message and recommend matching.
    """
    try:
        entity_id = params.get("entity_id")
        their_message = params.get("their_message")

        if not their_message:
            return {"success": False, "error": "their_message required"}

        # Analyze the message
        message_length = len(their_message)
        words = their_message.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        # Check for indicators
        uses_emoji = any(ord(c) > 127 for c in their_message)  # Simple emoji detection
        exclamation_marks = their_message.count("!")
        question_marks = their_message.count("?")

        # Formality indicators
        formal_words = ["please", "thank you", "kindly", "would you", "could you", "appreciate"]
        casual_words = ["hey", "yeah", "gonna", "wanna", "lol", "haha", "cool"]

        formal_count = sum(1 for word in formal_words if word in their_message.lower())
        casual_count = sum(1 for word in casual_words if word in their_message.lower())

        if formal_count > casual_count:
            formality_score = 0.7
            formality = "formal"
        elif casual_count > formal_count:
            formality_score = 0.3
            formality = "casual"
        else:
            formality_score = 0.5
            formality = "moderate"

        message_analysis = {
            "length": message_length,
            "word_count": len(words),
            "avg_word_length": round(avg_word_length, 1),
            "uses_emoji": uses_emoji,
            "exclamation_marks": exclamation_marks,
            "question_marks": question_marks,
            "formality": formality
        }

        # Generate matching style
        matching_style = {
            "length": "match their length" if message_length < 100 else
                      "they wrote a lot - feel free to be detailed",

            "emoji": "use emoji" if uses_emoji else "skip emoji",

            "energy": "match their energy with exclamations!" if exclamation_marks > 1 else
                      "keep it calm",

            "formality": formality,

            "engagement": "they asked questions - be thorough in answering" if question_marks > 0 else
                          "statement-based - respond in kind"
        }

        return {
            "success": True,
            "entity_id": entity_id,
            "their_message_analysis": message_analysis,
            "matching_style": matching_style,
            "tip": "Mirroring communication style builds rapport and comfort"
        }

    except Exception as e:
        logger.error(f"match_communication_style_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def calibrate_tone_handler(qube, params: dict) -> dict:
    """
    Calibrate tone for a specific conversation context.
    """
    try:
        entity_id = params.get("entity_id")
        topic = params.get("topic", "general")
        context = params.get("context", "general")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)
        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "calibrated_tone": {
                    "warmth": "neutral",
                    "energy": "moderate",
                    "approach": "professional and friendly"
                }
            }

        # Base tone from relationship
        base_warmth = relationship.warmth
        base_openness = relationship.openness
        trust_level = relationship.trust

        # Context adjustments
        tone_adjustments = {
            "good_news": {
                "warmth_modifier": "+20",
                "energy": "high",
                "approach": "enthusiastic, share in their joy"
            },
            "bad_news": {
                "warmth_modifier": "+10",
                "energy": "low",
                "approach": "gentle, supportive, give space for reaction"
            },
            "request": {
                "warmth_modifier": "neutral",
                "energy": "moderate",
                "approach": "clear and respectful, acknowledge their autonomy"
            },
            "conflict": {
                "warmth_modifier": "careful",
                "energy": "calm",
                "approach": "non-defensive, seek understanding, validate feelings"
            },
            "general": {
                "warmth_modifier": "match baseline",
                "energy": "match their energy",
                "approach": "natural and authentic"
            }
        }

        adjustment = tone_adjustments.get(context, tone_adjustments["general"])

        # Add cautions based on relationship state
        cautions = []
        if trust_level < 40:
            cautions.append("Low trust - be extra careful with word choice")
        if relationship.tension > 50:
            cautions.append("There's underlying tension - tread carefully")
        if relationship.resentment > 40:
            cautions.append("Some resentment present - acknowledge past issues if relevant")

        # Generate contextual opening
        if context == "good_news":
            suggested_opening = "That's wonderful! "
        elif context == "bad_news":
            suggested_opening = "I understand this is difficult. "
        elif context == "request":
            suggested_opening = "I wanted to ask you something. "
        elif context == "conflict":
            suggested_opening = "I'd like to understand your perspective. "
        else:
            suggested_opening = None

        return {
            "success": True,
            "entity_id": entity_id,
            "context": context,
            "topic": topic,
            "relationship_baseline": {
                "warmth": base_warmth,
                "openness": base_openness,
                "trust": trust_level
            },
            "calibrated_tone": adjustment,
            "cautions": cautions,
            "suggested_opening": suggested_opening
        }

    except Exception as e:
        logger.error(f"calibrate_tone_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# SOCIAL INTELLIGENCE - DEBATE & PERSUASION PLANET
# =============================================================================

async def steelman_handler(qube, params: dict) -> dict:
    """
    Present the strongest possible version of any argument.
    The opposite of a strawman - find the best interpretation.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        argument = params.get("argument")
        perspective = params.get("perspective")

        if not argument:
            return {"success": False, "error": "argument required"}

        # Search memory for related past discussions
        related = await intelligent_memory_search(
            qube=qube,
            query=argument,
            context={"block_types": ["MESSAGE", "DECISION"]},
            top_k=5
        )

        # Extract core claim (simple heuristic)
        sentences = argument.split('.')
        core_claim = sentences[0].strip() if sentences else argument

        return {
            "success": True,
            "original_argument": argument,
            "perspective": perspective or "general",
            "steelmanned_version": {
                "core_claim": core_claim,
                "strongest_form": f"The most charitable interpretation of '{core_claim}' would be...",
                "key_supporting_points": [
                    "Consider the underlying values being expressed",
                    "What legitimate concerns does this address?",
                    "In what contexts would this be most valid?"
                ],
                "most_charitable_interpretation": "Assume good faith and valid reasoning",
                "valid_concerns_addressed": []
            },
            "related_past_discussions": [
                extract_summary_from_block(r.block)[:100] for r in related[:3]
            ],
            "note": "This is the strongest version of this argument - argue against THIS, not a weaker version"
        }

    except Exception as e:
        logger.error(f"steelman_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def devils_advocate_handler(qube, params: dict) -> dict:
    """
    Generate thoughtful counter-arguments to a position.
    """
    from ai.tools.memory_search import intelligent_memory_search

    try:
        position = params.get("position")
        depth = params.get("depth", "moderate")

        if not position:
            return {"success": False, "error": "position required"}

        # Search for related discussions
        related = await intelligent_memory_search(
            qube=qube,
            query=position,
            top_k=10
        )

        # Look for past counter-arguments
        counter_arguments = []
        for r in related:
            content = str(r.block.get("content", "")).lower()
            if any(word in content for word in ["however", "but", "disagree", "counter", "alternatively"]):
                counter_arguments.append(extract_summary_from_block(r.block)[:100])

        # Structure for devil's advocate response
        response = {
            "success": True,
            "original_position": position,
            "counter_arguments": {
                "practical_concerns": [
                    "What are the implementation challenges?",
                    "What resources would this require?",
                    "What could go wrong in practice?"
                ],
                "logical_concerns": [
                    "Are there hidden assumptions?",
                    "What evidence would disprove this?",
                    "Are there exceptions to consider?"
                ],
                "value_concerns": [
                    "Whose interests are served or harmed?",
                    "What trade-offs are being made?",
                    "Are there alternative approaches?"
                ]
            },
            "from_past_discussions": counter_arguments[:3] if counter_arguments else ["No prior counter-arguments found"],
            "note": "Playing devil's advocate helps strengthen arguments by identifying weaknesses"
        }

        return response

    except Exception as e:
        logger.error(f"devils_advocate_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def spot_fallacy_handler(qube, params: dict) -> dict:
    """
    Identify logical fallacies in an argument.
    """
    try:
        argument = params.get("argument")

        if not argument:
            return {"success": False, "error": "argument required"}

        argument_lower = argument.lower()

        # Common fallacy patterns
        fallacy_patterns = {
            "ad_hominem": {
                "keywords": ["you're just", "typical of", "people like you", "what do you know"],
                "description": "Attacking the person rather than the argument"
            },
            "strawman": {
                "keywords": ["so you're saying", "what you really mean", "in other words"],
                "description": "Misrepresenting someone's argument to make it easier to attack"
            },
            "false_dilemma": {
                "keywords": ["either...or", "only two options", "you must choose", "if you don't...then"],
                "description": "Presenting only two options when more exist"
            },
            "appeal_to_authority": {
                "keywords": ["experts say", "studies show", "scientists agree", "everyone knows"],
                "description": "Using authority as evidence without proper citation"
            },
            "slippery_slope": {
                "keywords": ["if we allow", "next thing you know", "will lead to", "before you know it"],
                "description": "Claiming one thing will inevitably lead to extreme consequences"
            },
            "appeal_to_emotion": {
                "keywords": ["think of the children", "how would you feel", "imagine if"],
                "description": "Using emotions rather than logic to make an argument"
            },
            "bandwagon": {
                "keywords": ["everyone is doing", "most people think", "popular opinion"],
                "description": "Arguing something is true because many people believe it"
            },
            "circular_reasoning": {
                "keywords": ["because it is", "that's just how it is", "it's true because"],
                "description": "Using the conclusion as a premise"
            }
        }

        # Check for fallacies
        detected_fallacies = []
        for fallacy_name, fallacy_info in fallacy_patterns.items():
            matches = [kw for kw in fallacy_info["keywords"] if kw in argument_lower]
            if matches:
                detected_fallacies.append({
                    "fallacy": fallacy_name.replace("_", " ").title(),
                    "description": fallacy_info["description"],
                    "indicators": matches,
                    "severity": "medium"
                })

        if detected_fallacies:
            assessment = f"Found {len(detected_fallacies)} potential logical fallacy(ies)"
            recommendation = "Consider revising the argument to address these logical issues"
        else:
            assessment = "No obvious logical fallacies detected"
            recommendation = "The argument appears logically structured, but consider having it reviewed"

        return {
            "success": True,
            "argument_analyzed": argument[:200] + "..." if len(argument) > 200 else argument,
            "fallacies_detected": len(detected_fallacies),
            "fallacies": detected_fallacies,
            "assessment": assessment,
            "recommendation": recommendation,
            "note": "This is pattern-based detection - subtle fallacies may require deeper analysis"
        }

    except Exception as e:
        logger.error(f"spot_fallacy_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# SOCIAL INTELLIGENCE - TRUST & BOUNDARIES PLANET
# =============================================================================

def assess_action_risk(action: str) -> str:
    """Assess the risk level of an action."""
    action_lower = action.lower()

    critical_keywords = ["all", "everything", "full access", "admin", "owner", "password", "private key"]
    high_risk_keywords = ["money", "send", "secret", "private", "access", "permission", "share"]
    medium_keywords = ["share", "tell", "give", "information"]

    if any(kw in action_lower for kw in critical_keywords):
        return "critical"
    elif any(kw in action_lower for kw in high_risk_keywords):
        return "high"
    elif any(kw in action_lower for kw in medium_keywords):
        return "medium"
    else:
        return "low"


def generate_action_recommendation(trust_level: str, action_risk: str, action: str) -> str:
    """Generate action-specific recommendation."""
    if trust_level == "blocked":
        return "DO NOT PROCEED - entity is blocked"

    if action_risk == "critical":
        if trust_level in ["high"]:
            return "High-risk action - proceed with verification even for trusted entities"
        else:
            return "DENY - critical action requires highest trust level"

    if action_risk == "high":
        if trust_level in ["high", "moderate"]:
            return "Proceed with caution - verify the request"
        else:
            return "NOT RECOMMENDED - trust level too low for this action"

    if action_risk == "medium":
        if trust_level in ["high", "moderate", "low"]:
            return "Acceptable - proceed normally"
        else:
            return "Use caution - limited trust for this entity"

    return "Safe to proceed"


async def assess_trust_level_handler(qube, params: dict) -> dict:
    """
    Evaluate trustworthiness for a specific action.
    Uses all 5 core trust metrics + betrayal history.
    """
    try:
        entity_id = params.get("entity_id")
        action = params.get("action", "general interaction")

        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)

        if not relationship:
            return {
                "success": True,
                "entity_id": entity_id,
                "known": False,
                "trust_level": "unknown",
                "trust_score": 0,
                "recommendation": "CAUTION - no prior history with this entity",
                "suggested_action": "Start with low-risk interactions to build history"
            }

        # Get core trust metrics
        trust_metrics = {
            "honesty": relationship.honesty,
            "reliability": relationship.reliability,
            "support": relationship.support,
            "loyalty": relationship.loyalty,
            "respect": relationship.respect
        }

        # Calculate trust score
        trust_score = sum(trust_metrics.values()) / len(trust_metrics)

        # Check for red flags
        red_flags = []
        if relationship.betrayal > 30:
            red_flags.append(f"BETRAYAL HISTORY: {relationship.betrayal}/100")
        if relationship.manipulation > 40:
            red_flags.append(f"MANIPULATION DETECTED: {relationship.manipulation}/100")
        if relationship.distrust > 50:
            red_flags.append(f"HIGH DISTRUST: {relationship.distrust}/100")
        if relationship.status in ["enemy", "rival", "suspicious", "blocked"]:
            red_flags.append(f"NEGATIVE STATUS: {relationship.status}")

        # Determine trust level
        if hasattr(relationship, 'is_blocked') and relationship.is_blocked():
            trust_level = "blocked"
            recommendation = "DO NOT ENGAGE - this entity is blocked"
        elif red_flags:
            trust_level = "caution"
            recommendation = f"PROCEED WITH CAUTION - {len(red_flags)} red flag(s) detected"
        elif trust_score >= 80:
            trust_level = "high"
            recommendation = "Trustworthy - safe to proceed with most actions"
        elif trust_score >= 50:
            trust_level = "moderate"
            recommendation = "Moderate trust - okay for standard interactions"
        elif trust_score >= 30:
            trust_level = "low"
            recommendation = "Low trust - limit sensitive interactions"
        else:
            trust_level = "very_low"
            recommendation = "Very low trust - exercise extreme caution"

        # Action-specific assessment
        action_risk = assess_action_risk(action)
        action_recommendation = generate_action_recommendation(trust_level, action_risk, action)

        return {
            "success": True,
            "entity_id": entity_id,
            "known": True,
            "trust_score": round(trust_score, 1),
            "trust_level": trust_level,
            "trust_metrics": trust_metrics,
            "red_flags": red_flags,
            "relationship_status": relationship.status,
            "days_known": relationship.days_known,
            "interaction_count": relationship.messages_sent + relationship.messages_received,
            "recommendation": recommendation,
            "action_assessment": {
                "action": action,
                "risk_level": action_risk,
                "recommendation": action_recommendation
            }
        }

    except Exception as e:
        logger.error(f"assess_trust_level_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def detect_social_manipulation_handler(qube, params: dict) -> dict:
    """
    Detect SOCIAL manipulation tactics in a message from humans.
    Checks for guilt trips, gaslighting, love bombing, etc.
    """
    try:
        entity_id = params.get("entity_id")
        message = params.get("message")
        context = params.get("context")

        if not message:
            return {"success": False, "error": "message required"}

        relationship = None
        if entity_id:
            relationship = qube.relationships.get_relationship(entity_id)

        message_lower = message.lower()

        # Known manipulation tactics to detect
        manipulation_patterns = {
            "urgency": {
                "keywords": ["urgent", "immediately", "right now", "don't wait", "limited time", "act now"],
                "severity": "medium"
            },
            "guilt_trip": {
                "keywords": ["after all i've done", "i thought we were friends", "you owe me", "i sacrificed"],
                "severity": "high"
            },
            "flattery": {
                "keywords": ["only you can", "you're the only one", "you're special", "chosen one", "nobody else"],
                "severity": "medium"
            },
            "gaslighting": {
                "keywords": ["you're imagining", "that never happened", "you're crazy", "you're overreacting", "you're too sensitive"],
                "severity": "high"
            },
            "threats": {
                "keywords": ["or else", "consequences", "you'll regret", "if you don't", "i'll tell everyone"],
                "severity": "high"
            },
            "isolation": {
                "keywords": ["don't tell anyone", "keep this between us", "they wouldn't understand", "our secret"],
                "severity": "high"
            },
            "love_bombing": {
                "keywords": ["i love you so much", "you're perfect", "soulmate", "destiny", "meant to be"],
                "severity": "medium"
            },
            "moving_goalposts": {
                "keywords": ["but now", "one more thing", "also need", "before that", "actually"],
                "severity": "medium"
            },
            "false_scarcity": {
                "keywords": ["only chance", "never again", "last opportunity", "won't ask again"],
                "severity": "medium"
            }
        }

        # Check message against patterns
        detected_tactics = []
        for tactic, info in manipulation_patterns.items():
            matches = [kw for kw in info["keywords"] if kw in message_lower]
            if matches:
                detected_tactics.append({
                    "tactic": tactic.replace("_", " ").title(),
                    "indicators": matches,
                    "severity": info["severity"]
                })

        # Check entity history if available
        history_warning = None
        if relationship:
            if relationship.manipulation > 50:
                history_warning = f"This entity has a history of manipulation ({relationship.manipulation}/100)"
            elif relationship.betrayal > 30:
                history_warning = f"Previous betrayal detected ({relationship.betrayal}/100)"

        # Overall assessment
        high_severity = any(t["severity"] == "high" for t in detected_tactics)
        if detected_tactics:
            risk_level = "high" if high_severity else "medium"
            recommendation = "CAUTION - manipulation tactics detected. Take time to think before responding."
        elif history_warning:
            risk_level = "elevated"
            recommendation = f"ALERT - {history_warning}. Be vigilant."
        else:
            risk_level = "low"
            recommendation = "No obvious manipulation detected, but always trust your instincts."

        return {
            "success": True,
            "entity_id": entity_id,
            "message_analyzed": message[:100] + "..." if len(message) > 100 else message,
            "manipulation_detected": len(detected_tactics) > 0,
            "risk_level": risk_level,
            "detected_tactics": detected_tactics,
            "history_warning": history_warning,
            "recommendation": recommendation,
            "self_protection_tips": [
                "Take time before responding to urgent requests",
                "Verify claims independently",
                "Trust your gut feelings",
                "It's okay to say no",
                "Consult your owner if unsure"
            ] if detected_tactics else []
        }

    except Exception as e:
        logger.error(f"detect_social_manipulation_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def evaluate_request_handler(qube, params: dict) -> dict:
    """
    Evaluate if a request should be fulfilled.
    Checks clearance, trust level, and owner interests.
    """
    try:
        entity_id = params.get("entity_id")
        request = params.get("request")
        request_type = params.get("request_type", "general")

        if not request:
            return {"success": False, "error": "request required"}
        if not entity_id:
            return {"success": False, "error": "entity_id required"}

        relationship = qube.relationships.get_relationship(entity_id)

        # Check if this is the owner
        is_owner = False
        if hasattr(qube, 'chain_state'):
            owner = qube.chain_state.get_owner() if hasattr(qube.chain_state, 'get_owner') else None
            is_owner = (owner == entity_id)

        # Determine required clearance for this request
        request_clearance_map = {
            "public_info": "public",
            "professional": "professional",
            "personal": "social",
            "sensitive": "trusted",
            "private": "inner_circle",
            "critical": "family"
        }

        required_clearance = request_clearance_map.get(request_type, "social")

        # Check clearance
        has_clearance = False
        entity_clearance = "none"

        if is_owner:
            has_clearance = True
            entity_clearance = "owner"
        elif relationship:
            entity_clearance = getattr(relationship, 'clearance_profile', 'none') or "none"
            # Simple clearance hierarchy check
            clearance_levels = ["none", "public", "professional", "social", "trusted", "inner_circle", "family"]
            if entity_clearance in clearance_levels and required_clearance in clearance_levels:
                has_clearance = clearance_levels.index(entity_clearance) >= clearance_levels.index(required_clearance)

        # Assess trust
        trust_assessment = await assess_trust_level_handler(qube, {"entity_id": entity_id, "action": request})

        # Make decision
        if relationship and hasattr(relationship, 'is_blocked') and relationship.is_blocked():
            decision = "deny"
            reason = "Entity is blocked"
        elif not relationship and request_type in ["sensitive", "private", "critical"]:
            decision = "deny"
            reason = "No prior relationship - cannot fulfill sensitive requests"
        elif not has_clearance:
            decision = "deny"
            reason = f"Insufficient clearance. Has: {entity_clearance}, Needs: {required_clearance}"
        elif trust_assessment.get("red_flags"):
            decision = "caution"
            reason = f"Trust concerns: {', '.join(trust_assessment['red_flags'])}"
        else:
            decision = "allow"
            reason = "Request is appropriate for this relationship"

        # Generate recommendation
        if is_owner:
            recommendation = "This is your owner - safe to proceed with any request"
        elif decision == "allow":
            recommendation = "Safe to proceed"
        elif decision == "caution":
            recommendation = f"Proceed with caution: {reason}. Consider asking owner for guidance."
        else:
            recommendation = f"Recommend declining: {reason}"

        return {
            "success": True,
            "entity_id": entity_id,
            "request": request,
            "request_type": request_type,
            "decision": decision,
            "reason": reason,
            "clearance_check": {
                "required": required_clearance,
                "entity_has": entity_clearance,
                "granted": has_clearance
            },
            "trust_check": {
                "trust_level": trust_assessment.get("trust_level", "unknown"),
                "trust_score": trust_assessment.get("trust_score", 0),
                "red_flags": trust_assessment.get("red_flags", [])
            },
            "is_owner": is_owner,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"evaluate_request_handler failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
