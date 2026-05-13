"""Provider registry — central lookup for all providers."""

from __future__ import annotations

from typing import Optional

from .builtin import BUILTIN_PROVIDERS, get_builtin_provider_map
from .models import ProviderConfig


class ProviderRegistry:
    """Registry of all available providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderConfig] = get_builtin_provider_map()
        self._custom: dict[str, ProviderConfig] = {}

    def register(self, provider: ProviderConfig) -> None:
        """Register a custom provider."""
        self._custom[provider.id] = provider

    def get(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get a provider by ID."""
        return self._providers.get(provider_id) or self._custom.get(provider_id)

    def list_all(self) -> list[ProviderConfig]:
        """List all providers (builtin + custom)."""
        return list(self._providers.values()) + list(self._custom.values())

    def list_by_category(self, category: str) -> list[ProviderConfig]:
        """List providers filtered by category."""
        return [p for p in self.list_all() if p.category == category]

    def search(self, keyword: str) -> list[ProviderConfig]:
        """Search providers by keyword (name, id, notes)."""
        kw = keyword.lower()
        return [
            p for p in self.list_all()
            if kw in p.id.lower()
            or kw in p.display_name.lower()
            or kw in p.notes.lower()
            or kw in p.category.lower()
        ]

    @property
    def categories(self) -> list[str]:
        """Return all unique categories."""
        seen: set[str] = set()
        for p in self.list_all():
            seen.add(p.category)
        return sorted(seen)

    def __len__(self) -> int:
        return len(self._providers) + len(self._custom)

    def __contains__(self, provider_id: str) -> bool:
        return provider_id in self._providers or provider_id in self._custom


# Module-level singleton
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
