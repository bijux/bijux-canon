"""Deterministic generator for current evaluation evidence books."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class EvidenceBookIdentities:
    """Exact immutable inputs governing one evaluation run."""

    source_sha256: str
    data_sha256: str
    model_sha256: str
    config_sha256: str

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            _require_sha256(value)


@dataclass(frozen=True, slots=True)
class EvidenceBookCaseResult:
    """One retained case result, including failures and exclusions."""

    case_id: str
    passed: bool
    metrics: Mapping[str, float]
    errors: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or not self.metrics:
            raise ValueError("evidence-book case identity and metrics are required")
        if self.passed and self.errors:
            raise ValueError("passing evidence-book cases cannot retain errors")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


@dataclass(frozen=True, slots=True)
class EvidenceBookAggregate:
    """Aggregate arithmetic, interval, and baseline for one metric."""

    metric_id: str
    numerator: float
    denominator: float
    value: float
    confidence_lower: float
    confidence_upper: float
    confidence_method: str
    baseline_value: float | None

    def __post_init__(self) -> None:
        if not self.metric_id or self.denominator <= 0:
            raise ValueError("aggregate identity and denominator are required")
        if self.value != self.numerator / self.denominator:
            raise ValueError("aggregate value does not match exact arithmetic")
        if not self.confidence_lower <= self.value <= self.confidence_upper:
            raise ValueError("aggregate value is outside its confidence interval")
        if not self.confidence_method.strip():
            raise ValueError("aggregate confidence method is required")


@dataclass(frozen=True, slots=True)
class EvaluationEvidenceBook:
    """Complete current-HEAD evaluation evidence ready for publication."""

    artifact_id: str
    source_commit: str
    identities: EvidenceBookIdentities
    cases: tuple[EvidenceBookCaseResult, ...]
    aggregates: tuple[EvidenceBookAggregate, ...]
    limitations: tuple[str, ...]
    commands: tuple[str, ...]

    def __post_init__(self) -> None:
        if len({item.case_id for item in self.cases}) != len(self.cases):
            raise ValueError("evidence-book case IDs must be unique")
        if len({item.metric_id for item in self.aggregates}) != len(self.aggregates):
            raise ValueError("evidence-book aggregate IDs must be unique")
        if not self.cases or not self.aggregates:
            raise ValueError("evidence book requires cases and aggregates")
        if not self.limitations or not all(item.strip() for item in self.limitations):
            raise ValueError("evidence book requires explicit limitations")
        if not self.commands or not all(item.strip() for item in self.commands):
            raise ValueError("evidence book requires reproducible commands")
        if self.artifact_id != _artifact_id(self.payload(include_artifact=False)):
            raise ValueError("evidence-book identity does not match")

    def payload(self, *, include_artifact: bool = True) -> dict[str, object]:
        """Return canonical JSON-ready content."""
        payload: dict[str, object] = {
            "schema_version": "bijux.canon.evaluation.evidence-book.v1",
            "source_commit": self.source_commit,
            "identities": asdict(self.identities),
            "cases": [
                {
                    "case_id": item.case_id,
                    "passed": item.passed,
                    "metrics": dict(item.metrics),
                    "errors": list(item.errors),
                    "exclusions": list(item.exclusions),
                }
                for item in self.cases
            ],
            "aggregates": [asdict(item) for item in self.aggregates],
            "limitations": list(self.limitations),
            "commands": list(self.commands),
        }
        if include_artifact:
            payload["artifact_id"] = self.artifact_id
        return payload


class EvaluationEvidenceBookGenerator:
    """Build and publish deterministic, disposable evidence output."""

    def build(
        self,
        *,
        source_commit: str,
        current_commit: str,
        identities: EvidenceBookIdentities,
        cases: tuple[EvidenceBookCaseResult, ...],
        aggregates: tuple[EvidenceBookAggregate, ...],
        limitations: tuple[str, ...],
        commands: tuple[str, ...],
    ) -> EvaluationEvidenceBook:
        """Build only from results bound to the current source commit."""
        if source_commit != current_commit:
            raise ValueError("evidence book source commit is stale")
        provisional = {
            "schema_version": "bijux.canon.evaluation.evidence-book.v1",
            "source_commit": source_commit,
            "identities": asdict(identities),
            "cases": [
                {
                    "case_id": item.case_id,
                    "passed": item.passed,
                    "metrics": dict(item.metrics),
                    "errors": list(item.errors),
                    "exclusions": list(item.exclusions),
                }
                for item in cases
            ],
            "aggregates": [asdict(item) for item in aggregates],
            "limitations": list(limitations),
            "commands": list(commands),
        }
        return EvaluationEvidenceBook(
            artifact_id=_artifact_id(provisional),
            source_commit=source_commit,
            identities=identities,
            cases=cases,
            aggregates=aggregates,
            limitations=limitations,
            commands=commands,
        )

    def write(self, book: EvaluationEvidenceBook, output_dir: Path) -> tuple[Path, ...]:
        """Regenerate the JSON index, readable summary, and per-case records."""
        output_dir.mkdir(parents=True, exist_ok=True)
        case_dir = output_dir / "cases"
        case_dir.mkdir(exist_ok=True)
        index = output_dir / "evidence-book.json"
        index.write_text(_json(book.payload()), encoding="utf-8")
        written = [index]
        for item in book.cases:
            path = case_dir / f"{item.case_id}.json"
            path.write_text(
                _json(
                    {
                        "case_id": item.case_id,
                        "passed": item.passed,
                        "metrics": dict(item.metrics),
                        "errors": list(item.errors),
                        "exclusions": list(item.exclusions),
                    }
                ),
                encoding="utf-8",
            )
            written.append(path)
        summary = output_dir / "README.md"
        summary.write_text(_markdown(book), encoding="utf-8")
        written.append(summary)
        return tuple(written)


def _markdown(book: EvaluationEvidenceBook) -> str:
    lines = [
        "# Evaluation evidence book",
        "",
        f"Source commit: `{book.source_commit}`",
        "",
        "| Metric | Value | 95% interval | Method | Baseline |",
        "|---|---:|---:|---|---:|",
    ]
    for item in book.aggregates:
        baseline = "n/a" if item.baseline_value is None else str(item.baseline_value)
        lines.append(
            f"| {item.metric_id} | {item.value} | "
            f"[{item.confidence_lower}, {item.confidence_upper}] | "
            f"{item.confidence_method} | {baseline} |"
        )
    lines.extend(("", "## Limitations", ""))
    lines.extend(f"- {item}" for item in book.limitations)
    lines.extend(("", "## Reproduction", ""))
    lines.extend(f"- `{item}`" for item in book.commands)
    return "\n".join(lines) + "\n"


def _artifact_id(payload: object) -> str:
    return "sha256:" + hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def _json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
        raise ValueError("evidence-book identities must be SHA-256 digests")


__all__ = [
    "EvaluationEvidenceBook",
    "EvaluationEvidenceBookGenerator",
    "EvidenceBookAggregate",
    "EvidenceBookCaseResult",
    "EvidenceBookIdentities",
]
