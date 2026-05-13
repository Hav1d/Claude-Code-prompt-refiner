"""Provider configuration data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ApiStyle(str, Enum):
    """API protocol style."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    BEDROCK = "bedrock"
    CUSTOM = "custom"


class AuthScheme(str, Enum):
    """Authentication scheme."""
    BEARER = "bearer"           # Authorization: Bearer <token>
    API_KEY = "api_key"         # x-api-key: <key>
    X_API_KEY = "x_api_key"    # x-api-key: <key> (alias)
    CUSTOM_HEADER = "custom"    # Custom header
    AWS_SIGV4 = "aws_sigv4"    # AWS Signature V4
    NONE = "none"               # No auth needed


@dataclass
class ModelDefaults:
    """Default model names for a provider."""
    summary: str = ""
    refine: str = ""
    executor: str = ""
    reasoning: str = ""


@dataclass
class ProviderConfig:
    """Full configuration for a single provider."""
    id: str
    display_name: str
    category: str  # "official", "domestic", "international", "proxy", "custom"
    api_style: ApiStyle = ApiStyle.OPENAI
    base_url: str = ""
    auth_scheme: AuthScheme = AuthScheme.BEARER
    auth_env_names: list[str] = field(default_factory=list)
    auth_header_name: str = ""  # For custom header auth
    default_models: ModelDefaults = field(default_factory=ModelDefaults)
    model_aliases: dict[str, str] = field(default_factory=dict)
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_reasoning: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_params: dict[str, str] = field(default_factory=dict)
    notes: str = ""
    website: str = ""

    # User-facing config fields
    configurable_fields: list[str] = field(default_factory=lambda: [
        "api_key", "base_url", "model_summary", "model_refine"
    ])
