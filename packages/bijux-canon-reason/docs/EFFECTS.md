# EFFECTS

`bijux-canon-reason` performs these important effects:
- reads reasoning requests, plans, and evaluation inputs
- writes reasoning outputs, traces, and API responses
- dispatches step execution and tool calls through `execution/`
- emits verification outcomes and serialized artifacts

Effectful behavior should stay explicit in execution and interface layers. Core models should remain pure.
