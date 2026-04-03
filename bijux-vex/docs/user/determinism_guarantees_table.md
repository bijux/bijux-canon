# Determinism Guarantees vs Best‑Effort

| Category | Description | Why it exists |
| --- | --- | --- |
| Guaranteed | Exact search, canonical ordering, replay when hashes match | Needed for audit and regression proof |
| Best‑effort | Performance targets, optional backend optimizations | Varies by environment |
| Not guaranteed | Cross‑backend numeric equality, approximate search stability | Outside the deterministic contract |
