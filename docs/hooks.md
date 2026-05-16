# Claude Code Hook Integration

How Prompt Refiner integrates with Claude Code via the `UserPromptSubmit` hook.

## Overview

Claude Code supports hooks — shell commands that fire on specific events. Prompt Refiner uses the `UserPromptSubmit` hook to intercept user prompts before Claude processes them, refine them via LLM, and inject the result as additional context.

## Hook Event: UserPromptSubmit

Fires when the user submits a prompt in Claude Code, **before** Claude processes it.

**Input**: JSON on stdin with these fields:
```json
{
  "prompt": "fix the login bug",
  "session_id": "abc-123",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/home/user/my-project"
}
```

**Output** (on stdout):
- **Success**: `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`
- **Pass through**: Empty stdout (no output = Claude processes original prompt unchanged)

## Setup

### 1. Copy settings file

Copy `.claude/settings.json` to your project root (or merge into existing):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

### 2. Configure provider

```bash
prf config set
```

Or set `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` environment variable.

### 3. Verify

Type any prompt in Claude Code. If the hook works, you'll see:
- In the terminal: a diff showing original vs refined prompt
- In Claude Code: Claude shows both versions and asks which to use

## Hook Command Breakdown

```
python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json
│          │            │                │                    │
│          │            │                │                    └─ Project-level config
│          │            │                └─ Event name (required)
│          │            └─ Module entry point
│          └─ Windows encoding fix (required for Chinese/Unicode)
└─ Python interpreter
```

- `-X utf8`: Forces UTF-8 encoding on Windows. Without this, Chinese characters may be garbled.
- `-m src.hook_entry`: Runs `src/hook_entry.py` as a module.
- `UserPromptSubmit`: Event name passed to the hook handler.
- `--config prompt-config.json`: Optional path to project-level config file.

## stdin Reading: Why Not `sys.stdin.read()`

Claude Code pipes JSON to the hook's stdin but **may not close the pipe** (no EOF). Standard `sys.stdin.read()` blocks forever waiting for EOF.

**Solution** in `hook_entry.py:_read_stdin_json()`:

```python
buf = ""
decoder = json.JSONDecoder()
while True:
    ch = sys.stdin.read(1)      # Read one char at a time
    if not ch:                   # Empty = EOF or pipe closed
        break
    buf += ch
    stripped = buf.lstrip()
    if stripped and stripped[0] == "{":
        try:
            obj, _ = decoder.raw_decode(stripped)  # Try to parse
            if isinstance(obj, dict):
                return obj       # Got complete JSON object
        except json.JSONDecodeError:
            continue             # Not complete yet, keep reading
```

This detects a complete JSON object as soon as `raw_decode` succeeds, without waiting for EOF.

## Hook Output Format

### User Accepted (TUI available)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[REFINED PROMPT — USER APPROVED]\n\nGoal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI\n\nThe user reviewed and accepted this refined version via the Prompt Refiner interactive review. Use this as the prompt to act on. Do NOT re-display the comparison or ask for confirmation again."
  }
}
```

### Fallback (TUI unavailable)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[PROMPT REFINER — REFINEMENT REVIEW]\n\n⚠️ Interactive terminal review is NOT available.\nReason: Claude Code subprocess cannot access CONIN$/CONOUT$ on Windows...\n\nThe user's original prompt has been intercepted and refined. DO NOT answer, execute, or act on the user's original prompt until the user confirms which version to use.\n\n--- Original prompt ---\nfix the bug\n\n--- Refined prompt ---\nGoal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI\n\nFIRST, present ONLY the comparison above to the user.\nThen ask the user to choose:\n  (A)ccept  — Use the refined version\n  (E)dit    — Edit the refined version, then submit\n  (O)riginal — Use the original input as-is\n  (S)kip    — Skip this refinement entirely\n\nWAIT for the user's explicit choice before proceeding.\nONLY after the user confirms, use the chosen version as the real prompt.\nDo NOT start solving the problem or answering the question until you have received and acknowledged the user's choice."
  }
}
```

