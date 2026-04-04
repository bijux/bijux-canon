# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Lazy loading helpers for runtime execution integrations."""

from __future__ import annotations

from collections.abc import Callable
import importlib
from types import ModuleType
from typing import Any


def load_agent_runner() -> Callable[..., Any]:
    """Resolve the agent execution entrypoint when agent work is required."""
    return _load_callable(
        module_names=("bijux_canon_agent",),
        attribute="run",
        purpose="agent execution",
    )


def load_retrieval_runner() -> Callable[..., Any]:
    """Resolve the retrieval entrypoint when retrieval work is required."""
    return _load_callable(
        module_names=("bijux_canon_ingest", "bijux_rag"),
        attribute="retrieve",
        purpose="retrieval",
    )


def load_reasoning_runner() -> Callable[..., Any]:
    """Resolve the reasoning entrypoint when reasoning work is required."""
    return _load_callable(
        module_names=("bijux_canon_reason", "bijux_rar"),
        attribute="reason",
        purpose="reasoning",
    )


def load_vector_contract_enforcer() -> Callable[..., Any]:
    """Resolve the vector contract enforcement entrypoint when retrieval runs."""
    return _load_callable(
        module_names=("bijux_canon_index", "bijux_vex"),
        attribute="enforce_contract",
        purpose="vector contract enforcement",
    )


def _load_callable(
    *,
    module_names: tuple[str, ...],
    attribute: str,
    purpose: str,
) -> Callable[..., Any]:
    """Load the first available callable from the configured integration modules."""
    last_import_error: ImportError | None = None
    available_modules: list[str] = []
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            last_import_error = exc
            continue
        available_modules.append(module_name)
        exported = getattr(module, attribute, None)
        if callable(exported):
            return exported
    raise RuntimeError(
        _missing_callable_message(
            module_names=module_names,
            available_modules=tuple(available_modules),
            attribute=attribute,
            purpose=purpose,
            last_import_error=last_import_error,
        )
    )


def _missing_callable_message(
    *,
    module_names: tuple[str, ...],
    available_modules: tuple[str, ...],
    attribute: str,
    purpose: str,
    last_import_error: ImportError | None,
) -> str:
    """Build a stable error message for missing runtime integrations."""
    module_list = ", ".join(module_names)
    if available_modules:
        available_list = ", ".join(available_modules)
        return (
            f"Runtime integration for {purpose} is missing: "
            f"expected callable {attribute!r} on one of [{module_list}], "
            f"but only found modules [{available_list}] without that callable."
        )
    if last_import_error is not None:
        return (
            f"Runtime integration for {purpose} is unavailable: "
            f"none of [{module_list}] could be imported ({last_import_error})."
        )
    return (
        f"Runtime integration for {purpose} is unavailable: "
        f"none of [{module_list}] could be imported."
    )


__all__ = [
    "load_agent_runner",
    "load_reasoning_runner",
    "load_retrieval_runner",
    "load_vector_contract_enforcer",
]
