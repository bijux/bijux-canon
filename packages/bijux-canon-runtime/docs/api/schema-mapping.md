# schema-mapping  

**Scope:** API schema to runtime mapping.  
**Audience:** API and runtime maintainers.  
**Guarantees:** One mapping per API field.  
**Non-Goals:** Behavioral semantics beyond invariants.  
Why: This doc exists to record its single responsibility for review.  

## Mapping  

| API field | Internal class | Field | Invariant |
| --- | --- | --- | --- |
| `FlowRunRequest.flow_manifest` | `FlowManifest` | manifest source | Must resolve to a single manifest. |
| `FlowRunRequest.inputs_fingerprint` | `ResolvedStep` | `inputs_fingerprint` | First step fingerprint anchors deterministic seed. |
| `FlowRunRequest.run_mode` | `ExecutionConfig` | `mode` | Must map to `RunMode` live/dry/observe. |
| `FlowRunRequest.dataset_id` | `DatasetDescriptor` | `dataset_id` | Dataset identity must be immutable. |
| `FlowRunRequest.policy_fingerprint` | `VerificationPolicy` | fingerprint | Policy fingerprint must match execution policy. |
| `FlowRunResponse.run_id` | `FlowRunResult` | `run_id` | Run ID exists for persisted executions. |
| `FlowRunResponse.flow_id` | `ExecutionPlan` | `manifest.flow_id` | Flow identity is stable across replay. |
| `FlowRunResponse.status` | `ExecutionTrace` | execution status | Status reflects terminal run outcome. |
| `FlowRunResponse.determinism_class` | `DeterminismClass` | class | Determinism class must be declared, not inferred. |
| `FlowRunResponse.replay_acceptability` | `ReplayAcceptability` | acceptability | Replay acceptability matches manifest. |
| `FlowRunResponse.artifact_count` | `ExecutionTrace` | artifact count | Count reflects persisted artifacts. |
| `ReplayRequest.run_id` | `ExecutionTrace` | `run_id` | Replay references a stored run. |
| `ReplayRequest.expected_plan_hash` | `ExecutionSteps` | `plan_hash` | Plan hash must match stored plan. |
| `ReplayRequest.acceptability_threshold` | `ReplayAcceptability` | threshold | Replay must meet or exceed threshold. |
| `ReplayRequest.observer_mode` | `ExecutionConfig` | `mode` | Observer mode cannot mutate state. |
| `FailureEnvelope.failure_class` | `FailureClass` | class | Failure class is structural or semantic. |
| `FailureEnvelope.reason_code` | `ReasonCode` | code | Reason codes are enumerated. |
| `FailureEnvelope.violated_contract` | `ContractID` | contract | Violated contract must be explicit. |
| `FailureEnvelope.evidence_ids` | `EvidenceID` | evidence IDs | Evidence identifiers must be stable. |
| `FailureEnvelope.determinism_impact` | `DeterminismClass` | impact | Impact reflects declared determinism class. |
| `X-Agentic-Gate` | `GateID` | gate | Gate identifier must be declared. |
| `X-Determinism-Level` | `DeterminismLevel` | level | Determinism level controls enforcement. |
| `X-Policy-Fingerprint` | `VerificationPolicy` | fingerprint | Fingerprint must match policy hash. |
