# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.core.invariants import validate_trace
from bijux_canon_reason.core.types import Trace


def test_validate_trace_rejects_unknown_schema_version() -> None:
    t = Trace(schema_version=999, events=[])
    errs = validate_trace(t)
    assert any("schema_version" in e for e in errs)


def test_validate_trace_rejects_unknown_protocol_version() -> None:
    t = Trace(runtime_protocol_version=999, events=[])
    errs = validate_trace(t)
    assert any("runtime_protocol_version" in e for e in errs)
