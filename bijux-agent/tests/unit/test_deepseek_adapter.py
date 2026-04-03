from __future__ import annotations

import os
from typing import Any
from urllib import error as urllib_error

import pytest
import requests

from bijux_agent.models.adapter_factory import build_adapter
from bijux_agent.models.llm_adapter import (
    AdapterConfig,
    DeepSeekAdapter,
    DeepSeekAdapterError,
)
from bijux_agent.models.registry import Provider, resolve_provider
from bijux_agent.pipeline.results.failure import (
    FailureCategory,
    FailureClass,
)

SKIP_DOTENV_ENV = "BIJUX_AGENT_SKIP_DOTENV"


# ---------------------------------------------------------------------------
# NOTE (pytype):
# Nested classes referenced in annotations (even with future annotations)
# can produce "Name ... is not defined" under pytype.
# Keep small response stubs at module scope.
# ---------------------------------------------------------------------------
class DummyResponse200:
    status_code = 200

    def json(self) -> dict[str, Any]:
        return {"choices": [{"message": {"content": "ok"}}]}


class ErrorResponse418:
    status_code = 418

    def json(self) -> dict[str, Any]:
        return {"error": "tidal wave"}


@pytest.fixture(autouse=True)
def skip_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SKIP_DOTENV_ENV, "1")


def _deepseek_config(**overrides: Any) -> AdapterConfig:
    return AdapterConfig(
        provider=Provider.DEEPSEEK.value,
        model_name="deepseek-chat",
        temperature=float(overrides.get("temperature", 0.0)),
        max_tokens=int(overrides.get("max_tokens", 512)),
        timeout=float(overrides.get("timeout", 30.0)),
        retry_attempts=int(overrides.get("retry_attempts", 0)),
    )


def test_resolve_provider_accepts_deepseek_prefix() -> None:
    assert resolve_provider("deepseek-chat") is Provider.DEEPSEEK


def test_adapter_selection_uses_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    adapter = build_adapter({"model": "deepseek-chat"})
    assert isinstance(adapter, DeepSeekAdapter)
    assert adapter.base_url == DeepSeekAdapter.DEFAULT_BASE_URL
    headers = adapter._headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


def test_config_drives_model_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def _boom(*args, **kwargs):  # noqa: ANN001 - test helper
        raise AssertionError("OpenAI adapter should not be instantiated")

    monkeypatch.setattr("bijux_agent.models.adapter_factory.OpenAIAdapter", _boom)
    adapter = build_adapter({"model": "deepseek-chat"})
    assert isinstance(adapter, DeepSeekAdapter)


def test_deepseek_payload_shape_is_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    adapter = DeepSeekAdapter(_deepseek_config(temperature=0.2, max_tokens=256))
    payload = adapter._build_payload("hello world")
    assert list(payload.items()) == [
        ("model", "deepseek-chat"),
        ("messages", [{"role": "user", "content": "hello world"}]),
        ("temperature", 0.2),
        ("max_tokens", 256),
    ]


def test_missing_deepseek_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(DeepSeekAdapterError) as exc_info:
        build_adapter({"model": "deepseek-chat"})
    assert exc_info.value.failure_class == FailureClass.VALIDATION_ERROR


def test_missing_model_selection_requires_config() -> None:
    with pytest.raises(DeepSeekAdapterError) as exc_info:
        build_adapter({})
    assert exc_info.value.failure_class == FailureClass.VALIDATION_ERROR


def test_deepseek_model_env_overrides_conflicting_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    with pytest.raises(DeepSeekAdapterError):
        build_adapter({"model": "gpt-4o-mini"})


def test_retry_attempts_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    adapter = DeepSeekAdapter(_deepseek_config(retry_attempts=2))

    attempts = {"count": 0}

    def failing_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        attempts["count"] += 1
        raise urllib_error.URLError("boom")

    monkeypatch.setattr(DeepSeekAdapter, "_post_once", failing_post)
    with pytest.raises(DeepSeekAdapterError):
        adapter.generate("prompt")
    assert attempts["count"] == 3


def test_timeout_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured: dict[str, float | None] = {}

    def fake_post(
        *args: Any, timeout: float | None = None, **kwargs: Any
    ) -> DummyResponse200:
        captured["timeout"] = timeout
        return DummyResponse200()

    monkeypatch.setattr(requests, "post", fake_post)

    adapter = DeepSeekAdapter(_deepseek_config(timeout=15.0))
    response = adapter.generate("prompt")
    assert captured["timeout"] == 15.0
    assert response.text == "ok"


def test_timeout_classification_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    adapter = DeepSeekAdapter(_deepseek_config(timeout=0.1, retry_attempts=1))
    attempts: dict[str, int] = {"count": 0}

    def stall(self, payload: dict[str, Any]) -> dict[str, Any]:
        attempts["count"] += 1
        raise urllib_error.URLError("timed out")

    monkeypatch.setattr(DeepSeekAdapter, "_post_once", stall)
    with pytest.raises(DeepSeekAdapterError) as exc_info:
        adapter.generate("prompt")
    assert attempts["count"] == 2
    error = exc_info.value
    assert error.failure_class == FailureClass.RESOURCE_EXHAUSTION
    assert error.failure_category == FailureCategory.OPERATIONAL


def test_provider_error_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    class FakeClient:
        def post(self, *args: Any, **kwargs: Any) -> ErrorResponse418:
            return ErrorResponse418()

    adapter = DeepSeekAdapter(
        _deepseek_config(),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    with pytest.raises(DeepSeekAdapterError) as exc_info:
        adapter.generate("prompt")
    error = exc_info.value
    assert error.failure_class == FailureClass.EXECUTION_ERROR
    assert error.failure_category == FailureCategory.OPERATIONAL
    assert str(error) == "DeepSeek API error: status 418"


@pytest.mark.live
def test_deepseek_live_minimal_prompt() -> None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not configured")
    adapter = DeepSeekAdapter(_deepseek_config())
    try:
        response = adapter.generate("Return the word OK only.")
    except urllib_error.URLError as exc:
        pytest.skip(f"Live DeepSeek call failed ({exc}); skipping")
    assert response.text.strip()
    assert response.prompt_hash
    assert response.model_hash
