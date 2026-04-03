# If I disappear

- Releases: run `make lint quality security test docs api` then `make release`; tags drive versions (hatch-vcs).
- Must never change: deterministic execution semantics/ABI, public API modules, error taxonomy for deterministic paths.
- Say “no” to PRs that: bypass contracts, add DB-like semantics, or weaken invariants.
- Docs/tests are gates: mkdocs strict, api-freeze, conformance suites must stay green.
- Contact/review: treat ND/ANN changes as experimental; require contract/test updates.
