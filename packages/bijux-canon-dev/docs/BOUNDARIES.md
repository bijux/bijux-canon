# Boundaries

`bijux-canon-dev` is the maintenance boundary, not the product boundary.

## This package owns

- helpers that root `make` targets and CI depend on
- repository checks that apply across multiple packages
- package-specific maintenance support that is still driven from the repository root

## Product packages own

- runtime and domain behavior
- end-user CLI and API semantics
- package-local workflows that are meaningful even without the rest of the monorepo

## Boundary discipline

- do not park product logic here just because it is shared by tests
- do not duplicate repository logic across product packages
- do not let CI YAML become the only place where important policy lives
