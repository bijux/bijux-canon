# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import bijux_canon_ingest as ingest


def test_root_package_exports_version() -> None:
    assert "__version__" in ingest.__all__
    assert isinstance(ingest.__version__, str)
    assert ingest.__version__


def test_root_package_declares_lazy_exports_in_dir() -> None:
    exported_names = dir(ingest)
    assert "IngestConfig" in exported_names
    assert "build_ingest_deps" in exported_names
