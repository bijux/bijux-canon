
STATUS: AUTHORITATIVE
## Maintainer Rules

- PRs that relax invariants (grounding, replay, determinism) are rejected.
- PRs that add new event kinds without schema/version bump are rejected.
- Refactors that add hidden state or global randomness are rejected.
- Doc PRs must obey `docs/doc_invariants.md`; violations are rejected.
- Non-deterministic features must be opt-in, recorded, and replayable; otherwise rejected.
- Mandatory gates (lint, test, quality, security, api) must pass before review.
- Changes that can fail determinism or replay must be redesigned or dropped.
- Elegance does not trump invariants; if in doubt, keep the invariant intact.***
