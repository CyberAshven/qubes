"""
Skills Manager - Handles skill progression, XP tracking, and unlocking for Qubes

Storage Structure:
    data/users/{user_id}/qubes/{qube_id}/skills/
        skills.json - Current skill states (levels, XP, unlocked status)
        skill_history.json - Historical skill progression events

Skills System Design:
    - 3 tiers: Sun (major categories), Planet (specific skills), Moon (sub-skills)
    - 7 categories: AI Reasoning, Social Intelligence, Technical Expertise,
      Creative Expression, Knowledge Domains, Security & Privacy, Games
    - XP ranges: Sun (0-1000), Planet (0-500), Moon (0-250)
    - Levels: 1-100 with 4 tiers (novice, intermediate, advanced, expert)
    - Skills unlock based on prerequisites
    - Tool calls unlock when skills reach max level

Integration Points:
    - Blocks: Track which blocks contributed XP to which skills (evidence)
    - Relationships: Social skills progress based on relationship interactions
    - Tool Calls: New tools unlock when skills are maxed
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


# Skill category definitions
SKILL_CATEGORIES = [
    {"id": "ai_reasoning", "name": "AI Reasoning", "color": "#4A90E2", "icon": "🧠"},
    {"id": "social_intelligence", "name": "Social Intelligence", "color": "#FF69B4", "icon": "🤝"},
    {"id": "technical_expertise", "name": "Technical Expertise", "color": "#00FF88", "icon": "💻"},
    {"id": "creative_expression", "name": "Creative Expression", "color": "#FFB347", "icon": "🎨"},
    {"id": "knowledge_domains", "name": "Knowledge Domains", "color": "#9B59B6", "icon": "📚"},
    {"id": "security_privacy", "name": "Security & Privacy", "color": "#E74C3C", "icon": "🛡️"},
    {"id": "games", "name": "Games", "color": "#F39C12", "icon": "🎮"},
]


class SkillsManager:
    """Manages skill progression and persistence for a single Qube"""

    def __init__(self, qube_dir: Path):
        """
        Initialize SkillsManager for a specific qube

        Args:
            qube_dir: Path to qube's data directory
        """
        self.qube_dir = qube_dir
        self.skills_dir = qube_dir / "skills"
        self.skills_file = self.skills_dir / "skills.json"
        self.history_file = self.skills_dir / "skill_history.json"

        # Ensure skills directory exists
        self.skills_dir.mkdir(exist_ok=True)

    def load_skills(self) -> Dict[str, Any]:
        """
        Load current skill states from skills.json

        Returns:
            Dictionary containing skills data or default structure if file doesn't exist
        """
        if not self.skills_file.exists():
            logger.info(f"No skills file found at {self.skills_file}, initializing default skills")
            return self._initialize_default_skills()

        try:
            with open(self.skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded {len(data.get('skills', []))} skills from {self.skills_file}")
                return data
        except Exception as e:
            logger.error(f"Failed to load skills from {self.skills_file}: {e}")
            return self._initialize_default_skills()

    def save_skills(self, skills_data: Dict[str, Any]) -> bool:
        """
        Save skill states to skills.json

        Args:
            skills_data: Dictionary containing skills data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update last_updated timestamp
            skills_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

            with open(self.skills_file, 'w', encoding='utf-8') as f:
                json.dump(skills_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(skills_data.get('skills', []))} skills to {self.skills_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save skills to {self.skills_file}: {e}")
            return False

    def _initialize_default_skills(self) -> Dict[str, Any]:
        """
        Initialize default skill structure with all skills locked at level 0

        Generates the complete skill tree matching the frontend skillDefinitions.ts
        Structure: 7 categories, each with 1 sun + 5 planets + 10 moons

        Returns:
            Default skills data structure with all skills initialized
        """
        from utils.skill_definitions import generate_all_skills

        skills = generate_all_skills()

        default_skills = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "skills": skills
        }

        logger.info(f"Initialized {len(skills)} default skills")

        # Save the initialized skills to disk so they persist
        self.save_skills(default_skills)

        # Also initialize empty skill history file
        if not self.history_file.exists():
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"Initialized empty skill history at {self.history_file}")

        return default_skills

    def add_xp(self, skill_id: str, xp_amount: int, evidence_block_id: Optional[str] = None, evidence_description: Optional[str] = None, tool_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add XP to a specific skill and handle level-ups

        If the skill is locked, XP flows to the unlocked parent:
        - Locked moon → parent planet (if unlocked) → else parent sun (always unlocked)
        - Locked planet → parent sun (always unlocked)

        Args:
            skill_id: ID of the skill to add XP to
            xp_amount: Amount of XP to add
            evidence_block_id: Optional block ID that contributed this XP
            evidence_description: Optional description of how skill was demonstrated
            tool_details: Optional dict with tool-specific details (query, url, prompt, etc.)

        Returns:
            Dictionary with result including level_up status
        """
        skills_data = self.load_skills()

        # Find the skill
        skill = None
        for s in skills_data["skills"]:
            if s["id"] == skill_id:
                skill = s
                break

        if not skill:
            logger.warning(f"Skill {skill_id} not found")
            return {"success": False, "error": f"Skill {skill_id} not found"}

        # If skill is locked, flow XP to unlocked parent
        original_skill_id = skill_id
        xp_flowed_to_parent = False

        if not skill.get("unlocked", False):
            xp_flowed_to_parent = True  # Track that XP was redirected
            # Try parent skill first
            parent_id = skill.get("parentSkill")
            if parent_id:
                parent_skill = None
                for s in skills_data["skills"]:
                    if s["id"] == parent_id:
                        parent_skill = s
                        break

                if parent_skill:
                    if parent_skill.get("unlocked", False):
                        # Parent is unlocked, give XP to parent
                        skill = parent_skill
                        skill_id = parent_id
                        logger.info(f"Skill {original_skill_id} is locked, flowing XP to parent {skill_id}")
                    else:
                        # Parent also locked, try grandparent (should be sun, always unlocked)
                        grandparent_id = parent_skill.get("parentSkill")
                        if grandparent_id:
                            for s in skills_data["skills"]:
                                if s["id"] == grandparent_id:
                                    skill = s
                                    skill_id = grandparent_id
                                    logger.info(f"Skill {original_skill_id} and parent {parent_id} are locked, flowing XP to sun {skill_id}")
                                    break

        # Add XP
        old_xp = skill["xp"]
        old_level = skill["level"]
        skill["xp"] += xp_amount

        # Add evidence if provided
        if evidence_block_id:
            if "evidence" not in skill:
                skill["evidence"] = []

            # Store evidence as dict with optional description
            evidence_entry = {
                "block_id": evidence_block_id,
                "xp_gained": xp_amount,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            if evidence_description:
                evidence_entry["description"] = evidence_description

            skill["evidence"].append(evidence_entry)

        # Check for level-up
        max_xp = skill["maxXP"]
        leveled_up = False
        new_levels = 0

        while skill["xp"] >= max_xp and skill["level"] < 100:
            skill["xp"] -= max_xp
            skill["level"] += 1
            new_levels += 1
            leveled_up = True

            # Update tier based on level
            if skill["level"] >= 75:
                skill["tier"] = "expert"
            elif skill["level"] >= 50:
                skill["tier"] = "advanced"
            elif skill["level"] >= 25:
                skill["tier"] = "intermediate"
            else:
                skill["tier"] = "novice"

        # Cap at max level
        if skill["level"] >= 100:
            skill["level"] = 100
            skill["xp"] = max_xp

        # PROPAGATE XP TO CHILDREN: When a parent skill gains XP, children should too
        # This ensures Moon skills get XP when their parent Planet skill is used
        children_updated = []
        for child_skill in skills_data["skills"]:
            if child_skill.get("parentSkill") == skill_id:
                # Give child the same XP amount
                child_old_xp = child_skill["xp"]
                child_old_level = child_skill["level"]
                child_skill["xp"] += xp_amount

                # Check for child level-up
                child_max_xp = child_skill["maxXP"]
                child_leveled_up = False
                child_new_levels = 0

                while child_skill["xp"] >= child_max_xp and child_skill["level"] < 100:
                    child_skill["xp"] -= child_max_xp
                    child_skill["level"] += 1
                    child_new_levels += 1
                    child_leveled_up = True

                # Cap at max level
                if child_skill["level"] >= 100:
                    child_skill["level"] = 100
                    child_skill["xp"] = child_max_xp

                children_updated.append({
                    "skill_id": child_skill["id"],
                    "xp_gained": xp_amount,
                    "old_level": child_old_level,
                    "new_level": child_skill["level"],
                    "leveled_up": child_leveled_up
                })

                logger.debug(f"Propagated {xp_amount} XP to child skill {child_skill['id']}")

        # Save updated skills
        self.save_skills(skills_data)

        # Log to history
        event_data = {
            "event": "xp_gained",
            "skill_id": skill_id,
            "xp_amount": xp_amount,
            "old_xp": old_xp,
            "new_xp": skill["xp"],
            "old_level": old_level,
            "new_level": skill["level"],
            "leveled_up": leveled_up,
            "levels_gained": new_levels,
            "evidence_block_id": evidence_block_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Add original skill if XP flowed to parent
        if xp_flowed_to_parent:
            event_data["original_skill_id"] = original_skill_id
            event_data["xp_flowed_to_parent"] = True

        # Add description if provided
        if evidence_description:
            event_data["evidence_description"] = evidence_description

        # Add tool details if provided
        if tool_details:
            event_data["tool_details"] = tool_details

        # Include children in event data
        if children_updated:
            event_data["children_updated"] = children_updated

        self._log_skill_event(event_data)

        result = {
            "success": True,
            "skill_id": skill_id,
            "old_level": old_level,
            "new_level": skill["level"],
            "xp_gained": xp_amount,
            "current_xp": skill["xp"],
            "max_xp": max_xp,
            "leveled_up": leveled_up,
            "levels_gained": new_levels
        }

        # Include children that also received XP
        if children_updated:
            result["children_updated"] = children_updated
            logger.info(f"XP propagated to {len(children_updated)} child skill(s): {[c['skill_id'] for c in children_updated]}")

        # Check if skill is now maxed and should unlock a tool
        if skill["level"] == 100 and skill.get("toolCallReward"):
            result["tool_unlocked"] = skill["toolCallReward"]
            logger.info(f"Skill {skill_id} maxed! Unlocked tool: {skill['toolCallReward']}")

        return result

    def unlock_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Unlock a skill (check prerequisites first)

        Args:
            skill_id: ID of skill to unlock

        Returns:
            Dictionary with result
        """
        skills_data = self.load_skills()

        # Find the skill
        skill = None
        for s in skills_data["skills"]:
            if s["id"] == skill_id:
                skill = s
                break

        if not skill:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        if skill.get("unlocked", False):
            return {"success": False, "error": f"Skill {skill_id} is already unlocked"}

        # Check prerequisite
        if skill.get("prerequisite"):
            prereq_id = skill["prerequisite"]
            prereq_skill = None
            for s in skills_data["skills"]:
                if s["id"] == prereq_id:
                    prereq_skill = s
                    break

            if not prereq_skill or not prereq_skill.get("unlocked", False):
                return {
                    "success": False,
                    "error": f"Prerequisite skill {prereq_id} must be unlocked first"
                }

        # Unlock the skill
        skill["unlocked"] = True
        self.save_skills(skills_data)

        # Log event
        self._log_skill_event({
            "event": "skill_unlocked",
            "skill_id": skill_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        logger.info(f"Unlocked skill: {skill_id}")
        return {"success": True, "skill_id": skill_id}

    def get_skill_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all skills organized by category

        Returns:
            Dictionary with skill summary statistics
        """
        skills_data = self.load_skills()

        summary = {
            "total_skills": len(skills_data.get("skills", [])),
            "unlocked_skills": 0,
            "maxed_skills": 0,
            "total_xp": 0,
            "by_category": {},
            "unlocked_tools": []
        }

        for skill in skills_data.get("skills", []):
            # Count unlocked and maxed
            if skill.get("unlocked", False):
                summary["unlocked_skills"] += 1
            if skill.get("level", 0) == 100:
                summary["maxed_skills"] += 1
                if skill.get("toolCallReward"):
                    summary["unlocked_tools"].append(skill["toolCallReward"])

            # Sum XP
            summary["total_xp"] += skill.get("xp", 0)

            # Organize by category
            category_id = skill.get("category", "unknown")
            if category_id not in summary["by_category"]:
                summary["by_category"][category_id] = {
                    "total": 0,
                    "unlocked": 0,
                    "maxed": 0,
                    "avg_level": 0.0
                }

            cat = summary["by_category"][category_id]
            cat["total"] += 1
            if skill.get("unlocked", False):
                cat["unlocked"] += 1
            if skill.get("level", 0) == 100:
                cat["maxed"] += 1

        # Calculate average levels
        for category_id, cat in summary["by_category"].items():
            if cat["total"] > 0:
                total_levels = sum(
                    s.get("level", 0)
                    for s in skills_data.get("skills", [])
                    if s.get("category") == category_id
                )
                cat["avg_level"] = total_levels / cat["total"]

        return summary

    def _log_skill_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log a skill event to history file

        Args:
            event_data: Event data to log
        """
        try:
            # Load existing history
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            # Append new event
            history.append(event_data)

            # Keep only last 1000 events to prevent file bloat
            if len(history) > 1000:
                history = history[-1000:]

            # Save history
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to log skill event: {e}")
