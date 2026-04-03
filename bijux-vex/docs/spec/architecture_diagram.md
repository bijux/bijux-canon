# Architecture diagram (single source)

Textual diagram:

`CLI/API → Orchestrator (glue only) → ExecutionSession (state machine) → ExecutionPlan (immutable) → Algorithm (exact/approx mode)`

`Algorithm → Adapters (VectorSource, ExecutionLedger, ANN runner, optional VectorStoreAdapter) → ExecutionResult + Provenance → Ledger`

`Optional VectorStoreAdapter → External VDB (explicit opt-in)`

Contracts/invariants hit:

- Contract alignment (INV-010) at session start
- Randomness/budget required for ND (INV-020) in planning
- Plan immutability/fingerprint in ExecutionPlan
- Determinism enforcement pre-algorithm selection
- Provenance requirement on replay (INV-040)
- Ledger integrity on persist/replay

Trust boundaries:

- CLI/API input is untrusted; validation happens at the boundary.
- Adapter boundary is a trust boundary; external VDBs are **not** trusted by default.
- Optional VDB usage requires explicit opt-in and must not silently fall back.
