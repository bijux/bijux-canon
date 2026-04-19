# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from importlib import metadata

from bijux_canon_runtime.core.package_versions import (
    distribution_version,
    runtime_dependency_versions,
)
import pytest


def test_distribution_version_uses_first_installed_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions: dict[str, str] = {
        "bijux-canon-agent": "0.3.6",
    }

    def fake_version(name: str) -> str:
        return versions[name]

    monkeypatch.setattr(metadata, "version", fake_version)

    assert distribution_version("bijux-canon-agent") == "0.3.6"


def test_distribution_version_falls_back_when_no_distribution_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_version(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", fake_version)

    assert distribution_version("missing-a", "missing-b") == "0.0.0"


def test_runtime_dependency_versions_use_canonical_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "bijux-cli": "0.3.6",
        "bijux-canon-agent": "0.3.6",
        "bijux-canon-ingest": "0.3.6",
        "bijux-canon-reason": "0.3.6",
        "bijux-canon-index": "0.3.6",
    }

    def fake_version(name: str) -> str:
        version = values.get(name)
        if version is None:
            raise metadata.PackageNotFoundError(name)
        return version

    monkeypatch.setattr(metadata, "version", fake_version)

    assert runtime_dependency_versions() == {
        "bijux-cli": "0.3.6",
        "bijux-canon-agent": "0.3.6",
        "bijux-canon-ingest": "0.3.6",
        "bijux-canon-reason": "0.3.6",
        "bijux-canon-index": "0.3.6",
    }
