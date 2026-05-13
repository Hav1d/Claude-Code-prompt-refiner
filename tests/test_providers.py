"""Tests for provider registry and built-in providers."""

import pytest
from src.providers import get_registry, BUILTIN_PROVIDERS
from src.providers.models import ApiStyle, AuthScheme, ProviderConfig


EXPECTED_PROVIDER_IDS = [
    "custom", "claude", "shengsuan", "modelscope", "aihubmix",
    "siliconflow", "siliconflow-en", "dmxapi", "youyun",
    "openrouter", "therouter", "novita", "nvidia", "pipilm",
    "deepseek", "zhipu", "zhipu-en", "bailian", "bailian-coding",
    "kimi", "kimi-coding", "stepfun", "katcoder", "longcat",
    "minimax", "minimax-en", "doubao", "bailing", "mimo",
    "packycode", "cubence", "aigocode", "rightcode", "aicodemirror",
    "aicoding", "crazyrouter", "ssaicode", "micu", "xcodeapi",
    "ctok", "ddshub", "eflowcode", "lionccapi",
    "github-copilot", "codex", "bedrock-aksk", "bedrock-apikey",
]


class TestBuiltinProviders:
    def test_all_expected_providers_exist(self):
        """Every provider from the spec must be in the registry."""
        registry = get_registry()
        for pid in EXPECTED_PROVIDER_IDS:
            assert pid in registry, f"Provider '{pid}' missing from registry"

    def test_provider_count(self):
        """Registry must contain exactly the expected number of providers."""
        assert len(BUILTIN_PROVIDERS) == len(EXPECTED_PROVIDER_IDS)

    def test_no_duplicate_ids(self):
        """No duplicate provider IDs."""
        ids = [p.id for p in BUILTIN_PROVIDERS]
        assert len(ids) == len(set(ids))

    def test_every_provider_has_required_fields(self):
        """Every provider must have id, display_name, category, api_style."""
        for p in BUILTIN_PROVIDERS:
            assert p.id, f"Provider missing id"
            assert p.display_name, f"Provider {p.id} missing display_name"
            assert p.category, f"Provider {p.id} missing category"
            assert p.api_style, f"Provider {p.id} missing api_style"

    def test_every_provider_has_base_url_or_notes(self):
        """Every provider should have a base_url or notes explaining why not."""
        for p in BUILTIN_PROVIDERS:
            assert p.base_url or p.notes, f"Provider {p.id} has no base_url or notes"


class TestProviderRegistry:
    def test_get_existing(self):
        registry = get_registry()
        p = registry.get("claude")
        assert p is not None
        assert p.display_name == "Claude Official"

    def test_get_nonexistent(self):
        registry = get_registry()
        assert registry.get("nonexistent") is None

    def test_list_all(self):
        registry = get_registry()
        all_providers = registry.list_all()
        assert len(all_providers) == len(EXPECTED_PROVIDER_IDS)

    def test_list_by_category(self):
        registry = get_registry()
        domestic = registry.list_by_category("domestic")
        assert len(domestic) > 0
        for p in domestic:
            assert p.category == "domestic"

    def test_search_by_name(self):
        registry = get_registry()
        results = registry.search("deepseek")
        assert any(p.id == "deepseek" for p in results)

    def test_search_by_display_name(self):
        registry = get_registry()
        results = registry.search("OpenRouter")
        assert any(p.id == "openrouter" for p in results)

    def test_categories(self):
        registry = get_registry()
        cats = registry.categories
        assert "official" in cats
        assert "domestic" in cats
        assert "international" in cats
        assert "proxy" in cats
        assert "custom" in cats

    def test_register_custom(self):
        registry = get_registry()
        custom = ProviderConfig(
            id="test-custom",
            display_name="Test",
            category="custom",
            api_style=ApiStyle.OPENAI,
        )
        registry.register(custom)
        assert "test-custom" in registry
        assert registry.get("test-custom").display_name == "Test"
        # Clean up
        del registry._custom["test-custom"]


class TestProviderDefaults:
    def test_claude_has_anthropic_style(self):
        registry = get_registry()
        p = registry.get("claude")
        assert p.api_style == ApiStyle.ANTHROPIC
        assert p.auth_scheme == AuthScheme.X_API_KEY

    def test_openai_compat_providers(self):
        """Most providers should be OpenAI-compatible."""
        registry = get_registry()
        openai_style = [p for p in registry.list_all() if p.api_style == ApiStyle.OPENAI]
        assert len(openai_style) > 30  # Majority are OpenAI-compatible

    def test_bedrock_providers(self):
        registry = get_registry()
        bedrock = registry.get("bedrock-aksk")
        assert bedrock.api_style == ApiStyle.BEDROCK
        assert bedrock.auth_scheme == AuthScheme.AWS_SIGV4

    def test_deepseek_supports_reasoning(self):
        registry = get_registry()
        p = registry.get("deepseek")
        assert p.supports_reasoning is True
        assert p.default_models.reasoning == "deepseek-reasoner"
