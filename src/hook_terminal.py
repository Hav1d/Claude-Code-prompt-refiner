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
