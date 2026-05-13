"""Provider registry and adapter layer."""

from .adapters import ProviderAdapter, create_adapter
from .models import ApiStyle, AuthScheme, ModelDefaults, ProviderConfig
from .registry import ProviderRegistry, get_registry
from .builtin import BUILTIN_PROVIDERS

__all__ = [
    "ApiStyle",
    "AuthScheme",
    "BUILTIN_PROVIDERS",
    "ModelDefaults",
    "ProviderAdapter",
    "ProviderConfig",
    "ProviderRegistry",
    "create_adapter",
    "get_registry",
]
