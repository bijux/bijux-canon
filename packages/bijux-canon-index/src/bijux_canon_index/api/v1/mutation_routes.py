# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Response

from bijux_canon_index.api.v1.runtime import (
    REFUSAL_EXAMPLE,
    engine_from_payload,
    raise_http_error,
)
from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.interfaces.schemas.requests import (
    CreateRequest,
    ExecutionArtifactRequest,
    IngestRequest,
)


def register_mutation_routes(app: FastAPI) -> None:
    @app.post(
        "/create",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {"create": {"value": {"name": "my-corpus"}}}
                    }
                }
            }
        },
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {
                            "created": {
                                "value": {"name": "my-corpus", "status": "created"}
                            }
                        }
                    }
                }
            },
            400: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": REFUSAL_EXAMPLE}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def create(
        req: CreateRequest,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        try:
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            return VectorExecutionEngine().create(req)
        except BijuxError as exc:
            raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover - unexpected
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/ingest",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "ingest": {
                                "value": {
                                    "documents": ["hello"],
                                    "vectors": [[0.0, 1.0, 0.0]],
                                    "vector_store": "faiss",
                                    "vector_store_uri": "index.faiss",
                                }
                            }
                        }
                    }
                }
            }
        },
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {"ingested": {"value": {"ingested": 1}}}
                    }
                }
            },
            400: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": REFUSAL_EXAMPLE}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def ingest(
        req: IngestRequest,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ) -> dict[str, object]:
        try:
            if correlation_id and req.correlation_id is None:
                req = req.model_copy(update={"correlation_id": correlation_id})
            if idempotency_key and req.idempotency_key is None:
                req = req.model_copy(update={"idempotency_key": idempotency_key})
            engine = engine_from_payload(
                vector_store=req.vector_store,
                vector_store_uri=req.vector_store_uri,
                vector_store_options=req.vector_store_options,
                embed_provider=req.embed_provider,
                embed_model=req.embed_model,
                cache_embeddings=req.cache_embeddings,
            )
            result = engine.ingest(req)
            response.headers["X-Correlation-Id"] = str(
                result.get("correlation_id") or req.correlation_id or ""
            )
            return result
        except BijuxError as exc:
            raise_http_error(exc, req.correlation_id or correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/artifact",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "artifact": {
                                "value": {"execution_contract": "deterministic"}
                            }
                        }
                    }
                }
            }
        },
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {
                            "artifact": {
                                "value": {
                                    "artifact_id": "art-1",
                                    "execution_contract": "deterministic",
                                    "execution_contract_status": "stable",
                                    "replayable": True,
                                }
                            }
                        }
                    }
                }
            },
            400: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": REFUSAL_EXAMPLE}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def artifact(
        req: ExecutionArtifactRequest,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        try:
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            engine = engine_from_payload(
                vector_store=req.vector_store,
                vector_store_uri=req.vector_store_uri,
                vector_store_options=req.vector_store_options,
            )
            return engine.materialize(req)
        except BijuxError as exc:
            raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc


__all__ = ["register_mutation_routes"]
