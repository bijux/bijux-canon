# Vector Store Profile

Every vector-store integration should describe itself through a stable profile
instead of through vague marketing language or backend folklore.

## A useful profile should say

- whether exact queries are deterministic
- whether ANN queries are supported
- whether delete and filtering are supported
- what consistency semantics are exposed
- which backend version and plugin source produced the report

## Why this matters

`bijux-canon-index` treats backends as execution dependencies with consequences
for provenance and replay, not as invisible infrastructure.

When adding a backend, declare the narrowest truthful profile first. Expanding a
capability claim later is safer than over-promising and then having to explain a
broken replay or comparison story.
