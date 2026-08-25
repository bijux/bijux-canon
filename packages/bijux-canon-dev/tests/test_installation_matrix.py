from __future__ import annotations

from collections.abc import Mapping, Sequence
from email.message import Message
import json
from pathlib import Path
import tomllib
import zipfile

import pytest

from bijux_canon_dev.release.installation_matrix import (
    InstallationMatrixError,
    run_installation_matrix,
)
from bijux_canon_dev.release.python_support_matrix import CommandResult


SOURCE_COMMIT = "3" * 40
PYTHON_VERSIONS = ("3.11", "3.12", "3.13", "3.14")


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    package = root / "packages" / "example"
    source = package / "src" / "example"
    source.mkdir(parents=True)
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """\
[project]
name = "workspace-repository"
version = "1.2.3"
requires-python = ">=3.11,<4"

[tool.bijux_canon]
primary_packages = ["example"]
compat_packages = []

[tool.bijux_canon.package_dirs]
example = "packages/example"

[tool.hatch.build.targets.wheel]
bypass-selection = true
""",
        encoding="utf-8",
    )
    classifiers = "\n".join(
        f'  "Programming Language :: Python :: {version}",'
        for version in PYTHON_VERSIONS
    )
    (package / "pyproject.toml").write_text(
        f"""\
[project]
name = "example"
version = "1.2.3"
requires-python = ">=3.11,<4"
classifiers = [
{classifiers}
  "Operating System :: OS Independent",
]

[project.scripts]
example = "example:main"

[tool.hatch.build.targets.wheel]
packages = ["src/example"]
include = ["src/example/py.typed"]

[tool.hatch.build.targets.wheel.package-data]
example = ["py.typed"]
""",
        encoding="utf-8",
    )
    (source / "__init__.py").write_text("def main(): pass\n", encoding="utf-8")
    (source / "py.typed").write_text("typed\n", encoding="utf-8")
    return root


def _wheel(directory: Path, name: str, *, module: str | None) -> Path:
    normalized = name.replace("-", "_")
    path = directory / f"{normalized}-1.2.3-py3-none-any.whl"
    metadata = Message()
    metadata["Metadata-Version"] = "2.4"
    metadata["Name"] = name
    metadata["Version"] = "1.2.3"
    metadata["Requires-Python"] = ">=3.11,<4"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{normalized}-1.2.3.dist-info/METADATA", metadata.as_bytes())
        if module:
            archive.writestr(f"{module}/__init__.py", "def main(): pass\n")
            archive.writestr(f"{module}/py.typed", "typed\n")
            archive.writestr(
                f"{normalized}-1.2.3.dist-info/entry_points.txt",
                f"[console_scripts]\nexample = {module}:main\n",
            )
    return path


def _wheel_set(root: Path) -> Path:
    wheel_dir = root / "artifacts" / "wheels"
    wheel_dir.mkdir(parents=True)
    _wheel(wheel_dir, "example", module="example")
    return wheel_dir


def _dependency_wheel_set(root: Path) -> Path:
    directory = root / "artifacts" / "dependencies"
    directory.mkdir(parents=True)
    return directory


def _passing_runner(
    command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
) -> CommandResult:
    return CommandResult(tuple(command), 0, "{}\n", "", 0.01)


def test_matrix_installs_each_wheel_and_complete_family(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    dependency_wheel_dir = _dependency_wheel_set(root)
    output = root / "artifacts" / "reports" / "result.json"
    commands: list[tuple[str, ...]] = []

    def runner(
        command: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CommandResult:
        commands.append(tuple(command))
        return _passing_runner(command, cwd, environment)

    evidence = run_installation_matrix(
        repo_root=root,
        wheel_dir=wheel_dir,
        dependency_wheel_dir=dependency_wheel_dir,
        output_path=output,
        environment_root=root / "artifacts" / "install" / "environments",
        source_commit=SOURCE_COMMIT,
        python_version="3.11",
        uv_executable=Path("/usr/bin/true"),
        runner=runner,
    )

    assert evidence["result"] == "passed"
    assert evidence["wheel_count"] == 1
    assert evidence["individual_install_count"] == 1
    assert evidence["family_install_count"] == 1
    assert evidence["dependency_wheel_count"] == 0
    assert evidence["public_index_access"] is False
    assert evidence["package_results"] == [
        {
            "package_id": "example",
            "package_class": "canonical",
            "status": "passed",
        }
    ]
    assert len(commands) == 10
    assert any("--constraint" in command for command in commands)
    assert all(
        "--no-index" in command
        for command in commands
        if "pip" in command and "install" in command
    )
    assert any(command[-1] == "--help" for command in commands)
    inspector = next(command[-1] for command in commands if "-I" in command)
    assert "packages/example/src" in inspector
    assert "source_roots" in inspector
    constraints = root / str(evidence["constraint_file"])
    assert constraints == root / "artifacts" / "install" / "candidate-constraints.txt"
    assert constraints.read_text(encoding="utf-8") == "example==1.2.3\n"


def test_matrix_retains_one_row_failure_and_continues(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    dependency_wheel_dir = _dependency_wheel_set(root)
    output = root / "artifacts" / "install" / "result.json"

    def runner(
        command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
    ) -> CommandResult:
        fails = (
            "pip" in command and "check" in command and "/example/" in " ".join(command)
        )
        return CommandResult(
            tuple(command),
            1 if fails else 0,
            "",
            "broken dependency" if fails else "",
            0.01,
        )

    with pytest.raises(InstallationMatrixError, match="rows failed"):
        run_installation_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            dependency_wheel_dir=dependency_wheel_dir,
            output_path=output,
            environment_root=root / "artifacts" / "install" / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            runner=runner,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["result"] == "failed"
    assert "package-installation-closure" in evidence["retained_failures"]
    assert [row["status"] for row in evidence["install_results"]] == [
        "failed",
        "passed",
    ]


def test_matrix_requires_artifact_owned_environments(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    dependency_wheel_dir = _dependency_wheel_set(root)

    with pytest.raises(InstallationMatrixError, match="artifacts directory"):
        run_installation_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            dependency_wheel_dir=dependency_wheel_dir,
            output_path=root / "artifacts" / "install" / "result.json",
            environment_root=root / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            runner=_passing_runner,
        )


def test_project_publishes_installed_installation_matrix_command() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]

    assert scripts["bijux-canon-installation-matrix"] == (
        "bijux_canon_dev.release.installation_matrix:main"
    )


def test_matrix_rejects_candidate_wheel_in_dependency_closure(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    dependency_wheel_dir = _dependency_wheel_set(root)
    _wheel(dependency_wheel_dir, "example", module="example")

    with pytest.raises(InstallationMatrixError, match="candidate distribution"):
        run_installation_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            dependency_wheel_dir=dependency_wheel_dir,
            output_path=root / "artifacts" / "install" / "result.json",
            environment_root=root / "artifacts" / "install" / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            runner=_passing_runner,
        )
