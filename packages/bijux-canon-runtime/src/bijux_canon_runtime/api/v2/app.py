# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Thin FastAPI v2 adapter over the shared Runtime application service."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
import os
from pathlib import Path
import threading
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

from bijux_canon_runtime.api.v2.conversion import (
    job_status,
    operation_request,
)
from bijux_canon_runtime.api.v2.schemas import (
    AskRequest,
    BuildIndexRequest,
    CancelRequest,
    CompareRequest,
    CorpusInspectionResponse,
    IndexInspectionResponse,
    JobResultResponse,
    JobStatusResponse,
    LivenessResponse,
    PrepareCorpusRequest,
    ProblemDetail,
    ReadinessResponse,
    ReplayRequest,
    ResearchRequest,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
    RetrieveRequest,
    RunRequest,
    RuntimeCapabilityDiscoveryResponse,
)
from bijux_canon_runtime.application.capability_discovery import (
    RuntimeCapabilityDiscoveryService,
)
from bijux_canon_runtime.application.operations import (
    ApplicationCapabilityError,
    ReplayOperationRequest,
    RuntimeApplicationServicesV2,
    RuntimeRetrievalEvaluationInput,
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
from bijux_canon_runtime.model.execution.request_plan import ExecutionProfile
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    resolve_runtime_configuration,
)
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
from bijux_canon_runtime.runtime.execution.application_composition import (
    compose_runtime_application_services,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobError
from bijux_canon_runtime.runtime.pagination import PageRequest
from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    RuntimeReplayPolicy,
)

SUPPORTED_VERSION = "v2"


def _problem_response(description: str) -> dict[str, Any]:
    return {
        "model": ProblemDetail,
        "description": description,
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
            }
        },
    }


PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: _problem_response("Invalid typed request."),
    404: _problem_response("Resource not found."),
    406: _problem_response("Unsupported API version."),
    409: _problem_response("Immutable state conflict."),
    500: _problem_response("Application operation failed."),
    503: _problem_response("Application service unavailable."),
}


class RuntimeV2FastAPI(FastAPI):
    """FastAPI application with an explicit unauthenticated OpenAPI posture."""

    def openapi(self) -> dict[str, Any]:
        schema = super().openapi()
        schema["security"] = []
        return schema


