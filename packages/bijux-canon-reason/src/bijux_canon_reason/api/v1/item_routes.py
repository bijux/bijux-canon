# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Item routes helpers for API support."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as FastPath
from pydantic import BaseModel

from bijux_canon_reason.api.v1.openapi_models import (
    ErrorDetail,
    ItemListResponse,
    ItemResponse,
)
from bijux_canon_reason.application.item_service import (
    ItemConflictError,
    ItemNotFoundError,
    ItemRequestError,
    ItemService,
)

MAX_ITEM_ID = 1_000_000


class ItemCreate(BaseModel):
    """Represents item create."""

    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


class ItemUpdate(BaseModel):
    """Represents item update."""

    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


def configure_item_store(artifacts_dir: Path) -> Path:
    """Configure the item application service and return its store path."""
    return ItemService.configure(artifacts_dir).db_path


def register_item_routes(
    app: FastAPI,
    *,
    guard_request: Callable[[Request], None],
    enforce_response_size: Callable[[dict[str, object]], dict[str, object]],
    max_response_items: int,
    max_offset: int,
) -> None:
    """Register item routes."""
    service = ItemService(Path(app.state.db_path))
    guard_responses = {
        401: {
            "description": "Authentication failed for the requested endpoint.",
            "model": ErrorDetail,
        },
        413: {
            "description": "The request or response exceeded the configured size limit.",
            "model": ErrorDetail,
        },
        415: {
            "description": "The submitted content type is not accepted by the API.",
            "model": ErrorDetail,
        },
        429: {
            "description": "The caller exceeded the configured rate limit.",
            "model": ErrorDetail,
        },
    }

    @app.get(
        "/v1/items",
        response_model=ItemListResponse,
        tags=["Items"],
        summary="List active items",
        description=(
            "Return the current page of active items. Deleted records are hidden from "
            "this listing and pagination is controlled with limit and offset."
        ),
        operation_id="listReasonItems",
        responses={
            **guard_responses,
            422: {
                "description": "Validation failed for a query parameter.",
                "model": ErrorDetail,
            },
        },
    )
    def list_items(
        request: Request,
        limit: int = Query(default=10, ge=1, le=max_response_items),
        offset: int = Query(default=0, ge=0, le=max_offset),
    ) -> dict[str, object]:
        """List items."""
        guard_request(request)
        _reject_unknown_query_params(request=request, allowed={"limit", "offset"})
        return enforce_response_size(service.list_items(limit=limit, offset=offset))

    @app.get(
        "/v1/items/{item_id}",
        response_model=ItemResponse,
        tags=["Items"],
        summary="Get an item",
        description="Return a single active item by identifier.",
        operation_id="getReasonItem",
        responses={
            **guard_responses,
            404: {
                "description": "The requested item does not exist.",
                "model": ErrorDetail,
            },
            422: {
                "description": "Validation failed for the requested item id.",
                "model": ErrorDetail,
            },
        },
    )
    def get_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=MAX_ITEM_ID),
    ) -> dict[str, object]:
        """Return item."""
        guard_request(request)
        _validate_item_id(item_id)
        try:
            return service.get_item(item_id=item_id)
        except ItemNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete(
        "/v1/items/{item_id}",
        status_code=204,
        response_class=Response,
        tags=["Items"],
        summary="Delete an item",
        description="Mark an active item as deleted so it no longer appears in listings.",
        operation_id="deleteReasonItem",
        responses={
            **guard_responses,
            404: {
                "description": "The requested item does not exist.",
                "model": ErrorDetail,
            },
            422: {
                "description": "Validation failed for the requested item id.",
                "model": ErrorDetail,
            },
        },
    )
    def delete_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=MAX_ITEM_ID),
    ) -> Response:
        """Handle delete item."""
        guard_request(request)
        _validate_item_id(item_id)
        try:
            service.delete_item(item_id=item_id)
        except ItemNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(status_code=204)

    @app.post(
        "/v1/items",
        status_code=201,
        response_model=ItemResponse,
        tags=["Items"],
        summary="Create an item",
        description=(
            "Create a new item. If the name already exists and is active, the runtime "
            "returns the existing record instead of creating a duplicate."
        ),
        operation_id="createReasonItem",
        responses={
            **guard_responses,
            409: {
                "description": "The submitted name conflicts with another item.",
                "model": ErrorDetail,
            },
            400: {
                "description": "The submitted request body could not be parsed as JSON.",
                "model": ErrorDetail,
            },
            422: {
                "description": "Validation failed for the submitted payload.",
                "model": ErrorDetail,
            },
        },
    )
    def create_item(request: Request, payload: ItemCreate) -> dict[str, object]:
        """Create item."""
        guard_request(request)
        try:
            return service.create_item(
                name=payload.name,
                description=payload.description,
            )
        except ItemConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ItemRequestError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.put(
        "/v1/items/{item_id}",
        response_model=ItemResponse,
        tags=["Items"],
        summary="Update an item",
        description="Update an active item or create the requested identifier when it does not yet exist.",
        operation_id="updateReasonItem",
        responses={
            **guard_responses,
            404: {
                "description": "The requested item is deleted or unavailable.",
                "model": ErrorDetail,
            },
            409: {
                "description": "The submitted name conflicts with another item.",
                "model": ErrorDetail,
            },
            400: {
                "description": "The submitted request body could not be parsed as JSON.",
                "model": ErrorDetail,
            },
            422: {
                "description": "Validation failed for the submitted payload or item id.",
                "model": ErrorDetail,
            },
        },
    )
    def update_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=MAX_ITEM_ID),
        payload: ItemUpdate = ...,
    ) -> dict[str, object]:
        """Handle update item."""
        guard_request(request)
        _validate_item_id(item_id)
        try:
            return service.update_item(
                item_id=item_id,
                name=payload.name,
                description=payload.description,
            )
        except ItemNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ItemConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ItemRequestError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def _reject_unknown_query_params(*, request: Request, allowed: set[str]) -> None:
    """Handle reject unknown query params."""
    extras = [key for key in request.query_params if key not in allowed]
    if extras:
        raise HTTPException(
            status_code=422,
            detail=f"unknown query params: {', '.join(sorted(extras))}",
        )


def _validate_item_id(item_id: int) -> None:
    """Validate item ID."""
    if item_id < 1 or item_id > MAX_ITEM_ID:
        raise HTTPException(status_code=422, detail="item_id out of range")


__all__ = [
    "ItemCreate",
    "ItemUpdate",
    "configure_item_store",
    "register_item_routes",
]
