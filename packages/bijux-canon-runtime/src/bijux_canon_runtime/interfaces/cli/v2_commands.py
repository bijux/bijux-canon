# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stable JSON CLI adapter over Runtime v2 application services."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from enum import Enum
import json
import os
from pathlib import Path
import sys
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from bijux_canon_ingest.application.source_discovery import (
    SourceDiscoveryRequest,
    discover_source_directory,
)

from bijux_canon_runtime.api.v2.conversion import (
    job_status,
    json_value,
    operation_request,
)
from bijux_canon_runtime.api.v2.schemas import (
    AskRequest,
    BuildIndexRequest,
    CancelRequest,
    CompareRequest,
    PrepareCorpusRequest,
    ReplayRequest,
    ResearchRequest,
    RetrieveRequest,
    RunRequest,
)
from bijux_canon_runtime.application.operations import (
    ApplicationCapabilityError,
    ReplayOperationRequest,
    RuntimeApplicationServicesV2,
)
from bijux_canon_runtime.application.problems import (
    RuntimeProblemCode,
    runtime_problem,
    runtime_problem_fields,
)
from bijux_canon_runtime.application.readiness import (
    RuntimeReadinessService,
    runtime_liveness,
)
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.runtime.pagination import PageRequest
from bijux_canon_runtime.model.execution.request_plan import (
    RuntimeOperationRequest,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.comparison import (
    ComparisonDimension,
    RuntimeComparisonPolicy,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobError
from bijux_canon_runtime.runtime.execution.application_composition import (
    compose_runtime_application_services,
)
from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    RuntimeReplayPolicy,
)

EXIT_INVALID_REQUEST = 2
EXIT_MISSING_CAPABILITY = 3
EXIT_OPERATION_FAILED = 4
EXIT_NOT_READY = 5
_default_application_services: RuntimeApplicationServicesV2 | None = None
ModelT = TypeVar("ModelT", bound=BaseModel)


def run_v2_command(
    args: argparse.Namespace,
    *,
    services: RuntimeApplicationServicesV2 | None,
    readiness_service: RuntimeReadinessService | None = None,
) -> int:
    """Execute one parsed v2 command and emit exactly one JSON document."""
    correlation_id, run_id = _problem_context(args)
    owned_service: RuntimeApplicationServicesV2 | None = None
    try:
        if args.v2_command == "discover":
            return _discover(args)
        if args.v2_command == "live":
            _write(runtime_liveness())
            return 0
        if args.v2_command == "ready":
            readiness = readiness_service or RuntimeReadinessService(
                resolve_runtime_configuration(environment=os.environ),
                environment=os.environ,
            )
            report = readiness.evaluate()
            _write(report)
            return 0 if report.ready else EXIT_NOT_READY
        service = _require_services(services)
        if services is None:
            owned_service = service
        if args.v2_command in {"ingest", "index", "retrieve", "ask", "research", "run"}:
            return _submit(args, service)
        if args.v2_command == "corpus-inspect":
            _write(json_value(service.inspect_corpus(ArtifactID(args.corpus_id))))
            return 0
        if args.v2_command == "index-inspect":
            _write(
                service.inspect_index_page(
                    ArtifactID(args.index_id),
                    page=PageRequest(
                        limit=args.limit,
                        cursor=args.cursor,
                        offset=args.offset,
                    ),
                )
            )
            return 0
        if args.v2_command == "status":
            _write(job_status(service.status(args.job_id)).model_dump(mode="json"))
            return 0
        if args.v2_command == "result":
            _write(
                {
                    "job_id": args.job_id,
                    "result": service.result(args.job_id),
                    "schema_version": "bijux.runtime.cli-job-result.v2",
                }
            )
            return 0
        if args.v2_command == "inspect":
            return _inspect(args, service)
        if args.v2_command == "replay":
            return _replay(args, service)
        if args.v2_command == "compare":
            return _compare(args, service)
        if args.v2_command == "cancel":
            _load_model(Path(args.request), CancelRequest)
            _write(job_status(service.cancel(args.job_id)).model_dump(mode="json"))
            return 0
        raise ValueError(f"unsupported v2 command: {args.v2_command}")
    except ValidationError as exc:
        _failure(
            RuntimeProblemCode.INVALID_REQUEST,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc.errors()[0]["type"] if exc.errors() else type(exc).__name__,
        )
        return EXIT_INVALID_REQUEST
    except ValueError as exc:
        _failure(
            RuntimeProblemCode.INVALID_REQUEST,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_INVALID_REQUEST
    except (OSError, json.JSONDecodeError) as exc:
        _failure(
            RuntimeProblemCode.INVALID_REQUEST,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_INVALID_REQUEST
    except KeyError as exc:
        _failure(
            RuntimeProblemCode.NOT_FOUND,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_OPERATION_FAILED
    except DurableJobError as exc:
        _failure(
            RuntimeProblemCode.CONFLICT,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_OPERATION_FAILED
    except ApplicationCapabilityError as exc:
        _failure(
            RuntimeProblemCode.MISSING_CAPABILITY,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_MISSING_CAPABILITY
    except RuntimeError as exc:
        _failure(
            RuntimeProblemCode.OPERATION_FAILED,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_OPERATION_FAILED
    finally:
        if owned_service is not None:
            _close_default_services(owned_service)


def _require_services(
    services: RuntimeApplicationServicesV2 | None,
) -> RuntimeApplicationServicesV2:
    if services is not None:
        return services
    global _default_application_services
    if _default_application_services is not None:
        return _default_application_services
    configuration = resolve_runtime_configuration(environment=os.environ)
    if configuration.working_root is None:
        raise ApplicationCapabilityError(
            "BIJUX_CANON_RUNTIME_WORKING_ROOT is required for Runtime v2 operations"
        )
    if configuration.embedding_model_path is None:
        raise ApplicationCapabilityError(
            "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH is required for Runtime v2 operations"
        )
    _default_application_services = compose_runtime_application_services(
        working_root=configuration.working_root.expanduser().resolve(),
        model_root=configuration.embedding_model_path.expanduser().resolve(),
    )
    return _default_application_services


def _close_default_services(service: RuntimeApplicationServicesV2) -> None:
    """Finish process-owned work before Python begins executor shutdown."""
    global _default_application_services
    try:
        service.close()
    finally:
        if _default_application_services is service:
            _default_application_services = None


def _discover(args: argparse.Namespace) -> int:
    directory = Path(args.directory).resolve()
    outcome = discover_source_directory(
        SourceDiscoveryRequest(
            root_name=args.root_name,
            directory=directory,
            include=tuple(args.include) or ("**/*",),
            exclude=tuple(args.exclude),
            symlink_policy=args.symlink_policy,
        )
    )
    _write(outcome.manifest)
    return 0 if outcome.complete else EXIT_OPERATION_FAILED


def _submit(
    args: argparse.Namespace,
    service: RuntimeApplicationServicesV2,
) -> int:
    command = args.v2_command
    if command == "ingest":
        ingest_body = _load_model(Path(args.request), PrepareCorpusRequest)
        request = operation_request(
            context=ingest_body.context,
            operation=RuntimeRequestOperation.CORPUS_PREPARE,
            execution_profile=ingest_body.execution_profile,
            budget=ingest_body.budget,
            scope=ingest_body.scope,
            source_directory=ingest_body.source_directory,
        )
        snapshot = service.corpus(request, idempotency_key=args.idempotency_key)
    elif command == "index":
        index_body = _load_model(Path(args.request), BuildIndexRequest)
        request = operation_request(
            context=index_body.context,
            operation=RuntimeRequestOperation.INDEX_BUILD,
            execution_profile=index_body.execution_profile,
            budget=index_body.budget,
            scope=index_body.scope,
            corpus_id=index_body.corpus_id,
        )
        snapshot = service.index(request, idempotency_key=args.idempotency_key)
    elif command == "retrieve":
        retrieve_body = _load_model(Path(args.request), RetrieveRequest)
        request = _retrieval(retrieve_body, RuntimeRequestOperation.RETRIEVE)
        snapshot = service.retrieve(request, idempotency_key=args.idempotency_key)
    elif command == "ask":
        ask_body = _load_model(Path(args.request), AskRequest)
        request = _answer(ask_body, RuntimeRequestOperation.ASK)
        snapshot = service.ask(request, idempotency_key=args.idempotency_key)
    elif command == "research":
        research_body = _load_model(Path(args.request), ResearchRequest)
        request = _answer(research_body, RuntimeRequestOperation.RESEARCH)
        snapshot = service.research(request, idempotency_key=args.idempotency_key)
    else:
        run_body = _load_model(Path(args.request), RunRequest)
        request = operation_request(
            context=run_body.context,
            operation=RuntimeRequestOperation.RUN,
            execution_profile=run_body.execution_profile,
            budget=run_body.budget,
            scope=run_body.scope,
            query=run_body.query,
            source_directory=run_body.source_directory,
            corpus_id=run_body.corpus_id,
            filters=(
                run_body.filters.document_ids,
                run_body.filters.source_uris,
            ),
            top_k=run_body.top_k,
            answer_policy=run_body.answer_policy,
        )
        snapshot = service.run(request, idempotency_key=args.idempotency_key)
    _write(job_status(snapshot).model_dump(mode="json"))
    return 0


def _retrieval(
    body: RetrieveRequest, operation: RuntimeRequestOperation
) -> RuntimeOperationRequest:
    return operation_request(
        context=body.context,
        operation=operation,
        execution_profile=body.execution_profile,
        budget=body.budget,
        scope=body.scope,
        query=body.query,
        index_id=body.index_id,
        filters=(body.filters.document_ids, body.filters.source_uris),
        top_k=body.top_k,
    )


def _answer(
    body: AskRequest, operation: RuntimeRequestOperation
) -> RuntimeOperationRequest:
    return operation_request(
        context=body.context,
        operation=operation,
        execution_profile=body.execution_profile,
        budget=body.budget,
        scope=body.scope,
        query=body.query,
        corpus_id=body.corpus_id,
        index_id=body.index_id,
        filters=(body.filters.document_ids, body.filters.source_uris),
        top_k=body.top_k,
        answer_policy=body.answer_policy,
    )


def _inspect(args: argparse.Namespace, service: RuntimeApplicationServicesV2) -> int:
    _write(
        service.inspect_page(
            args.run_id,
            attempt_id=args.attempt_id,
            page=PageRequest(
                limit=args.limit,
                cursor=args.cursor,
                offset=args.offset,
            ),
        )
    )
    return 0


def _replay(args: argparse.Namespace, service: RuntimeApplicationServicesV2) -> int:
    body = _load_model(Path(args.request), ReplayRequest)
    request = ReplayOperationRequest(
        run_id=args.run_id,
        source_attempt_id=body.source_attempt_id,
        request_id=RequestID(body.context.request_id),
        process_id=body.process_id,
        policy=RuntimeReplayPolicy(
            replay_mode=ReplayMode(body.context.replay_mode),
            network_policy=ReplayNetworkPolicy(body.network_policy),
            provider_allowlist=body.provider_allowlist,
        ),
    )
    snapshot = service.replay(
        request,
        idempotency_key=args.idempotency_key,
        timeout_seconds=body.timeout_seconds,
    )
    _write(job_status(snapshot).model_dump(mode="json"))
    return 0


def _compare(args: argparse.Namespace, service: RuntimeApplicationServicesV2) -> int:
    body = _load_model(Path(args.request), CompareRequest)
    dimensions = tuple(ComparisonDimension(item) for item in body.dimensions)
    result = service.compare_page(
        baseline_run_id=body.baseline_run_id,
        baseline_attempt_id=body.baseline_attempt_id,
        candidate_run_id=body.candidate_run_id,
        candidate_attempt_id=body.candidate_attempt_id,
        page=PageRequest(limit=body.limit, cursor=body.cursor),
        policy=RuntimeComparisonPolicy(
            dimensions=dimensions,
            expected_differences=tuple(
                item
                for item in (ComparisonDimension.TIMING, ComparisonDimension.POLICY)
                if item in dimensions
            ),
        ),
    )
    _write(json_value(result))
    return 0


def _load_model(path: Path, model_type: type[ModelT]) -> ModelT:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return model_type.model_validate(payload)


def _problem_context(args: argparse.Namespace) -> tuple[str | None, str | None]:
    correlation_id = getattr(args, "correlation_id", None)
    run_id = getattr(args, "run_id", None)
    request_path = getattr(args, "request", None)
    if not isinstance(request_path, str):
        return correlation_id, run_id
    try:
        path = Path(request_path)
        if path.stat().st_size > 1_048_576:
            return correlation_id, run_id
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return correlation_id, run_id
    if not isinstance(payload, dict):
        return correlation_id, run_id
    context = payload.get("context")
    if correlation_id is None and isinstance(context, dict):
        candidate = context.get("correlation_id")
        if isinstance(candidate, str):
            correlation_id = candidate
    if run_id is None:
        candidate = payload.get("baseline_run_id")
        if isinstance(candidate, str):
            run_id = candidate
    return correlation_id, run_id


def _write(value: object) -> None:
    print(json.dumps(_normalize(value), sort_keys=True, separators=(",", ":")))


def _normalize(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _normalize(asdict(value))  # type: ignore[call-overload]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_normalize(item) for item in value]
    return value


def _failure(
    code: RuntimeProblemCode,
    *,
    correlation_id: str | None,
    run_id: str | None,
    cause: object | None,
) -> None:
    payload = runtime_problem_fields(
        runtime_problem(
            code,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=cause,
        )
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")), file=sys.stderr)


__all__ = [
    "EXIT_INVALID_REQUEST",
    "EXIT_MISSING_CAPABILITY",
    "EXIT_NOT_READY",
    "EXIT_OPERATION_FAILED",
    "run_v2_command",
]
