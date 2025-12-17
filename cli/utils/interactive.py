"""
Interactive utilities for CLI.

Provides:
- Rich prompts and menus
- Autocomplete for Qube names
- Interactive selections
- Color pickers
"""

from typing import List, Optional, Dict, Any, Callable
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()


def select_from_menu(
    title: str,
    options: List[str],
    descriptions: Optional[List[str]] = None,
    default: int = 1,
    show_numbers: bool = True
) -> tuple[int, str]:
    """
    Display interactive menu and get selection.

    Args:
        title: Menu title
        options: List of option strings
        descriptions: Optional descriptions for each option
        default: Default selection (1-indexed)
        show_numbers: Show option numbers

    Returns:
        Tuple of (selected_index, selected_option)
    """
    console.print(f"\n[bold]{title}[/bold]")

    for i, option in enumerate(options, 1):
        prefix = f"  {i}. " if show_numbers else "  • "
        desc = f" [dim]- {descriptions[i-1]}[/dim]" if descriptions and len(descriptions) >= i else ""
        console.print(f"{prefix}[cyan]{option}[/cyan]{desc}")

    while True:
        choice = Prompt.ask(
            "\nSelection",
            choices=[str(i) for i in range(1, len(options) + 1)],
            default=str(default)
        )

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return (idx, options[idx])
        except ValueError:
            console.print("[red]Invalid selection. Try again.[/red]")


def select_ai_model(default: str = "claude-sonnet-4.5") -> str:
    """
    Interactive AI model selection menu.

    Args:
        default: Default model name

    Returns:
        Selected AI model name
    """
    models = [
        "claude-sonnet-4.5",
        "claude-opus-4.1",
        "claude-3.7-sonnet",
        "gpt-5",
        "gpt-5-mini",
        "gpt-4o",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "sonar-pro",
        "llama3.3:70b",
        "qwen3:235b",
        "Custom (enter model ID)"
    ]

    descriptions = [
        "Anthropic - Balanced performance",
        "Anthropic - Highest capability",
        "Anthropic - Previous generation",
        "OpenAI - Latest flagship",
        "OpenAI - Fast and efficient",
        "OpenAI - Multimodal",
        "Google - Advanced reasoning",
        "Google - Fast responses",
        "Perplexity - Search-focused",
        "Meta - Open source large",
        "Alibaba - Open source extra large",
        "Enter your own model ID"
    ]

    # Find default index
    try:
        default_idx = models.index(default) + 1
    except ValueError:
        default_idx = 1

    idx, model = select_from_menu(
        "AI Model Selection",
        models,
        descriptions,
        default=default_idx
    )

    # Handle custom model entry
    if model == "Custom (enter model ID)":
        model = Prompt.ask("Enter custom AI model ID")

    return model


def select_voice_model(default: Optional[str] = "openai:alloy") -> Optional[str]:
    """
    Interactive voice model selection menu.

    Args:
        default: Default voice model name

    Returns:
        Selected voice model name, or None if disabled
    """
    use_voice = Confirm.ask("\nEnable voice capabilities?", default=True)

    if not use_voice:
        return None

    voices = [
        "openai:alloy",
        "openai:nova",
        "openai:shimmer",
        "openai:echo",
        "openai:fable",
        "openai:onyx",
        "elevenlabs:custom",
        "piper:en_US-lessac-medium",
        "Custom (enter voice ID)"
    ]

    descriptions = [
        "OpenAI - Neutral and balanced",
        "OpenAI - Warm and engaging",
        "OpenAI - Soft and pleasant",
        "OpenAI - Clear and direct",
        "OpenAI - Expressive",
        "OpenAI - Deep and authoritative",
        "ElevenLabs - High quality custom",
        "Piper - Fast local TTS",
        "Enter your own voice ID"
    ]

    # Find default index
    try:
        default_idx = voices.index(default) + 1 if default else 1
    except ValueError:
        default_idx = 1

    idx, voice = select_from_menu(
        "Voice Model Selection",
        voices,
        descriptions,
        default=default_idx
    )

    # Handle custom voice entry
    if voice == "Custom (enter voice ID)":
        voice = Prompt.ask("Enter custom voice model ID")

    return voice


