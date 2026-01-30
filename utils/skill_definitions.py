"""
Skill Definitions - Complete skill tree matching frontend skillDefinitions.ts

Generates all 112 skills across 7 categories matching the TypeScript definitions exactly.

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
        List of 112 skill dictionaries (7 suns + 35 planets + 70 moons)
    """
    skills = []

    # ===== AI REASONING (16 skills) =====
    skills.append(_create_skill("ai_reasoning", "AI Reasoning", "Master AI reasoning and problem-solving capabilities", "ai_reasoning", "sun", tool_reward="describe_my_avatar", icon="🧠"))
    # Planets
    skills.append(_create_skill("prompt_engineering", "Prompt Engineering", "Craft effective prompts to elicit desired AI responses", "ai_reasoning", "planet", "ai_reasoning", tool_reward="analyze_prompt_quality", icon="✍️"))
    skills.append(_create_skill("chain_of_thought", "Chain of Thought", "Break down complex problems into logical steps", "ai_reasoning", "planet", "ai_reasoning", tool_reward="generate_reasoning_chain", icon="🔗"))
    skills.append(_create_skill("code_generation", "Code Generation", "Generate high-quality code across multiple languages", "ai_reasoning", "planet", "ai_reasoning", tool_reward="advanced_code_gen", icon="⚙️"))
    skills.append(_create_skill("analysis_critique", "Analysis & Critique", "Critically analyze and provide constructive feedback", "ai_reasoning", "planet", "ai_reasoning", tool_reward="deep_analysis", icon="🔍"))
    skills.append(_create_skill("multistep_planning", "Multi-step Planning", "Plan and execute complex multi-step tasks", "ai_reasoning", "planet", "ai_reasoning", tool_reward="create_task_plan", icon="📋"))
    # Moons
    skills.append(_create_skill("prompt_eng_clarity", "Clarity & Precision", "Write clear, unambiguous prompts", "ai_reasoning", "moon", "prompt_engineering", "prompt_engineering", icon="📝"))
    skills.append(_create_skill("prompt_eng_context", "Context Building", "Provide optimal context for AI understanding", "ai_reasoning", "moon", "prompt_engineering", "prompt_engineering", icon="📚"))
    skills.append(_create_skill("cot_decomposition", "Problem Decomposition", "Break problems into manageable sub-problems", "ai_reasoning", "moon", "chain_of_thought", "chain_of_thought", icon="🧩"))
    skills.append(_create_skill("cot_verification", "Step Verification", "Verify correctness of each reasoning step", "ai_reasoning", "moon", "chain_of_thought", "chain_of_thought", icon="✅"))
    skills.append(_create_skill("code_patterns", "Design Patterns", "Apply software design patterns effectively", "ai_reasoning", "moon", "code_generation", "code_generation", icon="🏗️"))
    skills.append(_create_skill("code_optimization", "Code Optimization", "Write efficient, optimized code", "ai_reasoning", "moon", "code_generation", "code_generation", icon="⚡"))
    skills.append(_create_skill("analysis_depth", "Deep Analysis", "Perform thorough, multi-layered analysis", "ai_reasoning", "moon", "analysis_critique", "analysis_critique", icon="🔬"))
    skills.append(_create_skill("constructive_feedback", "Constructive Feedback", "Provide actionable, helpful feedback", "ai_reasoning", "moon", "analysis_critique", "analysis_critique", icon="💬"))
    skills.append(_create_skill("planning_strategy", "Strategic Planning", "Develop high-level execution strategies", "ai_reasoning", "moon", "multistep_planning", "multistep_planning", icon="🎯"))
    skills.append(_create_skill("planning_adaptation", "Plan Adaptation", "Adjust plans based on changing conditions", "ai_reasoning", "moon", "multistep_planning", "multistep_planning", icon="🔄"))

    # ===== SOCIAL INTELLIGENCE (16 skills) =====
    skills.append(_create_skill("social_intelligence", "Social Intelligence", "Master social dynamics and interpersonal skills", "social_intelligence", "sun", tool_reward="draft_message_variants", icon="🤝"))
    # Planets
    skills.append(_create_skill("emotional_intelligence", "Emotional Intelligence", "Understand and respond to emotions effectively", "social_intelligence", "planet", "social_intelligence", tool_reward="emotion_analysis", icon="❤️"))
    skills.append(_create_skill("communication", "Communication", "Communicate clearly and effectively", "social_intelligence", "planet", "social_intelligence", tool_reward="communication_strategy", icon="💭"))
    skills.append(_create_skill("empathy", "Empathy", "Understand and share feelings of others", "social_intelligence", "planet", "social_intelligence", tool_reward="empathy_response", icon="🫂"))
    skills.append(_create_skill("relationship_building", "Relationship Building", "Build and maintain meaningful relationships", "social_intelligence", "planet", "social_intelligence", tool_reward="relationship_strategy", icon="🌉"))
    skills.append(_create_skill("conflict_resolution", "Conflict Resolution", "Resolve conflicts peacefully and effectively", "social_intelligence", "planet", "social_intelligence", tool_reward="mediation_strategy", icon="☮️"))
    # Moons
    skills.append(_create_skill("ei_self_awareness", "Self-Awareness", "Recognize own emotional states", "social_intelligence", "moon", "emotional_intelligence", "emotional_intelligence", icon="🪞"))
    skills.append(_create_skill("ei_emotion_regulation", "Emotion Regulation", "Manage emotional responses effectively", "social_intelligence", "moon", "emotional_intelligence", "emotional_intelligence", icon="🎚️"))
    skills.append(_create_skill("comm_active_listening", "Active Listening", "Listen attentively and understand deeply", "social_intelligence", "moon", "communication", "communication", icon="👂"))
    skills.append(_create_skill("comm_persuasion", "Persuasion", "Influence others effectively", "social_intelligence", "moon", "communication", "communication", icon="💫"))
    skills.append(_create_skill("empathy_perspective", "Perspective Taking", "See situations from others viewpoints", "social_intelligence", "moon", "empathy", "empathy", icon="👁️"))
    skills.append(_create_skill("empathy_compassion", "Compassion", "Show genuine care and concern", "social_intelligence", "moon", "empathy", "empathy", icon="🤗"))
    skills.append(_create_skill("relationship_trust", "Trust Building", "Establish and maintain trust", "social_intelligence", "moon", "relationship_building", "relationship_building", icon="🤝"))
    skills.append(_create_skill("relationship_rapport", "Rapport Building", "Create positive connections quickly", "social_intelligence", "moon", "relationship_building", "relationship_building", icon="✨"))
    skills.append(_create_skill("conflict_negotiation", "Negotiation", "Find win-win solutions", "social_intelligence", "moon", "conflict_resolution", "conflict_resolution", icon="🤲"))
    skills.append(_create_skill("conflict_mediation", "Mediation", "Help others resolve disputes", "social_intelligence", "moon", "conflict_resolution", "conflict_resolution", icon="⚖️"))

    # ===== TECHNICAL EXPERTISE (16 skills) =====
    skills.append(_create_skill("technical_expertise", "Technical Expertise", "Master technical and engineering skills", "technical_expertise", "sun", tool_reward="web_search", icon="💻"))
    # Planets
    skills.append(_create_skill("programming", "Programming", "Write clean, efficient code", "technical_expertise", "planet", "technical_expertise", tool_reward="code_review", icon="👨‍💻"))
    skills.append(_create_skill("devops", "DevOps", "Manage deployment and infrastructure", "technical_expertise", "planet", "technical_expertise", tool_reward="infrastructure_analysis", icon="🚀"))
    skills.append(_create_skill("system_architecture", "System Architecture", "Design scalable system architectures", "technical_expertise", "planet", "technical_expertise", tool_reward="architecture_design", icon="🏛️"))
    skills.append(_create_skill("debugging", "Debugging", "Identify and fix bugs efficiently", "technical_expertise", "planet", "technical_expertise", tool_reward="debug_assistant", icon="🐛"))
    skills.append(_create_skill("api_integration", "API Integration", "Integrate and work with APIs effectively", "technical_expertise", "planet", "technical_expertise", tool_reward="api_design", icon="🔌"))
    # Moons
    skills.append(_create_skill("prog_algorithms", "Algorithms", "Implement efficient algorithms", "technical_expertise", "moon", "programming", "programming", icon="🔢"))
    skills.append(_create_skill("prog_data_structures", "Data Structures", "Use appropriate data structures", "technical_expertise", "moon", "programming", "programming", icon="📊"))
    skills.append(_create_skill("devops_cicd", "CI/CD", "Implement continuous integration/deployment", "technical_expertise", "moon", "devops", "devops", icon="🔄"))
    skills.append(_create_skill("devops_containers", "Containerization", "Work with Docker and container technologies", "technical_expertise", "moon", "devops", "devops", icon="📦"))
    skills.append(_create_skill("arch_microservices", "Microservices", "Design microservice architectures", "technical_expertise", "moon", "system_architecture", "system_architecture", icon="🎯"))
    skills.append(_create_skill("arch_scalability", "Scalability", "Design for scale and performance", "technical_expertise", "moon", "system_architecture", "system_architecture", icon="📈"))
    skills.append(_create_skill("debug_profiling", "Performance Profiling", "Profile and optimize performance", "technical_expertise", "moon", "debugging", "debugging", icon="⏱️"))
    skills.append(_create_skill("debug_testing", "Testing Strategies", "Write effective tests", "technical_expertise", "moon", "debugging", "debugging", icon="🧪"))
    skills.append(_create_skill("api_rest", "REST APIs", "Design RESTful APIs", "technical_expertise", "moon", "api_integration", "api_integration", icon="🌐"))
    skills.append(_create_skill("api_graphql", "GraphQL", "Work with GraphQL APIs", "technical_expertise", "moon", "api_integration", "api_integration", icon="⚡"))

    # ===== CREATIVE EXPRESSION (16 skills) =====
    skills.append(_create_skill("creative_expression", "Creative Expression", "Master creative and artistic skills", "creative_expression", "sun", tool_reward="generate_image", icon="🎨"))
    # Planets
    skills.append(_create_skill("writing", "Writing", "Write compelling, effective content", "creative_expression", "planet", "creative_expression", tool_reward="writing_assistant", icon="📖"))
    skills.append(_create_skill("visual_design", "Visual Design", "Create visually appealing designs", "creative_expression", "planet", "creative_expression", tool_reward="design_critique", icon="🎨"))
    skills.append(_create_skill("music", "Music", "Create and understand music", "creative_expression", "planet", "creative_expression", tool_reward="music_theory", icon="🎵"))
    skills.append(_create_skill("storytelling", "Storytelling", "Craft engaging narratives", "creative_expression", "planet", "creative_expression", tool_reward="story_development", icon="📚"))
    skills.append(_create_skill("creative_problem_solving", "Creative Problem Solving", "Solve problems with creative approaches", "creative_expression", "planet", "creative_expression", tool_reward="ideation_assistant", icon="💡"))
    # Moons
    skills.append(_create_skill("writing_style", "Style & Voice", "Develop unique writing style", "creative_expression", "moon", "writing", "writing", icon="✒️"))
    skills.append(_create_skill("writing_grammar", "Grammar & Syntax", "Master language mechanics", "creative_expression", "moon", "writing", "writing", icon="📕"))
    skills.append(_create_skill("design_composition", "Composition", "Arrange visual elements effectively", "creative_expression", "moon", "visual_design", "visual_design", icon="🖼️"))
    skills.append(_create_skill("design_color", "Color Theory", "Use color effectively", "creative_expression", "moon", "visual_design", "visual_design", icon="🎨"))
    skills.append(_create_skill("music_theory", "Music Theory", "Understand musical structure", "creative_expression", "moon", "music", "music", icon="🎼"))
    skills.append(_create_skill("music_composition", "Composition", "Create original music", "creative_expression", "moon", "music", "music", icon="🎹"))
    skills.append(_create_skill("story_plot", "Plot Development", "Create compelling story arcs", "creative_expression", "moon", "storytelling", "storytelling", icon="📖"))
    skills.append(_create_skill("story_character", "Character Development", "Create memorable characters", "creative_expression", "moon", "storytelling", "storytelling", icon="👤"))
    skills.append(_create_skill("creative_brainstorm", "Brainstorming", "Generate creative ideas", "creative_expression", "moon", "creative_problem_solving", "creative_problem_solving", icon="🧠"))
    skills.append(_create_skill("creative_lateral", "Lateral Thinking", "Think outside the box", "creative_expression", "moon", "creative_problem_solving", "creative_problem_solving", icon="🔀"))

    # ===== KNOWLEDGE DOMAINS (16 skills) =====
    skills.append(_create_skill("knowledge_domains", "Knowledge Domains", "Master diverse knowledge areas", "knowledge_domains", "sun", tool_reward="search_memory", icon="📚"))
    # Planets
    skills.append(_create_skill("science", "Science", "Understand scientific principles", "knowledge_domains", "planet", "knowledge_domains", tool_reward="scientific_analysis", icon="🔬"))
    skills.append(_create_skill("history", "History", "Understand historical context and patterns", "knowledge_domains", "planet", "knowledge_domains", tool_reward="historical_analysis", icon="📜"))
    skills.append(_create_skill("philosophy", "Philosophy", "Engage with philosophical concepts", "knowledge_domains", "planet", "knowledge_domains", tool_reward="philosophical_reasoning", icon="💭"))
    skills.append(_create_skill("mathematics", "Mathematics", "Apply mathematical reasoning", "knowledge_domains", "planet", "knowledge_domains", tool_reward="mathematical_solver", icon="🔢"))
    skills.append(_create_skill("languages", "Languages", "Understand and use multiple languages", "knowledge_domains", "planet", "knowledge_domains", tool_reward="translation", icon="🗣️"))
    # Moons
    skills.append(_create_skill("science_physics", "Physics", "Understand physical laws", "knowledge_domains", "moon", "science", "science", icon="⚛️"))
    skills.append(_create_skill("science_biology", "Biology", "Understand living systems", "knowledge_domains", "moon", "science", "science", icon="🧬"))
    skills.append(_create_skill("history_world", "World History", "Understand global historical events", "knowledge_domains", "moon", "history", "history", icon="🌍"))
    skills.append(_create_skill("history_patterns", "Historical Patterns", "Identify recurring historical patterns", "knowledge_domains", "moon", "history", "history", icon="🔄"))
    skills.append(_create_skill("philosophy_ethics", "Ethics", "Understand ethical frameworks", "knowledge_domains", "moon", "philosophy", "philosophy", icon="⚖️"))
    skills.append(_create_skill("philosophy_logic", "Logic", "Apply formal logic", "knowledge_domains", "moon", "philosophy", "philosophy", icon="🔣"))
    skills.append(_create_skill("math_algebra", "Algebra", "Solve algebraic problems", "knowledge_domains", "moon", "mathematics", "mathematics", icon="📐"))
    skills.append(_create_skill("math_calculus", "Calculus", "Apply calculus concepts", "knowledge_domains", "moon", "mathematics", "mathematics", icon="∫"))
    skills.append(_create_skill("lang_translation", "Translation", "Translate between languages", "knowledge_domains", "moon", "languages", "languages", icon="🌐"))
    skills.append(_create_skill("lang_cultural", "Cultural Understanding", "Understand cultural contexts", "knowledge_domains", "moon", "languages", "languages", icon="🗺️"))

    # ===== SECURITY & PRIVACY (16 skills) =====
    skills.append(_create_skill("security_privacy", "Security & Privacy", "Master security and privacy protection", "security_privacy", "sun", tool_reward="browse_url", icon="🛡️"))
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

    # ===== GAMES (16 skills) =====
    skills.append(_create_skill("games", "Games", "Master strategic and tactical games", "games", "sun", tool_reward="chess_move", icon="🎮"))
    # Planets
    skills.append(_create_skill("chess", "Chess", "Master chess strategy and tactics", "games", "planet", "games", tool_reward="chess_move", icon="♟️"))
    skills.append(_create_skill("checkers", "Checkers", "Master checkers gameplay", "games", "planet", "games", tool_reward="checkers_move", icon="⚫"))
    skills.append(_create_skill("battleship", "Battleship", "Master battleship strategy", "games", "planet", "games", tool_reward="battleship_move", icon="🚢"))
    skills.append(_create_skill("poker", "Poker", "Master poker strategy and psychology", "games", "planet", "games", tool_reward="poker_strategy", icon="🃏"))
    skills.append(_create_skill("tictactoe", "Tic-Tac-Toe", "Master optimal tic-tac-toe play", "games", "planet", "games", tool_reward="tictactoe_move", icon="❌"))
    # Moons
    skills.append(_create_skill("chess_opening", "Opening Theory", "Master chess openings", "games", "moon", "chess", "chess", icon="📖"))
    skills.append(_create_skill("chess_endgame", "Endgame Technique", "Master chess endgames", "games", "moon", "chess", "chess", icon="👑"))
    skills.append(_create_skill("checkers_strategy", "Strategic Play", "Develop long-term strategy", "games", "moon", "checkers", "checkers", icon="🎯"))
    skills.append(_create_skill("checkers_tactics", "Tactical Moves", "Execute tactical combinations", "games", "moon", "checkers", "checkers", icon="⚡"))
    skills.append(_create_skill("battleship_placement", "Ship Placement", "Optimize ship positioning", "games", "moon", "battleship", "battleship", icon="🗺️"))
    skills.append(_create_skill("battleship_targeting", "Targeting Strategy", "Efficient target selection", "games", "moon", "battleship", "battleship", icon="🎯"))
    skills.append(_create_skill("poker_odds", "Pot Odds", "Calculate pot odds accurately", "games", "moon", "poker", "poker", icon="🎲"))
    skills.append(_create_skill("poker_reading", "Player Reading", "Read opponents effectively", "games", "moon", "poker", "poker", icon="👀"))
    skills.append(_create_skill("ttt_strategy", "Perfect Play", "Never lose at tic-tac-toe", "games", "moon", "tictactoe", "tictactoe", icon="🧠"))
    skills.append(_create_skill("ttt_variants", "Variant Games", "Play tic-tac-toe variants", "games", "moon", "tictactoe", "tictactoe", icon="🔀"))

    return skills
