# Why agentic-flows exists

Agentic-flows targets a gap that general agent frameworks leave open: auditable execution with explicit contracts, replayability, and invariant enforcement. Typical frameworks optimize for flexibility and rapid iteration, but they do not treat execution traces, datasets, and policy decisions as contractual artifacts. That makes it hard to prove what happened, why it happened, or whether a run can be reproduced under the same declared conditions.

Determinism and replay are the core thesis because they turn execution into a verifiable record. A deterministic run with a replay envelope can be checked against stored traces, hashes, and policies without reinterpreting logs or inferring intent. This supports governance, debugging, and compliance workflows that require stable evidence rather than best-effort behavior.

This system is not for teams seeking interactive chat UX, rapid prompt experimentation, or non-reproducible exploration. It is also not a general-purpose agent runtime or a planner framework; it assumes a contract-first model and emphasizes auditability over convenience. If you need adaptive behavior without strict replay guarantees, this is the wrong tool.
