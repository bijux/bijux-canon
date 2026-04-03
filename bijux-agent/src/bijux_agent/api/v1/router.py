"""Framework-agnostic API routing registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class APIRoute:
    """Declarative API route definition."""

    name: str
    method: str
    handler: Callable[..., object]
    request_schema: type[object]
    response_schema: type[object]


def get_routes() -> tuple[APIRoute, ...]:
    """Return the API route registry."""
    from bijux_agent.api.v1.handlers import run_pipeline_v1
    from bijux_agent.api.v1.schemas import RunRequestV1, RunResponseV1

    return (
        APIRoute(
            name="run",
            method="POST",
            handler=run_pipeline_v1,
            request_schema=RunRequestV1,
            response_schema=RunResponseV1,
        ),
    )
