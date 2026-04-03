# Execution lifecycle (spec)

The canonical pipeline lifecycle exists to make traces semantically stable across refactors.

## Canonical phases

| Phase | Purpose | Allowed transitions |
| --- | --- | --- |
| `INIT` | Pre-run validation and context normalization | `PLAN` |
| `PLAN` | Planning / decomposition (if enabled) | `EXECUTE` |
| `EXECUTE` | Main agent execution | `JUDGE` |
| `JUDGE` | Convert agent outputs into a decision | `VERIFY` |
| `VERIFY` | Optional verification / veto checks | `FINALIZE` |
| `FINALIZE` | Emit final artifacts and trace metadata | `DONE` |
| `DONE` | Terminal | (none) |
| `ABORTED` | Terminal for fatal aborts | (none) |

Allowed transitions are defined in code by the canonical pipeline definition.

## Stop reasons and termination

The system records:

- stop reasons (why a phase stopped), and
- termination reasons (why the overall run ended)

Termination reasons are part of `final_status` and are also recorded in trace entries when present.

## Trace expectations

- A trace MUST contain at least one entry.
- Entries SHOULD be tagged with the phase they correspond to when available.

See also:

- `docs/spec/execution_artifacts.md`
- `docs/spec/failure_semantics.md`
