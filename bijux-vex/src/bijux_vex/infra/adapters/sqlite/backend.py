# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable, Iterable
import json
import sqlite3
import threading
from typing import NamedTuple

from bijux_vex.contracts.authz import AllowAllAuthz, Authz
from bijux_vex.contracts.resources import (
    BackendCapabilities,
    ExecutionLedger,
    ExecutionResources,
    VectorSource,
)
from bijux_vex.contracts.tx import Tx
from bijux_vex.core.contracts.determinism import DeterminismReport
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import (
    AtomicityViolationError,
    InvariantError,
    NotFoundError,
    ValidationError,
)
from bijux_vex.core.execution_result import (
    ApproximationReport,
    ExecutionCost,
    ExecutionResult,
    ExecutionStatus,
)
from bijux_vex.core.runtime.execution_plan import ExecutionPlan, RandomnessSource
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Result,
    Vector,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner

ACTIVE_CONNECTIONS: set[int] = set()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, text TEXT, source TEXT, version TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT, text TEXT, ordinal INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS vectors(id TEXT PRIMARY KEY, chunk_id TEXT, dim INTEGER, vec_values TEXT, model TEXT, metadata TEXT)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts(
            id TEXT PRIMARY KEY,
            corpus_fp TEXT,
            vector_fp TEXT,
            metric TEXT,
            scoring TEXT,
            execution_contract TEXT,
            execution_id TEXT,
            schema_version TEXT,
            build_params TEXT,
            replayable INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_results(
            execution_id TEXT PRIMARY KEY,
            artifact_id TEXT,
            payload TEXT
        )
        """
    )
    _ensure_vector_columns(conn)
    conn.commit()


def _ensure_vector_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(vectors)").fetchall()}
    if "model" not in existing:
        conn.execute("ALTER TABLE vectors ADD COLUMN model TEXT")
    if "metadata" not in existing:
        conn.execute("ALTER TABLE vectors ADD COLUMN metadata TEXT")


class SQLiteTx(Tx):
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock
        self._active = True
        self._entered = False

    @property
    def tx_id(self) -> str:
        return "sqlite-tx"

    def __enter__(self) -> Tx:
        self._lock.acquire()
        conn_id = id(self._conn)
        if conn_id in ACTIVE_CONNECTIONS:
            self._lock.release()
            raise AtomicityViolationError(message="Nested Tx is not allowed")
        self._conn.execute("BEGIN")
        ACTIVE_CONNECTIONS.add(conn_id)
        self._entered = True
        return self

    def commit(self) -> None:
        if not self._entered:
            raise AtomicityViolationError(message="Tx must be entered before commit")
        if not self._active:
            raise AtomicityViolationError(message="Tx already finished")
        try:
            self._conn.commit()
            self._active = False
            ACTIVE_CONNECTIONS.discard(id(self._conn))
        finally:
            self._lock.release()

    def abort(self) -> None:
        if not self._entered:
            raise AtomicityViolationError(message="Tx must be entered before abort")
        if not self._active:
            raise AtomicityViolationError(message="Tx already finished")
        try:
            self._conn.rollback()
            self._active = False
            ACTIVE_CONNECTIONS.discard(id(self._conn))
        finally:
            self._lock.release()


class SQLiteVectorSource(VectorSource):
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock
        self._metric_cache: dict[str, str] = {}
        self._artifact_cache: dict[str, ExecutionArtifact] = {}
        self._vector_cache: list[Vector] | None = None

    # Documents
    def put_document(self, tx: Tx, document: Document) -> None:
        with self._lock:
            self._conn.execute(
                "REPLACE INTO documents(id, text, source, version) VALUES(?,?,?,?)",
                (
                    document.document_id,
                    document.text,
                    document.source,
                    document.version,
                ),
            )

    def get_document(self, document_id: str) -> Document | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, text, source, version FROM documents WHERE id=?",
                (document_id,),
            ).fetchone()
        if not row:
            return None
        return Document(document_id=row[0], text=row[1], source=row[2], version=row[3])

    def list_documents(self) -> Iterable[Document]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, source, version FROM documents ORDER BY id"
            ).fetchall()
        return [
            Document(document_id=r[0], text=r[1], source=r[2], version=r[3])
            for r in rows
        ]

    def delete_document(self, tx: Tx, document_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM documents WHERE id=?", (document_id,))

    # Chunks
    def put_chunk(self, tx: Tx, chunk: Chunk) -> None:
        with self._lock:
            self._conn.execute(
                "REPLACE INTO chunks(id, document_id, text, ordinal) VALUES(?,?,?,?)",
                (chunk.chunk_id, chunk.document_id, chunk.text, chunk.ordinal),
            )

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, document_id, text, ordinal FROM chunks WHERE id=?",
                (chunk_id,),
            ).fetchone()
        if not row:
            return None
        return Chunk(chunk_id=row[0], document_id=row[1], text=row[2], ordinal=row[3])

    def list_chunks(self, document_id: str | None = None) -> Iterable[Chunk]:
        with self._lock:
            if document_id:
                rows = self._conn.execute(
                    "SELECT id, document_id, text, ordinal FROM chunks WHERE document_id=? ORDER BY id",
                    (document_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, document_id, text, ordinal FROM chunks ORDER BY id"
                ).fetchall()
        return [
            Chunk(chunk_id=r[0], document_id=r[1], text=r[2], ordinal=r[3])
            for r in rows
        ]

    def delete_chunk(self, tx: Tx, chunk_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM chunks WHERE id=?", (chunk_id,))

    def _load_artifact(self, artifact_id: str) -> ExecutionArtifact:
        cached = self._artifact_cache.get(artifact_id)
        if cached:
            return cached
        with self._lock:
            row = self._conn.execute(
                "SELECT id, corpus_fp, vector_fp, metric, scoring, execution_contract, execution_id, schema_version, build_params, replayable FROM artifacts WHERE id=?",
                (artifact_id,),
            ).fetchone()
        if not row:
            raise NotFoundError(message=f"Execution artifact {artifact_id} not found")
        build_params_raw = row[8] or "[]"
        build_params = tuple(tuple(p) for p in json.loads(build_params_raw))
        artifact = ExecutionArtifact(
            artifact_id=row[0],
            corpus_fingerprint=row[1],
            vector_fingerprint=row[2],
            metric=row[3],
            scoring_version=row[4],
            execution_contract=ExecutionContract(row[5]),
            execution_id=row[6],
            schema_version=row[7],
            build_params=build_params,
        )
        self._artifact_cache[artifact_id] = artifact
        self._metric_cache[artifact_id] = artifact.metric
        return artifact

    def put_vector(self, tx: Tx, vector: Vector) -> None:
        with self._lock:
            self._conn.execute(
                "REPLACE INTO vectors(id, chunk_id, dim, vec_values, model, metadata) VALUES(?,?,?,?,?,?)",
                (
                    vector.vector_id,
                    vector.chunk_id,
                    vector.dimension,
                    json_dumps(vector.values),
                    vector.model,
                    json_dumps_meta(vector.metadata),
                ),
            )
        self._vector_cache = None

    def get_vector(self, vector_id: str) -> Vector | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, chunk_id, dim, vec_values, model, metadata FROM vectors WHERE id=?",
                (vector_id,),
            ).fetchone()
        if not row:
            return None
        values = tuple(json_loads(row[3]))
        return Vector(
            vector_id=row[0],
            chunk_id=row[1],
            dimension=row[2],
            values=values,
            model=row[4],
            metadata=json_loads_meta(row[5]),
        )

    def list_vectors(self, chunk_id: str | None = None) -> Iterable[Vector]:
        if chunk_id is None and self._vector_cache is not None:
            return list(self._vector_cache)
        with self._lock:
            if chunk_id:
                rows = self._conn.execute(
                    "SELECT id, chunk_id, dim, vec_values, model, metadata FROM vectors WHERE chunk_id=? ORDER BY id",
                    (chunk_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, chunk_id, dim, vec_values, model, metadata FROM vectors ORDER BY id"
                ).fetchall()
        vectors = [
            Vector(
                vector_id=r[0],
                chunk_id=r[1],
                dimension=r[2],
                values=tuple(json_loads(r[3])),
                model=r[4],
                metadata=json_loads_meta(r[5]),
            )
            for r in rows
        ]
        if chunk_id is None:
            self._vector_cache = list(vectors)
        return vectors

    def query(self, artifact_id: str, request: ExecutionRequest) -> Iterable[Result]:
        # Basic deterministic L2 similar to memory
        if request.vector is None:
            raise ValidationError(message="execution vector required")
        artifact = self._load_artifact(artifact_id)
        if artifact.execution_contract is not request.execution_contract:
            raise InvariantError(
                message="Execution contract does not match artifact execution contract"
            )
        with self._lock:
            rows = self._conn.execute(
                "SELECT v.id, v.chunk_id, v.dim, v.vec_values, c.document_id "
                "FROM vectors v LEFT JOIN chunks c ON v.chunk_id = c.id ORDER BY v.id"
            ).fetchall()
        scored: list[Result] = []
        req_vec = request.vector
        for row in rows:
            vec_dim = row[2]
            if len(req_vec) != vec_dim:
                continue
            values = tuple(json_loads(row[3]))
            score = sum((q - v) * (q - v) for q, v in zip(req_vec, values, strict=True))
            doc_id = row[4] or ""
            scored.append(
                Result(
                    request_id=request.request_id,
                    document_id=doc_id,
                    chunk_id=row[1],
                    vector_id=row[0],
                    artifact_id=artifact_id,
                    score=score,
                    rank=0,
                )
            )
        scored.sort(key=lambda r: (r.score, r.vector_id, r.chunk_id, r.document_id))
        for idx, res in enumerate(scored[: request.top_k], start=1):
            scored[idx - 1] = Result(
                request_id=res.request_id,
                document_id=res.document_id,
                chunk_id=res.chunk_id,
                vector_id=res.vector_id,
                artifact_id=res.artifact_id,
                score=res.score,
                rank=idx,
            )
        return scored[: request.top_k]

    def delete_vector(self, tx: Tx, vector_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM vectors WHERE id=?", (vector_id,))
        self._vector_cache = None


class SQLiteExecutionLedger(ExecutionLedger):
    MAX_ARTIFACTS = 1000
    MAX_RESULTS = 5000

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock

    def put_artifact(self, tx: Tx, artifact: ExecutionArtifact) -> None:
        with self._lock:
            existing = self.get_artifact(artifact.artifact_id)
            if (
                existing
                and existing.execution_contract is not artifact.execution_contract
            ):
                raise InvariantError(
                    message="Cannot overwrite artifact with different execution contract"
                )
            if existing is None:
                count = self._conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[
                    0
                ]
                if count >= self.MAX_ARTIFACTS:
                    raise InvariantError(
                        message="Artifact retention limit exceeded; compact or delete artifacts"
                    )
            self._conn.execute(
                "REPLACE INTO artifacts(id, corpus_fp, vector_fp, metric, scoring, execution_contract, execution_id, schema_version, build_params, replayable) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    artifact.artifact_id,
                    artifact.corpus_fingerprint,
                    artifact.vector_fingerprint,
                    artifact.metric,
                    artifact.scoring_version,
                    artifact.execution_contract.value,
                    artifact.execution_id,
                    artifact.schema_version,
                    json.dumps(list(artifact.build_params)),
                    1 if artifact.replayable else 0,
                ),
            )

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, corpus_fp, vector_fp, metric, scoring, execution_contract, execution_id, schema_version, build_params FROM artifacts WHERE id=?",
                (artifact_id,),
            ).fetchone()
        if not row:
            return None
        build_params_raw = row[8] or "[]"
        return ExecutionArtifact(
            artifact_id=row[0],
            corpus_fingerprint=row[1],
            vector_fingerprint=row[2],
            metric=row[3],
            scoring_version=row[4],
            execution_contract=ExecutionContract(row[5]),
            execution_id=row[6],
            schema_version=row[7],
            build_params=tuple(tuple(p) for p in json.loads(build_params_raw)),
        )

    def list_artifacts(self) -> Iterable[ExecutionArtifact]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, corpus_fp, vector_fp, metric, scoring, execution_contract, execution_id, schema_version, build_params FROM artifacts ORDER BY id"
            ).fetchall()
        return [
            ExecutionArtifact(
                artifact_id=r[0],
                corpus_fingerprint=r[1],
                vector_fingerprint=r[2],
                metric=r[3],
                scoring_version=r[4],
                execution_contract=ExecutionContract(r[5]),
                execution_id=r[6],
                schema_version=r[7],
                build_params=tuple(tuple(p) for p in json.loads(r[8] or "[]")),
            )
            for r in rows
        ]

    def delete_artifact(self, tx: Tx, artifact_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM artifacts WHERE id=?", (artifact_id,))

    def put_execution_result(self, tx: Tx, result: ExecutionResult) -> None:
        payload = json.dumps(result.to_primitive())
        with self._lock:
            self._conn.execute(
                "REPLACE INTO execution_results(execution_id, artifact_id, payload) VALUES(?,?,?)",
                (result.execution_id, result.artifact_id, payload),
            )
            max_keep = 5
            self._conn.execute(
                """
                DELETE FROM execution_results
                WHERE artifact_id=?
                  AND rowid NOT IN (
                    SELECT rowid FROM execution_results
                    WHERE artifact_id=?
                    ORDER BY rowid DESC
                    LIMIT ?
                  )
                """,
                (result.artifact_id, result.artifact_id, max_keep),
            )

    def get_execution_result(self, execution_id: str) -> ExecutionResult | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM execution_results WHERE execution_id=?",
                (execution_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        # deserialize minimally; using direct dataclass constructors
        plan = ExecutionPlan(
            algorithm=payload["plan"]["algorithm"],
            contract=ExecutionContract(payload["plan"]["contract"]),
            k=payload["plan"]["k"],
            scoring_fn=payload["plan"]["scoring_fn"],
            randomness_sources=tuple(
                RandomnessSource(
                    name=src["name"],
                    description=src["description"],
                    category=src["category"],
                )
                for src in payload["plan"].get("randomness_sources", [])
            ),
            reproducibility_bounds=payload["plan"]["reproducibility_bounds"],
        )
        results = tuple(
            Result(
                request_id=r["request_id"],
                document_id=r["document_id"],
                chunk_id=r["chunk_id"],
                vector_id=r["vector_id"],
                artifact_id=r["artifact_id"],
                score=r["score"],
                rank=r["rank"],
            )
            for r in payload["results"]
        )
        cost = payload["cost"]
        approx_raw = payload.get("approximation")
        approximation = (
            ApproximationReport(
                recall_at_k=approx_raw["recall_at_k"],
                rank_displacement=approx_raw["rank_displacement"],
                distance_error=approx_raw["distance_error"],
            )
            if approx_raw
            else None
        )
        randomness_sources = tuple(payload.get("randomness_sources", ()))
        randomness_budget = tuple(
            tuple(item) for item in payload.get("randomness_budget", ())
        )
        determinism_raw = payload.get("determinism_report")
        determinism_report = (
            DeterminismReport(
                randomness_sources=tuple(determinism_raw.get("randomness_sources", ())),
                reproducibility_bounds=determinism_raw.get(
                    "reproducibility_bounds", ""
                ),
                expected_contract=determinism_raw.get("expected_contract", ""),
                actual_contract=determinism_raw.get("actual_contract", ""),
                notes=tuple(determinism_raw.get("notes", ())),
            )
            if determinism_raw
            else None
        )
        return ExecutionResult(
            execution_id=payload["execution_id"],
            signature=payload["signature"],
            artifact_id=payload["artifact_id"],
            plan=plan,
            results=results,
            cost=ExecutionCost(
                vector_reads=cost["vector_reads"],
                distance_computations=cost["distance_computations"],
                graph_hops=cost["graph_hops"],
                wall_time_estimate_ms=cost["wall_time_estimate_ms"],
                cpu_time_ms=cost.get("cpu_time_ms", cost["wall_time_estimate_ms"]),
                memory_estimate_mb=cost.get("memory_estimate_mb", 0.0),
                vector_ops=cost.get("vector_ops", len(results)),
            ),
            approximation=approximation,
            status=ExecutionStatus(payload.get("status", "success")),
            failure_reason=payload.get("failure_reason"),
            randomness_sources=randomness_sources,
            randomness_budget=randomness_budget,
            determinism_report=determinism_report,
        )

    def latest_execution_result(self, artifact_id: str) -> ExecutionResult | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM execution_results WHERE artifact_id=? ORDER BY rowid DESC LIMIT 1",
                (artifact_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        return self.get_execution_result(payload["execution_id"])


def json_dumps(vals: Iterable[float]) -> str:
    return json.dumps(list(vals))


def json_loads(raw: str) -> list[float]:
    loaded = json.loads(raw)
    return [float(v) for v in loaded]


def json_dumps_meta(
    metadata: tuple[tuple[str, str], ...] | dict[str, str] | None,
) -> str | None:
    if not metadata:
        return None
    payload = list(metadata.items()) if isinstance(metadata, dict) else list(metadata)
    return json.dumps(payload)


def json_loads_meta(raw: str | None) -> tuple[tuple[str, str], ...] | None:
    if not raw:
        return None
    loaded = json.loads(raw)
    return tuple((str(k), str(v)) for k, v in loaded)


class SQLiteFixture(NamedTuple):
    tx_factory: Callable[[], SQLiteTx]
    stores: ExecutionResources
    authz: Authz
    name: str
    ann: AnnExecutionRequestRunner | None = None
    diagnostics: dict[str, Callable[[], object]] | None = None


def sqlite_backend(db_path: str = ":memory:") -> SQLiteFixture:
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    _init_schema(conn)
    lock = threading.RLock()

    def tx_factory() -> SQLiteTx:
        return SQLiteTx(conn, lock)

    capabilities = BackendCapabilities(
        contracts={
            ExecutionContract.DETERMINISTIC,
            ExecutionContract.NON_DETERMINISTIC,
        },
        max_vector_size=4096,
        metrics={"l2"},
        deterministic_query=True,
        replayable=True,
        isolation_level="process",
        ann_support=True,
        supports_ann=True,
    )
    stores = ExecutionResources(
        name="sqlite",
        vectors=SQLiteVectorSource(conn, lock),
        ledger=SQLiteExecutionLedger(conn, lock),
        capabilities=capabilities,
    )
    diagnostics = {
        "health_check": lambda: {"status": "ok", "engine": "sqlite", "path": db_path},
        "capacity": lambda: {
            "documents": conn.execute("SELECT COUNT(1) FROM documents").fetchone()[0],
            "chunks": conn.execute("SELECT COUNT(1) FROM chunks").fetchone()[0],
            "vectors": conn.execute("SELECT COUNT(1) FROM vectors").fetchone()[0],
        },
        "corruption_check": lambda: conn.execute("PRAGMA integrity_check").fetchone(),
    }
    fixture = SQLiteFixture(
        tx_factory=tx_factory,
        stores=stores,
        authz=AllowAllAuthz(),
        name="sqlite",
        ann=None,
        diagnostics=diagnostics,
    )
    try:
        from bijux_vex.infra.adapters.ann_hnsw import HnswAnnRunner

        fixture = fixture._replace(ann=HnswAnnRunner(stores.vectors))
    except Exception:
        try:
            from bijux_vex.infra.adapters.ann_reference import ReferenceAnnRunner

            fixture = fixture._replace(ann=ReferenceAnnRunner(stores.vectors))
        except Exception:
            fixture = fixture._replace(ann=None)
    return fixture
