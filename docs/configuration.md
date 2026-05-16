# Configuration Reference

Complete reference for all configuration options, loading order, and provider setup.

## Config Loading Order

`load_config()` in `src/config.py` merges sources in this priority (lowest to highest):

| Priority | Source | Path |
|----------|--------|------|
| 1 | Built-in defaults | Hardcoded in `RefineConfig` class |
| 2 | User config | `~/.prompt-refiner/config.json` |
| 3 | Project config (cwd) | `./.prompt-refiner/config.json` |
| 4 | Project config (cwd) | `./prompt-config.json` |
| 5 | Explicit path | `--config` CLI flag |
| 6 | Environment variables | `ANTHROPIC_API_KEY`, `REFINE_MODEL`, etc. |

Later sources override earlier ones via `_deep_merge()` (recursive dict merge).

## Config Schema

### Top-Level Fields

```json
{
  "active_provider": "",
  "providers": {},
  "refine_model": "",
  "summary_model": "",
  "api_base_url": "",
  "api_key": "",
  "auth_token": "",
  "auto_refine": false,
  "auto_refine_min_length": 20,
  "history_lines": 15,
  "max_summary_tokens": 300,
  "max_refined_tokens": 800,
  "cache_ttl": 300.0,
  "cache_dir": "",
  "prefix": "",
  "suffix": "",
  "skip_commands": ["/no-refine", "/nr", "/skip"],
  "ignore_patterns": ["^\\s*$", "^/[a-z]+"],
  "project_rules": [],
  "user_rules": [],
  "language_rules": {},
  "transcript_path": "",
  "debug_mode": false,
  "log_dir": "",
  "log_format": "jsonl"
}
```

### Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `active_provider` | `str` | `""` | ID of the currently active provider (e.g., `"deepseek"`, `"claude"`) |
| `providers` | `dict[str, ProviderProfile]` | `{}` | Per-provider config profiles |
| `refine_model` | `str` | `""` | Legacy: refinement model name |
| `summary_model` | `str` | `""` | Legacy: summary model name |
| `api_base_url` | `str` | `""` | Legacy: API base URL |
| `api_key` | `str` | `""` | Legacy: API key |
| `auth_token` | `str` | `""` | Legacy: Bearer auth token |
| `auto_refine` | `bool` | `false` | Auto-accept refined prompt (skip TUI) |
| `auto_refine_min_length` | `int` | `20` | Minimum input length to trigger auto-refine |
| `history_lines` | `int` | `15` | Number of transcript entries to read |
| `max_summary_tokens` | `int` | `300` | Max tokens for summary LLM call |
| `max_refined_tokens` | `int` | `800` | Max tokens for refinement LLM call |
| `cache_ttl` | `float` | `300.0` | Summary cache lifetime in seconds |
| `cache_dir` | `str` | `""` | Cache directory (default: `~/.prompt-refiner/`) |
| `prefix` | `str` | `""` | Text prepended to every final prompt |
| `suffix` | `str` | `""` | Text appended to every final prompt |
| `skip_commands` | `list[str]` | `["/no-refine", "/nr", "/skip"]` | Input prefixes that skip refinement |
| `ignore_patterns` | `list[str]` | `["^\\s*$", "^/[a-z]+"]` | Regex patterns that skip refinement |
| `project_rules` | `list[str]` | `[]` | Project-specific rules (NOT passed to refinement LLM) |
| `user_rules` | `list[str]` | `[]` | User-specific rules (NOT passed to refinement LLM) |
| `language_rules` | `dict[str, list[str]]` | `{}` | Per-language rules (NOT passed to refinement LLM) |
| `transcript_path` | `str` | `""` | Explicit path to transcript file |
| `debug_mode` | `bool` | `false` | Enable debug logging |
| `log_dir` | `str` | `""` | Log directory (default: `~/.prompt-refiner/logs/`) |
| `log_format` | `str` | `"jsonl"` | Log format (currently only `jsonl`) |

### ProviderProfile Schema

Each entry in `providers` dict:

