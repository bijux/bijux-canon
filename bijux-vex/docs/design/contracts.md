# bijux-vex v1 Contract Spec

bijux-vex is a contract-driven vector execution system with explicit determinism semantics. Every surface binds to a small set of contracts; anything outside these contracts is rejected.

## Canonicalization + IDs
- Canonical bytes and fingerprints are stable and versioned.
- Modules: `src/bijux_vex/core/canon.py`, `src/bijux_vex/core/ids.py`, `src/bijux_vex/core/types.py`.

## Tx + authz + audit
- All mutations run inside a `Tx`, with explicit authz checks and tamper-evident audit chaining.
- Modules: `src/bijux_vex/contracts/tx.py`, `src/bijux_vex/contracts/authz.py`, `src/bijux_vex/domain/provenance/audit.py`.

## ExecutionArtifact
- Portable description of an execution artifact: fingerprints, metric, scoring version, `ExecutionContract`, and replayability.
- Modules: `src/bijux_vex/core/types.py` (`ExecutionArtifact`), `src/bijux_vex/core/ids.py`, `src/bijux_vex/core/invariants.py`.

## ExecutionRequest determinism
- Identical execution requests over identical corpora yield identical ranked results under the deterministic contract.
- Modules: `src/bijux_vex/core/types.py`, `src/bijux_vex/domain/execution_requests/scoring.py`, `tests/conformance/execution_request_determinism.py`.

## Explainability + replay
- Results must be explainable doc→chunk→vector→artifact→score with provenance that carries `execution_contract`, `nondeterministic_sources`, and `lossy_dimensions`.
- `ReplayOutcome` declares divergence; deterministic runs must match, non-deterministic runs must mark lossiness.
- Modules: `src/bijux_vex/domain/provenance/audit.py`, `src/bijux_vex/domain/provenance/lineage.py`, `src/bijux_vex/domain/provenance/replay.py`, `tests/conformance/test_execution_contracts.py`.

## Backend isolation
- Backend-specific knobs stay below `src/bijux_vex/infra/adapters/`.
- Forbidden leakage: backend table names, ANN parameters, backend-native IDs, or backend-specific consistency/authz semantics.
- Adapters translate contracts to backend knobs; the conformance suite must run unchanged across backends.
