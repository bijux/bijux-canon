from __future__ import annotations

from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import pytest

from bijux_canon_dev.release.workspace_install import (
    WorkspaceInstallError,
    main,
    resolve_workspace_install,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = REPO_ROOT / "packages" / "bijux-canon-runtime"


def test_runtime_install_includes_dynamic_dependencies_and_workspace_peers() -> None:
    plan = resolve_workspace_install(REPO_ROOT, RUNTIME_DIR, ("dev",))

    assert {
        canonicalize_name(Requirement(value).name)
        for value in plan.external_requirements
    } >= {"bijux-cli", "duckdb", "pydantic", "pytest"}
    assert {path.name for path in plan.local_paths} == {
        "bijux-canon-agent",
        "bijux-canon-index",
        "bijux-canon-ingest",
        "bijux-canon-reason",
    }


def test_runtime_install_rejects_an_undeclared_extra() -> None:
    with pytest.raises(WorkspaceInstallError, match="unknown extras"):
        resolve_workspace_install(REPO_ROOT, RUNTIME_DIR, ("missing",))


def test_workspace_install_cli_prints_external_requirements(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            (
                "--repo",
                str(REPO_ROOT),
                "--package-dir",
                str(RUNTIME_DIR),
                "--kind",
                "external",
                "--extras",
                "api",
            )
        )
        == 0
    )

    names = {
        canonicalize_name(Requirement(value).name)
        for value in capsys.readouterr().out.splitlines()
    }
    assert names >= {"bijux-cli", "duckdb", "fastapi", "pydantic"}
