# Index Package Guide

This documentation set explains `bijux-canon-index` as an execution package
with provenance, replay, and backend capability concerns.

## Start with these questions

- What belongs in this package: [SCOPE](SCOPE.md)
- How the package is arranged: [ARCHITECTURE](ARCHITECTURE.md)
- Where ownership stops: [BOUNDARIES](BOUNDARIES.md)
- Which surfaces are stable: [CONTRACTS](CONTRACTS.md)
- Which effects need care: [EFFECTS](EFFECTS.md)
- What maintainers must defend: [INVARIANTS](INVARIANTS.md)
- What callers can rely on: [PUBLIC_API](PUBLIC_API.md)
- Which files are authoritative: [SSOT](SSOT.md)
- How behavior is protected: [TESTS](TESTS.md)

## Deep reference

- [Mental model](spec/mental_model.md)
- [Failure semantics](spec/failure_semantics.md)
- [Vector store profile](spec/vdb_profile.md)
- [Freeze criteria](spec/freeze_criteria.md)

## Suggested reading order

1. Read [spec/mental_model.md](spec/mental_model.md) first.
2. Read [ARCHITECTURE](ARCHITECTURE.md) and [BOUNDARIES](BOUNDARIES.md) before changing code placement.
3. Read [CONTRACTS](CONTRACTS.md) and [spec/failure_semantics.md](spec/failure_semantics.md) before changing package behavior.
