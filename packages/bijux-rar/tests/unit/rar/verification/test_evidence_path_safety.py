# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import pytest
from pydantic import ValidationError

from bijux_rar.core.rar_types import EvidenceRef


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
