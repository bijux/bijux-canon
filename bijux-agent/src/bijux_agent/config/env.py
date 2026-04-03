"""Loads and validates API key configuration from environment files."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class APIKeySpec:
    """Describes how each provider exposes an API key in the environment."""

    provider: str
    env_var: str
    description: str


KEY_REGISTRY: tuple[APIKeySpec, ...] = (
    APIKeySpec("OpenAI", "OPENAI_API_KEY", "OpenAI chat/completion endpoints"),
    APIKeySpec("Anthropic", "ANTHROPIC_API_KEY", "Claude conversational endpoints"),
    APIKeySpec("HuggingFace", "HUGGINGFACE_API_KEY", "HF inference API"),
    APIKeySpec("Deepseek", "DEEPSEEK_API_KEY", "Deepseek chat completions"),
)


def load_environment(dotenv_path: str | Path | None = None) -> None:
    """Load `.env` files when available to seed API key lookups."""
    path = Path(dotenv_path) if dotenv_path else Path(".env")
    if path.exists():
        load_dotenv(dotenv_path=path)


def _missing_keys() -> list[str]:
    """Return any required API keys that are not configured."""
    return [spec.env_var for spec in KEY_REGISTRY if not os.getenv(spec.env_var)]


def validate_keys() -> None:
    """Ensure all required API keys are present before connecting to providers."""
    missing = _missing_keys()
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            f"Missing API keys: {missing_list}. Please define them in the environment or .env file."
        )


def key_for_provider(provider: str) -> str:
    """Return the configured key for a specific provider, or raise."""
    spec = next(
        (spec for spec in KEY_REGISTRY if spec.provider.lower() == provider.lower()),
        None,
    )
    if not spec:
        raise KeyError(f"Unknown provider: {provider}")
    value = os.getenv(spec.env_var)
    if not value:
        raise RuntimeError(f"API key for {provider} ({spec.env_var}) is not configured")
    return value


def configured_providers() -> Iterable[str]:
    """List providers that currently have API keys configured."""
    return [spec.provider for spec in KEY_REGISTRY if os.getenv(spec.env_var)]


__all__ = [
    "KEY_REGISTRY",
    "APIKeySpec",
    "load_environment",
    "validate_keys",
    "configured_providers",
    "key_for_provider",
]
