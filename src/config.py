"""Configuration system with multi-provider profile support.

Supports legacy config migration from the old single-provider format.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProviderProfile(BaseModel):
    """Configuration for a single provider."""

    enabled: bool = True
    api_key: str = ""
    auth_token: str = ""
    base_url: str = ""
    models: dict[str, str] = Field(
        default_factory=dict,
        description="Model mapping: summary, refine, executor, reasoning",
    )
    headers: dict[str, str] = Field(default_factory=dict)
    extra: dict[str, str] = Field(default_factory=dict)


class RefineConfig(BaseModel):
    """Full configuration schema for prompt refiner."""

    # Active provider
    active_provider: str = Field(
        default="",
        description="Currently active provider ID",
    )

    # Provider profiles
    providers: dict[str, ProviderProfile] = Field(
        default_factory=dict,
        description="Per-provider configuration profiles",
    )

    # Legacy fields (for migration compatibility)
    refine_model: str = Field(default="")
    summary_model: str = Field(default="")
    api_base_url: str = Field(default="")
    api_key: str = Field(default="")
    auth_token: str = Field(default="")

    # Auto-refine behavior
    auto_refine: bool = Field(default=False)
    auto_refine_min_length: int = Field(default=20)

    # History and context
    history_lines: int = Field(default=15)
    max_summary_tokens: int = Field(default=300)
    max_refined_tokens: int = Field(default=800)

    # Cache
    cache_ttl: float = Field(default=300.0)
    cache_dir: str = Field(default="")

    # Prompt injection
    prefix: str = Field(default="")
    suffix: str = Field(default="")

    # Skip rules
    skip_commands: list[str] = Field(
        default=["/no-refine", "/nr", "/skip"],
    )
    ignore_patterns: list[str] = Field(
        default=[r"^\s*$", r"^/[a-z]+"],
    )

    # Rules
    project_rules: list[str] = Field(default_factory=list)
    user_rules: list[str] = Field(default_factory=list)
    language_rules: dict[str, list[str]] = Field(default_factory=dict)

    # Transcript
    transcript_path: str = Field(default="")

    # Logging
    debug_mode: bool = Field(default=False)
    log_dir: str = Field(default="")
    log_format: str = Field(default="jsonl")

    # Refinement principles (built-in)
    refinement_principles: list[str] = Field(
        default=[
            "Do NOT expand the user's intent beyond what was stated.",
            "Do NOT guess or fabricate details not present in the input.",
            "Do NOT bloat a short input into a long description.",
            "Preserve all error messages, file paths, commands, and framework names exactly.",
            "If the input is ambiguous, generate a clarification question instead of guessing.",
            "Keep the refined prompt short, clear, and actionable.",
            "If the input is already precise, return it unchanged.",
            "Structure the output as: Goal, Context, Constraints (only if applicable).",
        ],
    )

    def get_active_profile(self) -> ProviderProfile:
        """Get the active provider's profile, or a default empty one."""
        if self.active_provider and self.active_provider in self.providers:
            return self.providers[self.active_provider]
        return ProviderProfile()

    def get_model(self, role: str = "refine") -> str:
        """Get the model name for a given role (summary/refine/executor)."""
        profile = self.get_active_profile()
        model = profile.models.get(role, "")
        if model:
            return model
        # Legacy fallback
        if role == "summary":
            return self.summary_model or "claude-haiku-4-5-20251001"
        if role == "refine":
            return self.refine_model or "claude-haiku-4-5-20251001"
        return "claude-haiku-4-5-20251001"

    def get_api_key(self) -> str:
        """Get the API key for the active provider."""
        profile = self.get_active_profile()
        return profile.api_key or profile.auth_token or self.api_key or self.auth_token or ""

    def get_base_url(self) -> str:
        """Get the base URL for the active provider."""
        profile = self.get_active_profile()
        return profile.base_url or self.api_base_url or ""


# ──────────────────────────────────────────────────────────────
# Config Loading
# ──────────────────────────────────────────────────────────────

_SEARCH_ORDER = [
    Path.home() / ".prompt-refiner" / "config.json",
    Path.cwd() / ".prompt-refiner" / "config.json",
    Path.cwd() / "prompt-config.json",
]


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, returning a new dict."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _migrate_legacy_config(data: dict) -> dict:
    """Migrate old single-provider config to new multi-provider format.

    If the config has legacy fields (api_key, api_base_url, etc.) but no
    active_provider, create a 'custom' provider profile from them.
    """
    # Already new format
    if data.get("active_provider"):
        return data

    has_legacy_key = data.get("api_key") or data.get("auth_token")
    has_legacy_url = data.get("api_base_url")

    if not has_legacy_key and not has_legacy_url:
        return data

    # Build a custom provider from legacy fields
    profile: dict[str, Any] = {
        "enabled": True,
        "api_key": data.pop("api_key", ""),
        "auth_token": data.pop("auth_token", ""),
        "base_url": data.pop("api_base_url", ""),
        "models": {},
    }

    if data.get("summary_model"):
        profile["models"]["summary"] = data.pop("summary_model")
    if data.get("refine_model"):
        profile["models"]["refine"] = data.pop("refine_model")

    data["active_provider"] = "custom"
    providers = data.get("providers", {})
    providers["custom"] = profile
    data["providers"] = providers

    return data


def load_config(
    config_path: Optional[str] = None,
    env_overrides: Optional[dict[str, str]] = None,
) -> RefineConfig:
    """Load configuration with layered merging.

    Priority (lowest to highest):
    1. Built-in defaults
    2. User config (~/.prompt-refiner/config.json)
    3. Project config (./prompt-config.json)
    4. Explicit config_path
    5. Environment variable overrides
    """
    merged: dict[str, Any] = {}

    for path in _SEARCH_ORDER:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                merged = _deep_merge(merged, data)
            except (json.JSONDecodeError, OSError):
                pass

    if config_path:
        p = Path(config_path)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = _deep_merge(merged, data)

    # Migrate legacy config
    merged = _migrate_legacy_config(merged)

    # Env overrides
    env_map = {
        "REFINE_MODEL": "refine_model",
        "SUMMARY_MODEL": "summary_model",
        "ANTHROPIC_BASE_URL": "api_base_url",
        "ANTHROPIC_API_KEY": "api_key",
        "ANTHROPIC_AUTH_TOKEN": "auth_token",
        "PROMPT_REFINE_DEBUG": "debug_mode",
        "PROMPT_REFINE_PROVIDER": "active_provider",
    }
    if env_overrides:
        env_map.update(env_overrides)

    for env_key, config_key in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            if config_key == "debug_mode":
                merged[config_key] = val.lower() in ("1", "true", "yes")
            else:
                merged[config_key] = val

    return RefineConfig(**merged)


def resolve_path(p: str, fallback: Path) -> Path:
    """Resolve a config path string to a Path, using fallback if empty."""
    return Path(p) if p else fallback
