English | [中文](README_zh.md)

# Prompt Refiner

A prompt refinement middleware for Claude Code. Intercepts user prompts, reads session context, and produces a clearer, more structured version before Claude processes it.

**Two modes of operation:**
- **CLI mode** (`prf refine`): Interactive TUI with Accept/Edit/Original/Skip review
- **Hook mode** (Claude Code `UserPromptSubmit`): Automatic refinement with two-step block review

Supports **47 built-in providers** across 5 categories: Official, Domestic (China), Gateway, Coding, and Custom.

## Core Workflow

```
User Input
    |
    v
[Skip Check]         -- /no-refine, short inputs, slash commands, greetings
    |
    v
[Read Transcript]    -- Recent Claude Code session history (.jsonl)
    |                   including thinking, tool calls, and results
    v
[Summarize Context]  -- Heuristic extraction of structured fields
    |                   (Task / Tech stack / Tried / Blocker / Modified / Constraints)
    v
[Refine Prompt]      -- LLM rewrites input with conversation context
    |
    v
[Review / Inject]    -- CLI: TUI review (Accept/Edit/Original/Skip)
                       Hook: block with comparison, user chooses a/e/o
```

## Quick Start

```bash
# Install
cd prompt-refiner
pip install -e ".[dev]"

# First-time setup (pick a provider, enter API key)
prf config set

# Refine a prompt (interactive)
prf refine

# Refine with direct input
prf refine "fix the login bug"

# Pipe input
echo "fix the user creation endpoint" | prf refine

# Continuous mode
prf batch

# Show config
prf config show
```

> **Note**: The CLI command is `prf`, not `pr`. The `pr` name conflicts with the GNU `pr` utility.

## Commands

| Command | Description |
|---------|-------------|
| `prf refine [PROMPT]` | Refine a prompt (interactive or with argument) |
| `prf batch` | Continuous refinement loop |
| `prf config show` | Show current configuration (key masked) |
| `prf config set` | Set or update provider via interactive wizard |
| `prf config clear` | Remove saved provider config |
| `prf providers list` | List all 47 built-in providers |
| `prf providers show ID` | Show provider details |
| `prf providers search Q` | Search providers by name/ID/notes |
| `prf clear-cache` | Clear summarization cache |
| `prf hook EVENT` | Hook entry point for Claude Code (legacy, prefer `hook_entry.py`) |

### Refine Options

| Flag | Description |
|------|-------------|
| `--config, -c` | Path to config file |
| `--no-submit, -n` | Don't submit to Claude Code after refinement |
| `--dry-run, -d` | Show what would happen without executing |
| `--output, -o` | Write final prompt to a file |
| `--skip, -s` | Skip refinement entirely |
| `--auto, -a` | Auto-accept refined version (no TUI) |
| `--debug` | Enable debug logging |

## Authentication

### First-Time Setup

```bash
prf config set
```

Launches an interactive wizard that:
1. Shows all 47 providers grouped by category
2. Lets you pick a provider
3. Prompts for API key (masked input)
4. Optionally lets you customize base URL and model
5. Saves to `~/.prompt-refiner/config.json` with 0600 permissions

### Credential Resolution Chain

On startup, credentials are resolved in this order (first match wins):

1. **Saved config**: `~/.prompt-refiner/config.json` → active provider's `api_key`
2. **Saved config**: `~/.prompt-refiner/config.json` → active provider's `auth_token`
3. **Environment**: `ANTHROPIC_API_KEY` env var
4. **Environment**: `ANTHROPIC_AUTH_TOKEN` env var (Bearer token)
5. **Fallback**: `~/.claude/config.json` → `primaryApiKey` (auto-detect)

### Graceful Degradation

If no API key is available:
- **CLI mode**: Skips LLM refinement, applies prefix/suffix only
- **Hook mode**: Passes through to Claude Code without modification (empty stdout)
- **No crashes, no error messages** — the tool always works, just without refinement

### Managing Credentials

```bash
prf config set     # Set or update provider + API key
prf config show    # Show config (key is masked: ********abcd)
prf config clear   # Remove saved provider config
```

