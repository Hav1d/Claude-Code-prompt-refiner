# Prompt Refiner

A prompt refinement middleware for Claude Code. Intercepts your prompts, reads session context, and produces a clearer, more structured version before submitting to Claude Code.

Supports **47 built-in providers** — from Claude Official to OpenRouter, DeepSeek, SiliconFlow, AWS Bedrock, and more.

## Why?

- **Vague inputs** get transformed into actionable, structured prompts
- **Session context** is automatically compressed and included
- **Token savings** by avoiding redundant context in every prompt
- **Full control** — accept, edit, use original, or skip at any time
- **Multi-provider** — use any LLM provider for refinement, not just Anthropic

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# First-time setup (pick a provider, enter API key)
pr config set

# Use interactively
pr refine

# Use with direct input
pr refine "fix the login bug"

# Pipe input
echo "fix the user creation endpoint" | pr refine

# Continuous mode
pr batch

# Show config
pr config show

# Clear cache
pr clear-cache
```

## Supported Providers

47 built-in providers across 5 categories:

### Official

| Provider | ID | Default Model | Notes |
|----------|-----|---------------|-------|
| Claude Official | `claude` | claude-haiku-4-5-20251001 | Anthropic direct API |
| GitHub Copilot | `github-copilot` | gpt-4o-mini | Requires Copilot subscription |
| Codex | `codex` | gpt-4o-mini | OpenAI Codex |
| AWS Bedrock (AKSK) | `bedrock-aksk` | anthropic.claude-3-5-haiku | AWS AKSK auth |
| AWS Bedrock (API Key) | `bedrock-apikey` | anthropic.claude-3-5-haiku | Bearer token auth |

### Domestic (China)

| Provider | ID | Default Model |
|----------|-----|---------------|
| ModelScope | `modelscope` | Qwen/Qwen3-235B-A22B |
| SiliconFlow | `siliconflow` | Qwen/Qwen3-235B-A22B |
| SiliconFlow en | `siliconflow-en` | Qwen/Qwen3-235B-A22B |
| DMXAPI | `dmxapi` | claude-haiku-4-5-20251001 |
| 优云智算 | `youyun` | qwen2.5-72b-instruct |
| 胜算云 | `shengsuan` | claude-haiku-4-5-20251001 |
| Zhipu GLM | `zhipu` | glm-4-flash |
| Zhipu GLM en | `zhipu-en` | glm-4-flash |
| Bailian | `bailian` | qwen-plus |
| Bailian For Coding | `bailian-coding` | qwen-code-latest |
| Kimi | `kimi` | moonshot-v1-8k |
| Kimi For Coding | `kimi-coding` | kimi-latest |
| StepFun | `stepfun` | step-1-flash |
| KAT-Coder | `katcoder` | kat-coder-pro |
| Longcat | `longcat` | longcat-coder |
| MiniMax | `minimax` | MiniMax-Text-01 |
| MiniMax en | `minimax-en` | MiniMax-Text-01 |
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
| Nvidia | `nvidia` | meta/llama-3.1-8b-instruct |
| PIPILM | `pipilm` | claude-haiku-4-5-20251001 |
| DeepSeek | `deepseek` | deepseek-chat |
| CrazyRouter | `crazyrouter` | claude-haiku-4-5-20251001 |

### Coding

| Provider | ID | Default Model |
|----------|-----|---------------|
| PackyCode | `packycode` | claude-haiku-4-5-20251001 |
| Cubence | `cubence` | claude-haiku-4-5-20251001 |
| AIGoCode | `aigocode` | claude-haiku-4-5-20251001 |
| RightCode | `rightcode` | claude-haiku-4-5-20251001 |
| AICodeMirror | `aicodemirror` | claude-haiku-4-5-20251001 |
| AICoding | `aicoding` | claude-haiku-4-5-20251001 |
| SSAiCode | `ssaicode` | claude-haiku-4-5-20251001 |
| Micu | `micu` | claude-haiku-4-5-20251001 |
| X-Code API | `xcodeapi` | claude-haiku-4-5-20251001 |
| CTok.ai | `ctok` | claude-haiku-4-5-20251001 |
| DDSHub | `ddshub` | claude-haiku-4-5-20251001 |
| E-FlowCode | `eflowcode` | claude-haiku-4-5-20251001 |
| LionCCAPI | `lionccapi` | claude-haiku-4-5-20251001 |

### Custom

| Provider | ID | Notes |
|----------|-----|-------|
| 自定义配置 | `custom` | Any OpenAI-compatible API, manually configured |

## Authentication

### First-Time Setup

```bash
pr config set
```

This launches an interactive wizard that:
1. Shows all 47 providers grouped by category
2. Lets you pick a provider
3. Prompts for API key (masked input)
4. Optionally lets you customize base URL and model
5. Saves everything to `~/.prompt-refiner/config.json`

### Credential Resolution Chain

On startup, credentials are resolved in this order:

1. **Saved config**: `~/.prompt-refiner/config.json` → provider `api_key`
2. **Environment**: `ANTHROPIC_API_KEY` env var
3. **Environment**: `ANTHROPIC_AUTH_TOKEN` env var (Bearer token for gateway/proxy)
4. **Fallback**: `~/.claude/config.json` → `primaryApiKey` (auto-detect)

### Managing Credentials

```bash
pr config set     # Set or update provider + API key
pr config show    # Show config (key is masked)
pr config clear   # Remove saved provider config
```

### Graceful Degradation

If no API key is available, Prompt Refiner still works:
- **CLI mode**: Skips LLM refinement, applies basic structure only
- **Hook mode**: Passes through to Claude Code without modification
- **No crashes, no errors** — the tool always works, just without refinement

## Provider Commands

```bash
# List all providers
pr providers list

