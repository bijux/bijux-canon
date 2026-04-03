# Why this is hard

- Vector execution is harder than storage: algorithms, randomness, and approximation choices happen at runtime, not at ingest.
- ANN breaks naïve determinism: traversal order, pruning, and sampling introduce entropy that must be declared and bounded.
- Replay is non-trivial: deterministic replay demands bit-stability; ND replay demands statistical envelopes and provenance strong enough to prove consistency.
- Backend drift is silent: without comparison and divergence detection, approximate systems rot unnoticed.
- Budgets are hard constraints: latency/memory/probe limits must halt execution, not merely warn.
