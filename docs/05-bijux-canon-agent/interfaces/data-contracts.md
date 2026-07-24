---
title: Data Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Data Contracts

Agent boundaries distinguish a role invocation, a complete pipeline execution,
and a persisted trace. Each shape answers a different question and has separate
compatibility requirements.

## Agent Invocation

`AgentInput` is immutable and rejects unknown fields. It contains:

- a non-empty `task_goal`;
- caller payload and metadata mappings;
- a non-empty `context_id`;
- the requested agent type; and
- synchronous or asynchronous execution mode.

`AgentOutput` contains non-empty text, artifact references, normalized scores,
confidence in `[0, 1]`, a pass/veto decision, and metadata. Every score must be
in `[0, 1]`, and metadata must carry the current contract version. This prevents
an output from looking valid while omitting the schema identity needed by its
consumer.

Expected role failures use `AgentError`: a typed failure code, message, optional
details, and a `transient` flag. That flag is evidence for retry policy, not an
instruction to retry without a bound.

## Pipeline Execution Result

`PipelineExecutionResult` is the orchestration response:

| Field | Meaning |
| --- | --- |
| `result` | final merged output, or `null` on failure |
| `stages` | named outputs retained from executed stages |
| `audit_trail` | ordered operational events |
| `revision_history` | feedback-driven revisions |
| `execution_path` | ordered stage and shard path |
| `final_status` | success, processed stages, iteration and stop details |
| `telemetry` | iteration, stage, shard, and duration measurements |
| `cache_hit` | whether orchestration returned retained work |
| `warnings` | non-fatal diagnostic messages |
| `error`, `action_plan` | structured recovery detail when execution fails |

`final_status.termination_reason` explains why execution ended. Convergence is
reported independently through its Boolean, reason, and iteration count.

## Final Result Artifact

The CLI writes `result/final_result.json`. For a traced execution it contains
the decision, confidence, epistemic status, stop reason, relative trace path,
runtime version, termination reason, and convergence details. Model metadata is
included when a trace exists.

Dry runs and runs without a successful entry produce an explicit veto artifact
with zero confidence and no trace path. Consumers must check the verdict and
trace path rather than treating file existence as success.

## Run Trace

The current trace schema version is `2`. A trace has a header and ordered
entries. The header identifies:

- configuration and pipeline-definition hashes;
- role and runtime versions;
- replayability status;
- convergence hash and reason;
- termination reason; and
- provider, model, temperature, and token-limit metadata.

Each entry records role and lifecycle node, status, timing, input, output or
error, scores, prompt and model hashes, run identity, stop and termination
reasons, replay metadata, epistemic status, decision/failure artifacts, and the
run fingerprint.

Timestamps are observational fields. Pipeline inputs, outputs, hashes,
decisions, lifecycle identity, and convergence metadata are deterministic
fields. Comparators must not let an expected clock difference hide a changed
prompt, model, configuration, or decision.

## Trace Validity

A canonical lifecycle trace must respect allowed transition order, contain
required lifecycle coverage or declared skip reasons, and end consistently
with its stop and epistemic state. Replay-critical entries require prompt hash,
model hash, run fingerprint, and convergence hash. The header requires runtime
version, convergence hash, and model metadata.

A trace marked replayable cannot declare non-zero model temperature. If the
execution cannot satisfy that constraint, mark it non-replayable rather than
publishing a misleading replay promise.

## Validation Surfaces

Two validators answer different questions:

| Validator | Establishes | Does not establish |
| --- | --- | --- |
| trace payload validation | supported schema version, run ID presence, non-empty entry list, runtime compatibility | lifecycle order, entry completeness, or replay parity |
| canonical `TraceValidator` | phase order, allowed transitions and agents, phase semantics, lifecycle completeness, epistemic consistency, replay-critical fields | byte integrity or equivalence to `final_result.json` |

Loading a trace for replay performs schema upgrade and payload validation. It
does not invoke the canonical lifecycle validator. A consumer accepting traces
from outside the producing workflow should run both validations before deriving
a decision.

`PipelineResult.from_trace()` is a projection from the final entry. It derives
status, decision, epistemic verdict, confidence, and stop reason and requires
header model metadata. It is not a re-execution of the agents and does not
recompute prompts, scores, convergence, or model output.

See [Execution Model](../architecture/execution-model.md) for how these values
are produced.
