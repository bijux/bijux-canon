"""Verify that wheel extras install and unlock their advertised capabilities."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import cast
import zipfile

from packaging.markers import Marker, default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from bijux_canon_dev.release.installation_matrix import (
    InstallationMatrixError,
    _dependency_wheels,
)
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


class ExtrasMatrixError(RuntimeError):
    """An advertised extra is empty, unproven, or cannot be installed."""


@dataclass(frozen=True)
class ExtraTarget:
    """One distribution extra and the capability imports that prove it."""

    distribution_name: str
    extra: str
    requirements: tuple[str, ...]
    capability_modules: tuple[str, ...]

    @property
    def target_id(self) -> str:
        """Return a stable identifier for the isolated install row."""
        return f"{canonicalize_name(self.distribution_name)}[{self.extra}]"


CAPABILITY_MODULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("bijux-canon-agent", "api"): ("fastapi",),
    ("bijux-canon-agent", "dev"): ("pytest", "ruff"),
    ("bijux-canon-agent", "doc"): ("sphinx",),
    ("bijux-canon-agent", "document-readers"): (
        "PIL",
        "docx",
        "fitz",
        "pandas",
        "pdfminer",
        "pypdf",
        "pytesseract",
    ),
    ("bijux-canon-agent", "env"): ("dotenv",),
    ("bijux-canon-agent", "extra"): (
        "PIL",
        "docx",
        "fitz",
        "pandas",
        "pdfminer",
        "pypdf",
        "pytesseract",
    ),
    ("bijux-canon-agent", "profiling"): ("memory_profiler", "psutil"),
    ("bijux-canon-dev", "dev"): ("mkdocs", "mypy", "pytest", "ruff"),
    ("bijux-canon-index", "api"): ("fastapi", "schemathesis", "uvicorn"),
    ("bijux-canon-index", "config"): ("yaml",),
    ("bijux-canon-index", "dev"): ("mypy", "pytest", "ruff"),
    ("bijux-canon-index", "docs"): ("mkdocs",),
    ("bijux-canon-index", "embeddings"): (
        "numpy",
        "sentence_transformers",
        "torch",
    ),
    ("bijux-canon-index", "local-cpu"): (
        "faiss",
        "numpy",
        "sentence_transformers",
        "torch",
    ),
    ("bijux-canon-index", "nd"): ("hnswlib",),
    ("bijux-canon-index", "vdb"): ("faiss", "numpy", "qdrant_client"),
    ("bijux-canon-ingest", "dev"): ("pytest", "ruff"),
    ("bijux-canon-ingest", "docs"): ("mkdocs",),
    ("bijux-canon-reason", "api"): ("fastapi", "schemathesis", "uvicorn"),
    ("bijux-canon-reason", "bench"): ("pytest_benchmark",),
    ("bijux-canon-reason", "dev"): ("pytest", "ruff"),
    ("bijux-canon-runtime", "api"): ("fastapi", "starlette", "uvicorn"),
    ("bijux-canon-runtime", "dev"): ("pytest", "ruff"),
    ("bijux-canon-runtime", "local-cpu"): (
        "faiss",
        "numpy",
        "sentence_transformers",
        "torch",
    ),
}

CPU_PROFILE_TARGETS = {
    "bijux-canon-index[local-cpu]",
    "bijux-canon-runtime[local-cpu]",
}

_MARKER_PLATFORMS = (
    ("darwin", "posix", "Darwin"),
    ("freebsd", "posix", "FreeBSD"),
    ("linux", "posix", "Linux"),
    ("win32", "nt", "Windows"),
)
_MARKER_MACHINES = ("AMD64", "aarch64", "arm64", "x86_64")
_MARKER_PYTHONS = ("3.11", "3.12", "3.13", "3.14")


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise ExtrasMatrixError("extras commands require an absolute executable")
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
        raise ExtrasMatrixError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def _python_path(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _wheel_extra_requirements(path: Path) -> dict[str, tuple[str, ...]]:
    with zipfile.ZipFile(path) as archive:
        metadata_names = sorted(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        if len(metadata_names) != 1:
            raise ExtrasMatrixError(
                f"wheel must contain exactly one METADATA file: {path.name}"
            )
        message = BytesParser().parsebytes(archive.read(metadata_names[0]))
    extras = tuple(
        sorted(
            {
                canonicalize_name(value)
                for value in message.get_all("Provides-Extra", [])
            }
        )
    )
    requirements = tuple(
        Requirement(value) for value in message.get_all("Requires-Dist", [])
    )
    result: dict[str, tuple[str, ...]] = {
        extra: tuple(
            sorted(
                str(requirement)
                for requirement in requirements
                if requirement.marker is not None
                and _marker_can_target_extra(requirement.marker, extra)
            )
        )
        for extra in extras
    }
    empty = [extra for extra, values in result.items() if not values]
    if empty:
        raise ExtrasMatrixError(
            f"wheel {path.name} advertises empty extras: {', '.join(empty)}"
        )
    return result


def _marker_can_target_extra(marker: Marker, extra: str) -> bool:
    """Return whether a wheel marker can apply on a supported environment."""

    baseline = {key: str(value) for key, value in default_environment().items()}
    for sys_platform, os_name, platform_system in _MARKER_PLATFORMS:
        for platform_machine in _MARKER_MACHINES:
            for python_version in _MARKER_PYTHONS:
                environment: dict[str, str] = {
                    **baseline,
                    "extra": extra,
                    "os_name": os_name,
                    "platform_machine": platform_machine,
                    "platform_system": platform_system,
                    "python_full_version": f"{python_version}.0",
                    "python_version": python_version,
                    "sys_platform": sys_platform,
                }
                if marker.evaluate(environment):
                    return True
    return False


def _source_extra_requirements(policy: PackagePolicy) -> dict[str, tuple[str, ...]]:
    return {
        extra: tuple(sorted(values)) for extra, values in policy.optional_dependencies
    }


def _normalized_requirements(
    requirements: Sequence[str],
) -> tuple[tuple[str, tuple[str, ...], str, str | None], ...]:
    normalized = []
    for value in requirements:
        requirement = Requirement(value)
        normalized.append(
            (
                canonicalize_name(requirement.name),
                tuple(sorted(canonicalize_name(extra) for extra in requirement.extras)),
                str(requirement.specifier),
                requirement.url,
            )
        )
    return tuple(sorted(normalized))


def _targets(
    records: Sequence[WheelRecord],
    policies: Sequence[PackagePolicy],
    capability_modules: Mapping[tuple[str, str], Sequence[str]],
) -> tuple[ExtraTarget, ...]:
    records_by_name = {
        canonicalize_name(record.distribution_name): record for record in records
    }
    declared: dict[tuple[str, str], tuple[str, ...]] = {}
    for policy in policies:
        if policy.package_key is None:
            continue
        distribution_name = canonicalize_name(policy.distribution_name)
        source_extras = _source_extra_requirements(policy)
        wheel_extras = _wheel_extra_requirements(
            records_by_name[distribution_name].path
        )
        if set(source_extras) != set(wheel_extras):
            raise ExtrasMatrixError(
                f"source and wheel extras disagree for {distribution_name}"
            )
        for extra, requirements in source_extras.items():
            if not requirements:
                raise ExtrasMatrixError(
                    f"source advertises empty extra {distribution_name}[{extra}]"
                )
            if _normalized_requirements(requirements) != _normalized_requirements(
                wheel_extras[extra]
            ):
                raise ExtrasMatrixError(
                    f"source and wheel requirements disagree for "
                    f"{distribution_name}[{extra}]"
                )
            declared[(distribution_name, extra)] = wheel_extras[extra]

    mapped: dict[tuple[str, str], tuple[str, ...]] = {
        (str(canonicalize_name(distribution)), str(canonicalize_name(extra))): tuple(
            modules
        )
        for (distribution, extra), modules in capability_modules.items()
    }
    if set(declared) != set(mapped):
        missing = sorted(set(declared) - set(mapped))
        stale = sorted(set(mapped) - set(declared))
        raise ExtrasMatrixError(
            f"capability mapping mismatch; missing={missing}, stale={stale}"
        )
    if any(not modules for modules in mapped.values()):
        raise ExtrasMatrixError("every advertised extra needs a capability import")
    return tuple(
        ExtraTarget(distribution, extra, declared[(distribution, extra)], mapped[key])
        for key in sorted(declared)
        for distribution, extra in (key,)
    )


def _constraint_file(records: Sequence[WheelRecord], environment_root: Path) -> Path:
    path = environment_root.parent / "candidate-constraints.txt"
    path.write_text(
        "".join(
            f"{record.distribution_name}=={record.version}\n" for record in records
        ),
        encoding="utf-8",
    )
    return path


def _generic_probe(target: ExtraTarget, *, source_roots: Sequence[Path]) -> str:
    dependency_names = tuple(
        sorted({Requirement(value).name for value in target.requirements})
    )
    return "\n".join(
        [
            "import importlib",
            "import importlib.metadata as metadata",
            "import json",
            "from pathlib import Path",
            "import sysconfig",
            f"dependency_names = {dependency_names!r}",
            f"modules = {target.capability_modules!r}",
            f"source_roots = tuple(Path(value).resolve() for value in {tuple(map(str, source_roots))!r})",
            "purelib = Path(sysconfig.get_paths()['purelib']).resolve()",
            "installed_dependencies = {}",
            "for name in dependency_names:",
            "    installed_dependencies[name] = metadata.version(name)",
            "module_origins = {}",
            "for name in modules:",
            "    module = importlib.import_module(name)",
            "    origin_value = getattr(module, '__file__', None)",
            "    assert origin_value, name",
            "    origin = Path(origin_value).resolve()",
            "    assert origin.is_relative_to(purelib), (name, origin, purelib)",
            "    assert not any(origin.is_relative_to(root) for root in source_roots), (name, origin, source_roots)",
            "    module_origins[name] = str(origin)",
            "print(json.dumps({'installed_dependencies': installed_dependencies, 'module_origins': module_origins}, sort_keys=True))",
        ]
    )


def _reader_probe(repo_root: Path) -> str:
    inputs = {
        "pdf": str(
            repo_root / "examples/document-formats/corpus/parser-pdf-digital-real.pdf"
        ),
        "docx": str(
            repo_root / "examples/document-formats/corpus/parser-docx-real.docx"
        ),
        "ocr_image": str(
            repo_root / "examples/document-formats/corpus/parser-ocr-required-real.jpg"
        ),
    }
    return "\n".join(
        [
            "import asyncio",
            "import hashlib",
            "import json",
            "from pathlib import Path",
            "from bijux_canon_agent.agents.file_reader.capabilities.universal_file_reader_core import UniversalFileReader",
            f"inputs = {inputs!r}",
            "async def exercise():",
            "    reader = UniversalFileReader({'ocr_enabled': True})",
            "    results = {}",
            "    for name, value in inputs.items():",
            "        result = await reader.read_file(Path(value))",
            "        assert 'error' not in result, (name, result.get('error'))",
            "        profile = result.get('processing_profile')",
            "        assert isinstance(profile, dict), (name, profile)",
            "        processing_method = profile.get('processing_method')",
            "        assert isinstance(processing_method, str) and processing_method, (name, profile)",
            "        text = str(result.get('text', ''))",
            "        if name != 'ocr_image':",
            "            assert text.strip(), name",
            "        if name == 'ocr_image':",
            "            assert processing_method == 'ocr_extraction', processing_method",
            "            assert any('OCR used' in str(warning) for warning in result.get('warnings', [])), result.get('warnings')",
            "        results[name] = {'source_sha256': hashlib.sha256(Path(value).read_bytes()).hexdigest(), 'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'text_characters': len(text), 'processing_method': processing_method, 'ocr_used': result.get('ocr_used'), 'warnings': result.get('warnings', [])} ",
            "    capabilities = reader.get_supported_formats()['dependencies']",
            "    assert all(capabilities.values()), capabilities",
            "    return {'inputs': results, 'capabilities': capabilities}",
            "print(json.dumps(asyncio.run(exercise()), sort_keys=True))",
        ]
    )


def _reason_probe() -> str:
    return "\n".join(
        [
            "import json",
            "from bijux_canon_reason.grounding.structured_provider import OpenAICompatibleStructuredSynthesizer, StructuredProviderConfiguration",
            "resolver_calls = 0",
            "def resolve_credential():",
            "    global resolver_calls",
            "    resolver_calls += 1",
            "    return 'unused'",
            "provider = OpenAICompatibleStructuredSynthesizer(StructuredProviderConfiguration(base_url='http://127.0.0.1:9', model='extras-proof'), credential_resolver=resolve_credential)",
            "assert resolver_calls == 0",
            "transport = provider._transport.__class__.__name__",
            "assert transport == 'UrllibJsonTransport'",
            "print(json.dumps({'credential_resolver_calls_during_construction': resolver_calls, 'transport': transport}, sort_keys=True))",
        ]
    )


def _cpu_profile_probe(*, runtime: bool) -> str:
    runtime_lines = (
        [
            "from bijux_canon_runtime.api.v2 import create_app",
            "assert '/api/v2/live' in create_app().openapi()['paths']",
        ]
        if runtime
        else []
    )
    return "\n".join(
        [
            "import importlib.metadata as metadata",
            "import json",
            "import torch",
            "import faiss",
            "import numpy as np",
            "assert torch.version.cuda is None, torch.version.cuda",
            "installed = sorted({(item.metadata.get('Name') or '').lower() for item in metadata.distributions()})",
            "gpu = [name for name in installed if name.startswith('nvidia-') or name in {'tensorflow-gpu', 'torch-directml'}]",
            "assert not gpu, gpu",
            "index = faiss.IndexFlatIP(2)",
            "vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype='float32')",
            "index.add(vectors)",
            "scores, identifiers = index.search(vectors[:1], 1)",
            "assert identifiers.tolist() == [[0]], identifiers",
            "assert scores.tolist() == [[1.0]], scores",
            *runtime_lines,
            "print(json.dumps({'cuda_runtime': torch.version.cuda, 'faiss_result': identifiers.tolist(), 'gpu_distributions': gpu, 'runtime_api': "
            + str(runtime)
            + "}, sort_keys=True))",
        ]
    )


def _runtime_api_probe() -> str:
    return "\n".join(
        [
            "import json",
            "from bijux_canon_runtime.api.v2 import create_app",
            "schema = create_app().openapi()",
            "assert '/api/v2/live' in schema['paths']",
            "assert '/api/v2/ready' in schema['paths']",
            "print(json.dumps({'openapi': schema['openapi'], 'paths': ['/api/v2/live', '/api/v2/ready']}, sort_keys=True))",
        ]
    )


def _json_stdout(result: CommandResult) -> dict[str, object]:
    if result.exit_code != 0 or not result.stdout.strip():
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def run_extras_matrix(
    *,
    repo_root: Path,
    wheel_dir: Path,
    dependency_wheel_dir: Path,
    output_path: Path,
    environment_root: Path,
    source_commit: str,
    python_version: str,
    uv_executable: Path,
    capability_modules: Mapping[tuple[str, str], Sequence[str]] = CAPABILITY_MODULES,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Install and probe every advertised extra in an isolated environment."""
    repo_root = repo_root.resolve()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ExtrasMatrixError("source commit must be a lowercase full Git SHA")
    wheel_dir = _artifact_path(wheel_dir, repo_root, label="wheel directory")
    dependency_wheel_dir = _artifact_path(
        dependency_wheel_dir, repo_root, label="dependency wheel directory"
    )
    output_path = _artifact_path(output_path, repo_root, label="output path")
    environment_root = _artifact_path(
        environment_root, repo_root, label="environment root"
    )
    support = inspect_workspace(repo_root)
    records = inspect_wheels(wheel_dir, support.distribution_names)
    try:
        dependency_wheels = _dependency_wheels(
            dependency_wheel_dir,
            candidate_names=tuple(record.distribution_name for record in records),
        )
    except InstallationMatrixError as exc:
        raise ExtrasMatrixError(str(exc)) from exc
    policies = inspect_workspace_policy(repo_root)
    targets = _targets(records, policies, capability_modules)
    records_by_name = {
        canonicalize_name(record.distribution_name): record for record in records
    }
    source_roots = tuple(
        (policy.pyproject_path.parent / "src").resolve()
        for policy in policies
        if policy.package_key is not None
    )
    environment_root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    constraints = _constraint_file(records, environment_root)
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
        target_root = environment_root / target.target_id.replace("[", "-").rstrip("]")
        python = _python_path(target_root)
        wheel = records_by_name[canonicalize_name(target.distribution_name)].path
        commands = [
            [
                str(uv_executable.absolute()),
                "venv",
                str(target_root),
                "--python",
                python_version,
                "--clear",
            ],
        ]
        commands.extend(
            [
                [
                    str(uv_executable.absolute()),
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "--constraint",
                    str(constraints),
                    "--no-index",
                    "--find-links",
                    str(wheel_dir),
                    "--find-links",
                    str(dependency_wheel_dir),
                    f"{wheel}[{target.extra}]",
                ],
                [
                    str(uv_executable.absolute()),
                    "pip",
                    "check",
                    "--python",
                    str(python),
                ],
                [
                    str(python),
                    "-I",
                    "-c",
                    _generic_probe(target, source_roots=source_roots),
                ],
            ],
        )
        generic_probe_index = len(commands) - 1
        capability_probe_index: int | None = None
        if target.target_id == "bijux-canon-agent[document-readers]":
            commands.append([str(python), "-I", "-c", _reader_probe(repo_root)])
            capability_probe_index = len(commands) - 1
        if target.target_id == "bijux-canon-reason[api]":
            commands.append([str(python), "-I", "-c", _reason_probe()])
            capability_probe_index = len(commands) - 1
        if target.target_id in CPU_PROFILE_TARGETS:
            commands.append(
                [
                    str(python),
                    "-I",
                    "-c",
                    _cpu_profile_probe(
                        runtime=target.target_id == "bijux-canon-runtime[local-cpu]"
                    ),
                ]
            )
            capability_probe_index = len(commands) - 1
        if target.target_id == "bijux-canon-runtime[api]":
            commands.append([str(python), "-I", "-c", _runtime_api_probe()])
            capability_probe_index = len(commands) - 1

        outcomes: list[CommandResult] = []
        for command in commands:
            outcome = runner(command, environment_root, environment)
            outcomes.append(outcome)
            if outcome.exit_code != 0:
                failures.append(f"{target.target_id}:{len(outcomes)}")
                break
        passed = len(outcomes) == len(commands) and all(
            outcome.exit_code == 0 for outcome in outcomes
        )
        results.append(
            {
                "target_id": target.target_id,
                "distribution_name": target.distribution_name,
                "extra": target.extra,
                "requirements": list(target.requirements),
                "capability_modules": list(target.capability_modules),
                "status": "passed" if passed else "failed",
                "generic_probe": (
                    _json_stdout(outcomes[generic_probe_index])
                    if len(outcomes) > generic_probe_index
                    else {}
                ),
                "capability_probe": (
                    _json_stdout(outcomes[capability_probe_index])
                    if capability_probe_index is not None
                    and len(outcomes) > capability_probe_index
                    else {}
                ),
                "commands": [_command_payload(outcome) for outcome in outcomes],
            }
        )

    package_class_by_name = dict(support.package_classes)
    rows_by_distribution: dict[str, list[dict[str, object]]] = {}
    for row in results:
        rows_by_distribution.setdefault(cast(str, row["distribution_name"]), []).append(
            row
        )
    package_results = [
        {
            "package_id": name,
            "package_class": package_class_by_name[name],
            "advertised_extra_count": len(rows_by_distribution.get(name, [])),
            "status": (
                "passed"
                if all(
                    row["status"] == "passed"
                    for row in rows_by_distribution.get(name, [])
                )
                else "failed"
            ),
        }
        for name in sorted(package_class_by_name, key=canonicalize_name)
    ]
    if any(row["status"] == "failed" for row in package_results):
        failures.append("package-extra-capabilities")

    agent_extras = {
        row.extra: row.requirements
        for row in targets
        if row.distribution_name == "bijux-canon-agent"
    }
    agent_extra = agent_extras.get("extra")
    document_readers = agent_extras.get("document-readers")
    if agent_extras and (
        agent_extra is None
        or document_readers is None
        or _normalized_requirements(agent_extra)
        != _normalized_requirements(document_readers)
    ):
        failures.append("agent-document-reader-alias")
    reason_policy = next(
        (
            policy
            for policy in policies
            if canonicalize_name(policy.distribution_name) == "bijux-canon-reason"
        ),
        None,
    )
    if reason_policy is not None and (
        "llm" in dict(reason_policy.optional_dependencies)
        or any(
            canonicalize_name(Requirement(value).name) == "openai"
            for value in reason_policy.dependencies
        )
    ):
        failures.append("reason-provider-dependency-policy")

    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.extras_matrix.v1",
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
        "extra_count": len(targets),
        "constraint_file": constraints.relative_to(repo_root).as_posix(),
        "dependency_wheel_directory": dependency_wheel_dir.relative_to(
            repo_root
        ).as_posix(),
        "public_index_access": False,
        "lock_identity": _sha256(repo_root / "uv.lock"),
        "dependency_wheels": list(dependency_wheels),
        "extra_results": results,
        "package_results": package_results,
        "retained_failures": sorted(set(failures)),
        "limitations": [
            "cross-platform extras remain owned by remote package verification",
            "OCR capability proves the installed reader path without requiring nonempty OCR text",
        ],
    }
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        raise ExtrasMatrixError(
            f"one or more extras rows failed; inspect {output_path}"
        )
    return evidence


def _git_identity(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ExtrasMatrixError("git executable not found")
    status = subprocess.run(
        [git, "status", "--porcelain=v1"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise ExtrasMatrixError(status.stderr.strip() or "git status failed")
    if status.stdout.strip():
        raise ExtrasMatrixError("extras matrix requires a clean source checkout")
    identity = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise ExtrasMatrixError(identity.stderr.strip() or "git rev-parse failed")
    return identity.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install every wheel extra in isolation and exercise its capability."
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
    """Run the installed extras and capability verifier."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    uv = args.uv or (Path(value) if (value := shutil.which("uv")) else None)
    if uv is None:
        raise SystemExit("uv executable not found; provide --uv")
    try:
        run_extras_matrix(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            dependency_wheel_dir=args.dependency_wheel_dir,
            output_path=args.output,
            environment_root=args.environment_root,
            source_commit=_git_identity(repo_root),
            python_version=args.python_version,
            uv_executable=uv,
        )
    except ExtrasMatrixError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
