# Non-deterministic execution (ND) semantics

ND execution is **first-class** at the contract level but remains **experimental** in behavior in v0.2.x. It is not a best-effort mode.

- Inputs and parameters **must be deterministic** (explicit seeds, declared randomness sources).
- Allowed divergence: ranking/score differences within declared approximation bounds; provenance must record randomness sources.
- Replay semantics: distribution-consistent. Replays MUST emit divergence envelopes, not equality, and MUST fail if randomness metadata is missing.
- Backends MUST declare whether they support ND; refusal is contractual, not an invariant failure.
- ND execution MAY legally fail with `NDExecutionUnavailableError` if no ANN backend is available; callers must provide ANN support or choose deterministic contracts.
- Every ND result MUST include:
  - `ApproximationReport` (recall, displacement, distance error, algorithm, backend, randomness_sources, fallback flag)
  - `DeterminismReport` with reproducibility bounds and randomness used.

Code mapping: see `src/bijux_vex/core/contracts/execution_contract.py`, `src/bijux_vex/domain/execution_requests/postprocess.py`, `src/bijux_vex/domain/provenance/replay.py`, `tests/conformance/test_execution_contracts.py`.
