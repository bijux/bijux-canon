from __future__ import annotations

from collections.abc import Mapping, Sequence
from email.message import Message
import json
from pathlib import Path
import tomllib
from typing import cast
import zipfile

import pytest

from bijux_canon_dev.release.python_support_matrix import (
    CommandResult,
    PythonSupportVerificationError,
    inspect_wheels,
    inspect_workspace,
    run_python_support_matrix,
)

SOURCE_COMMIT = "1" * 40
PYTHON_VERSIONS = ("3.11", "3.12", "3.13", "3.14")


def _project(name: str, *, classifiers: tuple[str, ...] = PYTHON_VERSIONS) -> str:
    classifier_lines = "\n".join(
        f'  "Programming Language :: Python :: {version}",' for version in classifiers
    )
    return f"""\
[project]
name = {name!r}
version = "1.2.3"
requires-python = ">=3.11,<4"
classifiers = [
{classifier_lines}
  "Operating System :: OS Independent",
]
"""


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    package = root / "packages" / "example"
    package.mkdir(parents=True)
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
""",
        encoding="utf-8",
    )
    (package / "pyproject.toml").write_text(_project("example"), encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return root


def _wheel(
    directory: Path,
    name: str,
    *,
    module: str | None,
    script: str | None = None,
) -> Path:
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
            archive.writestr(f"{module}/__init__.py", "")
        if script:
            archive.writestr(
                f"{normalized}-1.2.3.dist-info/entry_points.txt",
                f"[console_scripts]\n{script} = {module}:main\n",
            )
    return path


def _wheel_set(root: Path) -> Path:
    wheel_dir = root / "artifacts" / "wheels"
    wheel_dir.mkdir(parents=True)
    _wheel(wheel_dir, "example", module="example", script="example")
    return wheel_dir


def test_workspace_support_is_derived_from_every_package_classifier(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)

    support = inspect_workspace(root)

    assert support.python_versions == PYTHON_VERSIONS
    assert support.distribution_names == ("example",)
    assert support.package_classes == (("example", "canonical"),)


def test_workspace_support_rejects_classifier_drift(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    second = root / "packages" / "second"
    second.mkdir()
    (second / "pyproject.toml").write_text(
        _project("second", classifiers=("3.11", "3.12", "3.13")),
        encoding="utf-8",
    )
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text(
        root_pyproject.read_text(encoding="utf-8").replace(
            'primary_packages = ["example"]',
            'primary_packages = ["example", "second"]',
        )
        + 'second = "packages/second"\n',
        encoding="utf-8",
    )

    with pytest.raises(
        PythonSupportVerificationError, match="classifier sets disagree"
    ):
        inspect_workspace(root)


def test_workspace_support_rejects_ambiguous_package_class(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text(
        root_pyproject.read_text(encoding="utf-8").replace(
            "compat_packages = []", 'compat_packages = ["example"]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(PythonSupportVerificationError, match="must partition"):
        inspect_workspace(root)


def test_workspace_support_requires_platform_promise(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    package_pyproject = root / "packages" / "example" / "pyproject.toml"
    package_pyproject.write_text(
        package_pyproject.read_text(encoding="utf-8").replace(
            '  "Operating System :: OS Independent",\n', ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(PythonSupportVerificationError, match="platform promise"):
        inspect_workspace(root)


def test_wheel_inventory_reads_imports_scripts_and_hashes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)

    records = inspect_wheels(wheel_dir, ("example",))

    example = next(
        record for record in records if record.distribution_name == "example"
    )
    assert example.version == "1.2.3"
    assert example.import_names == ("example",)
    assert example.console_scripts == ("example",)
    assert len(example.sha256) == 64


def test_wheel_inventory_rejects_missing_and_unsafe_inputs(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    (wheel_dir / "example-1.2.3-py3-none-any.whl").unlink()

    with pytest.raises(PythonSupportVerificationError, match="missing"):
        inspect_wheels(wheel_dir, ("example",))

    bad = wheel_dir / "example-1.2.3-py3-none-any.whl"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("../METADATA", "unsafe")
    with pytest.raises(PythonSupportVerificationError, match="unsafe member"):
        inspect_wheels(wheel_dir, ("example",))


def test_matrix_runs_every_declared_version_and_retains_evidence(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    commands: list[tuple[str, ...]] = []

    def runner(
        command: Sequence[str], _cwd: Path, _env: Mapping[str, str]
    ) -> CommandResult:
        commands.append(tuple(command))
        return CommandResult(tuple(command), 0, "ok", "", 0.01)

    output = root / "artifacts" / "matrix" / "result.json"
    evidence = run_python_support_matrix(
        repo_root=root,
        wheel_dir=wheel_dir,
        output_path=output,
        environment_root=root / "artifacts" / "matrix" / "environments",
        source_commit=SOURCE_COMMIT,
        uv_executable=Path("/usr/bin/true"),
        runner=runner,
    )

    assert evidence["result"] == "passed"
    assert evidence["advertised_python_versions"] == list(PYTHON_VERSIONS)
    assert evidence["distribution_count"] == 1
    assert evidence["import_count"] == 1
    assert evidence["console_script_count"] == 1
    combinations = cast(
        list[dict[str, object]], evidence["package_python_combinations"]
    )
    assert [item["combination_id"] for item in combinations] == [
        "example--py311",
        "example--py312",
        "example--py313",
        "example--py314",
    ]
    assert len(commands) == len(PYTHON_VERSIONS) * 4
    assert (
        json.loads(output.read_text(encoding="utf-8"))["source_commit"] == SOURCE_COMMIT
    )


def test_matrix_retains_failed_command_and_continues_other_versions(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    failed_once = False

    def runner(
        command: Sequence[str], _cwd: Path, _env: Mapping[str, str]
    ) -> CommandResult:
        nonlocal failed_once
        should_fail = "3.12" in command and not failed_once
        failed_once = failed_once or should_fail
        return CommandResult(
            tuple(command),
            1 if should_fail else 0,
            "",
            "failure" if should_fail else "",
            0.01,
        )

    output = root / "artifacts" / "matrix" / "result.json"
    with pytest.raises(PythonSupportVerificationError, match="rows failed"):
        run_python_support_matrix(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=output,
            environment_root=root / "artifacts" / "matrix" / "environments",
            source_commit=SOURCE_COMMIT,
            uv_executable=Path("/usr/bin/true"),
            runner=runner,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["result"] == "failed"
    assert [row["status"] for row in evidence["version_results"]] == [
        "passed",
        "failed",
        "passed",
        "passed",
    ]
    failed = evidence["version_results"][1]["commands"][-1]
    assert failed["exit_code"] == 1
    assert failed["stderr"] == "failure"


def test_project_publishes_installed_support_command() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]

    assert scripts["bijux-canon-python-support"] == (
        "bijux_canon_dev.release.python_support_matrix:main"
    )
