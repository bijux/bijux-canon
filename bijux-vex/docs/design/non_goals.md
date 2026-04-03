---
title: Non-goals
---

# Non-goals (hard exclusions)

bijux-vex is a vector execution engine. The following are explicitly out of scope:

- Not a vector database or general-purpose datastore.
- Not a model runner or embedding factory.
- Not a retrieval framework or RAG orchestration layer.
- Not a streaming/online serving tier or SLA scheduler.
- Not an auto-tuner for ANN parameters.
- Not a distributed coordination or sharding system.
- Not a streaming/async result delivery mechanism; executions are bounded, audited batches only.

Any change that drifts into these areas must be rejected unless the scope is explicitly revised.
