# determinism  

**Scope:** Determinism narrative.  
**Audience:** Readers evaluating replay guarantees.  
**Guarantees:** Explains why and how determinism is enforced.  
**Non-Goals:** Formal specifications or enums.  
Why: This doc exists to record its single responsibility for review.  

## Motivation  
Determinism makes results trustworthy. If two runs cannot be compared, you cannot prove progress, regression, or integrity.  

## Threats  
Hidden randomness, mutable datasets, and silent retries erase causality. They make a run look consistent while changing the meaning of its outputs.  

## Enforcement  
Agentic-flows requires explicit budgets, declared entropy sources, and immutable artifacts. The system records what happened and refuses to accept unverifiable output.  

## Failure Modes  
When determinism is violated, replay diverges and the run is rejected. The system treats divergence as a signal, not a nuisance.  
