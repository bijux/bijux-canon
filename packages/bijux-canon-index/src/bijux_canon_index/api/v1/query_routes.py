# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Response

from bijux_canon_index.api.v1.runtime import (
    REFUSAL_EXAMPLE,
    engine_from_payload,
    raise_http_error,
    replay_inputs_from_request,
)
from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.interfaces.schemas.api_responses import (
    ExecuteResponse,
    ExplainResponse,
    ReplayResponse,
)
from bijux_canon_index.interfaces.schemas.requests import (
    ExecutionRequestPayload,
    ExplainRequest,
)


def register_query_routes(app: FastAPI) -> None:
    @app.post(
        "/execute",
        tags=["Execution"],
        summary="Execute a vector query",
        description=(
            "Execute a deterministic or bounded retrieval request against a materialized "
            "artifact and return the result identifiers plus replay metadata."
        ),
        operation_id="executeVectorQuery",
        response_model=ExecuteResponse,
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
                "description": "Execution completed successfully.",
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
                },
            },
            422: {
                "content": {
                    "application/json": {
                        "examples": {"refusal": {"value": REFUSAL_EXAMPLE}}
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
            engine = engine_from_payload(
                vector_store=req.vector_store,
                vector_store_uri=req.vector_store_uri,
                vector_store_options=req.vector_store_options,
            )
            result = engine.execute(req)
            response.headers["X-Correlation-Id"] = result.get("correlation_id", "")
            return result
        except BijuxError as exc:
            raise_http_error(exc, req.correlation_id or correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/explain",
        tags=["Execution"],
        summary="Explain a result",
        description=(
            "Resolve a result identifier back to the document, chunk, vector, and execution "
            "context that produced it."
        ),
        operation_id="explainExecutionResult",
        response_model=ExplainResponse,
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
                "description": "Result explanation returned successfully.",
                "content": {
                    "application/json": {
                        "examples": {
                            "explain": {
                                "value": {
                                    "document_id": "doc-1",
                                    "chunk_id": "chunk-1",
                                    "vector_id": "res-1",
                                    "artifact_id": "art-1",
                                    "metric": "l2",
                                    "score": 0.99,
                                    "correlation_id": "req-example",
                                    "execution_contract": "deterministic",
                                    "execution_contract_status": "stable",
                                    "replayable": True,
                                    "execution_id": "exec-1",
                                }
                            }
                        }
                    }
                },
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
            raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc

    @app.post(
        "/replay",
        tags=["Execution"],
        summary="Replay an execution outcome",
        description=(
            "Replay a prior execution contract against the currently available artifact and "
            "report whether the replay stayed within the declared equivalence boundary."
        ),
        operation_id="replayExecutionOutcome",
        response_model=ReplayResponse,
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
                "description": "Replay completed successfully.",
                "content": {
                    "application/json": {
                        "examples": {
                            "replay": {
                                "value": {
                                    "matches": True,
                                    "original_fingerprint": "orig-fp",
                                    "replay_fingerprint": "replay-fp",
                                    "details": {"status": "matched"},
                                    "nondeterministic_sources": [],
                                    "execution_contract": "deterministic",
                                    "execution_contract_status": "stable",
                                    "replayable": True,
                                    "execution_id": "exec-1",
                                }
                            }
                        }
                    }
                },
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
    def replay(
        req: ExecutionRequestPayload,
        response: Response,
        correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
    ) -> dict[str, object]:
        try:
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            request_text, randomness_profile, execution_budget = (
                replay_inputs_from_request(req)
            )
            return VectorExecutionEngine().replay(
                request_text,
                artifact_id=req.artifact_id,
                randomness_profile=randomness_profile,
                execution_budget=execution_budget,
            )
        except BijuxError as exc:
            raise_http_error(exc, correlation_id)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail="internal error") from exc


__all__ = ["register_query_routes"]
