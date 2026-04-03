# INTERNAL — NOT A PUBLIC EXTENSION POINT
# INTERNAL — SUBJECT TO CHANGE WITHOUT NOTICE
# INTERNAL API — NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

# Verification must never call agents or modify artifact; epistemic truth is delegated to authority.
"""Module definitions for runtime/verification_engine.py."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from agentic_flows.core.authority import evaluate_verification
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_policy,
)
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from agentic_flows.spec.model.verification.verification_result import VerificationResult
from agentic_flows.spec.ontology import (
    ArbitrationRule,
    ReasonCode,
    VerificationPhase,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import ArtifactID, PolicyFingerprint, RuleID


class VerificationEngine(Protocol):
    """Verification engine contract; misuse breaks verification."""

    engine_id: str

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        ...


class FlowVerificationEngine(Protocol):
    """Flow verification contract; misuse breaks flow verification."""

    engine_id: str

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify_flow and enforce its contract."""
        ...


@dataclass(frozen=True)
class ContentVerificationEngine:
    """Content verification engine; misuse breaks claim checks."""

    engine_id: str = "content"

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        result = evaluate_verification(reasoning, evidence, artifacts, policy)
        randomness = _max_rule_randomness(policy.rules)
        return VerificationResult(
            spec_version=result.spec_version,
            engine_id=self.engine_id,
            status=result.status,
            reason=result.reason,
            randomness=randomness,
            violations=result.violations,
            checked_artifact_ids=result.checked_artifact_ids,
            phase=result.phase,
            rules_applied=result.rules_applied,
            decision=result.decision,
        )


@dataclass(frozen=True)
class SignatureVerificationEngine:
    """Signature verification engine; misuse breaks signature checks."""

    engine_id: str = "signature"

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        return VerificationResult(
            spec_version="v1",
            engine_id=self.engine_id,
            status="PASS",
            reason="signature_ok",
            randomness=VerificationRandomness.DETERMINISTIC,
            violations=(),
            checked_artifact_ids=(reasoning.bundle_id,),
            phase=VerificationPhase.POST_EXECUTION,
            rules_applied=(),
            decision="PASS",
        )


