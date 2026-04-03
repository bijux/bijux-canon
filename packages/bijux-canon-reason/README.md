# bijux-canon-reason

`bijux-canon-reason` owns deterministic reasoning workflows and verification in `bijux-canon`.

It owns:
- reasoning plans and claims
- reasoning-step execution
- provenance and verification checks local to reasoning
- package-local CLI and API boundaries

It does not own runtime persistence, ingest/index engines, or repository tooling.

Start here:
- local package docs: [docs/index.md](docs/index.md)
- package-local architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- package-local contracts: [docs/CONTRACTS.md](docs/CONTRACTS.md)

Source layout:
- [src/bijux_canon_reason](src/bijux_canon_reason)
- [tests](tests)
- [tooling](tooling)
