# bijux-canon-agent

`bijux-canon-agent` is the agent-pipeline package in `bijux-canon`.

It owns:
- agent role implementations
- deterministic pipeline orchestration
- trace-backed result artifacts
- package-local CLI and HTTP boundaries

It does not own runtime persistence, replay authority, or repository tooling.

Start here:
- local package docs: [docs/index.md](docs/index.md)
- package-local architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- package-local boundaries: [docs/BOUNDARIES.md](docs/BOUNDARIES.md)

Source layout:
- [src/bijux_canon_agent](src/bijux_canon_agent)
- [tests](tests)
- [examples](examples)

Primary entrypoint:
- console script: `bijux-canon-agent`
