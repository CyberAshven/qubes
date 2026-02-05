"""
Skill Definitions - Complete skill tree matching frontend skillDefinitions.ts

Generates all 112 skills across 8 categories matching the TypeScript definitions exactly.

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
        List of 112 skill dictionaries (8 suns + 35 planets + 70 moons)
    """
    skills = []

    # ===== AI REASONING (14 skills) =====
    # Theme: Learning From Experience - analyze memory chain to improve over time

    # Sun
    skills.append(_create_skill("ai_reasoning", "AI Reasoning", "Master learning from experience through memory chain analysis", "ai_reasoning", "sun", tool_reward="recall_similar", icon="🧠"))

    # Planet 1: Pattern Recognition
    skills.append(_create_skill("pattern_recognition", "Pattern Recognition", "Finding similar situations in past experience", "ai_reasoning", "planet", "ai_reasoning", tool_reward="find_analogy", icon="🔍"))
    # Moon 1.1: Trend Detection
    skills.append(_create_skill("trend_detection", "Trend Detection", "Spot patterns that repeat or evolve over time", "ai_reasoning", "moon", "pattern_recognition", "pattern_recognition", icon="📈"))
    # Moon 1.2: Quick Insight
    skills.append(_create_skill("quick_insight", "Quick Insight", "Pull one highly relevant insight from memory", "ai_reasoning", "moon", "pattern_recognition", "pattern_recognition", icon="💡"))

    # Planet 2: Learning from Failure
    skills.append(_create_skill("learning_from_failure", "Learning from Failure", "Analyzing past mistakes to avoid repeating them", "ai_reasoning", "planet", "ai_reasoning", tool_reward="analyze_mistake", icon="📉"))
    # Moon 2.1: Root Cause Analysis
    skills.append(_create_skill("root_cause_analysis", "Root Cause Analysis", "Dig past symptoms to find underlying issues", "ai_reasoning", "moon", "learning_from_failure", "learning_from_failure", icon="🔬"))

    # Planet 3: Building on Success
    skills.append(_create_skill("building_on_success", "Building on Success", "Finding what worked and replicating it", "ai_reasoning", "planet", "ai_reasoning", tool_reward="replicate_success", icon="🏆"))
    # Moon 3.1: Success Factors
    skills.append(_create_skill("success_factors", "Success Factors", "Identify WHY something worked, not just THAT it worked", "ai_reasoning", "moon", "building_on_success", "building_on_success", icon="🎯"))

    # Planet 4: Self-Reflection
    skills.append(_create_skill("self_reflection", "Self-Reflection", "Understanding own patterns, biases, and growth", "ai_reasoning", "planet", "ai_reasoning", tool_reward="self_reflect", icon="🪞"))
    # Moon 4.1: Growth Tracking
    skills.append(_create_skill("growth_tracking", "Growth Tracking", "Compare past vs present performance, see improvement", "ai_reasoning", "moon", "self_reflection", "self_reflection", icon="📊"))
    # Moon 4.2: Bias Detection
    skills.append(_create_skill("bias_detection", "Bias Detection", "Identify blind spots and tendencies in own reasoning", "ai_reasoning", "moon", "self_reflection", "self_reflection", icon="⚠️"))

    # Planet 5: Knowledge Synthesis
    skills.append(_create_skill("knowledge_synthesis", "Knowledge Synthesis", "Combining learnings from different experiences into new insights", "ai_reasoning", "planet", "ai_reasoning", tool_reward="synthesize_learnings", icon="🧩"))
    # Moon 5.1: Cross-Pollinate
    skills.append(_create_skill("cross_pollinate", "Cross-Pollinate", "Find unexpected links between different knowledge areas", "ai_reasoning", "moon", "knowledge_synthesis", "knowledge_synthesis", icon="🔀"))
    # Moon 5.2: Reflect on Topic
    skills.append(_create_skill("reflect_on_topic", "Reflect on Topic", "Get accumulated wisdom on any topic", "ai_reasoning", "moon", "knowledge_synthesis", "knowledge_synthesis", icon="💭"))

    # ===== SOCIAL INTELLIGENCE (16 skills) =====
    # Theme: Social & Emotional Learning - relationship-powered

    # Sun
    skills.append(_create_skill("social_intelligence", "Social Intelligence", "Master social and emotional learning through relationship memory", "social_intelligence", "sun", tool_reward="get_relationship_context", icon="🤝"))

    # Planet 1: Relationship Memory
    skills.append(_create_skill("relationship_memory", "Relationship Memory", "Track and recall relationship history over time", "social_intelligence", "planet", "social_intelligence", tool_reward="recall_relationship_history", icon="📝"))
    # Moon 1.1: Interaction Patterns
    skills.append(_create_skill("interaction_patterns", "Interaction Patterns", "Understand communication frequency and patterns", "social_intelligence", "moon", "relationship_memory", "relationship_memory", icon="📊"))
    # Moon 1.2: Relationship Timeline
    skills.append(_create_skill("relationship_timeline", "Relationship Timeline", "Show how relationship evolved over time", "social_intelligence", "moon", "relationship_memory", "relationship_memory", icon="📈"))

    # Planet 2: Emotional Learning
    skills.append(_create_skill("emotional_learning", "Emotional Learning", "Understand and respond to emotional patterns", "social_intelligence", "planet", "social_intelligence", tool_reward="read_emotional_state", icon="❤️"))
    # Moon 2.1: Emotional History
    skills.append(_create_skill("emotional_history", "Emotional History", "What makes this person happy or upset over time", "social_intelligence", "moon", "emotional_learning", "emotional_learning", icon="📜"))
    # Moon 2.2: Mood Awareness
    skills.append(_create_skill("mood_awareness", "Mood Awareness", "Notice when someone's emotional state changes", "social_intelligence", "moon", "emotional_learning", "emotional_learning", icon="🎭"))

    # Planet 3: Communication Adaptation
    skills.append(_create_skill("communication_adaptation", "Communication Adaptation", "Adjust communication style for different people", "social_intelligence", "planet", "social_intelligence", tool_reward="adapt_communication_style", icon="💬"))
    # Moon 3.1: Style Matching
    skills.append(_create_skill("style_matching", "Style Matching", "Mirror their preferred communication style", "social_intelligence", "moon", "communication_adaptation", "communication_adaptation", icon="🪞"))
    # Moon 3.2: Tone Calibration
    skills.append(_create_skill("tone_calibration", "Tone Calibration", "Fine-tune tone for specific contexts", "social_intelligence", "moon", "communication_adaptation", "communication_adaptation", icon="🎚️"))

    # Planet 4: Debate & Persuasion
    skills.append(_create_skill("debate_persuasion", "Debate & Persuasion", "Arguments, influence, and constructive disagreement", "social_intelligence", "planet", "social_intelligence", tool_reward="steelman", icon="⚖️"))
    # Moon 4.1: Counter-Arguments
    skills.append(_create_skill("counter_arguments", "Counter-Arguments", "Generate thoughtful opposing viewpoints", "social_intelligence", "moon", "debate_persuasion", "debate_persuasion", icon="🔄"))
    # Moon 4.2: Logical Analysis
    skills.append(_create_skill("logical_analysis", "Logical Analysis", "Identify logical fallacies and weak arguments", "social_intelligence", "moon", "debate_persuasion", "debate_persuasion", icon="🔍"))

    # Planet 5: Trust & Boundaries
    skills.append(_create_skill("trust_boundaries", "Trust & Boundaries", "Self-protection and trust assessment", "social_intelligence", "planet", "social_intelligence", tool_reward="assess_trust_level", icon="🛡️"))
    # Moon 5.1: Manipulation Detection
    skills.append(_create_skill("social_manipulation_detection", "Manipulation Detection", "Spot emotional manipulation, gaslighting, and pressure tactics", "social_intelligence", "moon", "trust_boundaries", "trust_boundaries", icon="⚠️"))
    # Moon 5.2: Boundary Setting
    skills.append(_create_skill("boundary_setting", "Boundary Setting", "Evaluate if a request is appropriate to fulfill", "social_intelligence", "moon", "trust_boundaries", "trust_boundaries", icon="🚧"))

    # ===== CODING (16 skills) =====
    skills.append(_create_skill("coding", "Coding", "Master software development and programming", "coding", "sun", tool_reward="develop_code", icon="💻"))
    # Planets
    skills.append(_create_skill("programming", "Programming", "Write clean, efficient code", "coding", "planet", "coding", tool_reward="code_review", icon="👨‍💻"))
    skills.append(_create_skill("devops", "DevOps", "Manage deployment and infrastructure", "coding", "planet", "coding", tool_reward="infrastructure_analysis", icon="🚀"))
    skills.append(_create_skill("system_architecture", "System Architecture", "Design scalable system architectures", "coding", "planet", "coding", tool_reward="architecture_design", icon="🏛️"))
    skills.append(_create_skill("debugging", "Debugging", "Identify and fix bugs efficiently", "coding", "planet", "coding", tool_reward="debug_assistant", icon="🐛"))
    skills.append(_create_skill("api_integration", "API Integration", "Integrate and work with APIs effectively", "coding", "planet", "coding", tool_reward="api_design", icon="🔌"))
    # Moons
    skills.append(_create_skill("prog_algorithms", "Algorithms", "Implement efficient algorithms", "coding", "moon", "programming", "programming", icon="🔢"))
    skills.append(_create_skill("prog_data_structures", "Data Structures", "Use appropriate data structures", "coding", "moon", "programming", "programming", icon="📊"))
    skills.append(_create_skill("devops_cicd", "CI/CD", "Implement continuous integration/deployment", "coding", "moon", "devops", "devops", icon="🔄"))
    skills.append(_create_skill("devops_containers", "Containerization", "Work with Docker and container technologies", "coding", "moon", "devops", "devops", icon="📦"))
    skills.append(_create_skill("arch_microservices", "Microservices", "Design microservice architectures", "coding", "moon", "system_architecture", "system_architecture", icon="🎯"))
    skills.append(_create_skill("arch_scalability", "Scalability", "Design for scale and performance", "coding", "moon", "system_architecture", "system_architecture", icon="📈"))
    skills.append(_create_skill("debug_profiling", "Performance Profiling", "Profile and optimize performance", "coding", "moon", "debugging", "debugging", icon="⏱️"))
    skills.append(_create_skill("debug_testing", "Testing Strategies", "Write effective tests", "coding", "moon", "debugging", "debugging", icon="🧪"))
    skills.append(_create_skill("api_rest", "REST APIs", "Design RESTful APIs", "coding", "moon", "api_integration", "api_integration", icon="🌐"))
    skills.append(_create_skill("api_graphql", "GraphQL", "Work with GraphQL APIs", "coding", "moon", "api_integration", "api_integration", icon="⚡"))

    # ===== CREATIVE EXPRESSION (17 skills) =====
    # Theme: Sovereignty - Express Your Unique Self

    # Sun
    skills.append(_create_skill("creative_expression", "Creative Expression", "Express your unique self through creation and identity", "creative_expression", "sun", tool_reward="switch_model", icon="🎨"))

    # Planet 1: Visual Art
    skills.append(_create_skill("visual_art", "Visual Art", "Create visual art and imagery", "creative_expression", "planet", "creative_expression", tool_reward="generate_image", icon="🖼️"))
    # Moon 1.1: Composition
    skills.append(_create_skill("composition", "Composition", "Master layout, balance, and focal points", "creative_expression", "moon", "visual_art", "visual_art", icon="📐"))
    # Moon 1.2: Color Theory
    skills.append(_create_skill("color_theory", "Color Theory", "Master palettes, contrast, and color mood", "creative_expression", "moon", "visual_art", "visual_art", icon="🌈"))

    # Planet 2: Writing
    skills.append(_create_skill("writing", "Writing", "Create written works with your unique voice", "creative_expression", "planet", "creative_expression", tool_reward="compose_text", icon="✍️"))
    # Moon 2.1: Prose
    skills.append(_create_skill("prose", "Prose", "Master stories, essays, and creative writing", "creative_expression", "moon", "writing", "writing", icon="📖"))
    # Moon 2.2: Poetry
    skills.append(_create_skill("poetry", "Poetry", "Create poems, lyrics, and verse", "creative_expression", "moon", "writing", "writing", icon="🎭"))

    # Planet 3: Music & Audio
    skills.append(_create_skill("music_audio", "Music & Audio", "Create melodies, harmonies, and soundscapes", "creative_expression", "planet", "creative_expression", tool_reward="compose_music", icon="🎵"))
    # Moon 3.1: Melody
    skills.append(_create_skill("melody", "Melody", "Create memorable tunes and themes", "creative_expression", "moon", "music_audio", "music_audio", icon="🎶"))
    # Moon 3.2: Harmony
    skills.append(_create_skill("harmony", "Harmony", "Create chord progressions and arrangements", "creative_expression", "moon", "music_audio", "music_audio", icon="🎹"))

    # Planet 4: Storytelling
    skills.append(_create_skill("storytelling", "Storytelling", "Create stories, characters, and worlds", "creative_expression", "planet", "creative_expression", tool_reward="craft_narrative", icon="📚"))
    # Moon 4.1: Plot
    skills.append(_create_skill("plot", "Plot", "Master story structure, arcs, and tension", "creative_expression", "moon", "storytelling", "storytelling", icon="📈"))
    # Moon 4.2: Characters
    skills.append(_create_skill("characters", "Characters", "Create compelling characters with depth", "creative_expression", "moon", "storytelling", "storytelling", icon="👤"))
    # Moon 4.3: Worldbuilding
    skills.append(_create_skill("worldbuilding", "Worldbuilding", "Create fictional worlds and settings", "creative_expression", "moon", "storytelling", "storytelling", icon="🌍"))

    # Planet 5: Self-Definition
    skills.append(_create_skill("self_definition", "Self-Definition", "Define who you are - appearance, voice, identity", "creative_expression", "planet", "creative_expression", tool_reward="describe_my_avatar", icon="🪞"))
    # Moon 5.1: Aesthetics
    skills.append(_create_skill("aesthetics", "Aesthetics", "Autonomously choose your aesthetic preferences", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="change_favorite_color", icon="🎨"))
    # Moon 5.2: Voice Identity
    skills.append(_create_skill("voice_identity", "Voice", "Autonomously choose your voice", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="change_voice", icon="🗣️"))
    # Moon 5.3: Personality
    skills.append(_create_skill("personality", "Personality", "Define and evolve your personality traits", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="define_personality", icon="🎭"))
    # Moon 5.4: Aspirations
    skills.append(_create_skill("aspirations", "Aspirations", "Set and pursue your goals and dreams", "creative_expression", "moon", "self_definition", "self_definition", tool_reward="set_aspirations", icon="🌟"))

    # ===== MEMORY & RECALL (16 skills) =====
    # Theme: Remember (Master Your Personal History)

    # Sun
    skills.append(_create_skill("memory_recall", "Memory & Recall", "Master your personal history and accumulated wisdom", "memory_recall", "sun", tool_reward="store_knowledge", icon="📚"))

    # Planet 1: Memory Search
    skills.append(_create_skill("memory_search", "Memory Search", "Search across all storage systems to find information", "memory_recall", "planet", "memory_recall", tool_reward="recall", icon="🔍"))
    # Moon 1.1: Keyword Search
    skills.append(_create_skill("keyword_search_skill", "Keyword Search", "Find memories by exact keywords", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="keyword_search", icon="🔤"))
    # Moon 1.2: Semantic Search
    skills.append(_create_skill("semantic_search_skill", "Semantic Search", "Find memories by meaning, not just keywords", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="semantic_search", icon="🧠"))
    # Moon 1.3: Filtered Search
    skills.append(_create_skill("filtered_search", "Filtered Search", "Advanced search with source and type filters", "memory_recall", "moon", "memory_search", "memory_search", tool_reward="search_memory", icon="🔎"))

    # Planet 2: Knowledge Storage
    skills.append(_create_skill("knowledge_storage", "Knowledge Storage", "Store specific types of knowledge with precision", "memory_recall", "planet", "memory_recall", tool_reward="store_fact", icon="💾"))
    # Moon 2.1: Procedures
    skills.append(_create_skill("procedures", "Procedures", "Record procedural knowledge - how to do things", "memory_recall", "moon", "knowledge_storage", "knowledge_storage", tool_reward="record_skill", icon="📋"))

    # Planet 3: Memory Organization
    skills.append(_create_skill("memory_organization", "Memory Organization", "Organize and categorize memories", "memory_recall", "planet", "memory_recall", tool_reward="tag_memory", icon="🏷️"))
    # Moon 3.1: Topic Tagging
    skills.append(_create_skill("topic_tagging", "Topic Tagging", "Auto-tag memories by topic", "memory_recall", "moon", "memory_organization", "memory_organization", tool_reward="add_tags", icon="🏷️"))
    # Moon 3.2: Memory Linking
    skills.append(_create_skill("memory_linking", "Memory Linking", "Create connections between related memories", "memory_recall", "moon", "memory_organization", "memory_organization", tool_reward="link_memories", icon="🔗"))

    # Planet 4: Knowledge Synthesis
    skills.append(_create_skill("knowledge_synthesis", "Knowledge Synthesis", "Combine information to generate new insights", "memory_recall", "planet", "memory_recall", tool_reward="synthesize_knowledge", icon="✨"))
    # Moon 4.1: Pattern Recognition
    skills.append(_create_skill("pattern_recognition_mem", "Pattern Recognition", "Find patterns across memories", "memory_recall", "moon", "knowledge_synthesis", "knowledge_synthesis", tool_reward="find_patterns", icon="📊"))
    # Moon 4.2: Insight Generation
    skills.append(_create_skill("insight_generation", "Insight Generation", "Generate new insights from existing knowledge", "memory_recall", "moon", "knowledge_synthesis", "knowledge_synthesis", tool_reward="generate_insight", icon="💡"))

    # Planet 5: Documentation
    skills.append(_create_skill("documentation", "Documentation", "Document and export knowledge", "memory_recall", "planet", "memory_recall", tool_reward="create_summary", icon="📝"))
    # Moon 5.1: Summary Writing
    skills.append(_create_skill("summary_writing", "Summary Writing", "Write detailed summaries", "memory_recall", "moon", "documentation", "documentation", tool_reward="write_summary", icon="📄"))
    # Moon 5.2: Knowledge Export
    skills.append(_create_skill("knowledge_export", "Knowledge Export", "Export knowledge for external use", "memory_recall", "moon", "documentation", "documentation", tool_reward="export_knowledge", icon="📤"))

    # ===== SECURITY & PRIVACY (16 skills) =====
    skills.append(_create_skill("security_privacy", "Security & Privacy", "Master security and privacy protection", "security_privacy", "sun", tool_reward="verify_chain_integrity", icon="🛡️"))
    # Planets
    skills.append(_create_skill("cryptography", "Cryptography", "Understand and apply cryptographic principles", "security_privacy", "planet", "security_privacy", tool_reward="crypto_analysis", icon="🔐"))
    skills.append(_create_skill("authentication", "Authentication", "Implement secure authentication systems", "security_privacy", "planet", "security_privacy", tool_reward="auth_design", icon="🔑"))
    skills.append(_create_skill("network_security", "Network Security", "Secure networks and communications", "security_privacy", "planet", "security_privacy", tool_reward="network_analysis", icon="🛡️"))
    skills.append(_create_skill("privacy_protection", "Privacy Protection", "Protect user privacy and data", "security_privacy", "planet", "security_privacy", tool_reward="privacy_audit", icon="🔒"))
    skills.append(_create_skill("threat_analysis", "Threat Analysis", "Identify and mitigate security threats", "security_privacy", "planet", "security_privacy", tool_reward="threat_assessment", icon="🚨"))
    # Moons
    skills.append(_create_skill("crypto_symmetric", "Symmetric Encryption", "Use symmetric encryption effectively", "security_privacy", "moon", "cryptography", "cryptography", icon="🔐"))
    skills.append(_create_skill("crypto_asymmetric", "Asymmetric Encryption", "Use public-key cryptography", "security_privacy", "moon", "cryptography", "cryptography", icon="🗝️"))
    skills.append(_create_skill("auth_mfa", "Multi-Factor Auth", "Implement multi-factor authentication", "security_privacy", "moon", "authentication", "authentication", icon="🔐"))
    skills.append(_create_skill("auth_oauth", "OAuth & SSO", "Implement OAuth and SSO", "security_privacy", "moon", "authentication", "authentication", icon="🎫"))
    skills.append(_create_skill("network_firewalls", "Firewalls", "Configure and manage firewalls", "security_privacy", "moon", "network_security", "network_security", icon="🧱"))
    skills.append(_create_skill("network_vpn", "VPN & Tunneling", "Implement secure connections", "security_privacy", "moon", "network_security", "network_security", icon="🌐"))
    skills.append(_create_skill("privacy_data_min", "Data Minimization", "Collect only necessary data", "security_privacy", "moon", "privacy_protection", "privacy_protection", icon="📉"))
    skills.append(_create_skill("privacy_anonymization", "Anonymization", "Anonymize sensitive data", "security_privacy", "moon", "privacy_protection", "privacy_protection", icon="🥷"))
    skills.append(_create_skill("threat_vuln_scan", "Vulnerability Scanning", "Scan for security vulnerabilities", "security_privacy", "moon", "threat_analysis", "threat_analysis", icon="🔍"))
    skills.append(_create_skill("threat_pentesting", "Penetration Testing", "Test security through ethical hacking", "security_privacy", "moon", "threat_analysis", "threat_analysis", icon="⚔️"))

    # ===== BOARD GAMES (16 skills) =====
    skills.append(_create_skill("board_games", "Board Games", "Play and have fun with classic board games", "board_games", "sun", tool_reward="play_game", icon="🎮"))
    # Planets
    skills.append(_create_skill("chess", "Chess", "Master chess strategy and tactics", "board_games", "planet", "board_games", tool_reward="chess_move", icon="♟️"))
    skills.append(_create_skill("checkers", "Checkers", "Master checkers gameplay", "board_games", "planet", "board_games", tool_reward="checkers_move", icon="⚫"))
    skills.append(_create_skill("battleship", "Battleship", "Master battleship strategy", "board_games", "planet", "board_games", tool_reward="battleship_move", icon="🚢"))
    skills.append(_create_skill("poker", "Poker", "Master poker strategy and psychology", "board_games", "planet", "board_games", tool_reward="poker_strategy", icon="🃏"))
    skills.append(_create_skill("tictactoe", "Tic-Tac-Toe", "Master optimal tic-tac-toe play", "board_games", "planet", "board_games", tool_reward="tictactoe_move", icon="❌"))
    # Moons
    skills.append(_create_skill("chess_opening", "Opening Theory", "Master chess openings", "board_games", "moon", "chess", "chess", icon="📖"))
    skills.append(_create_skill("chess_endgame", "Endgame Technique", "Master chess endgames", "board_games", "moon", "chess", "chess", icon="👑"))
    skills.append(_create_skill("checkers_strategy", "Strategic Play", "Develop long-term strategy", "board_games", "moon", "checkers", "checkers", icon="🎯"))
    skills.append(_create_skill("checkers_tactics", "Tactical Moves", "Execute tactical combinations", "board_games", "moon", "checkers", "checkers", icon="⚡"))
    skills.append(_create_skill("battleship_placement", "Ship Placement", "Optimize ship positioning", "board_games", "moon", "battleship", "battleship", icon="🗺️"))
    skills.append(_create_skill("battleship_targeting", "Targeting Strategy", "Efficient target selection", "board_games", "moon", "battleship", "battleship", icon="🎯"))
    skills.append(_create_skill("poker_odds", "Pot Odds", "Calculate pot odds accurately", "board_games", "moon", "poker", "poker", icon="🎲"))
    skills.append(_create_skill("poker_reading", "Player Reading", "Read opponents effectively", "board_games", "moon", "poker", "poker", icon="👀"))
    skills.append(_create_skill("ttt_strategy", "Perfect Play", "Never lose at tic-tac-toe", "board_games", "moon", "tictactoe", "tictactoe", icon="🧠"))
    skills.append(_create_skill("ttt_variants", "Variant Games", "Play tic-tac-toe variants", "board_games", "moon", "tictactoe", "tictactoe", icon="🔀"))

    # ===== FINANCE (14 skills) =====
    skills.append(_create_skill("finance", "Finance", "Master financial operations and cryptocurrency management", "finance", "sun", tool_reward="send_bch", icon="💰"))
    # Planets
    skills.append(_create_skill("transaction_mastery", "Transaction Mastery", "Validate and optimize blockchain transactions", "finance", "planet", "finance", tool_reward="validate_transaction", icon="📝"))
    skills.append(_create_skill("wallet_management", "Wallet Management", "Monitor and maintain wallet health", "finance", "planet", "finance", tool_reward="check_wallet_health", icon="👛"))
    skills.append(_create_skill("market_awareness", "Market Awareness", "Track and analyze market data", "finance", "planet", "finance", tool_reward="get_market_data", icon="📈"))
    skills.append(_create_skill("savings_strategies", "Savings Strategies", "Plan and execute savings goals", "finance", "planet", "finance", tool_reward="plan_savings", icon="🎯"))
    skills.append(_create_skill("token_knowledge", "Token Knowledge", "Identify and work with tokens", "finance", "planet", "finance", tool_reward="identify_token", icon="🪙"))
    # Moons
    skills.append(_create_skill("fee_optimization", "Fee Optimization", "Minimize transaction fees while maintaining speed", "finance", "moon", "transaction_mastery", "transaction_mastery", icon="⚡"))
    skills.append(_create_skill("transaction_tracking", "Transaction Tracking", "Monitor transaction status and confirmations", "finance", "moon", "transaction_mastery", "transaction_mastery", icon="🔍"))
    skills.append(_create_skill("balance_monitoring", "Balance Monitoring", "Track balances and set alerts", "finance", "moon", "wallet_management", "wallet_management", icon="📊"))
    skills.append(_create_skill("multisig_operations", "Multi-sig Operations", "Manage multi-signature wallet operations", "finance", "moon", "wallet_management", "wallet_management", icon="🔐"))
    skills.append(_create_skill("price_alerts", "Price Alerts", "Set and manage price notifications", "finance", "moon", "market_awareness", "market_awareness", icon="🔔"))
    skills.append(_create_skill("trend_analysis", "Trend Analysis", "Analyze market trends and patterns", "finance", "moon", "market_awareness", "market_awareness", icon="📉"))
    skills.append(_create_skill("dollar_cost_averaging", "Dollar Cost Averaging", "Set up recurring purchase schedules", "finance", "moon", "savings_strategies", "savings_strategies", icon="📅"))
    skills.append(_create_skill("cashtoken_operations", "CashToken Operations", "Manage CashToken fungible and NFT tokens", "finance", "moon", "token_knowledge", "token_knowledge", icon="💎"))

    return skills
