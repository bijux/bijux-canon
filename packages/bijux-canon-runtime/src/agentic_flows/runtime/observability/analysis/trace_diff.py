# ANALYSIS ONLY — NOT REQUIRED FOR EXECUTION OR REPLAY
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/analysis/trace_diff.py."""

from __future__ import annotations

from dataclasses import asdict

from agentic_flows.runtime.observability.classification.determinism_classification import (
    determinism_classes_for_trace,
    determinism_profile_for_trace,
)
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.ontology import EntropyMagnitude
from agentic_flows.spec.ontology.public import ReplayAcceptability

_MAGNITUDE_ORDER = {
    EntropyMagnitude.LOW: 0,
    EntropyMagnitude.MEDIUM: 1,
    EntropyMagnitude.HIGH: 2,
}


def semantic_trace_diff(
    expected: ExecutionTrace,
    observed: ExecutionTrace,
    *,
    acceptability: ReplayAcceptability = ReplayAcceptability.EXACT_MATCH,
) -> dict[str, object]:
    """Compute semantic trace diff; misuse hides divergence."""
    diffs: dict[str, object] = {}
    if expected.flow_id != observed.flow_id:
        diffs["flow_id"] = {"expected": expected.flow_id, "observed": observed.flow_id}
    if expected.plan_hash != observed.plan_hash:
        diffs["plan_hash"] = {
            "expected": expected.plan_hash,
            "observed": observed.plan_hash,
        }
    if expected.tenant_id != observed.tenant_id:
        diffs["tenant_id"] = {
            "expected": expected.tenant_id,
            "observed": observed.tenant_id,
        }
    if expected.flow_state != observed.flow_state:
        diffs["flow_state"] = {
            "expected": expected.flow_state,
            "observed": observed.flow_state,
        }
    if expected.replay_envelope != observed.replay_envelope:
        diffs["replay_envelope"] = {
            "expected": _envelope_payload(expected.replay_envelope),
            "observed": _envelope_payload(observed.replay_envelope),
        }
    if expected.dataset != observed.dataset:
        diffs["dataset"] = {
            "expected": _dataset_payload(expected.dataset),
            "observed": _dataset_payload(observed.dataset),
        }
    if expected.allow_deprecated_datasets != observed.allow_deprecated_datasets:
        diffs["allow_deprecated_datasets"] = {
            "expected": expected.allow_deprecated_datasets,
            "observed": observed.allow_deprecated_datasets,
        }
    if expected.environment_fingerprint != observed.environment_fingerprint:
        diffs["environment_fingerprint"] = {
            "expected": expected.environment_fingerprint,
            "observed": observed.environment_fingerprint,
        }
    if (
        expected.verification_policy_fingerprint
        != observed.verification_policy_fingerprint
    ):
        diffs["verification_policy_fingerprint"] = {
            "expected": expected.verification_policy_fingerprint,
            "observed": observed.verification_policy_fingerprint,
        }
    expected_events = _event_signature(expected, acceptability)
    observed_events = _event_signature(observed, acceptability)
    if expected_events != observed_events:
        diffs["events"] = {
            "expected": expected_events,
            "observed": observed_events,
        }
    elif acceptability != ReplayAcceptability.EXACT_MATCH and _event_signature(
        expected, ReplayAcceptability.EXACT_MATCH
    ) != _event_signature(observed, ReplayAcceptability.EXACT_MATCH):
        diffs["acceptable_events"] = "different but acceptable under policy"
    if acceptability == ReplayAcceptability.STATISTICALLY_BOUNDED:
        diffs.update(_statistical_envelope_diff(expected, observed))
    if acceptability != ReplayAcceptability.EXACT_MATCH:
        diffs["non_determinism_report"] = non_determinism_report(expected, observed)
    return diffs


def render_semantic_diff(diff: dict[str, object]) -> str:
    """Render semantic diff; misuse hides operator clarity."""
    if not diff:
        return "no semantic differences"
    lines = ["semantic differences:"]
    for key, value in diff.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _event_signature(
    trace: ExecutionTrace, acceptability: ReplayAcceptability
) -> list[tuple[object, ...]]:
    """Internal helper; not part of the public API."""
    if acceptability == ReplayAcceptability.EXACT_MATCH:
        return [
            (event.event_type, event.step_index, event.payload_hash)
            for event in trace.events
        ]
    if acceptability == ReplayAcceptability.INVARIANT_PRESERVING:
        return [(event.event_type, event.step_index) for event in trace.events]
    if acceptability == ReplayAcceptability.STATISTICALLY_BOUNDED:
        return sorted((event.event_type, event.step_index) for event in trace.events)
    return [
        (event.event_type, event.step_index, event.payload_hash)
        for event in trace.events
    ]


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


def _statistical_envelope_diff(
    expected: ExecutionTrace,
    observed: ExecutionTrace,
) -> dict[str, object]:
    """Internal helper; not part of the public API."""
    diffs: dict[str, object] = {}
    expected_claims = set(expected.claim_ids)
    observed_claims = set(observed.claim_ids)
    overlap = 1.0
    if expected_claims:
        overlap = len(expected_claims & observed_claims) / len(expected_claims)
    if overlap < expected.replay_envelope.min_claim_overlap:
        diffs["claim_overlap"] = {
            "expected_min": expected.replay_envelope.min_claim_overlap,
            "observed": overlap,
        }
    contradiction_delta = abs(
        expected.contradiction_count - observed.contradiction_count
    )
    if contradiction_delta > expected.replay_envelope.max_contradiction_delta:
        diffs["contradiction_delta"] = {
            "allowed": expected.replay_envelope.max_contradiction_delta,
            "observed": contradiction_delta,
        }
    if expected.arbitration_decision != observed.arbitration_decision:
        diffs["arbitration_decision"] = {
            "expected": expected.arbitration_decision,
            "observed": observed.arbitration_decision,
        }
    return diffs


def non_determinism_report(
    expected: ExecutionTrace, observed: ExecutionTrace
) -> dict[str, object]:
    """Summarize nondeterminism; misuse hides entropy sources."""
    expected_summary = entropy_summary(expected.entropy_usage)
    observed_summary = entropy_summary(observed.entropy_usage)
    class_report = determinism_class_report(expected, observed)
    expected_profile = determinism_profile_for_trace(expected)
    observed_profile = determinism_profile_for_trace(observed)
    return {
        "expected_entropy": expected_summary,
        "observed_entropy": observed_summary,
        "entropy_sources_added": sorted(
            set(observed_summary["sources"]) - set(expected_summary["sources"])
        ),
        "entropy_sources_missing": sorted(
            set(expected_summary["sources"]) - set(observed_summary["sources"])
        ),
        "entropy_magnitude_delta": {
            "expected": expected_summary["max_magnitude"],
            "observed": observed_summary["max_magnitude"],
        },
        "determinism_classes": class_report,
        "determinism_profile": {
            "expected": asdict(expected_profile),
            "observed": asdict(observed_profile),
        },
    }


def entropy_summary(usage: tuple[EntropyUsage, ...]) -> dict[str, object]:
    """Summarize entropy usage; misuse hides budget drift."""
    sources = sorted({entry.source.value for entry in usage})
    max_magnitude = None
    if usage:
        max_entry = max(usage, key=lambda entry: _MAGNITUDE_ORDER[entry.magnitude])
        max_magnitude = max_entry.magnitude.value
    return {
        "sources": sources,
        "count": len(usage),
        "max_magnitude": max_magnitude,
    }


def determinism_class_report(
    expected: ExecutionTrace, observed: ExecutionTrace
) -> dict[str, object]:
    """Report determinism classes; misuse hides classification drift."""
    expected_classes = determinism_classes_for_trace(expected)
    observed_classes = determinism_classes_for_trace(observed)
    return {
        "expected": expected_classes,
        "observed": observed_classes,
        "added": sorted(set(observed_classes) - set(expected_classes)),
        "missing": sorted(set(expected_classes) - set(observed_classes)),
    }


__all__ = [
    "entropy_summary",
    "determinism_class_report",
    "non_determinism_report",
    "render_semantic_diff",
    "semantic_trace_diff",
]
