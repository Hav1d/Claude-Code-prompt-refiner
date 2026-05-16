---
description: Refine a user prompt into a structured task brief for Claude Code. Use when the user asks to "refine", "improve", "optimize", "structure", or "rewrite" a prompt, or when a prompt is vague and could benefit from context-aware clarification.
---

# Prompt Refiner

Refine user prompts into structured, actionable task briefs before Claude processes them.

## How It Works

1. Reads recent conversation history (transcript) for context
2. Compresses context into structured fields (Task, Tech Stack, Blocker, etc.)
3. Uses LLM to rewrite the prompt as a clear task brief
4. Presents the result for user review

## Usage

### CLI Mode

```bash
# Interactive refinement
prf refine

# Refine a specific prompt
prf refine "fix the login bug"

# Pipe input
echo "fix the user creation endpoint" | prf refine
```

### Hook Mode (Automatic)

When installed as a Claude Code plugin, prompts are automatically intercepted and refined via the `UserPromptSubmit` hook. The user sees a comparison and can accept, edit, or use the original.

## Configuration

The plugin uses `userConfig` for API key and provider settings, configured during installation.

To change configuration manually:
```bash
prf config set
```

## Skip Refinement

Prefix with `/no-refine` or `/nr` to skip refinement for a single prompt.
