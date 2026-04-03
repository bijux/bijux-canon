# Common Mistakes & Misconceptions

Determinism

- “Exact means fast.” It can be slower than ANN at scale.
- “Replay is optional.” If you care about audits, it is required.

ND

- “ND is just faster exact.” It is approximate and bounded.
- “Seeds make ND deterministic.” Seeds help; they don’t replace bounds.

Vector stores

- “Deletes are permanent.” Not unless the backend guarantees it.
- “All backends are equivalent.” Capabilities differ.
