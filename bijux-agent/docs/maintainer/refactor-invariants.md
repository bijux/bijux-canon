# Refactor invariants (maintainer)

Refactors are allowed to change structure, but not the contract.

## Must stay true

- trace schema versioning remains meaningful (no silent breaking changes)
- failure taxonomy remains total (profiles cover all classes)
- canonical pipeline definition remains stable unless explicitly versioned
- docs checksum invariant continues to pass

## If you must break something

- state the break explicitly
- bump the relevant version (trace schema and/or contract)
- update spec pages and checksums