```json
{
  "deepseek": {
    "enabled": true,
    "api_key": "sk-...",
    "auth_token": "",
    "base_url": "https://api.deepseek.com/v1",
    "models": {
      "refine": "deepseek-chat",
      "summary": "deepseek-chat"
    },
    "headers": {},
    "extra": {}
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `true` | Whether this provider is active |
| `api_key` | `str` | `""` | API key for this provider |
| `auth_token` | `str` | `""` | Bearer token (alternative to api_key) |
| `base_url` | `str` | `""` | API base URL |
| `models` | `dict[str, str]` | `{}` | Model mapping: `refine`, `summary` |
| `headers` | `dict[str, str]` | `{}` | Extra HTTP headers |
| `extra` | `dict[str, str]` | `{}` | Provider-specific extra params |

### Model Roles

The `models` dict in a provider profile uses these keys:

| Role | Used By | Description |
|------|---------|-------------|
| `refine` | `refine_prompt()` | Model for rewriting user prompts |
| `summary` | `summarize_history()` | Model for compressing session context |

If a role is not set, falls back to legacy fields (`refine_model`, `summary_model`), then to default `claude-haiku-4-5-20251001`.

## Environment Variables

| Variable | Config Field | Type | Description |
|----------|-------------|------|-------------|
| `ANTHROPIC_API_KEY` | `api_key` | `str` | API key |
| `ANTHROPIC_AUTH_TOKEN` | `auth_token` | `str` | Bearer token |
| `ANTHROPIC_BASE_URL` | `api_base_url` | `str` | API base URL |
| `REFINE_MODEL` | `refine_model` | `str` | Refinement model override |
| `SUMMARY_MODEL` | `summary_model` | `str` | Summary model override |
| `PROMPT_REFINE_PROVIDER` | `active_provider` | `str` | Active provider override |
| `PROMPT_REFINE_DEBUG` | `debug_mode` | `bool` | Debug mode (`1`/`true`/`yes`) |
| `CLAUDE_TRANSCRIPT_PATH` | (transcript) | `str` | Explicit transcript file path |

## Legacy Config Migration

Old single-provider configs (without `active_provider`) are auto-migrated by `_migrate_legacy_config()`:

```json
// Input (legacy)
{
  "api_key": "sk-ant-...",
  "refine_model": "claude-haiku-4-5-20251001",
  "api_base_url": "https://proxy.example.com"
}

// Output (migrated)
{
  "active_provider": "custom",
  "providers": {
    "custom": {
      "enabled": true,
      "api_key": "sk-ant-...",
      "auth_token": "",
      "base_url": "https://proxy.example.com",
      "models": {
        "refine": "claude-haiku-4-5-20251001"
      }
    }
  }
}
```

Legacy fields are preserved in the config but shadowed by the provider profile.

## Provider Setup Examples

### DeepSeek

```json
{
  "active_provider": "deepseek",
  "providers": {
    "deepseek": {
      "api_key": "sk-your-deepseek-key",
      "models": {
        "refine": "deepseek-chat",
        "summary": "deepseek-chat"
      }
    }
  }
}
```

### OpenRouter

```json
{
  "active_provider": "openrouter",
  "providers": {
    "openrouter": {
      "api_key": "sk-or-your-key",
      "models": {
        "refine": "anthropic/claude-3.5-haiku",
        "summary": "anthropic/claude-3.5-haiku"
      }
    }
  }
}
```

### Custom OpenAI-Compatible API

```json
{
  "active_provider": "custom",
  "providers": {
    "custom": {
      "api_key": "your-key",
      "base_url": "https://your-api.com/v1",
      "models": {
        "refine": "your-model",
        "summary": "your-model"
      }
    }
  }
}
```

### Using Environment Variables Only

No config file needed. Set env vars:

```bash
export ANTHROPIC_API_KEY="sk-..."
export ANTHROPIC_BASE_URL="https://api.deepseek.com/v1"
export REFINE_MODEL="deepseek-chat"
export SUMMARY_MODEL="deepseek-chat"
```

The tool auto-detects API style from the base URL (anthropic in URL → ANTHROPIC style, otherwise OPENAI style).

## Credential Resolution Detail

`resolve_for_config()` in `src/credentials.py`:

```
1. config.get_api_key()
   └─ provider_profile.api_key
   └─ provider_profile.auth_token
   └─ config.api_key (legacy)
   └─ config.auth_token (legacy)

2. os.environ["ANTHROPIC_API_KEY"]

3. os.environ["ANTHROPIC_AUTH_TOKEN"]

4. (empty string — graceful degradation)
```

`config.get_base_url()`:

```
1. provider_profile.base_url
2. config.api_base_url (legacy)
3. os.environ["ANTHROPIC_BASE_URL"]
4. (empty string)
```

## Prefix and Suffix

The `prefix` and `suffix` fields inject text around every refined prompt:

```json
{
  "prefix": "Prioritize using available skills, MCP tools, and plugins.",
  "suffix": "After completing changes, record key updates to memory."
}
```

Result:
```
Prioritize using available skills, MCP tools, and plugins.

Goal: Fix the 422 error on POST /users
Context: Building REST API with FastAPI

After completing changes, record key updates to memory.
```

Applied by `apply_prefix_suffix()` in `refiner.py`. Only applied to the final prompt (not passed to the refinement LLM).

## Skip Commands and Ignore Patterns

### Skip Commands

Input starts with any of these → refinement skipped entirely:

```json
["/no-refine", "/nr", "/skip"]
```

Match is case-insensitive prefix match.

### Ignore Patterns

Input matches any of these regex patterns → refinement skipped:

```json
["^\\s*$", "^/[a-z]+"]
```

- `^\s*$`: Empty or whitespace-only input
- `^/[a-z]+`: Slash commands (e.g., `/help`, `/clear`)
