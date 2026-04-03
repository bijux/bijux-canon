# bijux-vex — read this first

bijux-vex is a **vector execution engine**. It **MUST** run vector computations under explicit execution contracts, record the consequences, and make determinism vs. non-determinism auditable.

## What vector execution means
- Inputs are execution requests (text or vectors) routed through explicit plans.
- Backends are **execution substrates**, not storage layers.
- Artifacts are replayable records of how execution happened, not generic indexes.

## Deterministic vs non-deterministic contracts
- Deterministic: bit-stable, replay **MUST** match exactly, no hidden randomness **MAY** exist.
- Non-deterministic (experimental): randomness **MUST** be declared, bounded, and audited; replay **MUST** check distributional consistency within declared bounds.

## Why ANN is treated as execution (not indexing)
- ANN choices (graph walks, sampling, pruning) **MUST** be treated as execution-time decisions.
- Backends **MUST** refuse deterministic contracts when they cannot honor exactness.
- Approximation metadata (**MUST** include randomness sources and reproducibility bounds) is part of the execution artifact.

## Replay as a first-class invariant
- Replay **MUST** mean “re-run the same execution plan under the same contract.”
- Deterministic replay ⇒ equality; non-deterministic replay ⇒ declared envelope.
- Provenance chains **MUST** include contract, randomness profile, and artifact signature.

## Typing philosophy
- Runtime contracts and invariants are primary; static typing is advisory.
- Type checkers **MUST NOT** be treated as soundness gates. Invariants, provenance, and conformance tests enforce correctness.
- `ExecutionIntent` is represented canonically as intent strings (`exact_validation`, `reproducible_research`, `exploratory_search`, `production_retrieval`); the enum is a convenience veneer only.

All other spec documents link back here as the canonical mental model.
