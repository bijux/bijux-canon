# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Entrypoints helpers."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata
import logging
from typing import Any

from bijux_canon_index.infra.environment import read_env


def load_entrypoints(group: str, registry: Any) -> None:
    """Load entrypoints."""
    entries = []
    try:
        entries = list(metadata.entry_points(group=group))
    except TypeError:  # pragma: no cover - compatibility
        all_eps = metadata.entry_points()
        if hasattr(all_eps, "select"):
            entries = list(all_eps.select(group=group))
        else:
            entries = list(all_eps.get(group, []))
    for ep in entries:
        meta = _entrypoint_meta(ep, group)
        try:
            plugin = ep.load()
        except Exception as exc:
            _record_plugin_load(registry, meta, "failed", warning=str(exc))
            logging.getLogger(__name__).debug(
                "Failed to load entrypoint %s for group %s: %s", ep, group, exc
            )
            continue
        try:
            _set_active_plugin(registry, meta)

            def _register(plugin: Any = plugin, registry: Any = registry) -> None:
                """Register plugin."""
                _register_plugin(plugin, registry)

            _call_with_timeout(_register)
            _record_plugin_load(registry, meta, "loaded")
        except TimeoutError as exc:
            _record_plugin_load(registry, meta, "timeout", warning=str(exc))
        except Exception as exc:
            _record_plugin_load(registry, meta, "failed", warning=str(exc))
            logging.getLogger(__name__).debug(
                "Plugin registration failed for %s: %s", meta.get("name"), exc
            )
        finally:
            _clear_active_plugin(registry)


def _register_plugin(plugin: Any, registry: Any) -> None:
    """Register plugin."""
    if hasattr(plugin, "register") and callable(plugin.register):
        plugin.register(registry)
        return
    if callable(plugin):
        plugin(registry)
        return


def _call_with_timeout(func: Callable[[], None]) -> None:
    """Handle call with timeout."""
    timeout_ms = int(
        read_env(
            "BIJUX_CANON_INDEX_PLUGIN_TIMEOUT_MS",
            legacy="BIJUX_VEX_PLUGIN_TIMEOUT_MS",
            default="2000",
        )
        or "2000"
    )
    if timeout_ms <= 0:
        func()
        return
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        future.result(timeout=timeout_ms / 1000.0)


def _entrypoint_meta(ep: Any, group: str) -> dict[str, str | None]:
    """Handle entrypoint meta."""
    dist_name = None
    dist_version = None
    if getattr(ep, "dist", None) is not None:
        dist_name = getattr(ep.dist, "name", None)
        dist_version = getattr(ep.dist, "version", None)
    return {
        "group": group,
        "entrypoint": getattr(ep, "name", None) or str(ep),
        "name": dist_name or getattr(ep, "name", None) or "unknown",
        "version": dist_version,
    }


def _record_plugin_load(
    registry: Any, meta: dict[str, str | None], status: str, warning: str | None = None
) -> None:
    """Record plugin load."""
    if hasattr(registry, "_record_plugin_load"):
        registry._record_plugin_load(meta, status=status, warning=warning)


def _set_active_plugin(registry: Any, meta: dict[str, str | None]) -> None:
    """Handle set active plugin."""
    if hasattr(registry, "_set_active_plugin"):
        registry._set_active_plugin(meta)


def _clear_active_plugin(registry: Any) -> None:
    """Handle clear active plugin."""
    if hasattr(registry, "_clear_active_plugin"):
        registry._clear_active_plugin()


__all__ = ["load_entrypoints"]
