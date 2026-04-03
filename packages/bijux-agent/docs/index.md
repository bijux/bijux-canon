# Bijux Agent

Bijux Agent is a deterministic, auditable document-processing pipeline (CLI + optional HTTP API) designed to:

- process files or inline text,
- produce structured outputs,
- emit an audit trace suitable for replay validation and post-hoc inspection.

## Quickstart (CLI)

```bash
make bootstrap
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export HUGGINGFACE_API_KEY=...
export DEEPSEEK_API_KEY=...

python -m bijux_agent.main run path/to/file.txt --out artifacts/run1 --config config/config.yml
```

## Where to start

- **Using the tool**: `docs/user/usage.md`
- **Understanding the model**: `docs/overview/concepts.md`
- **Relying on guarantees**: `docs/spec/read_this_first.md`
- **Maintaining the repo**: `docs/maintainer/spec.md`

## Documentation invariant (checksum-tracked)

Docs are treated as part of the runtime contract. Every markdown file under `docs/` is tracked by checksum and enforced by tests.

<details>
<summary>Tracked documentation files (checksum-enforced)</summary>

- docs/api/index.md — API (v1)  
- docs/architecture/ARCHITECTURE.md — Architecture  
- docs/design/determinism.md — Determinism (design notes)  
- docs/examples/document-review.md — Example: document review workflow  
- docs/examples/minimal-pipeline.md — Example: minimal CLI run  
- docs/index.md — Bijux Agent (this page)  
- docs/legal/security.md — Security  
- docs/maintainer/CHANGELOG.md — Maintainer changelog  
- docs/maintainer/anti-features.md — Anti-features (maintainer)
- docs/maintainer/breaking_refactor.md — Breaking refactor policy (maintainer)
- docs/maintainer/code-map.md — Code map
- docs/maintainer/docs-parity.md — Docs ↔ code parity
- docs/maintainer/docs_contract.md — Documentation contract (maintainer)
- docs/maintainer/docs_voice.md — Documentation voice (maintainer)
- docs/maintainer/docstring-policy.md — Docstring policy (maintainer)
- docs/maintainer/documentation-invariant.md — Documentation invariant (maintainer)
- docs/maintainer/evaluation.md — Evaluation (maintainer)
- docs/maintainer/first-refactor-plan.md — First refactor plan (maintainer)
- docs/maintainer/pipeline_refactor_rules.md — Pipeline refactor rules (maintainer)
- docs/maintainer/project_tree.md — Project tree
- docs/maintainer/refactor-invariants.md — Refactor invariants (maintainer)
- docs/maintainer/refactor-plan.md — Refactor plan (maintainer)
- docs/maintainer/refactor-priority.md — Refactor priority (maintainer)
- docs/maintainer/refactor_scope.md — Refactor scope (maintainer)
- docs/maintainer/rejected-designs.md — Rejected designs (maintainer)
- docs/maintainer/shared/glossary.md — Maintainer glossary
- docs/maintainer/shared/structure.md — Docs structure (maintainer)
- docs/maintainer/shared/style.md — Docs style (maintainer)
- docs/maintainer/spec.md — Maintainer index
- docs/maintainer/system-boundaries.md — System boundaries (maintainer)
- docs/maintainer/testing.md — Testing (maintainer)
- docs/maintainer/tooling.md — Tooling (maintainer)
- docs/maintainer/typing-status.md — Typing status (maintainer)
- docs/maintainer/undefined-behavior.md — Undefined behavior (maintainer)
- docs/maintainer/vocabulary.md — Maintainer vocabulary
- docs/overview/concepts.md — Concepts
- docs/overview/readme.md — Documentation orientation
- docs/spec/agents/agent-contract.md — Agent contract (spec)
- docs/spec/agents/agent-output.md — Agent output expectations (spec)
- docs/spec/architecture_diagram.md — Architecture diagram (spec)
- docs/spec/execution_artifacts.md — Execution artifacts (spec)
- docs/spec/execution_contracts.md — Execution contracts (spec)
- docs/spec/execution_guarantees.md — Execution guarantees (spec)
- docs/spec/execution_intent_matrix.md — Execution intent matrix (spec)
- docs/spec/execution_lifecycle.md — Execution lifecycle (spec)
- docs/spec/failure_model.md — Failure model (spec)
- docs/spec/failure_semantics.md — Failure semantics (spec)
- docs/spec/identity.md — Identity and versioning (spec)
- docs/spec/invariants/architecture-invariants.md — Architecture invariants (spec)
- docs/spec/invariants/convergence-guarantees.md — Convergence guarantees (spec)
- docs/spec/invariants/core-invariants.md — Core invariants (spec)
- docs/spec/invariants/determinism.md — Determinism invariants (spec)
- docs/spec/models/deepseek.md — DeepSeek backend notes
- docs/spec/read_this_first.md — Read this first (spec)
- docs/spec/refusals.md — Refusals and non-features (spec)
- docs/spec/system_contract.md — System contract (spec)
- docs/spec/tracing-replay/why-trace-exists.md — Why tracing exists
- docs/spec/vocabulary.md — Vocabulary (spec)
- docs/user/reading_paths.md — Reading paths
- docs/user/usage.md — Usage

</details>
