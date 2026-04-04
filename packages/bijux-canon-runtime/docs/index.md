# Runtime Package Guide

This documentation set explains the package that owns execution authority in
`bijux-canon`.

## Start with these questions

- What belongs here: [SCOPE](SCOPE.md)
- How the runtime is organized: [ARCHITECTURE](ARCHITECTURE.md)
- Where its ownership stops: [BOUNDARIES](BOUNDARIES.md)
- Which surfaces are stable: [CONTRACTS](CONTRACTS.md)
- Which effects require special care: [EFFECTS](EFFECTS.md)
- What maintainers must defend: [INVARIANTS](INVARIANTS.md)
- What callers can rely on: [PUBLIC_API](PUBLIC_API.md)
- Which files are authoritative: [SSOT](SSOT.md)
- How runtime behavior is protected: [TESTS](TESTS.md)

## Suggested reading order

1. Read [SCOPE](SCOPE.md) and [BOUNDARIES](BOUNDARIES.md) first.
2. Read [ARCHITECTURE](ARCHITECTURE.md) before moving code across layers.
3. Read [CONTRACTS](CONTRACTS.md) and [TESTS](TESTS.md) before changing replay or persistence behavior.
