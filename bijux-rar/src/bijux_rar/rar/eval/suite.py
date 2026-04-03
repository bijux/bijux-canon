# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.skeleton.run_builder import RunArtifacts, RunBuilder, RunInputs
from bijux_rar.rar.verification.types import Severity


class EvalResult(dict[str, object]):
    """Lightweight eval result container for easier JSON use with attribute access."""

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - simple passthrough
        if item in self:
            return self[item]
        raise AttributeError(item)

    @property
    def suite(self) -> str:
        return str(self.get("suite", ""))

    @property
    def total(self) -> int:
        val = self.get("total", 0)
        return int(val) if isinstance(val, (int, float, str)) else 0

    @property
    def passed(self) -> int:
        val = self.get("passed", 0)
        return int(val) if isinstance(val, (int, float, str)) else 0

    @property
    def failed(self) -> int:
        val = self.get("failed", 0)
        return int(val) if isinstance(val, (int, float, str)) else 0

    def to_json(self) -> dict[str, object]:
        return dict(self)


def _default_suite_root() -> Path:
    """Locate `eval/suites`.

    - repo checkout: CWD contains eval/suites
    - installed package: resolve relative to this file
    """
    cwd_candidate = Path.cwd() / "eval" / "suites"
    if cwd_candidate.exists():
        return cwd_candidate
    return Path(__file__).resolve().parents[4] / "eval" / "suites"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows


def _case_metrics(arts: RunArtifacts) -> dict[str, Any]:
    trace = arts.trace
    vr = arts.verify_report

    evidence_count = sum(1 for ev in trace.events if ev.kind == "evidence_registered")
    claims = [ev.claim for ev in trace.events if ev.kind == "claim_emitted"]
    claims_with_support = [
        c for c in claims if any(s.kind == "evidence" for s in c.supports)
    ]
    alignment_rate = len(claims_with_support) / len(claims) if claims else 1.0
    faithfulness = (
        sum(len(c.supports) for c in claims_with_support) / len(claims_with_support)
        if claims_with_support
        else 0.0
    )
    insuff = any(
        ev.output.type == "insufficient_evidence"
        for ev in trace.events
        if ev.kind == "step_finished"
    )
    # Proxy retrieval metrics: success if any evidence retrieved.
    recall_at_k = 1.0 if evidence_count > 0 else 0.0
    mrr = 1.0 if evidence_count > 0 else 0.0

    taxonomy: dict[str, int] = {}
    for chk in vr.checks:
        if not chk.passed:
            taxonomy[chk.name] = taxonomy.get(chk.name, 0) + 1
    failure_messages = [f.message for f in vr.failures]
    severity_counts: dict[str, int] = {}
    for f in vr.failures:
        severity_counts[str(getattr(f, "severity", Severity.error))] = (
            severity_counts.get(str(getattr(f, "severity", Severity.error)), 0) + 1
        )

    return {
        "run_dir": str(arts.run_dir),
        "spec_path": str(arts.spec_path),
        "evidence_count": evidence_count,
        "claims": len(claims),
        "claims_with_support": len(claims_with_support),
        "alignment_rate": alignment_rate,
        "faithfulness": faithfulness,
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "insufficient": insuff,
        "verification_failures": failure_messages,
        "failure_taxonomy": taxonomy,
        "severity_counts": severity_counts,
        "verification_checks_failed": sum(1 for c in vr.checks if not c.passed),
        "claims_failed": len([f for f in vr.failures if "claim" in f.message.lower()]),
    }


def suite_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics from individual eval case rows."""
    if not results:
        return {"count": 0, "insufficient_rate": 0.0, "failure_taxonomy": {}}

    count = len(results)
    insuff = sum(1 for r in results if r.get("insufficient"))
    taxonomy: dict[str, int] = {}
    for r in results:
        for name, val in r.get("failure_taxonomy", {}).items():
            taxonomy[name] = taxonomy.get(name, 0) + int(val)

    return {
        "count": count,
        "recall_at_k": sum(r.get("recall_at_k", 0.0) for r in results) / count,
        "mrr": sum(r.get("mrr", 0.0) for r in results) / count,
        "alignment_rate": sum(r.get("alignment_rate", 0.0) for r in results) / count,
        "faithfulness": sum(r.get("faithfulness", 0.0) for r in results) / count,
        "insufficient_rate": insuff / count,
        "failure_taxonomy": taxonomy,
    }


def run_eval_suite(
    *,
    suite: str,
    artifacts_dir: Path,
    preset: str = "default",
    seed: int = 0,
    suite_root: Path | None = None,
) -> tuple[EvalResult, Path]:
    """Run a pinned set of ProblemSpecs.

    Contract:
    - each case runs in its own run_dir
    - a case passes iff verification yields zero failures
    """
    root = suite_root or _default_suite_root()
    suite_dir = root / suite
    problems_path = suite_dir / "problems.jsonl"
    if not problems_path.exists():
        raise FileNotFoundError(f"Missing suite problems: {problems_path}")

    cases = _read_jsonl(problems_path)
    builder = RunBuilder()

    failures: list[dict[str, object]] = []
    passed = 0
    metrics_rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(cases):
        spec = ProblemSpec.model_validate(raw)
        inputs = RunInputs(spec=spec, preset=preset, seed=seed)
        case_root = artifacts_dir / "eval" / suite / f"case_{idx:03d}"
        arts: RunArtifacts = builder.build(inputs=inputs, artifacts_root=case_root)
        metrics_rows.append({"case": idx, **_case_metrics(arts)})
        if arts.verify_report.failures:
            failures.append(
                {
                    "case": idx,
                    "spec_id": arts.spec_path.name,
                    "run_dir": str(arts.run_dir),
                    "n_failures": len(arts.verify_report.failures),
                    "failure_messages": [
                        f.message for f in arts.verify_report.failures
                    ],
                }
            )
        else:
            passed += 1

    res = EvalResult(
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

    alignment_avg = (
        sum(r["alignment_rate"] for r in metrics_rows) / len(metrics_rows)
        if metrics_rows
        else 0.0
    )
    faithfulness_avg = (
        sum(r["faithfulness"] for r in metrics_rows) / len(metrics_rows)
        if metrics_rows
        else 0.0
    )
    recall_avg = (
        sum(r["recall_at_k"] for r in metrics_rows) / len(metrics_rows)
        if metrics_rows
        else 0.0
    )
    mrr_avg = (
        sum(r["mrr"] for r in metrics_rows) / len(metrics_rows) if metrics_rows else 0.0
    )
    insuff_rate = (
        sum(1 for r in metrics_rows if r["insufficient"]) / len(metrics_rows)
        if metrics_rows
        else 0.0
    )

    taxonomy: dict[str, int] = {}
    for r in metrics_rows:
        for name, count in r["failure_taxonomy"].items():
            taxonomy[name] = taxonomy.get(name, 0) + count

    summary_payload = {
        **res.to_json(),
        "metrics": {
            "recall_at_k": recall_avg,
            "mrr": mrr_avg,
            "alignment_rate": alignment_avg,
            "faithfulness": faithfulness_avg,
            "insufficiency_rate": insuff_rate,
            "failure_taxonomy": taxonomy,
        },
    }

    out_path = eval_dir / "summary.json"
    out_path.write_text(
        json.dumps(summary_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return res, out_path
