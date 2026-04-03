# Project Contract

This page MUST define the runtime contract for bijux-agent. It MUST exist to bind Orchestrator, TraceRecorder, and FailureArtifact behavior. It MUST apply to all users and integrators.

## Contract Scope

- The contract MUST apply to runtime behavior only.
- The contract MUST cover Orchestrator, TraceRecorder, FailureArtifact, and AuditableDocPipeline.
- The contract MUST NOT cover performance, cost, model quality, or UX stability.

## Guarantees

- Orchestrator MUST record TraceEntry records via TraceRecorder.
- RunTrace MUST capture RunTraceHeader and ReplayMetadata fields.
- FailureArtifact MUST encode FailureClass and FailureCategory values.

## Refusals

- Agents MUST NOT orchestrate execution or manage lifecycle.
- Agents MUST NOT persist state across runs.
- Orchestrator MUST NOT apply silent retries without FailurePolicy.

## CLI Contract

- The CLI MUST invoke AuditableDocPipeline through `src/bijux_agent/main.py`.
- The CLI MUST NOT bypass FailurePolicy or TraceRecorder enforcement.
- The CLI and HTTP API MUST produce equivalent PipelineResult traces for identical inputs and config.

## Failure Semantics

- Invalid inputs MUST raise schema validation errors.
- Missing trace metadata MUST raise runtime errors in TraceRecorder.
