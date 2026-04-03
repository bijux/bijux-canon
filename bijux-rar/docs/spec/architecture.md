STATUS: EXPLANATORY
# Architecture
<a id="top"></a>

## Contracts
- Deterministic, content-addressed IDs (no UUID defaults)
- Canonical JSON + SHA256 fingerprints
- Pure invariants returning error lists
- Deterministic Trace JSONL serialization (header + event records)

## Planner (pure)
`ProblemSpec -> Plan` with deterministic decomposition:
`understand -> gather -> derive -> verify -> finalize`.
The flow is linear and acyclic; backedges are invalid.

Planner stores a structured `StepSpec` on each `PlanNode` (no free-form dict payloads).

## Executor (effectful, deterministic)
`Plan + Runtime -> Trace`:
- stable topological traversal
- emits structured trace events
- executes tool calls via a ToolRegistry
- emits structured claims and evidence registrations

No timestamps, no UUIDs, no environment dependence.

## Verification
`verify_trace(trace, plan)` is pure and produces a deterministic `VerificationReport`.

Checks include:
- core invariants (plan + trace)
- step completeness (required kinds, finished steps)
- tool linkage (tool_called must have tool_returned)
- claim support refs must resolve to known ids
- grounding check if evidence exists

## Replay and Diff
`replay_from_artifacts` re-runs a trace with the recorded spec/seed/runtime descriptor, writes a replay trace, and reports fingerprint and structural diffs for drift gating.

[Back to top](#top)
