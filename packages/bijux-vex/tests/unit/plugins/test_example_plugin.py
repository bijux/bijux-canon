# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations


def test_example_plugin_exports() -> None:
    from bijux_vex.plugins import example

    assert callable(example.register_vectorstore)
    assert callable(example.register_embedding)
    assert callable(example.register_runner)
