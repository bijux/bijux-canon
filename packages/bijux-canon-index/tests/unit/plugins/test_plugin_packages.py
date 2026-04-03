# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import tomllib


def test_external_plugin_examples_define_entrypoints() -> None:
    plugin_root = Path(__file__).resolve().parents[3] / "plugins"
    template = tomllib.loads(
        (plugin_root / "template_plugin" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    remote = tomllib.loads(
        (plugin_root / "example_remote_backend" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    assert "bijux_canon_index.vectorstores" in template["project"]["entry-points"]
    assert "bijux_canon_index.vectorstores" in remote["project"]["entry-points"]
