# Governance

Repository-wide governance is owned at the root.

## Canonical Files

- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `LICENSE`
- `CHANGELOG.md`

Package roots no longer carry separate copies of those files.

## Why

The repository is one collaboration surface even though it publishes multiple
distributions. Shared contributor policy should therefore have one canonical
definition.

## Commit Style

Use Conventional Commits with durable scopes and descriptions.

Examples:

- `build(pytest): centralize package pytest configuration`
- `docs(governance): add repository-wide contributor contracts`
- `refactor(governance): remove duplicated package policies`
