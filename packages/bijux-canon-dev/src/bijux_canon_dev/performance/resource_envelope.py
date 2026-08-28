"""Measure installed ancient-DNA workflows against declared resource ceilings."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any, cast


class ResourceEnvelopeError(RuntimeError):
    """Raised when a measurement is incomplete or exceeds its ceiling."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise ResourceEnvelopeError(message)


def _mapping(value: object, message: str) -> dict[str, Any]:
    _require(isinstance(value, dict), message)
    return cast(dict[str, Any], value)


def _directory_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def _paths_bytes(paths: Iterable[Path]) -> int:
    return sum(_directory_bytes(path) for path in paths)


def _load_workflow_summary(profile_root: Path) -> dict[str, Any]:
    path = profile_root / "evidence" / "summary.json"
    _require(path.is_file(), f"workflow summary is missing: {path}")
    return _mapping(
        json.loads(path.read_text()), f"workflow summary is invalid: {path}"
    )


def _index_bytes(
    *,
    workspace_roots: Sequence[Path],
    workflow_summary: Mapping[str, Any],
) -> int:
    index = _mapping(
        workflow_summary.get("index"), "workflow index identity is missing"
    )
    segments = index.get("segments")
    if isinstance(segments, list) and segments:
        segment_sizes: list[int] = []
        for position, value in enumerate(segments):
            segment = _mapping(value, f"workflow index segment {position} is invalid")
            size_value = segment.get("size_bytes")
            _require(
                isinstance(size_value, int)
                and not isinstance(size_value, bool)
                and size_value > 0,
                f"workflow index segment {position} omitted size_bytes",
            )
            segment_sizes.append(cast(int, size_value))
        return sum(segment_sizes)

    artifact_id = index.get("artifact_id")
    _require(
        isinstance(artifact_id, str) and artifact_id.startswith("sha256:"),
        "workflow index artifact identity is invalid",
    )
    digest = cast(str, artifact_id).removeprefix("sha256:")
    payloads = tuple(
        root / "cas" / "objects" / "sha256" / digest[:2] / digest / "payload"
        for root in workspace_roots
    )
    payload_sizes = {path.stat().st_size for path in payloads if path.is_file()}
    _require(payload_sizes, f"index payload is missing for {artifact_id}")
    _require(len(payload_sizes) == 1, f"index payload sizes disagree for {artifact_id}")
    return payload_sizes.pop()


def _exchange_duration(path: Path) -> float:
    exchange = _mapping(json.loads(path.read_text()), f"invalid exchange: {path}")
    value = exchange.get("duration_seconds")
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0,
        f"exchange omitted duration: {path}",
    )
    return float(cast(int | float, value))


def _sum_named(evidence: Path, names: Sequence[str]) -> float:
    paths = tuple(evidence / f"{name}.exchange.json" for name in names)
    for path in paths:
        _require(path.is_file(), f"required timing exchange is missing: {path.name}")
    return round(sum(_exchange_duration(path) for path in paths), 6)


def _sum_glob(evidence: Path, pattern: str) -> float:
    paths = tuple(sorted(evidence.glob(pattern)))
    _require(paths, f"timing exchange pattern matched nothing: {pattern}")
    return round(sum(_exchange_duration(path) for path in paths), 6)


def _profile_metrics(
    *,
    profile_id: str,
    profile_root: Path,
    measurement: Mapping[str, Any],
    startup: Mapping[str, Any],
) -> dict[str, Any]:
    evidence = profile_root / "evidence"
    workspace_roots = tuple(
        path for path in profile_root.glob("runtime-workspace*") if path.is_dir()
    )
    _require(workspace_roots, f"{profile_id} omitted its workspace")
    workflow_summary = _load_workflow_summary(profile_root)
    common = {
        "startup_seconds": float(startup["wall_seconds"]),
        "ingest_seconds": _sum_named(evidence, ("corpus-job",)),
        "inspection_seconds": _sum_glob(evidence, "*inspection.exchange.json"),
        "peak_rss_bytes": int(measurement["peak_rss_bytes"]),
        "profile_disk_bytes": _directory_bytes(profile_root),
        "workspace_disk_bytes": _paths_bytes(workspace_roots),
        "index_bytes": _index_bytes(
            workspace_roots=workspace_roots,
            workflow_summary=workflow_summary,
        ),
        "total_seconds": float(measurement["wall_seconds"]),
    }
    if profile_id == "offline-lexical":
        stages = {
            "index_seconds": _sum_named(evidence, ("lexical-index-job",)),
            "query_seconds": _sum_named(evidence, ("evidence-search-job",)),
            "answer_seconds": _sum_named(evidence, ("grounded-answer-job",)),
        }
    elif profile_id == "local-cpu-hybrid":
        stages = {
            "index_seconds": _sum_named(evidence, ("hybrid-index-job",)),
            "query_seconds": _sum_named(
                evidence, ("exact-search-job", "ann-search-job")
            ),
            "answer_seconds": _sum_glob(evidence, "rag-*-job.exchange.json"),
        }
    else:
        raise ResourceEnvelopeError(f"unsupported measured profile: {profile_id}")
    return {**common, **stages}


