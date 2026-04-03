# Contributor Architecture & Invariants

This guide explains where guarantees live and how to extend Bijux-Vex safely.

Core invariants

- Deterministic execution is exact and replayable.
- ND execution must declare randomness and bounds.
- No silent fallbacks or implicit defaults.
- Provenance is always emitted for executed requests.

Where logic must never go

- Do not embed policy decisions inside adapters.
- Do not bypass ND planning in runners.
- Do not emit unstructured errors.

How to add a vector store

- Implement the adapter interface.
- Declare capabilities and consistency semantics.
- Add redaction rules for credentials.
- Add conformance tests.

How to add an ND runner

- Declare determinism characteristics and randomness sources.
- Implement budget enforcement and parameter mapping.
- Emit ND quality metrics and confidence labels.

How to add an embedding provider

- Declare determinism status.
- Emit full provider metadata.
- Respect caching and redaction rules.

Running the full test suite safely

- `make lint quality security test docs api`
- Install extras for FAISS, Qdrant, and ND runners if you want all tests to run.
