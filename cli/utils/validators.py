"""
Input validation and Qube resolution utilities.

Handles:
- Qube name/ID resolution with partial matching
- Input validation (hex colors, model names, etc.)
- Confirmation dialogs for destructive actions
"""

import sys
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


def resolve_qube(name_or_id: str, orchestrator, all_qubes: Optional[List[Dict]] = None) -> Dict:
    """
    Resolve Qube by name or partial ID.

    Matching logic:
    1. Exact name match (case-insensitive)
    2. Partial ID match (minimum 4 characters)
    3. If multiple matches, show interactive selector or error

    Args:
        name_or_id: Qube name or ID (partial or full)
        orchestrator: Orchestrator instance
        all_qubes: Optional pre-fetched list of Qubes (for performance)

    Returns:
        Qube info dict with qube_id and name

    Raises:
        ValueError: If no match or ambiguous match in scriptable mode
    """
    import asyncio

    # Fetch Qubes if not provided
    if all_qubes is None:
        all_qubes = asyncio.run(orchestrator.list_qubes())

    if not all_qubes:
        raise ValueError("No Qubes found. Create one with: qubes create")

    # Try exact name match first (case-insensitive)
    name_matches = [q for q in all_qubes if q["name"].lower() == name_or_id.lower()]
    if len(name_matches) == 1:
        return name_matches[0]

    # Try partial ID match (minimum 4 characters)
    if len(name_or_id) >= 4:
        id_matches = [q for q in all_qubes if q["qube_id"].startswith(name_or_id.lower())]

        if len(id_matches) == 1:
            return id_matches[0]
        elif len(id_matches) > 1:
            # Multiple matches - show selector in interactive mode
            if sys.stdout.isatty():
                return _interactive_selector(id_matches, name_or_id)
            else:
                # Scriptable mode - error on ambiguous match
                matches_str = ", ".join([f"{q['name']} ({q['qube_id'][:8]})" for q in id_matches])
                raise ValueError(f"Ambiguous match for '{name_or_id}'. Matches: {matches_str}")

    # Try partial name match as fallback
    partial_name_matches = [q for q in all_qubes if name_or_id.lower() in q["name"].lower()]
    if len(partial_name_matches) == 1:
        return partial_name_matches[0]
    elif len(partial_name_matches) > 1:
        if sys.stdout.isatty():
            return _interactive_selector(partial_name_matches, name_or_id)
        else:
            matches_str = ", ".join([f"{q['name']} ({q['qube_id'][:8]})" for q in partial_name_matches])
            raise ValueError(f"Ambiguous match for '{name_or_id}'. Matches: {matches_str}")

    # No match
    raise ValueError(f"No Qube found matching '{name_or_id}'")


def _interactive_selector(matches: List[Dict], query: str) -> Dict:
    """Show interactive menu for multiple matches."""
    console.print(f"\n[yellow]Multiple Qubes match '{query}':[/yellow]\n")

    for i, match in enumerate(matches, 1):
        console.print(f"  {i}. [cyan]{match['name']}[/cyan] ([dim]{match['qube_id'][:16]}...[/dim])")

    while True:
        selection = Prompt.ask(
            "\nSelect Qube",
            choices=[str(i) for i in range(1, len(matches) + 1)]
        )
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection. Try again.[/red]")


def validate_hex_color(color: str) -> bool:
    """
    Validate hex color format.

    Args:
        color: Hex color string (e.g., "#4A90E2" or "4A90E2")

    Returns:
        True if valid, False otherwise
    """
    import re

    # Add # if missing
    if not color.startswith("#"):
        color = "#" + color

    # Validate format: #RRGGBB
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))


def normalize_hex_color(color: str) -> str:
    """
    Normalize hex color to #RRGGBB format.

    Args:
        color: Hex color string

    Returns:
        Normalized hex color with # prefix
    """
    if not color.startswith("#"):
        color = "#" + color
    return color.upper()


def confirm_destructive_action(
    action: str,
    target: str,
    details: Optional[List[str]] = None,
    auto_yes: bool = False
) -> bool:
    """
    Confirm destructive action with user.

    Args:
        action: Action description (e.g., "Delete")
        target: Target description (e.g., "Qube 'AlphaBot'")
        details: Optional list of detail strings
        auto_yes: Skip confirmation if True

    Returns:
        True if confirmed, False otherwise
    """
    if auto_yes:
        return True

    console.print(f"\n[red]⚠️  Warning: This will {action.lower()} {target}[/red]\n")

    if details:
        console.print("This includes:")
        for detail in details:
            console.print(f"  - {detail}")
        console.print()

    console.print("[yellow]This action cannot be undone.[/yellow]\n")

    return Confirm.ask(f"{action} {target}?", default=False)


def validate_ai_model(model: str) -> bool:
    """
    Validate AI model name.

    Args:
        model: AI model name

    Returns:
        True if valid
    """
    # List of known models (can be extended)
    known_models = [
        "claude-sonnet-4.5",
        "claude-opus-4.1",
        "claude-3.7-sonnet",
        "claude-3-5-sonnet-20241022",
        "gpt-5",
        "gpt-5-mini",
        "gpt-4o",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash-exp",
        "sonar-pro",
        "llama3.3:70b",
        "qwen3:235b"
    ]

    # Allow custom models (any string is technically valid)
    # Just warn if unknown
    if model not in known_models:
        console.print(f"[yellow]⚠️  Unknown model '{model}'. Proceeding anyway.[/yellow]")

    return True


def validate_voice_model(model: str) -> bool:
    """
    Validate voice model name.

    Args:
        model: Voice model name

    Returns:
        True if valid
    """
    known_voices = [
        "openai:alloy",
        "openai:nova",
        "openai:shimmer",
        "openai:echo",
        "openai:fable",
        "openai:onyx",
        "elevenlabs:custom",
        "piper:en_US-lessac-medium",
        "tts-1",
        "tts-1-hd"
    ]

    if model not in known_voices:
        console.print(f"[yellow]⚠️  Unknown voice model '{model}'. Proceeding anyway.[/yellow]")

    return True


def validate_trust_score(score: float) -> bool:
    """
    Validate trust score range.

    Args:
        score: Trust score (should be 0-10)

    Returns:
        True if valid

    Raises:
        ValueError: If score out of range
    """
    if not 0 <= score <= 10:
        raise ValueError(f"Trust score must be between 0 and 10, got {score}")
    return True


def validate_permission_level(permission: str) -> bool:
    """
    Validate memory sharing permission level.

    Args:
        permission: Permission level

    Returns:
        True if valid

    Raises:
        ValueError: If invalid permission
    """
    valid_permissions = ["read-only", "read-write", "full"]
    if permission not in valid_permissions:
        raise ValueError(f"Invalid permission '{permission}'. Must be one of: {', '.join(valid_permissions)}")
    return True


def parse_block_range(range_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse block range string.

    Examples:
        "10" -> (10, 10)
        "10-20" -> (10, 20)
        "-5" -> (None, 5)  # Last 5 blocks
        "10-" -> (10, None)  # From block 10 to end

    Args:
        range_str: Block range string

    Returns:
        Tuple of (start, end) or (None, count) for negative indexing
    """
    if "-" in range_str:
        parts = range_str.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid block range format: {range_str}")

        start = int(parts[0]) if parts[0] else None
        end = int(parts[1]) if parts[1] else None

        return (start, end)
    else:
        # Single block number
        num = int(range_str)
        return (num, num)
