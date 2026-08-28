"""Verify clean wheel installs without repository or sibling-source imports."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from packaging.utils import canonicalize_name, parse_wheel_filename

from bijux_canon_dev.release.python_support_matrix import (
    CommandResult,
    CommandRunner,
    WheelRecord,
    inspect_wheels,
    inspect_workspace,
)
from bijux_canon_dev.release.wheel_inventory import (
    PackagePolicy,
    inspect_workspace_policy,
)


class InstallationMatrixError(RuntimeError):
    """A clean installation imported or resolved outside its wheel contract."""


@dataclass(frozen=True)
class InstallTarget:
    """One independently installed distribution set."""

    target_id: str
    distributions: tuple[str, ...]
    import_names: tuple[str, ...]
    console_scripts: tuple[str, ...]
    required_assets: tuple[tuple[str, tuple[str, ...]], ...]
    compatibility_replacement: str | None


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise InstallationMatrixError(
            "installation commands require an absolute executable"
        )
    started = time.monotonic()
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(environment),
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        command=tuple(command),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=time.monotonic() - started,
    )


def _artifact_path(path: Path, repo_root: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to((repo_root / "artifacts").resolve())
    except ValueError as exc:
        raise InstallationMatrixError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def _python_path(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _script_path(environment: Path, script: str) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / f"{script}.exe"
    return environment / "bin" / script


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _targets(
    records: Sequence[WheelRecord], policies: Sequence[PackagePolicy]
) -> tuple[InstallTarget, ...]:
    policy_by_name = {
        canonicalize_name(policy.distribution_name): policy for policy in policies
    }
    targets: list[InstallTarget] = []
    for record in records:
        policy = policy_by_name[canonicalize_name(record.distribution_name)]
        if (
            policy.package_class == "compatibility"
            and len(policy.dynamic_dependency_names) != 1
        ):
            raise InstallationMatrixError(
                f"compatibility distribution needs one canonical replacement: "
                f"{record.distribution_name}"
            )
        targets.append(
            InstallTarget(
                target_id=record.distribution_name,
                distributions=(record.distribution_name,),
                import_names=record.import_names,
                console_scripts=record.console_scripts,
                required_assets=(
                    (
                        record.distribution_name,
                        policy.required_asset_patterns,
                    ),
                ),
                compatibility_replacement=(
                    policy.dynamic_dependency_names[0]
                    if policy.package_class == "compatibility"
                    and len(policy.dynamic_dependency_names) == 1
                    else None
                ),
            )
        )
    targets.append(
        InstallTarget(
            target_id="complete-family",
            distributions=tuple(record.distribution_name for record in records),
            import_names=tuple(
                sorted({name for record in records for name in record.import_names})
            ),
            console_scripts=tuple(
                sorted(
                    {script for record in records for script in record.console_scripts}
                )
            ),
            required_assets=tuple(
                (
                    record.distribution_name,
                    policy_by_name[
                        canonicalize_name(record.distribution_name)
                    ].required_asset_patterns,
                )
                for record in records
            ),
            compatibility_replacement=None,
        )
    )
    return tuple(targets)


def _inspector(
    *,
    target: InstallTarget,
    versions: Mapping[str, str],
    source_roots: Sequence[Path],
) -> str:
    assets = {name: list(patterns) for name, patterns in target.required_assets}
    return "\n".join(
        [
            "import fnmatch",
            "import importlib",
            "import importlib.metadata as metadata",
            "import json",
            "from pathlib import Path",
            "import sys",
            "import sysconfig",
            "import warnings",
            f"target_distributions = {target.distributions!r}",
            f"candidate_versions = {dict(versions)!r}",
            f"import_names = {target.import_names!r}",
            f"required_assets = {assets!r}",
            f"compatibility_replacement = {target.compatibility_replacement!r}",
            f"source_roots = tuple(Path(value).resolve() for value in {tuple(map(str, source_roots))!r})",
            "purelib = Path(sysconfig.get_paths()['purelib']).resolve()",
            "assert all(not any(Path(value or '.').resolve().is_relative_to(root) for root in source_roots) for value in sys.path)",
            "installed_candidates = {}",
            "for name, expected_version in candidate_versions.items():",
            "    try:",
            "        actual_version = metadata.version(name)",
            "    except metadata.PackageNotFoundError:",
            "        continue",
            "    assert actual_version == expected_version, (name, actual_version, expected_version)",
            "    installed_candidates[name] = actual_version",
            "for name in target_distributions:",
            "    assert name in installed_candidates, (name, installed_candidates)",
            "module_origins = {}",
            "with warnings.catch_warnings(record=True) as compatibility_warnings:",
            "    warnings.simplefilter('always', FutureWarning)",
            "    for name in import_names:",
            "        module = importlib.import_module(name)",
            "        origin = Path(module.__file__).resolve()",
            "        assert origin.is_relative_to(purelib), (name, origin, purelib)",
            "        assert not any(origin.is_relative_to(root) for root in source_roots), (name, origin, source_roots)",
            "        module_origins[name] = str(origin)",
            "warning_messages = [str(item.message) for item in compatibility_warnings if issubclass(item.category, FutureWarning)]",
            "if compatibility_replacement is not None:",
            "    assert any(compatibility_replacement in message for message in warning_messages), (compatibility_replacement, warning_messages)",
            "entry_points = {}",
            "data_files = {}",
            "for name in target_distributions:",
            "    dist = metadata.distribution(name)",
            "    files = tuple(dist.files or ())",
            "    file_names = [item.as_posix() for item in files]",
            "    for pattern in required_assets.get(name, []):",
            "        matches = [item for item in file_names if fnmatch.fnmatchcase(item, pattern)]",
            "        assert matches, (name, pattern, file_names)",
            "        for match in matches:",
            "            location = Path(dist.locate_file(match)).resolve()",
            "            assert location.is_relative_to(purelib), (name, match, location)",
            "        data_files.setdefault(name, []).extend(matches)",
            "    for entry in dist.entry_points:",
            "        loaded = entry.load()",
            "        assert loaded is not None, (name, entry.group, entry.name)",
            "        entry_points[f'{name}:{entry.group}:{entry.name}'] = entry.value",
            "print(json.dumps({'installed_candidates': installed_candidates, 'module_origins': module_origins, 'entry_points': entry_points, 'data_files': data_files, 'compatibility_warnings': warning_messages}, sort_keys=True))",
        ]
    )


def _ingest_document_probe(repo_root: Path) -> str:
    corpus = repo_root / "examples" / "document-formats" / "corpus"
    return "\n".join(
        [
            "import json",
            "from pathlib import Path",
            "from bijux_canon_ingest import CanonicalIngestRequest, ingest_corpus",
            f"corpus = Path({str(corpus)!r})",
            "result = ingest_corpus(CanonicalIngestRequest.for_directory(root_path=corpus, root_name='installed-formats', corpus_name='installed-formats'))",
            "manifest = result.manifest()",
            "expected = {'docx': 1, 'html': 1, 'jats': 1, 'markdown': 1, 'pdf-digital': 1, 'text': 1}",
            "assert manifest['formats'] == expected, manifest['formats']",
            "assert manifest['document_count'] == 6, manifest",
            "assert manifest['ocr_required_count'] == 1, manifest",
            "assert manifest['rejection_count'] == 0, manifest",
            "print(json.dumps(manifest, sort_keys=True))",
        ]
    )


def _constraint_file(records: Sequence[WheelRecord], *, environment_root: Path) -> Path:
    path = environment_root.parent / "candidate-constraints.txt"
    path.write_text(
        "".join(
            f"{record.distribution_name}=={record.version}\n" for record in records
        ),
        encoding="utf-8",
    )
    return path


def _dependency_wheels(
    directory: Path,
    *,
    candidate_names: Sequence[str],
) -> tuple[dict[str, object], ...]:
    if directory.is_symlink() or not directory.is_dir():
        raise InstallationMatrixError(
            f"dependency wheel directory must be a regular directory: {directory}"
        )
    candidates = {canonicalize_name(name) for name in candidate_names}
    records: list[dict[str, object]] = []
    identities: set[tuple[str, str]] = set()
    for wheel in sorted(directory.iterdir()):
        if wheel.is_symlink() or not wheel.is_file() or wheel.suffix != ".whl":
            raise InstallationMatrixError(
                f"dependency wheelhouse contains a non-wheel entry: {wheel.name}"
            )
        try:
            name, version, _build, _tags = parse_wheel_filename(wheel.name)
        except ValueError as exc:
            raise InstallationMatrixError(
                f"dependency wheel filename is invalid: {wheel.name}"
            ) from exc
        normalized = canonicalize_name(str(name))
        if normalized in candidates:
            raise InstallationMatrixError(
                f"candidate distribution duplicated in dependency wheelhouse: {name}"
            )
        identity = (normalized, str(version))
        if identity in identities:
            raise InstallationMatrixError(
                f"duplicate dependency wheel identity: {name}=={version}"
            )
        identities.add(identity)
        records.append(
            {
                "distribution_name": str(name),
                "version": str(version),
                "filename": wheel.name,
                "sha256": _sha256(wheel),
            }
        )
    return tuple(records)


def run_installation_matrix(
    *,
    repo_root: Path,
    wheel_dir: Path,
    dependency_wheel_dir: Path,
    output_path: Path,
    environment_root: Path,
    source_commit: str,
    python_version: str,
    uv_executable: Path,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Install every wheel independently and the complete exact family."""
    repo_root = repo_root.resolve()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise InstallationMatrixError("source commit must be a lowercase full Git SHA")
    wheel_dir = _artifact_path(wheel_dir, repo_root, label="wheel directory")
    dependency_wheel_dir = _artifact_path(
        dependency_wheel_dir, repo_root, label="dependency wheel directory"
    )
    output_path = _artifact_path(output_path, repo_root, label="output path")
    environment_root = _artifact_path(
        environment_root, repo_root, label="environment root"
    )
    uv_executable = uv_executable.absolute()
    support = inspect_workspace(repo_root)
    records = inspect_wheels(wheel_dir, support.distribution_names)
    dependency_wheels = _dependency_wheels(
        dependency_wheel_dir,
        candidate_names=[record.distribution_name for record in records],
    )
    policies = inspect_workspace_policy(repo_root)
    source_roots = tuple(
        (policy.pyproject_path.parent / "src").resolve()
        for policy in policies
        if policy.package_key is not None
    )
    targets = _targets(records, policies)
    versions = {record.distribution_name: record.version for record in records}
    record_by_name = {
        canonicalize_name(record.distribution_name): record for record in records
    }
    environment_root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    constraints = _constraint_file(records, environment_root=environment_root)
    cache_root = output_path.parent / "cache"
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(cache_root / "pycache"),
            "UV_CACHE_DIR": str(cache_root / "uv"),
            "UV_NO_INDEX": "1",
        }
    )

    results: list[dict[str, object]] = []
    failures: list[str] = []
    for target in targets:
        target_root = environment_root / canonicalize_name(target.target_id)
        python = _python_path(target_root)
        requested_wheels = [
            record_by_name[canonicalize_name(name)].path
            for name in target.distributions
        ]
        commands: list[list[str]] = [
            [
                str(uv_executable),
                "venv",
                str(target_root),
                "--python",
                python_version,
                "--clear",
            ],
            [
                str(uv_executable),
                "pip",
                "install",
                "--no-index",
                "--python",
                str(python),
                "--constraint",
                str(constraints),
                "--find-links",
                str(wheel_dir),
                "--find-links",
                str(dependency_wheel_dir),
                *[str(path) for path in requested_wheels],
            ],
            [
                str(uv_executable),
                "pip",
                "check",
                "--python",
                str(python),
            ],
            [
                str(python),
                "-I",
                "-c",
                _inspector(
                    target=target,
                    versions=versions,
                    source_roots=source_roots,
                ),
            ],
            *[
                [str(_script_path(target_root, script)), "--help"]
                for script in target.console_scripts
            ],
        ]
        product_probe_index: int | None = None
        if canonicalize_name(target.target_id) == "bijux-canon-ingest":
            commands.append(
                [str(python), "-I", "-c", _ingest_document_probe(repo_root)]
            )
            product_probe_index = len(commands) - 1
        outcomes: list[CommandResult] = []
        for command in commands:
            outcome = runner(command, environment_root, environment)
            outcomes.append(outcome)
            if outcome.exit_code != 0:
                failures.append(f"{target.target_id}:{len(outcomes)}")
                break
        compatibility_cli_warning = target.compatibility_replacement is None
        if target.compatibility_replacement is not None:
            console_outcomes = outcomes[4 : 4 + len(target.console_scripts)]
            compatibility_cli_warning = len(console_outcomes) == len(
                target.console_scripts
            ) and all(
                target.compatibility_replacement in outcome.stderr
                for outcome in console_outcomes
            )
            if not compatibility_cli_warning:
                failures.append(f"{target.target_id}:compatibility-cli-warning")
        passed = (
            len(outcomes) == len(commands)
            and all(outcome.exit_code == 0 for outcome in outcomes)
            and compatibility_cli_warning
        )
        results.append(
            {
                "target_id": target.target_id,
                "distributions": list(target.distributions),
                "imports": list(target.import_names),
                "console_scripts": list(target.console_scripts),
                "compatibility_replacement": target.compatibility_replacement,
                "compatibility_cli_warning": compatibility_cli_warning,
                "product_probe": (
                    _json_stdout(outcomes[product_probe_index])
                    if product_probe_index is not None
                    and len(outcomes) > product_probe_index
                    else {}
                ),
                "status": "passed" if passed else "failed",
                "commands": [_command_payload(outcome) for outcome in outcomes],
            }
        )

    family_status = next(
        result["status"]
        for result in results
        if result["target_id"] == "complete-family"
    )
    package_class_by_name = dict(support.package_classes)
    package_results = [
        {
            "package_id": name,
            "package_class": package_class_by_name[name],
            "status": (
                "passed"
                if family_status == "passed"
                and next(
                    result["status"]
                    for result in results
                    if result["target_id"] == name
                )
                == "passed"
                else "failed"
            ),
        }
        for name in sorted(package_class_by_name, key=canonicalize_name)
    ]
    if any(result["status"] == "failed" for result in package_results):
        failures.append("package-installation-closure")

    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.installation_matrix.v1",
        "source_commit": source_commit,
        "created_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not failures else "failed",
        "environment": {
            "platform": platform.platform(),
            "runner_python": platform.python_version(),
            "requested_python": python_version,
        },
        "wheel_count": len(records),
        "dependency_wheel_count": len(dependency_wheels),
        "individual_install_count": len(records),
        "family_install_count": 1,
        "constraint_file": constraints.relative_to(repo_root).as_posix(),
        "dependency_wheel_directory": dependency_wheel_dir.relative_to(
            repo_root
        ).as_posix(),
        "public_index_access": False,
        "lock_identity": _sha256(repo_root / "uv.lock"),
        "wheels": [
            {
                "distribution_name": record.distribution_name,
                "version": record.version,
                "filename": record.path.name,
                "sha256": record.sha256,
            }
            for record in records
        ],
        "dependency_wheels": list(dependency_wheels),
        "install_results": results,
        "package_results": package_results,
        "retained_failures": sorted(set(failures)),
        "limitations": [
            "cross-platform installation remains owned by the remote package matrix",
        ],
    }
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        raise InstallationMatrixError(
            f"one or more clean installation rows failed; inspect {output_path}"
        )
    return evidence


