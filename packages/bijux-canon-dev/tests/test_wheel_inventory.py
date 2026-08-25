from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tomllib
from typing import Any, cast
import zipfile

import pytest

from bijux_canon_dev.release.wheel_inventory import (
    CommandResult,
    WheelInventoryError,
    inspect_workspace_policy,
    run_wheel_inventory,
)


SOURCE_COMMIT = "2" * 40
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_live_workspace_declares_exact_twelve_distributions() -> None:
    policies = inspect_workspace_policy(REPO_ROOT)

    assert len(policies) == 12
    assert all(policy.package_key is not None for policy in policies)
    assert "bijux-canon-repository" not in {
        policy.distribution_name for policy in policies
    }


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    package = root / "packages" / "example"
    source = package / "src" / "example"
    source.mkdir(parents=True)
    (root / "LICENSE").write_text("license\n", encoding="utf-8")
    (root / "NOTICE").write_text("notice\n", encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """\
[project]
name = "workspace-repository"
version = "1.2.3"
requires-python = ">=3.11,<4"
dependencies = []

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
    (package / "pyproject.toml").write_text(
        """\
[project]
name = "example"
version = "1.2.3"
requires-python = ">=3.11,<4"
dependencies = ["packaging>=24,<27"]
license = { text = "Apache-2.0" }

[project.optional-dependencies]
feature = ["PyYAML>=6,<7"]

[project.scripts]
example = "example:main"

[tool.hatch.build.targets.wheel]
packages = ["src/example"]
include = ["src/example/py.typed"]

[tool.hatch.build.targets.wheel.package-data]
example = ["py.typed", "api/schema.hash"]
""",
        encoding="utf-8",
    )
    (source / "__init__.py").write_text("def main(): pass\n", encoding="utf-8")
    (source / "py.typed").write_text("typed\n", encoding="utf-8")
    (source / "api").mkdir()
    (source / "api" / "schema.hash").write_text("abc\n", encoding="utf-8")
    return root


def test_workspace_policy_rejects_conflicting_console_script_ownership(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text(
        root_pyproject.read_text(encoding="utf-8")
        .replace(
            'primary_packages = ["example"]',
            'primary_packages = ["example", "second"]',
        )
        .replace(
            'example = "packages/example"',
            'example = "packages/example"\nsecond = "packages/second"',
        ),
        encoding="utf-8",
    )
    example_pyproject = root / "packages" / "example" / "pyproject.toml"
    second = root / "packages" / "second"
    second.mkdir()
    (second / "pyproject.toml").write_text(
        example_pyproject.read_text(encoding="utf-8")
        .replace('name = "example"', 'name = "second"', 1)
        .replace('packages = ["src/example"]', 'packages = ["src/second"]')
        .replace('include = ["src/example/py.typed"]', 'include = ["src/second/py.typed"]')
        .replace(
            'example = ["py.typed", "api/schema.hash"]',
            'second = ["py.typed", "api/schema.hash"]',
        )
        .replace('example = "example:main"', 'example = "second:main"'),
        encoding="utf-8",
    )

    with pytest.raises(
        WheelInventoryError,
        match="one deterministic entrypoint",
    ):
        inspect_workspace_policy(root)


def _record(payloads: dict[str, bytes], record_name: str) -> bytes:
    rows: list[str] = []
    for name, payload in sorted(payloads.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=")
        rows.append(f"{name},sha256={digest.decode('ascii')},{len(payload)}")
    rows.append(f"{record_name},,")
    return ("\n".join(rows) + "\n").encode()


def _wheel(
    root: Path,
    name: str,
    *,
    dependency: str | None = None,
    extra_dependency: str | None = None,
    module: str | None = None,
    include_assets: bool = True,
    leak: bool = False,
    corrupt_record: bool = False,
) -> Path:
    wheel_dir = root / "artifacts" / "wheels"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    normalized = name.replace("-", "_")
    dist_info = f"{normalized}-1.2.3.dist-info"
    path = wheel_dir / f"{normalized}-1.2.3-py3-none-any.whl"

    metadata = Message()
    metadata["Metadata-Version"] = "2.4"
    metadata["Name"] = name
    metadata["Version"] = "1.2.3"
    metadata["Requires-Python"] = ">=3.11,<4"
    metadata["License-File"] = "LICENSE"
    metadata["License-File"] = "NOTICE"
    if module:
        metadata["License"] = "Apache-2.0"
        metadata["Requires-Dist"] = dependency or "packaging>=24,<27"
        metadata["Provides-Extra"] = "feature"
        metadata["Requires-Dist"] = (
            extra_dependency or "PyYAML>=6,<7; extra == 'feature'"
        )

    wheel_metadata = Message()
    wheel_metadata["Wheel-Version"] = "1.0"
    wheel_metadata["Generator"] = "tests"
    wheel_metadata["Root-Is-Purelib"] = "true"
    wheel_metadata["Tag"] = "py3-none-any"
    payloads = {
        f"{dist_info}/METADATA": metadata.as_bytes(),
        f"{dist_info}/WHEEL": wheel_metadata.as_bytes(),
        f"{dist_info}/licenses/LICENSE": (root / "LICENSE").read_bytes(),
        f"{dist_info}/licenses/NOTICE": (root / "NOTICE").read_bytes(),
    }
    if module:
        payloads[f"{module}/__init__.py"] = b"def main(): pass\n"
        payloads[f"{dist_info}/entry_points.txt"] = (
            f"[console_scripts]\nexample = {module}:main\n".encode()
        )
        if include_assets:
            payloads[f"{module}/py.typed"] = b"typed\n"
            payloads[f"{module}/api/schema.hash"] = b"abc\n"
    if leak:
        payloads["src/private.py"] = b"secret\n"
    record_name = f"{dist_info}/RECORD"
    payloads[record_name] = _record(payloads, record_name)
    if corrupt_record:
        payloads[record_name] = payloads[record_name].replace(
            b"sha256=", b"sha256=x", 1
        )
    with zipfile.ZipFile(path, "w") as archive:
        for member, payload in payloads.items():
            archive.writestr(member, payload)
    return path


def _sdist(root: Path, name: str, *, version: str = "1.2.3") -> Path:
    wheel_dir = root / "artifacts" / "wheels"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    normalized = name.replace("-", "_")
    archive_root = f"{normalized}-{version}"
    path = wheel_dir / f"{normalized}-{version}.tar.gz"
    metadata = f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"
    with tarfile.open(path, "w:gz") as archive:
        for relative, payload in (
            ("PKG-INFO", metadata.encode()),
            ("pyproject.toml", b"[build-system]\nrequires = []\n"),
        ):
            info = tarfile.TarInfo(f"{archive_root}/{relative}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return path


def _wheel_set(root: Path, **example_options: Any) -> Path:
    _wheel(root, "example", module="example", **example_options)
    _sdist(root, "example")
    return root / "artifacts" / "wheels"


def _passing_runner(
    command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
) -> CommandResult:
    return CommandResult(tuple(command), 0, "PASSED\n", "", 0.01)


def test_workspace_policy_derives_package_contracts(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)

    policies = inspect_workspace_policy(root)

    assert [policy.distribution_name for policy in policies] == ["example"]
    example = policies[0]
    assert example.package_class == "canonical"
    assert example.required_asset_patterns == (
        "example/__init__.py",
        "example/api/schema.hash",
        "example/py.typed",
    )


def test_inventory_validates_complete_family_and_retains_bindings(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    output = root / "artifacts" / "inventory" / "result.json"

    evidence = run_wheel_inventory(
        repo_root=root,
        wheel_dir=wheel_dir,
        output_path=output,
        source_commit=SOURCE_COMMIT,
        twine_python=Path("/usr/bin/true"),
        runner=_passing_runner,
    )

    assert evidence["result"] == "passed"
    assert evidence["wheel_count"] == 1
    assert evidence["sdist_count"] == 1
    assert evidence["artifact_count"] == 2
    assert evidence["package_count"] == 1
    assert evidence["version"] == "1.2.3"
    assert evidence["lock_identity"] == hashlib.sha256(b"version = 1\n").hexdigest()
    assert evidence["package_results"] == [
        {
            "package_id": "example",
            "package_class": "canonical",
            "status": "passed",
        }
    ]
    records = cast(list[dict[str, object]], evidence["records"])
    record = next(item for item in records if item["package_id"] == "example")
    assert record["schema_assets"] == ["example/api/schema.hash"]
    assert evidence["sdist_records"][0]["status"] == "passed"
    assert output.is_file()


def test_inventory_rejects_missing_source_archive(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)
    next(wheel_dir.glob("*.tar.gz")).unlink()
    output = root / "artifacts" / "inventory" / "result.json"

    with pytest.raises(WheelInventoryError):
        run_wheel_inventory(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=output,
            source_commit=SOURCE_COMMIT,
            twine_python=Path("/usr/bin/true"),
            runner=_passing_runner,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["retained_failures"] == ["missing-sdist:example"]


def test_inventory_retains_dependency_and_twine_failures(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root, dependency="packaging>=23,<24")
    output = root / "artifacts" / "inventory" / "result.json"

    def failing_twine(
        command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
    ) -> CommandResult:
        return CommandResult(tuple(command), 1, "", "invalid metadata", 0.02)

    with pytest.raises(WheelInventoryError, match="inspect"):
        run_wheel_inventory(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=output,
            source_commit=SOURCE_COMMIT,
            twine_python=Path("/usr/bin/false"),
            runner=failing_twine,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["result"] == "failed"
    assert "twine-check" in evidence["retained_failures"]
    example = next(
        item for item in evidence["records"] if item["package_id"] == "example"
    )
    assert "dependencies" in example["issues"]
    assert evidence["twine"]["stderr"] == "invalid metadata"


@pytest.mark.parametrize(
    ("options", "expected_issue"),
    [
        ({"include_assets": False}, "runtime-assets"),
        ({"leak": True}, "source-leaks"),
        ({"corrupt_record": True}, "record-hash"),
    ],
)
def test_inventory_rejects_missing_leaked_and_corrupt_contents(
    tmp_path: Path, options: dict[str, bool], expected_issue: str
) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root, **options)
    output = root / "artifacts" / "inventory" / "result.json"

    with pytest.raises(WheelInventoryError):
        run_wheel_inventory(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=output,
            source_commit=SOURCE_COMMIT,
            twine_python=Path("/usr/bin/true"),
            runner=_passing_runner,
        )

    evidence = json.loads(output.read_text(encoding="utf-8"))
    example = next(
        item for item in evidence["records"] if item["package_id"] == "example"
    )
    assert any(expected_issue in issue for issue in example["issues"])


def test_inventory_requires_disposable_output_boundaries(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    wheel_dir = _wheel_set(root)

    with pytest.raises(WheelInventoryError, match="artifacts directory"):
        run_wheel_inventory(
            repo_root=root,
            wheel_dir=wheel_dir,
            output_path=root / "wheel-inventory.json",
            source_commit=SOURCE_COMMIT,
            twine_python=Path("/usr/bin/true"),
            runner=_passing_runner,
        )


def test_project_publishes_installed_wheel_inventory_command() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]

    assert scripts["bijux-canon-wheel-inventory"] == (
        "bijux_canon_dev.release.wheel_inventory:main"
    )
