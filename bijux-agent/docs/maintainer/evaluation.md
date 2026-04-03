# Evaluation (maintainer)

You cannot evaluate an LLM system purely by “does it look good”. You need a regression story.

## What to evaluate

- **Artifact integrity**: does the run produce valid `final_result.json` and `run_trace.json`?
- **Contract compliance**: are required fields present and correctly classified?
- **Failure taxonomy**: do failures map cleanly into `FailureArtifact` profiles?
- **Replay validation**: can traces be validated/upgraded under the current schema?

## What not to evaluate here

- model quality claims (domain-dependent)
- benchmark scores without trace-backed provenance

## Practical regression loop

- Create small deterministic fixtures (text files).
- Run the CLI and compare:
  - run fingerprints,
  - replayability classification,
  - presence/shape of key fields.
