# Offline urban-heat generalization workflow

This independent challenge checks that the installed product generalizes beyond
the ancient-DNA corpus. It uses a small synthetic municipal heat-response
portfolio with Markdown, HTML, plain-text, and JATS XML sources; different
terminology; an explicit suitability conflict; operational limitations; and an
unsupported question that must produce abstention.

The repository authors created every source specifically as a deterministic
software acceptance fixture. The files are licensed under Apache-2.0 with the
repository, contain no third-party material, and make no claim to be real public
health guidance. [`corpus-manifest.json`](corpus-manifest.json) records exact
byte hashes, media types, authorship, provenance, and license scope.

[`acceptance.json`](acceptance.json) declares the evaluation cases and thresholds
before execution. The workflow evaluates only system-produced artifacts: every
admitted material claim must have direct verified support, every citation must
resolve to the exact source hash, and the unsupported case must expose no claims
or citations. It also requires bounded research to pursue distinct evidence
needs, classify candidates, retain citations, and stop within its declared
budget. No urban-heat-specific rule exists in product code or the runner.

Run it with a fresh installed base environment and new output directories:

```bash
python -m venv artifacts/urban-heat-generalization/venv
artifacts/urban-heat-generalization/venv/bin/python -m pip install bijux-canon-runtime

python examples/urban-heat-research/offline_generalization_workflow.py \
  --runtime-command artifacts/urban-heat-generalization/venv/bin/bijux-canon-runtime \
  --workspace artifacts/urban-heat-generalization/runtime-workspace \
  --evidence-directory artifacts/urban-heat-generalization/evidence
```

The command uses installed Runtime v2 `discover`, `ingest`, `index`, `ask`,
`research`, `result`, `inspect`, and paged artifact access. It removes source
checkout paths from subprocess configuration and points proxy variables at a
closed loopback port. On macOS, the installed acceptance test additionally
wraps the process in an operating-system network-denial sandbox.
