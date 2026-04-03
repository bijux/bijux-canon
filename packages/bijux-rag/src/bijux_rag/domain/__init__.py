# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Pure, production-facing architecture primitives (end-of-Bijux RAG).

Bijux RAG introduces a production architecture around the existing pure core:
- Capability protocols (typed `Protocol`s)
- Structured logs as pure data (`LogEntry` + Writer)
- Idempotent effect design for safe retries/replays

Note: `IOPlan` + IOPlan-specific retry/tx helpers live in `bijux_rag.domain.effects`.
"""

from .capabilities import Cache, Clock, Logger, Storage, StorageRead, StorageWrite
from .composition import chain_io, logged_read
from .idempotent import AtomicWriteCap, content_key, idempotent_write
from .logging import LogEntry, LogMonoid, Logs, log_tell, trace_stage, trace_value

__all__ = [
    # Logging (pure data)
    "LogEntry",
    "Logs",
    "LogMonoid",
    "log_tell",
    "trace_stage",
    "trace_value",
    # Capabilities
    "StorageRead",
    "StorageWrite",
    "Storage",
    "Clock",
    "Logger",
    "Cache",
    # Composition helpers
    "chain_io",
    "logged_read",
    # Idempotency + retry
    "AtomicWriteCap",
    "content_key",
    "idempotent_write",
]
