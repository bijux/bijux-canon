# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from pathlib import Path
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as FastPath
from pydantic import BaseModel

from bijux_canon_reason.api.v1.openapi_models import (
    ErrorDetail,
    ItemListResponse,
    ItemResponse,
)


class ItemCreate(BaseModel):
    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


class ItemUpdate(BaseModel):
    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


def configure_item_store(artifacts_dir: Path) -> Path:
    db_path = artifacts_dir / "api_storage.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect_item_store(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    return db_path


def register_item_routes(
    app: FastAPI,
    *,
    guard_request: Callable[[Request], None],
    enforce_response_size: Callable[[dict[str, object]], dict[str, object]],
    max_response_items: int,
    max_offset: int,
) -> None:
    db_path = Path(app.state.db_path)
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
        guard_request(request)
        _reject_unknown_query_params(request=request, allowed={"limit", "offset"})
        with closing(_connect_item_store(db_path)) as conn:
            rows = conn.execute(
                """
                SELECT id, name, description FROM items
                WHERE deleted = 0
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            total = int(
                conn.execute("SELECT COUNT(*) FROM items WHERE deleted = 0").fetchone()[
                    0
                ]
            )
        return enforce_response_size(
            {"items": [_row_to_item(row) for row in rows], "total": total}
        )

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
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> dict[str, object]:
        guard_request(request)
        _validate_item_id(item_id)
        with closing(_connect_item_store(db_path)) as conn:
            return _read_active_item(conn, item_id=item_id)

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
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> Response:
        guard_request(request)
        _validate_item_id(item_id)
        with closing(_connect_item_store(db_path)) as conn:
            row = _read_item_row(conn, item_id=item_id)
            if row is None:
                raise HTTPException(status_code=404, detail="item not found")
            if row["deleted"]:
                raise HTTPException(status_code=404, detail="item deleted")
            conn.execute("UPDATE items SET deleted = 1 WHERE id = ?", (item_id,))
            conn.commit()
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
            422: {
                "description": "Validation failed for the submitted payload.",
                "model": ErrorDetail,
            },
        },
    )
    def create_item(request: Request, payload: ItemCreate) -> dict[str, object]:
        guard_request(request)
        item_name = payload.name or f"item-{uuid.uuid4().hex[:8]}"
        description = payload.description or ""
        with closing(_connect_item_store(db_path)) as conn:
            try:
                item = _create_or_restore_item(
                    conn,
                    item_name=item_name,
                    description=description,
                )
                conn.commit()
                return item
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise HTTPException(
                    status_code=409, detail="name already exists"
                ) from exc
            except sqlite3.Error as exc:  # pragma: no cover - defensive
                conn.rollback()
                raise HTTPException(status_code=422, detail="invalid request") from exc

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
            422: {
                "description": "Validation failed for the submitted payload or item id.",
                "model": ErrorDetail,
            },
        },
    )
    def update_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
        payload: ItemUpdate = ...,
    ) -> dict[str, object]:
        guard_request(request)
        _validate_item_id(item_id)
        item_name = payload.name or f"item-{item_id}"
        description = payload.description
        with closing(_connect_item_store(db_path)) as conn:
            try:
                item = _upsert_item(
                    conn,
                    item_id=item_id,
                    item_name=item_name,
                    description=description,
                )
                conn.commit()
                return item
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise HTTPException(
                    status_code=409, detail="name already exists"
                ) from exc
            except sqlite3.Error as exc:  # pragma: no cover - defensive
                conn.rollback()
                raise HTTPException(status_code=422, detail="invalid request") from exc


def _connect_item_store(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _reject_unknown_query_params(*, request: Request, allowed: set[str]) -> None:
    extras = [key for key in request.query_params if key not in allowed]
    if extras:
        raise HTTPException(
            status_code=422,
            detail=f"unknown query params: {', '.join(sorted(extras))}",
        )


def _read_item_row(conn: sqlite3.Connection, *, item_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, description, deleted FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()


def _read_item_by_name(
    conn: sqlite3.Connection, *, item_name: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, description, deleted FROM items WHERE name = ?",
        (item_name,),
    ).fetchone()


def _read_active_item(conn: sqlite3.Connection, *, item_id: int) -> dict[str, object]:
    row = _read_item_row(conn, item_id=item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="item not found")
    if row["deleted"]:
        raise HTTPException(status_code=404, detail="item deleted")
    return _row_to_item(row)


def _create_or_restore_item(
    conn: sqlite3.Connection, *, item_name: str, description: str
) -> dict[str, object]:
    row = _read_item_by_name(conn, item_name=item_name)
    if row and not row["deleted"]:
        return _row_to_item(row)
    if row and row["deleted"]:
        conn.execute(
            "UPDATE items SET description = ?, deleted = 0 WHERE id = ?",
            (description, row["id"]),
        )
        return _read_active_item(conn, item_id=int(row["id"]))

    item_id = conn.execute(
        "INSERT INTO items (name, description, deleted) VALUES (?, ?, 0)",
        (item_name, description),
    ).lastrowid
    return _read_active_item(conn, item_id=int(item_id))


def _upsert_item(
    conn: sqlite3.Connection,
    *,
    item_id: int,
    item_name: str,
    description: str | None,
) -> dict[str, object]:
    row = _read_item_row(conn, item_id=item_id)
    if row is None:
        conn.execute(
            "INSERT INTO items (id, name, description, deleted) VALUES (?, ?, ?, 0)",
            (item_id, item_name, description or ""),
        )
        return _read_active_item(conn, item_id=item_id)
    if row["deleted"]:
        raise HTTPException(status_code=404, detail="item deleted")

    conn.execute(
        "UPDATE items SET name = ?, description = ? WHERE id = ?",
        (item_name, description, item_id),
    )
    return _read_active_item(conn, item_id=item_id)


def _row_to_item(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
    }


def _validate_item_id(item_id: int) -> None:
    if item_id < 1 or item_id > 1_000_000:
        raise HTTPException(status_code=422, detail="item_id out of range")


__all__ = [
    "ItemCreate",
    "ItemUpdate",
    "configure_item_store",
    "register_item_routes",
]
