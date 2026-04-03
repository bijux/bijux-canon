# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from typing import Any, cast

from pydantic import ValidationError
import pytest

from bijux_rar.core.rar_types import (
    EvidenceRef,
    StepStartedEvent,
    ToolCalledEvent,
    ToolReturnedEvent,
)


def test_trace_event_requires_fields() -> None:
    with pytest.raises(ValidationError):
        StepStartedEvent(step_id=cast(Any, None))

    with pytest.raises(ValidationError):
        ToolCalledEvent(step_id="s", call={"tool_name": "t"})

    with pytest.raises(ValidationError):
        ToolReturnedEvent(step_id="s", result={"success": True})


def test_evidence_ref_sha_validation() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            id="e1",
            uri="x",
            sha256=cast(Any, None),
            span=(0, 1),
            chunk_id="0" * 64,
            content_path="p.txt",
        )
