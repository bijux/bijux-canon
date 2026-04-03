# relationship-to-agentic-proteins  

**Scope:** Comparison to agentic-proteins.  
**Audience:** Readers familiar with both projects.  
**Guarantees:** Explicit similarities and differences.  
**Non-Goals:** Marketing claims.  
Why: This doc exists to record its single responsibility for review.  

## Shared Philosophy  
Both projects enforce determinism, provenance, and audit-ready outputs. Both treat invariants as non-negotiable contracts, not optional best practices.  

## Intentional Differences  
Agentic-proteins focuses on protein design workflows and domain-specific artifacts. Agentic-flows generalizes the same execution guarantees to broader agent workflows and replayable traces.  

## Comparison  
| Area | agentic-proteins | agentic-flows |
| --- | --- | --- |
| Scope | Protein design runtime | General execution and replay framework |
| Artifacts | Domain-specific design artifacts | Cross-domain execution artifacts |
| Primary users | Bio design teams | Research and platform teams |
| CLI focus | Design-centric commands | Flow, replay, and diff commands |
| Contracts | Protein-domain invariants | Execution invariants across agents |
