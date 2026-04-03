# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import threading

from bijux_vex.services._orchestrator import Orchestrator


def test_backend_pool_reuses_sqlite_backend(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BIJUX_VEX_BACKEND", raising=False)
    state_path = tmp_path / "session.sqlite"
    orchestrator_a = Orchestrator(state_path=state_path)
    orchestrator_b = Orchestrator(state_path=state_path)
    assert orchestrator_a.backend is orchestrator_b.backend


def test_backend_pool_separates_state_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BIJUX_VEX_BACKEND", raising=False)
    state_a = tmp_path / "a.sqlite"
    state_b = tmp_path / "b.sqlite"
    orchestrator_a = Orchestrator(state_path=state_a)
    orchestrator_b = Orchestrator(state_path=state_b)
    assert orchestrator_a.backend is not orchestrator_b.backend


def test_backend_pool_is_thread_safe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BIJUX_VEX_BACKEND", raising=False)
    state_path = tmp_path / "session.sqlite"
    backends: list[object] = []

    def _build() -> None:
        backends.append(Orchestrator(state_path=state_path).backend)

    threads = [threading.Thread(target=_build) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert backends
    assert all(backend is backends[0] for backend in backends)
