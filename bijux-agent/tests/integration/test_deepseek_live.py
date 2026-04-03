from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any

import pytest

from bijux_agent.constants import AGENT_CONTRACT_VERSION
from bijux_agent.models.adapter_factory import build_adapter
from bijux_agent.models.llm_adapter import DeepSeekAdapter
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.tracing import (
    ReplayMetadata,
    ReplayStatus,
    TraceEntry,
    TraceRecorder,
)
from bijux_agent.utilities.prompt_hash import prompt_hash


@pytest.mark.live
def test_deepseek_integration_metadata_and_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not configured")
    monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)

    attempts: dict[str, int] = {"count": 0}
    original = DeepSeekAdapter._call_with_retries

    def tracked(self: DeepSeekAdapter, payload: dict[str, Any]) -> Mapping[str, Any]:
        attempts["count"] += 1
        return original(self, payload)

    monkeypatch.setattr(DeepSeekAdapter, "_call_with_retries", tracked)

    config = {
        "model": "deepseek-chat",
        "temperature": 0.2,
        "max_tokens": 256,
        "timeout": 30.0,
        "retry_attempts": 0,
    }
    adapter = build_adapter(config)
    assert isinstance(adapter, DeepSeekAdapter)

    prompt = "Return the word OK only."
    response = adapter.generate(prompt)
    model_metadata = response.metadata["model_metadata"]
    assert model_metadata["provider"] == "DeepSeek"
    assert model_metadata["model_name"] == "deepseek-chat"
    assert model_metadata["temperature"] == 0.2
    assert model_metadata["max_tokens"] == 256
    assert attempts["count"] == 1

    recorder = TraceRecorder(
        run_id="live-deepseek",
        path=tmp_path / "trace.json",
    )
    entry = TraceEntry(
        agent_id="live-deepseek",
        node="deepseek",
        status="success",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        input={"prompt": prompt},
        output={
            "text": response.text,
            "artifacts": {},
            "scores": {"quality": response.confidence},
            "confidence": response.confidence,
            "metadata": {
                "contract_version": AGENT_CONTRACT_VERSION,
                "model_metadata": model_metadata,
            },
        },
        scores={"quality": response.confidence},
        prompt_hash=prompt_hash(prompt),
        model_hash=prompt_hash("deepseek-chat"),
        phase=PipelinePhase.EXECUTE.value,
        run_id="live-deepseek",
        replay_metadata=ReplayMetadata(
            input_hash=prompt_hash(prompt),
            config_hash="integration",
            model_id="live-deepseek",
            convergence_hash="",
            model_metadata=adapter.metadata(),
        ),
    )

    recorder.record_entry(entry)
    assert recorder.trace.header.replay_status == ReplayStatus.NON_REPLAYABLE
