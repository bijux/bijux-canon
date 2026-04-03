# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/orchestration/determinism_guard.py."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agentic_flows.runtime.observability.analysis.trace_diff import (
    non_determinism_report,
)
from agentic_flows.runtime.observability.capture.environment import (
    compute_environment_fingerprint,
)
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
    fingerprint_policy,
)
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_verdict import (
    ReplayVerdict,
    ReplayVerdictDetails,
)
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.ontology import DeterminismLevel
from agentic_flows.spec.ontology.public import (
    EventType,
    ReplayAcceptability,
    ReplayMode,
)


def validate_determinism(
    environment_fingerprint: str | None,
    seed: Any | None,
    unordered_normalized: bool,
    determinism_level: DeterminismLevel,
) -> None:
    """Input contract: environment_fingerprint is provided for the running host, seed is set when required, and unordered_normalized reflects input normalization; output guarantee: returns None when inputs satisfy the determinism_level requirements; failure semantics: raises ValueError on missing fingerprints, mismatches, or required normalization/seed violations."""
    current_fingerprint = compute_environment_fingerprint()
    if not environment_fingerprint:
        raise ValueError("environment_fingerprint is required before execution")
    if environment_fingerprint != current_fingerprint:
        raise ValueError("environment_fingerprint mismatch")
    if determinism_level in {DeterminismLevel.STRICT, DeterminismLevel.BOUNDED}:
        if seed is None:
            raise ValueError("deterministic seed is required for strict runs")
        if not unordered_normalized:
            raise ValueError(
                "unordered collections must be normalized before execution"
            )
    elif determinism_level == DeterminismLevel.PROBABILISTIC:
        if not unordered_normalized:
            raise ValueError(
                "unordered collections must be normalized before execution"
            )


def evaluate_structural_diffs(
    trace: ExecutionTrace,
    plan: ExecutionSteps,
    *,
    artifacts: Iterable[Artifact] | None = None,
    evidence: Iterable[RetrievedEvidence] | None = None,
    verification_policy: object | None = None,
) -> dict[str, object]:
    """Evaluate structural diffs for replay."""
    try:
        return replay_diff(
            trace,
            plan,
            artifacts=artifacts,
            evidence=evidence,
            verification_policy=verification_policy,
        )
    except ReplayDiffError as exc:
        return exc.diffs


def evaluate_entropy_diffs(
    expected_trace: ExecutionTrace, observed_trace: ExecutionTrace | None
) -> dict[str, object]:
    """Evaluate entropy diffs for replay."""
    if observed_trace is None:
        return {}
    return non_determinism_report(expected_trace, observed_trace)


def evaluate_policy_verdict(
    replay_mode: ReplayMode,
    acceptability: ReplayAcceptability,
    diffs: dict[str, object],
    entropy_report: dict[str, object],
    *,
    observed_trace: ExecutionTrace | None = None,
) -> ReplayVerdictDetails:
    """Evaluate replay verdicts under policy."""
    if observed_trace is not None and observed_trace.non_certifiable:
        return ReplayVerdictDetails(
            verdict=ReplayVerdict.NON_CERTIFIABLE,
            details={
                "reason": "observed trace marked non-certifiable",
                "diffs": diffs,
                "entropy_report": entropy_report,
            },
        )
    blocking, acceptable = _partition_diffs(diffs, acceptability)
    details: dict[str, object] = {
        "blocking": blocking,
        "acceptable": acceptable,
    }
    if entropy_report:
        details["entropy_report"] = entropy_report
    if replay_mode == ReplayMode.STRICT:
        verdict = ReplayVerdict.ACCEPTABLE if not diffs else ReplayVerdict.UNACCEPTABLE
    elif replay_mode == ReplayMode.BOUNDED:
        if blocking:
            verdict = ReplayVerdict.UNACCEPTABLE
        elif acceptable:
            verdict = ReplayVerdict.ACCEPTABLE_WITH_WARNINGS
        else:
            verdict = ReplayVerdict.ACCEPTABLE
    else:
        verdict = (
            ReplayVerdict.ACCEPTABLE_WITH_WARNINGS
            if diffs or acceptable or blocking
            else ReplayVerdict.ACCEPTABLE
        )
    return ReplayVerdictDetails(verdict=verdict, details=details)


