# Invariants

These are the truths the runtime package should keep even during deep refactors.

- replay and execution traces remain audit-oriented
- runtime owns execution authority and persistence semantics
- execution-store schema changes are intentional and versioned
- API and CLI surfaces reflect the same runtime contracts
