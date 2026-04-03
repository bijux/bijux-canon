# Bijux Agent

Bijux Agent is a deterministic, auditable document-processing pipeline (CLI + optional HTTP API) designed to:

- process files or inline text,
- produce structured outputs,
- emit an audit trace suitable for replay validation and post-hoc inspection.

Published package name: `bijux-canon-agent`

## Quickstart (CLI)

```bash
make bootstrap
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export HUGGINGFACE_API_KEY=...
export DEEPSEEK_API_KEY=...

python -m bijux_canon_agent run path/to/file.txt --out artifacts/bijux-canon-agent/run1 --config examples/reference-config.yml
```

## Where to start

- **Using the tool**: `docs/user/usage.md`
- **Understanding the package layout**: `docs/project_overview.md`
- **Understanding the model**: `docs/overview/concepts.md`
- **Relying on guarantees**: `docs/spec/read_this_first.md`
- **Maintaining the repo**: `docs/maintainer/spec.md`

## Documentation Coverage

- docs/api/index.md
- docs/architecture/ARCHITECTURE.md
- docs/design/determinism.md
- docs/examples/document-review.md
- docs/examples/minimal-pipeline.md
- docs/index.md
- docs/legal/security.md
- docs/maintainer/CHANGELOG.md
- docs/maintainer/anti-features.md
- docs/maintainer/architecture_contract.md
- docs/maintainer/code-map.md
- docs/maintainer/contributing.md
- docs/maintainer/docs-parity.md
- docs/maintainer/docs_contract.md
- docs/maintainer/docs_voice.md
- docs/maintainer/docstring-policy.md
- docs/maintainer/documentation-invariant.md
- docs/maintainer/evaluation.md
- docs/maintainer/rejected-designs.md
- docs/maintainer/shared/glossary.md
- docs/maintainer/shared/structure.md
- docs/maintainer/shared/style.md
- docs/maintainer/spec.md
- docs/maintainer/system-boundaries.md
- docs/maintainer/testing.md
- docs/maintainer/tooling.md
- docs/maintainer/typing-status.md
- docs/maintainer/undefined-behavior.md
- docs/maintainer/vocabulary.md
- docs/overview/concepts.md
- docs/overview/readme.md
- docs/project_overview.md
- docs/spec/agents/agent-contract.md
- docs/spec/agents/agent-output.md
- docs/spec/architecture_diagram.md
- docs/spec/execution_artifacts.md
- docs/spec/execution_contracts.md
- docs/spec/execution_guarantees.md
- docs/spec/execution_intent_matrix.md
- docs/spec/execution_lifecycle.md
- docs/spec/failure_model.md
- docs/spec/failure_semantics.md
- docs/spec/identity.md
- docs/spec/invariants/architecture-invariants.md
- docs/spec/invariants/convergence-guarantees.md
- docs/spec/invariants/core-invariants.md
- docs/spec/invariants/determinism.md
- docs/spec/models/deepseek.md
- docs/spec/read_this_first.md
- docs/spec/refusals.md
- docs/spec/system_contract.md
- docs/spec/tracing-replay/why-trace-exists.md
- docs/spec/vocabulary.md
- docs/user/reading_paths.md
- docs/user/usage.md