def _json_stdout(result: CommandResult) -> dict[str, object]:
    if result.exit_code != 0 or not result.stdout.strip():
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_identity(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise InstallationMatrixError("git executable not found")
    status = subprocess.run(
        [git, "status", "--porcelain=v1"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise InstallationMatrixError(status.stderr.strip() or "git status failed")
    if status.stdout.strip():
        raise InstallationMatrixError(
            "installation matrix requires a clean source checkout"
        )
    identity = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise InstallationMatrixError(identity.stderr.strip() or "git rev-parse failed")
    return identity.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install each repository wheel and the complete family in isolated "
            "environments without source-tree imports."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--dependency-wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument(
        "--python-version",
        default=f"{sys.version_info.major}.{sys.version_info.minor}",
    )
    parser.add_argument("--uv", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed clean-install verifier."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    uv = args.uv or (Path(value) if (value := shutil.which("uv")) else None)
    if uv is None:
        raise SystemExit("uv executable not found; provide --uv")
    try:
        run_installation_matrix(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            dependency_wheel_dir=args.dependency_wheel_dir,
            output_path=args.output,
            environment_root=args.environment_root,
            source_commit=_git_identity(repo_root),
            python_version=args.python_version,
            uv_executable=uv,
        )
    except InstallationMatrixError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
