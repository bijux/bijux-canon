# Architecture diagram (spec)

This diagram is a *conceptual* view of the runtime contract.

```
Caller (CLI / HTTP)
        |
        v
+------------------------+
| AuditableDocPipeline   |
|  (canonical phases)    |
+------------------------+
   |        |        |
   v        v        v
 Agents   Decision  Failure model
   |        |        |
   +--------+--------+
            |
            v
     +--------------+
     | Trace writer |
     | (run_trace)  |
     +--------------+
            |
            v
     +--------------+
     | final_result |
     +--------------+
```

For the concrete module map, see `docs/architecture/ARCHITECTURE.md`.
