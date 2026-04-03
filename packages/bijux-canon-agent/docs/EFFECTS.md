# EFFECTS

`bijux-canon-agent` performs these important effects:
- reads configuration, prompts, and input assets
- writes trace artifacts, result artifacts, and logs
- may call external model providers through `src/bijux_canon_agent/llm/`
- emits telemetry through `src/bijux_canon_agent/observability/`

Effectful code should stay at boundaries and adapters. Pure pipeline semantics should remain in reusable pipeline modules.
