# Docs Ownership

`bijux-canon` keeps one reader-facing documentation home under `root/docs`.

## Rules

- `docs/` is the published and navigable documentation spine for the monorepo.
- `docs/packages/<package>/` holds the primary narrative, tutorial, example, and maintainer docs for each package.
- `packages/<package>/docs/` stays intentionally small and code-adjacent.
- package-local docs exist for package readme content, package boundaries, and the small set of contract pages that are easiest to review next to code.
- cross-package guidance belongs at the repository root, not inside any one package.

## Package-local docs ceiling

Each package should keep fewer than ten long-lived docs in `packages/<package>/docs/`.

These files are reserved for:

- package landing/readme content
- project boundary overview
- public contract anchors that are reviewed with code changes
- checksum or freeze files that package tests depend on

Everything else should live under `docs/packages/<package>/`.

## Why

- docs stay discoverable in one place for readers
- package-local docs stay small enough to review with code
- package boundaries remain explicit instead of being buried in one giant root tree
- package sites can still publish from `root/docs/packages/<package>/`

## Migration rule

When moving a package doc from `packages/<package>/docs/` to `docs/packages/<package>/`:

- preserve stable names
- preserve relative structure when practical
- update links, mkdocs config, and docs tests in the same commit
- leave behind only the minimal package-local contract surface
