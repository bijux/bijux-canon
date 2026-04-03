# concepts  

**Scope:** Concept summaries.  
**Audience:** Readers learning the vocabulary.  
**Guarantees:** Short definitions and links.  
**Non-Goals:** Deep technical detail.  
Why: This doc exists to record its single responsibility for review.  

## Flow  
A flow is the ordered execution of steps under one determinism and policy contract. It is the unit of replay.  

## Step  
A step is a bounded unit of work in a flow. Steps emit events and produce artifacts.  

## Artifact  
An artifact is an immutable output produced by a step. Artifacts are hash-addressed and replayed.  

## Evidence  
Evidence is the traceable input that supports or contradicts reasoning. It is stored and replayed alongside artifacts.  

## Determinism  
Determinism is the guarantee that the same inputs yield the same outputs within declared bounds. It is enforced, not assumed.  

## Replay  
Replay re-executes a flow to confirm outputs and detect divergence. It is the audit path, not a debug convenience.  

## Pages  
- [Core Concepts](core_concepts.md)  
- [Determinism](determinism.md)  
- [Failures](failures.md)  
- [Failure Taxonomy](failure-taxonomy.md)  
