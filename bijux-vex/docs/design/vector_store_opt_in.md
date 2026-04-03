# Vector Store Opt-In Design (explicit only)

This design prevents silent persistence. Vector store usage must be explicit in both CLI and API.

## CLI
- Flag: `--vector-store <name>`
- Default is local memory when the flag is omitted.
- External vector stores are only used when `--vector-store` is set.

## API
- Field: `vector_store` in execution/materialization payloads.
- Omission means **no external store** (local memory only).

## Behavior
- If `vector_store` is set, the adapter is used for persistence/query.
- If `vector_store` is not set, the system uses only the execution ledger and in-memory/vector sources.
- No silent fallback between stores.

## Rationale
- Guarantees that persistence is always explicit.
- Prevents accidental data retention or storage semantics being inferred.
- Aligns with the “Nothing Is Implicit” contract.
