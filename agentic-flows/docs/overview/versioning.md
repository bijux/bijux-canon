# Versioning
> Rules for changes in the first public release.

This is the first public release and the rules start here.
v0.x carries no backward compatibility guarantees.
Version is a capability signal, not a stability promise.
Non-determinism semantics may evolve within v0.x.
The git tag (e.g., v0.1.0) is the source of truth for versioning.
Tagged builds must derive version exclusively from VCS metadata.
MAJOR: any change that can alter replay equivalence, persisted schema, or public contracts.
MINOR: additive, backward-compatible changes to public CLI, HTTP schema, or ontology values.
PATCH: documentation fixes, refactors, or internal changes with identical behavior.
Example PATCH: comment fixes or file moves with no API impact.
Example MINOR: adding an optional response field or a new CLI flag that preserves defaults.
Example MAJOR: changing determinism semantics, replay rules, or required fields.
