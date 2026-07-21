---
title: Failure Recovery
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Failure Recovery

Recovery starts from the last trustworthy controller state, not from the role
that happened to log last. `bijux-canon-agent` owns an ordered lifecycle and
writes a result/trace evidence pair; both are needed to decide whether a run
can be accepted, replayed, or safely retried.

```mermaid
flowchart TD
    incident[Failed or suspect run] --> preserve[Preserve output root and logs]
    preserve --> pair{Result and trace readable?}
    pair -- no --> partial[Classify partial artifact write]
    pair -- yes --> terminal[Inspect termination and lifecycle]
    terminal --> class{Failure class}
    class -- transient --> retry[Retry full governed boundary]
    class -- contract or policy --> correct[Correct input or configuration]
    class -- deterministic defect --> repair[Repair implementation or provider contract]
    retry --> fresh[Write to a fresh output root]
    correct --> fresh
    repair --> fresh
    fresh --> validate[Validate trace, result, and replay fields]
```

## Stabilize Evidence

Before retrying, retain:

- `result/final_result.json`, when present;
- `trace/run_trace.json`, when present;
- the resolved configuration and input digest;
- structured logs, provider error details, and process exit status;
- package/runtime version and model metadata;
- output-directory listing, sizes, and modification times.

The two artifact files are written separately with ordinary filesystem writes.
There is no manifest, transaction marker, or atomic directory commit. A crash
can leave one missing or truncated, and reusing an output root can mix or
overwrite evidence. Preserve the suspect directory and recover into a new one.

## Locate the Failed Boundary

| Boundary | Evidence | Recovery decision |
| --- | --- | --- |
| bootstrap | exit status and credential/configuration error | correct environment; no unchanged retry |
| input | validation issues and input path | repair path, content, task goal, or contract |
| preparation | context/configuration hashes and required stages | correct configuration or deterministic preparation defect |
| stage execution | execution path, audit event, role error, attempt | retry only a classified transient failure |
| provider | stable error code, transient flag, timeout/throttle detail | apply bounded backoff or correct provider request |
| shard merge | shard statuses, warnings, merged score | rerun the governed execution after correcting the failed shard cause |
| convergence | iteration history, reason, window hash | accept recorded stop or change policy explicitly |
| verification | veto, validation issues, action plan | correct evidence or result; do not convert veto to success |
| finalization | terminal state, trace construction, write error | preserve partial output; rerun into a fresh root |
| replay | trace validation and field mismatch | investigate schema, runtime, model, prompt, or configuration drift |

The normal lifecycle is `INIT → PLAN → EXECUTE → JUDGE → VERIFY → FINALIZE →
DONE`; `ABORTED` is terminal. An invalid transition is a controller or trace
contract failure, not a reason to skip forward to the missing phase.

## Decide Whether to Retry

Retry only when the failure is explicitly transient and repeating the complete
governed boundary cannot duplicate an external side effect. Examples include a
provider timeout or a declared transient transport failure within the
configured attempt limit.

Do not retry unchanged work for:

- schema, configuration, credential, or input validation failures;
- security or fatal failure codes;
- a substantive `VETO` decision;
- final quality below `quality_threshold`;
- deterministic replay mismatch;
- lifecycle or trace validation failure;
- maximum-iteration or convergence termination that the policy selected.

Built-in retry controls are bounded by `max_retries`, `retry_delay`, and
`stage_timeout`; provider runtimes may also apply exponential delay. Do not add
an unbounded outer retry loop around these controls. Record each outer attempt
as a distinct execution with a distinct output root.

## Partial and Inconsistent Artifacts

Use these states explicitly:

| Observed state | Interpretation | Action |
| --- | --- | --- |
| neither file exists | execution failed before artifact publication | diagnose logs and input; rerun only after classification |
| result exists, trace path is null | dry run or no primary successful input | inspect batch failures; do not claim provider execution |
| result exists, referenced trace is absent | interrupted or inconsistent publication | preserve result; rerun into a fresh root |
| trace exists, result is absent | trace write completed before result write | preserve trace; reconstruct for diagnosis, then rerun |
| both parse and agree | complete evidence pair | evaluate terminal status and policy |
| both parse but public fields differ | mixed, altered, or incompatible evidence | quarantine pair and investigate; do not edit either file |

For directory inputs, individual file failures do not necessarily make the CLI
exit nonzero. If at least one file succeeds, only the first success becomes the
primary artifact; if none succeeds, the CLI can write a veto-shaped fallback
without a trace. Automation must inspect the artifacts and logs instead of
using process status as the acceptance decision.

## Replay and Recovery

Replay validates the stored trace and reconstructs the terminal outcome. When
an adjacent final result exists, the CLI compares decision, confidence,
epistemic verdict, and stop reason. A printed `MATCH` covers those fields only;
it does not verify source bytes, termination reason, convergence fields, model
metadata, or the complete role output.

A replay mismatch does not currently produce a nonzero exit status. Treat it
as diagnostic evidence and investigate, in order:

1. trace schema and runtime compatibility;
2. pipeline definition and configuration hash;
3. model, prompt, temperature, and convergence identity;
4. the first differing terminal field;
5. whether result and trace came from the same output root and attempt.

Do not modify a stored trace to make replay pass. Preserve the original pair,
correct the producing boundary, and execute again.

## Acceptance After Recovery

A recovered execution is acceptable only when:

- the controller reaches a coherent terminal state through valid transitions;
- success, verdict, termination, stop reason, and convergence are interpreted
  as separate fields;
- the trace validates and the final result agrees with the trace-derived
  public fields;
- warnings, validation issues, failed shards, and action plans are resolved or
  explicitly accepted by policy;
- any replayability claim is consistent with model metadata and zero
  temperature;
- the new artifacts live in their own output root and the failed evidence
  remains available for comparison.

See [State and Persistence](../architecture/state-and-persistence.md) for write
guarantees, [Error Model](../architecture/error-model.md) for failure codes, and
[Observability and Diagnostics](observability-and-diagnostics.md) for the
artifact-led investigation order.