def _workflow_evidence(profile_root: Path, output_root: Path) -> dict[str, Any]:
    summary_path = profile_root / "evidence" / "summary.json"
    payload = summary_path.read_bytes()
    summary = _mapping(
        json.loads(payload), f"workflow summary is invalid: {summary_path}"
    )
    return {
        "installed_environment": _mapping(
            summary.get("installed_environment"),
            "workflow installed environment is missing",
        ),
        "model": summary.get("model"),
        "summary_path": summary_path.relative_to(output_root).as_posix(),
        "summary_sha256": sha256(payload).hexdigest(),
        "workload": {
            "corpus": _mapping(summary.get("corpus"), "workflow corpus is missing"),
            "index": _mapping(summary.get("index"), "workflow index is missing"),
        },
    }


def _evaluate(
    metrics: Mapping[str, Mapping[str, Any]],
    ceilings: Mapping[str, Any],
) -> list[dict[str, Any]]:
    declared = _mapping(ceilings.get("profiles"), "ceiling profiles are missing")
    observations: list[dict[str, Any]] = []
    for profile_id, profile_metrics in metrics.items():
        profile_ceilings = _mapping(
            declared.get(profile_id), f"ceilings are missing for {profile_id}"
        )
        for metric_id, ceiling in profile_ceilings.items():
            observed = profile_metrics.get(metric_id)
            _require(
                isinstance(observed, (int, float)) and not isinstance(observed, bool),
                f"measured metric is missing: {profile_id}.{metric_id}",
            )
            _require(
                isinstance(ceiling, (int, float)) and not isinstance(ceiling, bool),
                f"ceiling is invalid: {profile_id}.{metric_id}",
            )
            observations.append(
                {
                    "ceiling": ceiling,
                    "metric_id": metric_id,
                    "observed": observed,
                    "passed": observed <= ceiling,
                    "profile_id": profile_id,
                }
            )
    return observations


