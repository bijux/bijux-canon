---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Architecture

Use this section when the question is structural: which modules own role-local
agents, pipeline control, workflow policy, interfaces, traces, and
observability, and how those parts cooperate without collapsing into one
omnipotent orchestration layer.

`bijux-canon-agent` is easiest to read as a control system. Interfaces bring
work in, pipeline modules coordinate execution, agent modules do role-local
work, application policy and workflow graphs constrain behavior, and traces
plus observability make the result inspectable.

## Start Here

- open [Module Map](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/module-map/) for the shortest route from directory names
  to owned behavior
- open [Execution Model](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/execution-model/) when you need the lifecycle of an
  orchestrated run
- open [State and Persistence](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/state-and-persistence/) when the question is
  which results, traces, or replay data become durable

## Pages In This Section

- [Module Map](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/architecture-risks/)

## Open Architecture When

- you need to know which structural slice owns a behavior before editing it
- a review is about layering, orchestration flow, or module drift
- you need to explain how interfaces, pipeline control, role agents, and traces
  fit together

## Open Another Section When

- the main question is why the behavior belongs in agent orchestration at all
- you are deciding whether a command, schema, or artifact is a public contract
- the issue is mainly procedural or evidentiary rather than structural

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) for package purpose and ownership
- open [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) for CLI, API, artifact, and import
  contracts
- open [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) for setup, diagnostics, and release
  procedures
- open [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/) for invariants, tests, and architecture
  risk pressure

## Concrete Anchors

- `src/bijux_canon_agent/agents` for role-local behavior
- `src/bijux_canon_agent/pipeline` for execution flow orchestration
- `src/bijux_canon_agent/application` for workflow graph policy and orchestrator
  logic
- `src/bijux_canon_agent/traces` and `observability` for replay and inspection
  seams

## Bottom Line

`Architecture` makes the agent package readable as a control flow with
named responsibilities. If interfaces, pipeline logic, role agents, and trace
handling start blending together, the orchestration story gets harder to trust
even before tests fail.

