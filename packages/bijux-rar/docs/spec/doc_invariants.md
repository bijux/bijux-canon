
## Documentation Invariants
STATUS: AUTHORITATIVE

- One concept per file; no duplicates.
- Each core doc states scope, non-goals, and non-negotiable invariants.
- Every contract names how it can be violated.
- Examples must reference concrete artifacts (paths, fingerprints, outputs).
- Forward links only; no backward references that create circular reading.
- Any new invariant must name its failure mode.
- Docs are invalid if they drift from code constants or schemas.***
- Soft language is banned from core docs and is grounds for rejection.
- Any Markdown file with three or more top-level sections must include a `<a id="top"></a>` anchor near the top and a `[Back to top](#top)` link at the end.
- Docs directory layout (user/, spec/, maintainer/) is frozen for v0.1.x; adding new top-level categories requires a version bump and migration note.
