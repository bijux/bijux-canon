# Scope

`bijux-canon-dev` exists to keep the repository operable, consistent, and
auditable. It is the home for shared maintenance logic that would otherwise be
copied into shell scripts, CI YAML, or package-local utility clutter.

## In scope

- helpers behind root quality, lint, test, and security gates
- release, version, and SBOM support
- shared schema and OpenAPI maintenance logic
- package-specific maintenance adapters that are still repository concerns

## Out of scope

- product runtime behavior
- domain logic that belongs to a canonical package
- legacy compatibility surfaces meant for end users or downstream installations

## Rule of thumb

If the behavior exists to keep the repository healthy, reproducible, or
releasable, it belongs here. If it exists to make the product work for end
users, it belongs somewhere else.