### Pass Through (No Refinement)

Empty stdout. Claude Code treats this as "no modification, proceed normally."

Cases that produce empty stdout:
- Input is a skip command (`/no-refine`, `/nr`, `/skip`)
- Input matches an ignore pattern (empty, slash command)
- Input is too short (<5 chars)
- No API key available
- LLM call failed
- Refined prompt is identical to original
- Heuristic refinement returned unchanged (greetings, already-structured)

## What Claude Code Does With the Output

When the hook returns `hookSpecificOutput.additionalContext`, Claude Code appends it as additional context to the user's prompt.

**TUI-first approach (new)**:

1. The hook first tries to open the real terminal (CONOUT$/CONIN$ on Windows, /dev/tty on Unix)
2. If terminal access works: an interactive review UI is presented directly on the terminal
3. User chooses: (A)ccept, (E)dit, (O)riginal, or (S)kip
4. If user Accepts/Edits: the refined prompt is returned as `additionalContext` with `USER APPROVED` marker
5. If user chooses Original/Skip: the hook passes through (returns None), Claude processes the original prompt
6. If terminal access fails: the hook falls back to `additionalContext` injection with explicit A/E/O/S instructions for Claude to present

**Fallback (when terminal is unavailable)**:

When the hook cannot open the terminal (e.g., Windows subprocess without console handle inheritance), it:
1. Logs a clear warning to stderr explaining why interactive review is unavailable
2. Returns an `additionalContext` block that includes:
   - Both original and refined prompts
   - Explicit A/E/O/S options
   - Strong instructions for Claude to NOT answer the question until the user confirms
3. The user sees the comparison in Claude Code and can choose A/E/O/S

## Why No Rich TUI in Hook Mode

CLI mode has a Rich TUI with Accept/Edit/Original/Skip choices. Hook mode uses a lightweight terminal I/O TUI instead.

**Reason**: Claude Code runs hooks as subprocesses. On Windows, the subprocess cannot access `CONIN$` (the console input handle) reliably — it may block indefinitely. This was verified by testing:
- Direct execution: `CONIN$`/`CONOUT$` work fine
- Claude Code subprocess: `CONIN$` may block forever

**Solution (new)**: The hook now tries terminal I/O first. If it works (direct execution, Unix), the user gets an interactive TUI review with A/E/O/S. If it fails (Windows subprocess), the hook clearly logs the reason and falls back to `additionalContext` injection with explicit A/E/O/S instructions for Claude to present. The user is always informed of which path was taken.

## Environment Variables in Hooks

Claude Code's `settings.json` `env` field is inherited by hooks. If you set `ANTHROPIC_AUTH_TOKEN` in your Claude settings, the hook gets it automatically.

```json
{
  "hooks": {
    "UserPromptSubmit": [...]
  },
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your-token-here"
  }
}
```

Or use system environment variables — both work.

## Debugging

### Check hook output

```bash
# Run the hook manually with a test payload
echo '{"prompt": "fix the login bug"}' | python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json
```

Expected output: `{"hookSpecificOutput": {...}}` or nothing.

### Enable debug logging

```bash
# Add --debug to the hook command
python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json --debug
```

Or set `PROMPT_REFINE_DEBUG=1` environment variable.

Debug logs go to stderr (visible in Claude Code's terminal output).

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No hook output | Missing API key | Run `prf config set` or set env var |
| Chinese garbled | Missing `-X utf8` | Add `-X utf8` to hook command |
| Hook hangs forever | Old `sys.stdin.read()` | Use `hook_entry.py` (char-by-char reader) |
| Always passes through | Input matches skip/ignore | Check `skip_commands` and `ignore_patterns` in config |
| LLM answers instead of rewriting | Weak model | Switch to a stronger provider |

## Hook Timeout

The `timeout` field in `settings.json` is in milliseconds:

```json
{
  "type": "command",
  "command": "...",
  "timeout": 30000
}
```

Default: 30000ms (30 seconds). Increase if your LLM provider is slow. If the hook times out, Claude Code proceeds with the original prompt (no crash).