def _problem(
    *,
    code: RuntimeProblemCode,
    correlation_id: str | None = None,
    run_id: str | None = None,
    cause: object | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = runtime_problem(
        code,
        correlation_id=correlation_id,
        run_id=run_id,
        cause=cause,
    )
    payload = ProblemDetail.model_validate(runtime_problem_fields(problem))
    return JSONResponse(
        status_code=problem.status,
        content=payload.model_dump(mode="json"),
        media_type="application/problem+json",
        headers=headers,
    )


def create_app(
    services: RuntimeApplicationServicesV2 | None = None,
    readiness: RuntimeReadinessService | None = None,
    discovery: RuntimeCapabilityDiscoveryService | None = None,
    configuration: RuntimeConfiguration | None = None,
) -> FastAPI:
    """Create an isolated v2 adapter with explicit application composition."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            configured = application.state.application_services
            if services is None and isinstance(
                configured, RuntimeApplicationServicesV2
            ):
                configured.close()
                application.state.application_services = None

    api = RuntimeV2FastAPI(
        title="bijux-canon-runtime API",
        summary="Typed application operations for durable Bijux Canon workflows.",
        version=SUPPORTED_VERSION,
        openapi_version="3.1.0",
        contact={"name": "Bijux", "url": "https://github.com/bijux/bijux-canon"},
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
        servers=[{"url": "/"}],
        lifespan=lifespan,
    )
    api.state.application_services = services
    api.state.application_services_lock = threading.Lock()
    api.state.readiness_service = readiness
    api.state.capability_discovery_service = discovery
    api.state.runtime_configuration = configuration
    api.state.runtime_configuration_lock = threading.Lock()

    def effective_configuration(request: Request) -> RuntimeConfiguration:
        configured = request.app.state.runtime_configuration
        if configured is None:
            with request.app.state.runtime_configuration_lock:
                configured = request.app.state.runtime_configuration
                if configured is None:
                    configured = resolve_runtime_configuration(environment=os.environ)
                    request.app.state.runtime_configuration = configured
        if not isinstance(configured, RuntimeConfiguration):
            raise TypeError("runtime configuration has the wrong version")
        return configured

    def application_services(request: Request) -> RuntimeApplicationServicesV2:
        configured = request.app.state.application_services
        if configured is None:
            runtime_configuration = effective_configuration(request)
            with request.app.state.application_services_lock:
                configured = request.app.state.application_services
                if configured is None:
                    configured = compose_runtime_application_services(
                        configuration=runtime_configuration,
                    )
                    request.app.state.application_services = configured
        if not isinstance(configured, RuntimeApplicationServicesV2):
            raise TypeError("runtime application service has the wrong version")
        return configured

    async def require_version(
        request: Request,
        bijux_api_version: Annotated[
            str | None,
            Header(alias="Bijux-API-Version"),
        ] = None,
        correlation_id: Annotated[
            str | None,
            Header(alias="X-Correlation-ID", pattern=r"^[A-Za-z0-9._:-]{1,200}$"),
        ] = None,
    ) -> None:
        request.state.correlation_id = correlation_id or await _body_correlation_id(
            request
        )
        if bijux_api_version != SUPPORTED_VERSION:
            raise _UnsupportedVersion

    def readiness_service(request: Request) -> RuntimeReadinessService:
        configured = request.app.state.readiness_service
        if configured is not None:
            if not isinstance(configured, RuntimeReadinessService):
                raise TypeError("runtime readiness service has the wrong version")
            return configured
        return RuntimeReadinessService(
            effective_configuration(request),
            environment=os.environ,
        )

    def capability_discovery_service(
        request: Request,
    ) -> RuntimeCapabilityDiscoveryService:
        configured = request.app.state.capability_discovery_service
        if configured is not None:
            if not isinstance(configured, RuntimeCapabilityDiscoveryService):
                raise TypeError("runtime capability discovery has the wrong version")
            return configured
        return RuntimeCapabilityDiscoveryService(
            effective_configuration(request),
            environment=os.environ,
        )

    @api.middleware("http")
    async def supported_version_header(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Bijux-API-Supported-Versions"] = SUPPORTED_VERSION
        return response

    @api.exception_handler(_UnsupportedVersion)
    def unsupported_version(request: Request, __: _UnsupportedVersion) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.UNSUPPORTED_VERSION,
            correlation_id=_correlation_id(request),
            headers={"Bijux-API-Supported-Versions": SUPPORTED_VERSION},
        )

    @api.exception_handler(RequestValidationError)
    def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.INVALID_REQUEST,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=exc.errors()[0]["type"] if exc.errors() else None,
        )

    @api.exception_handler(KeyError)
    def not_found(request: Request, exc: KeyError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.NOT_FOUND,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=str(exc),
        )

    @api.exception_handler(ValueError)
    def invalid_value(request: Request, exc: ValueError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.INVALID_REQUEST,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=str(exc),
        )

    @api.exception_handler(DurableJobError)
    def job_conflict(request: Request, exc: DurableJobError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.CONFLICT,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=str(exc),
        )

    @api.exception_handler(ApplicationCapabilityError)
    def unavailable(request: Request, exc: ApplicationCapabilityError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.MISSING_CAPABILITY,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=str(exc),
        )

    @api.exception_handler(RuntimeError)
    def operation_failed(request: Request, exc: RuntimeError) -> JSONResponse:
        return _problem(
            code=RuntimeProblemCode.OPERATION_FAILED,
            correlation_id=_correlation_id(request),
            run_id=request.path_params.get("run_id"),
            cause=str(exc),
        )

    Version = Annotated[None, Depends(require_version)]
    Services = Annotated[RuntimeApplicationServicesV2, Depends(application_services)]
    Readiness = Annotated[RuntimeReadinessService, Depends(readiness_service)]
    Discovery = Annotated[
        RuntimeCapabilityDiscoveryService,
        Depends(capability_discovery_service),
    ]

    @api.get("/api/v2/live", response_model=LivenessResponse)
    def live(_: Version) -> LivenessResponse:
        return LivenessResponse.model_validate(asdict(runtime_liveness()))

    @api.get(
        "/api/v2/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse, "description": "Degraded."}},
    )
    def ready(
        _: Version,
        readiness_service: Readiness,
        operation: Annotated[ReadinessCapability, Query()] = (
            ReadinessCapability.INITIALIZED
        ),
        profile: Annotated[ExecutionProfile | None, Query()] = None,
    ) -> JSONResponse:
        report = readiness_service.evaluate(operation, execution_profile=profile)
        payload = ReadinessResponse.model_validate(asdict(report)).model_dump(
            mode="json"
        )
        return JSONResponse(status_code=200 if report.ready else 503, content=payload)

    @api.get(
        "/api/v2/capabilities",
        response_model=RuntimeCapabilityDiscoveryResponse,
    )
    def capabilities(
        _: Version,
        capability_discovery: Discovery,
    ) -> RuntimeCapabilityDiscoveryResponse:
        return RuntimeCapabilityDiscoveryResponse.model_validate(
            capability_discovery.inspect().record()
        )

    Idempotency = Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=16, max_length=200),
    ]

    @api.post(
        "/api/v2/corpora/prepare",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def prepare_corpus(
        body: Annotated[PrepareCorpusRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = operation_request(
            context=body.context,
            operation=RuntimeRequestOperation.CORPUS_PREPARE,
            execution_profile=body.execution_profile,
            budget=body.budget,
            scope=body.scope,
            source_directory=body.source_directory,
        )
        return job_status(service.corpus(request, idempotency_key=idempotency_key))

    @api.post(
        "/api/v2/indexes/build",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def build_index(
        body: Annotated[BuildIndexRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = operation_request(
            context=body.context,
            operation=RuntimeRequestOperation.INDEX_BUILD,
            execution_profile=body.execution_profile,
            budget=body.budget,
            scope=body.scope,
            corpus_id=body.corpus_id,
        )
        return job_status(service.index(request, idempotency_key=idempotency_key))

    @api.get(
        "/api/v2/corpora/{corpus_id}",
        response_model=CorpusInspectionResponse,
        responses=PROBLEM_RESPONSES,
    )
    def inspect_corpus(
        corpus_id: str,
        _: Version,
        service: Services,
    ) -> CorpusInspectionResponse:
        return CorpusInspectionResponse.model_validate(
            service.inspect_corpus(ArtifactID(corpus_id))
        )

    @api.get(
        "/api/v2/indexes/{index_id}",
        response_model=IndexInspectionResponse,
        responses=PROBLEM_RESPONSES,
    )
    def inspect_index(
        index_id: str,
        _: Version,
        service: Services,
        cursor: str | None = Query(default=None, min_length=1, max_length=4096),
        offset: Annotated[int | None, Query(ge=0)] = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> IndexInspectionResponse:
        return IndexInspectionResponse.model_validate(
            service.inspect_index_page(
                ArtifactID(index_id),
                page=PageRequest(limit=limit, cursor=cursor, offset=offset),
            )
        )

    @api.post(
        "/api/v2/retrieval-evaluations",
        response_model=RetrievalEvaluationResponse,
        responses=PROBLEM_RESPONSES,
    )
    def evaluate_retrieval(
        body: Annotated[RetrievalEvaluationRequest, Body(...)],
        _: Version,
        service: Services,
    ) -> RetrievalEvaluationResponse:
        parameters = RuntimeRetrievalEvaluationInput(
            cases_path=Path(body.cases_path).resolve(),
            qrels_path=Path(body.qrels_path).resolve(),
            index_artifact_id=body.index_id,
            split=body.split,
            mode=body.mode,
            top_k=body.top_k,
        )
        return RetrievalEvaluationResponse.model_validate(
            service.evaluate_reviewed_retrieval(parameters).manifest()
        )

    @api.post(
        "/api/v2/retrievals",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def retrieve(
        body: Annotated[RetrieveRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = _retrieval_request(body, RuntimeRequestOperation.RETRIEVE)
        return job_status(service.retrieve(request, idempotency_key=idempotency_key))

    @api.post(
        "/api/v2/answers",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def ask(
        body: Annotated[AskRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = _answer_request(body, RuntimeRequestOperation.ASK)
        return job_status(service.ask(request, idempotency_key=idempotency_key))

    @api.post(
        "/api/v2/research",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def research(
        body: Annotated[ResearchRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = _answer_request(body, RuntimeRequestOperation.RESEARCH)
        return job_status(service.research(request, idempotency_key=idempotency_key))

    @api.post(
        "/api/v2/runs",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def run(
        body: Annotated[RunRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        request = operation_request(
            context=body.context,
            operation=RuntimeRequestOperation.RUN,
            execution_profile=body.execution_profile,
            budget=body.budget,
            scope=body.scope,
            query=body.query,
            source_directory=body.source_directory,
            corpus_id=body.corpus_id,
            filters=(body.filters.document_ids, body.filters.source_uris),
            top_k=body.top_k,
            answer_policy=body.answer_policy,
        )
        return job_status(service.run(request, idempotency_key=idempotency_key))

    @api.post(
        "/api/v2/runs/{run_id}/replays",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def replay(
        run_id: str,
        body: Annotated[ReplayRequest, Body(...)],
        idempotency_key: Idempotency,
        _: Version,
        service: Services,
    ) -> JobStatusResponse:
        replay_request = ReplayOperationRequest(
            run_id=run_id,
            source_attempt_id=body.source_attempt_id,
            request_id=RequestID(body.context.request_id),
            process_id=body.process_id,
            policy=RuntimeReplayPolicy(
                replay_mode=ReplayMode(body.context.replay_mode),
                network_policy=ReplayNetworkPolicy(body.network_policy),
                provider_allowlist=body.provider_allowlist,
            ),
        )
        return job_status(
            service.replay(
                replay_request,
                idempotency_key=idempotency_key,
                timeout_seconds=body.timeout_seconds,
            )
        )

    @api.get(
        "/api/v2/jobs/{job_id}",
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def inspect_job(job_id: str, _: Version, service: Services) -> JobStatusResponse:
        return job_status(service.status(job_id))

    @api.get(
        "/api/v2/jobs/{job_id}/result",
        response_model=JobResultResponse,
        responses=PROBLEM_RESPONSES,
    )
    def job_result(job_id: str, _: Version, service: Services) -> JobResultResponse:
        return JobResultResponse(
            schema_version="bijux.runtime.http-job-result.v2",
            job_id=job_id,
            result=service.result(job_id),
        )

    @api.post(
        "/api/v2/jobs/{job_id}/cancellation",
        status_code=202,
        response_model=JobStatusResponse,
        responses=PROBLEM_RESPONSES,
    )
    def cancel_job(
        job_id: str,
        _: Version,
        body: Annotated[CancelRequest, Body(...)],
        idempotency_key: Idempotency,
        service: Services,
    ) -> JobStatusResponse:
        del body, idempotency_key
        return job_status(service.cancel(job_id))

    @api.get("/api/v2/runs/{run_id}", responses=PROBLEM_RESPONSES)
    def inspect_run(
        run_id: str,
        _: Version,
        service: Services,
        attempt_id: str | None = Query(default=None),
        cursor: str | None = Query(default=None, min_length=1, max_length=4096),
        offset: Annotated[int | None, Query(ge=0)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 5,
    ) -> dict[str, object]:
        return dict(
            service.inspect_page(
                run_id,
                attempt_id=attempt_id,
                page=PageRequest(limit=limit, cursor=cursor, offset=offset),
            )
        )

    @api.get(
        "/api/v2/artifacts/{artifact_id}/payload",
        responses=PROBLEM_RESPONSES,
    )
    def artifact_payload(
        artifact_id: str,
        _: Version,
        service: Services,
        offset: Annotated[int, Query(ge=0)] = 0,
        max_bytes: Annotated[int, Query(ge=1, le=65536)] = 65536,
    ) -> dict[str, object]:
        return dict(
            service.read_artifact_payload_page(
                ArtifactID(artifact_id),
                offset=offset,
                max_bytes=max_bytes,
            )
        )

    @api.post("/api/v2/comparisons", responses=PROBLEM_RESPONSES)
    def compare(
        body: Annotated[CompareRequest, Body(...)],
        _: Version,
        service: Services,
    ) -> object:
        policy = RuntimeComparisonPolicy(
            dimensions=tuple(ComparisonDimension(item) for item in body.dimensions),
            expected_differences=tuple(
                item
                for item in (
                    ComparisonDimension.TIMING,
                    ComparisonDimension.POLICY,
                )
                if item in body.dimensions
            ),
        )
        return service.compare_page(
            baseline_run_id=body.baseline_run_id,
            baseline_attempt_id=body.baseline_attempt_id,
            candidate_run_id=body.candidate_run_id,
            candidate_attempt_id=body.candidate_attempt_id,
            page=PageRequest(limit=body.limit, cursor=body.cursor),
            policy=policy,
        )

    return api


class _UnsupportedVersion(Exception):
    pass


def _correlation_id(request: Request) -> str | None:
    value = getattr(request.state, "correlation_id", None)
    if isinstance(value, str):
        return value
    header = request.headers.get("X-Correlation-ID")
    return header if isinstance(header, str) else None


async def _body_correlation_id(request: Request) -> str | None:
    raw_length = request.headers.get("content-length")
    try:
        length = int(raw_length) if raw_length is not None else None
    except ValueError:
        return None
    if length is None or not 0 < length <= 1_048_576:
        return None
    try:
        payload = await request.json()
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    context = payload.get("context")
    if not isinstance(context, dict):
        return None
    correlation_id = context.get("correlation_id")
    return correlation_id if isinstance(correlation_id, str) else None


def _retrieval_request(
    body: RetrieveRequest,
    operation: RuntimeRequestOperation,
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


def _answer_request(
    body: AskRequest,
    operation: RuntimeRequestOperation,
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


app = create_app()

__all__ = ["app", "create_app"]
