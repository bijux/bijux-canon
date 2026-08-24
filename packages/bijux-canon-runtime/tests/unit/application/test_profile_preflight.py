# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for installed execution-profile capability checks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bijux_canon_runtime.application.profile_preflight import (
    InstalledProfilePreflight,
)


def test_dense_preflight_initializes_torch_before_faiss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []
    modules = {
        "torch": SimpleNamespace(),
        "faiss": SimpleNamespace(
            IndexFlatIP=lambda: None,
            IndexHNSWFlat=lambda: None,
        ),
    }

    def import_module(name: str) -> object:
        imported.append(name)
        return modules[name]

    monkeypatch.setattr(
        "bijux_canon_runtime.application.profile_preflight.importlib.import_module",
        import_module,
    )

    InstalledProfilePreflight._verify_local_dense_backend()

    assert imported == ["torch", "faiss"]
