# Mental model (non-negotiable)

This file is the single-page spine for bijux-vex v0.1.0. Read this before any other doc.

## What an execution is

- A `VectorExecution` = `(ExecutionRequest + ExecutionPlan + ExecutionContract + VectorSource + RandomnessProfile + ExecutionSession)`.
- An execution always produces **two** artifacts: an immutable `ExecutionResult` (with cost + determinism report) and an `ExecutionArtifact` lineage entry in the ledger.
- Execution identity is `ExecutionSignature(request, plan, contract, randomness, parameters, vectors)` and is hash-stable.

## What is guaranteed

- If `ExecutionContract == DETERMINISTIC`, replay under the same signature MUST produce bit-identical results and matching `results_fingerprint`.
- If `ExecutionContract == NON_DETERMINISTIC` (experimental), replay MUST stay within declared `reproducibility_bounds` and emit a `DeterminismReport` describing randomness sources and bounds.
- Provenance is mandatory: replay is only legal when a stored `ExecutionResult` exists for the artifact.
- Budgets are enforced pre- and mid-plan; overruns result in `PARTIAL` status with `BudgetExceededError` provenance.

## What is not guaranteed

- No persistence semantics beyond the execution ledger; this is **not** a vector DB.
- No implicit fallbacks: ANN runners MUST declare bounds; deterministic fallbacks are explicit.
- No silent retries: `InvariantError` and ABI violations are terminal.
- No execution without declared contract, intent, and session randomness policy.

## Replay legality

- Legal replay requires: matching contract, stored `ExecutionResult`, and compatible ABI fingerprint.
- Deterministic replay: must produce identical `results_fingerprint`; mismatch is a failure.
- Non-deterministic replay: may diverge, but divergence MUST be recorded in `ReplayOutcome.details` and `DeterminismReport`.
- Replay is illegal if provenance is missing, contract mismatches, ABI fingerprint changed, or ledger is compacted past the required chain.
