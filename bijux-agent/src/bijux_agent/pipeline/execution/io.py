"""IO helpers for persisting pipeline outputs."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, TypeAlias

PipelineExecutionResult: TypeAlias = dict[str, Any]


class PipelineIOMixin:
    """Encapsulate file-system interactions for pipeline outputs."""

    results_dir: Path
    logger: Any
    logger_manager: Any
    _metric_type: Any

    def _persist_pipeline_result(
        self,
        pipeline_result: PipelineExecutionResult,
        context_id: str,
    ) -> None:
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        result_file = (
            self.results_dir / f"pipeline_result_{context_id}_{timestamp}.json"
        )
        try:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(pipeline_result, f, ensure_ascii=False, indent=2)
            self.logger.info(
                "Pipeline results saved",
                extra={
                    "context": {"result_file": str(result_file), "stage": "completion"}
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to save pipeline results",
                extra={
                    "context": {
                        "result_file": str(result_file),
                        "error": str(e),
                        "stage": "completion",
                    }
                },
            )
