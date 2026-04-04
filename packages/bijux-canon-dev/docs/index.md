# Dev Package Guide

This documentation set explains the package that keeps the repository itself
working. The goal is to help maintainers answer two recurring questions:

- does this helper belong in repository tooling or in a product package
- how can I change a root gate without creating a maintenance trap later

## Start with these questions

- What belongs here: [SCOPE](SCOPE.md)
- How the tooling package is organized: [ARCHITECTURE](ARCHITECTURE.md)
- Where the ownership edges are: [BOUNDARIES](BOUNDARIES.md)
- Which helpers are relied on by automation: [CONTRACTS](CONTRACTS.md)
- Which effects need special care: [EFFECTS](EFFECTS.md)
- What must stay true as tooling evolves: [INVARIANTS](INVARIANTS.md)
- Which modules are safe to treat as repository-facing API: [PUBLIC_API](PUBLIC_API.md)
- Which sources are authoritative: [SSOT](SSOT.md)
- How tooling behavior should be tested: [TESTS](TESTS.md)

## Suggested reading order

1. Read [SCOPE](SCOPE.md) before creating a new helper.
2. Read [BOUNDARIES](BOUNDARIES.md) if you are unsure whether the change belongs in a product package.
3. Read [CONTRACTS](CONTRACTS.md) and [TESTS](TESTS.md) before changing anything used by `make` or CI.
