# Deterministic Replay

## Why this exists

Replay is how you prove that a result is real and repeatable. Without replay, you can’t audit, you can’t compare changes safely, and you can’t trust regression tests.

If you skip replay, you risk shipping changes that look fine in one run and break quietly later. This section is for teams that care about evidence, not guesses.

## Story / scenario

A ranking change seems safe, but users complain a week later. Replay against the original artifact would have shown the drift immediately.

## What usually goes wrong

- Artifacts are rebuilt implicitly, changing the index.
- Backends change versions without tracking it.
- Replay is attempted with a different config.

## How Bijux-Vex handles it

Replay is allowed only when fingerprints match. Otherwise it refuses with a precise reason.

## What trade-offs remain

- Replay requires stable artifacts and storage.
- Some environments cannot guarantee the same backend versions.

## Where to go deeper

- `docs/user/determinism_refusals.md`
- `docs/user/determinism_end_to_end.md`

---

When replay is allowed

- Same artifact ID and index hash.
- Same backend signature and parameters.
- Same execution contract and intent.

When replay is refused

- Index hash mismatch.
- Backend version mismatch that invalidates determinism.
- Configuration or parameter drift.

How fingerprints are checked

- Vector fingerprints ensure the corpus is identical.
- Config and algorithm fingerprints ensure the plan matches.
- Backend signature ensures the same deterministic guarantees.

What “matches” means

- Deterministic results must be **bit-identical** and ordered by the canonical query contract.
- Any deviation is reported as a mismatch with a structured refusal.

## Common misunderstandings

- “Replay is just re-running the request.” It also requires matching artifacts and hashes.
- “Close enough is fine.” Deterministic replay is exact by definition.
- “Replay is optional.” If you need audits, it is required.
