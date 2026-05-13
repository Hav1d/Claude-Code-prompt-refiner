"""Terminal UI for reviewing refined prompts using Rich."""

from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.theme import Theme

from .logger import format_diff
from .models import UserChoice

custom_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "original": "dim white",
        "refined": "bold white",
        "choice": "bold cyan",
        "diff.add": "green",
        "diff.del": "red",
    }
)

console = Console(theme=custom_theme)


def show_welcome() -> None:
    """Display the welcome banner."""
    console.print()
    console.print(
        Panel(
            "[bold]Prompt Refiner[/bold] — Refine before you send",
            border_style="cyan",
            expand=False,
        )
    )


def show_refinement_result(
    original: str,
    refined: str,
    context_summary: str,
    degraded: bool = False,
) -> UserChoice:
    """Display the refinement result and get user choice.

    Shows:
    - Context summary (if available)
    - Diff between original and refined
    - Full refined prompt
    - Action menu with keyboard shortcuts

    Returns:
        UserChoice enum value.
    """
    console.print()

    # Context summary
    if context_summary and context_summary != "(no context)":
        console.print(
            Panel(
                context_summary,
                title="[info]Session Context[/info]",
                border_style="dim",
                expand=False,
            )
        )

    # Degradation warning
    if degraded:
        console.print(
            "[warning]⚠ Refinement model unavailable — showing minimal structure only.[/warning]"
        )

    # Diff view
    diff = format_diff(original, refined)
    if diff.strip() and original.strip() != refined.strip():
        console.print()
        console.print("[bold]Changes:[/bold]")
        for line in diff.splitlines():
            if line.startswith("+ "):
                console.print(f"  [diff.add]{line}[/diff.add]")
            elif line.startswith("- "):
                console.print(f"  [diff.del]{line}[/diff.del]")
            else:
                console.print(f"  {line}")
    else:
        console.print("[info]No changes — input was already clear.[/info]")

    # Full refined prompt
    console.print()
    console.print(
        Panel(
            refined,
            title="[refined]Refined Prompt[/refined]",
            border_style="green",
            expand=True,
        )
    )

    # Action menu
    console.print()
    console.print("[bold]Actions:[/bold]")
    console.print("  [choice][A][/choice]ccept    — Use refined version")
    console.print("  [choice][E][/choice]dit      — Edit before submitting")
    console.print("  [choice][O][/choice]riginal  — Use original input as-is")
    console.print("  [choice][S][/choice]kip      — Skip refinement this time")
    console.print()

    return _get_choice()


def _get_choice() -> UserChoice:
    """Prompt user for action choice with keyboard input."""
    while True:
        try:
            key = Prompt.ask(
                "Choose action",
                choices=["a", "e", "o", "s", "A", "E", "O", "S"],
                default="a",
                show_choices=False,
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[info]Cancelled.[/info]")
            return UserChoice.SKIP

        key = key.lower()
        if key == "a":
            return UserChoice.ACCEPT
        elif key == "e":
            return UserChoice.EDIT
        elif key == "o":
            return UserChoice.ORIGINAL
        elif key == "s":
            return UserChoice.SKIP


def edit_prompt(original_refined: str) -> str:
    """Allow user to edit the refined prompt in-terminal.

    Uses a simple line-by-line editor (no external editor dependency).
    """
    console.print()
    console.print("[info]Enter your edited prompt (empty line to finish):[/info]")
    console.print(
        f"[dim]Current: {original_refined[:80]}{'...' if len(original_refined) > 80 else ''}[/dim]"
    )
    console.print()

    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        if not lines:
            return original_refined

    edited = "\n".join(lines).strip()
    return edited if edited else original_refined


def show_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[error]Error: {message}[/error]")


def show_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[success]{message}[/success]")


def show_info(message: str) -> None:
    """Display an info message."""
    console.print(f"[info]{message}[/info]")


def show_skip_reason(reason: str) -> None:
    """Display why refinement was skipped."""
    console.print(f"[dim]Skipped: {reason}[/dim]")


def show_final_prompt(prompt: str) -> None:
    """Display the final prompt that will be submitted."""
    console.print()
    console.print(
        Panel(
            prompt,
            title="[success]Final Prompt → Claude Code[/success]",
            border_style="green",
            expand=True,
        )
    )


def confirm_submit(prompt: str) -> bool:
    """Ask user to confirm before submitting to Claude Code."""
    show_final_prompt(prompt)
    try:
        answer = Prompt.ask(
            "\nSubmit to Claude Code?",
            choices=["y", "n", "Y", "N"],
            default="y",
            show_choices=False,
        )
        return answer.lower() == "y"
    except (KeyboardInterrupt, EOFError):
        return False
