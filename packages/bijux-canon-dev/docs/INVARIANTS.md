# INVARIANTS

`bijux-canon-dev` keeps these invariants:
- product packages do not re-accumulate duplicated maintenance scripts
- repository automation stays callable from root-owned gates
- tooling names remain durable and package-neutral where possible
- package-specific maintenance helpers stay under `packages/`, not product code
