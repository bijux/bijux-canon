# Pre‑Release Self‑Audit

Run these before tagging a release:

- `make lint quality security test docs api`
- `bijux vex doctor`
- `bijux vex bench --mode exact --store memory --repeats 1`
- Inspect one deterministic provenance artifact
- Inspect one ND provenance artifact
