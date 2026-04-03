# Irreducible core (must survive any refactor)

Non-negotiable invariants:
1) Contract alignment (INV-010): artifact and request execution_contract must match; enforced in planning and replay.
2) Determinism declaration (INV-020): ND execution requires explicit randomness + budget; deterministic path forbids ANN.
3) Provenance requirement (INV-040): replay only legal with stored execution result and matching contract/ABI.
4) Plan immutability: ExecutionPlan fingerprint ties algorithm+contract+k+randomness; mutation invalidates execution.
5) Ledger integrity: artifacts/results persisted with signatures; deletion/compaction must preserve chain hashes.

Minimum modules to enforce:

- `core/runtime/execution_plan.py` (plan fingerprint, randomness labels)
- `core/runtime/execution_session.py` (state machine, contract alignment)
- `core/contracts/execution_contract.py` + `core/contracts/determinism.py`
- `domain/execution_requests/plan.py` (capability + contract checks)
- `domain/provenance/replay.py` (provenance gate)
- `core/invariants.py` + `core/contracts/invariants.py` (guardrails)

Everything else is supportive. If removed, these must remain intact for vex to stay itself.
