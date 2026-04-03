"""Telemetry metric support for agent logging."""

from __future__ import annotations

import asyncio
from collections import defaultdict
import datetime
from enum import Enum
import json
from logging import Logger
from pathlib import Path
import threading
from typing import Any

from bijux_canon_agent.observability.log_handlers import LoggerConfig


class MetricType(Enum):
    """Enum for supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class LoggerTelemetry:
    """Collect and export telemetry metrics for a logger manager."""

    def __init__(self, config: LoggerConfig, logger: Logger) -> None:
        self.config = config
        self.logger = logger
        self._metric_tasks: list[asyncio.Task[Any]] = []
        self._telemetry_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "type": MetricType.COUNTER.value,
                "value": 0,
                "histogram": (
                    defaultdict(int) if self.config.histogram_buckets else None
                ),
            }
        )
        self._metrics_lock = threading.Lock()

    def record(
        self,
        metric_name: str,
        value: int | float,
        metric_type: MetricType = MetricType.COUNTER,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a telemetry metric and export it when configured."""
        if not self.config.telemetry_enabled:
            return

        tags_dict = dict(tags or {})
        with self._metrics_lock:
            metric = self._telemetry_metrics[metric_name]
            metric["type"] = metric_type.value
            metric["tags"] = tags_dict

            if metric_type == MetricType.COUNTER:
                metric["value"] += value
            elif metric_type == MetricType.GAUGE:
                metric["value"] = value
            elif metric_type == MetricType.HISTOGRAM and self.config.histogram_buckets:
                metric["value"] += value
                histogram = metric.get("histogram")
                if isinstance(histogram, dict):
                    for bucket in self.config.histogram_buckets:
                        if value <= bucket:
                            histogram[f"le_{bucket}"] = (
                                histogram.get(f"le_{bucket}", 0) + 1
                            )
                            break

            self.logger.debug(
                f"Metric recorded: {metric_name} = {value}",
                extra={
                    "metric_name": metric_name,
                    "metric_type": metric_type.value,
                    "tags": tags_dict,
                    "metrics": {
                        metric_name: {"value": value, "type": metric_type.value}
                    },
                },
            )

            if self.config.metric_export_callback:
                self._export_metric(
                    self._build_metric_data(metric_name, metric, metric_type, tags_dict)
                )

    async def export_async(self, metric_data: dict[str, Any]) -> None:
        """Export metric data asynchronously via the configured callback."""
        callback = self.config.metric_export_callback
        if callback is None:
            return
        try:
            await asyncio.to_thread(callback, metric_data)
        except Exception as exc:
            self.logger.error(
                f"Async metric export failed: {exc}",
                extra={"metric_name": metric_data["name"], "error": str(exc)},
            )

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return collected telemetry metrics."""
        with self._metrics_lock:
            return dict(self._telemetry_metrics)

    def reset(self) -> None:
        """Reset all telemetry metrics."""
        with self._metrics_lock:
            self._telemetry_metrics.clear()
        self.logger.debug("Telemetry metrics reset", extra={"stage": "metrics_reset"})

    def export_to_file(self, file_path: str | Path) -> None:
        """Export collected telemetry metrics to a JSON file."""
        metrics = self.snapshot()
        try:
            with open(file_path, "w", encoding="utf-8") as file_obj:
                json.dump(metrics, file_obj, indent=2)
            self.logger.info(
                f"Metrics exported to {file_path}",
                extra={"stage": "metrics_export"},
            )
        except Exception as exc:
            self.logger.error(
                f"Metrics export to file failed: {exc}",
                extra={"file_path": str(file_path), "error": str(exc)},
            )

    def _build_metric_data(
        self,
        metric_name: str,
        metric: dict[str, Any],
        metric_type: MetricType,
        tags: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "name": metric_name,
            "type": metric_type.value,
            "value": metric["value"],
            "tags": tags,
            "histogram": (
                dict(metric["histogram"])
                if metric_type == MetricType.HISTOGRAM
                else None
            ),
            "timestamp": datetime.datetime.now().isoformat(),
        }

    def _export_metric(self, metric_data: dict[str, Any]) -> None:
        try:
            task = asyncio.create_task(self.export_async(metric_data))
            self._metric_tasks.append(task)
            self._metric_tasks = [task_ref for task_ref in self._metric_tasks if not task_ref.done()]
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.export_async(metric_data))
            loop.close()
        except Exception as exc:
            self.logger.error(
                f"Metric export failed: {exc}",
                extra={"metric_name": metric_data["name"], "error": str(exc)},
            )


__all__ = ["LoggerTelemetry", "MetricType"]
