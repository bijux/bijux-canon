
## Minimal Mental Model
STATUS: EXPLANATORY

- bijux-rar is a pipeline that turns a problem statement into a verified trace of reasoning steps.
- Each step emits structured events; nothing is free-form text that bypasses checks.
- Evidence is chunked, hashed, and cited by byte span. Claims must point to those spans.
- Verification replays the trace logic against artifacts and fails closed on any mismatch.
- Replay guarantees: with the same artifacts and config, fingerprints are identical.

Audience: skeptical practitioners who need auditable reasoning, not convenience.***
