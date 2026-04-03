# Extension acceptance policy

Welcome:

- New backends/adapters that honor contracts and invariants.
- New comparison policies or audit/reporting extensions.
- Additional examples, docs, or tooling that reinforce contracts.

Not welcome:

- Extensions that bypass contracts (silent fallback, hidden randomness).
- New public entrypoints that duplicate existing verbs (`execute`, `replay`, `compare`, `explain`).
- Mutations during replay or compare paths.

Rules:

- Public API modules are fixed; extend via documented seams (adapters, policies), not by adding new surfaces.
- Any extension must document its invariants and add tests that enforce them.
