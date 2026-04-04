# Effects

## Main side effects

- reading reasoning requests, plans, and evaluation inputs
- dispatching step execution and tool calls
- writing reasoning outputs, traces, and API responses
- emitting verification outcomes and serialized artifacts

## Guardrails

- effectful behavior should stay explicit in execution and interface layers
- reasoning and verification models should remain easy to inspect without hidden I/O
- evidence use should be explainable after the fact
