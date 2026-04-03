# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.boundaries.serde.json_file import read_json_file, write_json_file


def test_atomic_write_and_read(tmp_path: Path) -> None:
    payload = {"a": 1, "b": ["x", "y"]}
    path = tmp_path / "out.json"
    write_json_file(path, payload)
    assert path.exists()
    data = read_json_file(path)
    assert data == payload


def test_read_unknown_wrapper_is_passthrough(tmp_path: Path) -> None:
    path = tmp_path / "wrapped.json"
    path.write_text(
        '{"canonical_version":1,"data":{"hello":"world"}}', encoding="utf-8"
    )
    data = read_json_file(path)
    assert data == {"hello": "world"}
