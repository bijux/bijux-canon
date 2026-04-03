# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for core/verification_rules.py."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_rule import VerificationRule
from agentic_flows.spec.ontology import VerificationRandomness
from agentic_flows.spec.ontology.ids import RuleID

RuleEvaluator = Callable[
    [ReasoningBundle, Sequence[RetrievedEvidence], Sequence[Artifact]], bool
]


@dataclass(frozen=True)
class RuleMetadata:
    """Rule metadata; misuse breaks verification policy evaluation."""

    rule_id: RuleID
    randomness: VerificationRandomness
    cost: int


class RuleRegistry:
    """Rule registry; misuse breaks rule enforcement."""

    def __init__(self) -> None:
        """Internal helper; not part of the public API."""
        self._rules: dict[RuleID, tuple[RuleEvaluator, RuleMetadata]] = {}

    def register(self, evaluator: RuleEvaluator, metadata: RuleMetadata) -> None:
        """Execute register and enforce its contract."""
        self._rules[metadata.rule_id] = (evaluator, metadata)

    def metadata(self, rule_id: RuleID) -> RuleMetadata:
        """Execute metadata and enforce its contract."""
        if rule_id not in self._rules:
            raise ValueError(f"verification rule not registered: {rule_id}")
        return self._rules[rule_id][1]

    def evaluate(
        self,
        policy: VerificationPolicy,
        reasoning: ReasoningBundle,
        evidence: Sequence[RetrievedEvidence],
        artifacts: Sequence[Artifact],
        *,
        include_baseline: bool = True,
    ) -> tuple[list[RuleID], int, list[RuleID]]:
        """Execute evaluate and enforce its contract."""
        violations: list[RuleID] = []
        randomness_violations: list[RuleID] = []
        total_cost = 0
        rules = list(policy.rules)
        if include_baseline:
            rules.extend(_BASELINE_RULES)
        for rule in rules:
            evaluator, metadata = self._rules.get(rule.rule_id, (None, None))
            if evaluator is None or metadata is None:
                raise ValueError(f"verification rule not registered: {rule.rule_id}")
            if _randomness_rank(metadata.randomness) > _randomness_rank(
                policy.randomness_tolerance
            ):
                randomness_violations.append(RuleID("rule_randomness_exceeds_policy"))
            total_cost += metadata.cost
            if not evaluator(reasoning, evidence, artifacts):
                violations.append(rule.rule_id)
        return violations, total_cost, randomness_violations


def default_rule_registry() -> RuleRegistry:
    """Build default registry; misuse breaks baseline verification."""
    registry = RuleRegistry()
    registry.register(_claim_requires_evidence, _meta("claim_requires_evidence", 1))
    registry.register(_confidence_in_range, _meta("confidence_in_range", 1))
    registry.register(_unique_claim_ids, _meta("unique_claim_ids", 1))
    registry.register(
        _bundle_evidence_ids_match_inputs,
        _meta("bundle_evidence_ids_match_inputs", 1),
    )
    registry.register(
        _claim_supports_known_evidence, _meta("claim_supports_known_evidence", 1)
    )
    registry.register(
        _claim_mentions_evidence_id, _meta("claim_mentions_evidence_id", 1)
    )
    registry.register(
        _claim_mentions_evidence_hash, _meta("claim_mentions_evidence_hash", 1)
    )
    registry.register(
        _claim_mentions_artifact_hash, _meta("claim_mentions_artifact_hash", 1)
    )
    return registry


def _meta(rule_id: str, cost: int) -> RuleMetadata:
    """Internal helper; not part of the public API."""
    return RuleMetadata(
        rule_id=RuleID(rule_id),
        randomness=VerificationRandomness.DETERMINISTIC,
        cost=cost,
    )


def _claim_requires_evidence(
    reasoning: ReasoningBundle,
    _evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    return all(claim.supported_by for claim in reasoning.claims)


def _confidence_in_range(
    reasoning: ReasoningBundle,
    _evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    return all(0.0 <= claim.confidence <= 1.0 for claim in reasoning.claims)


def _unique_claim_ids(
    reasoning: ReasoningBundle,
    _evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    claim_ids = [claim.claim_id for claim in reasoning.claims]
    return len(set(claim_ids)) == len(claim_ids)


def _bundle_evidence_ids_match_inputs(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    evidence_ids = {item.evidence_id for item in evidence}
    return set(reasoning.evidence_ids) == evidence_ids


def _claim_supports_known_evidence(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    evidence_ids = {item.evidence_id for item in evidence}
    return all(
        evidence_id in evidence_ids
        for claim in reasoning.claims
        for evidence_id in claim.supported_by
    )


def _claim_mentions_evidence_id(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    evidence_map = {item.evidence_id: item for item in evidence}
    for claim in reasoning.claims:
        for evidence_id in claim.supported_by:
            if str(evidence_id) not in claim.statement:
                return False
            evidence_item = evidence_map.get(evidence_id)
            if evidence_item is None:
                return False
    return True


def _claim_mentions_evidence_hash(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    _artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    evidence_map = {item.evidence_id: item for item in evidence}
    for claim in reasoning.claims:
        for evidence_id in claim.supported_by:
            evidence_item = evidence_map.get(evidence_id)
            if evidence_item is None:
                return False
            if str(evidence_item.content_hash) not in claim.statement:
                return False
    return True


def _claim_mentions_artifact_hash(
    reasoning: ReasoningBundle,
    _evidence: Sequence[RetrievedEvidence],
    artifacts: Sequence[Artifact],
) -> bool:
    """Internal helper; not part of the public API."""
    if not artifacts:
        return True
    artifact_hashes = {artifact.content_hash for artifact in artifacts}
    return all(
        any(str(artifact_hash) in claim.statement for artifact_hash in artifact_hashes)
        for claim in reasoning.claims
    )


def _randomness_rank(randomness: VerificationRandomness) -> int:
    """Internal helper; not part of the public API."""
    return {
        VerificationRandomness.DETERMINISTIC: 0,
        VerificationRandomness.SAMPLED: 1,
        VerificationRandomness.STATISTICAL: 2,
    }[randomness]


_BASELINE_RULES: tuple[VerificationRule, ...] = (
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("claim_requires_evidence"),
        description="Claims must cite evidence.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("confidence_in_range"),
        description="Claim confidence must be in range.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("unique_claim_ids"),
        description="Claims must be unique.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("bundle_evidence_ids_match_inputs"),
        description="Bundle evidence must match inputs.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("claim_supports_known_evidence"),
        description="Claims must reference known evidence.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("claim_mentions_evidence_id"),
        description="Claims must mention evidence IDs.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("claim_mentions_evidence_hash"),
        description="Claims must mention evidence hashes.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
    VerificationRule(
        spec_version="v1",
        rule_id=RuleID("claim_mentions_artifact_hash"),
        description="Claims must mention artifact hashes.",
        severity="error",
        target="reasoning_bundle",
        randomness_requirement=VerificationRandomness.DETERMINISTIC,
        cost=1,
    ),
)


__all__ = ["RuleMetadata", "RuleRegistry", "default_rule_registry"]
