# Execution artifacts

An execution artifact records **what ran and how**:

- links to corpus + vector fingerprints
- execution contract and plan fingerprint
- randomness audit (sources, budget)
- approximation + determinism reports
- execution signature tying all of the above

Portability guarantees:

- Artifacts are versioned; compatibility is enforced by the execution ABI.
- Replay does not require live vector sources; artifacts plus plan are sufficient.
- Backends must refuse execution if they cannot meet the artifact’s contract/metric.

Mutation rules:

- Artifacts are immutable once committed.
- Ledger retention may prune historical results but preserves chain hash integrity.

Docs → code

- `src/bijux_vex/core/execution_result.py`
- `src/bijux_vex/core/abi/__init__.py`
- `src/bijux_vex/domain/execution_artifacts/`
