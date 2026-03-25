"""
Voice Command Parser

Parses natural language voice commands into structured actions.
From docs/27_Audio_TTS_STT_Integration.md Section 7.2
"""

from typing import Optional, Dict, Any
import re

from utils.logging import get_logger

logger = get_logger(__name__)


class VoiceCommandParser:
    """Parse natural language voice commands"""

    # Command patterns (regex -> action + args mapping)
    COMMAND_PATTERNS = {
        r"create (?:a )?(?:new )?qube (?:named |called )?(\w+)": {
            "action": "create_qube",
            "args": {"name": 1},  # Capture group 1
        },
        r"list (?:all )?qubes": {
            "action": "list_qubes",
            "args": {},
        },
        r"(?:talk to|switch to|open) (\w+)": {
            "action": "switch_qube",
            "args": {"name": 1},
        },
        r"send message (.+)": {
            "action": "send_message",
            "args": {"message": 1},
        },
        r"(?:open|show) (?:the )?dashboard": {
            "action": "open_dashboard",
            "args": {},
        },
        r"(?:export|backup) (?:my )?data": {
            "action": "export_data",
            "args": {},
        },
        r"delete (?:qube )?(\w+)": {
            "action": "delete_qube",
            "args": {"name": 1},
        },
        r"mint (?:nft|token) for (\w+)": {
            "action": "mint_nft",
            "args": {"qube_name": 1},
        },
        r"search (?:memory|memories) (?:for )?(.+)": {
            "action": "recall",
            "args": {"query": 1},
        },
        r"(?:shutdown|stop|exit|quit)": {
            "action": "shutdown",
            "args": {},
        },
        r"help": {
            "action": "show_help",
            "args": {},
        },
        r"what('s| is) my status": {
            "action": "show_status",
            "args": {},
        },
        r"connect to (?:network|p2p)": {
            "action": "connect_p2p",
            "args": {},
        },
        r"disconnect from (?:network|p2p)": {
            "action": "disconnect_p2p",
            "args": {},
        },
    }

    def __init__(self):
        logger.debug("voice_command_parser_initialized")

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse voice command to action + args

        Args:
            text: Transcribed voice command text

        Returns:
            Dict with 'action', 'args', and 'raw_text', or None if no match
        """
        text_clean = text.lower().strip()

        logger.debug("parsing_voice_command", text=text_clean)

        for pattern, command in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, text_clean, re.IGNORECASE)
            if match:
                # Extract arguments from capture groups
                args = {}
                for arg_name, group_idx in command["args"].items():
                    args[arg_name] = match.group(group_idx)

                result = {
                    "action": command["action"],
                    "args": args,
                    "raw_text": text_clean,
                }

                logger.info("voice_command_parsed", action=result["action"], args=args)

                return result

        # No pattern matched - treat as message to current Qube
        result = {
            "action": "send_message",
            "args": {"message": text_clean},
            "raw_text": text_clean,
        }

        logger.debug("voice_command_default_to_message", text=text_clean[:50])

        return result

    def validate_command(self, command: Dict[str, Any]) -> bool:
        """
        Validate parsed command before execution

        Args:
            command: Parsed command dict

        Returns:
            True if command is valid, False otherwise
        """
        action = command["action"]
        args = command["args"]

        logger.debug("validating_command", action=action, args=args)

        if action == "create_qube":
            # Name must be alphanumeric, 3-30 chars
            name = args.get("name", "")
            is_valid = bool(re.match(r"^\w{3,30}$", name))
            if not is_valid:
                logger.warning("invalid_qube_name", name=name)
            return is_valid

        elif action == "switch_qube":
            # Must have name
            is_valid = bool(args.get("name"))
            if not is_valid:
                logger.warning("missing_qube_name")
            return is_valid

        elif action == "delete_qube":
            # Must have name
            is_valid = bool(args.get("name"))
            if not is_valid:
                logger.warning("missing_qube_name_for_deletion")
            return is_valid

        elif action == "send_message":
            # Message must not be empty
            message = args.get("message", "").strip()
            is_valid = len(message) > 0
            if not is_valid:
                logger.warning("empty_message")
            return is_valid

        # Default: valid
        logger.debug("command_valid", action=action)
        return True

    def get_help_text(self) -> str:
        """
        Get help text explaining available voice commands

        Returns:
            Help text string
        """
        return """
Available Voice Commands:

Qube Management:
- "Create a new Qube named <name>"
- "List all Qubes"
- "Talk to <name>" / "Switch to <name>"
- "Delete Qube <name>"

Communication:
- "Send message <text>"
- "<any text>" (sends to current Qube)

Blockchain:
- "Mint NFT for <qube name>"

Memory:
- "Search memory for <query>"

Network:
- "Connect to network"
- "Disconnect from network"

System:
- "Show dashboard"
- "Export my data"
- "What's my status"
- "Shutdown"
- "Help"
"""
