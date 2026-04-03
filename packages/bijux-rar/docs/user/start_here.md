
## START HERE (15 minutes)
STATUS: EXPLANATORY

What this solves (2 min):
- Produces verifiable reasoning traces: plans → evidence → claims → verification → replay with drift detection.

What you must know first (5 min):
- Read [read_this_first.md](../spec/read_this_first.md) (hostile gatekeeper).
- Read [mental_model.md](../spec/mental_model.md) (concept map, no code).
- Read [execution_flow.md](../spec/execution_flow.md) (one linear pass).

Exact reading order with time estimates (8 min):
1. [state_and_artifacts.md](../spec/state_and_artifacts.md) (1 min)
2. [trace_format.md](../spec/trace_format.md) (2 min)
3. [trace_lifecycle.md](../spec/trace_lifecycle.md) (1 min)
4. [core_contracts.md](../spec/core_contracts.md) (2 min)
5. [determinism.md](../spec/determinism.md) (1 min)
6. [verification_model.md](../spec/verification_model.md) (1 min)

If you disagree with these constraints, stop here. This system is not for you.

Do NOT continue unless you accept span+hash grounding, deterministic replay, and fail-closed verification.***

## What is NOT guaranteed
- Performance beyond documented benchmarks.
- Compatibility with undocumented runtimes or tooling.
- Acceptance of partial artifacts or ungrounded claims.
- Support for improvisational workflows outside the documented pipeline.
