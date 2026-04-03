"""Factory for selecting LLM adapters based on configuration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from typing import Any

from bijux_agent.config.env import load_environment
from bijux_agent.models.llm_adapter import (
    AdapterConfig,
    BaseLLMAdapter,
    DeepSeekAdapter,
    DeepSeekAdapterError,
    LocalAdapter,
    MockAdapter,
    OpenAIAdapter,
)
from bijux_agent.models.registry import (
    DEEPSEEK_PREFIX,
    Provider,
    resolve_provider,
    validate_model_name,
)
from bijux_agent.pipeline.results.failure import FailureClass


def _resolve_model_name(config: Mapping[str, Any]) -> str:
    env_model = os.getenv("DEEPSEEK_MODEL")
    config_model = config.get("model")
    if env_model:
        normalized = env_model.strip()
        if not normalized:
            raise DeepSeekAdapterError(
                "DEEPSEEK_MODEL cannot be empty", FailureClass.VALIDATION_ERROR
            )
        if not normalized.startswith(DEEPSEEK_PREFIX):
            raise DeepSeekAdapterError(
                "DEEPSEEK_MODEL must start with 'deepseek-'",
                FailureClass.VALIDATION_ERROR,
            )
        if config_model and str(config_model) != normalized:
            raise DeepSeekAdapterError(
                "DEEPSEEK_MODEL overrides explicit model selection",
                FailureClass.VALIDATION_ERROR,
            )
        return normalized
    if config_model:
        return str(config_model)
    raise DeepSeekAdapterError(
        "Model selection is required; set `model` in configuration",
        FailureClass.VALIDATION_ERROR,
    )


DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 512
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRY_ATTEMPTS = 0


def _resolve_temperature(config: Mapping[str, Any], provider: Provider) -> float:
    if "temperature" in config and config["temperature"] is not None:
        return float(config["temperature"])
    if provider is Provider.DEEPSEEK:
        env_temp = os.getenv("DEEPSEEK_TEMPERATURE")
        if env_temp is not None and env_temp != "":
            return float(env_temp)
    return DEFAULT_TEMPERATURE


def _resolve_max_tokens(config: Mapping[str, Any]) -> int:
    if "max_tokens" in config and config["max_tokens"] is not None:
        return int(config["max_tokens"])
    return DEFAULT_MAX_TOKENS


def _resolve_timeout(config: Mapping[str, Any]) -> float:
    if "timeout" in config and config["timeout"] is not None:
        return float(config["timeout"])
    return DEFAULT_TIMEOUT


def _resolve_retry_attempts(config: Mapping[str, Any]) -> int:
    if "retry_attempts" in config and config["retry_attempts"] is not None:
        return int(config["retry_attempts"])
    return DEFAULT_RETRY_ATTEMPTS


def _build_deepseek_adapter(
    adapter_config: AdapterConfig, user_config: Mapping[str, Any]
) -> BaseLLMAdapter:
    base_url = user_config.get("base_url", DeepSeekAdapter.DEFAULT_BASE_URL)
    return DeepSeekAdapter(adapter_config, base_url=base_url)


def _build_openai_adapter(
    adapter_config: AdapterConfig, user_config: Mapping[str, Any]
) -> BaseLLMAdapter:
    _ = user_config
    return OpenAIAdapter(adapter_config)


def _build_mock_adapter(
    adapter_config: AdapterConfig, user_config: Mapping[str, Any]
) -> BaseLLMAdapter:
    response = user_config.get("canned_response")
    return MockAdapter(adapter_config, canned_response=response)


def _build_local_adapter(
    adapter_config: AdapterConfig, user_config: Mapping[str, Any]
) -> BaseLLMAdapter:
    _ = user_config
    return LocalAdapter(adapter_config)


_ADAPTER_BUILDERS: dict[
    Provider, Callable[[AdapterConfig, Mapping[str, Any]], BaseLLMAdapter]
] = {
    Provider.OPENAI: _build_openai_adapter,
    Provider.DEEPSEEK: _build_deepseek_adapter,
    Provider.MOCK: _build_mock_adapter,
    Provider.LOCAL: _build_local_adapter,
}


SKIP_DOTENV_ENV = "BIJUX_AGENT_SKIP_DOTENV"


def build_adapter(config: Mapping[str, Any]) -> BaseLLMAdapter:
    """Build an adapter from the provided config."""
    if os.getenv(SKIP_DOTENV_ENV) != "1":
        load_environment()
    model_name = _resolve_model_name(config)
    validate_model_name(model_name)
    provider = resolve_provider(model_name)
    temperature = _resolve_temperature(config, provider)
    max_tokens = _resolve_max_tokens(config)
    timeout = _resolve_timeout(config)
    retry_attempts = _resolve_retry_attempts(config)

    adapter_config = AdapterConfig(
        provider=provider.value,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        retry_attempts=retry_attempts,
    )

    builder = _ADAPTER_BUILDERS.get(provider)
    if not builder:
        raise DeepSeekAdapterError(
            f"No adapter registered for provider {provider}",
            FailureClass.VALIDATION_ERROR,
        )
    return builder(adapter_config, config)


__all__ = ["build_adapter"]
