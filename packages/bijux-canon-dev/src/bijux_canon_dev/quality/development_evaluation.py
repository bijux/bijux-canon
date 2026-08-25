"""Consolidate installed development evaluation without accepting supplied answers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from typing import Mapping, Sequence, cast

from bijux_canon_dev.quality.evaluation_evidence_book import (
    EvaluationEvidenceBookGenerator,
    EvidenceBookAggregate,
    EvidenceBookCaseResult,
    EvidenceBookIdentities,
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID = re.compile(r"^run_v1_[0-9a-f]{64}$")
_ATTEMPT_ID = re.compile(r"^attempt_v1_[0-9a-f]{64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_RETRIEVAL_FLOORS = {
    "recall-at-5": 0.90,
    "mrr-at-10": 0.85,
    "ndcg-at-10": 0.85,
}
_SEMANTIC_DIMENSIONS = (
    "citation-quality",
    "claim-faithfulness",
    "qualifier-retention",
    "conflict-retention",
    "research-utility",
)


class DevelopmentEvaluationError(ValueError):
    """Development evidence is incomplete, inconsistent, or truth-derived."""


def build_development_evaluation(
    *,
    source_commit: str,
    cases: Sequence[Mapping[str, object]],
    retrieval: Mapping[str, object],
    outputs: Sequence[Mapping[str, object]],
    research: Mapping[str, object],
    output_directory: Path,
    command: str,
) -> dict[str, object]:
    """Build one evidence book from persisted installed-product observations."""

    if _COMMIT.fullmatch(source_commit) is None:
        raise DevelopmentEvaluationError("source commit must be a full Git SHA")
    selected = _development_cases(cases)
    _validate_retrieval_identity(retrieval)
    retrieval_by_query = _retrieval_cases(retrieval)
    observations_by_query = _retrieval_observations(retrieval)
    outputs_by_case = _system_outputs(outputs)
    case_ids = {str(item["case_id"]) for item in selected}
    query_ids = {str(item["question_id"]) for item in selected}
    if set(outputs_by_case) != case_ids:
        raise DevelopmentEvaluationError(
            "persisted system outputs do not cover the development population"
        )
    if set(retrieval_by_query) != query_ids or set(observations_by_query) != query_ids:
        raise DevelopmentEvaluationError(
            "persisted retrieval runs do not cover the development population"
        )
    _validate_research(research, case_ids)

    rows: list[dict[str, object]] = []
    book_cases: list[EvidenceBookCaseResult] = []
    for case in selected:
        case_id = str(case["case_id"])
        query_id = str(case["question_id"])
        truth = _mapping(case.get("truth"), f"{case_id} truth")
        output = outputs_by_case[case_id]
        retrieval_case = retrieval_by_query[query_id]
        retrieval_observation = observations_by_query[query_id]
        _validate_ranking_binding(retrieval_case, retrieval_observation)
        disposition_match = _disposition_matches(truth, output)
        citation_count = len(_sequence(output.get("citations"), "output citations"))
        claim_rows = _sequence(output.get("claims"), "output claims")
        claim_count = len(claim_rows)
        qualified_count = sum(
            isinstance(item, Mapping) and item.get("disposition") == "qualified"
            for item in claim_rows
        )
        metrics = {
            "retrieval.recall-at-5": _number(
                retrieval_case.get("recall_at_5"), "retrieval recall"
            ),
            "retrieval.mrr-at-10": _number(
                retrieval_case.get("reciprocal_rank_at_10"), "retrieval MRR"
            ),
            "retrieval.ndcg-at-10": _number(
                retrieval_case.get("ndcg_at_10"), "retrieval nDCG"
            ),
            "citation.runtime-resolution": 1.0,
            "abstention.disposition-match": float(disposition_match),
            "completion.product-success-rate": 1.0,
        }
        research_result: dict[str, object] = {"status": "not-applicable"}
        if research.get("case_id") == case_id:
            usage = _mapping(research.get("budget_usage"), "research budget usage")
            limits = _mapping(research.get("budget_limits"), "research budget limits")
            within_budget = all(
                _number(usage.get(name), f"research budget usage {name}")
                <= _number(limit, f"research budget limit {name}")
                for name, limit in limits.items()
            )
            research_result = {
                "attempt_id": research["attempt_id"],
                "budget_within_limits": within_budget,
                "run_id": research["run_id"],
                "status": "pending-independent-review",
                "terminal_outcome": research.get("terminal_outcome"),
                "trace_artifact_id": research.get("trace_artifact_id"),
            }
        row: dict[str, object] = {
            "answer": {
                "attempt_id": output["runtime_attempt_id"],
                "output_id": output["output_id"],
                "run_id": output["runtime_run_id"],
                "trace_identity_sha256": output["trace_identity_sha256"],
            },
            "case_id": case_id,
            "query_id": query_id,
            "retrieval": {
                "attempt_id": retrieval_observation["attempt_id"],
                "metrics": {
                    key.removeprefix("retrieval."): value
                    for key, value in metrics.items()
                    if key.startswith("retrieval.")
                },
                "run_id": retrieval_observation["run_id"],
                "status": "evaluated",
            },
            "citation": {
                "produced_count": citation_count,
                "runtime_resolution_ratio": 1.0,
                "semantic_status": "pending-independent-review",
            },
            "claim": {
                "produced_count": claim_count,
                "status": "pending-independent-review",
            },
            "qualifier": {
                "produced_qualified_count": qualified_count,
                "status": "pending-independent-review",
            },
            "conflict": {"status": "pending-independent-review"},
            "abstention": {
                "expected": bool(truth.get("abstention_expected")),
                "matched": disposition_match,
                "observed_disposition": output.get("disposition"),
                "status": "evaluated",
            },
            "budget": research_result,
            "research_utility": {
                "status": (
                    "pending-independent-review"
                    if research.get("case_id") == case_id
                    else "not-applicable"
                )
            },
        }
        rows.append(row)
        book_cases.append(
            EvidenceBookCaseResult(
                case_id=case_id,
                passed=disposition_match,
                metrics=metrics,
                errors=(
                    ()
                    if disposition_match
                    else ("observed disposition differs from development truth",)
                ),
            )
        )

    aggregates = _aggregates(tuple(book_cases), retrieval)
    identities = EvidenceBookIdentities(
        source_sha256=_sha256(source_commit),
        data_sha256=_sha256(
            {
                "cases": selected,
                "outputs": list(outputs),
                "research": research,
                "retrieval_evidence_sha256": retrieval["evidence_sha256"],
            }
        ),
        model_sha256=_sha256(retrieval.get("model_lock_artifact_ids")),
        config_sha256=_sha256(retrieval.get("configuration_ids")),
    )
    generator = EvaluationEvidenceBookGenerator()
    book = generator.build(
        source_commit=source_commit,
        current_commit=source_commit,
        identities=identities,
        cases=tuple(book_cases),
        aggregates=aggregates,
        limitations=(
            "Development metrics do not estimate held-out generalization.",
            "Claim, qualifier, conflict, citation-quality, and research-utility scores remain unavailable until independent output review and adjudication are supplied.",
            "The bounded research utility population currently contains one development case.",
        ),
        commands=(command,),
    )
    book_paths = generator.write(book, output_directory / "evidence-book")
    macro_values = _macro_values(retrieval)
    research_budget_rows = tuple(
        _mapping(item["budget"], "case research budget")
        for item in rows
        if _mapping(item["budget"], "case research budget").get("status")
        != "not-applicable"
    )
    report: dict[str, object] = {
        "schema_version": "bijux.canon.development-evaluation.v1",
        "source_commit": source_commit,
        "identities": {
            "config_sha256": identities.config_sha256,
            "data_sha256": identities.data_sha256,
            "model_sha256": identities.model_sha256,
            "source_sha256": identities.source_sha256,
        },
        "case_count": len(rows),
        "cases": rows,
        "macro": {
            "retrieval": {
                metric_id: {
                    "floor": _RETRIEVAL_FLOORS[metric_id],
                    "passed": value >= _RETRIEVAL_FLOORS[metric_id],
                    "value": value,
                }
                for metric_id, value in macro_values.items()
            },
            "citation": {
                "runtime_resolution_ratio": 1.0,
                "semantic_status": "pending-independent-review",
            },
            "claim": {"status": "pending-independent-review"},
            "qualifier": {"status": "pending-independent-review"},
            "conflict": {"status": "pending-independent-review"},
            "abstention": {
                "disposition_match_rate": sum(
                    cast(bool, _mapping(item["abstention"], "abstention")["matched"])
                    for item in rows
                )
                / len(rows),
                "status": "evaluated",
            },
            "budget": {
                "case_count": len(research_budget_rows),
                "within_limits": all(
                    item.get("budget_within_limits") is True
                    for item in research_budget_rows
                ),
            },
            "research_utility": {"status": "pending-independent-review"},
        },
        "retrieval_gate_passed": all(
            macro_values[key] >= floor for key, floor in _RETRIEVAL_FLOORS.items()
        ),
        "release_readiness": "blocked-independent-review",
        "pending_dimensions": list(_SEMANTIC_DIMENSIONS),
        "evidence_book": {
            "artifact_id": book.artifact_id,
            "paths": [str(path.relative_to(output_directory)) for path in book_paths],
        },
        "system_output_may_define_truth": False,
    }
    report["artifact_id"] = "sha256:" + _sha256(report)
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "development-evaluation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _development_cases(
    cases: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    forbidden = {"hits", "ranked_hits", "retrieved_qrel_ids"}
    if any(forbidden.intersection(item) for item in cases):
        raise DevelopmentEvaluationError(
            "evaluation truth must not contain supplied retrieval rankings"
        )
    selected = tuple(
        sorted(
            (item for item in cases if item.get("split") == "development"),
            key=lambda item: str(item.get("case_id")),
        )
    )
    if not selected or any(
        item.get("system_output_consulted") is not False
        or item.get("system_output_may_define_truth") is not False
        for item in selected
    ):
        raise DevelopmentEvaluationError(
            "development truth must be source-first and independent of system output"
        )
    identities = {(item.get("case_id"), item.get("question_id")) for item in selected}
    if len(identities) != len(selected) or any(
        not isinstance(case_id, str) or not isinstance(query_id, str)
        for case_id, query_id in identities
    ):
        raise DevelopmentEvaluationError("development identities must be unique")
    return selected


def _validate_retrieval_identity(retrieval: Mapping[str, object]) -> None:
    if retrieval.get("schema_version") != (
        "bijux.canon.index.public-retrieval-evaluation.v2"
    ):
        raise DevelopmentEvaluationError(
            "development evaluation requires the installed public retrieval report"
        )
    evidence = retrieval.get("evidence_sha256")
    payload = {key: value for key, value in retrieval.items() if key != "evidence_sha256"}
    if not isinstance(evidence, str) or evidence != _sha256(payload):
        raise DevelopmentEvaluationError("retrieval evidence identity mismatch")


def _retrieval_cases(
    retrieval: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    macro = _mapping(retrieval.get("macro"), "retrieval macro")
    rows = _mapping_sequence(macro.get("queries"), "retrieval macro queries")
    result = {str(item.get("query_id")): item for item in rows}
    if len(result) != len(rows) or "None" in result:
        raise DevelopmentEvaluationError("retrieval metric query identities are invalid")
    return result


def _retrieval_observations(
    retrieval: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    rows = _mapping_sequence(retrieval.get("observations"), "retrieval observations")
    result: dict[str, Mapping[str, object]] = {}
    for item in rows:
        query_id = item.get("query_id")
        if not isinstance(query_id, str) or query_id in result:
            raise DevelopmentEvaluationError(
                "retrieval observation identities are invalid"
            )
        if (
            item.get("status") != "success"
            or _RUN_ID.fullmatch(str(item.get("run_id"))) is None
            or _ATTEMPT_ID.fullmatch(str(item.get("attempt_id"))) is None
        ):
            raise DevelopmentEvaluationError(
                "retrieval observations must come from successful persisted runs"
            )
        result[query_id] = item
    return result


def _system_outputs(
    outputs: Sequence[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for item in outputs:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or case_id in result:
            raise DevelopmentEvaluationError("system output identities are invalid")
        if (
            item.get("schema_version") != "bijux.canon.evaluation.system-output.v1"
            or item.get("system_output_may_define_truth") is not False
            or _RUN_ID.fullmatch(str(item.get("runtime_run_id"))) is None
            or _ATTEMPT_ID.fullmatch(str(item.get("runtime_attempt_id"))) is None
            or _ARTIFACT_ID.fullmatch(str(item.get("output_id"))) is None
            or _SHA256.fullmatch(str(item.get("trace_identity_sha256"))) is None
        ):
            raise DevelopmentEvaluationError(
                "system outputs must retain persisted run and trace lineage"
            )
        result[case_id] = item
    return result


def _validate_research(research: Mapping[str, object], case_ids: set[str]) -> None:
    if (
        research.get("case_id") not in case_ids
        or research.get("system_output_may_define_truth") is not False
        or _RUN_ID.fullmatch(str(research.get("run_id"))) is None
        or _ATTEMPT_ID.fullmatch(str(research.get("attempt_id"))) is None
        or _ARTIFACT_ID.fullmatch(str(research.get("trace_artifact_id"))) is None
    ):
        raise DevelopmentEvaluationError(
            "research evidence must retain persisted run and trace lineage"
        )


def _validate_ranking_binding(
    metrics: Mapping[str, object], observation: Mapping[str, object]
) -> None:
    metric_hits = _sequence(metrics.get("ordered_evidence_ids"), "metric ranking")
    raw_hits = _mapping_sequence(observation.get("hits"), "observed retrieval hits")
    observed_hits = [item.get("chunk_id") for item in raw_hits]
    if metric_hits != observed_hits[: len(metric_hits)]:
        raise DevelopmentEvaluationError(
            "scored ranking differs from the persisted retrieval observation"
        )


def _disposition_matches(
    truth: Mapping[str, object], output: Mapping[str, object]
) -> bool:
    expected = truth.get("expected_disposition")
    observed = output.get("disposition")
    allowed = {
        "answer": {"answered"},
        "qualified-answer": {"answered", "partially_abstained"},
        "clarification-required": {"abstained"},
        "abstain": {"abstained"},
    }
    return isinstance(expected, str) and observed in allowed.get(expected, set())


def _macro_values(retrieval: Mapping[str, object]) -> dict[str, float]:
    macro = _mapping(retrieval.get("macro"), "retrieval macro")
    rows = _mapping_sequence(macro.get("metrics"), "retrieval macro metrics")
    result = {
        str(item.get("metric_id")): _number(item.get("value"), "macro metric")
        for item in rows
    }
    if set(result) != set(_RETRIEVAL_FLOORS):
        raise DevelopmentEvaluationError("retrieval macro metric set is incomplete")
    return result


def _aggregates(
    cases: tuple[EvidenceBookCaseResult, ...],
    retrieval: Mapping[str, object],
) -> tuple[EvidenceBookAggregate, ...]:
    case_ids = tuple(item.case_id for item in cases)
    macro = _mapping(retrieval.get("macro"), "retrieval macro")
    raw_metrics = {
        str(item.get("metric_id")): item
        for item in _mapping_sequence(macro.get("metrics"), "retrieval macro metrics")
    }
    definitions = (
        ("retrieval.recall-at-5", "recall-at-5"),
        ("retrieval.mrr-at-10", "mrr-at-10"),
        ("retrieval.ndcg-at-10", "ndcg-at-10"),
        ("citation.runtime-resolution", None),
        ("abstention.disposition-match", None),
        ("completion.product-success-rate", None),
    )
    results: list[EvidenceBookAggregate] = []
    for metric_id, public_id in definitions:
        values = tuple(float(item.metrics[metric_id]) for item in cases)
        numerator = sum(values)
        value = numerator / len(values)
        if public_id is None:
            lower = upper = value
            method = "complete observed development population"
        else:
            public = _mapping(raw_metrics.get(public_id), f"{public_id} macro")
            interval = _mapping(public.get("confidence_interval"), "confidence interval")
            lower = _number(interval.get("lower"), "confidence lower")
            upper = _number(interval.get("upper"), "confidence upper")
            method = str(interval.get("method"))
            if not math.isclose(value, _number(public.get("value"), "macro value")):
                raise DevelopmentEvaluationError(
                    f"per-case and macro retrieval arithmetic differ: {public_id}"
                )
        results.append(
            EvidenceBookAggregate(
                metric_id=metric_id,
                definition_version=1,
                aggregation="macro-mean",
                population_unit="development question",
                semantic_denominator="all executed development questions",
                case_ids=case_ids,
                numerator=numerator,
                denominator=float(len(values)),
                value=value,
                confidence_lower=lower,
                confidence_upper=upper,
                confidence_method=method,
                population_standard_deviation=statistics.pstdev(values),
                worst_case_ids=tuple(
                    item.case_id
                    for item in cases
                    if item.metrics[metric_id] == min(values)
                ),
                baseline_value=None,
            )
        )
    return tuple(results)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DevelopmentEvaluationError(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise DevelopmentEvaluationError(f"{label} must be a list")
    return value


def _mapping_sequence(value: object, label: str) -> list[Mapping[str, object]]:
    rows = _sequence(value, label)
    if any(not isinstance(item, Mapping) for item in rows):
        raise DevelopmentEvaluationError(f"{label} must contain objects")
    return [cast(Mapping[str, object], item) for item in rows]


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DevelopmentEvaluationError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise DevelopmentEvaluationError(f"{label} must be finite")
    return number


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def _jsonl(path: Path) -> list[Mapping[str, object]]:
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DevelopmentEvaluationError(f"cannot read JSONL: {path}") from error
    return [_mapping(item, str(path)) for item in rows]


def main() -> None:
    """Run the installed development evidence consolidator."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--retrieval-report", type=Path, required=True)
    parser.add_argument("--system-outputs", type=Path, required=True)
    parser.add_argument("--research-report", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    command = " ".join(
        (
            "bijux-canon-development-evaluation",
            "--cases",
            str(args.cases),
            "--retrieval-report",
            str(args.retrieval_report),
            "--system-outputs",
            str(args.system_outputs),
            "--research-report",
            str(args.research_report),
            "--source-commit",
            args.source_commit,
            "--output-directory",
            str(args.output_directory),
        )
    )
    try:
        report = build_development_evaluation(
            source_commit=args.source_commit,
            cases=_jsonl(args.cases),
            retrieval=_mapping(
                json.loads(args.retrieval_report.read_text(encoding="utf-8")),
                "retrieval report",
            ),
            outputs=_jsonl(args.system_outputs),
            research=_mapping(
                json.loads(args.research_report.read_text(encoding="utf-8")),
                "research report",
            ),
            output_directory=args.output_directory,
            command=command,
        )
    except (ValueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"development evaluation failed: {error}") from error
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "DevelopmentEvaluationError",
    "build_development_evaluation",
    "main",
]
