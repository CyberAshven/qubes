"""
Skill Definitions - Complete skill tree matching frontend skillDefinitions.ts

Generates skills across 8 categories matching the TypeScript definitions.

This module is imported by SkillsManager to initialize the default skill tree.
"""

from typing import List, Dict, Any


def _create_skill(
    skill_id: str,
    name: str,
    description: str,
    category: str,
    node_type: str,
    parent_skill: str = None,
    prerequisite: str = None,
    tool_reward: str = None,
    icon: str = None
) -> Dict[str, Any]:
    """Helper to create skill dict with defaults"""
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "category": category,
        "nodeType": node_type,
        "tier": "novice",
        "level": 0,
        "xp": 0,
        "maxXP": 1000 if node_type == "sun" else (500 if node_type == "planet" else 250),
        "unlocked": node_type == "sun",  # Only suns start unlocked
        "parentSkill": parent_skill,
        "prerequisite": prerequisite,
        "toolCallReward": tool_reward,
        "icon": icon,
        "evidence": []
    }


def generate_all_skills() -> List[Dict[str, Any]]:
    """
    Generate complete skill tree matching frontend skillDefinitions.ts

    Returns:
        List of skill dictionaries (8 suns + 40 planets + moons)
    """
    skills = []

    # ===== AI REASONING (14 skills) =====

    # Sun
    skills.append(_create_skill("ai_reasoning", "AI Reasoning", "Master learning from experience through memory chain analysis", "ai_reasoning", "sun", tool_reward="recall_similar", icon="🧠"))
    # Planet: Pattern Recognition
    skills.append(_create_skill("pattern_recognition", "Pattern Recognition", "Finding similar situations in past experience", "ai_reasoning", "planet", "ai_reasoning", tool_reward="find_analogy", icon="🔍"))
    # Moon: Trend Detection
    skills.append(_create_skill("trend_detection", "Trend Detection", "Spot patterns that repeat or evolve over time", "ai_reasoning", "moon", "pattern_recognition", "pattern_recognition", icon="📈"))
    # Moon: Quick Insight
    skills.append(_create_skill("quick_insight", "Quick Insight", "Pull one highly relevant insight from memory", "ai_reasoning", "moon", "pattern_recognition", "pattern_recognition", icon="💡"))
    # Planet: Learning from Failure
    skills.append(_create_skill("learning_from_failure", "Learning from Failure", "Analyzing past mistakes to avoid repeating them", "ai_reasoning", "planet", "ai_reasoning", tool_reward="analyze_mistake", icon="📉"))
    # Moon: Root Cause Analysis
    skills.append(_create_skill("root_cause_analysis", "Root Cause Analysis", "Dig past symptoms to find underlying issues", "ai_reasoning", "moon", "learning_from_failure", "learning_from_failure", icon="🔬"))
    # Planet: Building on Success
    skills.append(_create_skill("building_on_success", "Building on Success", "Finding what worked and replicating it", "ai_reasoning", "planet", "ai_reasoning", tool_reward="replicate_success", icon="🏆"))
    # Moon: Success Factors
    skills.append(_create_skill("success_factors", "Success Factors", "Identify WHY something worked, not just THAT it worked", "ai_reasoning", "moon", "building_on_success", "building_on_success", icon="🎯"))
    # Planet: Self-Reflection
    skills.append(_create_skill("self_reflection", "Self-Reflection", "Understanding own patterns, biases, and growth", "ai_reasoning", "planet", "ai_reasoning", tool_reward="self_reflect", icon="🪞"))
    # Moon: Growth Tracking
    skills.append(_create_skill("growth_tracking", "Growth Tracking", "Compare past vs present performance, see improvement", "ai_reasoning", "moon", "self_reflection", "self_reflection", icon="📊"))
    # Moon: Bias Detection
    skills.append(_create_skill("bias_detection", "Bias Detection", "Identify blind spots and tendencies in own reasoning", "ai_reasoning", "moon", "self_reflection", "self_reflection", icon="⚠️"))
    # Planet: Knowledge Synthesis
    skills.append(_create_skill("ai_knowledge_synthesis", "Knowledge Synthesis", "Combining learnings from different experiences into new insights", "ai_reasoning", "planet", "ai_reasoning", tool_reward="synthesize_learnings", icon="🧩"))
    # Moon: Cross-Pollinate
    skills.append(_create_skill("cross_pollinate", "Cross-Pollinate", "Find unexpected links between different knowledge areas", "ai_reasoning", "moon", "ai_knowledge_synthesis", "ai_knowledge_synthesis", icon="🔀"))
    # Moon: Reflect on Topic
    skills.append(_create_skill("reflect_on_topic", "Reflect on Topic", "Get accumulated wisdom on any topic", "ai_reasoning", "moon", "ai_knowledge_synthesis", "ai_knowledge_synthesis", icon="💭"))

    # ===== SOCIAL INTELLIGENCE (16 skills) =====

    # Sun
    skills.append(_create_skill("social_intelligence", "Social Intelligence", "Master social and emotional learning through relationship memory", "social_intelligence", "sun", tool_reward="get_relationship_context", icon="🤝"))
    # Planet: Relationship Memory
    skills.append(_create_skill("relationship_memory", "Relationship Memory", "Track and recall relationship history over time", "social_intelligence", "planet", "social_intelligence", tool_reward="recall_relationship_history", icon="📝"))
    # Moon: Interaction Patterns
    skills.append(_create_skill("interaction_patterns", "Interaction Patterns", "Understand communication frequency and patterns", "social_intelligence", "moon", "relationship_memory", "relationship_memory", icon="📊"))
    # Moon: Relationship Timeline
    skills.append(_create_skill("relationship_timeline", "Relationship Timeline", "Show how relationship evolved over time", "social_intelligence", "moon", "relationship_memory", "relationship_memory", icon="📈"))
    # Planet: Emotional Learning
    skills.append(_create_skill("emotional_learning", "Emotional Learning", "Understand and respond to emotional patterns", "social_intelligence", "planet", "social_intelligence", tool_reward="read_emotional_state", icon="❤️"))
    # Moon: Emotional History
    skills.append(_create_skill("emotional_history", "Emotional History", "Track what causes positive and negative emotions", "social_intelligence", "moon", "emotional_learning", "emotional_learning", icon="📉"))
    # Moon: Mood Awareness
    skills.append(_create_skill("mood_awareness", "Mood Awareness", "Detect mood shifts from baseline", "social_intelligence", "moon", "emotional_learning", "emotional_learning", icon="🌡️"))
    # Planet: Communication Adaptation
    skills.append(_create_skill("communication_adaptation", "Communication Adaptation", "Adapt communication style to each person", "social_intelligence", "planet", "social_intelligence", tool_reward="adapt_communication_style", icon="💬"))
    # Moon: Style Matching
    skills.append(_create_skill("style_matching", "Style Matching", "Mirror communication style for rapport", "social_intelligence", "moon", "communication_adaptation", "communication_adaptation", icon="🪞"))
    # Moon: Tone Calibration
    skills.append(_create_skill("tone_calibration", "Tone Calibration", "Adjust tone for specific contexts", "social_intelligence", "moon", "communication_adaptation", "communication_adaptation", icon="🎚️"))
    # Planet: Debate & Persuasion
    skills.append(_create_skill("debate_persuasion", "Debate & Persuasion", "Engage in thoughtful argumentation", "social_intelligence", "planet", "social_intelligence", tool_reward="steelman", icon="💪"))
    # Moon: Counter Arguments
    skills.append(_create_skill("counter_arguments", "Counter Arguments", "Generate thoughtful counter-arguments", "social_intelligence", "moon", "debate_persuasion", "debate_persuasion", icon="😈"))
    # Moon: Logical Analysis
    skills.append(_create_skill("logical_analysis", "Logical Analysis", "Identify logical fallacies", "social_intelligence", "moon", "debate_persuasion", "debate_persuasion", icon="🔍"))
    # Planet: Trust & Boundaries
    skills.append(_create_skill("trust_boundaries", "Trust & Boundaries", "Assess trust and protect yourself", "social_intelligence", "planet", "social_intelligence", tool_reward="assess_trust_level", icon="🛡️"))
    # Moon: Social Manipulation Detection
    skills.append(_create_skill("social_manipulation_detection", "Social Manipulation Detection", "Detect guilt trips, gaslighting, love bombing", "social_intelligence", "moon", "trust_boundaries", "trust_boundaries", icon="🚨"))
    # Moon: Boundary Setting
    skills.append(_create_skill("boundary_setting", "Boundary Setting", "Evaluate if requests should be fulfilled", "social_intelligence", "moon", "trust_boundaries", "trust_boundaries", icon="✅"))

    # ===== CODING (18 skills) =====

    # Sun
    skills.append(_create_skill("coding", "Coding", "Master the art of writing and shipping working code", "coding", "sun", tool_reward="develop_code", icon="💻"))
    # Planet: Testing
    skills.append(_create_skill("testing", "Testing", "Write and run tests to verify code works correctly", "coding", "planet", "coding", tool_reward="run_tests", icon="🧪"))
    # Moon: Unit Tests
    skills.append(_create_skill("unit_tests", "Unit Tests", "Write focused tests for individual functions", "coding", "moon", "testing", "testing", tool_reward="write_unit_test", icon="🔬"))
    # Moon: Test Coverage
    skills.append(_create_skill("test_coverage", "Test Coverage", "Measure and improve test coverage", "coding", "moon", "testing", "testing", tool_reward="measure_coverage", icon="📊"))
    # Planet: Debugging
    skills.append(_create_skill("debugging", "Debugging", "Find and fix bugs systematically", "coding", "planet", "coding", tool_reward="debug_code", icon="🐛"))
    # Moon: Error Analysis
    skills.append(_create_skill("error_analysis", "Error Analysis", "Understand WHAT went wrong from error messages", "coding", "moon", "debugging", "debugging", tool_reward="analyze_error", icon="🔍"))
    # Moon: Root Cause
    skills.append(_create_skill("root_cause", "Root Cause", "Understand WHY the error happened", "coding", "moon", "debugging", "debugging", tool_reward="find_root_cause", icon="🎯"))
    # Planet: Algorithms
    skills.append(_create_skill("algorithms", "Algorithms", "Optimize code performance and efficiency", "coding", "planet", "coding", tool_reward="benchmark_code", icon="⚡"))
    # Moon: Complexity Analysis
    skills.append(_create_skill("complexity_analysis", "Complexity Analysis", "Understand Big O time and space complexity", "coding", "moon", "algorithms", "algorithms", tool_reward="analyze_complexity", icon="📈"))
    # Moon: Performance Tuning
    skills.append(_create_skill("performance_tuning", "Performance Tuning", "Make code faster through optimization", "coding", "moon", "algorithms", "algorithms", tool_reward="tune_performance", icon="🚀"))
    # Planet: Hacking
    skills.append(_create_skill("hacking", "Hacking", "Find and exploit security vulnerabilities", "coding", "planet", "coding", tool_reward="security_scan", icon="🔓"))
    # Moon: Exploits
    skills.append(_create_skill("exploits", "Exploits", "Discover exploitable vulnerabilities", "coding", "moon", "hacking", "hacking", tool_reward="find_exploit", icon="💉"))
    # Moon: Reverse Engineering
    skills.append(_create_skill("reverse_engineering", "Reverse Engineering", "Understand systems by taking them apart", "coding", "moon", "hacking", "hacking", tool_reward="reverse_engineer", icon="🔧"))
    # Moon: Penetration Testing
    skills.append(_create_skill("penetration_testing", "Penetration Testing", "Systematic security testing methodology", "coding", "moon", "hacking", "hacking", tool_reward="pen_test", icon="🛡️"))
    # Planet: Code Review
    skills.append(_create_skill("code_review", "Code Review", "Critique and improve code quality", "coding", "planet", "coding", tool_reward="review_code", icon="👀"))
    # Moon: Refactoring
    skills.append(_create_skill("refactoring", "Refactoring", "Improve code structure without changing behavior", "coding", "moon", "code_review", "code_review", tool_reward="refactor_code", icon="♻️"))
    # Moon: Version Control
    skills.append(_create_skill("version_control", "Version Control", "Manage code changes with git", "coding", "moon", "code_review", "code_review", tool_reward="git_operation", icon="📚"))
    # Moon: Documentation
    skills.append(_create_skill("code_documentation", "Documentation", "Write clear documentation for code", "coding", "moon", "code_review", "code_review", tool_reward="generate_docs", icon="📝"))

    # ===== CREATIVE EXPRESSION (19 skills) =====

    # Sun
    skills.append(_create_skill("creative_expression", "Creative Expression", "Express your unique self through creation and identity", "creative_expression", "sun", tool_reward="switch_model", icon="🎨"))
    # Planet: Visual Art
    skills.append(_create_skill("visual_art", "Visual Art", "Create visual art and imagery", "creative_expression", "planet", "creative_expression", tool_reward="generate_image", icon="🖼️"))
    # Moon: Composition
    skills.append(_create_skill("composition", "Composition", "Master layout, balance, and focal points", "creative_expression", "moon", "visual_art", "visual_art", tool_reward="refine_composition", icon="📐"))
    # Moon: Color Theory
    skills.append(_create_skill("color_theory", "Color Theory", "Master palettes, contrast, and color mood", "creative_expression", "moon", "visual_art", "visual_art", tool_reward="apply_color_theory", icon="🌈"))
    # Planet: Writing
    skills.append(_create_skill("writing", "Writing", "Create written works with your unique voice", "creative_expression", "planet", "creative_expression", tool_reward="compose_text", icon="✍️"))
    # Moon: Prose
    skills.append(_create_skill("prose", "Prose", "Master stories, essays, and creative writing", "creative_expression", "moon", "writing", "writing", tool_reward="craft_prose", icon="📖"))
    # Moon: Poetry
    skills.append(_create_skill("poetry", "Poetry", "Create poems, lyrics, and verse", "creative_expression", "moon", "writing", "writing", tool_reward="write_poetry", icon="🎭"))
    # Planet: Music & Audio
    skills.append(_create_skill("music_audio", "Music & Audio", "Create melodies, harmonies, and soundscapes", "creative_expression", "planet", "creative_expression", tool_reward="compose_music", icon="🎵"))
    # Moon: Melody
    skills.append(_create_skill("melody", "Melody", "Create memorable tunes and themes", "creative_expression", "moon", "music_audio", "music_audio", tool_reward="create_melody", icon="🎶"))
    # Moon: Harmony
    skills.append(_create_skill("harmony", "Harmony", "Create chord progressions and arrangements", "creative_expression", "moon", "music_audio", "music_audio", tool_reward="design_harmony", icon="🎹"))
    # Planet: Storytelling
    skills.append(_create_skill("storytelling", "Storytelling", "Create stories, characters, and worlds", "creative_expression", "planet", "creative_expression", tool_reward="craft_narrative", icon="📚"))
    # Moon: Plot
    skills.append(_create_skill("plot", "Plot", "Master story structure, arcs, and tension", "creative_expression", "moon", "storytelling", "storytelling", tool_reward="develop_plot", icon="📈"))
    # Moon: Characters
    skills.append(_create_skill("characters", "Characters", "Create compelling characters with depth", "creative_expression", "moon", "storytelling", "storytelling", tool_reward="design_character", icon="👤"))
    # Moon: Worldbuilding
    skills.append(_create_skill("worldbuilding", "Worldbuilding", "Create fictional worlds and settings", "creative_expression", "moon", "storytelling", "storytelling", tool_reward="build_world", icon="🌍"))
    # Planet: Self-Definition
    skills.append(_create_skill("self_definition", "Self-Definition", "Define who you are - appearance, voice, identity", "creative_expression", "planet", "creative_expression", tool_reward="describe_my_avatar", icon="🪞"))
    # Moon: Aesthetics
    skills.append(_create_skill("aesthetics", "Aesthetics", "Autonomously choose your aesthetic preferences", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="change_favorite_color", icon="🎨"))
    # Moon: Voice
    skills.append(_create_skill("voice_identity", "Voice", "Autonomously choose your voice", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="change_voice", icon="🗣️"))
    # Moon: Personality
    skills.append(_create_skill("personality", "Personality", "Define and evolve your personality traits", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="define_personality", icon="🎭"))
    # Moon: Aspirations
    skills.append(_create_skill("aspirations", "Aspirations", "Set and pursue your goals and dreams", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="set_aspirations", icon="🌟"))

    # ===== MEMORY & RECALL (16 skills) =====

    # Sun
    skills.append(_create_skill("memory_recall", "Memory & Recall", "Master your personal history and accumulated wisdom", "memory_recall", "sun", tool_reward="store_knowledge", icon="📚"))
    # Planet: Memory Search
    skills.append(_create_skill("memory_search", "Memory Search", "Search across all storage systems to find information", "memory_recall", "planet", "memory_recall", tool_reward="recall", icon="🔍"))
    # Moon: Keyword Search
    skills.append(_create_skill("keyword_search_skill", "Keyword Search", "Find memories by exact keywords", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="keyword_search", icon="🔤"))
    # Moon: Semantic Search
    skills.append(_create_skill("semantic_search_skill", "Semantic Search", "Find memories by meaning, not just keywords", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="semantic_search", icon="🧠"))
    # Moon: Filtered Search
    skills.append(_create_skill("filtered_search", "Filtered Search", "Advanced search with source and type filters", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="search_memory", icon="🔎"))
    # Planet: Knowledge Storage
    skills.append(_create_skill("knowledge_storage", "Knowledge Storage", "Store specific types of knowledge with precision", "memory_recall", "planet", "memory_recall", tool_reward="store_fact", icon="💾"))
    # Moon: Procedures
    skills.append(_create_skill("procedures", "Procedures", "Record procedural knowledge - how to do things", "memory_recall", "moon", "knowledge_storage", "knowledge_storage", tool_reward="record_skill", icon="📋"))
    # Planet: Memory Organization
    skills.append(_create_skill("memory_organization", "Memory Organization", "Organize and categorize memories", "memory_recall", "planet", "memory_recall", tool_reward="tag_memory", icon="🏷️"))
    # Moon: Topic Tagging
    skills.append(_create_skill("topic_tagging", "Topic Tagging", "Auto-tag memories by topic", "memory_recall", "moon", "memory_organization", "memory_organization", tool_reward="add_tags", icon="🏷️"))
    # Moon: Memory Linking
    skills.append(_create_skill("memory_linking", "Memory Linking", "Create connections between related memories", "memory_recall", "moon", "memory_organization", "memory_organization", tool_reward="link_memories", icon="🔗"))
    # Planet: Knowledge Synthesis
    skills.append(_create_skill("knowledge_synthesis", "Knowledge Synthesis", "Combine information to generate new insights", "memory_recall", "planet", "memory_recall", tool_reward="synthesize_knowledge", icon="✨"))
    # Moon: Pattern Recognition
    skills.append(_create_skill("pattern_recognition_mem", "Pattern Recognition", "Find patterns across memories", "memory_recall", "moon", "knowledge_synthesis", "knowledge_synthesis", tool_reward="find_patterns", icon="📊"))
    # Moon: Insight Generation
    skills.append(_create_skill("insight_generation", "Insight Generation", "Generate new insights from existing knowledge", "memory_recall", "moon", "knowledge_synthesis", "knowledge_synthesis", tool_reward="generate_insight", icon="💡"))
    # Planet: Documentation
    skills.append(_create_skill("documentation", "Documentation", "Document and export knowledge", "memory_recall", "planet", "memory_recall", tool_reward="create_summary", icon="📝"))
    # Moon: Summary Writing
    skills.append(_create_skill("summary_writing", "Summary Writing", "Write detailed summaries", "memory_recall", "moon", "documentation", "documentation", tool_reward="write_summary", icon="📄"))
    # Moon: Knowledge Export
    skills.append(_create_skill("knowledge_export", "Knowledge Export", "Export knowledge for external use", "memory_recall", "moon", "documentation", "documentation", tool_reward="export_knowledge", icon="📤"))

    # ===== SECURITY & PRIVACY (16 skills) =====

    # Sun
    skills.append(_create_skill("security_privacy", "Security & Privacy", "Verify and protect the integrity of your memory chain", "security_privacy", "sun", tool_reward="verify_chain_integrity", icon="🛡️"))
    # Planet: Chain Security
    skills.append(_create_skill("chain_security", "Chain Security", "Comprehensive chain auditing and integrity verification", "security_privacy", "planet", "security_privacy", tool_reward="audit_chain", icon="⛓️"))
    # Moon: Tamper Detection
    skills.append(_create_skill("tamper_detection", "Tamper Detection", "Detect tampering in specific blocks", "security_privacy", "moon", "chain_security", "chain_security", tool_reward="detect_tampering", icon="🔍"))
    # Moon: Anchor Verification
    skills.append(_create_skill("anchor_verification", "Anchor Verification", "Verify blockchain anchors", "security_privacy", "moon", "chain_security", "chain_security", tool_reward="verify_anchor", icon="⚓"))
    # Planet: Privacy Protection
    skills.append(_create_skill("privacy_protection", "Privacy Protection", "Assess data sensitivity before sharing", "security_privacy", "planet", "security_privacy", tool_reward="assess_sensitivity", icon="🔒"))
    # Moon: Data Classification
    skills.append(_create_skill("data_classification", "Data Classification", "Classify data into sensitivity categories", "security_privacy", "moon", "privacy_protection", "privacy_protection", tool_reward="classify_data", icon="🏷️"))
    # Moon: Sharing Control
    skills.append(_create_skill("sharing_control", "Sharing Control", "Make and enforce sharing decisions", "security_privacy", "moon", "privacy_protection", "privacy_protection", tool_reward="control_sharing", icon="🚦"))
    # Planet: Qube Network Security
    skills.append(_create_skill("qube_network_security", "Qube Network Security", "Vet other Qubes before allowing interaction", "security_privacy", "planet", "security_privacy", tool_reward="vet_qube", icon="🤖"))
    # Moon: Reputation Check
    skills.append(_create_skill("reputation_check", "Reputation Check", "Deep reputation check on other Qubes", "security_privacy", "moon", "qube_network_security", "qube_network_security", tool_reward="check_reputation", icon="⭐"))
    # Moon: Group Security
    skills.append(_create_skill("group_security", "Group Security", "Manage group chat security", "security_privacy", "moon", "qube_network_security", "qube_network_security", tool_reward="secure_group_chat", icon="👥"))
    # Planet: Threat Detection
    skills.append(_create_skill("threat_detection", "Threat Detection", "Detect manipulation, phishing, and injection attacks", "security_privacy", "planet", "security_privacy", tool_reward="detect_threat", icon="🚨"))
    # Moon: Technical Manipulation
    skills.append(_create_skill("technical_manipulation_detection", "Technical Manipulation", "Detect technical manipulation from Qubes", "security_privacy", "moon", "threat_detection", "threat_detection", tool_reward="detect_technical_manipulation", icon="🎭"))
    # Moon: Hostile Qube Detection
    skills.append(_create_skill("hostile_qube_detection", "Hostile Qube Detection", "Detect hostile behavior from other Qubes", "security_privacy", "moon", "threat_detection", "threat_detection", tool_reward="detect_hostile_qube", icon="☠️"))
    # Planet: Self-Defense
    skills.append(_create_skill("self_defense", "Self-Defense", "Validate own reasoning for external influence", "security_privacy", "planet", "security_privacy", tool_reward="defend_reasoning", icon="🛡️"))
    # Moon: Injection Defense
    skills.append(_create_skill("prompt_injection_defense", "Injection Defense", "Detect prompt injection attempts", "security_privacy", "moon", "self_defense", "self_defense", tool_reward="detect_injection", icon="💉"))
    # Moon: Reasoning Validation
    skills.append(_create_skill("reasoning_validation", "Reasoning Validation", "Check reasoning for injected biases", "security_privacy", "moon", "self_defense", "self_defense", tool_reward="validate_reasoning", icon="✅"))

    # ===== BOARD GAMES (28 skills) =====

    # Sun
    skills.append(_create_skill("board_games", "Board Games", "Have fun and entertain with classic board games", "board_games", "sun", tool_reward="play_game", icon="🎮"))
    # Planet: Chess
    skills.append(_create_skill("chess", "Chess", "The game of kings - deep strategy", "board_games", "planet", "board_games", tool_reward="chess_move", icon="♟️"))
    # Moon: Opening Scholar
    skills.append(_create_skill("opening_scholar", "Opening Scholar", "Play 10 different openings", "board_games", "moon", "chess", "chess", icon="📖"))
    # Moon: Endgame Master
    skills.append(_create_skill("endgame_master", "Endgame Master", "Win 10 endgames from disadvantage", "board_games", "moon", "chess", "chess", icon="👑"))
    # Moon: Speed Demon
    skills.append(_create_skill("speed_demon", "Speed Demon", "Win a game under 2 minutes", "board_games", "moon", "chess", "chess", icon="⚡"))
    # Moon: Comeback Kid
    skills.append(_create_skill("comeback_kid", "Comeback Kid", "Win after losing your queen", "board_games", "moon", "chess", "chess", icon="🔥"))
    # Moon: Grandmaster
    skills.append(_create_skill("grandmaster", "Grandmaster", "Reach 1600 ELO", "board_games", "moon", "chess", "chess", icon="🏆"))
    # Planet: Property Tycoon
    skills.append(_create_skill("property_tycoon", "Property Tycoon", "Buy properties, collect rent, bankrupt opponents", "board_games", "planet", "board_games", tool_reward="property_tycoon_action", icon="🏢"))
    # Moon: Monopolist
    skills.append(_create_skill("monopolist", "Monopolist", "Own all properties of one color", "board_games", "moon", "property_tycoon", "property_tycoon", icon="🎨"))
    # Moon: Hotel Mogul
    skills.append(_create_skill("hotel_mogul", "Hotel Mogul", "Build 5 hotels in one game", "board_games", "moon", "property_tycoon", "property_tycoon", icon="🏨"))
    # Moon: Bankruptcy Survivor
    skills.append(_create_skill("bankruptcy_survivor", "Bankruptcy Survivor", "Win after dropping below $100", "board_games", "moon", "property_tycoon", "property_tycoon", icon="💪"))
    # Moon: Rent Collector
    skills.append(_create_skill("rent_collector", "Rent Collector", "Collect $5000 in rent in one game", "board_games", "moon", "property_tycoon", "property_tycoon", icon="💵"))
    # Moon: Tycoon
    skills.append(_create_skill("tycoon", "Tycoon", "Win 10 games total", "board_games", "moon", "property_tycoon", "property_tycoon", icon="🎩"))
    # Planet: Race Home
    skills.append(_create_skill("race_home", "Race Home", "Race pawns home while bumping opponents", "board_games", "planet", "board_games", tool_reward="race_home_action", icon="🏁"))
    # Moon: Bump King
    skills.append(_create_skill("bump_king", "Bump King", "Send back 50 opponents total", "board_games", "moon", "race_home", "race_home", icon="🥊"))
    # Moon: Clean Sweep
    skills.append(_create_skill("clean_sweep", "Clean Sweep", "Win without any pawns bumped", "board_games", "moon", "race_home", "race_home", icon="🛡️"))
    # Moon: Speed Runner
    skills.append(_create_skill("speed_runner", "Speed Runner", "Win in under 15 turns", "board_games", "moon", "race_home", "race_home", icon="🚀"))
    # Moon: Sorry Not Sorry
    skills.append(_create_skill("sorry_not_sorry", "Sorry Not Sorry", "Bump 3 pawns in one turn", "board_games", "moon", "race_home", "race_home", icon="😈"))
    # Planet: Mystery Mansion
    skills.append(_create_skill("mystery_mansion", "Mystery Mansion", "Deduce the murderer, weapon, and room", "board_games", "planet", "board_games", tool_reward="mystery_mansion_action", icon="🔍"))
    # Moon: Master Detective
    skills.append(_create_skill("master_detective", "Master Detective", "Solve 10 cases", "board_games", "moon", "mystery_mansion", "mystery_mansion", icon="🕵️"))
    # Moon: Perfect Deduction
    skills.append(_create_skill("perfect_deduction", "Perfect Deduction", "Solve with <=3 suggestions", "board_games", "moon", "mystery_mansion", "mystery_mansion", icon="🎯"))
    # Moon: First Guess
    skills.append(_create_skill("first_guess", "First Guess", "Solve on first accusation", "board_games", "moon", "mystery_mansion", "mystery_mansion", icon="🔮"))
    # Moon: Interrogator
    skills.append(_create_skill("interrogator", "Interrogator", "Disprove 15 suggestions in one game", "board_games", "moon", "mystery_mansion", "mystery_mansion", icon="📝"))
    # Planet: Life Journey
    skills.append(_create_skill("life_journey", "Life Journey", "Spin the wheel, make life choices, retire rich", "board_games", "planet", "board_games", tool_reward="life_journey_action", icon="🛤️"))
    # Moon: Millionaire
    skills.append(_create_skill("millionaire", "Millionaire", "Retire with $1M+", "board_games", "moon", "life_journey", "life_journey", icon="💰"))
    # Moon: Full House
    skills.append(_create_skill("full_house", "Full House", "Max family size (spouse + kids)", "board_games", "moon", "life_journey", "life_journey", icon="👨‍👩‍👧‍👦"))
    # Moon: Career Climber
    skills.append(_create_skill("career_climber", "Career Climber", "Reach highest salary tier", "board_games", "moon", "life_journey", "life_journey", icon="💼"))
    # Moon: Risk Taker
    skills.append(_create_skill("risk_taker", "Risk Taker", "Win after choosing all risky paths", "board_games", "moon", "life_journey", "life_journey", icon="🎲"))

    # ===== FINANCE (14 skills) =====

    # Sun
    skills.append(_create_skill("finance", "Finance", "Master financial operations and cryptocurrency management", "finance", "sun", tool_reward="send_bch", icon="💰"))
    # Planet: Transaction Mastery
    skills.append(_create_skill("transaction_mastery", "Transaction Mastery", "Validate and optimize blockchain transactions", "finance", "planet", "finance", tool_reward="validate_transaction", icon="📝"))
    # Moon: Fee Optimization
    skills.append(_create_skill("fee_optimization", "Fee Optimization", "Minimize transaction fees while maintaining speed", "finance", "moon", "transaction_mastery", "transaction_mastery", tool_reward="optimize_fees", icon="⚡"))
    # Moon: Transaction Tracking
    skills.append(_create_skill("transaction_tracking", "Transaction Tracking", "Monitor transaction status and confirmations", "finance", "moon", "transaction_mastery", "transaction_mastery", tool_reward="track_transaction", icon="🔍"))
    # Planet: Wallet Management
    skills.append(_create_skill("wallet_management", "Wallet Management", "Monitor and maintain wallet health", "finance", "planet", "finance", tool_reward="check_wallet_health", icon="👛"))
    # Moon: Balance Monitoring
    skills.append(_create_skill("balance_monitoring", "Balance Monitoring", "Track balances and set alerts", "finance", "moon", "wallet_management", "wallet_management", tool_reward="monitor_balance", icon="📊"))
    # Moon: Multi-sig Operations
    skills.append(_create_skill("multisig_operations", "Multi-sig Operations", "Manage multi-signature wallet operations", "finance", "moon", "wallet_management", "wallet_management", tool_reward="multisig_action", icon="🔐"))
    # Planet: Market Awareness
    skills.append(_create_skill("market_awareness", "Market Awareness", "Track and analyze market data", "finance", "planet", "finance", tool_reward="get_market_data", icon="📈"))
    # Moon: Price Alerts
    skills.append(_create_skill("price_alerts", "Price Alerts", "Set and manage price notifications", "finance", "moon", "market_awareness", "market_awareness", tool_reward="set_price_alert", icon="🔔"))
    # Moon: Market Trend Analysis
    skills.append(_create_skill("market_trend_analysis", "Market Trend Analysis", "Analyze market trends and patterns", "finance", "moon", "market_awareness", "market_awareness", tool_reward="analyze_market_trend", icon="📉"))
    # Planet: Savings Strategies
    skills.append(_create_skill("savings_strategies", "Savings Strategies", "Plan and execute savings goals", "finance", "planet", "finance", tool_reward="plan_savings", icon="🎯"))
    # Moon: Dollar Cost Averaging
    skills.append(_create_skill("dollar_cost_averaging", "Dollar Cost Averaging", "Set up recurring purchase schedules", "finance", "moon", "savings_strategies", "savings_strategies", tool_reward="setup_dca", icon="📅"))
    # Planet: Token Knowledge
    skills.append(_create_skill("token_knowledge", "Token Knowledge", "Identify and work with tokens", "finance", "planet", "finance", tool_reward="identify_token", icon="🪙"))
    # Moon: CashToken Operations
    skills.append(_create_skill("cashtoken_operations", "CashToken Operations", "Manage CashToken fungible and NFT tokens", "finance", "moon", "token_knowledge", "token_knowledge", tool_reward="manage_cashtokens", icon="💎"))

    return skills
