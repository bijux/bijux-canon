# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from importlib import metadata

import pytest

from bijux_canon_runtime.core.package_versions import distribution_version
from bijux_canon_runtime.core.package_versions import runtime_dependency_versions


def test_distribution_version_uses_first_installed_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions = {
        "bijux-canon-agent": "0.3.0",
    }

    def fake_version(name: str) -> str:
        result = versions[name]
        if result is metadata.PackageNotFoundError:
            raise metadata.PackageNotFoundError(name)
        return result

    monkeypatch.setattr(metadata, "version", fake_version)

    assert distribution_version("bijux-canon-agent") == "0.3.0"


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
        "bijux-cli": "0.3.3",
        "bijux-canon-agent": "0.3.0",
        "bijux-canon-ingest": "0.3.0",
        "bijux-canon-reason": "0.3.0",
        "bijux-canon-index": "0.3.0",
    }

    def fake_version(name: str) -> str:
        result = values.get(name, metadata.PackageNotFoundError)
        if result is metadata.PackageNotFoundError:
            raise metadata.PackageNotFoundError(name)
        return result

    monkeypatch.setattr(metadata, "version", fake_version)

    assert runtime_dependency_versions() == {
        "bijux-cli": "0.3.3",
        "bijux-canon-agent": "0.3.0",
        "bijux-canon-ingest": "0.3.0",
        "bijux-canon-reason": "0.3.0",
        "bijux-canon-index": "0.3.0",
    }
