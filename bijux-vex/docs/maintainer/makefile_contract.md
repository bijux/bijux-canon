# Makefile contract

The Makefile targets are part of the public tooling surface. Changes require justification in `docs/maintainer/compatibility_breaks.md`.

Stable targets (treated as contracts):

- `install`, `bootstrap`
- `fmt`, `lint`, `test`, `quality`, `security`, `docs`, `api`, `hygiene`, `sbom`
- `all`, `clean`, `clean-soft`
- `release`

Reserved/UX-parity targets:

- `build`: intentionally fails with guidance to use `make release`.
- `citation`: intentionally fails until citation metadata is published.

Any new target added for CI or user workflows must be documented here before release.
