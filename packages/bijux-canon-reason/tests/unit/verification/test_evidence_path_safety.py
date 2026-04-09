# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.core.types import EvidenceRef
from pydantic import ValidationError
import pytest


@pytest.mark.parametrize(
    "bad",
    [
        "../evil.txt",
        "..",
        "/abs/path",
        "C:/evil.txt",
        "evidence\\winsep.txt",
        "evidence/../escape.txt",
    ],
)
def test_evidence_content_path_rejects_traversal(bad: str) -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            uri="u", sha256="0" * 64, span=(0, 1), chunk_id="0" * 64, content_path=bad
        )
