# Storage Model
> How persistence and dataset governance work together.

DuckDB is used as the canonical store because it provides durable, queryable, and audited execution records in one place. It enables strict schema enforcement and replay comparisons without ad-hoc serialization. This keeps execution history consistent across runs and environments.

DVC controls dataset identity, versioning, and immutability boundaries for replayable data. It is the single authority for dataset fingerprints and frozen artifacts. DuckDB records those identities but does not replace DVC as the dataset system of record.

Bypassing DVC breaks dataset provenance, invalidates replay guarantees, and makes stored runs unverifiable. It also severs the link between persisted runs and the dataset contract. The system treats such runs as invalid for replay acceptance.

## DuckDB Execution Model
> Operational guarantees you must respect.

- Single-writer: only one execution write store should hold the write lock per DB file at a time. Concurrent writers are undefined and may corrupt replay invariants.
- Advisory locking: the runtime relies on process-level coordination to avoid write conflicts. External orchestration must serialize writers.
- Replay isolation: replays read immutable traces. Do not mutate or vacuum historical tables between capture and replay.
