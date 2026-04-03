# Pre‑Release Self‑Audit

Run these before tagging a release:

- `make lint quality security test docs api`
- `bijux doctor`
- `bijux bench --mode exact --store memory --repeats 1`
- Inspect one deterministic provenance artifact
- Inspect one ND provenance artifact
