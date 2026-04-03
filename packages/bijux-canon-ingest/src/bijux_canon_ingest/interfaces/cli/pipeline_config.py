# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Helpers for loading CLI-owned pipeline configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bijux_canon_ingest.application.pipeline_definitions.configured import PipelineConfig, StepConfig


def load_pipeline_config(path: Path) -> PipelineConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError("config must be an object with a 'steps' field")

    steps_raw = data["steps"]
    if not isinstance(steps_raw, list):
        raise ValueError("config.steps must be a list")

    steps: list[StepConfig] = []
    for step in steps_raw:
        if not isinstance(step, dict) or "name" not in step:
            raise ValueError("each step must be an object with a 'name'")
        name: Any = step["name"]
        params: Any = step.get("params", {})
        if not isinstance(name, str) or not isinstance(params, dict):
            raise ValueError("step.name must be str and step.params must be object")
        steps.append(StepConfig(name=name, params=params))

    return PipelineConfig(steps=tuple(steps))


__all__ = ["load_pipeline_config"]
