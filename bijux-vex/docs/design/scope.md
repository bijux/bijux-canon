# Scope

bijux-vex delivers contract-driven vector execution semantics (not a database). v1 focuses on:

- deterministic canonicalization and IDs
- transactional mutation with authz + audit
- backend-agnostic execution resources and conformance suite
- reference memory + SQLite adapters with explicit execution contracts

Excluded (v1): streaming ingestion, distributed execution, on-device embedding inference, backend tuning controls above adapters.