def select_color(default: str = "#4A90E2") -> str:
    """
    Interactive color picker.

    Args:
        default: Default hex color

    Returns:
        Selected hex color
    """
    presets = {
        "Blue": "#4A90E2",
        "Green": "#41DAAA",
        "Red": "#E74C3C",
        "Purple": "#9B59B6",
        "Orange": "#E67E22",
        "Pink": "#EC407A",
        "Cyan": "#00BCD4",
        "Yellow": "#FFC107"
    }

    console.print(f"\n[bold]Favorite Color Selection[/bold]")
    console.print(f"Current: [{default}]████[/{default}] {default}\n")

    console.print("Presets:")
    for i, (name, color) in enumerate(presets.items(), 1):
        console.print(f"  {i}. [{color}]████[/{color}] {name} ({color})")

    console.print(f"  {len(presets) + 1}. Custom (enter hex code)")

    choice = Prompt.ask(
        "\nSelection",
        choices=[str(i) for i in range(1, len(presets) + 2)],
        default="1"
    )

    idx = int(choice) - 1

    if idx < len(presets):
        # Preset selected
        color = list(presets.values())[idx]
    else:
        # Custom color
        while True:
            color = Prompt.ask("Enter hex color (e.g., #4A90E2 or 4A90E2)")

            # Validate
            from cli.utils.validators import validate_hex_color, normalize_hex_color

            if validate_hex_color(color):
                color = normalize_hex_color(color)
                break
            else:
                console.print("[red]Invalid hex color format. Try again.[/red]")

    # Show preview
    console.print(f"\nSelected: [{color}]████[/{color}] {color}")

    return color


def multiline_input(prompt: str = "Enter text") -> str:
    """
    Get multiline input from user.

    Args:
        prompt: Input prompt

    Returns:
        Multiline string
    """
    console.print(f"\n[bold]{prompt}[/bold] (press Ctrl+D or Ctrl+Z when done)")

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    return "\n".join(lines)


def confirm_with_preview(
    action: str,
    preview_data: Dict[str, Any],
    border_color: str = "cyan"
) -> bool:
    """
    Show preview and confirm action.

    Args:
        action: Action description
        preview_data: Dict of key-value pairs to preview
        border_color: Border color for panel

    Returns:
        True if confirmed
    """
    # Build preview text
    preview_lines = []
    for key, value in preview_data.items():
        preview_lines.append(f"[bold]{key}:[/bold] {value}")

    preview_text = "\n".join(preview_lines)

    console.print(Panel(
        preview_text,
        title=f"Preview: {action}",
        border_style=border_color
    ))

    return Confirm.ask(f"\n{action}?", default=True)


def progress_menu(
    items: List[str],
    process_func: Callable[[str], bool],
    title: str = "Processing"
) -> Dict[str, bool]:
    """
    Process items with progress display and success/failure tracking.

    Args:
        items: List of items to process
        process_func: Function to process each item (returns True on success)
        title: Progress title

    Returns:
        Dict of {item: success_status}
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    results = {}

    console.print(f"\n[bold]{title}[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        for item in items:
            task = progress.add_task(f"Processing {item}...", total=None)

            try:
                success = process_func(item)
                results[item] = success

                progress.update(task, completed=True)

                if success:
                    console.print(f"  [green]✓[/green] {item}")
                else:
                    console.print(f"  [red]✗[/red] {item} - Failed")

            except Exception as e:
                results[item] = False
                progress.update(task, completed=True)
                console.print(f"  [red]✗[/red] {item} - Error: {str(e)}")

    return results


def show_table(
    title: str,
    headers: List[str],
    rows: List[List[str]],
    styles: Optional[List[str]] = None,
    border_style: str = "cyan"
) -> None:
    """
    Display formatted table.

    Args:
        title: Table title
        headers: Column headers
        rows: List of row data
        styles: Optional styles for each column
        border_style: Border color
    """
    table = Table(title=title, border_style=border_style)

    # Add columns
    for i, header in enumerate(headers):
        style = styles[i] if styles and len(styles) > i else None
        table.add_column(header, style=style)

    # Add rows
    for row in rows:
        table.add_row(*row)

    console.print(table)
    console.print()


def paginated_display(
    items: List[Any],
    display_func: Callable[[Any], str],
    items_per_page: int = 20,
    title: str = "Results"
) -> None:
    """
    Display items with pagination.

    Args:
        items: List of items to display
        display_func: Function to convert item to display string
        items_per_page: Items per page
        title: Display title
    """
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    current_page = 1

    while True:
        # Calculate slice
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))

        # Display current page
        console.print(f"\n[bold]{title}[/bold] (Page {current_page}/{total_pages})\n")

        for item in items[start_idx:end_idx]:
            console.print(display_func(item))

        # Navigation
        if total_pages == 1:
            break

        console.print(f"\n[dim]Page {current_page} of {total_pages}[/dim]")

        if current_page < total_pages:
            action = Prompt.ask(
                "Action",
                choices=["n", "p", "q"],
                default="n"
            )

            if action == "n":
                current_page += 1
            elif action == "p" and current_page > 1:
                current_page -= 1
            elif action == "q":
                break
        else:
            action = Prompt.ask(
                "Action",
                choices=["p", "q"],
                default="q"
            )

            if action == "p":
                current_page -= 1
            elif action == "q":
                break
