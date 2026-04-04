# Effects

Effects are the whole point of this package, which means they need to be
described plainly.

## Main side effects

- reading package metadata, schemas, docs, and repository configuration
- spawning subprocesses such as `git`, `deptry`, `pip`, and related tooling
- writing generated artifacts like requirements exports or OpenAPI snapshots
- inspecting repository state and failing checks when policy is violated

## Guardrails

- subprocess usage should be explicit and reviewable
- generated files should be deliberate, stable, and easy to regenerate
- repository checks should explain failures in language maintainers can act on