# Show provider details
pr providers show deepseek

# Search providers
pr providers search silicon
```

## Switching Providers

```bash
# Re-run the wizard to pick a different provider
pr config set

# Or edit ~/.prompt-refiner/config.json directly
{
  "active_provider": "deepseek",
  "providers": {
    "deepseek": {
      "api_key": "sk-...",
      "models": {
        "refine": "deepseek-chat",
        "summary": "deepseek-chat"
      }
    }
  }
}
```

## How It Works

```
User Input
    │
    ▼
┌─────────────────┐
│ Skip Check       │  ← /no-refine, short inputs, slash commands
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Read Transcript  │  ← Recent Claude Code session history
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Summarize        │  ← Compress context into structured summary
│ Context          │    (cached per session)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Refine Prompt    │  ← LLM rewrites input with context + rules
│ (via provider    │    Uses configured provider's API
│  adapter)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TUI Review       │  ← Accept / Edit / Original / Skip
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply Rules      │  ← Prefix + Suffix injection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Submit to        │  ← claude CLI or pipe
│ Claude Code      │
└─────────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `pr refine [PROMPT]` | Refine a prompt (interactive or with argument) |
| `pr batch` | Continuous refinement loop |
| `pr config show` | Show current configuration |
| `pr config set` | Set or update provider via wizard |
| `pr config clear` | Remove saved provider config |
| `pr providers list` | List all built-in providers |
| `pr providers show ID` | Show provider details |
| `pr providers search Q` | Search providers by name/ID |
| `pr clear-cache` | Clear summarization cache |
| `pr hook EVENT` | Hook entry point for Claude Code integration |

### Refine Options

| Flag | Description |
|------|-------------|
| `--config, -c` | Path to config file |
| `--no-submit, -n` | Don't submit to Claude Code after refinement |
| `--dry-run, -d` | Show what would happen without executing |
| `--output, -o` | Write final prompt to a file |
| `--skip, -s` | Skip refinement entirely |
| `--auto, -a` | Auto-accept refined version |
| `--debug` | Enable debug logging |

## Configuration

Config is loaded in priority order (lowest to highest):

1. **Built-in defaults**
2. **User config**: `~/.prompt-refiner/config.json`
3. **Project config**: `./prompt-config.json`
4. **Environment variables**: `REFINE_MODEL`, `SUMMARY_MODEL`, etc.

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

### Legacy Config (Auto-Migrated)

Old single-provider configs are automatically migrated:

```json
{
  "api_key": "sk-ant-...",
  "refine_model": "claude-haiku-4-5-20251001",
  "api_base_url": "https://proxy.example.com"
}
```

Becomes:

