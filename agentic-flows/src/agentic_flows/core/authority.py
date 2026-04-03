# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for core/authority.py."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from agentic_flows.core.errors import SemanticViolationError
from agentic_flows.core.verification_rules import default_rule_registry
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from agentic_flows.spec.model.verification.verification_result import VerificationResult
from agentic_flows.spec.ontology import (
    VerificationPhase,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import RuleID
from agentic_flows.spec.ontology.public import EventType

SEMANTICS_VERSION = "v1"
SEMANTICS_SOURCE = "docs/guarantees/system_guarantees.md"

SEMANTIC_DOMAIN = "structural_truth"
VERIFICATION_DOMAIN = "epistemic_truth"

Mode = Literal["plan", "dry-run", "live", "observe", "unsafe"]


class _Event(Protocol):
    """Internal helper type; not part of the public API."""

    event_type: EventType


class _Trace(Protocol):
    """Internal helper type; not part of the public API."""

    finalized: bool
    events: Sequence[_Event]


class _RunResult(Protocol):
    """Internal helper type; not part of the public API."""

    trace: _Trace | None
    verification_results: Sequence[object]
    verification_arbitrations: Sequence[VerificationArbitration]
    reasoning_bundles: Sequence[object]


@dataclass(frozen=True)
class AuthorityToken:
    """Authority token; misuse breaks semantic enforcement."""

    scope: str = "agentic_flows.authority"


def authority_token() -> AuthorityToken:
    """Issue authority token; misuse breaks semantic enforcement."""
    return AuthorityToken()


def enforce_runtime_semantics(result: _RunResult, *, mode: Mode) -> None:
    """Enforce runtime semantics; misuse breaks execution guarantees."""
    if mode == "plan":
        return
    if mode == "unsafe":
        _require_trace_finalized(result)
        return
    _require_trace_finalized(result)
    if mode == "live":
        _require_verification_once_per_step(result)


def finalize_trace(trace) -> None:
    """Finalize trace; misuse breaks immutability guarantees."""
    if object.__getattribute__(trace, "finalized"):
        raise SemanticViolationError("execution trace already finalized")
    trace.finalize()


def evaluate_verification(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    artifacts: Sequence[Artifact],
    policy: VerificationPolicy,
) -> VerificationResult:
    """Evaluate verification; misuse breaks verification trust."""
    registry = default_rule_registry()
    violations, total_cost, randomness_violations = registry.evaluate(
        policy, reasoning, evidence, artifacts
    )
    if total_cost > policy.max_rule_cost:
        violations.append(RuleID("verification_cost_budget"))
    violations.extend(randomness_violations)
    status = "PASS"
    reason = "verification_passed"

    if violations:
        status = "FAIL"
        reason = "baseline_rule_violation"

    if status == "PASS":
        if any(rule_id in policy.fail_on for rule_id in violations):
            status = "FAIL"
            reason = "policy_fail_on"
        elif any(rule_id in policy.escalate_on for rule_id in violations):
            status = "ESCALATE"
            reason = "policy_escalate_on"

    return VerificationResult(
        spec_version="v1",
        engine_id="content",
        status=status,
        reason=reason,
        randomness=VerificationRandomness.DETERMINISTIC,
        violations=tuple(violations),
        checked_artifact_ids=(reasoning.bundle_id,),
        phase=VerificationPhase.POST_EXECUTION,
        rules_applied=tuple(rule.rule_id for rule in policy.rules),
        decision=status,
    )


def baseline_violations(
    reasoning: ReasoningBundle,
    evidence: Sequence[RetrievedEvidence],
    artifacts: Sequence[Artifact],
) -> tuple[RuleID, ...]:
    """Compute baseline violations; misuse breaks rule evaluation."""
    violations: list[RuleID] = []
    evidence_map = {item.evidence_id: item for item in evidence}
    artifact_hashes = {artifact.content_hash for artifact in artifacts}

    if any(len(claim.supported_by) == 0 for claim in reasoning.claims):
        violations.append(RuleID("claim_requires_evidence"))

    if any(not (0.0 <= claim.confidence <= 1.0) for claim in reasoning.claims):
        violations.append(RuleID("confidence_in_range"))

    claim_ids = [claim.claim_id for claim in reasoning.claims]
    if len(set(claim_ids)) != len(claim_ids):
        violations.append(RuleID("unique_claim_ids"))

    if set(reasoning.evidence_ids) != set(evidence_map.keys()):
        violations.append(RuleID("bundle_evidence_ids_match_inputs"))

    for claim in reasoning.claims:
        for evidence_id in claim.supported_by:
            evidence_item = evidence_map.get(evidence_id)
            if evidence_item is None:
                violations.append(RuleID("claim_supports_known_evidence"))
                continue
            if str(evidence_id) not in claim.statement:
                violations.append(RuleID("claim_mentions_evidence_id"))
            if str(evidence_item.content_hash) not in claim.statement:
                violations.append(RuleID("claim_mentions_evidence_hash"))

        if artifact_hashes and not any(
            str(artifact_hash) in claim.statement for artifact_hash in artifact_hashes
        ):
            violations.append(RuleID("claim_mentions_artifact_hash"))

    return tuple(violations)


def _require_trace_finalized(result: _RunResult) -> None:
    """Internal helper; not part of the public API."""
    if result.trace is None:
        raise SemanticViolationError("execution trace must be returned for execution")
    if not result.trace.finalized:
        raise SemanticViolationError("execution trace must be finalized before return")


def _require_verification_once_per_step(result: _RunResult) -> None:
    """Internal helper; not part of the public API."""
    reasoning_bundle_ids = {
        bundle.bundle_id
        for bundle in result.reasoning_bundles
        if hasattr(bundle, "bundle_id")
    }
    arbitration_bundle_ids: set[str] = set()
    for arbitration in result.verification_arbitrations:
        arbitration_bundle_ids.update(
            str(item) for item in arbitration.target_artifact_ids
        )
    if reasoning_bundle_ids and arbitration_bundle_ids.issuperset(
        {str(bundle_id) for bundle_id in reasoning_bundle_ids}
    ):
        return
    trace = result.trace
    if trace is None:
        raise SemanticViolationError("verification must run exactly once per step")
    failure_events = {
        EventType.REASONING_FAILED,
        EventType.RETRIEVAL_FAILED,
        EventType.STEP_FAILED,
    }
    if not _has_event(trace.events, failure_events):
        raise SemanticViolationError("verification must run exactly once per step")


def _has_event(events: Iterable[_Event], failure_events: set[EventType]) -> bool:
    """Internal helper; not part of the public API."""
    return any(event.event_type in failure_events for event in events)


__all__ = [
    "AuthorityToken",
    "Mode",
    "SEMANTIC_DOMAIN",
    "SEMANTICS_SOURCE",
    "SEMANTICS_VERSION",
    "VERIFICATION_DOMAIN",
    "authority_token",
    "baseline_violations",
    "enforce_runtime_semantics",
    "evaluate_verification",
    "finalize_trace",
]
