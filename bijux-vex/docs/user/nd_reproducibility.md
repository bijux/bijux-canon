# ND Reproducibility (Honest Version)

## Why this exists

ND is powerful but can be misleading if people assume replay means exact equality. This doc explains what ND can replay and what it cannot so teams don’t build false guarantees into their systems.

If you skip this, you risk audits that can’t be reproduced and decisions based on unstable results.

## Story / scenario

An incident review asks, “Why did the system show those results?” Without ND reproducibility bounds, the answer is guesswork.

## What usually goes wrong

- Seeds are omitted.
- Index hashes drift without being noticed.
- ND runs are treated as deterministic.

## How Bijux-Vex handles it

ND can be reproducible **within bounds**, but it is not deterministic. Reproducibility depends on index hash, parameters, and randomness declarations.

## What trade-offs remain

- Replay may be refused if bounds are not met.
- Some backends cannot seed fully.

## Where to go deeper

- `docs/user/nd_parameters.md`
- `docs/user/nd_execution_model.md`

---

What can be replayed

- ND executions with explicit seeds and stable index hashes.
- ND runs with replayable bounds declared in provenance.

What cannot be replayed

- Runs without explicit randomness declarations.
- Runs where index hash or parameters drift.

Role of seeds

- If a runner supports seeding, the seed is mandatory for replay.
- If a runner cannot seed, the execution is marked non-replayable.

Index hashes

- ND replay requires matching index hash and corpus fingerprint.
- If hashes differ, replay is refused with a structured payload.

Reproducibility bounds

- ND provenance reports expected overlap or instability bounds.
- These bounds are the contract, not bit-identical equality.

## Common misunderstandings

- “ND replay is the same as deterministic replay.” It is not.
- “A seed guarantees identical results.” It only helps within bounds.
- “Reproducibility is optional.” It must be declared explicitly.
