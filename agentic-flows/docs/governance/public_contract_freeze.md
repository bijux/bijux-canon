# public-contract-freeze  

**Scope:** Public contract stability.  
**Audience:** Maintainers and integrators.  
**Guarantees:** V1 API and CLI semantics are frozen.  
**Non-Goals:** Feature roadmap or implementation detail.  
Why: This doc exists to record its single responsibility for review.  

## Decision  
The v1 public contract is frozen. This includes CLI commands, API schemas, and the semantics described in the docs.  

## Policy  
Any breaking change to v1 behavior requires a v2 release. No silent or implicit changes are allowed.  

## Enforcement  
Contract changes must be reviewed as governance decisions, not convenience patches.  
