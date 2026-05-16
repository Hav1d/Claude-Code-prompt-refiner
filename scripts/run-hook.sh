#!/usr/bin/env bash
# UserPromptSubmit hook: run prompt-refiner on user input.
set -e

DATA_DIR="${1:-${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/prompt-refiner}}"
PLUGIN_ROOT="${2:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
VENV_PYTHON="${DATA_DIR}/.venv/bin/python"

# If venv doesn't exist yet, pass through silently
if [ ! -f "$VENV_PYTHON" ]; then
  exit 0
fi

# Build runtime config from userConfig environment variables
CONFIG_FILE="${DATA_DIR}/runtime-config.json"
PROVIDER="${CLAUDE_PLUGIN_OPTION_PROVIDER:-deepseek}"
API_KEY="${CLAUDE_PLUGIN_OPTION_API_KEY:-}"
BASE_URL="${CLAUDE_PLUGIN_OPTION_BASE_URL:-}"

if [ -n "$API_KEY" ]; then
  cat > "$CONFIG_FILE" << JSONEOF
{
  "active_provider": "${PROVIDER}",
  "providers": {
    "${PROVIDER}": {
      "api_key": "${API_KEY}",
      "base_url": "${BASE_URL}"
    }
  },
  "history_lines": 50
}
JSONEOF
else
  # No API key from userConfig, try without config file (env var fallback)
  CONFIG_FILE=""
fi

# Execute the hook
if [ -n "$CONFIG_FILE" ]; then
  exec "$VENV_PYTHON" -X utf8 -m src.hook_entry UserPromptSubmit --config "$CONFIG_FILE"
else
  exec "$VENV_PYTHON" -X utf8 -m src.hook_entry UserPromptSubmit
fi
