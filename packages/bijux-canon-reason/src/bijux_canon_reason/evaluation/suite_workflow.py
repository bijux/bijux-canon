# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Suite workflow helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from bijux_canon_reason.application.run_artifacts import (
    RunArtifacts,
    RunBuilder,
    RunInputs,
)
from bijux_canon_reason.core.types import (
    Claim,
    ClaimEmittedEvent,
    EvidenceRef,
    EvidenceRegisteredEvent,
    ProblemSpec,
    StepFinishedEvent,
    SupportKind,
)
from bijux_canon_reason.verification.types import Severity


@dataclass(frozen=True)
class EvalResult:
    """Represents eval result."""

    suite: str
    total: int
    passed: int
    failed: int
    failures: list[dict[str, object]] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        """Convert to JSON."""
        return {
            "suite": self.suite,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "failures": list(self.failures),
        }


@dataclass(frozen=True)
class EvalCaseMetrics:
    """Represents eval case metrics."""

    run_dir: str
    spec_path: str
    evidence_count: int
    claims: int
    claims_with_exact_support: int
    exact_support_rate: float
    support_links_per_supported_claim: float
    insufficient: bool
    verification_failures: list[str]
    failure_taxonomy: dict[str, int]
    severity_counts: dict[str, int]
    verification_checks_failed: int
    claims_failed: int

    def to_json(self) -> dict[str, object]:
        """Convert to JSON."""
        return {
            "run_dir": self.run_dir,
            "spec_path": self.spec_path,
            "evidence_count": self.evidence_count,
            "claims": self.claims,
            "claims_with_exact_support": self.claims_with_exact_support,
            "exact_support_rate": self.exact_support_rate,
            "support_links_per_supported_claim": self.support_links_per_supported_claim,
            "insufficient": self.insufficient,
            "verification_failures": list(self.verification_failures),
            "failure_taxonomy": dict(self.failure_taxonomy),
            "severity_counts": dict(self.severity_counts),
            "verification_checks_failed": self.verification_checks_failed,
            "claims_failed": self.claims_failed,
        }


@dataclass(frozen=True)
class EvalSummaryMetrics:
    """Represents eval summary metrics."""

    exact_support_rate: float
    support_links_per_supported_claim: float
    insufficiency_rate: float
    failure_taxonomy: dict[str, int]

    def to_json(self) -> dict[str, object]:
        """Convert to JSON."""
        return {
            "exact_support_rate": self.exact_support_rate,
            "support_links_per_supported_claim": self.support_links_per_supported_claim,
            "insufficiency_rate": self.insufficiency_rate,
            "failure_taxonomy": dict(self.failure_taxonomy),
        }


def _default_suite_root() -> Path:
    """Locate bundled or caller-provided evaluation suites."""
    cwd_candidates = (
        Path.cwd() / "tooling" / "evaluation_suites",
        Path.cwd() / "benchmarks" / "suites",
    )
    for candidate in cwd_candidates:
        if candidate.exists():
            return candidate

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        for candidate in (
            parent / "tooling" / "evaluation_suites",
            parent / "benchmarks" / "suites",
        ):
            if candidate.exists():
                return candidate
    return module_path.parents[3] / "tooling" / "evaluation_suites"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Read JSONL."""
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            payload = line.strip()
            if not payload:
                continue
            rows.append(json.loads(payload))
    return rows


def _exact_evidence_support_count(
    *, run_dir: Path, evidence_by_id: dict[str, EvidenceRef], claim: Claim
) -> int | None:
    """Return the support count only when every support resolves exactly."""
    if not claim.supports:
        return None
    for support in claim.supports:
        if support.kind is not SupportKind.evidence:
            return None
        evidence = evidence_by_id.get(support.ref_id)
        if evidence is None or not evidence.content_path:
            return None
        try:
            content = (run_dir / evidence.content_path).read_bytes()
        except OSError:
            return None
        if hashlib.sha256(content).hexdigest() != evidence.sha256:
            return None
        start, end = support.span
        if start < 0 or end <= start or end > len(content):
            return None
        exact = content[start:end]
        if hashlib.sha256(exact).hexdigest() != support.snippet_sha256:
            return None
        try:
            exact_text = exact.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if exact_text not in claim.statement:
            return None
    return len(claim.supports)


def _case_metrics(arts: RunArtifacts) -> EvalCaseMetrics:
    """Handle case metrics."""
    trace = arts.trace
    verify_report = arts.verify_report

    evidence_by_id = {
        event.evidence.id: event.evidence
        for event in trace.events
        if isinstance(event, EvidenceRegisteredEvent)
    }
    evidence_count = len(evidence_by_id)
    claims = [
        event.claim for event in trace.events if isinstance(event, ClaimEmittedEvent)
    ]
    exact_support_counts = [
        support_count
        for claim in claims
        if (
            support_count := _exact_evidence_support_count(
                run_dir=arts.run_dir,
                evidence_by_id=evidence_by_id,
                claim=claim,
            )
        )
        is not None
    ]
    exact_support_rate = len(exact_support_counts) / len(claims) if claims else 0.0
    support_links_per_supported_claim = (
        sum(exact_support_counts) / len(exact_support_counts)
        if exact_support_counts
        else 0.0
    )
    insufficient = any(
        event.output.type == "insufficient_evidence"
        for event in trace.events
        if isinstance(event, StepFinishedEvent)
    )
    taxonomy: dict[str, int] = {}
    for check in verify_report.checks:
        if not check.passed:
            taxonomy[check.name] = taxonomy.get(check.name, 0) + 1

    severity_counts: dict[str, int] = {}
    for failure in verify_report.failures:
        severity = str(getattr(failure, "severity", Severity.error))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return EvalCaseMetrics(
        run_dir=str(arts.run_dir),
        spec_path=str(arts.spec_path),
        evidence_count=evidence_count,
        claims=len(claims),
        claims_with_exact_support=len(exact_support_counts),
        exact_support_rate=exact_support_rate,
        support_links_per_supported_claim=support_links_per_supported_claim,
        insufficient=insufficient,
        verification_failures=[failure.message for failure in verify_report.failures],
        failure_taxonomy=taxonomy,
        severity_counts=severity_counts,
        verification_checks_failed=sum(
            1 for check in verify_report.checks if not check.passed
        ),
        claims_failed=sum(
            1
            for failure in verify_report.failures
            if "claim" in failure.message.lower()
        ),
    )


def suite_summary(results: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate metrics from individual eval case rows."""
    if not results:
        return {"count": 0, "insufficient_rate": 0.0, "failure_taxonomy": {}}

    metrics = _summary_metrics(results)
    return {
        "count": len(results),
        "insufficient_rate": metrics.insufficiency_rate,
        **metrics.to_json(),
    }


