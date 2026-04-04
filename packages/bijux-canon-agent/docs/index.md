# Agent Package Guide

This documentation set explains how `bijux-canon-agent` is meant to be read,
changed, and defended over time.

## Start with these questions

- What belongs in this package: [SCOPE](SCOPE.md)
- How the package is shaped: [ARCHITECTURE](ARCHITECTURE.md)
- Where the ownership edges are: [BOUNDARIES](BOUNDARIES.md)
- Which surfaces are stable: [CONTRACTS](CONTRACTS.md)
- Which side effects need care: [EFFECTS](EFFECTS.md)
- What must always remain true: [INVARIANTS](INVARIANTS.md)
- What downstream users can rely on: [PUBLIC_API](PUBLIC_API.md)
- Which files are authoritative for which concern: [SSOT](SSOT.md)
- How behavior is protected in tests: [TESTS](TESTS.md)

## Suggested reading order

1. Read [SCOPE](SCOPE.md) if you are deciding whether code belongs here.
2. Read [ARCHITECTURE](ARCHITECTURE.md) before moving modules or creating new ones.
3. Read [BOUNDARIES](BOUNDARIES.md) and [CONTRACTS](CONTRACTS.md) before changing any public behavior.
4. Read [TESTS](TESTS.md) before adding or reshaping behavior.

Root documentation can summarize this package, but package-local intent lives
here because this is where maintainers decide what the agent package is for.
