"""
Models package.

IMPORTANT: keep this module import-light.
Importing adapters/factories here can pull in `bijux_agent.pipeline` early and
create circular imports (especially under tox/installed-wheel imports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Provider",
    "build_adapter",
    "resolve_provider",
    "validate_model_name",
    "OpenAIAdapter",
    "DeepSeekAdapter",
    "MockAdapter",
    "LocalAdapter",
]

if TYPE_CHECKING:
    from .adapter_factory import build_adapter
    from .llm_adapter import DeepSeekAdapter, LocalAdapter, MockAdapter, OpenAIAdapter
    from .registry import Provider, resolve_provider, validate_model_name


def __getattr__(name: str) -> Any:
    if name == "build_adapter":
        from .adapter_factory import build_adapter

        return build_adapter
    if name in {"Provider", "resolve_provider", "validate_model_name"}:
        from . import registry as _registry

        return getattr(_registry, name)
    if name in {"OpenAIAdapter", "DeepSeekAdapter", "MockAdapter", "LocalAdapter"}:
        from . import llm_adapter as _llm_adapter

        return getattr(_llm_adapter, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
