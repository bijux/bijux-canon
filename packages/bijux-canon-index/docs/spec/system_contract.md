# System contract

bijux-canon-index is a **vector execution engine**. The following requirements are normative:

- The system **MUST** treat vector execution as the core unit; storage is supporting only.
- Deterministic executions **MUST** be bit-stable and **MUST NOT** contain hidden randomness.
- Non-deterministic executions **MUST** declare randomness sources, budgets, and reproducibility bounds; replay **MUST** verify within those bounds.
- Non-deterministic/ANN behavior is **experimental** until ANN graduation criteria are met.
- Replay **MUST** mean re-running the same plan under the same contract; deterministic replay **MUST** match exactly, ND replay **MUST** stay within declared envelopes.
- Backends **MUST** refuse contracts they cannot honor.
- Absence of an ANN backend is a valid state; ND requests MAY fail with a contractual capability error (`NDExecutionUnavailableError`).
- bijux-canon-index **MUST NOT** position itself as a vector DB, embedding system, RAG stack, or serving layer.
- Public API modules (stable): `bijux_canon_index.core.types`, `bijux_canon_index.core.contracts.execution_contract`, `bijux_canon_index.core.runtime.vector_execution`, `bijux_canon_index.contracts.resources`, `bijux_canon_index.application.engine`, `bijux_canon_index.api.v1`. Everything else is internal.

Any code path or API that violates these statements is a defect.