```json
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

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `active_provider` | `""` | Currently active provider ID |
| `providers` | `{}` | Provider profiles with keys, URLs, models |
| `auto_refine` | `false` | Skip TUI, auto-accept |
| `auto_refine_min_length` | `20` | Min chars to trigger auto-refine |
| `history_lines` | `15` | Transcript entries to read |
| `prefix` | `""` | Text prepended to every prompt |
| `suffix` | `""` | Text appended to every prompt |
| `cache_ttl` | `300` | Summary cache lifetime (seconds) |

## Claude Code Integration

### Hooks (UserPromptSubmit)

Copy `.claude/settings.json` to your project:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m src.hook_entry UserPromptSubmit",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

The hook fires on every user prompt, before Claude processes it. You'll see a terminal review showing the diff and refined prompt, with options to Accept/Edit/Original/Skip. The chosen version is injected as `additionalContext` — Claude sees both the original and the refined version.

### Hook Output Format

The hook uses the official Claude Code format:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Goal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI"
  }
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for LLM calls |
| `ANTHROPIC_AUTH_TOKEN` | Bearer token for gateway/proxy |
| `ANTHROPIC_BASE_URL` | Custom API endpoint |
| `REFINE_MODEL` | Override refinement model |
| `SUMMARY_MODEL` | Override summary model |
| `PROMPT_REFINE_PROVIDER` | Override active provider |
| `PROMPT_REFINE_DEBUG` | Enable debug mode |

## Extending: Adding a New Provider

To add a custom provider that isn't in the built-in registry:

1. Use the `custom` provider in your config:

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

2. Or register programmatically:

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

The adapter layer supports 4 API styles:

| Style | Used By | Format |
|-------|---------|--------|
| `OPENAI` | Most providers | OpenAI chat completions format |
| `ANTHROPIC` | Claude Official | Anthropic messages format |
| `BEDROCK` | AWS Bedrock | AWS-signed requests |
| `CUSTOM` | Custom providers | Configurable format |

## Refinement Principles

The refiner follows these built-in rules:

1. Does NOT expand user intent beyond what was stated
2. Does NOT guess or fabricate details
3. Does NOT bloat short inputs
4. Preserves all error messages, paths, commands, and framework names
5. Asks clarification questions for ambiguous input
6. Keeps output short, clear, and actionable
7. Returns already-precise inputs unchanged
8. Structures output as: Goal / Context / Constraints

## Logging

Every refinement is logged to `~/.prompt-refiner/logs/`:

```json
{
  "timestamp": "2026-05-13T10:30:00Z",
  "original_input": "fix the bug",
  "context_summary": "Task: Build REST API\nBlocker: 422 error",
  "refined_prompt": "Goal: Fix the 422 error on POST /users\nContext: Building REST API with FastAPI",
  "final_prompt": "Goal: Fix the 422 error...",
  "user_choice": "accept",
  "duration_ms": 1500.0,
  "error": null,
  "degraded": false
}
```

## Project Structure

```
prompt-refiner/
├── src/
│   ├── __init__.py
│   ├── app.py              # CLI entry point (Typer)
│   ├── config.py           # Configuration loading (Pydantic)
│   ├── credentials.py      # Credential resolution chain
│   ├── models.py           # Data models
│   ├── transcript_reader.py # Claude Code transcript parser
│   ├── summarizer.py       # Context compression
│   ├── refiner.py          # Core refinement logic
│   ├── llm.py              # LLM caller (uses provider adapter)
│   ├── ui.py               # Rich TUI interface
│   ├── executor.py         # Claude Code submission
│   ├── cache.py            # File-backed caching
│   ├── logger.py           # Structured logging
│   ├── hook_integration.py # Claude Code hooks (UserPromptSubmit)
│   ├── hook_entry.py       # Hook __main__ entry point
│   ├── hook_terminal.py    # Terminal I/O for hook TUI review
│   ├── setup_wizard.py     # Provider selection + API key wizard
│   └── providers/          # Multi-provider system
│       ├── __init__.py
│       ├── models.py       # ProviderConfig, ApiStyle, AuthScheme
│       ├── builtin.py      # 47 built-in provider definitions
│       ├── registry.py     # Provider registry (singleton)
│       └── adapters.py     # Unified adapter layer
├── tests/
├── examples/
├── docs/
├── .claude/
│   ├── settings.json
│   └── settings.local.json.example
├── prompt-config.json
├── pyproject.toml
├── install.sh
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

## License

MIT
