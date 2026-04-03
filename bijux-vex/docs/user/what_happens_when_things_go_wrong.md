# What Happens If Things Go Wrong?

Crashes

- Incomplete runs are marked invalid and excluded from replay and compare.
- Artifacts written partially are refused on load.

Partial writes

- Atomic write strategy prevents partial state from being treated as valid.
- If partial state is detected, execution refuses and explains why.

Backend outages

- Requests fail fast with structured error payloads.
- Circuit breakers stop repeated failures from cascading.

ND failures

- ND refuses when bounds cannot be met.
- Witness failures are recorded in provenance.
