"""Submit refined prompts to Claude Code."""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

from .ui import console, show_error, show_info, show_success


def submit_to_claude_code(
    prompt: str,
    cwd: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """Submit the final prompt to Claude Code CLI.

    Args:
        prompt: The finalized prompt to submit.
        cwd: Working directory for Claude Code.
        dry_run: If True, print the command without executing.

    Returns:
        Exit code from Claude Code (0 = success).
    """
    cmd = ["claude"]

    if dry_run:
        show_info(f"[Dry run] Would execute: claude")
        show_info(f"[Dry run] Prompt: {prompt[:100]}...")
        return 0

    show_info("Submitting to Claude Code...")

    try:
        # Use --print mode to pipe the prompt and get output
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=False,
            text=True,
            cwd=cwd,
        )
        return result.returncode
    except FileNotFoundError:
        show_error(
            "Claude Code CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
        )
        return 1
    except KeyboardInterrupt:
        show_info("\nInterrupted by user.")
        return 130


def submit_via_pipe(prompt: str) -> int:
    """Submit prompt by piping to claude --print.

    This is the simplest integration: the refined prompt is
    passed as stdin to `claude --print`.
    """
    try:
        result = subprocess.run(
            ["claude", "--print"],
            input=prompt,
            text=True,
        )
        return result.returncode
    except FileNotFoundError:
        show_error("Claude Code CLI not found in PATH.")
        return 1
    except KeyboardInterrupt:
        return 130


def write_to_file(prompt: str, path: str) -> None:
    """Write the final prompt to a file for manual use."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)
    show_success(f"Prompt written to: {path}")
