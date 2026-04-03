# bijux-vex is not a vector DB

bijux-vex is an execution engine, not a storage system. It does **not** provide vector DB semantics by default.

## What it is not
- No storage contract: the execution ledger is provenance, not a database.
- No serving guarantees: latency/availability are not SLAs; budgets are for experiments.
- No CRUD API beyond ingestion for execution-scoped artifacts.
- Determinism and nondeterminism are **execution contracts**, not storage modes.

## What it can integrate with (explicitly)
- External vector stores can be wired in **only via explicit opt-in**.
- There is no silent persistence or implicit vector store selection.
- If you need multi-tenant storage, use a vector DB and run bijux-vex for audited execution only.

## Replay clarity
- ANN replay is not equality: ND executions record envelopes and audit; replay validates envelopes, not ANN equality.
