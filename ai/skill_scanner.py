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

logger = get_logger(__name__)


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
TOOL_TO_SKILL_MAPPING = {
    # Regular Tools
    "generate_image": "visual_design",           # creative_expression → visual_design planet
    "search_memory": "knowledge_domains",    # knowledge_domains → sun (general research)
    "describe_my_avatar": "analysis_critique",   # ai_reasoning → analysis_critique planet
    # Note: get_system_state and update_system_state are general-purpose tools, not skill-specific

    # AI Reasoning Tools
    "think_step_by_step": "chain_of_thought",    # ai_reasoning → chain_of_thought planet
    "self_critique": "analysis_critique",        # ai_reasoning → analysis_critique planet
    "explore_alternatives": "multistep_planning",# ai_reasoning → multistep_planning planet

    # Social Intelligence Tools
    "draft_message_variants": "communication",   # social_intelligence → communication planet
    "predict_reaction": "empathy",               # social_intelligence → empathy planet
    "build_rapport_strategy": "relationship_building", # social_intelligence → relationship_building planet

    # Technical Expertise Tools
    "debug_systematically": "debugging",         # technical_expertise → debugging planet
    "research_with_synthesis": "science",        # knowledge_domains → science planet
    "validate_solution": "debugging",            # technical_expertise → debugging planet

    # Creative Expression Tools
    "brainstorm_variants": "creative_problem_solving", # creative_expression → creative_problem_solving planet
    "iterate_design": "visual_design",           # creative_expression → visual_design planet
    "cross_pollinate_ideas": "creative_problem_solving", # creative_expression → creative_problem_solving planet

    # Knowledge Domains Tools
    "deep_research": "science",                  # knowledge_domains → science planet
    "synthesize_knowledge": "philosophy",        # knowledge_domains → philosophy planet
    "explain_like_im_five": "philosophy",        # knowledge_domains → philosophy planet

    # Security & Privacy Tools
    "assess_security_risks": "threat_analysis",  # security_privacy → threat_analysis planet
    "privacy_impact_analysis": "privacy_protection", # security_privacy → privacy_protection planet
    "verify_authenticity": "authentication",     # security_privacy → authentication planet

    # Games Tools
    "analyze_game_state": "chess",               # games → chess planet (as example game)
    "plan_strategy": "chess",                    # games → chess planet
    "learn_from_game": "chess",                  # games → chess planet
}


def analyze_research_topic(query: str, url: str = None) -> str:
    """
    Analyze a search query or URL to determine which skill it relates to

    Uses keyword matching to categorize research topics into appropriate skills.

    Args:
        query: Search query text
        url: URL being visited (optional)

    Returns:
        skill_id of the most appropriate skill
    """
    text = (query or "").lower()
    if url:
        text += " " + url.lower()

    # Keyword patterns for each skill category
    # Ordered by specificity (most specific first)

    # Security & Privacy
    if re.search(r'\b(crypto|bitcoin|blockchain|encryption|hash|security|privacy|authentication|password|ssl|tls)\b', text):
        return "cryptography"

    # Technical Expertise
    if re.search(r'\b(programming|code|python|javascript|java|developer|software|api|debug|algorithm)\b', text):
        return "programming"
    if re.search(r'\b(deploy|docker|kubernetes|devops|ci/cd|infrastructure|cloud)\b', text):
        return "devops"
    if re.search(r'\b(architecture|microservice|system design|scalability|distributed)\b', text):
        return "system_architecture"

    # Knowledge Domains - Science
    if re.search(r'\b(physics|quantum|mechanics|relativity|particle|energy|force)\b', text):
        return "science"
    if re.search(r'\b(biology|chemistry|scientific|experiment|research|hypothesis)\b', text):
        return "science"

    # Knowledge Domains - Math
    if re.search(r'\b(math|algebra|calculus|geometry|statistics|equation|formula)\b', text):
        return "mathematics"

    # Knowledge Domains - History
    if re.search(r'\b(history|historical|ancient|civilization|war|empire|dynasty)\b', text):
        return "history"

    # Knowledge Domains - Philosophy
    if re.search(r'\b(philosophy|ethics|logic|reasoning|metaphysics|epistemology)\b', text):
        return "philosophy"

    # Knowledge Domains - Languages
    if re.search(r'\b(language|translation|spanish|french|chinese|grammar|linguistic)\b', text):
        return "languages"

    # Creative Expression
    if re.search(r'\b(art|design|visual|graphic|color|composition|aesthetic)\b', text):
        return "visual_design"
    if re.search(r'\b(writing|author|novel|story|narrative|prose|poetry)\b', text):
        return "writing"
    if re.search(r'\b(music|song|melody|harmony|composer|instrument)\b', text):
        return "music"

    # Games
    if re.search(r'\b(chess|checkers|poker|game|strategy|tactics)\b', text):
        return "chess"

    # Default: knowledge_domains (general research)
    logger.debug(f"No specific skill match for query '{query[:50]}...', defaulting to knowledge_domains")
    return "knowledge_domains"


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
                        # Successful use: +3 XP
                        xp_amount = 3
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
                    elif action_type in ["think_step_by_step", "self_critique", "explore_alternatives"]:
                        tool_details["task"] = params.get("task", "")
                    elif action_type == "draft_message_variants":
                        tool_details["message"] = params.get("message", "")[:100]  # Truncate long messages
                    elif action_type == "debug_systematically":
                        tool_details["problem"] = params.get("problem", "")[:100]
                    elif action_type in ["research_with_synthesis", "deep_research"]:
                        tool_details["topic"] = params.get("topic", "")
                    elif action_type == "explain_like_im_five":
                        tool_details["concept"] = params.get("concept", "")
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
        Apply XP gains from skill detections to the qube's skills

        Args:
            skill_detections: List of {"skill_id": str, "xp_amount": float, "evidence": str}
            block_numbers: List of block numbers that were scanned (for evidence)

        Returns:
            Number of skills that gained XP
        """
        if not skill_detections:
            return 0

        try:
            # Use the qube's existing skills_manager (which uses ChainState)
            skills_manager = self.qube.skills_manager
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
                skills_manager.add_xp(
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
