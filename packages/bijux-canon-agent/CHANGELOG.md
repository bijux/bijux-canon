Owner: Bijan Mousavi <bijan@bijux.io>
Status: stable
Scope: Changelog.

# Changelog

This file records user-visible package changes.

The changelog should stay focused on durable behavior:

- public CLI and API changes
- trace or artifact shape changes
- compatibility and replay-impacting changes
- operator-visible workflow changes

Implementation-only refactors belong in commit history unless they change the
package contract in a way that downstream users need to know about.

## v0.1.0 (first public release)

- First public, contract-complete release of Bijux Agent.
- Deterministic execution with replayable artifacts and provenance.
- Non-deterministic exploration via structured randomness reports and convergence audits.
- CLI and orchestration surfaces frozen; trace schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
- Agent execution kernel, lifecycle invariants, and passive-agent enforcement.
- Trace schema versioning, migration guards, and runtime compatibility checks.
- Convergence strategies and dry-run trace generator for deterministic tests.
- Example pipelines, public API boundary docs, and star-import invariants.
