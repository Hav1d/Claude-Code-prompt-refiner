"""Provider adapters — unified request/response handling.

Each adapter knows how to:
- Build request headers and payload for its API style
- Parse the response into a plain text string
- Handle authentication
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from .models import ApiStyle, AuthScheme, ProviderConfig


class ProviderAdapter:
    """Base adapter for making LLM API calls."""

    def __init__(self, provider: ProviderConfig, api_key: str = "", base_url: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url or provider.base_url

    def build_headers(self) -> dict[str, str]:
        """Build authentication headers."""
        headers: dict[str, str] = {
            "content-type": "application/json",
            **self.provider.extra_headers,
        }
        if not self.api_key:
            return headers

        scheme = self.provider.auth_scheme
        if scheme in (AuthScheme.BEARER, AuthScheme.NONE):
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif scheme in (AuthScheme.API_KEY, AuthScheme.X_API_KEY):
            headers["x-api-key"] = self.api_key
        elif scheme == AuthScheme.CUSTOM_HEADER:
            header_name = self.provider.auth_header_name or "x-api-key"
            headers[header_name] = self.api_key
        # AWS_SIGV4 is handled separately

        return headers

    def build_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 800,
        model: str = "",
    ) -> dict[str, Any]:
        """Build the request payload."""
        style = self.provider.api_style

        if style == ApiStyle.ANTHROPIC:
            return self._build_anthropic_payload(
                system_prompt, user_prompt, max_tokens, model
            )
        elif style == ApiStyle.OPENAI:
            return self._build_openai_payload(
                system_prompt, user_prompt, max_tokens, model
            )
        elif style == ApiStyle.BEDROCK:
            return self._build_bedrock_payload(
                system_prompt, user_prompt, max_tokens, model
            )
        else:
            return self._build_openai_payload(
                system_prompt, user_prompt, max_tokens, model
            )

    def build_url(self, model: str = "") -> str:
        """Build the full API URL."""
        style = self.provider.api_style
        base = self.base_url.rstrip("/")

        if style == ApiStyle.ANTHROPIC:
            return f"{base}/v1/messages"
        elif style == ApiStyle.BEDROCK:
            region = self.provider.extra_params.get("region", "us-east-1")
            base = base.replace("{region}", region)
            return f"{base}/model/{model}/invoke"
        else:
            return f"{base}/chat/completions"

    def parse_response(self, data: dict[str, Any]) -> str:
        """Parse the API response into plain text."""
        style = self.provider.api_style

        if style == ApiStyle.ANTHROPIC:
            return self._parse_anthropic_response(data)
        elif style == ApiStyle.OPENAI:
            return self._parse_openai_response(data)
        elif style == ApiStyle.BEDROCK:
            return self._parse_bedrock_response(data)
        else:
            return self._parse_openai_response(data)

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 800,
        model: str = "",
        timeout: float = 30.0,
    ) -> str:
        """Make the API call and return the response text."""
        if not self.api_key:
            raise ValueError(
                f"No API key for provider '{self.provider.id}'. "
                f"Run 'pr config set' to configure."
            )

        url = self.build_url(model)
        headers = self.build_headers()
        payload = self.build_payload(system_prompt, user_prompt, max_tokens, model)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return self.parse_response(data)

    # ── Anthropic format ────────────────────────────────────

    def _build_anthropic_payload(
        self, system: str, user: str, max_tokens: int, model: str
    ) -> dict:
        return {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

    def _parse_anthropic_response(self, data: dict) -> str:
        parts = []
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)

    # ── OpenAI format ───────────────────────────────────────

    def _build_openai_payload(
        self, system: str, user: str, max_tokens: int, model: str
    ) -> dict:
        return {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def _parse_openai_response(self, data: dict) -> str:
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return message.get("content", "")

    # ── Bedrock format ──────────────────────────────────────

    def _build_bedrock_payload(
        self, system: str, user: str, max_tokens: int, model: str
    ) -> dict:
        # Bedrock uses Anthropic format for Claude models
        if "anthropic" in model or "claude" in model:
            return self._build_anthropic_payload(system, user, max_tokens, model)
        # Generic Bedrock format
        return {
            "inputText": f"{system}\n\n{user}",
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
            },
        }

    def _parse_bedrock_response(self, data: dict) -> str:
        # Anthropic-style response on Bedrock
        if "content" in data:
            return self._parse_anthropic_response(data)
        # Generic Bedrock response
        results = data.get("results", [])
        if results:
            return results[0].get("outputText", "")
        return ""


def create_adapter(
    provider: ProviderConfig,
    api_key: str = "",
    base_url: str = "",
) -> ProviderAdapter:
    """Create an adapter for the given provider."""
    return ProviderAdapter(provider, api_key=api_key, base_url=base_url)
