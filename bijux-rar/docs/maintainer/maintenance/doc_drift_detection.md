STATUS: AUTHORITATIVE

BREAKING_IF_CHANGED: true
## Doc Drift Detection

Rules:
- If code under a module listed in `docs/doc_to_code_map.md` changes, the corresponding doc must be reviewed/updated or explicitly waived in the PR.
- If a doc references a module/path, that module/path must exist.
- STATUS headers, BREAKING_IF_CHANGED markers, and invariant IDs must remain intact.

These rules are enforced via tests in `tests/unit/test_doc_drift.py`.***
