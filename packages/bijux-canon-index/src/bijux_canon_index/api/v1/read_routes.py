# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Header, Response

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.schemas.api_responses import (
    ListArtifactsResponse,
    ListRunsResponse,
)
from bijux_canon_index.interfaces.schemas.reports import (
    BackendCapabilitiesReport,
)


def register_read_routes(app: FastAPI) -> None:
    @app.get(
        "/capabilities",
        tags=["Discovery"],
        summary="Describe backend capabilities",
        description=(
            "Report the active execution backend, supported contracts, storage backends, "
            "vector store capabilities, and ANN readiness in one envelope."
        ),
        operation_id="describeBackendCapabilities",
        response_model=BackendCapabilitiesReport,
        responses={
            200: {
                "description": "Capability report returned successfully.",
                "content": {
                    "application/json": {
                        "examples": {
                            "capabilities": {
                                "value": {
                                    "backend": "sqlite",
                                    "contracts": ["deterministic", "non_deterministic"],
                                    "deterministic_query": True,
                                    "supports_ann": False,
                                    "replayable": True,
                                    "metrics": ["l2", "cosine"],
                                    "max_vector_size": 4096,
                                    "isolation_level": "read_committed",
                                    "execution_modes": [
                                        "strict",
                                        "bounded",
                                        "exploratory",
                                    ],
                                    "ann_status": "unavailable",
                                    "storage_backends": [],
                                    "vector_stores": [],
                                    "plugins": {},
                                }
                            }
                        }
                    }
                },
            }
        },
    )  # type: ignore[untyped-decorator]
    def capabilities(
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> BackendCapabilitiesReport:
        engine = VectorExecutionEngine()
        if correlation_id:
            response.headers["X-Correlation-Id"] = correlation_id
        return cast(
            BackendCapabilitiesReport,
            BackendCapabilitiesReport.model_validate(engine.capabilities()),
        )

    @app.get(
        "/artifacts",
        tags=["Discovery"],
        summary="List execution artifacts",
        description=(
            "Return artifact identifiers known to the current backend so operators can "
            "inspect or reuse previously materialized execution state."
        ),
        operation_id="listExecutionArtifacts",
        response_model=ListArtifactsResponse,
        responses={
            200: {
                "description": "Artifact inventory returned successfully.",
                "content": {
                    "application/json": {
                        "examples": {"artifacts": {"value": {"artifacts": ["art-1"]}}}
                    }
                },
            }
        },
    )  # type: ignore[untyped-decorator]
    def list_artifacts(
        response: Response,
        limit: int | None = None,
        offset: int = 0,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        if correlation_id:
            response.headers["X-Correlation-Id"] = correlation_id
        engine = VectorExecutionEngine()
        return engine.list_artifacts(limit=limit, offset=offset)

    @app.get(
        "/runs",
        tags=["Discovery"],
        summary="List execution runs",
        description=(
            "Return recorded run identifiers from the run store for audit, replay, or "
            "support workflows."
        ),
        operation_id="listExecutionRuns",
        response_model=ListRunsResponse,
        responses={
            200: {
                "description": "Run inventory returned successfully.",
                "content": {
                    "application/json": {
                        "examples": {"runs": {"value": {"runs": ["run-1"]}}}
                    }
                },
            }
        },
    )  # type: ignore[untyped-decorator]
    def list_runs(
        response: Response,
        limit: int | None = None,
        offset: int = 0,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        if correlation_id:
            response.headers["X-Correlation-Id"] = correlation_id
        runs = RunStore().list_runs(limit=limit, offset=offset)
        return {"runs": runs}


__all__ = ["register_read_routes"]
