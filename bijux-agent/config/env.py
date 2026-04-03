"""Shallow proxy for the Bijux Agent key loader."""

from __future__ import annotations

from bijux_agent.config.env import (
    KEY_REGISTRY,
    APIKeySpec,
    configured_providers,
    key_for_provider,
    load_environment,
    validate_keys,
)

__all__ = [
    "APIKeySpec",
    "KEY_REGISTRY",
    "load_environment",
    "validate_keys",
    "configured_providers",
    "key_for_provider",
]
