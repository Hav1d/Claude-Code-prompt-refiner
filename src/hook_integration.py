"""Claude Code hook integration module.

Handles the UserPromptSubmit hook event with official Claude Code format:
    Output: {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}
    Pass-through: empty stdout
"""

from __future__ import annotations

import difflib
import json
import sys
from typing import Any, Optional

from .config import RefineConfig, load_config
from .refiner import should_refine


def parse_hook_payload(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def extract_prompt_from_hook(payload: dict[str, Any]) -> str:
    return payload.get("prompt", "")


def build_hook_response(
    refined_prompt: str,
    event_name: str = "UserPromptSubmit",
) -> dict[str, Any]:
    if not refined_prompt:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": refined_prompt,
        }
    }


def _show_refinement_in_terminal(original: str, refined: str) -> None:
    """Show refinement diff in terminal via stderr (visible in Claude Code)."""
    print("\n" + "=" * 50, file=sys.stderr)
    print("  Prompt Refiner — Refinement Result", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    orig_lines = original.strip().splitlines()
    ref_lines = refined.strip().splitlines()

    if orig_lines != ref_lines:
        diff = difflib.unified_diff(
            orig_lines, ref_lines,
            fromfile="original", tofile="refined",
            lineterm="",
        )
        for line in diff:
            print(f"  {line}", file=sys.stderr)
    else:
        print("  (No significant changes)", file=sys.stderr)

    print(f"\n  Refined: {refined.strip()}", file=sys.stderr)
    print("=" * 50 + "\n", file=sys.stderr)


async def handle_hook(
    payload: dict[str, Any],
    config: Optional[RefineConfig] = None,
    event_name: str = "UserPromptSubmit",
) -> dict[str, Any] | None:
    """Process a Claude Code hook event.

    Returns hookSpecificOutput dict on success, None to pass through.
    """
    if config is None:
        config = load_config()

    raw_input = extract_prompt_from_hook(payload)
    _stderr_log(f"prompt={raw_input!r}")
    if not raw_input:
        return None
    if not should_refine(raw_input, config):
        _stderr_log("skipped: should_refine=False")
        return None

    # Check credentials
    from .credentials import resolve_for_config
    api_key, _ = resolve_for_config(config)
    if not api_key:
        _stderr_log("skipped: no API key")
        return None

    from .llm import make_llm_caller
    from .models import SessionContext
    from .refiner import apply_prefix_suffix, refine_prompt
    from .summarizer import summarize_history
    from .transcript_reader import format_transcript_for_context, read_transcript

    entries = read_transcript(
        max_entries=config.history_lines,
        explicit_path=payload.get("transcript_path", config.transcript_path),
    )

    context = SessionContext()
    if entries:
        transcript_text = format_transcript_for_context(entries)
        if transcript_text:
            try:
                summary_caller = make_llm_caller(config)
                context = await summarize_history(entries, config, llm_caller=summary_caller)
            except Exception:
                pass

    _stderr_log("calling LLM to refine...")
    try:
        llm_caller = make_llm_caller(config)
        refined, _ = await refine_prompt(raw_input, context, config, llm_caller=llm_caller)
    except Exception as e:
        _stderr_log(f"LLM failed: {e}")
        return None

    _stderr_log(f"refined={refined!r}")

    # Skip if no meaningful change
    if raw_input.strip() == refined.strip():
        _stderr_log("skipped: no change")
        return None

    # Show refinement in terminal (visible to user)
    _show_refinement_in_terminal(raw_input, refined)

    # Build context that instructs Claude to present options to user
    refined_text = apply_prefix_suffix(refined, config)
    context_block = (
        f"[Prompt Refiner] The user's prompt has been refined for clarity.\n\n"
        f"Original prompt:\n{raw_input.strip()}\n\n"
        f"Refined prompt:\n{refined_text.strip()}\n\n"
        f"IMPORTANT: Show the user both versions above, then ask: "
        f'"Use the refined version? Reply \'y\' to use refined, \'n\' for original, '
        f'or paste your own edited version." '
        f"Do NOT proceed until the user confirms which version to use."
    )

    return build_hook_response(context_block, event_name)


def _stderr_log(message: str) -> None:
    """Log to stderr for debugging."""
    print(f"[prompt-refiner] {message}", file=sys.stderr)
