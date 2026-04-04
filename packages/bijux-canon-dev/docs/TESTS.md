# Tests

Tests in `bijux-canon-dev` should stay fast, focused, and honest about what the
package owns.

## What to test here

- direct helper behavior with small, controlled fixtures
- importability and stable entrypoints used by automation
- package-maintenance adapters that root gates depend on

## What not to over-test here

- product workflows that belong to another package
- expensive end-to-end scenarios that are already covered where the helper is consumed

The best test split is usually:

- verify the helper here
- verify the repository workflow at the root or in the consuming package
