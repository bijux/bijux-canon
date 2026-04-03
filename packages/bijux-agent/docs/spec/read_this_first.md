# Read this first (spec)

This section is the **normative** contract for Bijux Agent: what the system guarantees, what it refuses to do, and how consumers can safely integrate.

If you are looking for “how do I run it?”, start in `docs/user/usage.md` instead.

## How to read the spec

- **MUST**: required for correctness and contract tests
- **SHOULD**: strong recommendation; deviations must be explicit
- **MAY**: optional

The spec is intentionally narrow: it binds runtime behavior, artifacts, and failure semantics.

## What is covered

- the canonical pipeline (`AuditableDocPipeline`)
- CLI run artifacts (`final_result.json`, `run_trace.json`)
- API v1 execution behavior

## What is not covered

- model quality
- latency/cost
- UI/UX stability
- provider availability

## Start here

1. `docs/spec/system_contract.md` — system-level guarantees and boundaries
2. `docs/spec/execution_artifacts.md` — what is written and how to interpret it
3. `docs/spec/failure_model.md` and `docs/spec/failure_semantics.md` — failure taxonomy and propagation
4. `docs/spec/invariants/core-invariants.md` — invariants that must remain true across refactors
