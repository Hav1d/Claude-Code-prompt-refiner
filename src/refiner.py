"""Core prompt refinement logic."""

from __future__ import annotations

import re
from typing import Optional

from .config import RefineConfig
from .models import SessionContext

_REFINE_SYSTEM_PROMPT = """You are a prompt refiner for Claude Code. Your job is to take a user's raw input and rewrite it into a clearer, more structured prompt that Claude Code can execute more effectively.

## Core Principles
{principles}

## Output Format
Return ONLY the refined prompt text. No meta-commentary, no explanations, no "Here is the refined prompt:" prefix.

If the input is already clear and specific enough, return it nearly unchanged.
If the input is ambiguous, output a single clarifying question prefixed with "[Clarify] ".

## Structure Template (use when applicable)
Goal: <what to accomplish>
Context: <relevant background — errors, files, current state>
Constraints: <explicit limitations or requirements>

## Additional Rules
{user_rules}
{project_rules}
"""


def should_refine(input_text: str, config: RefineConfig) -> bool:
    """Determine whether the input should go through refinement.

    Returns False if:
    - Input matches a skip command
    - Input matches an ignore pattern
    - Input is too short to meaningfully refine
    """
    stripped = input_text.strip()

    # Skip commands
    for cmd in config.skip_commands:
        if stripped.lower().startswith(cmd.lower()):
            return False

    # Ignore patterns
    for pattern in config.ignore_patterns:
        if re.match(pattern, stripped):
            return False

    # Too short
    if len(stripped) < 5:
        return False

    return True


def build_refine_prompt(
    raw_input: str,
    context: SessionContext,
    config: RefineConfig,
) -> tuple[str, str]:
    """Build the system and user prompts for the refinement LLM call.

    Returns:
        (system_prompt, user_prompt) tuple
    """
    principles_text = "\n".join(f"- {p}" for p in config.refinement_principles)

    user_rules_text = ""
    if config.user_rules:
        user_rules_text = "User rules:\n" + "\n".join(
            f"- {r}" for r in config.user_rules
        )

    project_rules_text = ""
    if config.project_rules:
        project_rules_text = "Project rules:\n" + "\n".join(
            f"- {r}" for r in config.project_rules
        )

    system_prompt = _REFINE_SYSTEM_PROMPT.format(
        principles=principles_text,
        user_rules=user_rules_text,
        project_rules=project_rules_text,
    )

    # Build user prompt with context
    parts = []
    context_text = context.to_text()
    if context_text and context_text != "(no context)":
        parts.append(f"## Session Context\n{context_text}")
    parts.append(f"## User Input\n{raw_input}")
    user_prompt = "\n\n".join(parts)

    return system_prompt, user_prompt


def apply_prefix_suffix(prompt: str, config: RefineConfig) -> str:
    """Apply configured prefix and suffix to the final prompt."""
    parts = []
    if config.prefix:
        parts.append(config.prefix.strip())
    parts.append(prompt)
    if config.suffix:
        parts.append(config.suffix.strip())
    return "\n\n".join(parts)



async def refine_prompt(
    raw_input: str,
    context: SessionContext,
    config: RefineConfig,
    llm_caller: Optional[callable] = None,
) -> tuple[str, bool]:
    """Refine a raw user input into a structured prompt.

    Args:
        raw_input: The user's original input.
        context: Compressed session context.
        config: Configuration.
        llm_caller: Async function (system, user, max_tokens) -> str.

    Returns:
        (refined_prompt, was_degraded) tuple.
    """
    if llm_caller is None:
        # No LLM available — return original input unchanged
        return raw_input, True

    system_prompt, user_prompt = build_refine_prompt(raw_input, context, config)

    try:
        result = await llm_caller(
            system_prompt,
            user_prompt,
            config.max_refined_tokens,
        )
        result = result.strip()

        # Sanity check: if LLM returned empty or garbage, fall back to original
        if not result or len(result) < 3:
            return raw_input, True

        return result, False
    except Exception:
        return raw_input, True
