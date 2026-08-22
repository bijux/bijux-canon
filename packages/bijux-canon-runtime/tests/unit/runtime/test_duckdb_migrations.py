# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from bijux_canon_runtime.observability.storage.execution_store import (
    MIGRATIONS_DIR,
    SCHEMA_CONTRACT_PATH,
    SCHEMA_HASH_PATH,
    SCHEMA_VERSION,
    DuckDBExecutionWriteStore,
)

pytestmark = pytest.mark.unit


def test_duckdb_migrations_apply(tmp_path: Path) -> None:
    db_path = tmp_path / "execution.duckdb"
    DuckDBExecutionWriteStore(db_path)
    store = DuckDBExecutionWriteStore(db_path)
    connection = store._connection
    rows = connection.execute(
        "SELECT version, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert [int(row[0]) for row in rows] == [1, 2, 3, SCHEMA_VERSION]
    expected_init = DuckDBExecutionWriteStore._hash_payload(
        (MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8")
    )
    expected_update = DuckDBExecutionWriteStore._hash_payload(
        (MIGRATIONS_DIR / "002_nondeterminism_governance.sql").read_text(
            encoding="utf-8"
        )
    )
    expected_slices = DuckDBExecutionWriteStore._hash_payload(
        (MIGRATIONS_DIR / "003_entropy_budget_slices.sql").read_text(encoding="utf-8")
    )
    expected_metadata = DuckDBExecutionWriteStore._hash_payload(
        (MIGRATIONS_DIR / "004_metadata_authority.sql").read_text(encoding="utf-8")
    )
    assert rows[0][1] == expected_init
    assert rows[1][1] == expected_update
    assert rows[2][1] == expected_slices
    assert rows[3][1] == expected_metadata
    contract_row = connection.execute(
        "SELECT schema_version, schema_hash FROM schema_contract"
    ).fetchone()
    assert contract_row is not None
    assert int(contract_row[0]) == SCHEMA_VERSION
    contract_hash = DuckDBExecutionWriteStore._hash_payload(
        SCHEMA_CONTRACT_PATH.read_text(encoding="utf-8")
    )
    assert contract_row[1] == contract_hash
    expected_schema_hash = SCHEMA_HASH_PATH.read_text(encoding="utf-8").strip()
    assert expected_schema_hash == contract_hash


def test_duckdb_migrations_reject_future_version(tmp_path: Path) -> None:
    db_path = tmp_path / "future.duckdb"
    store = DuckDBExecutionWriteStore(db_path)
    store._connection.execute(
        "INSERT INTO schema_migrations (version, checksum, applied_at) VALUES (?, ?, ?)",
        (SCHEMA_VERSION + 1, "deadbeef", "now"),
    )
    store._connection.commit()
    with pytest.raises(RuntimeError, match="ahead of code migrations"):
        DuckDBExecutionWriteStore(db_path)


def test_duckdb_migration_updates_prior_schema_contract(tmp_path: Path) -> None:
    db_path = tmp_path / "upgrade.duckdb"
    store = DuckDBExecutionWriteStore(db_path)
    connection = store._connection
    for table in (
        "run_publications",
        "run_checks",
        "run_policies",
        "artifact_references",
        "run_attempts",
        "run_dags",
        "run_revisions",
        "artifact_payload_dependencies",
        "artifact_payloads",
    ):
        connection.execute(f"DROP TABLE {table}")
    connection.execute("DELETE FROM schema_migrations WHERE version = 4")
    connection.execute(
        """
        UPDATE schema_contract
        SET schema_version = 3, schema_hash = 'prior-schema-hash'
        WHERE schema_version = 4
        """
    )
    connection.commit()
    store._store.close()

    upgraded = DuckDBExecutionWriteStore(db_path)
    contract_row = upgraded._connection.execute(
        "SELECT schema_version, schema_hash FROM schema_contract"
    ).fetchone()
    assert contract_row == (
        SCHEMA_VERSION,
        SCHEMA_HASH_PATH.read_text(encoding="utf-8").strip(),
    )
    assert upgraded._connection.execute(
        "SELECT count(*) FROM artifact_payloads"
    ).fetchone() == (0,)


def test_duckdb_migrations_rollback_on_failure(tmp_path: Path, monkeypatch) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_init.sql").write_text("BROKEN SQL", encoding="utf-8")
    monkeypatch.setattr(
        "bijux_canon_runtime.observability.storage.execution_store.MIGRATIONS_DIR",
        migrations_dir,
    )
    with pytest.raises(duckdb.Error):
        DuckDBExecutionWriteStore(tmp_path / "broken.duckdb")


def test_schema_contract_mismatch_fails(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "contract.duckdb"
    DuckDBExecutionWriteStore(db_path)
    contract_path = tmp_path / "schema.sql"
    contract_path.write_text("-- bad schema", encoding="utf-8")
    monkeypatch.setattr(
        "bijux_canon_runtime.observability.storage.execution_store.SCHEMA_CONTRACT_PATH",
        contract_path,
    )
    with pytest.raises(RuntimeError, match="schema.hash"):
        DuckDBExecutionWriteStore(db_path)


def test_schema_hash_mismatch_fails(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "schema_hash.duckdb"
    DuckDBExecutionWriteStore(db_path)
    hash_path = tmp_path / "schema.hash"
    hash_path.write_text("deadbeef", encoding="utf-8")
    monkeypatch.setattr(
        "bijux_canon_runtime.observability.storage.execution_store.SCHEMA_HASH_PATH",
        hash_path,
    )
    with pytest.raises(RuntimeError, match="schema.hash"):
        DuckDBExecutionWriteStore(db_path)
