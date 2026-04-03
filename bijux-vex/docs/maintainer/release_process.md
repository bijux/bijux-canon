# Release process (bijux-vex v0.1.x)

## Preconditions
- Working tree clean; `git status` empty.
- All gates green: `make lint quality security test`.
- Public API surface and OpenAPI freeze tests passing.
- Execution ABI fingerprint unchanged or intentionally bumped with doc updates.

## Versioning and tagging
- Version derives from git tags via `hatch-vcs`; do **not** edit `pyproject.toml` for version bumps.
- Tag format: `v0.1.0`, `v0.1.0-rc1`, etc.
- Dirty worktree produces a `.dirty` local version; do not publish in that state.

## Release steps
1) `make lint quality security test`
2) `make docs` (mkdocs build --strict)
3) `make api-freeze` (ensures schema.yaml → openapi.v1.json drift-free)
4) `make release` (builds wheel+sdist, SBOM, refreshes OpenAPI)
5) Update CHANGELOG via towncrier if needed.
6) Confirm `docs/maintainer/release_checklist.md` is complete.
7) Create signed tag `git tag -s v0.1.0 -m "v0.1.0"`
8) Push tag: `git push origin v0.1.0`

## GitHub automation expectations
- CI workflow must run tests, lint, quality, security on PRs and tags.
- Release workflow should build wheel/sdist, attach SBOM, and upload artifacts to the GitHub release page.
- Tag protection: only signed, CI-green tags are published.

## Post-release
- Update docs/README if behavior changed.
- If ABI or public surface shifts, bump PUBLIC API or ABI versions and document rationale.
