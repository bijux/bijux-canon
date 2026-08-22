# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application service for the persisted v1 item lifecycle."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import cast
import uuid


class ItemNotFoundError(LookupError):
    """An item does not exist or is no longer active."""


class ItemConflictError(ValueError):
    """An item name conflicts with an existing record."""


class ItemRequestError(ValueError):
    """An item mutation could not be persisted."""


class ItemService:
    """Own item persistence and lifecycle decisions outside HTTP transport."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @classmethod
    def configure(cls, artifacts_dir: Path) -> ItemService:
        """Create the durable store and return its application service."""
        db_path = artifacts_dir / "api_storage.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        service = cls(db_path)
        with closing(service._connect()) as conn:
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
            conn.execute("UPDATE items SET description = '' WHERE description IS NULL")
            conn.commit()
        return service

    @property
    def db_path(self) -> Path:
        """Return the configured store path for compatibility diagnostics."""
        return self._db_path

    def list_items(self, *, limit: int, offset: int) -> dict[str, object]:
        """Return a deterministic page of active items."""
        with closing(self._connect()) as conn:
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
        return {"items": [self._row_to_item(row) for row in rows], "total": total}

    def get_item(self, *, item_id: int) -> dict[str, object]:
        """Return one active item."""
        with closing(self._connect()) as conn:
            return self._read_active_item(conn, item_id=item_id)

    def delete_item(self, *, item_id: int) -> None:
        """Mark one active item as deleted."""
        with closing(self._connect()) as conn:
            row = self._read_item_row(conn, item_id=item_id)
            if row is None:
                raise ItemNotFoundError("item not found")
            if row["deleted"]:
                raise ItemNotFoundError("item deleted")
            conn.execute("UPDATE items SET deleted = 1 WHERE id = ?", (item_id,))
            conn.commit()

    def create_item(
        self, *, name: str | None, description: str | None
    ) -> dict[str, object]:
        """Create or restore an item under the v1 idempotency rules."""
        item_name = name or f"item-{uuid.uuid4().hex[:8]}"
        item_description = description or ""
        with closing(self._connect()) as conn:
            try:
                item = self._create_or_restore_item(
                    conn,
                    item_name=item_name,
                    description=item_description,
                )
                conn.commit()
                return item
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise ItemConflictError("name already exists") from exc
            except sqlite3.Error as exc:  # pragma: no cover - defensive
                conn.rollback()
                raise ItemRequestError("invalid request") from exc

    def update_item(
        self,
        *,
        item_id: int,
        name: str | None,
        description: str | None,
    ) -> dict[str, object]:
        """Update or create an item under the v1 upsert rules."""
        item_name = name or f"item-{item_id}"
        item_description = description or ""
        with closing(self._connect()) as conn:
            try:
                item = self._upsert_item(
                    conn,
                    item_id=item_id,
                    item_name=item_name,
                    description=item_description,
                )
                conn.commit()
                return item
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise ItemConflictError("name already exists") from exc
            except sqlite3.Error as exc:  # pragma: no cover - defensive
                conn.rollback()
                raise ItemRequestError("invalid request") from exc

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _read_item_row(
        conn: sqlite3.Connection, *, item_id: int
    ) -> sqlite3.Row | None:
        row = conn.execute(
            "SELECT id, name, description, deleted FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _read_item_by_name(
        conn: sqlite3.Connection, *, item_name: str
    ) -> sqlite3.Row | None:
        row = conn.execute(
            "SELECT id, name, description, deleted FROM items WHERE name = ?",
            (item_name,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    def _read_active_item(
        self, conn: sqlite3.Connection, *, item_id: int
    ) -> dict[str, object]:
        row = self._read_item_row(conn, item_id=item_id)
        if row is None:
            raise ItemNotFoundError("item not found")
        if row["deleted"]:
            raise ItemNotFoundError("item deleted")
        return self._row_to_item(row)

    def _create_or_restore_item(
        self,
        conn: sqlite3.Connection,
        *,
        item_name: str,
        description: str,
    ) -> dict[str, object]:
        row = self._read_item_by_name(conn, item_name=item_name)
        if row and not row["deleted"]:
            return self._row_to_item(row)
        if row and row["deleted"]:
            conn.execute(
                "UPDATE items SET description = ?, deleted = 0 WHERE id = ?",
                (description, row["id"]),
            )
            return self._read_active_item(conn, item_id=int(row["id"]))
        item_id = conn.execute(
            "INSERT INTO items (name, description, deleted) VALUES (?, ?, 0)",
            (item_name, description),
        ).lastrowid
        if item_id is None:
            raise ItemRequestError("item creation did not return an identity")
        return self._read_active_item(conn, item_id=int(item_id))

    def _upsert_item(
        self,
        conn: sqlite3.Connection,
        *,
        item_id: int,
        item_name: str,
        description: str,
    ) -> dict[str, object]:
        row = self._read_item_row(conn, item_id=item_id)
        if row is None:
            conn.execute(
                "INSERT INTO items (id, name, description, deleted) VALUES (?, ?, ?, 0)",
                (item_id, item_name, description),
            )
            return self._read_active_item(conn, item_id=item_id)
        if row["deleted"]:
            raise ItemNotFoundError("item deleted")
        conn.execute(
            "UPDATE items SET name = ?, description = ? WHERE id = ?",
            (item_name, description, item_id),
        )
        return self._read_active_item(conn, item_id=item_id)

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"] or "",
        }


__all__ = [
    "ItemConflictError",
    "ItemNotFoundError",
    "ItemRequestError",
    "ItemService",
]