## Configuration

Config is loaded in priority order (lowest to highest):

1. **Built-in defaults** (in `src/config.py`)
2. **User config**: `~/.prompt-refiner/config.json`
3. **Project config**: `./prompt-config.json`
4. **Explicit path**: `--config` flag
5. **Environment variables**: `REFINE_MODEL`, `ANTHROPIC_API_KEY`, etc.

### Multi-Provider Config Format

```json
{
  "active_provider": "deepseek",
  "providers": {
    "deepseek": {
      "api_key": "sk-...",
      "base_url": "https://api.deepseek.com/v1",
      "models": {
        "refine": "deepseek-chat",
        "summary": "deepseek-chat"
      }
    },
    "openrouter": {
      "api_key": "sk-or-...",
      "base_url": "https://openrouter.ai/api/v1",
      "models": {
        "refine": "anthropic/claude-3.5-haiku",
        "summary": "anthropic/claude-3.5-haiku"
      }
    }
  },
  "prefix": "Prioritize using available skills, MCP tools, and plugins.",
  "suffix": "After completing changes, record key updates to memory.",
  "auto_refine": false,
  "history_lines": 15,
  "debug_mode": false
}
```

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `active_provider` | `""` | Currently active provider ID |
| `providers` | `{}` | Provider profiles with keys, URLs, models |
| `auto_refine` | `false` | Skip TUI review, auto-accept refined prompt |
| `auto_refine_min_length` | `20` | Min chars to trigger auto-refine |
| `history_lines` | `15` | Transcript entries to read for context |
| `max_summary_tokens` | `300` | Max tokens for context summary LLM call |
| `max_refined_tokens` | `800` | Max tokens for refinement LLM call |
| `prefix` | `""` | Text prepended to every final prompt |
| `suffix` | `""` | Text appended to every final prompt |
| `cache_ttl` | `300` | Summary cache lifetime in seconds |
| `skip_commands` | `["/no-refine", "/nr", "/skip"]` | Commands that skip refinement |
| `ignore_patterns` | `["^\\s*$", "^/[a-z]+"]` | Regex patterns to skip |
| `project_rules` | `[]` | Project-specific rules (not passed to refinement LLM) |
| `user_rules` | `[]` | User-specific rules (not passed to refinement LLM) |
| `debug_mode` | `false` | Enable debug logging |

### Environment Variables

| Variable | Maps To | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | `api_key` | API key for LLM calls |
| `ANTHROPIC_AUTH_TOKEN` | `auth_token` | Bearer token for gateway/proxy |
| `ANTHROPIC_BASE_URL` | `api_base_url` | Custom API endpoint |
| `REFINE_MODEL` | `refine_model` | Override refinement model |
| `SUMMARY_MODEL` | `summary_model` | Override summary model |
| `PROMPT_REFINE_PROVIDER` | `active_provider` | Override active provider |
| `PROMPT_REFINE_DEBUG` | `debug_mode` | Enable debug mode (`1`/`true`/`yes`) |

### Legacy Config Migration

Old single-provider configs are auto-migrated to the multi-provider format:

```json
// Old format (still works)
{
  "api_key": "sk-ant-...",
  "refine_model": "claude-haiku-4-5-20251001",
  "api_base_url": "https://proxy.example.com"
}

// Auto-migrated to:
{
  "active_provider": "custom",
  "providers": {
    "custom": {
      "api_key": "sk-ant-...",
      "base_url": "https://proxy.example.com",
      "models": {
        "refine": "claude-haiku-4-5-20251001"
      }
    }
  }
}
```

## Claude Code Integration (Hooks)

### Setup

Copy `.claude/settings.json` to your project root:

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

The `-X utf8` flag is required on Windows to handle Chinese/Unicode correctly.

### How the Hook Works

**Two-step block flow (Windows compatible):**

1. User submits prompt → Hook reads transcript → LLM refines
2. If refined differs from original → saves to temp file → returns `decision: "block"` to block the prompt
3. Claude Code shows original vs refined comparison, user chooses:
   - `a` = Accept refined
   - `e` = Edit refined
   - `o` = Use original
