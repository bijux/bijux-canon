from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_package_imports() -> None:
    import bijux_canon_dev

    assert bijux_canon_dev.__doc__
