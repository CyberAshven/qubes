"""
Skills Manager - Handles skill progression, XP tracking, and unlocking for Qubes

UPDATED FOR COMPACT STORAGE:
- Only stores skills that have XP > 0 or are unlocked beyond defaults
- Skill definitions loaded from skill_definitions.py at runtime
- Significantly reduces chain_state size

Storage Structure (within chain_state.json):
    skills: {
        skill_xp: {skill_id: {xp: float, level: int}, ...},  # Only skills with XP
        extra_unlocked: [skill_id, ...],  # Skills unlocked beyond defaults (suns are default unlocked)
        history: [...],  # Capped at 100 entries
        total_xp: float,
        last_xp_gain: timestamp or null
    }

Skills System Design:
    - 3 tiers: Sun (major categories), Planet (specific skills), Moon (sub-skills)
    - 8 categories: AI Reasoning, Social Intelligence, Technical Expertise,
      Creative Expression, Knowledge Domains, Security & Privacy, Board Games, Finance
    - XP ranges: Sun (0-1000), Planet (0-500), Moon (0-250)
    - Levels: 1-100 with 4 tiers (novice, intermediate, advanced, expert)
    - Skills unlock based on prerequisites
    - Tool calls unlock when skills reach max level
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime
import structlog

if TYPE_CHECKING:
    from core.chain_state import ChainState

logger = structlog.get_logger(__name__)

# Maximum skill history entries to retain
MAX_SKILL_HISTORY = 100


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
    """
    Manages skill progression and persistence for a single Qube.

    Uses compact storage format - only stores skills with XP gained.
    Skill definitions are loaded from skill_definitions.py at runtime.
    """

    def __init__(self, chain_state: "ChainState"):
        """
        Initialize SkillsManager for a specific qube.

        Args:
            chain_state: ChainState instance for this qube
        """
        self.chain_state = chain_state
        self._skill_definitions_cache = None

    def _get_skill_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get skill definitions from skill_definitions.py (cached).

        Returns:
            Dict mapping skill_id -> skill definition
        """
        if self._skill_definitions_cache is None:
            from utils.skill_definitions import generate_all_skills
            skills_list = generate_all_skills()
            self._skill_definitions_cache = {s["id"]: s for s in skills_list}
        return self._skill_definitions_cache

    def _get_compact_skills_data(self) -> Dict[str, Any]:
        """
        Get the compact skills data from chain_state.

        Returns:
            Dict with skill_xp, extra_unlocked, history, total_xp, last_xp_gain
        """
        skills_section = self.chain_state.state.get("skills", {})

        # Handle migration from old format (has "skills" array)
        if "skills" in skills_section and isinstance(skills_section.get("skills"), list):
            return self._migrate_from_old_format(skills_section)

        # Return compact format with defaults
        return {
            "skill_xp": skills_section.get("skill_xp", {}),
            "extra_unlocked": skills_section.get("extra_unlocked", []),
            "history": skills_section.get("history", []),
            "total_xp": skills_section.get("total_xp", 0),
            "last_xp_gain": skills_section.get("last_xp_gain", None)
        }

    def _migrate_from_old_format(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from old format (full skill tree) to compact format.

        Args:
            old_data: Old skills data with "skills" array

        Returns:
            Compact format data
        """
        logger.info("Migrating skills from old format to compact format")

        skill_definitions = self._get_skill_definitions()
        skill_xp = {}
        extra_unlocked = []
        total_xp = 0

        for skill in old_data.get("skills", []):
            skill_id = skill.get("id")
            if not skill_id:
                continue

            xp = skill.get("xp", 0)
            level = skill.get("level", 0)
            unlocked = skill.get("unlocked", False)

            # Get default unlocked state from definitions
            default_def = skill_definitions.get(skill_id, {})
            default_unlocked = default_def.get("unlocked", False)

            # Store XP if > 0 or level > 0
            if xp > 0 or level > 0:
                skill_xp[skill_id] = {"xp": xp, "level": level}
                total_xp += xp

            # Store unlocked if different from default
            if unlocked and not default_unlocked:
                extra_unlocked.append(skill_id)

        compact_data = {
            "skill_xp": skill_xp,
            "extra_unlocked": extra_unlocked,
            "history": old_data.get("history", [])[-MAX_SKILL_HISTORY:],
            "total_xp": total_xp,
            "last_xp_gain": old_data.get("last_updated")
        }

        # Save migrated data
        self.chain_state.state["skills"] = compact_data
        self.chain_state._save()

        logger.info(f"Migrated to compact format: {len(skill_xp)} skills with XP, {len(extra_unlocked)} extra unlocked")
        return compact_data

    def _save_compact_data(self, data: Dict[str, Any]) -> bool:
        """
        Save compact skills data to chain_state.

        Also writes to unencrypted skills_cache.json for GUI access.

        Args:
            data: Compact skills data

        Returns:
            True if successful
        """
        try:
            self.chain_state.state["skills"] = data
            self.chain_state._save()

            # Also write to unencrypted cache for GUI access
            self._write_skills_cache(data)

            return True
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")
            return False

    def _write_skills_cache(self, data: Dict[str, Any]) -> None:
        """
        Write skills data to unencrypted cache file for GUI access.

        The cache file is stored alongside chain_state.json.

        Args:
            data: Compact skills data to cache
        """
        try:
            cache_file = self.chain_state.data_dir / "skills_cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Wrote skills cache to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to write skills cache: {e}")

    def load_skills(self) -> Dict[str, Any]:
        """
        Load current skill states, merging compact storage with definitions.

        Also updates the skills cache file for GUI access.

        Returns:
            Dictionary containing full skills data for compatibility
        """
        compact_data = self._get_compact_skills_data()
        skill_definitions = self._get_skill_definitions()

        # Update cache for GUI access (sync from chain_state)
        self._write_skills_cache(compact_data)

        # Build full skill list by merging definitions with stored XP
        skills_list = []
        for skill_id, definition in skill_definitions.items():
            skill = definition.copy()

            # Apply stored XP/level
            if skill_id in compact_data["skill_xp"]:
                stored = compact_data["skill_xp"][skill_id]
                skill["xp"] = stored.get("xp", 0)
                skill["level"] = stored.get("level", 0)
                # Update tier based on level
                if skill["level"] >= 75:
                    skill["tier"] = "expert"
                elif skill["level"] >= 50:
                    skill["tier"] = "advanced"
                elif skill["level"] >= 25:
                    skill["tier"] = "intermediate"
                else:
                    skill["tier"] = "novice"

            # Apply extra unlocked status
            if skill_id in compact_data["extra_unlocked"]:
                skill["unlocked"] = True

            skills_list.append(skill)

        return {
            "skills": skills_list,
            "history": compact_data["history"],
            "last_updated": compact_data["last_xp_gain"],
            "total_xp": compact_data["total_xp"]
        }

    def save_skills(self, skills_data: Dict[str, Any]) -> bool:
        """
        Save skill states to chain_state in compact format.

        Args:
            skills_data: Dictionary containing skills data (full format)

        Returns:
            True if successful, False otherwise
        """
        try:
            skill_definitions = self._get_skill_definitions()
            skill_xp = {}
            extra_unlocked = []
            total_xp = 0

            for skill in skills_data.get("skills", []):
                skill_id = skill.get("id")
                if not skill_id:
                    continue

                xp = skill.get("xp", 0)
                level = skill.get("level", 0)
                unlocked = skill.get("unlocked", False)

                # Get default unlocked state
                default_def = skill_definitions.get(skill_id, {})
                default_unlocked = default_def.get("unlocked", False)

                # Store XP if > 0 or level > 0
                if xp > 0 or level > 0:
                    skill_xp[skill_id] = {"xp": xp, "level": level}
                    total_xp += xp

                # Store unlocked if different from default
                if unlocked and not default_unlocked:
                    if skill_id not in extra_unlocked:
                        extra_unlocked.append(skill_id)

            compact_data = {
                "skill_xp": skill_xp,
                "extra_unlocked": extra_unlocked,
                "history": skills_data.get("history", [])[-MAX_SKILL_HISTORY:],
                "total_xp": total_xp,
                "last_xp_gain": datetime.utcnow().isoformat() + "Z"
            }

            return self._save_compact_data(compact_data)

        except Exception as e:
            logger.error(f"Failed to save skills: {e}")
            return False

    def _initialize_default_skills(self) -> Dict[str, Any]:
        """
        Initialize default skill structure (empty compact format).

        Returns:
            Default skills data structure
        """
        default_data = {
            "skill_xp": {},
            "extra_unlocked": [],
            "history": [],
            "total_xp": 0,
            "last_xp_gain": None
        }

        self._save_compact_data(default_data)
        logger.info("Initialized empty skills (compact format)")

        return default_data

    def add_xp(
        self,
        skill_id: str,
        xp_amount: float,
        evidence_block_id: Optional[str] = None,
        evidence_description: Optional[str] = None,
        tool_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add XP to a specific skill and handle level-ups.

        If the skill is locked, XP flows to the unlocked parent.

        Args:
            skill_id: ID of the skill to add XP to
            xp_amount: Amount of XP to add (supports decimals, e.g., 0.1)
            evidence_block_id: Optional block ID that contributed this XP
            evidence_description: Optional description of how skill was demonstrated
            tool_details: Optional dict with tool-specific details

        Returns:
            Dictionary with result including level_up status
        """
        compact_data = self._get_compact_skills_data()
        skill_definitions = self._get_skill_definitions()

        # Find the skill definition
        if skill_id not in skill_definitions:
            logger.warning(f"Skill {skill_id} not found")
            return {"success": False, "error": f"Skill {skill_id} not found"}

        skill_def = skill_definitions[skill_id]

        # Check if skill is unlocked (default or extra)
        is_unlocked = skill_def.get("unlocked", False) or skill_id in compact_data["extra_unlocked"]

        # If skill is locked, flow XP to unlocked parent
        original_skill_id = skill_id
        xp_flowed_to_parent = False

        if not is_unlocked:
            xp_flowed_to_parent = True
            parent_id = skill_def.get("parentSkill")
            if parent_id and parent_id in skill_definitions:
                parent_def = skill_definitions[parent_id]
                parent_unlocked = parent_def.get("unlocked", False) or parent_id in compact_data["extra_unlocked"]

                if parent_unlocked:
                    skill_id = parent_id
                    skill_def = parent_def
                    logger.info(f"Skill {original_skill_id} is locked, flowing XP to parent {skill_id}")
                else:
                    # Try grandparent (sun)
                    grandparent_id = parent_def.get("parentSkill")
                    if grandparent_id and grandparent_id in skill_definitions:
                        skill_id = grandparent_id
                        skill_def = skill_definitions[grandparent_id]
                        logger.info(f"Skill {original_skill_id} and parent locked, flowing to sun {skill_id}")

        # Get current XP/level for target skill
        current = compact_data["skill_xp"].get(skill_id, {"xp": 0, "level": 0})
        old_xp = current["xp"]
        old_level = current["level"]

        # Add XP
        new_xp = old_xp + xp_amount
        new_level = old_level
        max_xp = skill_def["maxXP"]
        leveled_up = False
        new_levels = 0

        # Check for level-up
        while new_xp >= max_xp and new_level < 100:
            new_xp -= max_xp
            new_level += 1
            new_levels += 1
            leveled_up = True

        # Cap at max level
        if new_level >= 100:
            new_level = 100
            new_xp = max_xp

        # Update stored XP
        compact_data["skill_xp"][skill_id] = {"xp": new_xp, "level": new_level}
        compact_data["total_xp"] += xp_amount

        # Save updated data
        compact_data["last_xp_gain"] = datetime.utcnow().isoformat() + "Z"

        # DEBUG: Log XP addition before save
        logger.info(
            f"[DEBUG] skills_manager.add_xp BEFORE save: skill={skill_id}, xp_amount={xp_amount}, "
            f"total_xp={compact_data['total_xp']}, skill_xp_keys={list(compact_data['skill_xp'].keys())}"
        )

        self._save_compact_data(compact_data)

        # DEBUG: Verify state after save
        logger.info(
            f"[DEBUG] skills_manager.add_xp AFTER save: chain_state skills total_xp={self.chain_state.state.get('skills', {}).get('total_xp', 0)}"
        )

        # Log to history
        event_data = {
            "event": "xp_gained",
            "skill_id": skill_id,
            "xp_amount": xp_amount,
            "old_xp": old_xp,
            "new_xp": new_xp,
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "levels_gained": new_levels,
            "evidence_block_id": evidence_block_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if xp_flowed_to_parent:
            event_data["original_skill_id"] = original_skill_id
            event_data["xp_flowed_to_parent"] = True

        if evidence_description:
            event_data["evidence_description"] = evidence_description

        if tool_details:
            event_data["tool_details"] = tool_details

        self._log_skill_event(event_data)

        result = {
            "success": True,
            "skill_id": skill_id,
            "old_level": old_level,
            "new_level": new_level,
            "xp_gained": xp_amount,
            "current_xp": new_xp,
            "max_xp": max_xp,
            "leveled_up": leveled_up,
            "levels_gained": new_levels
        }

        if new_level == 100 and skill_def.get("toolCallReward"):
            result["tool_unlocked"] = skill_def["toolCallReward"]
            logger.info(f"Skill {skill_id} maxed! Unlocked tool: {skill_def['toolCallReward']}")

        return result

    def unlock_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Unlock a skill (check prerequisites first).

        Args:
            skill_id: ID of skill to unlock

        Returns:
            Dictionary with result
        """
        compact_data = self._get_compact_skills_data()
        skill_definitions = self._get_skill_definitions()

        if skill_id not in skill_definitions:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        skill_def = skill_definitions[skill_id]

        # Check if already unlocked
        is_unlocked = skill_def.get("unlocked", False) or skill_id in compact_data["extra_unlocked"]
        if is_unlocked:
            return {"success": False, "error": f"Skill {skill_id} is already unlocked"}

        # Check prerequisite
        prereq_id = skill_def.get("prerequisite")
        if prereq_id:
            prereq_def = skill_definitions.get(prereq_id, {})
            prereq_unlocked = prereq_def.get("unlocked", False) or prereq_id in compact_data["extra_unlocked"]
            if not prereq_unlocked:
                return {"success": False, "error": f"Prerequisite skill {prereq_id} must be unlocked first"}

        # Unlock the skill
        if skill_id not in compact_data["extra_unlocked"]:
            compact_data["extra_unlocked"].append(skill_id)
        self._save_compact_data(compact_data)

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
        Get a summary of all skills organized by category.

        Returns:
            Dictionary with skill summary statistics
        """
        compact_data = self._get_compact_skills_data()
        skill_definitions = self._get_skill_definitions()

        summary = {
            "total_skills": len(skill_definitions),
            "unlocked_skills": 0,
            "maxed_skills": 0,
            "total_xp": compact_data["total_xp"],
            "by_category": {},
            "unlocked_tools": []
        }

        for skill_id, skill_def in skill_definitions.items():
            # Check unlocked status
            is_unlocked = skill_def.get("unlocked", False) or skill_id in compact_data["extra_unlocked"]
            if is_unlocked:
                summary["unlocked_skills"] += 1

            # Get level from stored data
            stored = compact_data["skill_xp"].get(skill_id, {})
            level = stored.get("level", 0)

            if level == 100:
                summary["maxed_skills"] += 1
                if skill_def.get("toolCallReward"):
                    summary["unlocked_tools"].append(skill_def["toolCallReward"])

            # Category stats
            category_id = skill_def.get("category", "unknown")
            if category_id not in summary["by_category"]:
                summary["by_category"][category_id] = {
                    "total": 0,
                    "unlocked": 0,
                    "maxed": 0,
                    "total_xp": 0
                }

            cat = summary["by_category"][category_id]
            cat["total"] += 1
            if is_unlocked:
                cat["unlocked"] += 1
            if level == 100:
                cat["maxed"] += 1
            cat["total_xp"] += stored.get("xp", 0)

        return summary

    def _log_skill_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log a skill event to history (capped at MAX_SKILL_HISTORY).

        Args:
            event_data: Event data to log
        """
        try:
            compact_data = self._get_compact_skills_data()
            history = compact_data.get("history", [])

            # Append new event
            history.append(event_data)

            # Cap at MAX_SKILL_HISTORY
            if len(history) > MAX_SKILL_HISTORY:
                history = history[-MAX_SKILL_HISTORY:]

            compact_data["history"] = history
            self._save_compact_data(compact_data)

        except Exception as e:
            logger.error(f"Failed to log skill event: {e}")

    # =========================================================================
    # MIGRATION HELPER (for transitioning from old file-based storage)
    # =========================================================================

    @classmethod
    def migrate_from_files(cls, chain_state: "ChainState", qube_dir: Path) -> "SkillsManager":
        """
        Migrate skills from old file-based storage to chain_state.

        Args:
            chain_state: ChainState instance to migrate into
            qube_dir: Path to qube's data directory

        Returns:
            New SkillsManager instance with migrated data
        """
        skills_file = qube_dir / "skills" / "skills.json"
        history_file = qube_dir / "skills" / "skill_history.json"

        manager = cls(chain_state)
        skill_definitions = manager._get_skill_definitions()

        skill_xp = {}
        extra_unlocked = []
        total_xp = 0
        history = []

        # Migrate skills.json
        if skills_file.exists():
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)

                for skill in old_data.get("skills", []):
                    skill_id = skill.get("id")
                    if not skill_id:
                        continue

                    xp = skill.get("xp", 0)
                    level = skill.get("level", 0)
                    unlocked = skill.get("unlocked", False)

                    default_def = skill_definitions.get(skill_id, {})
                    default_unlocked = default_def.get("unlocked", False)

                    if xp > 0 or level > 0:
                        skill_xp[skill_id] = {"xp": xp, "level": level}
                        total_xp += xp

                    if unlocked and not default_unlocked:
                        extra_unlocked.append(skill_id)

                logger.info(f"Migrated {len(skill_xp)} skills with XP from {skills_file}")
            except Exception as e:
                logger.error(f"Failed to migrate skills: {e}")

        # Migrate skill_history.json
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    old_history = json.load(f)
                history = old_history[-MAX_SKILL_HISTORY:]
                logger.info(f"Migrated {len(history)} skill history events")
            except Exception as e:
                logger.error(f"Failed to migrate skill history: {e}")

        # Save compact format
        compact_data = {
            "skill_xp": skill_xp,
            "extra_unlocked": extra_unlocked,
            "history": history,
            "total_xp": total_xp,
            "last_xp_gain": datetime.utcnow().isoformat() + "Z" if skill_xp else None
        }
        chain_state.state["skills"] = compact_data
        chain_state._save()

        # Delete old files
        try:
            if skills_file.exists():
                skills_file.unlink()
            if history_file.exists():
                history_file.unlink()

            skills_dir = qube_dir / "skills"
            if skills_dir.exists() and not any(skills_dir.iterdir()):
                skills_dir.rmdir()
                logger.info("Removed empty skills directory")
        except Exception as e:
            logger.warning(f"Failed to cleanup old skill files: {e}")

        return manager
