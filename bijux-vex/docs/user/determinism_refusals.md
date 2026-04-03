# Determinism Refusal Guide

## Why this exists

Refusals are how the system protects you from hidden correctness failures. They are not errors to “work around.” They are early warnings that the execution you asked for cannot be trusted.

If you ignore refusals, you get silent approximation, misleading audits, and outputs that cannot be explained later. This section is for anyone who needs defensible results in production.

## Story / scenario

A team ships a fix, but results still drift. The root cause is an ANN index used in a deterministic path. A refusal would have made this visible immediately.

## What usually goes wrong

- Teams assume a backend can do exact search.
- ND features creep into deterministic execution.
- Replay is attempted without matching artifacts.

## How Bijux-Vex handles it

The system refuses with a structured payload and remediation guidance.

## What trade-offs remain

- Some refusals require you to rebuild indexes or switch modes.
- There is no “force” flag for deterministic correctness.

## Where to go deeper

- `docs/user/deterministic_replay.md`
- `docs/user/determinism_end_to_end.md`

---

Common refusal reasons

- `backend_capability_missing`: The selected backend does not support deterministic exact.
- `determinism_violation`: A requested mode or component is non-deterministic.
- `index_mismatch`: Index hash or parameters do not match the artifact.
- `randomness_required`: ND-only randomness was requested under deterministic contract.

Example refusal payload

```json
{
  "error": {
    "reason": "determinism_violation",
    "message": "[INV-203] What happened: deterministic execution requested with ANN index.\nWhy: ANN is non-deterministic.\nHow to fix: use exact index or switch to ND contract.\nWhere to learn more: docs/user/determinism_refusals.md",
    "remediation": "Use exact mode or explicitly request ND with bounds."
  }
}
```

How to resolve

- Use an exact backend and exact index mode.
- Remove ANN-only flags.
- Rebuild artifacts to match the expected configuration.

When override is allowed

- Deterministic refusals are not overridable. If you need approximation, use ND explicitly.

## Common misunderstandings

- “Refusals mean the system is broken.” They mean the system is protecting you.
- “I can just retry.” If the inputs are wrong, retrying won’t help.
- “It’s safe to ignore the warning.” It is not safe if you need correctness.
