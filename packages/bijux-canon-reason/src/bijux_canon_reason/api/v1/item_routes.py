# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sqlite3
import uuid
from typing import Any, no_type_check

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as FastPath
from pydantic import BaseModel


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
    conn = sqlite3.connect(db_path)
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
    conn.close()
    return db_path


def register_item_routes(
    app: FastAPI,
    *,
    guard_request: Callable[[Request], None],
    enforce_response_size: Callable[[dict[str, object]], dict[str, object]],
    max_response_items: int,
    max_offset: int,
) -> None:
    @app.get("/v1/items")
    @no_type_check
    def list_items(
        request: Request,
        limit: int = Query(default=10, ge=1, le=max_response_items),
        offset: int = Query(default=0, ge=0, le=max_offset),
    ) -> dict[str, object]:
        guard_request(request)
        allowed_keys = {"limit", "offset"}
        extras = [key for key in request.query_params if key not in allowed_keys]
        if extras:
            raise HTTPException(
                status_code=422,
                detail=f"unknown query params: {', '.join(sorted(extras))}",
            )
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, name, description FROM items
            WHERE deleted = 0
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        total_cur = conn.execute("SELECT COUNT(*) FROM items WHERE deleted = 0")
        total = int(total_cur.fetchone()[0])
        conn.close()
        return enforce_response_size(
            {"items": [_row_to_item(row) for row in rows], "total": total}
        )

    @app.get("/v1/items/{item_id}")
    @no_type_check
    def get_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> dict[str, object]:
        guard_request(request)
        _validate_item_id(item_id)
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, name, description, deleted FROM items WHERE id = ?",
            (item_id,),
        )
        row = cur.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="item not found")
        if row["deleted"]:
            conn.close()
            raise HTTPException(status_code=404, detail="item deleted")
        result = _row_to_item(row)
        conn.close()
        return result

    @app.delete("/v1/items/{item_id}", status_code=204, response_class=Response)
    @no_type_check
    def delete_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> Response:
        guard_request(request)
        _validate_item_id(item_id)
        conn = sqlite3.connect(app.state.db_path)
        cur = conn.execute("SELECT deleted FROM items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="item not found")
        if row[0]:
            conn.close()
            raise HTTPException(status_code=404, detail="item deleted")
        conn.execute("UPDATE items SET deleted = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return Response(status_code=204)

    @app.post("/v1/items", status_code=201)
    @no_type_check
    def create_item(
        request: Request,
        payload: ItemCreate = Body(default=...),  # noqa: B008
    ) -> dict[str, object]:
        guard_request(request)
        raw_name = payload.name or f"item-{uuid.uuid4().hex[:8]}"
        description = payload.description or ""
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT id, name, description, deleted FROM items WHERE name = ?",
                (raw_name,),
            )
            row = cur.fetchone()
            if row and not row["deleted"]:
                return _row_to_item(row)
            if row and row["deleted"]:
                conn.execute(
                    "UPDATE items SET description = ?, deleted = 0 WHERE id = ?",
                    (description, row["id"]),
                )
                conn.commit()
                cur = conn.execute(
                    "SELECT id, name, description FROM items WHERE id = ?",
                    (row["id"],),
                )
                row = cur.fetchone()
                return _row_to_item(row)
            cur = conn.execute(
                "INSERT INTO items (name, description, deleted) VALUES (?, ?, 0)",
                (raw_name, description),
            )
            item_id = cur.lastrowid
            conn.commit()
            cur = conn.execute(
                "SELECT id, name, description FROM items WHERE id = ?",
                (item_id,),
            )
            row = cur.fetchone()
            return _row_to_item(row)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail="name already exists") from exc
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            conn.rollback()
            raise HTTPException(status_code=422, detail="invalid request") from exc
        finally:
            conn.close()

    @app.put("/v1/items/{item_id}")
    @no_type_check
    def update_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
        payload: ItemUpdate = Body(default=...),  # noqa: B008
    ) -> dict[str, object]:
        guard_request(request)
        _validate_item_id(item_id)
        raw_name = payload.name or f"item-{item_id}"
        description = payload.description
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT id, deleted FROM items WHERE id = ?", (item_id,))
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO items (id, name, description, deleted) VALUES (?, ?, ?, 0)",
                    (item_id, raw_name, description or ""),
                )
                conn.commit()
                cur = conn.execute(
                    "SELECT id, name, description FROM items WHERE id = ?",
                    (item_id,),
                )
                new_row = cur.fetchone()
                return _row_to_item(new_row)
            if row["deleted"]:
                raise HTTPException(status_code=404, detail="item deleted")
            conn.execute(
                "UPDATE items SET name = ?, description = ? WHERE id = ?",
                (raw_name, description, item_id),
            )
            conn.commit()
            cur = conn.execute(
                "SELECT id, name, description FROM items WHERE id = ?",
                (item_id,),
            )
            new_row = cur.fetchone()
            return _row_to_item(new_row)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail="name already exists") from exc
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            conn.rollback()
            raise HTTPException(status_code=422, detail="invalid request") from exc
        finally:
            conn.close()


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
