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
import uuid

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
from bijux_canon_runtime.application.capability_discovery import (
    RuntimeCapabilityDiscovery,
    RuntimeCapabilityDiscoveryService,
)
from bijux_canon_runtime.application.operations import (
    ApplicationCapabilityError,
    ReplayOperationRequest,
    RuntimeApplicationServicesV2,
    RuntimeRetrievalConfigurationSearchReport,
    RuntimeRetrievalEvaluationInput,
    RuntimeRetrievalEvaluationReport,
    retrieval_configuration_summary,
)
from bijux_canon_runtime.application.problems import (
    RuntimeProblemCode,
    runtime_problem,
    runtime_problem_fields,
)
from bijux_canon_runtime.application.readiness import (
    ReadinessCapability,
    RuntimeReadinessService,
    runtime_liveness,
)
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_protection import (
    RuntimeWorkspaceProtection,
    WorkspaceProtectionError,
)
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.comparison import (
    ComparisonDimension,
    RuntimeComparisonPolicy,
)
from bijux_canon_runtime.runtime.execution.application_composition import (
    compose_runtime_application_services,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobError
from bijux_canon_runtime.runtime.pagination import PageRequest
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
    capability_discovery_service: RuntimeCapabilityDiscoveryService | None = None,
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
        if args.v2_command == "capabilities":
            discovery = (
                capability_discovery_service
                or RuntimeCapabilityDiscoveryService(
                    resolve_runtime_configuration(environment=os.environ),
                    environment=os.environ,
                )
            )
            capability_report = discovery.inspect()
            if args.human:
                _write_capabilities_human(capability_report)
            else:
                _write(capability_report)
            return 0
        if args.v2_command == "ready":
            readiness = readiness_service or RuntimeReadinessService(
                resolve_runtime_configuration(environment=os.environ),
                environment=os.environ,
            )
            readiness_report = readiness.evaluate(
                ReadinessCapability(args.operation),
                execution_profile=(
                    None if args.profile is None else ExecutionProfile(args.profile)
                ),
            )
            _write(readiness_report)
            return 0 if readiness_report.ready else EXIT_NOT_READY
        if args.v2_command == "backup":
            protection = RuntimeWorkspaceProtection(
                resolve_runtime_configuration(environment=os.environ)
            )
            _write(
                protection.backup(
                    backup_id=args.backup_id,
                    created_at=args.created_at,
                )
            )
            return 0
        if args.v2_command == "restore":
            _write(
                RuntimeWorkspaceProtection.restore(
                    backup_generation=Path(args.backup_generation),
                    restore_root=Path(args.restore_root),
                )
            )
            return 0
        service = _require_services(services)
        if services is None:
            owned_service = service
        if args.v2_command in {
            "ingest",
            "index",
            "search",
            "retrieve",
            "ask",
            "research",
            "run",
        }:
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
        if args.v2_command in {
            "evaluate-retrieval",
            "search-retrieval-configurations",
        }:
            evaluation_input = RuntimeRetrievalEvaluationInput(
                cases_path=Path(args.cases).resolve(),
                qrels_path=Path(args.qrels).resolve(),
                index_artifact_id=args.index_id,
                split=args.split,
                mode=args.mode,
                top_k=args.top_k,
            )
            if args.v2_command == "search-retrieval-configurations":
                search = service.search_retrieval_configurations(evaluation_input)
                if args.human:
                    _write_configuration_search_human(search)
                else:
                    _write(asdict(search))
                return 0
            evaluation = service.evaluate_reviewed_retrieval(evaluation_input)
            if args.human:
                _write_retrieval_evaluation_human(evaluation)
            else:
                _write(evaluation.manifest())
            return 0
        if args.v2_command == "evaluate-answer":
            _write(
                service.evaluate_persisted_answer(
                    case_id=args.case_id,
                    question=args.question,
                    run_id=args.run_id,
                    attempt_id=args.attempt_id,
                ).model_dump(mode="json")
            )
            return 0
        if args.v2_command == "status":
            snapshot = (
                service.wait(args.job_id, timeout_seconds=args.timeout_seconds)
                if args.follow
                else service.status(args.job_id)
            )
            _write(job_status(snapshot).model_dump(mode="json"))
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
        if args.v2_command == "artifact-payload":
            _write(
                service.read_artifact_payload_page(
                    ArtifactID(args.artifact_id),
                    offset=args.offset,
                    max_bytes=args.max_bytes,
                )
            )
            return 0
        if args.v2_command == "replay":
            return _replay(args, service)
        if args.v2_command == "compare":
            return _compare(args, service)
        if args.v2_command == "cancel":
            _cancel_body(args)
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
    except TimeoutError as exc:
        _failure(
            RuntimeProblemCode.OPERATION_FAILED,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_OPERATION_FAILED
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
    except WorkspaceProtectionError as exc:
        _failure(
            RuntimeProblemCode.OPERATION_FAILED,
            correlation_id=correlation_id,
            run_id=run_id,
            cause=exc,
        )
        return EXIT_OPERATION_FAILED
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
    _default_application_services = compose_runtime_application_services(
        configuration=configuration,
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
    command = "retrieve" if args.v2_command == "search" else args.v2_command
    if command == "ingest":
        ingest_body = _operation_body(args, PrepareCorpusRequest)
        request = operation_request(
            context=ingest_body.context,
            operation=RuntimeRequestOperation.CORPUS_PREPARE,
            execution_profile=ingest_body.execution_profile,
            budget=ingest_body.budget,
            scope=ingest_body.scope,
            source_directory=ingest_body.source_directory,
        )
        snapshot = service.corpus(
            request,
            idempotency_key=args.idempotency_key or ingest_body.context.request_id,
        )
    elif command == "index":
        index_body = _operation_body(args, BuildIndexRequest)
        request = operation_request(
            context=index_body.context,
            operation=RuntimeRequestOperation.INDEX_BUILD,
            execution_profile=index_body.execution_profile,
            budget=index_body.budget,
            scope=index_body.scope,
            corpus_id=index_body.corpus_id,
        )
        snapshot = service.index(
            request,
            idempotency_key=args.idempotency_key or index_body.context.request_id,
        )
    elif command == "retrieve":
        retrieve_body = _operation_body(args, RetrieveRequest)
        request = _retrieval(retrieve_body, RuntimeRequestOperation.RETRIEVE)
        snapshot = service.retrieve(
            request,
            idempotency_key=args.idempotency_key or retrieve_body.context.request_id,
        )
    elif command == "ask":
        ask_body = _operation_body(args, AskRequest)
        request = _answer(ask_body, RuntimeRequestOperation.ASK)
        snapshot = service.ask(
            request,
            idempotency_key=args.idempotency_key or ask_body.context.request_id,
        )
    elif command == "research":
        research_body = _operation_body(args, ResearchRequest)
        request = _answer(research_body, RuntimeRequestOperation.RESEARCH)
        snapshot = service.research(
            request,
            idempotency_key=args.idempotency_key or research_body.context.request_id,
        )
    else:
        run_body = _operation_body(args, RunRequest)
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
        snapshot = service.run(
            request,
            idempotency_key=args.idempotency_key or run_body.context.request_id,
        )
    if args.wait:
        snapshot = service.wait(
            snapshot.job_id,
            timeout_seconds=args.wait_timeout_seconds,
        )
    _write(job_status(snapshot).model_dump(mode="json"))
    return 0


def _operation_body(args: argparse.Namespace, model_type: type[ModelT]) -> ModelT:
    request_path = getattr(args, "request", None)
    if request_path is not None:
        return _load_model(Path(request_path), model_type)
    return model_type.model_validate(_direct_operation_payload(args))


def _direct_operation_payload(args: argparse.Namespace) -> dict[str, object]:
    command = "retrieve" if args.v2_command == "search" else args.v2_command
    common: dict[str, object] = {
        "budget": _budget_payload(args),
        "context": _context_payload(args),
        "execution_profile": args.profile,
        "scope": args.scope,
    }
    if command == "ingest":
        return {
            **common,
            "source_directory": str(
                Path(_required(args.source_directory, "source directory")).resolve()
            ),
        }
    if command == "index":
        return {
            **common,
            "corpus_id": _required(args.corpus_id, "corpus identity"),
        }
    filters = {
        "document_ids": args.document_id,
        "source_uris": args.source_uri,
    }
    if command == "retrieve":
        return {
            **common,
            "filters": filters,
            "index_id": _required(args.index_id, "index identity"),
            "query": _required(args.query, "query"),
            "top_k": args.top_k,
        }
    answer_policy = {
        "permit_insufficient_answer": True,
        "provider": args.provider,
        "publish": True,
        "require_citations": True,
    }
    if command in {"ask", "research"}:
        return {
            **common,
            "answer_policy": answer_policy,
            "corpus_id": _required(args.corpus_id, "corpus identity"),
            "filters": filters,
            "index_id": _required(args.index_id, "index identity"),
            "query": _required(args.query, "query"),
            "top_k": args.top_k,
        }
    source_directory = args.source_directory
    corpus_id = args.corpus_id
    if (source_directory is None) == (corpus_id is None):
        raise ValueError(
            "run requires exactly one of --source-directory or --corpus-id"
        )
    return {
        **common,
        "answer_policy": answer_policy,
        "corpus_id": corpus_id,
        "filters": filters,
        "query": _required(args.query, "query"),
        "source_directory": (
            None if source_directory is None else str(Path(source_directory).resolve())
        ),
        "top_k": args.top_k,
    }


def _context_payload(args: argparse.Namespace) -> dict[str, str]:
    request_id = args.request_id or f"request-{uuid.uuid4().hex}"
    correlation_id = args.correlation_id or f"correlation-{uuid.uuid4().hex}"
    args.correlation_id = correlation_id
    return {
        "contract_version": "v2",
        "correlation_id": correlation_id,
        "replay_mode": "strict",
        "request_id": request_id,
    }


def _budget_payload(args: argparse.Namespace) -> dict[str, object]:
    return {
        "max_artifact_bytes": args.max_artifact_bytes,
        "max_provider_tokens": args.max_provider_tokens,
        "max_steps": args.max_steps,
        "timeout_seconds": args.operation_timeout_seconds,
    }


def _required(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"direct command requires {label} or --request JSON")
    return value


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
    if args.request is not None:
        body = _load_model(Path(args.request), ReplayRequest)
    else:
        body = ReplayRequest.model_validate(
            {
                "context": _context_payload(args),
                "network_policy": args.network_policy,
                "process_id": args.process_id,
                "provider_allowlist": args.provider_allowlist,
                "source_attempt_id": _required(
                    args.source_attempt_id, "source attempt identity"
                ),
                "timeout_seconds": args.job_timeout_seconds,
            }
        )
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
        idempotency_key=args.idempotency_key or body.context.request_id,
        timeout_seconds=body.timeout_seconds,
    )
    if args.wait:
        snapshot = service.wait(
            snapshot.job_id,
            timeout_seconds=args.wait_timeout_seconds,
        )
    _write(job_status(snapshot).model_dump(mode="json"))
    return 0


def _compare(args: argparse.Namespace, service: RuntimeApplicationServicesV2) -> int:
    if args.request is not None:
        body = _load_model(Path(args.request), CompareRequest)
    else:
        body = CompareRequest.model_validate(
            {
                "baseline_attempt_id": _required(
                    args.baseline_attempt_id, "baseline attempt identity"
                ),
                "baseline_run_id": _required(
                    args.baseline_run_id, "baseline run identity"
                ),
                "candidate_attempt_id": _required(
                    args.candidate_attempt_id, "candidate attempt identity"
                ),
                "candidate_run_id": _required(
                    args.candidate_run_id, "candidate run identity"
                ),
                "context": _context_payload(args),
                "cursor": args.cursor,
                "dimensions": args.dimension or ["outcome", "claims", "citations"],
                "limit": args.limit,
            }
        )
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


def _cancel_body(args: argparse.Namespace) -> CancelRequest:
    if args.request is not None:
        return _load_model(Path(args.request), CancelRequest)
    return CancelRequest.model_validate(
        {
            "context": _context_payload(args),
            "reason": args.reason,
        }
    )


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


def _write_capabilities_human(report: RuntimeCapabilityDiscovery) -> None:
    record = report.record()
    print(f"Configuration: {report.configuration['identity_sha256']}")
    print(
        "Configuration sources: "
        + json.dumps(report.configuration["origins"], sort_keys=True)
    )
    print(
        f"Workspace: {report.workspace.status} {report.workspace.workspace_id or '-'}"
    )
    print(f"Model: {report.model.status} {report.model.model_lock_artifact_id or '-'}")
    print(f"Index: {report.index.status} {report.index.generation_id or '-'}")
    print("Operations: " + ", ".join(report.operations))
    print(
        "Parsers: "
        + ", ".join(
            f"{parser.format_id}={parser.disposition}" for parser in report.parsers
        )
    )
    print(
        "Providers: " + ", ".join(provider.provider_id for provider in report.providers)
    )
    print(
        "Readiness: "
        + ", ".join(
            f"{readiness.capability.value}={readiness.status}"
            for readiness in report.readiness
        )
    )
    print(
        "Installed distributions: "
        + ", ".join(
            f"{item.name}={item.version}" for item in report.installed_distributions
        )
    )
    print("Discovery record: " + json.dumps(record, sort_keys=True))


def _write_retrieval_evaluation_human(
    report: RuntimeRetrievalEvaluationReport,
) -> None:
    metrics = {item.metric_id: item for item in report.macro.metrics}
    print(f"Queries: {report.query_count}")
    print(f"Reviewed qrels: {report.qrel_count}")
    print(f"Generation: {', '.join(report.generation_ids)}")
    print(f"Model: {', '.join(report.model_lock_artifact_ids)}")
    print(f"Configuration: {', '.join(report.configuration_ids)}")
    print(
        "Macro metrics: "
        f"Recall@5={metrics['recall-at-5'].value:.6f}, "
        f"MRR@10={metrics['mrr-at-10'].value:.6f}, "
        f"nDCG@10={metrics['ndcg-at-10'].value:.6f}"
    )
    print(
        "Pooled evidence: "
        f"{report.micro.retrieved_relevant_at_5}/"
        f"{report.micro.relevant_qrels} relevant qrels at 5; "
        f"refused={report.micro.refused_queries}; failed={report.micro.failed_queries}"
    )
    print(
        "Relevant-evidence outcomes: "
        + ", ".join(
            f"{disposition}={count}"
            for disposition, count in report.stage_analysis.disposition_counts
        )
    )
    print(
        "Stage recall: "
        + ", ".join(
            f"{item.stage_id}={item.numerator}/{item.denominator} ({item.value:.6f})"
            for item in report.stage_analysis.recall
        )
    )
    for query in report.stage_analysis.queries:
        losses = ", ".join(
            f"{item.qrel_id}={item.disposition.value}"
            f"(L{item.lexical_source_rank or '-'}"
            f"/D{item.dense_rank or '-'}"
            f"/F{item.fusion_rank or '-'}"
            f"/R{item.final_rank or '-'})"
            for item in query.relevant_evidence
        )
        print(
            f"Stage {query.query_id}: "
            f"lexical={query.lexical_included_count}/"
            f"{query.lexical_observed_count}; "
            f"dense={query.dense_observed_count}; fusion={query.fusion_count}; "
            f"final={query.final_count}; {losses}"
        )
    print("Worst queries: " + ", ".join(report.worst_query_ids))
    print(f"Evidence: {report.evidence_sha256}")


def _write_configuration_search_human(
    report: RuntimeRetrievalConfigurationSearchReport,
) -> None:
    ranked = sorted(
        report.results,
        key=lambda result: (
            -sum(metric.value for metric in result.metrics.metrics),
            result.configuration.configuration_id,
        ),
    )
    print(f"Queries: {report.query_count}")
    print(f"Reviewed qrels: {report.qrel_count}")
    print(f"Configurations: {len(report.results)}")
    print(f"Selected: {report.selected_configuration_id or 'none'}")
    for result in ranked[:10]:
        metrics = {item.metric_id: item.value for item in result.metrics.metrics}
        print(
            f"Configuration {result.configuration.configuration_id}: "
            f"{retrieval_configuration_summary(result.configuration)}; "
            f"Recall@5={metrics['recall-at-5']:.6f}, "
            f"MRR@10={metrics['mrr-at-10']:.6f}, "
            f"nDCG@10={metrics['ndcg-at-10']:.6f}; "
            f"failed={','.join(result.failed_metrics) or 'none'}"
        )
    best = ranked[0]
    for query in best.metrics.queries:
        print(
            f"Best tradeoff {query.query_id}: "
            f"Recall@5={query.recall_at_5:.6f}, "
            f"MRR@10={query.reciprocal_rank_at_10:.6f}, "
            f"nDCG@10={query.ndcg_at_10:.6f}"
        )
    print(f"Evidence: {report.evidence_sha256}")


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
