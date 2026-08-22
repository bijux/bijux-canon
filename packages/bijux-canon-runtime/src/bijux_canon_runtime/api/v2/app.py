# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Thin FastAPI v2 adapter over the shared Runtime application service."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Body, Depends, FastAPI, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

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
    CorpusInspectionResponse,
    IndexInspectionResponse,
    JobResultResponse,
    JobStatusResponse,
    PrepareCorpusRequest,
    ProblemDetail,
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
from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    RuntimeReplayPolicy,
)

SUPPORTED_VERSION = "v2"
PROBLEM_RESPONSES = {
    400: {"model": ProblemDetail, "description": "Invalid typed request."},
    404: {"model": ProblemDetail, "description": "Resource not found."},
    406: {"model": ProblemDetail, "description": "Unsupported API version."},
    409: {"model": ProblemDetail, "description": "Immutable state conflict."},
    500: {"model": ProblemDetail, "description": "Application operation failed."},
    503: {"model": ProblemDetail, "description": "Application service unavailable."},
}


def _problem(
    *,
    status_code: int,
    code: str,
    title: str,
    remediation: str,
    correlation_id: str = "correlation-unavailable",
    retryable: bool = False,
    cause: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ProblemDetail(
        type=f"https://bijux.org/problems/runtime/{code}",
        title=title,
        status=status_code,
        code=code,
        correlation_id=correlation_id,
        retryable=retryable,
        remediation=remediation,
        cause=cause,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        media_type="application/problem+json",
        headers=headers,
    )


def create_app(
    services: RuntimeApplicationServicesV2 | None = None,
) -> FastAPI:
    """Create an isolated v2 adapter with explicit application composition."""
    api = FastAPI(
        title="bijux-canon-runtime API",
        summary="Typed application operations for durable Bijux Canon workflows.",
        version=SUPPORTED_VERSION,
        openapi_version="3.1.0",
        contact={"name": "Bijux", "url": "https://github.com/bijux/bijux-canon"},
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
    )
    api.state.application_services = services

    def application_services(request: Request) -> RuntimeApplicationServicesV2:
        configured = request.app.state.application_services
        if configured is None:
            raise ApplicationCapabilityError(
                "runtime application services are not configured"
            )
        if not isinstance(configured, RuntimeApplicationServicesV2):
            raise TypeError("runtime application service has the wrong version")
        return configured

    def require_version(
        bijux_api_version: Annotated[
            str | None,
            Header(alias="Bijux-API-Version"),
        ] = None,
    ) -> None:
        if bijux_api_version != SUPPORTED_VERSION:
            raise _UnsupportedVersion

    @api.middleware("http")
    async def supported_version_header(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Bijux-API-Supported-Versions"] = SUPPORTED_VERSION
        return response

    @api.exception_handler(_UnsupportedVersion)
    def unsupported_version(_: Request, __: _UnsupportedVersion) -> JSONResponse:
        return _problem(
            status_code=406,
            code="unsupported-version",
            title="Unsupported API version",
            remediation="Send Bijux-API-Version: v2.",
            headers={"Bijux-API-Supported-Versions": SUPPORTED_VERSION},
        )

    @api.exception_handler(RequestValidationError)
    def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            status_code=400,
            code="invalid-request",
            title="Request validation failed",
            remediation="Correct the fields identified by the v2 request schema.",
            cause=exc.errors()[0]["type"] if exc.errors() else None,
        )

    @api.exception_handler(KeyError)
    def not_found(_: Request, exc: KeyError) -> JSONResponse:
        return _problem(
            status_code=404,
            code="not-found",
            title="Runtime resource not found",
            remediation="Use an identity returned by this configured Runtime store.",
            cause=str(exc),
        )

    @api.exception_handler(ValueError)
    def invalid_value(_: Request, exc: ValueError) -> JSONResponse:
        return _problem(
            status_code=400,
            code="invalid-request",
            title="Application request is invalid",
            remediation="Correct the request without changing its idempotency key.",
            cause=str(exc),
        )

    @api.exception_handler(DurableJobError)
    def job_conflict(_: Request, exc: DurableJobError) -> JSONResponse:
        return _problem(
            status_code=409,
            code="conflict",
            title="Durable job state conflicts with the request",
            remediation="Inspect the existing job before retrying.",
            cause=str(exc),
        )

    @api.exception_handler(ApplicationCapabilityError)
    def unavailable(_: Request, exc: ApplicationCapabilityError) -> JSONResponse:
        return _problem(
            status_code=503,
            code="missing-capability",
            title="Runtime application service is unavailable",
            remediation="Configure the v2 application service composition.",
            retryable=True,
            cause=str(exc),
        )

    @api.exception_handler(RuntimeError)
    def operation_failed(_: Request, exc: RuntimeError) -> JSONResponse:
        return _problem(
            status_code=500,
            code="operation-failed",
            title="Runtime application operation failed",
            remediation="Inspect persisted evidence and retry.",
            retryable=True,
            cause=str(exc),
        )

    Version = Annotated[None, Depends(require_version)]
    Services = Annotated[RuntimeApplicationServicesV2, Depends(application_services)]
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
    ) -> IndexInspectionResponse:
        return IndexInspectionResponse.model_validate(
            service.inspect_index(ArtifactID(index_id))
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
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> dict[str, object]:
        inspection = json_value(service.inspect(run_id, attempt_id=attempt_id))
        assert isinstance(inspection, dict)
        return _paginate_inspection(inspection, offset=offset, limit=limit)

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
        return json_value(
            service.compare(
                baseline_run_id=body.baseline_run_id,
                baseline_attempt_id=body.baseline_attempt_id,
                candidate_run_id=body.candidate_run_id,
                candidate_attempt_id=body.candidate_attempt_id,
                policy=policy,
            )
        )

    return api


class _UnsupportedVersion(Exception):
    pass


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


def _paginate_inspection(
    inspection: dict[str, object],
    *,
    offset: int,
    limit: int,
) -> dict[str, object]:
    result = dict(inspection)
    for field in ("steps", "artifacts", "events"):
        values = result.get(field)
        if isinstance(values, list):
            result[field] = values[offset : offset + limit]
    result["page"] = {
        "limit": limit,
        "next_offset": offset + limit if _has_more(inspection, offset, limit) else None,
        "offset": offset,
    }
    return result


def _has_more(inspection: dict[str, object], offset: int, limit: int) -> bool:
    for field in ("steps", "artifacts", "events"):
        values = inspection.get(field)
        if isinstance(values, list) and len(values) > offset + limit:
            return True
    return False


app = create_app()

__all__ = ["app", "create_app"]
