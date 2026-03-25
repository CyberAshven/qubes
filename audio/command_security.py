"""
Command Security

Validates and secures voice commands before execution.
From docs/27_Audio_TTS_STT_Integration.md Section 12.2
"""

from typing import Dict, Any

from core.exceptions import QubesError
from utils.logging import get_logger

logger = get_logger(__name__)


# Destructive actions that require confirmation
DESTRUCTIVE_ACTIONS = [
    "delete_qube",
    "delete_all_qubes",
    "reset_memory",
    "shutdown",
    "export_data",
]


def requires_confirmation(command: Dict[str, Any]) -> bool:
    """
    Check if command needs user confirmation

    Args:
        command: Parsed command dict

    Returns:
        True if confirmation required, False otherwise
    """
    action = command.get("action", "")
    needs_confirmation = action in DESTRUCTIVE_ACTIONS

    if needs_confirmation:
        logger.info("command_requires_confirmation", action=action)

    return needs_confirmation


async def execute_voice_command(command: Dict[str, Any], orchestrator) -> str:
    """
    Execute voice command with security checks

    Args:
        command: Parsed command dict
        orchestrator: Orchestrator instance

    Returns:
        Execution result message

    Raises:
        QubesError: If command is invalid or fails security checks
    """
    from audio.command_parser import VoiceCommandParser

    parser = VoiceCommandParser()

    logger.info(
        "executing_voice_command",
        action=command.get("action"),
        args=command.get("args")
    )

    # Validate command
    if not parser.validate_command(command):
        error_msg = f"Invalid command: {command}"
        logger.error("voice_command_validation_failed", command=command)
        raise QubesError(error_msg)

    # Check if destructive action requires confirmation
    if requires_confirmation(command):
        logger.warning(
            "destructive_command_attempted",
            action=command.get("action"),
            message="This command requires confirmation"
        )

        # In a real implementation, this would prompt the user
        # For now, we'll return a message asking for confirmation
        return f"⚠️ Are you sure you want to {command['action']}? This action cannot be undone. Say 'yes' to confirm."

    # Execute command via orchestrator
    try:
        result = await _dispatch_command(command, orchestrator)
        logger.info("voice_command_executed", action=command.get("action"))
        return result

    except Exception as e:
        logger.error(
            "voice_command_execution_failed",
            action=command.get("action"),
            error=str(e),
            exc_info=True
        )
        raise QubesError(f"Command execution failed: {e}", cause=e)


async def _dispatch_command(command: Dict[str, Any], orchestrator) -> str:
    """
    Dispatch command to appropriate handler

    Args:
        command: Parsed command dict
        orchestrator: Orchestrator instance

    Returns:
        Execution result message
    """
    action = command["action"]
    args = command["args"]

    # Command routing
    if action == "create_qube":
        qube_name = args.get("name", "")
        # await orchestrator.create_qube(name=qube_name)
        return f"Created new Qube named '{qube_name}'."

    elif action == "list_qubes":
        # qubes = await orchestrator.list_qubes()
        # return f"You have {len(qubes)} Qubes: {', '.join([q.name for q in qubes])}"
        return "Listing all Qubes..."

    elif action == "switch_qube":
        qube_name = args.get("name", "")
        # await orchestrator.switch_qube(name=qube_name)
        return f"Switched to Qube '{qube_name}'."

    elif action == "send_message":
        message = args.get("message", "")
        # response = await orchestrator.send_message(message)
        return f"Message sent: {message[:50]}..."

    elif action == "open_dashboard":
        # await orchestrator.open_dashboard()
        return "Opening dashboard..."

    elif action == "export_data":
        # await orchestrator.export_data()
        return "Exporting data..."

    elif action == "delete_qube":
        qube_name = args.get("name", "")
        # await orchestrator.delete_qube(name=qube_name)
        return f"Deleted Qube '{qube_name}'."

    elif action == "mint_nft":
        qube_name = args.get("qube_name", "")
        # await orchestrator.mint_nft(qube_name=qube_name)
        return f"Minting NFT for Qube '{qube_name}'..."

    elif action == "recall":
        query = args.get("query", "")
        return f"Searching memory for: {query[:50]}..."

    elif action == "show_status":
        # status = await orchestrator.get_status()
        return "System status: operational."

    elif action == "show_help":
        from audio.command_parser import VoiceCommandParser
        parser = VoiceCommandParser()
        return parser.get_help_text()

    elif action == "connect_p2p":
        # await orchestrator.connect_p2p()
        return "Connecting to P2P network..."

    elif action == "disconnect_p2p":
        # await orchestrator.disconnect_p2p()
        return "Disconnecting from P2P network..."

    elif action == "shutdown":
        # await orchestrator.shutdown()
        return "Shutting down..."

    else:
        logger.warning("unknown_voice_command", action=action)
        return f"Unknown command: {action}"


# Whitelist of allowed commands (security measure)
ALLOWED_COMMANDS = {
    "create_qube",
    "list_qubes",
    "switch_qube",
    "send_message",
    "open_dashboard",
    "export_data",
    "delete_qube",
    "mint_nft",
    "recall",
    "show_status",
    "show_help",
    "connect_p2p",
    "disconnect_p2p",
    "shutdown",
}


def is_command_allowed(command: Dict[str, Any]) -> bool:
    """
    Check if command is in whitelist

    Args:
        command: Parsed command dict

    Returns:
        True if allowed, False otherwise
    """
    action = command.get("action", "")
    is_allowed = action in ALLOWED_COMMANDS

    if not is_allowed:
        logger.warning("command_not_in_whitelist", action=action)

    return is_allowed
