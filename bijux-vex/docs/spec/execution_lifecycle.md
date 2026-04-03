# Execution lifecycle (canonical)

Flow (text diagram):
`ExecutionSession.start` → `ExecutionPlan.build` → `execute_request` → `postprocess` → `ledger.persist` → `replay|compare`

Where invariants fire:

- Session start: contract alignment, capability checks (INV-010, capability invariants).
- Planning: randomness required for ND (INV-020), ABI compatibility.
- Execute: budget enforcement, ANN refusal for deterministic.
- Postprocess: determinism/approximation reports attached.
- Ledger persist: artifact/signature immutability.
- Replay: provenance required (INV-040); deterministic equality vs ND envelope.

Determinism enforcement:

- Contract split before algorithm selection.
- ND requires randomness profile + budget; deterministic forbids ANN paths.
- Replay checks `results_fingerprint` (deterministic) or divergence envelope (ND).

Artifacts and provenance:

- ExecutionResult stores plan, cost, approximation, determinism report, fingerprints.
- ExecutionArtifact ties corpus/vector fingerprints to execution signature.
- Ledger retention may compact but must preserve chain hashes.

Docs → code

- `src/bijux_vex/core/runtime/execution_plan.py`
- `src/bijux_vex/core/runtime/execution_session.py`
- `src/bijux_vex/domain/execution_requests/plan.py`
- `src/bijux_vex/domain/execution_requests/execute.py`
- `src/bijux_vex/domain/provenance/replay.py`
