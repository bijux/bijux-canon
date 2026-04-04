"""Contradiction detection helpers for flow verification."""

from __future__ import annotations

from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.ontology.ids import RuleID


def detect_contradictions(
    bundles: list[ReasoningBundle],
) -> tuple[RuleID, ...]:
    """Detect contradiction-related rule violations across reasoning bundles."""
    statements, negatives, circular = collect_statement_facts(bundles)
    violations: list[RuleID] = []
    append_direct_contradiction(violations, statements, negatives)
    append_weakened_restatement(violations, statements)
    if circular:
        violations.append(RuleID("circular_justification"))
    return tuple(dict.fromkeys(violations))


def normalize_statement(statement: str) -> str:
    """Normalize a claim statement for contradiction comparison."""
    return " ".join(statement.lower().strip().split())


def collect_statement_facts(
    bundles: list[ReasoningBundle],
) -> tuple[dict[str, list[float]], set[str], bool]:
    """Collect normalized statements, negative claims, and circularity flags."""
    statements: dict[str, list[float]] = {}
    negatives: set[str] = set()
    circular = False
    for bundle in bundles:
        for claim in bundle.claims:
            normalized = normalize_statement(claim.statement)
            if normalized.startswith("not "):
                negatives.add(normalized.removeprefix("not ").strip())
            statements.setdefault(normalized, []).append(claim.confidence)
            if str(claim.claim_id) in normalized:
                circular = True
    return statements, negatives, circular


def append_direct_contradiction(
    violations: list[RuleID],
    statements: dict[str, list[float]],
    negatives: set[str],
) -> None:
    """Append a direct contradiction violation when present."""
    for statement in statements:
        base = statement.removeprefix("not ").strip()
        if base in negatives and statement != f"not {base}":
            violations.append(RuleID("direct_contradiction"))
            return


def append_weakened_restatement(
    violations: list[RuleID],
    statements: dict[str, list[float]],
) -> None:
    """Append a weakened restatement violation when confidence regresses."""
    for confidences in statements.values():
        if len(confidences) > 1 and any(
            conf < max(confidences) for conf in confidences
        ):
            violations.append(RuleID("weakened_restatement"))
            return


__all__ = ["detect_contradictions"]
