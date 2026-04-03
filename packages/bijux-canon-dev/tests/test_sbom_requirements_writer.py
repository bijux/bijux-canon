from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.sbom.requirements_writer import render_local_requirement


def test_render_local_requirement_rewrites_workspace_dependency(tmp_path) -> None:
    package_dir = tmp_path / "packages" / "bijux-canon-runtime"
    package_dir.mkdir(parents=True)

    rendered = render_local_requirement(
        "bijux-canon-runtime[api]>=0.3.0; python_version >= '3.11'",
        {"bijux-canon-runtime": package_dir},
    )

    assert rendered == (
        f"bijux-canon-runtime[api] @ {package_dir.as_uri()}; python_version >= \"3.11\""
    )