def validate_replay(
    trace: ExecutionTrace,
    plan: ExecutionSteps,
    *,
    observed_trace: ExecutionTrace | None = None,
    artifacts: Iterable[Artifact] | None = None,
    evidence: Iterable[RetrievedEvidence] | None = None,
    verification_policy: object | None = None,
) -> ReplayVerdictDetails:
    """Validate replay; misuse breaks acceptability checks."""
    structural = evaluate_structural_diffs(
        trace,
        plan,
        artifacts=artifacts,
        evidence=evidence,
        verification_policy=verification_policy,
    )
    entropy_report = (
        evaluate_entropy_diffs(trace, observed_trace)
        if observed_trace is not None
        else {}
    )
    verdict = evaluate_policy_verdict(
        plan.replay_mode,
        plan.replay_acceptability,
        structural,
        entropy_report,
        observed_trace=observed_trace,
    )
    if (
        plan.replay_mode == ReplayMode.STRICT
        and verdict.verdict is ReplayVerdict.UNACCEPTABLE
    ):
        raise ValueError(f"replay mismatch: {verdict.details}")
    if (
        plan.replay_mode == ReplayMode.BOUNDED
        and verdict.verdict is ReplayVerdict.UNACCEPTABLE
    ):
        raise ValueError(f"replay mismatch: {verdict.details}")
    return verdict


def replay_diff(
    trace: ExecutionTrace,
    plan: ExecutionSteps,
    *,
    artifacts: Iterable[Artifact] | None = None,
    evidence: Iterable[RetrievedEvidence] | None = None,
    verification_policy: object | None = None,
) -> dict[str, object]:
    """Input contract: trace and plan describe the same run boundary and are finalized for comparison; output guarantee: returns a diff map of all contract mismatches across plan, environment, dataset, artifact, evidence, and policy; failure semantics: raises ReplayDiffError when any mismatch is detected."""
    diffs: dict[str, object] = {}
    if trace.plan_hash != plan.plan_hash:
        diffs["plan_hash"] = {
            "expected": plan.plan_hash,
            "observed": trace.plan_hash,
        }
    if trace.determinism_level != plan.determinism_level:
        diffs["determinism_level"] = {
            "expected": plan.determinism_level,
            "observed": trace.determinism_level,
        }
    if trace.replay_acceptability != plan.replay_acceptability:
        diffs["replay_acceptability"] = {
            "expected": plan.replay_acceptability,
            "observed": trace.replay_acceptability,
        }
    if trace.tenant_id != plan.tenant_id:
        diffs["tenant_id"] = {
            "expected": plan.tenant_id,
            "observed": trace.tenant_id,
        }
    if trace.flow_state != plan.flow_state:
        diffs["flow_state"] = {
            "expected": plan.flow_state,
            "observed": trace.flow_state,
        }
    if trace.replay_envelope != plan.replay_envelope:
        diffs["replay_envelope"] = {
            "expected": _envelope_payload(plan.replay_envelope),
            "observed": _envelope_payload(trace.replay_envelope),
        }
    if trace.environment_fingerprint != plan.environment_fingerprint:
        diffs["environment_fingerprint"] = {
            "expected": plan.environment_fingerprint,
            "observed": trace.environment_fingerprint,
        }
    if trace.dataset != plan.dataset:
        diffs["dataset"] = {
            "expected": _dataset_payload(plan.dataset),
            "observed": _dataset_payload(trace.dataset),
        }
    if trace.allow_deprecated_datasets != plan.allow_deprecated_datasets:
        diffs["allow_deprecated_datasets"] = {
            "expected": plan.allow_deprecated_datasets,
            "observed": trace.allow_deprecated_datasets,
        }
    if (
        plan.dataset.dataset_state.value == "deprecated"
        and not plan.allow_deprecated_datasets
    ):
        diffs["deprecated_dataset"] = {
            "expected": False,
            "observed": True,
        }

    if trace.verification_policy_fingerprint is not None:
        if verification_policy is None:
            diffs["verification_policy"] = {
                "expected": trace.verification_policy_fingerprint,
                "observed": None,
            }
        else:
            current = fingerprint_policy(verification_policy)
            if current != trace.verification_policy_fingerprint:
                diffs["verification_policy"] = {
                    "expected": trace.verification_policy_fingerprint,
                    "observed": current,
                }

    missing_step_end = _missing_step_end(trace.events, plan.steps)
    if missing_step_end:
        diffs["missing_step_end"] = sorted(missing_step_end)

    failed_steps = _failed_steps(trace.events)
    if failed_steps:
        diffs["failed_steps"] = sorted(failed_steps)

    human_events = _human_intervention_events(trace.events)
    if human_events:
        diffs["human_intervention_events"] = human_events

    if diffs and artifacts is not None:
        artifact_list = list(artifacts)
        diffs["artifact_fingerprint"] = semantic_artifact_fingerprint(artifact_list)
        diffs["artifact_count"] = len(artifact_list)

    if diffs and evidence is not None:
        evidence_list = list(evidence)
        diffs["evidence_fingerprint"] = semantic_evidence_fingerprint(evidence_list)
        diffs["evidence_count"] = len(evidence_list)

    if diffs:
        primary = next(iter(diffs))
        diffs["summary"] = f"Replay rejected: {primary}"
        raise ReplayDiffError(
            step_id=_first_divergent_step(plan, diffs),
            reason_code=primary,
            diffs=diffs,
        )

    return diffs


