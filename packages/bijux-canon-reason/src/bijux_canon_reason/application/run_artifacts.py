# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import time

from bijux_canon_reason import __version__ as package_version
from bijux_canon_reason.application.run_workflow import run_app
from bijux_canon_reason.core.fingerprints import fingerprint_obj, stable_id
from bijux_canon_reason.core.types import (
    Plan,
    ProblemSpec,
    RuntimeDescriptor,
    Trace,
    TraceEventKind,
    VerificationReport,
)
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.interfaces.serialization.json_file import write_json_file
from bijux_canon_reason.interfaces.serialization.trace_jsonl import (
    fingerprint_trace_file,
    write_trace_jsonl,
)
from bijux_canon_reason.traces.checksum import compute_invariant_checksum

SCHEMA_VERSION = 1
RUN_DISK_QUOTA_BYTES = int(os.getenv("RAR_RUN_DISK_QUOTA_BYTES", "0"))
RUN_TIME_BUDGET_SEC = float(os.getenv("RAR_RUN_TIME_BUDGET_SEC", "0"))
RUN_CPU_BUDGET_SEC = float(os.getenv("RAR_RUN_CPU_BUDGET_SEC", "0"))


def _default_corpus_fixture() -> Path:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / "tests" / "fixtures" / "corpus_small.jsonl"
        if candidate.exists():
            return candidate
    return module_path.parents[3] / "tests" / "fixtures" / "corpus_small.jsonl"


def _dir_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


@dataclass(frozen=True)
class RunInputs:
    spec: ProblemSpec
    preset: str
    seed: int


@dataclass(frozen=True)
class RunArtifacts:
    run_id: str
    run_dir: Path

    spec_path: Path
    plan_path: Path
    trace_path: Path
    verify_path: Path
    fingerprint_path: Path
    run_meta_path: Path
    manifest_path: Path

    plan: Plan
    trace: Trace
    verify_report: VerificationReport
    runtime_descriptor: RuntimeDescriptor


@dataclass(frozen=True)
class RunRuntimeConfig:
    needs_retrieval: bool
    corpus_path: Path | None
    chunk_chars: int
    overlap_chars: int
    k1: float
    b: float
    corpus_max_bytes: int | None


class RunBuilder:
    """
    Artifact contract (unchanged):
      artifacts/bijux-canon-reason/runs/<run_id>/
        spec.json
        plan.json
        trace.jsonl
        verify.json
        fingerprint.txt
        run_meta.json
        manifest.json
    """

    def build(self, inputs: RunInputs, artifacts_root: Path) -> RunArtifacts:
        start_time = time.time()
        start_cpu = time.process_time()
        spec_with_id = inputs.spec if inputs.spec.id else inputs.spec.with_content_id()
        runtime_config = _resolve_runtime_config(spec_with_id)
        rt = _build_runtime(
            seed=inputs.seed,
            artifacts_dir=None,
            config=runtime_config,
        )
        runtime_descriptor = rt.descriptor
        runtime_fp = fingerprint_obj(runtime_descriptor.model_dump(mode="json"))
        run_id = stable_id(
            "run",
            {
                "spec_id": spec_with_id.id,
                "preset": inputs.preset,
                "seed": inputs.seed,
                "runtime_fingerprint": runtime_fp,
            },
        )

        run_dir = artifacts_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        _enforce_disk_quota(run_dir.parent, message="disk quota exceeded before run")

        spec_path = run_dir / "spec.json"
        plan_path = run_dir / "plan.json"
        trace_path = run_dir / "trace.jsonl"
        verify_path = run_dir / "verify.json"
        fingerprint_path = run_dir / "fingerprint.txt"
        run_meta_path = run_dir / "run_meta.json"
        manifest_path = run_dir / "manifest.json"

        live_rt = _build_runtime(
            seed=inputs.seed,
            artifacts_dir=run_dir,
            config=runtime_config,
        )

        res = run_app(
            spec=spec_with_id,
            preset=inputs.preset,
            seed=inputs.seed,
            artifacts_dir=run_dir,
            runtime=live_rt,
        )
        plan = res.plan
        runtime_descriptor = res.runtime_descriptor
        trace_meta = dict(res.trace.metadata)
        trace_meta["runtime_fingerprint"] = runtime_fp
        checksum = compute_invariant_checksum(
            plan=plan, trace=res.trace, runtime_descriptor=runtime_descriptor
        )
        trace_meta["invariant_checksum"] = checksum
        trace = res.trace.model_copy(update={"metadata": trace_meta}).with_content_id()
        verify_report = res.verify_report

        write_json_file(spec_path, spec_with_id.model_dump(mode="json"))
        write_json_file(plan_path, plan.model_dump(mode="json"))
        write_trace_jsonl(trace, trace_path)
        write_json_file(verify_path, verify_report.model_dump(mode="json"))

        fp = fingerprint_trace_file(trace_path)
        fingerprint_path.write_text(fp + "\n", encoding="utf-8")

        write_json_file(
            run_meta_path,
            {
                "run_id": run_id,
                "spec_id": spec_with_id.id,
                "plan_id": plan.id,
                "trace_id": trace.id,
                "preset": inputs.preset,
                "seed": inputs.seed,
                "runtime": {
                    "kind": runtime_descriptor.kind,
                    "mode": runtime_descriptor.mode,
                },
                "runtime_descriptor": runtime_descriptor.model_dump(mode="json"),
                "runtime_fingerprint": runtime_fp,
                "invariant_checksum": checksum,
                "schema_version": SCHEMA_VERSION,
                "producer_version": package_version,
            },
        )
        write_json_file(
            manifest_path,
            _build_manifest(
                run_dir=run_dir,
                trace=trace,
                core_files=[
                    spec_path,
                    plan_path,
                    trace_path,
                    verify_path,
                    fingerprint_path,
                    run_meta_path,
                ],
            ),
        )

        _enforce_disk_quota(run_dir, message="disk quota exceeded after run")
        _enforce_time_budget(start_time)
        _enforce_cpu_budget(start_cpu)

        return RunArtifacts(
            run_id=run_id,
            run_dir=run_dir,
            spec_path=spec_path,
            plan_path=plan_path,
            trace_path=trace_path,
            verify_path=verify_path,
            fingerprint_path=fingerprint_path,
            run_meta_path=run_meta_path,
            manifest_path=manifest_path,
            plan=plan,
            trace=trace,
            verify_report=verify_report,
            runtime_descriptor=runtime_descriptor,
        )


