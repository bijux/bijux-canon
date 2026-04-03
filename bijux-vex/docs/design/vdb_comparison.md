# Why bijux-vex is not a vector DB (concrete comparison)

bijux-vex is an execution engine; vector DBs are storage/serving systems. Key differences:

- Contracts first: every execution declares determinism vs non-determinism; vector DBs often hide approximation trade-offs.
- Replay semantics: deterministic replay is enforced; ND replay is envelope-validated. Most vector DBs offer best-effort behavior without provenance.
- Provenance: executions emit lineage, randomness, and approximation metadata as a first-class artifact; vector DBs treat queries as transient.
- Capability honesty: backends must declare support for ND and determinism; vector DBs frequently downgrade silently.
- No CRUD semantics: bijux-vex does not expose database operations; ingestion/materialization are execution-scoped, not general storage APIs.

Use bijux-vex when you need audited, contract-bound vector execution. Use a vector DB when you need a managed serving tier with CRUD and scale-out storage.
