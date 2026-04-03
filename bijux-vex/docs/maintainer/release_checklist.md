# Release checklist (v0.1.x)

- [ ] Working tree clean; no untracked artifacts.
- [ ] `make lint quality security test` passes with zero warnings.
- [ ] `make docs` (mkdocs build --strict) passes; no navigation warnings.
- [ ] `docs/maintainer/docs_freeze_checklist.md` reviewed and satisfied.
- [ ] `api/v1/schema.yaml` committed; `make api-freeze` passes (no drift).
- [ ] OpenAPI validation tests green; schema reachable in docs.
- [ ] README badges and docs links verified.
- [ ] CHANGELOG updated via towncrier; v0.1.0 section accurate.
- [ ] Release artifacts built (`make release`): wheel/sdist, SBOM, refreshed OpenAPI.
- [ ] Tags signed: `git tag -s v0.1.x`.
- [ ] CI workflows (ci.yml, release.yml) green on tag.
