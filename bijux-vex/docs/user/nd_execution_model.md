# ND Execution Model Explained

## Why this exists

ND is where speed meets uncertainty. It powers real workloads like search and recommendations, but it can also hide risk if treated casually. This doc explains ND as a **tool with boundaries**, not a warning label.

If you skip this, you may ship fast results that drift, weaken audits, or behave unpredictably under load. This section is for engineers and operators who want speed without losing control.

## Story / scenario

A recommendation pipeline switches to ANN for scale. Latency drops, but results become unstable and user behavior changes. Without ND visibility, the team can’t explain why.

## What usually goes wrong

- Approximation is introduced without explicit bounds.
- Randomness is not declared or tracked.
- Budgets are exceeded silently.

## How Bijux-Vex handles it

ND (non-deterministic) execution is an **explicit** mode with declared randomness, bounded quality, and refusal when bounds are violated.

## What trade-offs remain

- ND is not bit-replayable.
- Higher quality usually costs latency.

## Where to go deeper

- `docs/user/nd_quality_confidence.md`
- `docs/user/nd_reproducibility.md`
- `docs/user/nd_parameters.md`

---

ND planning

- Selects a runner based on capabilities and configuration.
- Resolves parameters from explicit profiles or tuning output.
- Applies budgets and refusal rules before execution.

Runner selection

- The system chooses the best available ND runner.
- If no runner can satisfy the requested capabilities, ND refuses.

Parameters and budgets

- Parameters are explicit or resolved from profiles.
- Budgets bound latency, memory, and candidate exploration.

Degradation and refusal

- ND may degrade only through explicit policies.
- If bounds are exceeded or determinism rules are violated, ND refuses.

## Common misunderstandings

- “ND is just faster exact.” It is approximate and must be treated as such.
- “Seeds make ND deterministic.” Seeds help but do not replace bounds.
- “ND doesn’t need provenance.” ND needs provenance even more.
