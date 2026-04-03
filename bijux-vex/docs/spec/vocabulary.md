# Vocabulary (authoritative)

- Execution: interpreting an `ExecutionPlan` under an `ExecutionContract` against a `VectorSource`, producing an `ExecutionResult` + provenance.
- ExecutionPlan: immutable plan describing algorithm, contract, k, scoring, randomness sources, bounds; fingerprinted.
- ExecutionSession: lifecycle holder (state machine) tying plan + artifact + randomness + budget.
- Artifact: `ExecutionArtifact` linking corpus/vector fingerprints to execution signature; persisted in ledger.
- Provenance: ledger records (artifacts, results, audit chain) required for replay and comparison.
- Determinism: contract dimension; deterministic ⇒ bit-identical replay; non_deterministic ⇒ bounded divergence with `DeterminismReport`.
- Replay: re-running an execution with the same contract/ABI; deterministic checks equality, ND checks envelope. Replayable does **not** mean cached; it means re-execution is possible under the same contract.
- Comparison: structured diff between executions (overlap, recall delta, rank instability), exact vs approximate.
- Execution fidelity: mode expressing how close results adhere to exact semantics (deterministic exact vs ND approximate).
- Stability: deterministic surfaces are frozen; ND/ANN is **stable_bounded** at the contract level but **experimental** in behavior (outcomes vary within declared envelopes).
- Reproducibility: ability to recreate execution behavior under the same contract/plan/randomness (deterministic ⇒ equality, ND ⇒ bounded envelope).
