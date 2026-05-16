"""Credential resolution — single source of truth for all modules.

Resolution chain:
1. Active provider profile's api_key / auth_token
2. Legacy config api_key / auth_token
3. CLAUDE_PLUGIN_OPTION_API_KEY (from Claude Code plugin userConfig)
4. ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN env vars
5. ~/.claude/config.json -> primaryApiKey (optional fallback)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

_CLAUDE_CONFIG_PATH = Path.home() / ".claude" / "config.json"


def resolve_credentials(
    config_api_key: str = "",
    config_auth_token: str = "",
) -> tuple[Optional[str], Optional[str]]:
    """Resolve credentials from explicit values or env vars.

    Returns (credential, auth_type) or (None, None).
    """
    if config_api_key:
        return config_api_key, "api_key"
    if config_auth_token:
        return config_auth_token, "bearer"

    # Claude Code plugin userConfig (set by Claude Code as env var)
    plugin_key = os.environ.get("CLAUDE_PLUGIN_OPTION_API_KEY", "").strip()
    if plugin_key:
        return plugin_key, "api_key"

    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key, "api_key"

    env_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    if env_token:
        return env_token, "bearer"

    claude_key = _read_claude_config_key()
    if claude_key:
        return claude_key, "api_key"

    return None, None


def resolve_for_config(config: "RefineConfig") -> tuple[str, str]:
    """Resolve API key and base_url from a RefineConfig object.

    This is the primary entry point for llm.py and hook_integration.py.
    Returns (api_key, base_url) — either may be empty string.
    """
    from .config import RefineConfig

    api_key = config.get_api_key()
    base_url = config.get_base_url()

    # Env var fallbacks for api_key
    if not api_key:
        api_key = (
            os.environ.get("CLAUDE_PLUGIN_OPTION_API_KEY", "")
            or os.environ.get("ANTHROPIC_API_KEY", "")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        ).strip()

    # Env var fallback for base_url
    if not base_url:
        base_url = (
            os.environ.get("CLAUDE_PLUGIN_OPTION_BASE_URL", "")
            or os.environ.get("ANTHROPIC_BASE_URL", "")
        ).strip()

    return api_key, base_url


def has_credentials(config_api_key: str = "", config_auth_token: str = "") -> bool:
    key, _ = resolve_credentials(config_api_key, config_auth_token)
    return key is not None


def _read_claude_config_key() -> Optional[str]:
    try:
        if not _CLAUDE_CONFIG_PATH.is_file():
            return None
        with open(_CLAUDE_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("primaryApiKey", "")
        return key if key else None
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def build_auth_headers(credential: str, auth_type: str) -> dict[str, str]:
    if auth_type == "bearer":
        return {"Authorization": f"Bearer {credential}"}
    return {"x-api-key": credential}