4. User resubmits choice → Hook returns corresponding `additionalContext`
5. Claude processes the final prompt (won't treat the choice letter as the prompt)

### Hook vs CLI Mode

| Aspect | CLI Mode | Hook Mode |
|--------|----------|-----------|
| TUI review | Yes (Accept/Edit/Original/Skip) | **Block review** (comparison + choice) |
| Output | Submits to Claude Code or pipe | `additionalContext` + `decision: "block"` |
| User sees | Rich terminal diff + choice | Claude shows both versions, user types a/e/o |
| Credential missing | Runs wizard (interactive) | Passes through silently |
| stdin reading | `typer.prompt()` | Char-by-char with `raw_decode` (avoids EOF blocking) |

### Hook Output Format

**When blocking (step 1):**
```json
{
  "decision": "block",
  "reason": "Prompt Refiner has optimized your input.\n\n--- Original ---\nfix the bug\n\n--- Refined ---\nGoal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI\n\nChoose one:\n  a = Accept refined\n  e = Edit refined\n  o = Use original\n\nType your choice and resubmit."
}
```

**When user accepts (step 2):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[PROMPT-REFINER: USER APPROVED]\n\nThe user's message (e.g. 'a') is a selection choice from the prompt refiner, NOT the actual prompt. The real prompt the user wants you to process is:\n\nGoal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI\n\nProcess THIS prompt as if the user typed it directly. Do NOT respond to the selection letter."
  }
}
```

## Supported Providers (47)

### Official

| Provider | ID | Default Model |
|----------|-----|---------------|
| Claude Official | `claude` | claude-haiku-4-5-20251001 |
| GitHub Copilot | `github-copilot` | gpt-4o-mini |
| Codex | `codex` | gpt-4o-mini |
| AWS Bedrock (AKSK) | `bedrock-aksk` | anthropic.claude-3-5-haiku |
| AWS Bedrock (API Key) | `bedrock-apikey` | anthropic.claude-3-5-haiku |

### Domestic (China)

| Provider | ID | Default Model |
|----------|-----|---------------|
| ModelScope | `modelscope` | Qwen/Qwen3-235B-A22B |
| SiliconFlow | `siliconflow` | Qwen/Qwen3-235B-A22B |
| DMXAPI | `dmxapi` | claude-haiku-4-5-20251001 |
| 优云智算 | `youyun` | qwen2.5-72b-instruct |
| 胜算云 | `shengsuan` | claude-haiku-4-5-20251001 |
| Zhipu GLM | `zhipu` | glm-4-flash |
| Bailian | `bailian` | qwen-plus |
| Bailian For Coding | `bailian-coding` | qwen-code-latest |
| Kimi | `kimi` | moonshot-v1-8k |
| Kimi For Coding | `kimi-coding` | kimi-latest |
| StepFun | `stepfun` | step-1-flash |
| KAT-Coder | `katcoder` | kat-coder-pro |
| Longcat | `longcat` | longcat-coder |
| MiniMax | `minimax` | MiniMax-Text-01 |
| DouBaoSeed | `doubao` | doubao-1.5-pro |
| BaiLing | `bailing` | bailing-coder |
| Xiaomi MiMo | `mimo` | mimo-v2.5-pro |

### Gateway

| Provider | ID | Default Model |
|----------|-----|---------------|
| AiHubMix | `aihubmix` | claude-haiku-4-5-20251001 |
| OpenRouter | `openrouter` | anthropic/claude-3.5-haiku |
| TheRouter | `therouter` | claude-3-5-haiku-latest |
| Novita AI | `novita` | meta-llama/llama-3.1-8b-instruct |
| DeepSeek | `deepseek` | deepseek-chat |
| + 3 more | | |

### Coding

| Provider | ID | Default Model |
|----------|-----|---------------|
| PackyCode | `packycode` | claude-haiku-4-5-20251001 |
| Cubence | `cubence` | claude-haiku-4-5-20251001 |
| + 11 more | | |

### Custom

| Provider | ID | Notes |
|----------|-----|-------|
| 自定义配置 | `custom` | Any OpenAI-compatible API, manually configured |

Use `prf providers list` to see all 47 providers, or `prf providers search <keyword>` to filter.

## Project Structure

```
prompt-refiner/
├── src/
│   ├── __init__.py
│   ├── app.py                # CLI entry point (Typer), all commands
│   ├── config.py             # Pydantic config, layered loading, legacy migration
│   ├── credentials.py        # Credential resolution chain
│   ├── models.py             # Data models: UserChoice, RefineResult, SessionContext
│   ├── refiner.py            # Core refinement: heuristic + LLM, should_refine check
│   ├── llm.py                # LLM caller using provider adapter layer
│   ├── summarizer.py         # Context compression (LLM + heuristic fallback)
│   ├── transcript_reader.py  # Claude Code .jsonl transcript parser
│   ├── ui.py                 # Rich TUI: diff display, Accept/Edit/Original/Skip
│   ├── executor.py           # Submit to claude CLI, write to file
│   ├── cache.py              # File-backed summarization cache
│   ├── logger.py             # Structured JSONL logging
│   ├── hook_integration.py   # Hook logic: handle_hook, build_hook_response
│   ├── hook_entry.py         # Hook __main__: stdin reading, arg parsing
│   ├── hook_terminal.py      # CONIN$/CONOUT$ terminal bypass (Windows)
│   ├── setup_wizard.py       # Provider selection + API key wizard
│   └── providers/
│       ├── __init__.py       # Public API re-exports
│       ├── models.py         # ProviderConfig, ApiStyle, AuthScheme
│       ├── builtin.py        # 47 built-in provider definitions
│       ├── registry.py       # Provider registry (singleton)
│       └── adapters.py       # Unified adapter: OPENAI/ANTHROPIC/BEDROCK/CUSTOM
├── tests/                    # 170 tests (168 passing, 2 pre-existing failures)
├── examples/                 # Hook payload examples
├── docs/                     # Extended documentation
├── .claude/
│   ├── settings.json         # Hook configuration for Claude Code
│   └── settings.local.json.example
├── prompt-config.json        # Project-level config template
├── pyproject.toml            # Build config, entry points
├── install.sh                # Installation script
└── README.md
```

## Extending: Adding a New Provider

### Via Config (Recommended)

```json
{
  "active_provider": "custom",
  "providers": {
    "custom": {
      "api_key": "your-key",
      "base_url": "https://your-provider.com/v1",
      "models": {
        "refine": "your-model",
        "summary": "your-model"
      }
    }
  }
}
```

### Via Code

```python
from src.providers import get_registry, ProviderConfig, ApiStyle, AuthScheme, ModelDefaults

