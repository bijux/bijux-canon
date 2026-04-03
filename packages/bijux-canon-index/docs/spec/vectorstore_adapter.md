# VectorStoreAdapter (interface contract)

This is the explicit adapter surface for external vector stores. v0.2.0 includes a local FAISS adapter and a no-op adapter for explicit memory routing.

## Interface
Location: `src/bijux_vex/infra/adapters/vectorstore.py`

Methods:

- `connect()`
- `insert(vectors, metadata)`
- `query(vector, k, mode)`
- `delete(ids)`

## Contract notes
- No defaults: adapters must be selected explicitly (see `docs/design/vector_store_opt_in.md`).
- No silent fallbacks: failures are terminal and must surface as explicit errors.
- Adapter implementations live under `src/bijux_vex/infra/adapters/`.
- Registry: `src/bijux_vex/infra/adapters/vectorstore_registry.py` resolves adapters by name.