def _resolve_runtime_config(spec: ProblemSpec) -> RunRuntimeConfig:
    constraints = spec.constraints or {}
    needs_retrieval = bool(constraints.get("needs_retrieval"))
    default_corpus = _default_corpus_fixture()
    corpus_path = constraints.get("corpus_path")
    use_corpus: Path | None = None
    if isinstance(corpus_path, str) and corpus_path.strip():
        use_corpus = Path(corpus_path)
    elif needs_retrieval and default_corpus.exists():
        use_corpus = default_corpus

    return RunRuntimeConfig(
        needs_retrieval=needs_retrieval,
        corpus_path=use_corpus,
        chunk_chars=_coerce_int_constraint(constraints.get("chunk_chars"), default=800),
        overlap_chars=_coerce_int_constraint(
            constraints.get("overlap_chars"), default=120
        ),
        k1=_coerce_float_constraint(constraints.get("bm25_k1"), default=1.2),
        b=_coerce_float_constraint(constraints.get("bm25_b"), default=0.75),
        corpus_max_bytes=int(os.getenv("RAR_RETRIEVAL_CORPUS_MAX_BYTES", "0")) or None,
    )


def _build_runtime(
    *, seed: int, artifacts_dir: Path | None, config: RunRuntimeConfig
) -> Runtime:
    if config.needs_retrieval and config.corpus_path is not None:
        return Runtime.local_bm25(
            seed=seed,
            corpus_path=config.corpus_path,
            artifacts_dir=artifacts_dir,
            chunk_chars=config.chunk_chars,
            overlap_chars=config.overlap_chars,
            k1=config.k1,
            b=config.b,
            corpus_max_bytes=config.corpus_max_bytes,
        )
    return Runtime.fake(seed=seed, artifacts_dir=artifacts_dir)


def _coerce_int_constraint(value: object, *, default: int) -> int:
    if isinstance(value, (int, float, str)):
        return int(value)
    return default


def _coerce_float_constraint(value: object, *, default: float) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    return default


def _build_manifest(
    *,
    run_dir: Path,
    trace: Trace,
    core_files: list[Path],
) -> dict[str, str]:
    manifest: dict[str, str] = {}

    for event in trace.events:
        if event.kind != TraceEventKind.evidence_registered:
            continue
        rel = event.evidence.content_path
        if not rel:
            raise ValueError(
                "Evidence missing content_path (artifact contract violation)"
            )
        abs_path = run_dir / rel
        if not abs_path.exists():
            raise FileNotFoundError(f"Missing evidence file: {rel}")
        got = _hash_file(abs_path)
        if got != event.evidence.sha256:
            raise ValueError(f"Evidence sha256 mismatch for {rel}")
        manifest[rel] = got

    prov_root = run_dir / "provenance"
    if prov_root.exists():
        for path in sorted(prov_root.rglob("*")):
            if path.is_file():
                manifest[path.relative_to(run_dir).as_posix()] = _hash_file(path)

    for path in core_files:
        if path.exists():
            manifest[path.relative_to(run_dir).as_posix()] = _hash_file(path)

    return dict(sorted(manifest.items()))


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _enforce_disk_quota(root: Path, *, message: str) -> None:
    if RUN_DISK_QUOTA_BYTES <= 0:
        return
    if _dir_size(root) > RUN_DISK_QUOTA_BYTES:
        raise RuntimeError(message)


def _enforce_time_budget(start_time: float) -> None:
    if RUN_TIME_BUDGET_SEC <= 0:
        return
    if time.time() - start_time > RUN_TIME_BUDGET_SEC:
        raise RuntimeError("run exceeded time budget")


def _enforce_cpu_budget(start_cpu: float) -> None:
    if RUN_CPU_BUDGET_SEC <= 0:
        return
    if time.process_time() - start_cpu > RUN_CPU_BUDGET_SEC:
        raise RuntimeError("run exceeded CPU budget")
