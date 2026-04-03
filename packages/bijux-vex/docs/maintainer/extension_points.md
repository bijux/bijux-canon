# Extension points (public seams)

Allowed:

- New adapters implementing `contracts.resources.VectorSource`/`ExecutionLedger` respecting ExecutionContract capabilities.
- New ANN runners subclassing `AnnExecutionRequestRunner` that declare randomness sources, bounds, and deterministic fallback policy.
- New execution algorithms registered via `domain.execution_algorithms.base.register_algorithm` that respect contract compatibility.
- Plugins discovered via entrypoints: `bijux_vex.vectorstores`, `bijux_vex.embeddings`, `bijux_vex.runners`.

Forbidden:

- Injecting execution logic into services or boundaries layers.
- Extending public API without corresponding spec coverage and invariant IDs.
- Mutating provenance or ledger entries post-commit.

Warnings (will break determinism if abused):

- Randomness sources not surfaced in `DeterminismReport`.
- Adapters claiming deterministic support while using approximate paths.
- Bypassing `ExecutionSession`/`ExecutionPlan` when executing.
