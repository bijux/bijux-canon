# why-agentic-flows  

**Scope:** Motivation for agentic-flows.  
**Audience:** Readers evaluating fit.  
**Guarantees:** States what agentic-flows enforces.  
**Non-Goals:** Marketing or competitive positioning.  
Why: This doc exists to record its single responsibility for review.  

## Overview  
Most agent frameworks optimize for speed and flexibility, then retroactively ask users to trust the results. The result is opaque runs, unverifiable outcomes, and systems that drift as soon as scale or team size increases.  

Agentic-flows enforces determinism, provenance, and replayability as first-class guarantees. It treats execution as a contract, not a best-effort convenience, and makes divergence visible instead of silently accepted.  

## Non-Goals  
- An agent runtime that prioritizes autonomous behavior over auditability.  
- A general-purpose chat or planning framework.  
- A best-effort system that accepts unverifiable outputs.  
