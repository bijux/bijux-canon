---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Dependencies and Adjacencies

Dependency and adjacency pressure in `bijux-canon-runtime` matters because seeing the last step in a flow makes it tempting to absorb every late-stage concern. Reviewers need final authority named explicitly so it stays narrower than late execution.

## Library Pressure

- persistence, observability, and runtime helpers support authority but do not replace the need for explicit acceptance policy
- interface and artifact helpers matter because runtime outputs become durable system records
- library choice is not a reason to drag lower-package semantics into runtime

## Neighbor Pressure

- ingest, index, reason, and agent produce behavior that runtime governs but does not redefine
- maintenance surfaces automate repository workflows without becoming runtime semantics
- adjacent packages stay narrower when runtime limits itself to authority and durability

## Bottom Line

Dependencies matter, but they should never be allowed to silently redefine package ownership.
