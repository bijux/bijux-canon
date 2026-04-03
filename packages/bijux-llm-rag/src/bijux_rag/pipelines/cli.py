# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 6: config overrides and CLI-friendly spec handling (end-of-Bijux RAG).

This module is stdlib-only and keeps the "override" mechanics pure/testable.
Shells can parse args and delegate to these helpers.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .configured import PipelineConfig, StepConfig


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries (override wins)."""

    out: dict[str, Any] = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def parse_override(expr: str) -> dict[str, Any]:
    """Parse a simple dotted override like `a.b.c=1` into nested dicts.

    Values are parsed as: bool/int/float/str.
    """

    expr = expr.strip()
    if not expr:
        return {}
    if "=" not in expr:
        raise ValueError("override must contain '='")
    path_s, value_s = expr.split("=", 1)
    keys = [k for k in path_s.split(".") if k]
    if not keys:
        raise ValueError("override path is empty")

    raw: Any = value_s
    v = value_s.strip()
    if v.lower() in {"true", "false"}:
        raw = v.lower() == "true"
    else:
        try:
            raw = int(v)
        except ValueError:
            try:
                raw = float(v)
            except ValueError:
                raw = v

    out: dict[str, Any] = {}
    cur: dict[str, Any] = out
    for k in keys[:-1]:
        nxt: dict[str, Any] = {}
        cur[k] = nxt
        cur = nxt
    cur[keys[-1]] = raw
    return out


def apply_step_params(
    cfg: PipelineConfig, step_name: str, params: dict[str, Any]
) -> PipelineConfig:
    """Return a new PipelineConfig with merged params for all matching steps."""

    steps: list[StepConfig] = []
    for step in cfg.steps:
        if step.name != step_name:
            steps.append(step)
            continue
        merged = deep_merge(dict(step.params), params)
        steps.append(replace(step, params=merged))
    return replace(cfg, steps=tuple(steps))


__all__ = ["deep_merge", "parse_override", "apply_step_params"]
