# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Boundary parsing for ingest configuration payloads."""

from __future__ import annotations

from collections.abc import Mapping

from bijux_canon_ingest.config.cleaning import DEFAULT_CLEAN_CONFIG, RULES, CleanConfig
from bijux_canon_ingest.config.ingest import IngestConfig
from bijux_canon_ingest.core.types import RagEnv
from bijux_canon_ingest.result import Err, Ok, Result


def parse_ingest_config(raw: Mapping[str, object]) -> Result[IngestConfig, str]:
    """Parse untyped boundary config into frozen ``IngestConfig``."""

    chunk_size_raw = raw.get("chunk_size", 512)
    if not isinstance(chunk_size_raw, int):
        return Err(
            f"Invalid config: chunk_size must be int (got {type(chunk_size_raw).__name__})"
        )

    rule_names_raw = raw.get("clean_rules", DEFAULT_CLEAN_CONFIG.rule_names)
    if not isinstance(rule_names_raw, (tuple, list)) or not all(
        isinstance(name, str) for name in rule_names_raw
    ):
        return Err("Invalid config: clean_rules must be list[str] or tuple[str, ...]")
    rule_names = tuple(rule_names_raw)
    missing = [name for name in rule_names if name not in RULES]
    if missing:
        available = ", ".join(sorted(RULES))
        return Err(
            f"Invalid config: unknown clean rule(s): {missing}; available: {available}"
        )

    return Ok(
        IngestConfig(
            env=RagEnv(chunk_size_raw), clean=CleanConfig(rule_names=rule_names)
        )
    )


__all__ = ["parse_ingest_config"]
