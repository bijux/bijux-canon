# Execution Mode Comparison

| Mode | Replayable? | Auditable? | Fast? | Safe for prod? |
| --- | --- | --- | --- | --- |
| Deterministic (exact) | Yes | Yes | Moderate | Yes |
| Deterministic (vector store) | Yes | Yes | Moderate | Yes |
| ND bounded | Bounded | Yes | Fast | Yes, with checks |
| ND best‑effort | No | Partial | Fastest | Only with caution |
