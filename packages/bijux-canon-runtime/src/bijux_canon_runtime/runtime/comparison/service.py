# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Explain semantic and performance differences across persisted attempts."""

from __future__ import annotations

from dataclasses import asdict
import hashlib

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.runtime.comparison.models import (
    ComparisonDimension,
    DifferenceClassification,
    RuntimeComparisonPolicy,
    RuntimeComparisonResult,
    RuntimeDifference,
)
from bijux_canon_runtime.runtime.inspection import (
    InspectedEventKind,
    RuntimeInspectionError,
    RuntimeRunInspection,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    required_dict,
    required_object,
    required_string,
)


class RuntimeComparisonService:
    """Compare persisted attempts without depending on live process state."""

    def __init__(self, inspector: RuntimeRunInspector) -> None:
        self._inspector = inspector

    def compare(
        self,
        *,
        baseline_run_id: str,
        baseline_attempt_id: str,
        candidate_run_id: str,
        candidate_attempt_id: str,
        policy: RuntimeComparisonPolicy | None = None,
    ) -> RuntimeComparisonResult:
        """Return one classified explanation for every selected dimension."""
        effective = policy or RuntimeComparisonPolicy()
        baseline = self._inspector.inspect(
            baseline_run_id,
            attempt_id=baseline_attempt_id,
        )
        candidate = self._inspector.inspect(
            candidate_run_id,
            attempt_id=candidate_attempt_id,
        )
        differences = tuple(
            self._difference(dimension, baseline, candidate, effective)
            for dimension in effective.dimensions
        )
        equivalent = all(
            item.classification
            in {
                DifferenceClassification.EQUAL,
                DifferenceClassification.EXPECTED,
                DifferenceClassification.BOUNDED,
            }
            for item in differences
        )
        identity_payload = {
            "baseline_attempt_id": baseline_attempt_id,
            "baseline_run_id": baseline_run_id,
            "candidate_attempt_id": candidate_attempt_id,
            "candidate_run_id": candidate_run_id,
            "differences": [_json_value(asdict(item)) for item in differences],
            "policy": _json_value(asdict(effective)),
            "schema_version": "bijux.runtime.comparison.v1",
        }
        comparison_sha256 = hashlib.sha256(
            canonical_json_bytes(identity_payload)
        ).hexdigest()
        return RuntimeComparisonResult(
            schema_version="bijux.runtime.comparison.v1",
            comparison_sha256=comparison_sha256,
            baseline_run_id=baseline_run_id,
            baseline_attempt_id=baseline_attempt_id,
            candidate_run_id=candidate_run_id,
            candidate_attempt_id=candidate_attempt_id,
            equivalent=equivalent,
            differences=differences,
        )

    @staticmethod
    def _difference(
        dimension: ComparisonDimension,
        baseline: RuntimeRunInspection,
        candidate: RuntimeRunInspection,
        policy: RuntimeComparisonPolicy,
    ) -> RuntimeDifference:
        if dimension is ComparisonDimension.TIMING:
            return _timing_difference(baseline, candidate, policy)
        baseline_value = _dimension_value(dimension, baseline)
        candidate_value = _dimension_value(dimension, candidate)
        if baseline_value == candidate_value:
            classification = DifferenceClassification.EQUAL
            explanation = f"{dimension.value} is identical"
        elif baseline_value is None or candidate_value is None:
            classification = DifferenceClassification.INCOMPARABLE
            explanation = f"{dimension.value} is absent from one attempt"
        elif dimension in policy.expected_differences:
            classification = DifferenceClassification.EXPECTED
            explanation = f"{dimension.value} differs under declared policy"
        else:
            classification = DifferenceClassification.REGRESSION
            explanation = f"{dimension.value} differs outside declared policy"
        return RuntimeDifference(
            dimension,
            f"$.{dimension.value}",
            classification,
            explanation,
            baseline_value,
            candidate_value,
        )


def _dimension_value(
    dimension: ComparisonDimension,
    inspection: RuntimeRunInspection,
) -> object:
    if dimension is ComparisonDimension.DAG:
        return [
            {
                "depends_on": list(step.depends_on),
                "input_contract_ids": list(step.input_contract_ids),
                "operation": step.operation,
                "output_contract_ids": list(step.output_contract_ids),
                "step_id": step.step_id,
            }
            for step in inspection.steps
        ]
    if dimension is ComparisonDimension.CONFIGURATION:
        return _configuration(inspection)
    if dimension in {
        ComparisonDimension.CORPUS,
        ComparisonDimension.INDEX,
        ComparisonDimension.MODEL,
    }:
        return _domain_values(inspection, dimension.value)
    if dimension is ComparisonDimension.RETRIEVAL:
        return {
            "queries": [item.value for item in inspection.queries],
            "hits": [item.value for item in inspection.hits],
        }
    if dimension is ComparisonDimension.CLAIMS:
        return [item.value for item in inspection.claims]
    if dimension is ComparisonDimension.CITATIONS:
        return [item.value for item in inspection.citations]
    if dimension is ComparisonDimension.PROVIDER_CALLS:
        return [item.value for item in inspection.provider_calls]
    if dimension is ComparisonDimension.POLICY:
        return _policies(inspection)
    if dimension is ComparisonDimension.OUTCOME:
        return {
            "checks": [item.value for item in inspection.checks],
            "failures": [
                {
                    "causes": list(item.error.causes),
                    "error_type": item.error.error_type,
                    "message": item.error.message,
                    "step_id": item.step_id,
                }
                for item in inspection.failures
            ],
            "status": inspection.status.value,
        }
    raise AssertionError(f"unsupported comparison dimension: {dimension}")


