#!/usr/bin/env bash
set -euo pipefail

echo "=== Prompt Refiner Installer ==="
echo ""

# Check Python
if ! command -v python &> /dev/null; then
    echo "ERROR: Python 3.11+ is required."
    exit 1
fi

PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYTHON_VERSION"

# Install in development mode
echo ""
echo "Installing dependencies..."
pip install -e ".[dev]" --quiet

# Check for existing credentials
echo ""
CONFIG_FILE="$HOME/.prompt-refiner/config.json"
if [ -f "$CONFIG_FILE" ]; then
    PROVIDER=$(python -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('active_provider', ''))" 2>/dev/null || echo "")
    if [ -n "$PROVIDER" ]; then
        echo "Provider '$PROVIDER' configured in $CONFIG_FILE"
    else
        # Check legacy format
        LEGACY_KEY=$(python -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('api_key', ''))" 2>/dev/null || echo "")
        if [ -n "$LEGACY_KEY" ]; then
            echo "Legacy API key found — will auto-migrate on first run."
        else
            echo "No provider configured. Run 'pr config set' to set up."
        fi
    fi
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "Using ANTHROPIC_API_KEY from environment."
elif [ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
    echo "Using ANTHROPIC_AUTH_TOKEN from environment."
else
    echo "No API key found. Run 'pr config set' to pick a provider and enter your key."
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Quick start:"
echo "  pr config set                       # pick a provider, enter API key"
echo "  pr refine 'your prompt here'        # refine a prompt"
echo ""
echo "Usage:"
echo "  pr refine                           # interactive input"
echo "  pr refine 'your prompt'             # direct input"
echo "  pr batch                            # continuous mode"
echo "  pr config show                      # show current config"
echo "  pr config set                       # set/update provider"
echo "  pr config clear                     # remove saved config"
echo "  pr providers list                   # list all 47 providers"
echo "  pr providers show <id>              # show provider details"
echo "  pr providers search <query>         # search providers"
echo "  pr clear-cache                      # clear cache"
echo ""
echo "Configuration:"
echo "  User config:    ~/.prompt-refiner/config.json"
echo "  Project config: ./prompt-config.json"
echo ""
echo "Claude Code integration:"
echo "  Copy .claude/settings.json to your project's .claude/ directory"
echo "  The hook uses UserPromptSubmit to refine prompts before Claude sees them."
echo ""
