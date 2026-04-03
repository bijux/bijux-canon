# Concept Map

## Contracts
- **Execution contract** defines determinism and replay guarantees.
- **Implicitness contract** requires explicit opt-in for persistence and approximation.

## Determinism vs ANN
- **Deterministic**: bit-identical results when replayed.
- **ANN**: approximate results, explicitly labeled experimental until criteria are met.

## Storage vs Execution
- **Storage** holds documents, chunks, vectors, and artifacts.
- **Execution** runs algorithms over stored vectors under a declared contract.

## Provenance
- **Provenance** explains how a result was produced.
- **Embedding metadata** and **vector store metadata** must be present when used.

## Trust Boundaries
- Execution engine is deterministic only when every component declares determinism.
- External backends (VDB/ANN) must be explicitly configured.
