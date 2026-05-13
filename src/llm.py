"""LLM caller using the provider adapter layer."""

from __future__ import annotations

from typing import Optional

from .config import RefineConfig
from .providers import create_adapter, get_registry


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800,
    model: str = "",
    config: Optional[RefineConfig] = None,
) -> str:
    """Make an LLM call using the active provider's adapter.

    Falls back to legacy single-key mode if no provider is configured.
    """
    from .credentials import resolve_for_config
    from .providers.models import ApiStyle, AuthScheme, ModelDefaults, ProviderConfig

    if config is None:
        config = RefineConfig()

    api_key, base_url = resolve_for_config(config)

    # Resolve model from config if not explicitly provided
    if not model:
        model = config.get_model("refine")

    if not api_key:
        raise ValueError(
            "No API key found. Run 'pr config set' to configure, "
            "or set ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN."
        )

    # Get provider config
    registry = get_registry()
    provider = None
    if config.active_provider:
        provider = registry.get(config.active_provider)

    # If no provider found, try legacy mode with Anthropic-compatible defaults
    if provider is None:
        provider = ProviderConfig(
            id="legacy",
            display_name="Legacy",
            category="custom",
            api_style=ApiStyle.ANTHROPIC if not base_url or "anthropic" in base_url else ApiStyle.OPENAI,
            base_url=base_url or "https://api.anthropic.com",
            auth_scheme=AuthScheme.X_API_KEY if "anthropic" in (base_url or "") else AuthScheme.BEARER,
            default_models=ModelDefaults(summary=model, refine=model),
        )

    # If user overrode base_url and it differs from provider default,
    # auto-detect API style from the URL (e.g. anthropic proxy → ANTHROPIC style)
    if base_url and base_url != provider.base_url:
        is_anthropic_url = "anthropic" in base_url.lower()
        if is_anthropic_url and provider.api_style != ApiStyle.ANTHROPIC:
            from dataclasses import replace
            provider = replace(provider, api_style=ApiStyle.ANTHROPIC)

    adapter = create_adapter(provider, api_key=api_key, base_url=base_url)
    return await adapter.call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        model=model,
    )


def make_llm_caller(config: RefineConfig):
    """Create an LLM caller closure bound to config.

    Returns an async callable (system, user, max_tokens) -> str.
    """
    async def caller(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        model = config.get_model("refine")
        return await call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            model=model,
            config=config,
        )
    return caller


def make_summary_caller(config: RefineConfig):
    """Create a summary-specific LLM caller."""
    async def caller(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        model = config.get_model("summary")
        return await call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            model=model,
            config=config,
        )
    return caller
