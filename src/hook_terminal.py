"""Terminal I/O for hook mode — bypasses stdin pipe to access the real terminal.

Windows: opens CONIN$ (read) and CONOUT$ (write) separately.
Unix: opens /dev/tty (read+write).

Used by hook_integration to show TUI review when stdin is a JSON pipe.
Fails explicitly if no terminal is available — never silently degrades.
"""

from __future__ import annotations

import sys
from typing import Optional, TextIO


def open_terminal_out() -> Optional[TextIO]:
    """Open a write handle to the user's terminal."""
    try:
        if sys.platform == "win32":
            return open("CONOUT$", "w", encoding="utf-8", errors="replace")
        else:
            return open("/dev/tty", "w", encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return None


def open_terminal_in() -> Optional[TextIO]:
    """Open a read handle to the user's terminal."""
    try:
        if sys.platform == "win32":
            return open("CONIN$", "r", encoding="utf-8", errors="replace")
        else:
            return open("/dev/tty", "r", encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return None


def prompt_choice(out: TextIO, inp: TextIO, prompt: str, valid: str, default: str) -> str:
    """Prompt for a single-character choice on the terminal."""
    while True:
        out.write(prompt)
        out.flush()
        try:
            line = inp.readline().strip().lower()
        except (EOFError, OSError):
            return default
        if not line:
            return default
        if line in valid:
            return line
        out.write(f"Please enter one of: {', '.join(valid)}\n")
        out.flush()


def tty_print(out: TextIO, text: str) -> None:
    """Print a line to the terminal."""
    out.write(text + "\n")
    out.flush()


def tty_readline(inp: TextIO) -> str:
    """Read a line from the terminal."""
    try:
        return inp.readline().rstrip("\n")
    except (EOFError, OSError):
        return ""


def tui_refine_review(
    out: TextIO,
    inp: TextIO,
    original: str,
    refined: str,
    context_summary: str = "",
    degraded: bool = False,
) -> tuple[str, str]:
    """Present the refinement review UI on the terminal and get user choice.

    Shows: context summary, diff, refined prompt, and A/E/O/S menu.
    Returns: (choice, edited_text) where choice is "accept"/"edit"/"original"/"skip".
    """
    sep = "=" * 60

    out.write(f"\n{sep}\n")
    out.write("  Prompt Refiner — Refinement Review\n")
    out.write(f"{sep}\n\n")

    # Context summary
    if context_summary and context_summary != "(no context)":
        out.write("Session Context:\n")
        out.write(f"  {context_summary}\n\n")

    # Degradation warning
    if degraded:
        out.write("WARNING: Refinement model unavailable — showing minimal structure only.\n\n")

    # Diff
    if original.strip() != refined.strip():
        out.write("Changes:\n")
        orig_lines = original.strip().splitlines()
        ref_lines = refined.strip().splitlines()
        max_lines = max(len(orig_lines), len(ref_lines))
        for i in range(max_lines):
            o = orig_lines[i] if i < len(orig_lines) else ""
            r = ref_lines[i] if i < len(ref_lines) else ""
            if o != r:
                if o:
                    out.write(f"  - {o}\n")
                if r:
                    out.write(f"  + {r}\n")
            else:
                out.write(f"    {o}\n")
        out.write("\n")
    else:
        out.write("No changes — input was already clear.\n\n")

    # Full refined prompt
    out.write(f"Refined Prompt:\n  {refined.strip()}\n\n")

    # Actions menu
    out.write("Actions:\n")
    out.write("  [A]ccept    — Use refined version\n")
    out.write("  [E]dit      — Edit before submitting\n")
    out.write("  [O]riginal  — Use original input as-is\n")
    out.write("  [S]kip      — Skip refinement this time\n\n")
    out.flush()

    choice = prompt_choice(out, inp, "Choose action [A/E/O/S] (default=A): ", "aeos", "a")
    out.write("\n")
    out.flush()

    if choice == "e":
        out.write("Enter your edited prompt (empty line to finish):\n")
        out.write(f"Current: {refined[:120]}{'...' if len(refined) > 120 else ''}\n\n")
        out.flush()
        lines: list[str] = []
        while True:
            try:
                line = inp.readline()
            except (EOFError, OSError):
                break
            if not line:  # EOF
                break
            line = line.rstrip("\n").rstrip("\r")
            if line == "":
                break  # empty line finishes
            lines.append(line)
        edited = "\n".join(lines).strip()
        return ("edit", edited if edited else refined)

    return ({"a": "accept", "e": "edit", "o": "original", "s": "skip"}[choice], "")


def terminal_unavailable_reason() -> str:
    """Return a human-readable reason why the terminal TUI is unavailable."""
    if sys.platform == "win32":
        return (
            "Claude Code subprocess cannot access CONIN$/CONOUT$ on Windows. "
            "The hook runs as a child process without console handle inheritance."
        )
    return (
        "Cannot open /dev/tty. The hook may be running in a non-interactive "
        "context (e.g. piped, background, or CI environment)."
    )