def _physical_memory_bytes() -> int | None:
    try:
        return int(os.sysconf("SC_PHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _environment() -> dict[str, Any]:
    return {
        "cpu_count": os.cpu_count(),
        "machine": platform.machine(),
        "operating_system": platform.platform(),
        "physical_memory_bytes": _physical_memory_bytes(),
        "processor": platform.processor() or None,
        "python": platform.python_version(),
    }


def _worker(command: Sequence[str], record_path: Path) -> int:
    try:
        import resource
    except ImportError as exc:  # pragma: no cover - benchmark targets POSIX hosts
        raise ResourceEnvelopeError(
            "peak RSS measurement requires the POSIX resource module"
        ) from exc
    started = perf_counter()
    completed = subprocess.run(  # noqa: S603 - explicit benchmark command
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    raw_peak = float(usage.ru_maxrss)
    peak_rss_bytes = int(raw_peak if sys.platform == "darwin" else raw_peak * 1024)
    record = {
        "command": list(command),
        "peak_rss_bytes": peak_rss_bytes,
        "returncode": completed.returncode,
        "stderr": completed.stderr,
        "stdout": completed.stdout,
        "wall_seconds": round(perf_counter() - started, 6),
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if completed.returncode == 0 else 1


def _measure(command: Sequence[str], record_path: Path) -> dict[str, Any]:
    completed = subprocess.run(  # noqa: S603 - isolated resource worker
        (
            sys.executable,
            "-m",
            "bijux_canon_dev.performance.resource_envelope",
            "_measure",
            str(record_path),
            *command,
        ),
        check=False,
    )
    _require(completed.returncode == 0, f"measured command failed: {record_path}")
    return _mapping(json.loads(record_path.read_text()), "measurement is invalid")


def _command_path(value: str, label: str) -> Path:
    import shutil

    resolved = Path(shutil.which(value) or value).resolve()
    _require(resolved.is_file(), f"{label} command not found: {value}")
    return resolved


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    repository = Path.cwd()
    example = repository / "examples" / "ancient-dna-research"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-command", default="bijux-canon-runtime")
    parser.add_argument("--index-command", default="bijux-canon-index")
    parser.add_argument(
        "--development-evaluation-command",
        default="bijux-canon-development-evaluation",
    )
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument(
        "--ceilings",
        type=Path,
        default=example / "resource-ceilings.json",
    )
    parser.add_argument("--example-directory", type=Path, default=example)
    return parser.parse_args(argv)


def _run(argv: Sequence[str] | None) -> int:
    arguments = _arguments(argv)
    output = arguments.output_directory.resolve()
    _require(not output.exists(), "output directory must be new")
    output.mkdir(parents=True)
    example = arguments.example_directory.resolve()
    runtime = _command_path(arguments.runtime_command, "Runtime")
    index = _command_path(arguments.index_command, "Index")
    development = _command_path(
        arguments.development_evaluation_command, "development evaluation"
    )
    model = arguments.model_directory.resolve()
    _require(model.is_dir(), "model directory is missing")
    ceilings = _mapping(
        json.loads(arguments.ceilings.resolve().read_text()), "ceilings are invalid"
    )

    startup: dict[str, dict[str, Any]] = {}
    measurements: dict[str, dict[str, Any]] = {}
    profile_commands = {
        "offline-lexical": (
            sys.executable,
            str(example / "offline_lexical_workflow.py"),
            "--runtime-command",
            str(runtime),
            "--workspace",
            str(output / "offline-lexical" / "runtime-workspace"),
            "--evidence-directory",
            str(output / "offline-lexical" / "evidence"),
        ),
        "local-cpu-hybrid": (
            sys.executable,
            str(example / "cpu_hybrid_workflow.py"),
            "--runtime-command",
            str(runtime),
            "--index-command",
            str(index),
            "--development-evaluation-command",
            str(development),
            "--source-commit",
            arguments.source_commit,
            "--model-directory",
            str(model),
            "--workspace",
            str(output / "local-cpu-hybrid" / "runtime-workspace"),
            "--evidence-directory",
            str(output / "local-cpu-hybrid" / "evidence"),
        ),
    }
    for profile_id, command in profile_commands.items():
        profile_root = output / profile_id
        profile_root.mkdir()
        startup[profile_id] = _measure(
            (str(runtime), "--help"), profile_root / "startup-measurement.json"
        )
        measurements[profile_id] = _measure(
            command, profile_root / "workflow-measurement.json"
        )

    metrics = {
        profile_id: _profile_metrics(
            profile_id=profile_id,
            profile_root=output / profile_id,
            measurement=measurements[profile_id],
            startup=startup[profile_id],
        )
        for profile_id in profile_commands
    }
    observations = _evaluate(metrics, ceilings)
    summary = {
        "ceilings": ceilings,
        "environment": _environment(),
        "measurements": metrics,
        "observations": observations,
        "result": "passed"
        if all(item["passed"] for item in observations)
        else "failed",
        "schema_version": "bijux.canon.resource_envelope.v1",
        "source_commit": arguments.source_commit,
        "workflow_evidence": {
            profile_id: _workflow_evidence(output / profile_id, output)
            for profile_id in profile_commands
        },
    }
    (output / "resource-envelope.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["result"] == "passed" else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the public benchmark or one isolated internal measurement worker."""
    values = tuple(sys.argv[1:] if argv is None else argv)
    if values and values[0] == "_measure":
        _require(len(values) >= 3, "measurement worker requires a record and command")
        return _worker(values[2:], Path(values[1]))
    try:
        return _run(values)
    except (OSError, ResourceEnvelopeError, json.JSONDecodeError) as error:
        print(f"resource envelope failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
