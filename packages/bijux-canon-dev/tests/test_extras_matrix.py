from __future__ import annotations

from collections.abc import Mapping, Sequence
from email.message import Message
import json
from pathlib import Path
import tomllib
import zipfile

import pytest

from bijux_canon_dev.release.extras_matrix import (
    ExtrasMatrixError,
    run_extras_matrix,
)
from bijux_canon_dev.release.python_support_matrix import CommandResult


SOURCE_COMMIT = "4" * 40
PYTHON_VERSIONS = ("3.11", "3.12", "3.13", "3.14")
CAPABILITIES = {("example", "api"): ("fastapi",)}


def _repository(tmp_path: Path, *, extra_dependencies: bool = True) -> Path:
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
    dependency = '  "fastapi>=0.110,<1.0",' if extra_dependencies else ""
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

[project.optional-dependencies]
api = [
{dependency}
]

[tool.hatch.build.targets.wheel]
packages = ["src/example"]
include = ["src/example/py.typed"]

[tool.hatch.build.targets.wheel.package-data]
example = ["py.typed"]
""",
        encoding="utf-8",
    )
    (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "py.typed").write_text("typed\n", encoding="utf-8")
    return root


def _wheel(
    directory: Path,
    name: str,
    *,
    module: str | None,
    extra_dependencies: bool = True,
) -> Path:
    normalized = name.replace("-", "_")
    path = directory / f"{normalized}-1.2.3-py3-none-any.whl"
    metadata = Message()
    metadata["Metadata-Version"] = "2.4"
    metadata["Name"] = name
    metadata["Version"] = "1.2.3"
    metadata["Requires-Python"] = ">=3.11,<4"
    if module:
        metadata["Provides-Extra"] = "api"
        if extra_dependencies:
            metadata["Requires-Dist"] = 'fastapi<1.0,>=0.110; extra == "api"'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{normalized}-1.2.3.dist-info/METADATA", metadata.as_bytes())
        if module:
            archive.writestr(f"{module}/__init__.py", "")
            archive.writestr(f"{module}/py.typed", "typed\n")
    return path


def _wheel_set(root: Path, *, extra_dependencies: bool = True) -> Path:
    wheel_dir = root / "artifacts" / "wheels"
    wheel_dir.mkdir(parents=True)
    _wheel(wheel_dir, "workspace-repository", module=None)
    _wheel(
        wheel_dir,
        "example",
        module="example",
        extra_dependencies=extra_dependencies,
    )
    return wheel_dir


def _passing_runner(
    command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
) -> CommandResult:
    stdout = (
        '{"installed_dependencies":{"fastapi":"1.0"},"module_origins":{}}\n'
        if "-I" in command
        else ""
    )
    return CommandResult(tuple(command), 0, stdout, "", 0.01)


def test_matrix_installs_and_probes_each_advertised_extra(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    output = root / "artifacts" / "extras" / "result.json"
    commands: list[tuple[str, ...]] = []

    def runner(
        command: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CommandResult:
        commands.append(tuple(command))
        return _passing_runner(command, cwd, environment)

    evidence = run_extras_matrix(
        repo_root=root,
        wheel_dir=wheel_dir,
        output_path=output,
        environment_root=root / "artifacts" / "extras" / "environments",
        source_commit=SOURCE_COMMIT,
        python_version="3.11",
        uv_executable=Path("/usr/bin/true"),
        capability_modules=CAPABILITIES,
        runner=runner,
    )

    assert evidence["result"] == "passed"
    assert evidence["extra_count"] == 1
    assert evidence["package_results"] == [
        {
            "package_id": "example",
            "package_class": "canonical",
            "advertised_extra_count": 1,
            "status": "passed",
        }
    ]
    assert len(commands) == 4
    assert str(next(wheel_dir.glob("example-*.whl"))) + "[api]" in commands[1]
    assert "fastapi" in commands[3][-1]
    assert json.loads(output.read_text(encoding="utf-8"))["result"] == "passed"


def test_matrix_rejects_an_empty_advertised_extra(tmp_path: Path) -> None:
    root = _repository(tmp_path, extra_dependencies=False)
    wheel_dir = _wheel_set(root, extra_dependencies=False)

    with pytest.raises(ExtrasMatrixError, match="empty extras"):
        run_extras_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=root / "artifacts" / "extras" / "result.json",
            environment_root=root / "artifacts" / "extras" / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            capability_modules=CAPABILITIES,
            runner=_passing_runner,
        )


def test_matrix_rejects_an_unmapped_capability(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)

    with pytest.raises(ExtrasMatrixError, match="capability mapping mismatch"):
        run_extras_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=root / "artifacts" / "extras" / "result.json",
            environment_root=root / "artifacts" / "extras" / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            capability_modules={},
            runner=_passing_runner,
        )


def test_matrix_retains_a_failed_install_row(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)

    def runner(
        command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
    ) -> CommandResult:
        failed = "install" in command
        return CommandResult(tuple(command), 1 if failed else 0, "", "failed", 0.01)

    output = root / "artifacts" / "extras" / "result.json"
    with pytest.raises(ExtrasMatrixError, match="extras rows failed"):
        run_extras_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=output,
            environment_root=root / "artifacts" / "extras" / "environments",
            source_commit=SOURCE_COMMIT,
            python_version="3.11",
            uv_executable=Path("/usr/bin/true"),
            capability_modules=CAPABILITIES,
            runner=runner,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["result"] == "failed"
    assert "package-extra-capabilities" in evidence["retained_failures"]


def test_project_publishes_installed_extras_matrix_command() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]

    assert scripts["bijux-canon-extras-matrix"] == (
        "bijux_canon_dev.release.extras_matrix:main"
    )
