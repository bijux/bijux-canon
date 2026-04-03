# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Schema file discovery helpers for the DuckDB execution store."""

from __future__ import annotations

from pathlib import Path


def default_migrations_dir() -> Path:
    """Return the canonical migrations directory."""
    return Path(__file__).resolve().parents[1] / "migrations"


def default_schema_contract_path() -> Path:
    """Return the canonical schema contract path."""
    return Path(__file__).resolve().parents[1] / "schema.sql"


def default_schema_hash_path() -> Path:
    """Return the canonical schema hash path."""
    return Path(__file__).resolve().parents[1] / "schema.hash"


def load_migration_statements(migrations_dir: Path) -> dict[int, str]:
    """Load ordered schema migration statements from disk."""
    if not migrations_dir.exists():
        raise RuntimeError("Migration directory missing.")
    migrations: dict[int, str] = {}
    for file in sorted(migrations_dir.glob("*.sql")):
        version = int(file.name.split("_", 1)[0])
        migrations[version] = file.read_text(encoding="utf-8")
    return migrations


__all__ = [
    "default_migrations_dir",
    "default_schema_contract_path",
    "default_schema_hash_path",
    "load_migration_statements",
]
