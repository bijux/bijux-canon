# Invariants

These are the rules the package should keep even when backend support grows.

- execution artifacts remain provenance-aware and replay-relevant
- plugin loading remains explicit, declared, and inspectable
- backend details do not silently redefine stable domain meaning
- pinned schemas change only on purpose and with review

If a shortcut makes the package harder to explain after the fact, it is
probably violating an invariant.
