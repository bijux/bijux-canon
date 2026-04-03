# SPDX-FileCopyrightText: Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
"""Typed stub for FileReaderAgent used by pipeline tests."""

from __future__ import annotations

from typing import Any

from bijux_agent.agents.file_reader import FileReaderAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.utilities.logger_manager import LoggerManager


class FileReaderStub(FileReaderAgent):
    """Minimal FileReaderAgent replacement that produces deterministic payloads."""

    def __init__(
        self,
        logger_manager: LoggerManager,
        config: dict[str, Any] | None = None,
    ) -> None:
        resolved_config = config or {"file_reader": {}}
        super().__init__(resolved_config, logger_manager)

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "text": context.get("text", "file-reader-stub"),
            "artifacts": {"file_path": context.get("file_path")},
            "scores": {"quality": 1.0},
            "confidence": 0.95,
            "metadata": {
                "contract_version": CONTRACT_VERSION,
                "file_reader_stub": True,
            },
        }
        validated = self.validate_output(payload)
        result: dict[str, Any] = validated.model_dump()
        return result
