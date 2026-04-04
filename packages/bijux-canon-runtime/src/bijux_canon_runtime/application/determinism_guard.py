# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for application/determinism_guard.py."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from bijux_canon_runtime.application.replay_event_analysis import (
    failed_steps,
    first_divergent_step,
    human_intervention_events,
    missing_step_end,
)
from bijux_canon_runtime.application.replay_support import (
    dataset_payload,
    envelope_payload,
    partition_diffs,
    semantic_artifact_fingerprint,
    semantic_evidence_fingerprint,
)
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.execution.replay_verdict import (
    ReplayVerdict,
    ReplayVerdictDetails,
)
from bijux_canon_runtime.observability.analysis.trace_diff import (
    non_determinism_report,
)
from bijux_canon_runtime.observability.capture.environment import (
    compute_environment_fingerprint,
)
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_policy,
)
from bijux_canon_runtime.ontology import DeterminismLevel
from bijux_canon_runtime.ontology.public import (
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
    blocking, acceptable = partition_diffs(diffs, acceptability)
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
            "expected": envelope_payload(plan.replay_envelope),
            "observed": envelope_payload(trace.replay_envelope),
        }
    if trace.environment_fingerprint != plan.environment_fingerprint:
        diffs["environment_fingerprint"] = {
            "expected": plan.environment_fingerprint,
            "observed": trace.environment_fingerprint,
        }
    if trace.dataset != plan.dataset:
        diffs["dataset"] = {
            "expected": dataset_payload(plan.dataset),
            "observed": dataset_payload(trace.dataset),
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

    missing_steps = missing_step_end(trace.events, plan.steps)
    if missing_steps:
        diffs["missing_step_end"] = sorted(missing_steps)

    failed_step_indexes = failed_steps(trace.events)
    if failed_step_indexes:
        diffs["failed_steps"] = sorted(failed_step_indexes)

    human_events = human_intervention_events(trace.events)
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
            step_id=first_divergent_step(plan, diffs),
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
