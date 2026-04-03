# bijux-canon-runtime

`bijux-canon-runtime` owns governed execution and replay in `bijux-canon`.

It owns:
- flow execution authority
- replay and acceptance semantics
- trace capture and runtime persistence
- package-local CLI and API boundaries

It does not own agent composition policy, ingest/index ownership, or repository tooling.

Start here:
- local package docs: [docs/index.md](docs/index.md)
- package-local architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- package-local boundaries: [docs/BOUNDARIES.md](docs/BOUNDARIES.md)

Source layout:
- [src/bijux_canon_runtime](src/bijux_canon_runtime)
- [tests](tests)
- [examples](examples)

Primary entrypoint:
- console script: `bijux-canon-runtime`
