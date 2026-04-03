# Deletion policy

- Prefer deletion over abstraction when:
  - invariants can be enforced without an extra layer
  - an extension seam is unused across releases
  - a feature is undocumented or not backed by specs/tests
- Any new abstraction must list the invariant it enforces; otherwise delete or inline.
- Deprecations: mark in docs/spec/identity.md and remove in next minor unless ecosystem-bound.
- Freeze rule: dead code or unused flags are removed before tagging; no “maybe later” retention.
