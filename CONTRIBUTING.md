# Contributing

This repository is a monorepo for independently publishable Python packages.

## Repository Model

- publishable distributions live in `packages/`
- repo-owned tooling lives in `configs/` and `makes/`
- repository-wide governance lives at the root

When a concern is shared across packages, prefer fixing it once at the
repository level instead of duplicating the same policy in multiple package
roots.

## Working Style

- keep package runtime code inside the owning package
- move shared tooling concerns to `configs/` or `makes/`
- keep generated files and caches under `artifacts/`
- avoid names that depend on temporary planning language

## Commits

Use Conventional Commits with clear, durable intent, for example:

- `build(repo): centralize pytest configuration`
- `docs(governance): add repository security policy`
- `refactor(tooling): remove duplicated package licenses`

Prefer small, logical commits that each leave the repository in a coherent
state.

## Before Opening Changes

- run the relevant package checks for the area you touched
- update shared docs when repository contracts change
- update package metadata and links when root-owned files move

## Getting Help

Open an issue for repository questions or package-specific problems that are
not security-sensitive.
