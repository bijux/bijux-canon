# Invariants

These are the maintenance rules this package exists to preserve.

- repository-wide maintenance logic should not drift back into duplicated scripts
- root automation should keep calling stable helpers instead of re-embedding logic inline
- tooling names should describe durable intent, not temporary cleanup work
- package-specific maintenance helpers should stay grouped under `packages/`

When the repository starts re-accumulating one-off scripts and hidden policy in
CI configuration, this package is losing its reason to exist.
