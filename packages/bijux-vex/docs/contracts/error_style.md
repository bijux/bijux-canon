# Error Message Style Guide

Bijux-Vex error messages must be human-first and actionable. Every message should answer four questions:

1. What happened  
State the failure in plain language. No internal jargon unless necessary.

2. Why it happened  
Explain the immediate cause (missing dependency, mismatch, unavailable backend).

3. How to fix  
Give a concrete next step a user can take.

4. Where to learn more  
Point to a doc path in this repository (no external links required).

Keep it short. If a sentence does not help a user act, remove it.

**Template**

```
What happened: <short description>
Why: <root cause>
How to fix: <specific action>
Where to learn more: <doc path>
```

**Examples**

```
What happened: vector store backend unavailable.
Why: 'faiss' is not installed.
How to fix: pip install "bijux-vex[vdb]".
Where to learn more: docs/spec/vectorstore_adapter.md
```

```
What happened: deterministic execution refused.
Why: ANN mode is non-deterministic.
How to fix: choose exact mode or switch to ND explicitly.
Where to learn more: docs/spec/determinism_matrix.md
```
