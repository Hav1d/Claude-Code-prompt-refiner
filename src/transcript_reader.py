"""Read and parse Claude Code transcript files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .models import TranscriptEntry


def _cwd_to_project_dir(cwd: Path) -> str:
    """Convert a cwd path to Claude Code's project directory name.

    Claude Code uses: drive letter + '--' + path components joined by '-'
    E.g. C:\\Users\\Lenovo → C--Users-Lenovo
    E.g. C:\\Users\\Lenovo\\prompt-refiner → C--Users-Lenovo-prompt-refiner
    """
    resolved = str(cwd.resolve())
    # Replace drive colon+separator with -- (e.g. C:\ → C--)
    if len(resolved) >= 3 and resolved[1] == ":" and resolved[2] in ("\\", "/"):
        resolved = resolved[0] + "--" + resolved[3:]
    # Replace remaining path separators with -
    name = resolved.replace("\\", "-").replace("/", "-")
    return name.strip("-")


def _find_transcript_path(explicit_path: str = "") -> Optional[Path]:
    """Locate the Claude Code transcript file for the current project.

    Search order:
   1. Explicit path from config
    2. CLAUDE_TRANSCRIPT_PATH env var
    3. ~/.claude/projects/<cwd-derived-name>/*.jsonl (most recent)
    4. ~/.claude/history.jsonl (global fallback)
    """
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p

    env_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p

    # Try project-specific transcript — match cwd to project dir name
    claude_dir = Path.home() / ".claude"
    projects_dir = claude_dir / "projects"
    if projects_dir.is_dir():
        cwd = Path.cwd()
        expected_dir = _cwd_to_project_dir(cwd)
        proj_dir = projects_dir / expected_dir
        if proj_dir.is_dir():
            # Find the most recent .jsonl file in this project dir
            jsonl_files = sorted(
                proj_dir.glob("*.jsonl"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if jsonl_files:
                return jsonl_files[0]

    # Global fallback
    global_hist = claude_dir / "history.jsonl"
    if global_hist.is_file():
        return global_hist

    return None


def read_transcript(
    max_entries: int = 15,
    explicit_path: str = "",
) -> list[TranscriptEntry]:
    """Read the last N entries from the Claude Code transcript.

    Args:
        max_entries: Maximum number of recent entries to return.
        explicit_path: Override path to transcript file.

    Returns:
        List of TranscriptEntry objects, most recent last.
    """
    path = _find_transcript_path(explicit_path)
    if path is None:
        return []

    entries: list[TranscriptEntry] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Handle nested "message" structure (Claude Code format)
                msg = data.get("message", data)
                role = msg.get("role", "")
                content = _extract_content(msg)
                if content and role in ("human", "assistant", "user"):
                    normalized_role = "human" if role == "user" else role
                    entries.append(
                        TranscriptEntry(
                            role=normalized_role,
                            content=content,
                            timestamp=msg.get("timestamp", data.get("timestamp")),
                        )
                    )
    except OSError:
        return []

    return entries[-max_entries:]


def _extract_content(data: dict) -> str:
    """Extract text content from a transcript entry, handling various formats."""
    content = data.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        # Anthropic message format: list of content blocks
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "thinking":
                    thinking = block.get("thinking", "")
                    if thinking:
                        parts.append(f"[thinking]: {thinking[:300]}")
                elif btype == "tool_use":
                    name = block.get("name", "tool")
                    inp = block.get("input", {})
                    # Summarize tool input briefly
                    inp_str = str(inp)[:150]
                    parts.append(f"[tool: {name}] {inp_str}")
                elif btype == "tool_result":
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, str) and len(tool_content) > 200:
                        tool_content = tool_content[:200] + "..."
                    parts.append(f"[tool result]: {tool_content}")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    return str(content).strip()


def format_transcript_for_context(
    entries: list[TranscriptEntry],
    max_chars: int = 8000,
) -> str:
    """Format transcript entries into a compact text block for LLM consumption.

    Truncates from the oldest entries if total exceeds max_chars.
    """
    lines: list[str] = []
    total = 0

    for entry in reversed(entries):
        prefix = "User" if entry.role == "human" else "Assistant"
        # Truncate very long individual entries
        content = entry.content
        if len(content) > 500:
            content = content[:500] + "..."
        line = f"[{prefix}]: {content}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)

    lines.reverse()
    return "\n".join(lines)