def run_eval_suite(
    *,
    suite: str,
    artifacts_dir: Path,
    preset: str = "default",
    seed: int = 0,
    suite_root: Path | None = None,
) -> tuple[EvalResult, Path]:
    """Run a pinned set of ProblemSpecs."""
    root = suite_root or _default_suite_root()
    suite_dir = root / suite
    problems_path = suite_dir / "problems.jsonl"
    if not problems_path.exists():
        raise FileNotFoundError(f"Missing suite problems: {problems_path}")

    cases = _read_jsonl(problems_path)
    builder = RunBuilder()

    failures: list[dict[str, object]] = []
    passed = 0
    metrics_rows: list[dict[str, object]] = []
    for idx, raw in enumerate(cases):
        spec = ProblemSpec.model_validate(raw)
        inputs = RunInputs(spec=spec, preset=preset, seed=seed)
        case_root = artifacts_dir / "eval" / suite / f"case_{idx:03d}"
        artifacts = builder.build(inputs=inputs, artifacts_root=case_root)
        metrics_rows.append({"case": idx, **_case_metrics(artifacts).to_json()})
        if artifacts.verify_report.failures:
            failures.append(
                {
                    "case": idx,
                    "spec_id": artifacts.spec_path.name,
                    "run_dir": str(artifacts.run_dir),
                    "n_failures": len(artifacts.verify_report.failures),
                    "failure_messages": [
                        failure.message for failure in artifacts.verify_report.failures
                    ],
                }
            )
            continue
        passed += 1

    result = EvalResult(
        suite=suite,
        total=len(cases),
        passed=passed,
        failed=len(cases) - passed,
        failures=failures,
    )

    eval_dir = artifacts_dir / "eval" / suite
    eval_dir.mkdir(parents=True, exist_ok=True)
    cases_path = eval_dir / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as fh:
        for row in metrics_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    summary_payload = {
        **result.to_json(),
        "metrics": _summary_metrics(metrics_rows).to_json(),
    }

    out_path = eval_dir / "summary.json"
    out_path.write_text(
        json.dumps(summary_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, out_path


def _average_metric(rows: list[dict[str, object]], key: str) -> float:
    """Handle average metric."""
    if not rows:
        return 0.0
    values = (_metric_value(row.get(key, 0.0)) for row in rows)
    return sum(values, start=0.0) / len(rows)


def _metric_value(value: object) -> float:
    """Coerce an admitted JSON metric to a finite numeric value."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _aggregate_taxonomy(rows: list[dict[str, object]]) -> dict[str, int]:
    """Handle aggregate taxonomy."""
    taxonomy: dict[str, int] = {}
    for row in rows:
        raw_taxonomy = row.get("failure_taxonomy", {})
        if not isinstance(raw_taxonomy, dict):
            continue
        for name, value in raw_taxonomy.items():
            taxonomy[str(name)] = taxonomy.get(str(name), 0) + int(value)
    return taxonomy


def _insufficiency_rate(rows: list[dict[str, object]]) -> float:
    """Handle insufficiency rate."""
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("insufficient")) / len(rows)


def _summary_metrics(rows: list[dict[str, object]]) -> EvalSummaryMetrics:
    """Handle summary metrics."""
    return EvalSummaryMetrics(
        exact_support_rate=_average_metric(rows, "exact_support_rate"),
        support_links_per_supported_claim=_average_metric(
            rows, "support_links_per_supported_claim"
        ),
        insufficiency_rate=_insufficiency_rate(rows),
        failure_taxonomy=_aggregate_taxonomy(rows),
    )
