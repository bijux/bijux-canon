---
title: Decision Rules
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Decision Rules

The root should make ownership decisions faster, not more political.

Use these rules when a change proposal could plausibly land in more than one
surface and the repository needs one honest owner.

## Yes Or No Tests

Ask these questions in order:

1. Can one package handbook explain the behavior honestly on its own?
2. Does the rule protect more than one canonical package at once?
3. Is the question about shared documentation shape, schema storage, workflow
   coordination, or release framing rather than product behavior?
4. Is the issue really about repository-health tooling instead of a product
   contract?
5. Does the issue exist only because a legacy public name still needs support?

If the answer to the first question is yes, start in that package. If the first
answer is no and one of questions two through five is yes, keep the work at the
root, in maintenance, or in compatibility as appropriate.

## Borderline Example

A schema pin that protects ingest, index, and runtime together belongs at the
root. A change to ingest-local payload shaping does not, even if shared checks
also need updates.

## Escalate To Root When

- more than one canonical package contract needs the same shared rule
- a workflow or schema check is protecting repository-wide truth
- the docs structure itself is part of the problem being solved

## Send Work Back Down When

- a root page starts explaining package-local implementation detail
- maintainer automation begins to encode product behavior
- compatibility logic starts being treated as the preferred package surface

## Bottom Line

The root owns shared truth, not ambiguous overflow. If one package can defend
the behavior clearly, that package should stay the owner.
