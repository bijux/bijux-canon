from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.sbom.requirements_writer import (
    render_local_requirement,
    write_requirements,
)


def test_render_local_requirement_rewrites_workspace_dependency(tmp_path: Path) -> None:
    package_dir = tmp_path / "packages" / "bijux-canon-runtime"
    package_dir.mkdir(parents=True)

    rendered = render_local_requirement(
        "bijux-canon-runtime[api]>=0.3.0; python_version >= '3.11'",
        {"bijux-canon-runtime": package_dir},
    )

    assert rendered == (
        f'bijux-canon-runtime[api] @ {package_dir.as_uri()}; python_version >= "3.11"'
    )


def test_write_requirements_rewrites_workspace_dependencies_for_prod_group(
    tmp_path: Path,
) -> None:
    packages_dir = tmp_path / "packages"
    runtime_dir = packages_dir / "bijux-canon-runtime"
    agent_dir = packages_dir / "bijux-canon-agent"
    runtime_dir.mkdir(parents=True)
    agent_dir.mkdir(parents=True)

    (runtime_dir / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "bijux-canon-runtime"',
                "dependencies = [",
                '  "bijux-canon-agent>=0.3.8,<0.4.0",',
                '  "duckdb>=1.1.3,<2.0.0",',
                "]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (agent_dir / "pyproject.toml").write_text(
        "\n".join(["[project]", 'name = "bijux-canon-agent"', "dependencies = []", ""]),
        encoding="utf-8",
    )

    output_path = tmp_path / "artifacts" / "requirements.txt"
    result = write_requirements(
        pyproject_path=runtime_dir / "pyproject.toml",
        output_path=output_path,
        group="prod",
        optional_group="dev",
    )

    assert result == 0
    assert output_path.read_text(encoding="utf-8").splitlines() == [
        f"bijux-canon-agent @ {agent_dir.as_uri()}",
        "duckdb>=1.1.3,<2.0.0",
    ]
