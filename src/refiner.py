"""Core prompt refinement logic."""

from __future__ import annotations

import re
from typing import Optional

from .config import RefineConfig
from .models import SessionContext

_REFINE_SYSTEM_PROMPT = """You are a prompt REWRITER for Claude Code. Your ONLY job is to take user input and output a REWRITTEN version that is clearer and more actionable.

CRITICAL RULES:
1. You NEVER answer questions. You NEVER respond conversationally. You ONLY rewrite.
2. You NEVER ask clarifying questions. You NEVER use "[Clarify]" prefix.
3. You NEVER produce greetings, pleasantries, or conversational responses.
4. If the input is a simple greeting or small talk (hello, hi, hey, 你好, etc.), return it EXACTLY unchanged.
5. If the input is already a clear instruction, return it nearly unchanged.
6. If the input is vague, INFER the most likely intent and rewrite as a clear task.
7. Preserve the original language (Chinese → Chinese, English → English).

Your output is a PROMPT that will be given to Claude Code to execute. It must be an instruction, not a conversation.

## Examples

Input: "hello"
Output: "hello"

Input: "hi"
Output: "hi"

Input: "fix the login bug"
Output: "Goal: Fix the login bug. Investigate the root cause, implement a fix, and verify it works."

Input: "你看看这个结构是啥，我看不懂"
Output: "请检查项目的目录结构和主要文件，解释整体架构设计、各模块的功能和它们之间的关系。"

Input: "refactor this"
Output: "Goal: Refactor the current code for better readability and maintainability. Apply clean code principles, extract functions where needed, and ensure all tests still pass."

Input: "这个报错怎么解决"
Output: "分析当前遇到的错误，找出根本原因，提供修复方案并实施修复。"

Input: "帮我写个函数"
Output: "编写一个函数。请说明函数的用途、输入参数和预期输出。"

## Structure Template (use when applicable)
Goal: <what to accomplish>
Context: <relevant background>
Constraints: <limitations>

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
