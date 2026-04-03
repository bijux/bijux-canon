API handlers are intentionally not unit-tested in this repository.
The OpenAPI schema and schemathesis runs are the contract gate.
Schema drift is the primary failure mode we protect against here.
Coverage percentages are misleading because API behavior is stubbed.
We prefer contract validation over handler-level tests.
