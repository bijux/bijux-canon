# Audit-Grade
> What constitutes audit-grade evidence in this system.

## Sufficient artifacts
Audit-grade evidence consists of the persisted execution trace, the resolved plan, declared policies, and the dataset descriptor with DVC identity. These artifacts establish what ran, under which rules, and with which inputs. If any of these are missing, audit-grade status is not met.

## Intentionally excluded
Runtime memory, ephemeral caches, and live tool sessions are intentionally excluded from audit evidence. They are not stable, not replayable, and not part of the contract. Their absence is deliberate and should not be interpreted as incomplete persistence.

## Auditor inference limits
Auditors can verify that recorded events and artifacts match declared contracts and replay acceptability. They cannot infer hidden randomness, unstated external inputs, or undeclared dataset changes. Audit conclusions are bounded by what is explicitly persisted.
