# Execution contracts

## Deterministic execution
- MUST guarantee bit-stable results.
- MUST NOT include hidden randomness or approximate paths.
- Replay MUST match exactly; any divergence is an invariant failure.
- Backends MUST declare `deterministic_query=True` and MUST refuse if they cannot meet it.

## Non-deterministic execution
- Contract is stable; behavior remains **experimental** until ANN graduation criteria are met.
- REQUIRES:
  - `RandomnessProfile` (seed, sources, boundedness, budget)
  - `DeterminismReport` persisted with every result
  - `ApproximationReport` (recall, rank displacement, distance error, algorithm, backend, randomness sources, fallback flag)
- Replay MUST compare within declared bounds (distribution-consistent), not equality.
- See `docs/spec/non_deterministic_execution.md` for the full semantics.

## Allowed sources of nondeterminism
- Graph traversal order.
- Sampling/beam heuristics.
- Parallelism-induced ordering changes.
All MUST be named in the plan via `RandomnessSource`.

## Comparison semantics
- Exact vs approximate comparisons MUST measure recall@k, rank instability, overlap ratio.
- Policies MAY gate approximate runs: minimum recall, maximum instability.

## Versioning rationale
- ABI versioning exists to keep deterministic replay stable across refactors.
- Canon versioning exists to keep fingerprints and hashing rules stable for provenance chains.
- Schema versioning (API/OpenAPI) exists to keep external integrations honest; breaking changes require a new major API version.

## Doc → code map
- Contracts: `src/bijux_vex/core/contracts/__init__.py`
- Randomness profile: `src/bijux_vex/core/vector_execution.py`
- Reports: `src/bijux_vex/core/execution_result.py`
- Enforcement: `src/bijux_vex/domain/execution_requests/execute.py`, `plan.py`
