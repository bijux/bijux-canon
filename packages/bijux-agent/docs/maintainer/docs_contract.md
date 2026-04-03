# Documentation contract (maintainer)

The documentation set must remain:

- **auditable**: changes are explicit and checksum-tracked
- **tiered**: user vs overview vs spec vs maintainer
- **accurate**: contract pages match runtime behavior

## Required properties

- Every markdown file under `docs/` is tracked by checksum.
- `docs/index.md` lists every tracked file.
- Spec pages use normative language and avoid implementation noise.

## What to avoid

- Duplicating the same concept across multiple pages without cross-links.
- Encoding unstable implementation details as guarantees.
- Mixing maintainer process notes into the spec.

Enforcement: `tests/invariants/test_documentation_invariant.py`.
