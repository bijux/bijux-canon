# VEX stance on vector DB semantics

bijux-vex is **not** a vector database. It provides execution contracts, not storage guarantees. No `ExecutionProfile.VDB` exists for v0.2.0; any persistence semantics are limited to the execution ledger unless an explicit vector store adapter is selected.

Implications:

- No CRUD API for vectors beyond fixture ingestion.
- No serving/read/write SLAs.
- Any adapter exposing database-like APIs must document why it exists and must not claim DB parity.
