# failures  

**Scope:** Failure taxonomy explained.  
**Audience:** Operators and reviewers.  
**Guarantees:** Human-readable failure classification.  
**Non-Goals:** Stack traces or raw logs.  
Why: This doc exists to record its single responsibility for review.  

## Overview  
Failure classes exist to make blame clear and resolution consistent. Instead of debating symptoms, you classify what failed and follow the correct recovery path.  

## Examples  
A dataset mismatch means the run used different source data than expected, even if outputs look similar.  
A nondeterminism violation means the system observed unapproved entropy, so replay can no longer be trusted.  
A verification conflict means reasoning and evidence disagree, so the run is invalid even if execution completed.  
A budget exhaustion means the run exceeded declared limits and must be rejected.  

## Why It Matters  
Operators should be able to classify a failure without reading code. The class tells you whether to fix the data, the policy, or the execution path.  

## Related  
See [Failure Taxonomy](failure-taxonomy.md) for the class-to-action mapping.  
