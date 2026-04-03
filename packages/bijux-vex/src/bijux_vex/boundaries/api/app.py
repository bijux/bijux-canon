# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from typing import NoReturn, cast

from fastapi import FastAPI, Header, HTTPException, Response

from bijux_vex.boundaries.exception_bridge import (
    is_refusal,
    record_failure,
    refusal_payload,
    to_http_status,
)
from bijux_vex.boundaries.pydantic_edges.models import (
    BackendCapabilitiesReport,
    CreateRequest,
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)
from bijux_vex.core.config import (
    EmbeddingCacheConfig,
    EmbeddingConfig,
    ExecutionConfig,
    VectorStoreConfig,
)
from bijux_vex.core.errors import BijuxError
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import ExecutionBudget
from bijux_vex.infra.run_store import RunStore
from bijux_vex.services.execution_engine import VectorExecutionEngine


def build_app() -> FastAPI:
    app = FastAPI(title="bijux-vex execution API", version="v1")

    refusal_example = {
        "error": {
            "reason": "determinism_violation",
            "message": "[INV-000] Deterministic execution requires a deterministic vector store",
            "remediation": "Use deterministic inputs or switch to non_deterministic contract with declared randomness.",
        }
    }

    def _raise_http_error(
        exc: BijuxError, correlation_id: str | None = None
    ) -> NoReturn:
        record_failure(exc)
        detail: object
        if is_refusal(exc):
            detail = {"error": refusal_payload(exc)}
        else:
            detail = {"message": str(exc)}
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else None
        raise HTTPException(
            status_code=to_http_status(exc), detail=detail, headers=headers
        ) from None

    def _config_from_payload(
        *,
        vector_store: str | None = None,
        vector_store_uri: str | None = None,
        vector_store_options: dict[str, str] | None = None,
        embed_provider: str | None = None,
        embed_model: str | None = None,
        cache_embeddings: str | None = None,
    ) -> ExecutionConfig:
        vs_cfg = None
        if vector_store:
            vs_cfg = VectorStoreConfig(
                backend=vector_store,
                uri=vector_store_uri,
                options=vector_store_options,
            )
        embed_cfg = None
        if embed_provider or embed_model or cache_embeddings:
            cache_cfg = (
                EmbeddingCacheConfig(backend=None, uri=cache_embeddings)
                if cache_embeddings
                else None
            )
            embed_cfg = EmbeddingConfig(
                provider=embed_provider,
                model=embed_model,
                cache=cache_cfg,
            )
        return ExecutionConfig(vector_store=vs_cfg, embeddings=embed_cfg)

    @app.get(
        "/capabilities",
        response_model=BackendCapabilitiesReport,
        responses={
            200: {
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
                }
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
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {"artifacts": {"value": {"artifacts": ["art-1"]}}}
                    }
                }
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
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {"runs": {"value": {"runs": ["run-1"]}}}
                    }
                }
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
                        "examples": {"refusal": {"value": refusal_example}}
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
            _raise_http_error(exc, correlation_id)
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
                        "examples": {"refusal": {"value": refusal_example}}
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
            engine = VectorExecutionEngine(
                config=_config_from_payload(
                    vector_store=req.vector_store,
                    vector_store_uri=req.vector_store_uri,
                    vector_store_options=req.vector_store_options,
                    embed_provider=req.embed_provider,
                    embed_model=req.embed_model,
                    cache_embeddings=req.cache_embeddings,
                )
            )
            result = engine.ingest(req)
            response.headers["X-Correlation-Id"] = str(
                result.get("correlation_id") or req.correlation_id or ""
            )
            return result
        except BijuxError as exc:
            _raise_http_error(exc, req.correlation_id or correlation_id)
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
                        "examples": {"refusal": {"value": refusal_example}}
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
            engine = VectorExecutionEngine(
                config=_config_from_payload(
                    vector_store=req.vector_store,
                    vector_store_uri=req.vector_store_uri,
                    vector_store_options=req.vector_store_options,
                )
            )
            return engine.materialize(req)
        except BijuxError as exc:
            _raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/execute",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "execute": {
                                "value": {
                                    "artifact_id": "art-1",
                                    "vector": [0.0, 1.0, 0.0],
                                    "top_k": 3,
                                    "execution_contract": "deterministic",
                                    "execution_intent": "exact_validation",
                                    "execution_mode": "strict",
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
                        "examples": {
                            "execute": {
                                "value": {
                                    "results": ["vec-1"],
                                    "correlation_id": "req-example",
                                    "execution_contract": "deterministic",
                                    "execution_contract_status": "stable",
                                    "replayable": True,
                                    "execution_id": "exec-1",
                                }
                            }
                        }
                    }
                }
            },
            422: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": refusal_example}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def execute(
        req: ExecutionRequestPayload,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        try:
            if correlation_id and req.correlation_id is None:
                req = req.model_copy(update={"correlation_id": correlation_id})
            engine = VectorExecutionEngine(
                config=_config_from_payload(
                    vector_store=req.vector_store,
                    vector_store_uri=req.vector_store_uri,
                    vector_store_options=req.vector_store_options,
                )
            )
            result = engine.execute(req)
            response.headers["X-Correlation-Id"] = result.get("correlation_id", "")
            return result
        except BijuxError as exc:
            _raise_http_error(exc, req.correlation_id or correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/explain",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {"explain": {"value": {"result_id": "res-1"}}}
                    }
                }
            }
        },
        responses={
            200: {
                "content": {
                    "application/json": {
                        "examples": {"explain": {"value": {"result_id": "res-1"}}}
                    }
                }
            },
            400: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": refusal_example}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def explain(
        req: ExplainRequest,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        try:
            result = VectorExecutionEngine().explain(req)
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            return result
        except BijuxError as exc:
            _raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/replay",
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "replay": {
                                "value": {
                                    "artifact_id": "art-1",
                                    "request_text": "hello",
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
                        "examples": {"replay": {"value": {"matches": True}}}
                    }
                }
            },
            400: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": refusal_example}}
                    }
                }
            },
        },
    )  # type: ignore[untyped-decorator]
    def replay(
        req: ExecutionRequestPayload,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        request_text = req.request_text or ""
        try:
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            randomness_profile = None
            if req.randomness_profile is not None:
                randomness_profile = RandomnessProfile(
                    seed=req.randomness_profile.seed,
                    sources=tuple(req.randomness_profile.sources or ()),
                    bounded=req.randomness_profile.bounded,
                    non_replayable=req.randomness_profile.non_replayable,
                )
            execution_budget = None
            if req.execution_budget is not None:
                execution_budget = ExecutionBudget(
                    max_latency_ms=req.execution_budget.max_latency_ms,
                    max_memory_mb=req.execution_budget.max_memory_mb,
                    max_error=req.execution_budget.max_error,
                )
            return VectorExecutionEngine().replay(
                request_text,
                artifact_id=req.artifact_id,
                randomness_profile=randomness_profile,
                execution_budget=execution_budget,
            )
        except BijuxError as exc:
            _raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    return app


app = build_app()

__all__ = ["build_app", "app"]
