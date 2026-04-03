# Glossary

- **Document**: Source text unit provided by users.
- **Chunk**: Deterministic slice of a document with stable ordinal.
- **Vector**: Numeric representation associated with a chunk and model.
- **ExecutionArtifact**: Portable description of an execution build and its provenance.
- **ExecutionContract**: Required determinism contract for every artifact and execution request.
- **Backend**: Adapter implementation of execution resources.
- **Tx**: Transaction boundary required for any mutation.
- **Authz**: Authorization hook invoked before mutations.
- **AuditRecord**: Tamper-evident record chaining mutation history.
- **Determinism**: Contract where replay MUST be bit-identical; hidden randomness forbidden.
- **Non-determinism**: Contract where randomness MUST be declared; replay checks envelopes, not equality.
- **Replay**: Re-running the same plan under the same contract; deterministic ⇒ equality, ND ⇒ bounded envelope. Replayable means re-execution is possible, not that results are cached.
- **Stability**: Deterministic surfaces are frozen; ND/ANN is stable at the contract level but **experimental** in behavior (outcomes vary within declared bounds).
- **Reproducibility**: Ability to obtain the same execution behavior under the same plan/contract/randomness; stronger than “similar results.”
- **Determinism vs reproducibility**: determinism demands identical outputs; ND reproducibility means divergence stays within the recorded approximation envelope.
