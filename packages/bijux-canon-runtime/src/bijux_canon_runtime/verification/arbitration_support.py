"""Arbitration helpers for verification orchestration."""

from __future__ import annotations

from collections import Counter

from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.model.verification.verification_rule import VerificationRule
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_policy,
)
from bijux_canon_runtime.ontology import (
    ArbitrationRule,
    VerificationRandomness,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, PolicyFingerprint


def arbitrate_results(
    results: list[VerificationResult], policy: VerificationPolicy
) -> VerificationArbitration:
    """Arbitrate verification results under the configured policy."""
    arbitration_policy = policy.arbitration_policy
    statuses = [result.status for result in results]
    randomness = max_result_randomness(results)
    decision = arbitration_decision(
        statuses, arbitration_policy.rule, arbitration_policy.quorum_threshold
    )
    if decision == "PASS" and randomness_exceeds(
        randomness, policy.randomness_tolerance
    ):
        decision = "ESCALATE"
    engine_ids = tuple(result.engine_id for result in results)
    engine_statuses = tuple(statuses)
    return VerificationArbitration(
        spec_version="v1",
        rule=arbitration_policy.rule,
        policy_fingerprint=PolicyFingerprint(fingerprint_policy(policy)),
        decision=decision,
        randomness=randomness,
        engine_ids=engine_ids,
        engine_statuses=engine_statuses,
        target_artifact_ids=target_artifact_ids(results),
    )


def arbitration_decision(
    statuses: list[str],
    rule: ArbitrationRule,
    quorum_threshold: int | None,
) -> str:
    """Resolve the final arbitration decision for a set of engine statuses."""
    if rule == ArbitrationRule.STRICT_FIRST_FAILURE:
        return strict_first_failure_decision(statuses)
    if rule == ArbitrationRule.UNANIMOUS:
        return unanimous_decision(statuses)
    if rule == ArbitrationRule.QUORUM:
        return quorum_decision(statuses, quorum_threshold)
    raise ValueError(f"unsupported arbitration rule: {rule}")


def strict_first_failure_decision(statuses: list[str]) -> str:
    """Return the first non-pass status, or PASS if all engines pass."""
    for status in statuses:
        if status != "PASS":
            return status
    return "PASS"


def unanimous_decision(statuses: list[str]) -> str:
    """Return the unanimous decision across all engine statuses."""
    if all(status == "PASS" for status in statuses):
        return "PASS"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    return "ESCALATE"


def quorum_decision(statuses: list[str], quorum_threshold: int | None) -> str:
    """Return the majority decision across engine statuses."""
    counts = Counter(statuses)
    threshold = quorum_threshold
    if threshold is None:
        threshold = len(statuses) // 2 + 1
    if counts["PASS"] >= threshold:
        return "PASS"
    if counts["FAIL"] >= threshold:
        return "FAIL"
    return "ESCALATE"


def target_artifact_ids(results: list[VerificationResult]) -> tuple[ArtifactID, ...]:
    """Flatten checked artifact ids across verification results."""
    target_ids: list[ArtifactID] = []
    for result in results:
        target_ids.extend(result.checked_artifact_ids)
    return tuple(target_ids)


def max_rule_randomness(
    rules: tuple[VerificationRule, ...],
) -> VerificationRandomness:
    """Return the highest randomness requirement across verification rules."""
    if not rules:
        return VerificationRandomness.DETERMINISTIC
    return max(
        (rule.randomness_requirement for rule in rules),
        key=randomness_rank,
    )


def max_result_randomness(
    results: list[VerificationResult],
) -> VerificationRandomness:
    """Return the highest observed randomness across verification results."""
    if not results:
        return VerificationRandomness.DETERMINISTIC
    return max((result.randomness for result in results), key=randomness_rank)


def randomness_rank(randomness: VerificationRandomness) -> int:
    """Return the sort rank for a randomness level."""
    order = {
        VerificationRandomness.DETERMINISTIC: 0,
        VerificationRandomness.SAMPLED: 1,
        VerificationRandomness.STATISTICAL: 2,
    }
    return order[randomness]


def randomness_exceeds(
    observed: VerificationRandomness, tolerance: VerificationRandomness
) -> bool:
    """Return whether observed randomness exceeds the configured tolerance."""
    return randomness_rank(observed) > randomness_rank(tolerance)


__all__ = [
    "arbitrate_results",
    "max_rule_randomness",
]
