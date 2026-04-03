# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import time

from bijux_rar import __version__ as package_version
from bijux_rar.boundaries.serde.json_file import write_json_file
from bijux_rar.boundaries.serde.trace_jsonl import (
    fingerprint_trace_file,
    write_trace_jsonl,
)
from bijux_rar.core.fingerprints import fingerprint_obj, stable_id
from bijux_rar.core.rar_types import (
    Plan,
    ProblemSpec,
    RuntimeDescriptor,
    Trace,
    TraceEventKind,
    VerificationReport,
)
from bijux_rar.rar.app import run_app
from bijux_rar.rar.execution.runtime import Runtime
from bijux_rar.rar.traces.checksum import compute_invariant_checksum

SCHEMA_VERSION = 1
RUN_DISK_QUOTA_BYTES = int(os.getenv("RAR_RUN_DISK_QUOTA_BYTES", "0"))
RUN_TIME_BUDGET_SEC = float(os.getenv("RAR_RUN_TIME_BUDGET_SEC", "0"))
RUN_CPU_BUDGET_SEC = float(os.getenv("RAR_RUN_CPU_BUDGET_SEC", "0"))


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


class RunBuilder:
    """
    Artifact contract (unchanged):
      artifacts/runs/<run_id>/
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
        constraints = spec_with_id.constraints or {}
        needs_retrieval = bool(constraints.get("needs_retrieval"))
        corpus_path = constraints.get("corpus_path")
        k1 = 1.2
        raw_k1 = constraints.get("bm25_k1")
        if isinstance(raw_k1, (int, float, str)):
            k1 = float(raw_k1)
        b = 0.75
        raw_b = constraints.get("bm25_b")
        if isinstance(raw_b, (int, float, str)):
            b = float(raw_b)
        chunk_chars = 800
        raw_chunk = constraints.get("chunk_chars")
        if isinstance(raw_chunk, (int, float, str)):
            chunk_chars = int(raw_chunk)
        overlap_chars = 120
        raw_overlap = constraints.get("overlap_chars")
        if isinstance(raw_overlap, (int, float, str)):
            overlap_chars = int(raw_overlap)
        default_corpus = (
            Path(__file__).resolve().parents[4]
            / "tests"
            / "fixtures"
            / "corpus_small.jsonl"
        )
        use_corpus: Path | None = None
        if isinstance(corpus_path, str) and corpus_path.strip():
            use_corpus = Path(corpus_path)
        elif needs_retrieval and default_corpus.exists():
            use_corpus = default_corpus

        if needs_retrieval and use_corpus is not None:
            rt = Runtime.local_bm25(
                seed=inputs.seed,
                corpus_path=use_corpus,
                artifacts_dir=None,
                chunk_chars=chunk_chars,
                overlap_chars=overlap_chars,
                k1=k1,
                b=b,
                corpus_max_bytes=int(os.getenv("RAR_RETRIEVAL_CORPUS_MAX_BYTES", "0"))
                or None,
            )
        else:
            rt = Runtime.fake(seed=inputs.seed, artifacts_dir=None)
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
        if RUN_DISK_QUOTA_BYTES > 0:
            current = _dir_size(run_dir.parent)
            if current > RUN_DISK_QUOTA_BYTES:
                raise RuntimeError("disk quota exceeded before run")

        spec_path = run_dir / "spec.json"
        plan_path = run_dir / "plan.json"
        trace_path = run_dir / "trace.jsonl"
        verify_path = run_dir / "verify.json"
        fingerprint_path = run_dir / "fingerprint.txt"
        run_meta_path = run_dir / "run_meta.json"

        live_rt = (
            Runtime.local_bm25(
                seed=inputs.seed,
                corpus_path=use_corpus,
                artifacts_dir=run_dir,
                chunk_chars=chunk_chars,
                overlap_chars=overlap_chars,
                k1=k1,
                b=b,
                corpus_max_bytes=int(os.getenv("RAR_RETRIEVAL_CORPUS_MAX_BYTES", "0"))
                or None,
            )
            if needs_retrieval and use_corpus is not None
            else Runtime.fake(seed=inputs.seed, artifacts_dir=run_dir)
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

        # Evidence files are written by the executor under run_dir/evidence/*.txt
        # The manifest is a content-addressed summary for audit/release.
        manifest: dict[str, str] = {}
        evidence_root = run_dir / "evidence"
        if evidence_root.exists():
            for ev in trace.events:
                if ev.kind != TraceEventKind.evidence_registered:
                    continue
                rel = ev.evidence.content_path
                if not rel:
                    raise ValueError(
                        "Evidence missing content_path (artifact contract violation)"
                    )
                abs_path = run_dir / rel
                if not abs_path.exists():
                    raise FileNotFoundError(f"Missing evidence file: {rel}")
                got = hashlib.sha256(abs_path.read_bytes()).hexdigest()
                if got != ev.evidence.sha256:
                    raise ValueError(f"Evidence sha256 mismatch for {rel}")
                manifest[rel] = got
        # provenance files (corpus/index/chunks/retrieval_provenance.json) if present
        prov_root = run_dir / "provenance"
        if prov_root.exists():
            for p in sorted(prov_root.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(run_dir).as_posix()
                    manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

        # Pin core artifacts and provenance into manifest
        def _hash_file(p: Path) -> str:
            return hashlib.sha256(p.read_bytes()).hexdigest()

        core_files = [
            spec_path,
            plan_path,
            trace_path,
            verify_path,
            fingerprint_path,
            run_meta_path,
        ]
        for p in core_files:
            if p.exists():
                manifest[p.relative_to(run_dir).as_posix()] = _hash_file(p)

        provenance_files = [
            run_dir / "provenance" / "corpus.jsonl",
            run_dir / "provenance" / "index" / "bm25_index.json",
        ]
        for p in provenance_files:
            if p.exists():
                manifest[p.relative_to(run_dir).as_posix()] = _hash_file(p)

        manifest_path = run_dir / "manifest.json"
        write_json_file(manifest_path, dict(sorted(manifest.items())))

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

        if RUN_DISK_QUOTA_BYTES > 0:
            total_size = _dir_size(run_dir)
            if total_size > RUN_DISK_QUOTA_BYTES:
                raise RuntimeError("disk quota exceeded after run")

        if RUN_TIME_BUDGET_SEC > 0:
            elapsed = time.time() - start_time
            if elapsed > RUN_TIME_BUDGET_SEC:
                raise RuntimeError("run exceeded time budget")
        if RUN_CPU_BUDGET_SEC > 0:
            cpu_elapsed = time.process_time() - start_cpu
            if cpu_elapsed > RUN_CPU_BUDGET_SEC:
                raise RuntimeError("run exceeded CPU budget")

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
