# Architecture invariants (spec)

These invariants preserve the system boundary and auditability.

## Separation of concerns

- Orchestration MUST live in the pipeline runner, not in agents.
- Agents MUST be pure workers: given an input contract, return an output contract.

## Artifact ownership

- Final artifacts (`final_result.json`, `run_trace.json`) MUST be written by the orchestrator/finalize layer.
- Agents MUST NOT write or mutate run artifacts directly.

## Statelessness

- The system MUST NOT require persistent state across runs.
- Any optional caching MUST be explicitly documented and must not change semantics when absent.

## Schema discipline

- Trace schema and agent output schema are compatibility gates; breaking changes require version bumps.
