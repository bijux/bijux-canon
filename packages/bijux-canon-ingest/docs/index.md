# Ingest Package Guide

This documentation set explains `bijux-canon-ingest` as a package with a wide
source tree but a clear mission: deterministic document preparation and
ingest-local retrieval assembly.

## Start with these questions

- What the package is for: [project_overview.md](project_overview.md)
- How the tree should be read: [LAYOUT](LAYOUT.md)
- What belongs here: [SCOPE](SCOPE.md)
- How the package is structured: [ARCHITECTURE](ARCHITECTURE.md)
- Where ownership stops: [BOUNDARIES](BOUNDARIES.md)
- Which surfaces are stable: [CONTRACTS](CONTRACTS.md)
- Which effects need care: [EFFECTS](EFFECTS.md)
- What maintainers must defend: [INVARIANTS](INVARIANTS.md)
- What callers can rely on: [PUBLIC_API](PUBLIC_API.md)
- Which files are authoritative: [SSOT](SSOT.md)
- How behavior is protected: [TESTS](TESTS.md)

## Suggested reading order

1. Read [project_overview.md](project_overview.md).
2. Read [LAYOUT](LAYOUT.md) before moving modules.
3. Read [BOUNDARIES](BOUNDARIES.md) and [CONTRACTS](CONTRACTS.md) before changing public behavior.
