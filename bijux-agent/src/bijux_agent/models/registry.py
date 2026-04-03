"""Registry helpers for model/provider resolution."""

from __future__ import annotations

from enum import Enum


class Provider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "OpenAI"
    DEEPSEEK = "DeepSeek"
    LOCAL = "Local"
    MOCK = "Mock"


DEEPSEEK_PREFIX = "deepseek-"
LOCAL_PREFIX = "local-"

MODEL_REGISTRY: dict[str, Provider] = {
    "gpt-4o-mini": Provider.OPENAI,
    "gpt-3.5-turbo": Provider.OPENAI,
    "mock-model": Provider.MOCK,
    "deepseek-chat": Provider.DEEPSEEK,
    "local-deterministic": Provider.LOCAL,
}


def validate_model_name(model_name: str) -> None:
    """Ensure the model name is recognized by the registry."""
    if model_name.startswith(DEEPSEEK_PREFIX):
        return
    if model_name.startswith(LOCAL_PREFIX):
        return
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_name}")


def resolve_provider(model_name: str) -> Provider:
    """Resolve a model name into a provider."""
    if model_name.startswith(DEEPSEEK_PREFIX):
        return Provider.DEEPSEEK
    if model_name.startswith(LOCAL_PREFIX):
        return Provider.LOCAL
    if model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name]
    raise ValueError(f"Unknown model: {model_name}")


__all__ = [
    "Provider",
    "MODEL_REGISTRY",
    "DEEPSEEK_PREFIX",
    "resolve_provider",
    "validate_model_name",
]
