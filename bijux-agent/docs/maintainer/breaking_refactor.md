# Breaking refactor policy (maintainer)

“Breaking” means a consumer can no longer safely interpret artifacts or rely on the contract.

## Examples of breaking changes

- removing or renaming required `final_result.json` fields
- changing trace semantics without bumping `trace_schema_version`
- altering failure taxonomy values (enums) without migration
- changing replayability classification rules

## Process

1. Declare the break explicitly.
2. Update spec pages.
3. Bump the relevant version(s).
4. Provide an upgrade/migration path when feasible.
