# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Thin HTTP transport for immutable index-generation operations."""

from __future__ import annotations

from typing import NoReturn

from fastapi import FastAPI, HTTPException

from bijux_canon_index.api.v1.runtime import generation_service
from bijux_canon_index.interfaces.schemas.index_generations import (
    IndexActivationRequestPayload,
    IndexBuildRequestPayload,
    IndexInspectionResponse,
    IndexQueryRequestPayload,
    IndexQueryResponse,
    IndexSelectionPayload,
)


def _raise_transport_error(error: Exception) -> NoReturn:
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    if isinstance(error, FileNotFoundError):
        raise HTTPException(status_code=404, detail="index generation not found") from error
    if isinstance(error, RuntimeError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=500, detail="internal error") from error


def register_index_generation_routes(app: FastAPI) -> None:
    """Register generation routes backed only by the canonical application service."""

    @app.post(
        "/index/generations/build",
        tags=["Materialization"],
        operation_id="buildIndexGeneration",
        response_model=IndexInspectionResponse,
    )
    def build_generation(request: IndexBuildRequestPayload) -> IndexInspectionResponse:
        try:
            report = generation_service().build(
                (chunk.to_domain() for chunk in request.chunks),
                snapshot_artifact_id=request.snapshot_artifact_id,
                model_lock_artifact_id=request.model_lock_artifact_id,
                limits=request.limits.to_domain(),
                hnsw_parameters=request.hnsw_parameters.to_domain(),
                activate=request.activate,
            )
            return IndexInspectionResponse.from_report(report)
        except Exception as error:
            _raise_transport_error(error)

    @app.post(
        "/index/generations/activate",
        tags=["Materialization"],
        operation_id="activateIndexGeneration",
        response_model=IndexInspectionResponse,
    )
    def activate_generation(
        request: IndexActivationRequestPayload,
    ) -> IndexInspectionResponse:
        try:
            return IndexInspectionResponse.from_report(
                generation_service().activate(request.generation_id)
            )
        except Exception as error:
            _raise_transport_error(error)

    @app.post(
        "/index/generations/inspect",
        tags=["Discovery"],
        operation_id="inspectIndexGeneration",
        response_model=IndexInspectionResponse,
    )
    def inspect_generation(request: IndexSelectionPayload) -> IndexInspectionResponse:
        try:
            return IndexInspectionResponse.from_report(
                generation_service().inspect(request.generation_id)
            )
        except Exception as error:
            _raise_transport_error(error)

    @app.post(
        "/index/generations/verify",
        tags=["Discovery"],
        operation_id="verifyIndexGeneration",
        response_model=IndexInspectionResponse,
    )
    def verify_generation(request: IndexSelectionPayload) -> IndexInspectionResponse:
        try:
            return IndexInspectionResponse.from_report(
                generation_service().verify(request.generation_id)
            )
        except Exception as error:
            _raise_transport_error(error)

    @app.post(
        "/index/generations/query",
        tags=["Execution"],
        operation_id="queryIndexGeneration",
        response_model=IndexQueryResponse,
    )
    def query_generation(request: IndexQueryRequestPayload) -> IndexQueryResponse:
        try:
            report = generation_service().query(
                request.to_domain(),
                generation_id=request.generation_id,
            )
            return IndexQueryResponse.from_report(report)
        except Exception as error:
            _raise_transport_error(error)


__all__ = ["register_index_generation_routes"]
