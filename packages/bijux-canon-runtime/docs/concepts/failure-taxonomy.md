# failure-taxonomy  

**Scope:** Failure class meaning and action.  
**Audience:** Operators and reviewers.  
**Guarantees:** Each class maps to a clear response.  
**Non-Goals:** Implementation detail.  
Why: This doc exists to record its single responsibility for review.  

## Taxonomy  
| FailureClass | Meaning | User action |
| --- | --- | --- |
| structural | The run violated declared structure or ordering. | Fix the flow manifest, dataset descriptor, or execution ordering. |
| semantic | Reasoning or evidence failed verification. | Correct claims, evidence, or policy expectations. |
| environmental | The execution environment drifted from the declared fingerprint. | Rebuild environment to match the plan. |
| authority | An unauthorized action or entropy source was used. | Remove or explicitly authorize the source. |