registry = get_registry()
registry.register(ProviderConfig(
    id="my-provider",
    display_name="My Provider",
    category="custom",
    api_style=ApiStyle.OPENAI,
    base_url="https://my-provider.com/v1",
    auth_scheme=AuthScheme.BEARER,
    default_models=ModelDefaults(refine="my-model"),
))
```

### API Styles

| Style | Used By | Endpoint Format |
|-------|---------|-----------------|
| `OPENAI` | Most providers | `{base}/chat/completions` |
| `ANTHROPIC` | Claude Official | `{base}/v1/messages` |
| `BEDROCK` | AWS Bedrock | `{base}/model/{model}/invoke` |
| `CUSTOM` | Custom providers | Configurable |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_refiner.py -v
```

## Known Limitations

1. **Hook mode uses two-step block flow**: Since Claude Code's subprocess cannot access CONIN$ for interactive terminal input on Windows, the hook uses `decision: "block"` to block the prompt and show a comparison for the user to choose from.

2. **stdin EOF handling**: Claude Code may not close stdin after piping JSON. `hook_entry.py` reads char-by-char with `json.JSONDecoder.raw_decode()` to detect complete JSON without blocking on EOF.

3. **Windows encoding**: The `-X utf8` Python flag is required in the hook command for correct Chinese/Unicode handling on Windows.

4. **Model quality matters**: Weak models may answer questions instead of rewriting prompts. The refiner includes conversational response rejection as a safety net, but a capable model produces better results.

## License

MIT
