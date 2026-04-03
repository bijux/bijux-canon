# Failure taxonomy
> Reference mapping for failure envelopes returned by the API.

| FailureClass | ReasonCode | Meaning (1 sentence) | Expected user action |
| --- | --- | --- | --- |
| ResolutionFailure | INVALID_MANIFEST | The flow manifest violates the schema or required invariants. | Fix the manifest and re-run. |
| ResolutionFailure | PLAN_MISMATCH | The resolved plan hash does not match the expected value. | Regenerate the plan from the declared manifest. |
| ExecutionFailure | EXECUTION_ABORTED | The run was cancelled or halted before completion. | Inspect cancellation cause and retry if appropriate. |
| ExecutionFailure | DATASET_MISMATCH | The dataset identity or fingerprint does not match the run contract. | Reconcile dataset versioning and retry with the correct dataset. |
| RetrievalFailure | EVIDENCE_MISSING | Required evidence could not be retrieved deterministically. | Restore evidence sources or adjust retrieval contracts. |
| ReasoningFailure | CLAIM_CONFLICT | Reasoning claims contradict required evidence constraints. | Revise the reasoning policy or inputs. |
| ReplayUnacceptable | explicit | Replay exceeded the declared acceptability threshold. | Re-run with a compatible dataset/policy or lower the acceptability threshold. |
| VerificationFailure | VERIFICATION_CONFLICT | Verification engines disagree beyond the allowed threshold. | Review arbitration policy and tighten evidence requirements. |
| SemanticViolationError | UNAUTHORIZED_ENTROPY | An entropy source was used without explicit authorization. | Update the policy to authorize the source or remove it. |
| VerificationFailure | CONTRACT_VIOLATION | The run violates a declared contract or invariant. | Fix the contract breach and re-run. |

## Failure severity legend
> Severity guidance by failure class.

FailureClass → severity
ResolutionFailure → ERROR
ExecutionFailure → FATAL
RetrievalFailure → WARN
ReasoningFailure → ERROR
ReplayUnacceptable → ERROR
VerificationFailure → ERROR
SemanticViolationError → FATAL
