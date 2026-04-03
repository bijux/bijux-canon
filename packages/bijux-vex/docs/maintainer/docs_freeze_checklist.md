# Documentation freeze checklist

Use this before tagging any v0.1.x release. Documentation is a release artifact.

- [ ] `mkdocs build --strict` passes with zero warnings.
- [ ] All Markdown files are reachable from navigation (see `tests/unit/test_docs_invariants.py`).
- [ ] README links and badges validated (docs, spec, API, examples, license, start_here).
- [ ] `docs/user/start_here.md` present and linked from README and docs home.
- [ ] API contract: `api/v1/schema.yaml` committed; `make api-freeze` produces no drift.
- [ ] Docs are self-contained (no cross-repo references).
- [ ] Experimental surfaces (ND/ANN) labeled consistently across README, spec, and API.
- [ ] Changelog reflects current release and states “first public release” history squash.
- [ ] Release checklist items that touch docs are complete (`docs/maintainer/release_checklist.md`).
- [ ] Documentation debt log (`docs/maintainer/debt_log.md`) reviewed and none of the items block freeze.
- [ ] Root docs (README, docs/index.md, start_here) are frozen; any change after freeze requires compatibility justification in `docs/maintainer/compatibility_breaks.md`.
