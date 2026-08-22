# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical restart-safe codecs for shared application operation requests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from enum import Enum

from bijux_canon_runtime.application.operations.models import ReplayOperationRequest
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RetrievalFilters,
    RuntimeOperationRequest,
    RuntimeOutputPolicy,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    ReplayTolerance,
    RuntimeReplayPolicy,
)

_RUNTIME_REQUEST_SCHEMA = "bijux.runtime.application-request.v2"
_REPLAY_REQUEST_SCHEMA = "bijux.runtime.application-replay-request.v2"


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def _object(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _strings(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be an array of strings")
    return tuple(value)


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    return value


def _required_string(value: object, field_name: str) -> str:
    result = _optional_string(value, field_name)
    if result is None:
        raise ValueError(f"{field_name} is required")
    return result


def _optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer or null")
    return value


def _required_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def runtime_request_payload(request: RuntimeOperationRequest) -> dict[str, object]:
    """Encode a validated Runtime request for durable job persistence."""
    payload = _json_value(asdict(request))
    assert isinstance(payload, dict)
    result: dict[str, object] = {
        "request": payload,
        "schema_version": _RUNTIME_REQUEST_SCHEMA,
    }
    canonical_json_bytes(result)
    return result


def runtime_request_from_payload(
    payload: Mapping[str, object],
) -> RuntimeOperationRequest:
    """Reconstruct a typed Runtime request after worker process restart."""
    if payload.get("schema_version") != _RUNTIME_REQUEST_SCHEMA:
        raise ValueError("runtime application request schema is unsupported")
    request = _object(payload.get("request"), "request")
    budget = _object(request.get("budget"), "request.budget")
    filters = _object(request.get("filters"), "request.filters")
    raw_output_policy = request.get("output_policy")
    output_policy = None
    if raw_output_policy is not None:
        policy = _object(raw_output_policy, "request.output_policy")
        output_policy = RuntimeOutputPolicy(
            require_citations=_required_bool(
                policy.get("require_citations"),
                "request.output_policy.require_citations",
            ),
            permit_insufficient_answer=_required_bool(
                policy.get("permit_insufficient_answer"),
                "request.output_policy.permit_insufficient_answer",
            ),
            publish=_required_bool(
                policy.get("publish"), "request.output_policy.publish"
            ),
        )
    corpus_id = _optional_string(request.get("corpus_id"), "request.corpus_id")
    index_id = _optional_string(request.get("index_id"), "request.index_id")
    timeout_seconds = budget.get("timeout_seconds")
    max_artifact_bytes = budget.get("max_artifact_bytes")
    if isinstance(timeout_seconds, bool) or not isinstance(
        timeout_seconds, int | float
    ):
        raise ValueError("request.budget.timeout_seconds must be numeric")
    if isinstance(max_artifact_bytes, bool) or not isinstance(max_artifact_bytes, int):
        raise ValueError("request.budget.max_artifact_bytes must be an integer")
    return RuntimeOperationRequest(
        request_id=RequestID(
            _required_string(request.get("request_id"), "request.request_id")
        ),
        operation=RuntimeRequestOperation(
            _required_string(request.get("operation"), "request.operation")
        ),
        execution_profile=ExecutionProfile(
            _required_string(
                request.get("execution_profile"), "request.execution_profile"
            )
        ),
        budget=RuntimeRequestBudget(
            timeout_seconds=float(timeout_seconds),
            max_artifact_bytes=max_artifact_bytes,
            max_steps=_optional_int(
                budget.get("max_steps"), "request.budget.max_steps"
            ),
            max_provider_tokens=_optional_int(
                budget.get("max_provider_tokens"),
                "request.budget.max_provider_tokens",
            ),
        ),
        replay_mode=ReplayMode(
            _required_string(request.get("replay_mode"), "request.replay_mode")
        ),
        scope=_required_string(request.get("scope"), "request.scope"),
        query=_optional_string(request.get("query"), "request.query"),
        source_directory=_optional_string(
            request.get("source_directory"), "request.source_directory"
        ),
        corpus_id=None if corpus_id is None else ArtifactID(corpus_id),
        index_id=None if index_id is None else ArtifactID(index_id),
        filters=RetrievalFilters(
            document_ids=_strings(
                filters.get("document_ids"), "request.filters.document_ids"
            ),
            source_uris=_strings(
                filters.get("source_uris"), "request.filters.source_uris"
            ),
        ),
        top_k=_optional_int(request.get("top_k"), "request.top_k"),
        provider=_optional_string(request.get("provider"), "request.provider"),
        output_policy=output_policy,
        replay_attempt_id=_optional_string(
            request.get("replay_attempt_id"), "request.replay_attempt_id"
        ),
    )


def replay_request_payload(request: ReplayOperationRequest) -> dict[str, object]:
    """Encode complete replay authority for durable worker reconstruction."""
    result = {
        "policy": _json_value(asdict(request.policy)),
        "process_id": request.process_id,
        "request_id": str(request.request_id),
        "run_id": request.run_id,
        "schema_version": _REPLAY_REQUEST_SCHEMA,
        "source_attempt_id": request.source_attempt_id,
    }
    canonical_json_bytes(result)
    return result


def replay_request_from_payload(
    payload: Mapping[str, object],
) -> ReplayOperationRequest:
    """Reconstruct complete replay authority after process restart."""
    if payload.get("schema_version") != _REPLAY_REQUEST_SCHEMA:
        raise ValueError("runtime replay application request schema is unsupported")
    policy = _object(payload.get("policy"), "policy")
    tolerance = _object(policy.get("tolerance"), "policy.tolerance")
    max_duration_delta_ms = tolerance.get("max_duration_delta_ms")
    max_duration_ratio = tolerance.get("max_duration_ratio")
    if (
        isinstance(max_duration_delta_ms, bool)
        or not isinstance(max_duration_delta_ms, int | float)
        or isinstance(max_duration_ratio, bool)
        or not isinstance(max_duration_ratio, int | float)
    ):
        raise ValueError("replay tolerance values must be numeric")
    return ReplayOperationRequest(
        run_id=_required_string(payload.get("run_id"), "run_id"),
        source_attempt_id=_required_string(
            payload.get("source_attempt_id"), "source_attempt_id"
        ),
        request_id=RequestID(_required_string(payload.get("request_id"), "request_id")),
        process_id=_required_string(payload.get("process_id"), "process_id"),
        policy=RuntimeReplayPolicy(
            replay_mode=ReplayMode(
                _required_string(policy.get("replay_mode"), "policy.replay_mode")
            ),
            network_policy=ReplayNetworkPolicy(
                _required_string(policy.get("network_policy"), "policy.network_policy")
            ),
            provider_allowlist=_strings(
                policy.get("provider_allowlist"), "policy.provider_allowlist"
            ),
            tolerance=ReplayTolerance(
                max_duration_delta_ms=float(max_duration_delta_ms),
                max_duration_ratio=float(max_duration_ratio),
            ),
        ),
    )


__all__ = [
    "replay_request_from_payload",
    "replay_request_payload",
    "runtime_request_from_payload",
    "runtime_request_payload",
]