class ReplayDiffError(ValueError):
    """Replay diff error; misuse breaks deterministic replay."""

    def __init__(self, *, step_id: int, reason_code: str, diffs: dict[str, object]):
        super().__init__(f"replay diff at step {step_id}: {reason_code}")
        self.step_id = step_id
        self.reason_code = reason_code
        self.diffs = diffs


def _first_divergent_step(plan: ExecutionSteps, diffs: dict[str, object]) -> int:
    """Internal helper; not part of the public API."""
    candidates: list[int] = []
    missing = diffs.get("missing_step_end")
    if isinstance(missing, list):
        candidates.extend(int(value) for value in missing)
    failed = diffs.get("failed_steps")
    if isinstance(failed, list):
        candidates.extend(int(value) for value in failed)
    if candidates:
        return min(candidates)
    if plan.steps:
        return int(plan.steps[0].step_index)
    return 0


def _missing_step_end(
    events: Iterable[ExecutionEvent], steps: Iterable[object]
) -> set[int]:
    """Internal helper; not part of the public API."""
    expected_steps = {step.step_index for step in steps}
    ended = {
        event.step_index for event in events if event.event_type == EventType.STEP_END
    }
    failed = _failed_steps(events)
    return expected_steps.difference(ended.union(failed))


def _failed_steps(events: Iterable[ExecutionEvent]) -> set[int]:
    """Internal helper; not part of the public API."""
    failure_events = {
        EventType.REASONING_FAILED,
        EventType.RETRIEVAL_FAILED,
        EventType.STEP_FAILED,
        EventType.VERIFICATION_FAIL,
    }
    return {event.step_index for event in events if event.event_type in failure_events}


def _human_intervention_events(events: Iterable[ExecutionEvent]) -> list[int]:
    """Internal helper; not part of the public API."""
    return [
        event.event_index
        for event in events
        if event.event_type == EventType.HUMAN_INTERVENTION
    ]


def semantic_artifact_fingerprint(artifacts: Iterable[Artifact]) -> str:
    """Fingerprint artifact; misuse breaks replay comparison."""
    normalized = sorted(
        artifacts,
        key=lambda item: (
            str(item.tenant_id),
            str(item.artifact_id),
            str(item.content_hash),
        ),
    )
    return fingerprint_inputs(
        [
            {
                "tenant_id": item.tenant_id,
                "artifact_id": item.artifact_id,
                "content_hash": item.content_hash,
            }
            for item in normalized
        ]
    )


def semantic_evidence_fingerprint(evidence: Iterable[RetrievedEvidence]) -> str:
    """Fingerprint evidence; misuse breaks replay comparison."""
    normalized = sorted(
        evidence, key=lambda item: (str(item.evidence_id), str(item.content_hash))
    )
    return fingerprint_inputs(
        [
            {
                "evidence_id": item.evidence_id,
                "content_hash": item.content_hash,
                "determinism": item.determinism,
            }
            for item in normalized
        ]
    )


def _partition_diffs(
    diffs: dict[str, object], acceptability: ReplayAcceptability
) -> tuple[dict[str, object], dict[str, object]]:
    # ReplayAcceptability.EXACT_MATCH: triggers on any divergence; acceptable in production: yes.
    # ReplayAcceptability.INVARIANT_PRESERVING: triggers when only invariant-safe deltas exist; acceptable in production: yes.
    # ReplayAcceptability.STATISTICALLY_BOUNDED: triggers when bounded statistical drift is present; acceptable in production: depends on policy.
    """Internal helper; not part of the public API."""
    if not diffs:
        return {}, {}
    allowed: set[str] = set()
    if acceptability in {
        ReplayAcceptability.INVARIANT_PRESERVING,
        ReplayAcceptability.STATISTICALLY_BOUNDED,
    }:
        allowed = {
            "events",
            "artifact_fingerprint",
            "artifact_count",
            "evidence_fingerprint",
            "evidence_count",
        }
    blocking = {key: value for key, value in diffs.items() if key not in allowed}
    acceptable = {key: value for key, value in diffs.items() if key in allowed}
    return blocking, acceptable


def _dataset_payload(dataset) -> dict[str, object]:
    """Internal helper; not part of the public API."""
    return {
        "dataset_id": dataset.dataset_id,
        "tenant_id": dataset.tenant_id,
        "dataset_version": dataset.dataset_version,
        "dataset_hash": dataset.dataset_hash,
        "dataset_state": dataset.dataset_state,
    }


def _envelope_payload(envelope) -> dict[str, object]:
    """Internal helper; not part of the public API."""
    return {
        "min_claim_overlap": envelope.min_claim_overlap,
        "max_contradiction_delta": envelope.max_contradiction_delta,
    }


__all__ = [
    "evaluate_entropy_diffs",
    "evaluate_policy_verdict",
    "evaluate_structural_diffs",
    "replay_diff",
    "semantic_artifact_fingerprint",
    "semantic_evidence_fingerprint",
    "validate_determinism",
    "validate_replay",
]
