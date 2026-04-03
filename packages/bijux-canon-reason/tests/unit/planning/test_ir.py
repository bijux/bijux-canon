# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.planning.ir import StepSpec, ToolRequest


def test_stepspec_defaults_and_tool_requests() -> None:
    spec = StepSpec(kind="derive")
    assert spec.kind == "derive"
    tr = ToolRequest(tool_name="retrieve", arguments={"query": "q"})
    assert tr.tool_name == "retrieve"
    assert tr.arguments["query"] == "q"
