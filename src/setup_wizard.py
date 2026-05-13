"""First-time setup wizard with provider selection.

Flow:
1. Show provider list (grouped by category)
2. User selects a provider
3. Show required fields for that provider
4. User enters credentials
5. Save to ~/.prompt-refiner/config.json
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .config import ProviderProfile, RefineConfig
from .providers import BUILTIN_PROVIDERS, ProviderConfig, get_registry

_USER_CONFIG_DIR = Path.home() / ".prompt-refiner"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.json"


def check_and_run_wizard(config: RefineConfig, interactive: bool = True) -> bool:
    """Check for credentials and run wizard if needed.

    Returns True if credentials are available (either existing or newly configured).
    """
    # Check if active provider already has a key
    if config.active_provider and config.get_api_key():
        return True

    # Check env vars as fallback
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True

    if not interactive or not sys.stdin.isatty():
        return False

    return run_wizard()


def run_wizard() -> bool:
    """Run the interactive setup wizard.

    Returns True if a provider was configured successfully.
    """
    console = Console()

    console.print()
    console.print(
        Panel(
            Text.assemble(
                ("Welcome to Prompt Refiner!", "bold cyan"),
                "\n\n",
                "Choose an AI provider for prompt refinement.",
                "\n",
                "Your selection is saved locally at:\n",
                (str(_USER_CONFIG_PATH), "dim"),
                "\n\n",
                "You can change it later with: ",
                ("pr config set", "bold"),
            ),
            title="[bold]Setup[/bold]",
            border_style="cyan",
            expand=False,
        )
    )

    # Show provider list
    provider = _select_provider(console)
    if provider is None:
        return False

    # Collect credentials
    console.print()
    console.print(f"[bold]Configuring: {provider.display_name}[/bold]")
    if provider.notes:
        console.print(f"[dim]{provider.notes}[/dim]")
    if provider.website:
        console.print(f"[dim]{provider.website}[/dim]")
    console.print()

    api_key = _prompt_for_key(console, provider)
    if not api_key:
        console.print("[warning]No key entered. Skipping setup.[/warning]")
        return False

    base_url = _prompt_for_url(console, provider)
    model = _prompt_for_model(console, provider)

    # Save config
    _save_provider_config(provider, api_key, base_url, model)
    console.print()
    console.print(f"[success]Configuration saved to {_USER_CONFIG_PATH}[/success]")
    console.print("[dim]You won't need to enter it again.[/dim]")
    console.print()
    return True


def _select_provider(console: Console) -> Optional[ProviderConfig]:
    """Show provider list and get user selection."""
    registry = get_registry()
    providers = registry.list_all()

    # Build numbered list grouped by category
    category_labels = {
        "official": "Official",
        "domestic": "国内",
        "international": "国际",
        "proxy": "代理",
        "custom": "自定义",
    }

    table = Table(
        title="Available Providers",
        show_lines=False,
        show_header=True,
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Provider", style="bold")
    table.add_column("Category", style="dim")
    table.add_column("Default Model", style="dim")
    table.add_column("Notes", style="dim", max_width=30)

    indexed: list[ProviderConfig] = []
    idx = 1
    for cat in ["official", "domestic", "international", "proxy", "custom"]:
        cat_providers = [p for p in providers if p.category == cat]
        if not cat_providers:
            continue
        for p in cat_providers:
            model_hint = p.default_models.refine or p.default_models.summary or "-"
            notes = p.notes[:28] + ".." if len(p.notes) > 30 else p.notes
            table.add_row(
                str(idx),
                p.display_name,
                category_labels.get(cat, cat),
                model_hint,
                notes,
            )
            indexed.append(p)
            idx += 1

    console.print()
    console.print(table)
    console.print()

    while True:
        choice = Prompt.ask(
            "[bold]Select provider number[/bold]",
            default="1",
        )
        try:
            num = int(choice)
            if 1 <= num <= len(indexed):
                return indexed[num - 1]
        except ValueError:
            pass
        console.print(f"[warning]Please enter a number between 1 and {len(indexed)}[/warning]")


def _prompt_for_key(console: Console, provider: ProviderConfig) -> str:
    """Prompt for API key based on provider auth scheme."""
    scheme = provider.auth_scheme.value
    env_hint = ", ".join(provider.auth_env_names[:2]) if provider.auth_env_names else ""

    if scheme == "aws_sigv4":
        # AWS needs multiple fields
        console.print("[dim]AWS Bedrock requires Access Key ID and Secret Access Key.[/dim]")
        ak = Prompt.ask("[bold]AWS Access Key ID[/bold]")
        sk = Prompt.ask("[bold]AWS Secret Access Key[/bold]")
        if ak and sk:
            return f"{ak}:{sk}"
        return ""

    label = "API Key"
    if "token" in scheme.lower():
        label = "Token"

    hint = f" (env: {env_hint})" if env_hint else ""
    api_key = Prompt.ask(f"[bold]{label}[/bold]{hint}")
    return api_key.strip() if api_key else ""


def _prompt_for_url(console: Console, provider: ProviderConfig) -> str:
    """Prompt for base URL (with default)."""
    default_url = provider.base_url
    if not default_url:
        url = Prompt.ask("[bold]Base URL[/bold]")
        return url.strip() if url else ""

    url = Prompt.ask(
        "[bold]Base URL[/bold]",
        default=default_url,
    )
    return url.strip() if url else default_url


def _prompt_for_model(console: Console, provider: ProviderConfig) -> str:
    """Prompt for model name (with default)."""
    default_model = provider.default_models.refine or provider.default_models.summary or ""
    if not default_model:
        model = Prompt.ask("[bold]Model name[/bold]")
        return model.strip() if model else ""

    model = Prompt.ask(
        "[bold]Model name[/bold]",
        default=default_model,
    )
    return model.strip() if model else default_model


def _save_provider_config(
    provider: ProviderConfig,
    api_key: str,
    base_url: str,
    model: str,
) -> None:
    """Save provider config to user config file."""
    _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing config
    existing: dict = {}
    if _USER_CONFIG_PATH.is_file():
        try:
            with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    # Build provider profile
    profile: dict = {
        "enabled": True,
        "api_key": api_key if ":" not in api_key else "",
        "auth_token": "" if ":" not in api_key else api_key,
        "base_url": base_url,
        "models": {
            "summary": model,
            "refine": model,
        },
    }

    # AWS special case
    if ":" in api_key and provider.auth_scheme.value == "aws_sigv4":
        parts = api_key.split(":", 1)
        profile["extra"] = {
            "access_key_id": parts[0],
            "secret_access_key": parts[1],
        }
        profile["api_key"] = ""

    # Update config
    existing["active_provider"] = provider.id
    providers = existing.get("providers", {})
    providers[provider.id] = profile
    existing["providers"] = providers

    with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    # Restrictive permissions
    try:
        os.chmod(_USER_CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def clear_saved_config() -> bool:
    """Remove the saved provider config.

    Returns True if something was removed.
    """
    if not _USER_CONFIG_PATH.is_file():
        return False

    try:
        with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    changed = False
    if "active_provider" in data:
        del data["active_provider"]
        changed = True
    if "providers" in data:
        del data["providers"]
        changed = True
    # Also clear legacy fields
    for field in ("api_key", "auth_token"):
        if field in data:
            del data[field]
            changed = True

    if changed:
        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return changed


def show_config_status(config: RefineConfig) -> None:
    """Display the current credential status."""
    from rich.console import Console

    console = Console()

    if not config.active_provider:
        console.print("[warning]No provider configured.[/warning]")
        console.print("[dim]Run 'pr config set' to set up.[/dim]")
        return

    registry = get_registry()
    provider = registry.get(config.active_provider)
    if provider:
        console.print(f"[bold]Provider:[/bold] {provider.display_name} ({provider.id})")
    else:
        console.print(f"[bold]Provider:[/bold] {config.active_provider}")

    api_key = config.get_api_key()
    if api_key:
        masked = _mask_key(api_key)
        console.print(f"[bold]API Key:[/bold] {masked}")
    else:
        console.print("[warning]No API key[/warning]")

    base_url = config.get_base_url()
    if base_url:
        console.print(f"[bold]Base URL:[/bold] {base_url}")

    for role in ("summary", "refine"):
        model = config.get_model(role)
        if model:
            console.print(f"[bold]Model ({role}):[/bold] {model}")


def _mask_key(key: str) -> str:
    """Mask an API key for display."""
    if len(key) <= 8:
        return "****"
    return f"{'*' * (len(key) - 4)}{key[-4:]}"
