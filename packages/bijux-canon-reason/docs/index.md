# Reason Package Guide

This documentation set explains `bijux-canon-reason` as the package that owns
reasoning behavior, not just one more API surface.

## Start with these questions

- What belongs here: [SCOPE](SCOPE.md)
- How the package is arranged: [ARCHITECTURE](ARCHITECTURE.md)
- Where ownership stops: [BOUNDARIES](BOUNDARIES.md)
- Which surfaces are stable: [CONTRACTS](CONTRACTS.md)
- Which effects need care: [EFFECTS](EFFECTS.md)
- What maintainers must defend: [INVARIANTS](INVARIANTS.md)
- What callers can rely on: [PUBLIC_API](PUBLIC_API.md)
- Which files are authoritative: [SSOT](SSOT.md)
- How behavior is protected: [TESTS](TESTS.md)

## Suggested reading order

1. Read [SCOPE](SCOPE.md) and [BOUNDARIES](BOUNDARIES.md) before deciding where new logic belongs.
2. Read [ARCHITECTURE](ARCHITECTURE.md) before moving planning, execution, or verification code.
3. Read [CONTRACTS](CONTRACTS.md) and [TESTS](TESTS.md) before changing package-facing behavior.
