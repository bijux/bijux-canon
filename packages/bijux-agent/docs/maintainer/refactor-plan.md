# Refactor plan (maintainer)

This is a living plan; it should stay short and honest.

## Near-term

- converge on a single LLM adapter interface
- ensure CLI and API produce equivalent *artifacts* for equivalent inputs/config

## Medium-term

- emit per-phase trace entries (not only finalize)
- strengthen trace upgrade tooling and validation UX

## Guardrails

- preserve `docs/spec/*` invariants unless you version a breaking change
- preserve failure taxonomy and trace schema discipline
