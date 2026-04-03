# What WILL break compatibility

Changes that REQUIRE a major version bump:

- Changing deterministic execution semantics or ABI.
- Removing or renaming public API modules: `bijux_vex.core.types`, `bijux_vex.core.contracts.execution_contract`, `bijux_vex.core.runtime.vector_execution`, `bijux_vex.contracts.resources`, `bijux_vex.services.execution_engine`, `bijux_vex.api.v1`.
- Changing public error types or their messages for deterministic paths.
- Changing OpenAPI v1 schema in a non-additive way.
- Altering provenance structure such that existing artifacts cannot be replayed/validated.

Changes that do NOT require a major bump (but still need tests/docs):

- Additive OpenAPI v1 fields with safe defaults.
- New internal modules or refactors that do not touch public surfaces.
- Performance improvements that preserve deterministic behavior and ND envelopes.
- Additional examples or docs that do not alter contracts.
