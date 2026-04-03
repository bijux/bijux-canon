"""Explicit default settings for pipeline configuration."""

from __future__ import annotations

PIPELINE_DEFAULTS: dict[str, object] = {
    "max_retries": 2,
    "chunk_size": 1000,
    "shard_threshold": 1_000_000,
    "max_iterations": 3,
    "concurrency_limit": 10,
    "stage_timeout": 300.0,
    "retry_delay": 1.0,
    "quality_threshold": 0.8,
}

MINIMAL_REFERENCE_CONFIG: dict[str, object] = {
    "pipeline": {"parameters": {"stage_timeout": 15}},
    "agents": ["file_reader", "task_handler"],
}
