# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Internal helpers for typed lazy public exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any, TypeAlias

LazyExport: TypeAlias = tuple[str, str]


def resolve_lazy_export(
    *,
    module_name: str,
    name: str,
    exports: dict[str, LazyExport],
) -> Any:
    target = exports.get(name)
    if target is None:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

    import_path, attr_name = target
    return getattr(import_module(import_path, module_name), attr_name)


__all__ = ["LazyExport", "resolve_lazy_export"]
