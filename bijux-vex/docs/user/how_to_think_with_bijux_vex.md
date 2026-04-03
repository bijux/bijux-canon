# How to Think With Bijux‑Vex

Bijux‑Vex is a system for making **correctness a conscious decision**. The core habit it teaches is this: decide what you need to be true, then ask the system to enforce it.

Reasoning about correctness

- Decide which parts must be deterministic.
- Treat ND as a tool for speed, not truth.
- Require explicit randomness when approximation is used.

Choosing trade-offs

- If auditability matters, prefer deterministic execution and replay.
- If latency matters, use ND with explicit budgets and witness checks.

Debugging with provenance

- Use provenance to understand “what happened” and “why.”
- Compare fingerprints to explain differences between runs.

Evolving safely

- Change one variable at a time.
- Keep old artifacts for replay.
- When in doubt, let the system refuse and surface the mismatch.

This mindset turns vector search from guesswork into evidence.
