# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bijux_vex.infra.plugins.contract import PluginContract
from bijux_vex.infra.plugins.entrypoints import load_entrypoints


@dataclass(frozen=True)
class RunnerDescriptor:
    name: str


RunnerFactory = Callable[[], object]


class RunnerRegistry:
    def __init__(self) -> None:
        self._runners: dict[str, tuple[RunnerFactory, PluginContract]] = {}
        self._plugin_loads: list[dict[str, object]] = []
        self._plugin_sources: dict[str, dict[str, str | None]] = {}
        self._active_plugin: dict[str, str | None] | None = None

    def register(
        self, name: str, *, factory: RunnerFactory, contract: PluginContract
    ) -> None:
        if not contract.determinism:
            raise ValueError("Runner contract must declare determinism")
        if contract.randomness_sources is None:
            raise ValueError("Runner contract must declare randomness sources")
        self._runners[name] = (factory, contract)
        if self._active_plugin is not None:
            self._plugin_sources[name] = dict(self._active_plugin)

    def available(self) -> list[str]:
        return sorted(self._runners.keys())

    def _record_plugin_load(
        self,
        meta: dict[str, str | None],
        *,
        status: str,
        warning: str | None = None,
    ) -> None:
        entry: dict[str, object] = dict(meta)
        entry["status"] = status
        if warning:
            entry["warning"] = warning
        self._plugin_loads.append(entry)

    def _set_active_plugin(self, meta: dict[str, str | None]) -> None:
        self._active_plugin = dict(meta)

    def _clear_active_plugin(self) -> None:
        self._active_plugin = None

    def plugin_reports(self) -> list[dict[str, object]]:
        reports: list[dict[str, object]] = []
        for name, meta in self._plugin_sources.items():
            _factory, contract = self._runners[name]
            reports.append(
                {
                    "name": name,
                    "group": "bijux_vex.runners",
                    "source": meta.get("name"),
                    "version": meta.get("version"),
                    "entrypoint": meta.get("entrypoint"),
                    "status": "loaded",
                    "determinism": contract.determinism,
                    "randomness_sources": list(contract.randomness_sources),
                    "approximation": contract.approximation,
                }
            )
        reports.extend(
            [entry for entry in self._plugin_loads if entry.get("status") != "loaded"]
        )
        return reports


RUNNERS = RunnerRegistry()
load_entrypoints("bijux_vex.runners", RUNNERS)


__all__ = ["RunnerRegistry", "RunnerDescriptor", "RUNNERS"]
