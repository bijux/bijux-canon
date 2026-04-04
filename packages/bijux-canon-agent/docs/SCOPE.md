# Scope

`bijux-canon-agent` exists to run agent workflows in a way that is predictable,
inspectable, and easy to hand off to the runtime package for broader governance.

## In scope

- role implementations and the local rules that make those roles work
- orchestration of the package-local agent pipeline
- trace and result artifacts that explain an execution after the fact
- operator-facing CLI and HTTP entrypoints that belong specifically to the agent package

## Out of scope

- replay governance, persistence authority, and runtime-wide policy decisions
- ingest, vector, and reasoning engines that belong to other canonical packages
- repository tooling, release helpers, or generic shared infrastructure

## Rule of thumb

If the question is "how should this agent workflow run and explain itself,"
the change probably belongs here. If the question is "who stores, approves,
replays, or governs the run across the wider system," it probably belongs in
`bijux-canon-runtime`.
