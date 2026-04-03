# TESTS

`bijux-canon-dev` tests should stay focused and cheap:
- module import coverage
- helper behavior with small fixture inputs
- package-maintenance adapters used by tests and root gates

Expensive end-to-end behavior belongs in the package that consumes the helper, not here.
