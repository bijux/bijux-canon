# architecture-note  

**Scope:** Determinism, replay, and contracts rationale.  
**Audience:** Senior engineers.  
**Guarantees:** Clear justification without marketing.  
**Non-Goals:** Implementation tutorial.  
Why: This doc exists to record its single responsibility for review.  

## Why Determinism  
Determinism is the only way to make results comparable over time. Without it, regressions hide inside noise, and every run becomes an anecdote. A deterministic system turns execution into evidence. It makes failures reproducible and makes success meaningful.  

Determinism here does not mean no entropy. It means entropy is explicit, bounded, and accounted for. When you declare the acceptable sources of nondeterminism, you make divergence a contract violation instead of a mystery.  

## Why Replay  
Replay is the audit path. A system that cannot replay cannot prove that a result was produced under the declared constraints. Replay provides the second execution that validates the first and exposes drift in data, environment, or behavior.  

Replay also forces you to define minimal inputs. If you cannot replay with recorded inputs, then your system depends on hidden state. Hidden state is the enemy of trust and the cause of hard-to-debug regressions.  

## Why Contracts Over Heuristics  
Heuristics tolerate ambiguity. Contracts reject it. A contract-first system specifies what must be true before and after each phase, so violations are caught immediately. This is more valuable than adding fallback behavior because it protects the integrity of the run.  

Contracts are also the only scalable governance mechanism. As the system grows, a contract is stable and testable. Heuristics drift, expand, and become folklore.  

## Summary  
Determinism makes outcomes comparable, replay makes outcomes verifiable, and contracts make outcomes enforceable. The combination turns agent execution into an auditable process rather than a best-effort workflow.  
