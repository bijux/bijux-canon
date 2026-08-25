# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for installed execution-profile capability checks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bijux_canon_runtime.application.profile_preflight import (
    InstalledProfilePreflight,
)
from bijux_canon_runtime.application.operations.service import (
    ApplicationCapabilityError,
)
from bijux_canon_runtime.model.execution.request_plan import ExecutionProfile


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


def test_dense_preflight_refuses_missing_model_before_importing_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = InstalledProfilePreflight(
        layout=SimpleNamespace(),  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
    )
    backend_checked = False

    def missing_model() -> None:
        raise ApplicationCapabilityError("model unavailable")

    def check_backend() -> None:
        nonlocal backend_checked
        backend_checked = True

    monkeypatch.setattr(preflight, "_verified_model", missing_model)
    monkeypatch.setattr(preflight, "_verify_local_dense_backend", check_backend)

    request = SimpleNamespace(execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN)
    with pytest.raises(ApplicationCapabilityError, match="model unavailable"):
        preflight(request)  # type: ignore[arg-type]

    assert not backend_checked
