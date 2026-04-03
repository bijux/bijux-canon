"""HTTP adapter for API v1."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_agent.api.v1.handlers import run_pipeline_v1
from bijux_agent.api.v1.schemas import RunRequestV1

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def handle_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse, run, and serialize the v1 pipeline handler."""
    request = RunRequestV1.model_validate(payload)
    response = run_pipeline_v1(request)
    return response.model_dump()


def build_router() -> APIRouter | None:
    """Return a FastAPI router when FastAPI is available."""
    try:
        from fastapi import APIRouter
    except ImportError:  # pragma: no cover
        return None

    router = APIRouter()

    @router.post("/v1/run")
    def run_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
        return handle_run(payload)

    return router
