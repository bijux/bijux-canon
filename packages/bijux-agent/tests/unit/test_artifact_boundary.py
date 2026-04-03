"""Ensure the artifact guard keeps writes inside artifacts/test/."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_artifact_guard_prevents_root_writes(tmp_path: Path) -> None:
    """Writing outside artifacts/test/ must raise a runtime error."""
    forbidden = Path("/") / "tmp" / "illegal_artifact.txt"
    with pytest.raises(RuntimeError, match="Writes, temporary files, and artifacts"):
        forbidden.write_text("should fail")
