# Execution Contracts

bijux-vex supports two explicit execution contracts. There is no default: callers must choose the contract when materializing execution artifacts and when issuing execution requests.

## Deterministic
- Exact execution; vector scores are stable and tie-broken deterministically.
- Replayable: execution requests can be re-run and compared byte-for-byte via fingerprints.
- Execution artifacts and provenance record `execution_contract=deterministic` and remain fully explainable.

## Non-deterministic (ANN)
- Uses declared approximate runners; results may differ across runs even with identical inputs.
- Replay is allowed but must declare divergence via `nondeterministic_sources`, `lossy_dimensions`, and replay details.
- Treated as an operational escape hatch, not the primary mode; **experimental** until ANN graduation criteria are met. Deterministic and non-deterministic contracts cannot mix on the same artifact ID.

## Positioning
- Deterministic mode is the first-class experience and the baseline for conformance.
- ANN is opt-in per execution artifact and must refuse deterministic contracts.
- Provenance is never silent: lossy paths must describe why an exact replay is impossible.
