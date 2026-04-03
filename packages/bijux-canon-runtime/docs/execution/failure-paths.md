# failure-paths  

**Scope:** Execution failure paths.  
**Audience:** Operators and reviewers.  
**Guarantees:** Clear triggers, detection, and outcomes.  
**Non-Goals:** Implementation detail.  
Why: This doc exists to record its single responsibility for review.  

## Dataset Mismatch  
- Trigger: The dataset fingerprint differs from the declared dataset.  
- Detection point: Replay validation before step execution.  
- Outcome: Run rejected; replay marked invalid.  

## Non-Determinism Violation  
- Trigger: An entropy source appears without authorization.  
- Detection point: Runtime entropy ledger on first use.  
- Outcome: Run aborted; trace marked non-replayable.  

## Verification Conflict  
- Trigger: Evidence contradicts reasoning claims.  
- Detection point: Verification gate after reasoning bundle.  
- Outcome: Run rejected; verification failure recorded.  

## Budget Exhaustion  
- Trigger: Entropy or rule cost exceeds declared budget.  
- Detection point: Budget accounting during execution.  
- Outcome: Run terminated; failure classified as budget exhaustion.  
