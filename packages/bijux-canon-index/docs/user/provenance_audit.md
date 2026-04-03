# Provenance as an Audit Narrative

## Why this exists

When something goes wrong, “the system said so” is not an explanation. Provenance tells you **what happened**, **why it happened**, and **what was refused** so you can defend your results.

Without provenance, incidents become guesswork. With it, you have evidence.

## Story / scenario

A customer asks why results changed between two runs. Provenance shows the exact index hash, configuration, and randomness declaration that changed.

## What usually goes wrong

- Provenance is treated as optional logging.
- Results are stored without the plan that produced them.

## How Bijux-Vex handles it

Provenance is emitted for every execution and includes the decisions and artifacts needed to audit results.

## What trade-offs remain

- Provenance adds storage overhead.
- Some details require careful redaction.

## Where to go deeper

- `docs/user/failure_modes_safety.md`
- `docs/user/deterministic_replay.md`

---

Structure

- Inputs: vectors, documents, and configuration.
- Decisions: runner selection, budgets, parameters.
- Randomness: seeds and declared sources.
- Artifacts: index hash, corpus fingerprint, and execution IDs.

How to store

- Treat provenance as immutable audit data.
- Store alongside results and configuration snapshots.

How to compare

- Compare fingerprints to verify deterministic replay.
- Compare ND quality metrics to track stability over time.

Retention strategies

- Keep provenance for all production runs.
- For large volumes, store summaries and reference full artifacts by ID.

How provenance answers “why did this happen?”

- It records the exact plan and parameters used.
- It shows whether any degradation or refusal occurred.

## Common misunderstandings

- “Provenance is just logs.” It is structured, queryable evidence.
- “Provenance is optional.” It is a core contract.
- “It’s too verbose to use.” Summaries can be stored while full data is retained.
