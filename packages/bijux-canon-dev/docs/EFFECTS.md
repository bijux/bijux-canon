# EFFECTS

`bijux-canon-dev` performs repository-maintenance effects:
- reads package metadata, schemas, and docs
- spawns subprocesses such as `git`, `deptry`, and `pip`
- writes generated requirement files and OpenAPI snapshots
- inspects repository state for policy checks

It should remain explicit about filesystem and subprocess effects because those are its core job.
