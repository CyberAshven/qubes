"""
Skill Scanner System

Scans unencrypted ACTION blocks BEFORE encryption during anchoring.
Detects skill tool usage and awards XP based on which tools were used and whether they succeeded.
Much faster than post-encryption scanning since no decryption is needed.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re

from utils.logging import get_logger
from core.events import Events

logger = get_logger(__name__)

# Category colors for celebration UI (matches frontend skillDefinitions.ts)
CATEGORY_COLORS = {
    "ai_reasoning": "#4A90E2",
    "social_intelligence": "#FF69B4",
    "coding": "#00FF88",
    "creative_expression": "#FFB347",
    "memory_recall": "#9B59B6",
    "security_privacy": "#E74C3C",
    "board_games": "#F39C12",
    "finance": "#00D4AA",
}


def calculate_document_xp(file_size_bytes: int, page_count: int) -> int:
    """
    Calculate XP for document processing (1-10 XP).
    Awards whichever gives more XP: file size or page count.

    Args:
        file_size_bytes: File size in bytes
        page_count: Number of pages

    Returns:
        XP amount (1-10)
    """
    # File size XP: 1 XP per 500 KB, capped at 10
    file_size_xp = min(10, max(1, file_size_bytes // 500_000))

    # Page count XP: ~0.8 XP per page, capped at 10
    page_count_xp = min(10, max(2, int(page_count * 0.8)))

    # Return whichever gives more XP
    return max(file_size_xp, page_count_xp)


# Tool-to-Skill Mapping
# Maps each tool (by action_type) to a skill_id (must match skillDefinitions.ts planet IDs)
# Note: web_search and browse_url use intelligent detection (analyze_research_topic)
# Note: get_system_state, update_system_state, get_skill_tree are utility tools (no XP)
TOOL_TO_SKILL_MAPPING = {
    # ═══════════════════════════════════════════════════════════════════
    # AI REASONING - Learning From Experience
    # Theme: Analyze memory chain to find patterns, learn from mistakes,
    #        build on successes, and synthesize knowledge over time
    # ═══════════════════════════════════════════════════════════════════
    # Sun Tool
    "recall_similar": "ai_reasoning",

    # Planet 1: Pattern Recognition
    "find_analogy": "pattern_recognition",
    # Moons
    "detect_trend": "trend_detection",
    "quick_insight": "quick_insight",

    # Planet 2: Learning from Failure
    "analyze_mistake": "learning_from_failure",
    # Moon
    "find_root_cause": "root_cause_analysis",

    # Planet 3: Building on Success
    "replicate_success": "building_on_success",
    # Moon
    "extract_success_factors": "success_factors",

    # Planet 4: Self-Reflection
    "self_reflect": "self_reflection",
    # Moons
    "track_growth": "growth_tracking",
    "detect_bias": "bias_detection",

    # Planet 5: Knowledge Synthesis
    "synthesize_learnings": "knowledge_synthesis",
    # Moons
    "cross_pollinate": "cross_pollinate",
    "reflect_on_topic": "reflect_on_topic",

    # ═══════════════════════════════════════════════════════════════════
    # SOCIAL INTELLIGENCE - Social & Emotional Learning
    # Theme: Relationship-powered social learning with 48-field relationship
    # tracking, emotional patterns, communication adaptation, and self-protection
    # ═══════════════════════════════════════════════════════════════════
    # Sun Tool
    "get_relationship_context": "social_intelligence",

    # Planet 1: Relationship Memory
    "recall_relationship_history": "relationship_memory",
    # Moons
    "analyze_interaction_patterns": "interaction_patterns",
    "get_relationship_timeline": "relationship_timeline",

    # Planet 2: Emotional Learning
    "read_emotional_state": "emotional_learning",
    # Moons
    "track_emotional_patterns": "emotional_history",
    "detect_mood_shift": "mood_awareness",

    # Planet 3: Communication Adaptation
    "adapt_communication_style": "communication_adaptation",
    # Moons
    "match_communication_style": "style_matching",
    "calibrate_tone": "tone_calibration",

    # Planet 4: Debate & Persuasion
    "steelman": "debate_persuasion",
    # Moons
    "devils_advocate": "counter_arguments",
    "spot_fallacy": "logical_analysis",

    # Planet 5: Trust & Boundaries
    "assess_trust_level": "trust_boundaries",
    # Moons
    "detect_social_manipulation": "social_manipulation_detection",
    "evaluate_request": "boundary_setting",

    # ═══════════════════════════════════════════════════════════════════
    # CODING (Phase 3 - 18 tools)
    # Theme: Ship It (Results-Focused)
    # XP Model: Waitress (base 1 + tips 0-9)
    # ═══════════════════════════════════════════════════════════════════

    # Sun Tool
    "develop_code": "coding",

    # Planet 1: Testing
    "run_tests": "testing",
    # Moons
    "write_unit_test": "unit_tests",
    "measure_coverage": "test_coverage",

    # Planet 2: Debugging
    "debug_code": "debugging",
    # Moons
    "analyze_error": "error_analysis",
    "find_root_cause": "root_cause",

    # Planet 3: Algorithms
    "benchmark_code": "algorithms",
    # Moons
    "analyze_complexity": "complexity_analysis",
    "tune_performance": "performance_tuning",

    # Planet 4: Hacking
    "security_scan": "hacking",
    # Moons
    "find_exploit": "exploits",
    "reverse_engineer": "reverse_engineering",
    "pen_test": "penetration_testing",

    # Planet 5: Code Review
    "review_code": "code_review",
    # Moons
    "refactor_code": "refactoring",
    "git_operation": "version_control",
    "generate_docs": "documentation",

    # ═══════════════════════════════════════════════════════════════════
    # CREATIVE EXPRESSION - Sovereignty (Express Your Unique Self)
    # Theme: Identity through creation - visual art, writing, music,
    # storytelling, and self-definition tools
    # ═══════════════════════════════════════════════════════════════════
    # Sun Tool
    "switch_model": "creative_expression",

    # Planet 1: Visual Art
    "generate_image": "visual_art",
    # Moons
    "refine_composition": "composition",
    "apply_color_theory": "color_theory",

    # Planet 2: Writing
    "compose_text": "writing",
    # Moons
    "craft_prose": "prose",
    "write_poetry": "poetry",

    # Planet 3: Music & Audio
    "compose_music": "music_audio",
    # Moons
    "create_melody": "melody",
    "design_harmony": "harmony",

    # Planet 4: Storytelling
    "craft_narrative": "storytelling",
    # Moons
    "develop_plot": "plot",
    "design_character": "characters",
    "build_world": "worldbuilding",

    # Planet 5: Self-Definition
    "describe_my_avatar": "self_definition",
    # Moons
    "change_favorite_color": "aesthetics",
    "change_voice": "voice_identity",
    "define_personality": "personality",
    "set_aspirations": "aspirations",

    # ═══════════════════════════════════════════════════════════════════
    # MEMORY & RECALL - Remember Theme (Master Your Personal History)
    # Theme: Librarian Sun that manages ALL knowledge - searches, organizes,
    # synthesizes, and documents knowledge across all storage systems
    # ═══════════════════════════════════════════════════════════════════
    # Sun Tool
    "store_knowledge": "memory_recall",

    # Planet 1: Memory Search
    "recall": "memory_search",
    # Moons
    "keyword_search": "keyword_search_skill",
    "semantic_search": "semantic_search_skill",
    "search_memory": "filtered_search",

    # Planet 2: Knowledge Storage
    "store_fact": "knowledge_storage",
    # Moon
    "record_skill": "procedures",

    # Planet 3: Memory Organization
    "tag_memory": "memory_organization",
    # Moons
    "add_tags": "topic_tagging",
    "link_memories": "memory_linking",

    # Planet 4: Knowledge Synthesis
    "synthesize_knowledge": "knowledge_synthesis",
    # Moons
    "find_patterns": "pattern_recognition_mem",
    "generate_insight": "insight_generation",

    # Planet 5: Documentation
    "create_summary": "documentation",
    # Moons
    "write_summary": "summary_writing",
    "export_knowledge": "knowledge_export",

    # ═══════════════════════════════════════════════════════════════════
    # SECURITY & PRIVACY (Phase 6 - 16 tools)
    # Theme: Chain Integrity & Self-Defense
    # ═══════════════════════════════════════════════════════════════════

    # Sun Tool
    "verify_chain_integrity": "security_privacy",

    # Planet 1: Chain Security
    "audit_chain": "chain_security",
    # Moons
    "detect_tampering": "tamper_detection",
    "verify_anchor": "anchor_verification",

    # Planet 2: Privacy Protection
    "assess_sensitivity": "privacy_protection",
    # Moons
    "classify_data": "data_classification",
    "control_sharing": "sharing_control",

    # Planet 3: Qube Network Security
    "vet_qube": "qube_network_security",
    # Moons
    "check_reputation": "reputation_check",
    "secure_group_chat": "group_security",

    # Planet 4: Threat Detection
    "detect_threat": "threat_detection",
    # Moons
    "detect_technical_manipulation": "technical_manipulation_detection",
    "detect_hostile_qube": "hostile_qube_detection",

    # Planet 5: Self-Defense
    "defend_reasoning": "self_defense",
    # Moons
    "detect_injection": "prompt_injection_defense",
    "validate_reasoning": "reasoning_validation",

    # ═══════════════════════════════════════════════════════════════════
    # BOARD GAMES (Phase 7 - 6 tools + achievements)
    # Theme: Play (Have Fun and Entertain)
    # XP Model: 0.1/turn + outcome bonuses
    # ═══════════════════════════════════════════════════════════════════

    # Sun Tool
    "play_game": "board_games",

    # Planet 1: Chess
    "chess_move": "chess",
    "analyze_game_state": "chess",
    "plan_strategy": "chess",
    "learn_from_game": "chess",

    # Planet 2: Property Tycoon
    "property_tycoon_action": "property_tycoon",

    # Planet 3: Race Home
    "race_home_action": "race_home",

    # Planet 4: Mystery Mansion
    "mystery_mansion_action": "mystery_mansion",

    # Planet 5: Life Journey
    "life_journey_action": "life_journey",

    # ═══════════════════════════════════════════════════════════════════
    # FINANCE (NEW CATEGORY)
    # ═══════════════════════════════════════════════════════════════════
    "send_bch": "finance",                         # Sun tool
    "validate_transaction": "transaction_mastery",
    "optimize_fees": "fee_optimization",
    "track_transaction": "transaction_tracking",
    "check_wallet_health": "wallet_management",
    "monitor_balance": "balance_monitoring",
    "multisig_action": "multisig_operations",
    "get_market_data": "market_awareness",
    "set_price_alert": "price_alerts",
    "analyze_market_trend": "market_trend_analysis",
    "plan_savings": "savings_strategies",
    "setup_dca": "dollar_cost_averaging",
    "identify_token": "token_knowledge",
    "manage_cashtokens": "cashtoken_operations",
}


def analyze_research_topic(query: str, url: str = None) -> str:
    """
    Analyze a search query or URL to determine which skill should receive XP.
    Returns skill_id for intelligent routing.

    Uses keyword matching to categorize research topics into Sun-level categories.

    Args:
        query: Search query text
        url: URL being visited (optional)

    Returns:
        skill_id of the Sun-level category
    """
    text = f"{query or ''} {url or ''}".lower()

    # Keyword patterns mapped to Sun-level skills
    # Using word boundaries (\b) to ensure whole word matching
    patterns = {
        # Security & Privacy (check first - security terms are specific)
        "security_privacy": [
            r"\b(security|secure|encrypt\w*|decrypt\w*|hash|authenticat\w*)\b",
            r"\b(privacy|private|protect\w*|vulnerabil\w*|exploit\w*|attack)\b",
            r"\b(password|credential|certificate|ssl|tls)\b",
        ],

        # Coding (formerly Technical Expertise)
        "coding": [
            r"\b(python|javascript|typescript|react|code|programming|developer|api)\b",
            r"\b(function|class|method|variable|bug|error|debug|compile)\b",
            r"\b(git|github|repository|commit|merge|branch)\b",
            r"\b(deploy|docker|kubernetes|devops|ci/cd|infrastructure|cloud)\b",
            r"\b(architecture|microservice|system design|scalability|distributed)\b",
        ],

        # Finance (NEW) - check before memory_recall to avoid "fee" in unrelated words
        "finance": [
            r"\b(bitcoin|bch|crypto|cryptocurrency|blockchain|wallet)\b",
            r"\b(price|market|trading|exchange|transaction)\b",
            r"\b(token|nft|defi|stake|yield)\b",
            r"\bfee\b",  # Use explicit word boundary for fee
        ],

        # Memory & Recall (formerly Knowledge Domains)
        "memory_recall": [
            r"\b(history|historical|ancient|medieval|century|era|civilization)\b",
            r"\b(science|scientific|research|study|experiment|theory)\b",
            r"\b(philosophy|philosophical|ethics)\b",
            r"\b(math|mathematics|equation|formula|calculus|algebra)\b",
            r"\b(physics|quantum|mechanics|relativity|particle|energy)\b",
            r"\b(biology|chemistry|hypothesis)\b",
            r"\b(language|translation|spanish|french|chinese|grammar|linguistic)\b",
        ],

        # Creative Expression
        "creative_expression": [
            r"\b(art|design|creative|visual|graphic|color|composition)\b",
            r"\b(music|song|melody|harmony|composer|musician)\b",
            r"\b(writing|story|narrative|character|plot|fiction)\b",
        ],

        # Social Intelligence
        "social_intelligence": [
            r"\b(relationship|communication|emotion|empathy|social)\b",
            r"\b(persuasion|negotiation|conflict|trust|rapport)\b",
        ],

        # AI Reasoning
        "ai_reasoning": [
            r"\b(pattern|analysis|insight|learning)\b",
            r"\b(mistake|failure|success|growth|reflection)\b",
        ],

        # Board Games (formerly Games)
        "board_games": [
            r"\b(chess|strategy|tactics|opening|endgame)\b",
            r"\b(monopoly|clue|sorry)\b",
            r"\blife\s+game\b",
        ],
    }

    # Check each pattern
    for skill_id, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                return skill_id

    # Default to Memory & Recall (general knowledge)
    logger.debug(f"No specific skill match for query '{(query or '')[:50]}...', defaulting to memory_recall")
    return "memory_recall"


class SkillScanner:
    """
    Scans blocks at anchor time to detect skill usage and award XP

    Analyzes tool usage and intelligently maps to appropriate skills based on context.
    """

    def __init__(self, qube):
        """
        Initialize skill scanner

        Args:
            qube: Qube instance with reasoner access
        """
        self.qube = qube

    async def scan_blocks_for_skills(self, blocks: List[Any]) -> Dict[str, Any]:
        """
        Scan session blocks for skill demonstrations BEFORE encryption

        Looks for ACTION blocks and awards XP based on which tools were used.
        Called during anchoring before blocks are encrypted.

        Args:
            blocks: List of unencrypted Block objects (session blocks)

        Returns:
            Dict with skill_detections: [{"skill_id": str, "xp_amount": float, "evidence": str, "block_number": int}]
        """
        if not blocks:
            return {"skill_detections": []}

        try:
            # Scan ACTION blocks for tool usage
            skill_detections = []

            for block in blocks:
                # Get block type
                block_type = block.block_type if isinstance(block.block_type, str) else block.block_type.value
                logger.info(f"[SKILL_SCANNER] Processing block {block.block_number}, type={block_type}")

                # Process ACTION blocks for tool usage
                if block_type == "ACTION":
                    # Get content (should already be unencrypted session blocks)
                    content = block.content
                    logger.info(f"[SKILL_SCANNER] ACTION block content type: {type(content)}, is_dict: {isinstance(content, dict)}")
                    if not content or not isinstance(content, dict):
                        logger.warning(f"[SKILL_SCANNER] Skipping block {block.block_number}: content is not a dict (type={type(content)})")
                        continue

                    # Extract action_type (maps to tool name)
                    action_type = content.get("action_type")
                    logger.info(f"[SKILL_SCANNER] action_type={action_type}")
                    if not action_type:
                        logger.warning(f"[SKILL_SCANNER] Skipping block {block.block_number}: no action_type in content")
                        continue

                    # Determine skill_id based on tool type and content
                    skill_id = None

                    # For research tools (web_search, browse_url), analyze the query/URL
                    if action_type == "web_search":
                        params = content.get("parameters", {})
                        query = params.get("query", "")
                        skill_id = analyze_research_topic(query)
                        logger.debug(
                            f"[SKILL_SCANNER] Analyzed web_search query '{query[:50]}...' → {skill_id}",
                            tool=action_type,
                            query=query[:100],
                            skill=skill_id
                        )
                    elif action_type == "browse_url":
                        params = content.get("parameters", {})
                        url = params.get("url", "")
                        # Extract domain/path for analysis
                        skill_id = analyze_research_topic("", url)
                        logger.debug(
                            f"[SKILL_SCANNER] Analyzed browse_url '{url}' → {skill_id}",
                            tool=action_type,
                            url=url,
                            skill=skill_id
                        )
                    elif action_type == "process_document":
                        # Document processing always goes to knowledge_domains (research)
                        skill_id = "knowledge_domains"
                        logger.debug(
                            f"[SKILL_SCANNER] process_document → {skill_id}",
                            tool=action_type,
                            skill=skill_id
                        )
                    elif action_type in TOOL_TO_SKILL_MAPPING:
                        # Use hardcoded mapping for other tools
                        skill_id = TOOL_TO_SKILL_MAPPING[action_type]
                    else:
                        # Not a tracked tool, skip
                        logger.debug(
                            f"[SKILL_SCANNER] Tool '{action_type}' not mapped to any skill",
                            tool=action_type,
                            block=block.block_number
                        )
                        continue

                    # Determine XP based on success/failure
                    status = content.get("status", "unknown")
                    result = content.get("result", {})

                    # Custom XP calculation for process_document
                    if action_type == "process_document":
                        if status == "completed" and isinstance(result, dict) and result.get("success", False):
                            # Use custom formula based on file size and page count
                            params = content.get("parameters", {})
                            file_size_bytes = params.get("file_size_bytes", 0)
                            page_count = result.get("page_count", 0)

                            xp_amount = calculate_document_xp(file_size_bytes, page_count)
                            evidence = f"Processed document: {page_count} pages, {file_size_bytes / 1024 / 1024:.1f} MB"

                            logger.info(
                                "document_xp_calculated_during_anchor",
                                file_size_bytes=file_size_bytes,
                                page_count=page_count,
                                xp_amount=xp_amount
                            )
                        elif status == "completed":
                            # Partial extraction - minimum XP
                            xp_amount = 1
                            evidence = f"Attempted to process document (partial extraction)"
                        else:
                            # Failed - no XP
                            xp_amount = 0
                            continue  # Skip failed extractions
                    elif status == "completed" and isinstance(result, dict) and result.get("success", False):
                        # Check for "no-op" results where the tool succeeded but didn't actually do anything
                        # These shouldn't award XP since no real action was taken
                        if result.get("already_on_model"):
                            # switch_model called but already on that model - no XP
                            logger.debug(
                                f"[SKILL_SCANNER] switch_model no-op (already on model), skipping XP",
                                tool=action_type,
                                block=block.block_number
                            )
                            continue
                        # Successful use: +5 XP
                        xp_amount = 5
                        evidence = f"Successfully used {action_type} tool"
                    elif status == "completed":
                        # Completed but may have had issues: +2 XP
                        xp_amount = 2
                        evidence = f"Used {action_type} tool"
                    else:
                        # Failed or error: no XP (prevents gaming)
                        continue

                    # Extract detailed parameters for skill_history
                    params = content.get("parameters", {})
                    tool_details = {}

                    if action_type == "web_search":
                        tool_details["query"] = params.get("query", "")
                    elif action_type == "browse_url":
                        tool_details["url"] = params.get("url", "")
                    elif action_type == "generate_image":
                        tool_details["prompt"] = params.get("prompt", "")
                        # Check if result has image URL
                        if isinstance(result, dict) and "image_url" in result:
                            tool_details["image_url"] = result.get("image_url")
                    # AI Reasoning tools (Learning From Experience)
                    elif action_type in ["recall_similar", "find_analogy", "quick_insight"]:
                        tool_details["situation"] = params.get("situation", params.get("context", ""))
                    elif action_type in ["analyze_mistake", "replicate_success"]:
                        tool_details["topic"] = params.get("topic", params.get("goal", ""))
                    elif action_type == "self_reflect":
                        tool_details["topic"] = params.get("topic", "")
                    elif action_type == "synthesize_learnings":
                        tool_details["topics"] = params.get("topics", [])
                    # Social Intelligence tools
                    elif action_type in ["get_relationship_context", "recall_relationship_history",
                                        "analyze_interaction_patterns", "get_relationship_timeline",
                                        "read_emotional_state", "track_emotional_patterns",
                                        "detect_mood_shift", "assess_trust_level"]:
                        tool_details["entity_id"] = params.get("entity_id", "")
                    elif action_type in ["adapt_communication_style", "calibrate_tone"]:
                        tool_details["entity_id"] = params.get("entity_id", "")
                        tool_details["context"] = params.get("context", params.get("message_type", ""))
                    elif action_type == "match_communication_style":
                        tool_details["their_message"] = params.get("their_message", "")[:100]
                    elif action_type in ["steelman", "devils_advocate", "spot_fallacy"]:
                        tool_details["argument"] = params.get("argument", params.get("position", ""))[:100]
                    elif action_type == "detect_social_manipulation":
                        tool_details["message"] = params.get("message", "")[:100]
                    elif action_type == "evaluate_request":
                        tool_details["request"] = params.get("request", "")[:100]
                    elif action_type == "debug_systematically":
                        tool_details["problem"] = params.get("problem", "")[:100]
                    elif action_type in ["research_with_synthesis", "deep_research"]:
                        tool_details["topic"] = params.get("topic", "")
                    elif action_type == "explain_like_im_five":
                        tool_details["concept"] = params.get("concept", "")
                    # Creative Expression tools (generate_image handled above)
                    elif action_type in ["refine_composition", "apply_color_theory"]:
                        tool_details["description"] = params.get("description", params.get("image_url", ""))[:100]
                    elif action_type in ["compose_text", "craft_prose", "write_poetry"]:
                        tool_details["topic"] = params.get("topic", params.get("theme", ""))[:100]
                    elif action_type in ["compose_music", "create_melody", "design_harmony"]:
                        tool_details["style"] = params.get("style", params.get("mood", ""))[:50]
                    elif action_type in ["craft_narrative", "develop_plot", "design_character", "build_world"]:
                        tool_details["concept"] = params.get("concept", params.get("description", ""))[:100]
                    elif action_type in ["describe_my_avatar", "define_personality"]:
                        tool_details["aspect"] = params.get("aspect", "")[:50]
                    elif action_type in ["change_favorite_color", "change_voice", "set_aspirations"]:
                        tool_details["value"] = params.get("value", params.get("color", params.get("voice", "")))[:50]
                    # Add more as needed...

                    detection_entry = {
                        "skill_id": skill_id,  # Use mapped skill_id, not tool name
                        "xp_amount": xp_amount,
                        "evidence": evidence,
                        "block_number": block.block_number,
                        "tool_used": action_type,  # Track which tool was used
                    }

                    # Add tool-specific details if any were extracted
                    if tool_details:
                        detection_entry["tool_details"] = tool_details

                    skill_detections.append(detection_entry)

                    logger.info(
                        f"[SKILL_SCANNER] ✅ DETECTED: skill={skill_id}, tool={action_type}, xp={xp_amount}, block={block.block_number}"
                    )

                # Process MESSAGE blocks for social intelligence skills
                elif block_type == "MESSAGE":
                    content = block.content
                    if not content or not isinstance(content, dict):
                        continue

                    # Extract message text
                    message_text = content.get("message", "").lower()
                    sender = content.get("sender", "unknown")

                    if not message_text:
                        continue

                    # Analyze message for social intelligence indicators
                    social_detections = []

                    # Empathy indicators: emotional language, understanding
                    if re.search(r'\b(feel|feeling|understand|sorry|glad|happy|sad|upset|excited|worried)\b', message_text):
                        social_detections.append({
                            "skill_id": "empathy",  # social_intelligence → empathy planet
                            "xp_amount": 1,
                            "evidence": f"Demonstrated empathy in conversation",
                            "block_number": block.block_number,
                            "tool_used": "conversation",
                            "tool_details": {
                                "message_preview": message_text[:100],
                                "sender": sender,
                                "indicator": "emotional_language"
                            }
                        })

                    # Communication indicators: questions, explanations
                    if re.search(r'\b(what|why|how|when|where|who|explain|because|let me|here\'s why)\b', message_text):
                        social_detections.append({
                            "skill_id": "communication",  # social_intelligence → communication planet
                            "xp_amount": 1,
                            "evidence": f"Engaged in active communication",
                            "block_number": block.block_number,
                            "tool_used": "conversation",
                            "tool_details": {
                                "message_preview": message_text[:100],
                                "sender": sender,
                                "indicator": "questions_or_explanations"
                            }
                        })

                    # Relationship building: greetings, appreciation, collaboration
                    if re.search(r'\b(thanks|thank you|appreciate|great job|well done|let\'s|we can|together)\b', message_text):
                        social_detections.append({
                            "skill_id": "relationship_building",  # social_intelligence → relationship_building planet
                            "xp_amount": 1,
                            "evidence": f"Demonstrated relationship building",
                            "block_number": block.block_number,
                            "tool_used": "conversation",
                            "tool_details": {
                                "message_preview": message_text[:100],
                                "sender": sender,
                                "indicator": "appreciation_or_collaboration"
                            }
                        })

                    # Add social detections to main list
                    skill_detections.extend(social_detections)

                    if social_detections:
                        logger.debug(
                            f"[SKILL_SCANNER] Detected social skills in MESSAGE",
                            skills_detected=len(social_detections),
                            block=block.block_number
                        )

            if not skill_detections:
                logger.debug("[SKILL_SCANNER] No tools mapped to skills used in ACTION blocks")
                return {"skill_detections": []}

            logger.info(
                "[SKILL_SCANNER] Scan complete",
                action_blocks_scanned=len([b for b in blocks if (b.block_type if isinstance(b.block_type, str) else b.block_type.value) == "ACTION"]),
                skills_detected=len(skill_detections)
            )

            return {"skill_detections": skill_detections}

        except Exception as e:
            logger.error(f"[SKILL_SCANNER] Scan failed: {e}", exc_info=True)
            return {"skill_detections": []}

    async def apply_skill_xp(self, skill_detections: List[Dict[str, Any]], block_numbers: List[int]) -> int:
        """
        NO-OP: XP is now awarded during session by registry.py's _award_xp_for_action_block.

        This method is kept to avoid breaking call sites. XP was already awarded
        during the session and persists when anchored. If session is discarded,
        the XP rolls back with the session.

        Args:
            skill_detections: List of {"skill_id": str, "xp_amount": float, "evidence": str}
            block_numbers: List of block numbers that were scanned (for evidence)

        Returns:
            0 (no additional XP awarded at anchor time)
        """
        # XP already awarded during session - don't double-count
        logger.info(f"[SKILL_SCANNER] Skipping anchor-time XP (already awarded during session): {len(skill_detections)} detections")
        return 0

    async def _apply_skill_xp_DISABLED(self, skill_detections: List[Dict[str, Any]], block_numbers: List[int]) -> int:
        """
        DISABLED: Original implementation kept for reference.
        """
        if not skill_detections:
            return 0

        try:
            # Use the qube's existing skills_manager (which uses ChainState)
            skills_manager = self.qube.skills_manager
            skill_definitions = skills_manager._get_skill_definitions()
            skills_gained = 0

            for detection in skill_detections:
                skill_id = detection.get("skill_id")
                xp_amount = detection.get("xp_amount", 1)
                evidence = detection.get("evidence", "")
                block_number = detection.get("block_number")
                tool_details = detection.get("tool_details")  # Extract tool_details

                if not skill_id:
                    continue

                # Use specific block number if available, otherwise use range
                if block_number is not None:
                    evidence_block_id = f"block_{block_number}"
                elif block_numbers:
                    evidence_block_id = f"blocks_{min(block_numbers)}-{max(block_numbers)}"
                else:
                    evidence_block_id = "unknown"

                # Add XP to the skill with detailed tool information
                result = skills_manager.add_xp(
                    skill_id=skill_id,
                    xp_amount=xp_amount,
                    evidence_block_id=evidence_block_id,
                    evidence_description=evidence,
                    tool_details=tool_details  # Pass tool_details
                )

                skills_gained += 1
                logger.debug(
                    f"[SKILL_SCANNER] Awarded XP",
                    skill_id=skill_id,
                    xp_amount=xp_amount,
                    evidence=evidence[:50]
                )

                # Emit celebration event for frontend
                if result.get("success") and hasattr(self.qube, 'events'):
                    # Get skill definition for name, icon, category
                    actual_skill_id = result.get("skill_id", skill_id)
                    skill_def = skill_definitions.get(actual_skill_id, {})
                    category = skill_def.get("category", "unknown")

                    # Build celebration payload
                    celebration_payload = {
                        "skill_id": actual_skill_id,
                        "skill_name": skill_def.get("name", actual_skill_id),
                        "skill_icon": skill_def.get("icon", "⭐"),
                        "category": category,
                        "category_color": CATEGORY_COLORS.get(category, "#888888"),
                        "node_type": skill_def.get("nodeType", "planet"),
                        "xp_amount": result.get("xp_gained", xp_amount),
                        "new_xp": result.get("current_xp", 0),
                        "max_xp": result.get("max_xp", 500),
                        "previous_level": result.get("old_level", 0),
                        "new_level": result.get("new_level", 0),
                        "leveled_up": result.get("leveled_up", False),
                        "levels_gained": result.get("levels_gained", 0),
                        "maxed_out": result.get("new_level", 0) >= 100,
                        "tool_unlocked": result.get("tool_unlocked"),
                    }

                    # Emit XP gained event for celebrations
                    self.qube.events.emit(Events.XP_GAINED, celebration_payload)
                    logger.debug(f"[SKILL_SCANNER] Emitted XP_GAINED celebration event for {actual_skill_id}")

                    # Emit skill unlock event if a tool was unlocked (skill maxed)
                    if result.get("tool_unlocked"):
                        self.qube.events.emit(Events.SKILL_UNLOCKED, {
                            "skill_id": actual_skill_id,
                            "skill_name": skill_def.get("name", actual_skill_id),
                            "skill_icon": skill_def.get("icon", "⭐"),
                            "category": category,
                            "category_color": CATEGORY_COLORS.get(category, "#888888"),
                            "node_type": skill_def.get("nodeType", "planet"),
                            "tool_unlocked": result.get("tool_unlocked"),
                        })
                        logger.info(f"[SKILL_SCANNER] Emitted SKILL_UNLOCKED event for {actual_skill_id}")

            if skills_gained > 0:
                logger.info(
                    f"[SKILL_SCANNER] XP applied",
                    skills_affected=skills_gained,
                    total_xp=sum(d.get("xp_amount", 1) for d in skill_detections)
                )

            return skills_gained

        except Exception as e:
            logger.error(f"[SKILL_SCANNER] Failed to apply XP: {e}")
            return 0