def _configuration(inspection: RuntimeRunInspection) -> object:
    manifest = _manifest(inspection)
    plan = required_object(manifest, "plan")
    raw_steps = plan.get("steps")
    if not isinstance(raw_steps, list):
        raise RuntimeInspectionError("comparison plan steps are invalid")
    result = []
    for raw_step in raw_steps:
        step = required_dict(raw_step, "plan step")
        inputs = dict(required_object(step, "inputs"))
        inputs.pop("request_id", None)
        inputs.pop("replay_attempt_id", None)
        result.append(
            {
                "inputs": inputs,
                "operation": required_string(step, "operation"),
                "step_id": required_string(step, "step_id"),
            }
        )
    return result


def _domain_values(
    inspection: RuntimeRunInspection,
    domain: str,
) -> object:
    values: list[dict[str, object]] = []
    for artifact in inspection.artifacts:
        matches_schema = domain in artifact.schema_id.lower()
        selected: list[tuple[str, object]] = []
        if artifact.json_value is not None:
            _find_domain_values(artifact.json_value, domain, "$", selected)
        if matches_schema or selected:
            record: dict[str, object] = {
                "values": [
                    {"path": path, "value": value} for path, value in selected
                ]
            }
            if matches_schema:
                record["artifact_id"] = str(artifact.artifact_id)
                record["schema_id"] = artifact.schema_id
            values.append(record)
    return sorted(values, key=canonical_json_bytes)


def _find_domain_values(
    value: object,
    domain: str,
    path: str,
    found: list[tuple[str, object]],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if domain in str(key).lower():
                found.append((child, item))
            else:
                _find_domain_values(item, domain, child, found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _find_domain_values(item, domain, f"{path}[{index}]", found)


def _policies(inspection: RuntimeRunInspection) -> object:
    manifest = _manifest(inspection)
    event_policies = []
    for event in inspection.events:
        if event.policy not in event_policies:
            event_policies.append(event.policy)
    return {
        "execution_metadata": manifest.get("execution_metadata", {}),
        "event_policies": event_policies,
    }


def _manifest(inspection: RuntimeRunInspection) -> dict[str, object]:
    for artifact in inspection.artifacts:
        if (
            artifact.schema_id != "bijux.runtime.execution-manifest.v1"
            or not isinstance(artifact.json_value, dict)
        ):
            continue
        attempt = required_object(artifact.json_value, "attempt")
        if required_string(attempt, "attempt_id") == inspection.selected_attempt_id:
            return artifact.json_value
    raise RuntimeInspectionError("comparison attempt manifest is unresolved")


def _timing_difference(
    baseline: RuntimeRunInspection,
    candidate: RuntimeRunInspection,
    policy: RuntimeComparisonPolicy,
) -> RuntimeDifference:
    baseline_value = _timings(baseline)
    candidate_value = _timings(candidate)
    baseline_total = sum(baseline_value.values())
    candidate_total = sum(candidate_value.values())
    delta = abs(candidate_total - baseline_total)
    if baseline_total == candidate_total == 0:
        ratio: float | None = 1.0
    elif min(baseline_total, candidate_total) == 0:
        ratio = None
    else:
        ratio = max(baseline_total, candidate_total) / min(
            baseline_total, candidate_total
        )
    equal = baseline_value == candidate_value
    bounded = (
        delta <= policy.max_duration_delta_ms
        and (ratio is None or ratio <= policy.max_duration_ratio)
    )
    if equal:
        classification = DifferenceClassification.EQUAL
        explanation = "step timings are identical"
    elif bounded:
        classification = DifferenceClassification.BOUNDED
        explanation = "step timings differ within declared absolute and ratio bounds"
    elif ComparisonDimension.TIMING in policy.expected_differences:
        classification = DifferenceClassification.EXPECTED
        explanation = "step timings differ beyond bounds but are declared expected"
    else:
        classification = DifferenceClassification.REGRESSION
        explanation = "step timings exceed declared bounds"
    return RuntimeDifference(
        ComparisonDimension.TIMING,
        "$.timing",
        classification,
        explanation,
        {"steps": baseline_value, "total_ms": baseline_total},
        {
            "delta_ms": delta,
            "ratio": ratio,
            "steps": candidate_value,
            "total_ms": candidate_total,
        },
    )


def _timings(inspection: RuntimeRunInspection) -> dict[str, float]:
    return {
        event.step_id: event.duration_ms or 0.0
        for event in inspection.events
        if event.event_kind
        in {
            InspectedEventKind.COMPLETED,
            InspectedEventKind.FAILED,
            InspectedEventKind.CANCELLED,
            InspectedEventKind.TIMED_OUT,
        }
    }


def _json_value(value: object) -> object:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


__all__ = ["RuntimeComparisonService"]