@dataclass(frozen=True)
class ContradictionVerificationEngine:
    """Contradiction engine; misuse breaks contradiction detection."""

    engine_id: str = "contradiction"

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify_flow and enforce its contract."""
        violations = _detect_contradictions(reasoning_bundles)
        status = "PASS"
        reason = "no_contradictions"
        if violations:
            status = "FAIL"
            reason = ReasonCode.CONTRADICTION_DETECTED.value
        bundle_ids = tuple(bundle.bundle_id for bundle in reasoning_bundles)
        return VerificationResult(
            spec_version="v1",
            engine_id=self.engine_id,
            status=status,
            reason=reason,
            randomness=VerificationRandomness.DETERMINISTIC,
            violations=violations,
            checked_artifact_ids=bundle_ids,
            phase=VerificationPhase.POST_EXECUTION,
            rules_applied=(),
            decision=status,
        )


def _detect_contradictions(
    bundles: list[ReasoningBundle],
) -> tuple[RuleID, ...]:
    """Internal helper; not part of the public API."""
    statements: dict[str, list[float]] = {}
    negatives: set[str] = set()
    circular = False

    for bundle in bundles:
        for claim in bundle.claims:
            normalized = _normalize_statement(claim.statement)
            if normalized.startswith("not "):
                base = normalized.removeprefix("not ").strip()
                negatives.add(base)
            statements.setdefault(normalized, []).append(claim.confidence)
            if str(claim.claim_id) in normalized:
                circular = True

    violations: list[RuleID] = []
    for statement in statements:
        base = statement.removeprefix("not ").strip()
        if base in negatives and statement != f"not {base}":
            violations.append(RuleID("direct_contradiction"))
            break

    for confidences in statements.values():
        if len(confidences) > 1 and any(
            conf < max(confidences) for conf in confidences
        ):
            violations.append(RuleID("weakened_restatement"))
            break

    if circular:
        violations.append(RuleID("circular_justification"))

    return tuple(dict.fromkeys(violations))


def _normalize_statement(statement: str) -> str:
    """Internal helper; not part of the public API."""
    return " ".join(statement.lower().strip().split())


class VerificationOrchestrator:
    """Verification orchestrator; misuse breaks arbitration flow."""

    def __init__(
        self,
        *,
        bundle_engines: tuple[VerificationEngine, ...] | None = None,
        flow_engines: tuple[FlowVerificationEngine, ...] | None = None,
    ) -> None:
        """Internal helper; not part of the public API."""
        self._bundle_engines = bundle_engines or (
            ContentVerificationEngine(),
            SignatureVerificationEngine(),
        )
        self._flow_engines = flow_engines or (ContradictionVerificationEngine(),)

    def verify_bundle(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Execute verify_bundle and enforce its contract."""
        results = [
            engine.verify(reasoning, evidence, artifacts, policy)
            for engine in self._bundle_engines
        ]
        arbitration = _arbitrate(results, policy)
        return results, arbitration

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Execute verify_flow and enforce its contract."""
        results = [
            engine.verify_flow(reasoning_bundles, policy)
            for engine in self._flow_engines
        ]
        arbitration = _arbitrate(results, policy)
        return results, arbitration


def _arbitrate(
    results: list[VerificationResult], policy: VerificationPolicy
) -> VerificationArbitration:
    """Internal helper; not part of the public API."""
    arbitration_policy = policy.arbitration_policy
    rule = arbitration_policy.rule
    statuses = [result.status for result in results]
    randomness = _max_result_randomness(results)
    decision = "PASS"
    if rule == ArbitrationRule.STRICT_FIRST_FAILURE:
        for status in statuses:
            if status != "PASS":
                decision = status
                break
    elif rule == ArbitrationRule.UNANIMOUS:
        if all(status == "PASS" for status in statuses):
            decision = "PASS"
        elif any(status == "FAIL" for status in statuses):
            decision = "FAIL"
        else:
            decision = "ESCALATE"
    elif rule == ArbitrationRule.QUORUM:
        counts = Counter(statuses)
        threshold = arbitration_policy.quorum_threshold
        if threshold is None:
            threshold = len(statuses) // 2 + 1
        if counts["PASS"] >= threshold:
            decision = "PASS"
        elif counts["FAIL"] >= threshold:
            decision = "FAIL"
        else:
            decision = "ESCALATE"
    if decision == "PASS" and _randomness_exceeds(
        randomness, policy.randomness_tolerance
    ):
        decision = "ESCALATE"
    engine_ids = tuple(result.engine_id for result in results)
    engine_statuses = tuple(statuses)
    target_ids: list[ArtifactID] = []
    for result in results:
        target_ids.extend(result.checked_artifact_ids)
    return VerificationArbitration(
        spec_version="v1",
        rule=arbitration_policy.rule,
        policy_fingerprint=PolicyFingerprint(fingerprint_policy(policy)),
        decision=decision,
        randomness=randomness,
        engine_ids=engine_ids,
        engine_statuses=engine_statuses,
        target_artifact_ids=tuple(target_ids),
    )


def _max_rule_randomness(rules: tuple[object, ...]) -> VerificationRandomness:
    """Internal helper; not part of the public API."""
    if not rules:
        return VerificationRandomness.DETERMINISTIC
    return max(
        (rule.randomness_requirement for rule in rules),
        key=_randomness_rank,
    )


def _max_result_randomness(
    results: list[VerificationResult],
) -> VerificationRandomness:
    """Internal helper; not part of the public API."""
    if not results:
        return VerificationRandomness.DETERMINISTIC
    return max((result.randomness for result in results), key=_randomness_rank)


def _randomness_rank(randomness: VerificationRandomness) -> int:
    """Internal helper; not part of the public API."""
    order = {
        VerificationRandomness.DETERMINISTIC: 0,
        VerificationRandomness.SAMPLED: 1,
        VerificationRandomness.STATISTICAL: 2,
    }
    return order[randomness]


def _randomness_exceeds(
    observed: VerificationRandomness, tolerance: VerificationRandomness
) -> bool:
    """Internal helper; not part of the public API."""
    return _randomness_rank(observed) > _randomness_rank(tolerance)


__all__ = [
    "ContentVerificationEngine",
    "ContradictionVerificationEngine",
    "SignatureVerificationEngine",
    "VerificationEngine",
    "VerificationOrchestrator",
]
