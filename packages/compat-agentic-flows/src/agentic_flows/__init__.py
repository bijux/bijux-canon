# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility alias module for ``bijux_canon_runtime``."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .runtime_alias import install_runtime_aliases

_ALIAS_PACKAGE = "agentic_flows"
_RUNTIME_PACKAGE = "bijux_canon_runtime"
_LOCAL_SUBMODULES = frozenset({"__main__", "runtime_alias"})
_runtime_module = import_module(_RUNTIME_PACKAGE)

install_runtime_aliases(
    alias_package=_ALIAS_PACKAGE,
    runtime_package=_RUNTIME_PACKAGE,
    local_submodules=_LOCAL_SUBMODULES,
)

__all__ = list(getattr(_runtime_module, "__all__", ()))


def __getattr__(name: str) -> Any:
    """Forward compatibility lookups to the canonical runtime package."""
    return getattr(_runtime_module, name)


def __dir__() -> list[str]:
    """Expose the canonical runtime attributes in interactive discovery."""
    return sorted(set(globals()) | set(dir(_runtime_module)) | set(__all__))
