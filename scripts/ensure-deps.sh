#!/usr/bin/env bash
# SessionStart hook: ensure Python venv and dependencies are installed.
# Runs every session but exits fast (0.01s) if already up to date.
# Reads CLAUDE_PLUGIN_ROOT and CLAUDE_PLUGIN_DATA from environment.
set -e

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DATA_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/prompt-refiner}"
VENV_DIR="${DATA_DIR}/.venv"
REQ_FILE="${PLUGIN_ROOT}/requirements.txt"
STAMP_FILE="${DATA_DIR}/.deps-stamp"

# Platform detection: Windows (MSYS/Git Bash) uses Scripts/, others use bin/
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    VENV_BIN="${VENV_DIR}/Scripts"
    VENV_PYTHON="${VENV_BIN}/python.exe"
    VENV_PIP="${VENV_BIN}/pip.exe"
    ;;
  *)
    VENV_BIN="${VENV_DIR}/bin"
    VENV_PYTHON="${VENV_BIN}/python"
    VENV_PIP="${VENV_BIN}/pip"
    ;;
esac

# Fast path: check if dependencies are already installed and up to date
if [ -f "$STAMP_FILE" ] && [ -d "$VENV_DIR" ] && diff -q "$REQ_FILE" "$STAMP_FILE" >/dev/null 2>&1; then
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
fi

# Find Python
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
fi

# Create data directory
mkdir -p "$DATA_DIR"

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi

# Install dependencies
"$VENV_PIP" install -q --disable-pip-version-check -r "$REQ_FILE" 2>/dev/null

# Install prompt-refiner package itself
"$VENV_PIP" install -q --disable-pip-version-check -e "$PLUGIN_ROOT" 2>/dev/null

# Write stamp
cp "$REQ_FILE" "$STAMP_FILE"

echo '{"continue":true,"suppressOutput":true}'
