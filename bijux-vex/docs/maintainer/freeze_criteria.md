# Freeze criteria (v0.1.0)

Freeze is allowed only when all gates are satisfied:

- Core decomposition in place (contracts/runtime/policies/types/identity) with no file >300 LOC doing mixed responsibilities.
- Services contain glue only; decision logic delegated to commands/domain.
- Test tree mirrors src tree 1:1.
- Adversarial execution scenarios pass (drift-within-bounds, corruption replay refusal, budget exhaustion).
- Failure semantics and invariants documented and enforced by tests.
- No TODO/FIXME in `src/bijux_vex/core`.
- Docs: mental_model, failure_semantics, vdb_profile present and linked in doc map.
- All gates: `make test lint quality security` green.
- Exclusions honored: `pgvector_backend` remains excluded (see `core/v1_exclusions.py`).
- Deterministic execution surface and ABI are frozen; breaking deterministic changes require a major version bump.
- Non-deterministic/ANN execution is **experimental** and may change; users must treat ND behavior as unstable.
- Posture: bijux-vex is **contract-complete** and open to empirical refinement; feature changes must be framed as contract extensions and approved through freeze governance.

Kill-switch: if any criterion fails, release tagging is blocked and freeze is revoked.
