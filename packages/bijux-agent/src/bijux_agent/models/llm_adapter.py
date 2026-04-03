"""Lightweight adapter layer for interacting with LLM APIs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
import importlib
import socket
from types import ModuleType
from typing import Any, cast
from urllib import error as urllib_error
from urllib import parse as urllib_parse

from pydantic import ConfigDict, Field
import requests

from bijux_agent.config.env import key_for_provider
from bijux_agent.pipeline.results.failure import (
    FailureCategory,
    FailureClass,
    failure_profile_for,
)
from bijux_agent.schema.base import TypedBaseModel
from bijux_agent.tracing.trace import ModelMetadata
from bijux_agent.utilities.prompt_hash import prompt_hash

_openai_module: ModuleType | None = None
try:  # pragma: no cover
    _openai_module = importlib.import_module("openai")
except ImportError:  # pragma: no cover
    _openai_module = None
openai: ModuleType | None = _openai_module


class DeepSeekAdapterError(RuntimeError):
    """Structured failure for DeepSeek adapter requests."""

    failure_class: FailureClass
    failure_category: FailureCategory

    def __init__(self, message: str, failure_class: FailureClass) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.failure_category = failure_profile_for(failure_class).category


class LLMResponse(TypedBaseModel):
    """Normalized response container for any backend adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    model: str
    prompt_hash: str
    model_hash: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)


@dataclass(frozen=True)
class AdapterConfig:
    """Shared configuration used to initialize adapters."""

    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout: float | None = None
    retry_attempts: int = 0

    def model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            provider=self.provider,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


@dataclass(frozen=True)
class AdapterCapabilities:
    """Capabilities supported by an adapter implementation."""

    streaming: bool = False
    retries: bool = False


class BaseLLMAdapter(ABC):
    """Base specialization that keeps metadata/temperature handling consistent."""

    def __init__(self, config: AdapterConfig, client: Any | None = None) -> None:
        self._config = config
        self._client = client

    @property
    def config(self) -> AdapterConfig:
        return self._config

    @property
    def client(self) -> Any | None:
        return self._client

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Generate text from the language model."""

    def metadata(self) -> ModelMetadata:
        return self._config.model_metadata()

    @abstractmethod
    def capabilities(self) -> AdapterCapabilities:
        """Describe the adapter's supported operations."""

    def _prepare_metadata(
        self, extra: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]:
        model_meta = self.metadata()
        base: dict[str, Any] = {
            "provider": model_meta.provider,
            "model_name": model_meta.model_name,
            "temperature": model_meta.temperature,
            "max_tokens": model_meta.max_tokens,
            "model_metadata": asdict(model_meta),
        }
        if extra:
            base.update(extra)
        return base


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter that delegates to OpenAI chat completions."""

    def __init__(self, config: AdapterConfig, client: Any | None = None) -> None:
        super().__init__(config)
        actual_client = client
        if actual_client is None:
            if openai is None:
                raise RuntimeError("openai package is not installed")
            actual_client = openai
        self._client = actual_client

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        metadata = self._prepare_metadata(kwargs.get("metadata"))
        completion_kwargs = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **{k: v for k, v in kwargs.items() if k != "metadata"},
        }
        client = cast(ModuleType, self._client)
        response = client.ChatCompletion.create(**completion_kwargs)
        text = response.choices[0].message.content
        return LLMResponse(
            text=text,
            model=self.config.model_name,
            prompt_hash=prompt_hash(prompt),
            model_hash=prompt_hash(self.config.model_name),
            metadata={**metadata, "usage": getattr(response, "usage", {})},
            confidence=float(kwargs.get("confidence", 0.8)),
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=False, retries=False)


class DeepSeekAdapter(BaseLLMAdapter):
    """Adapter for DeepSeek chat completions."""

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(
        self,
        config: AdapterConfig,
        base_url: str = DEFAULT_BASE_URL,
        client: Any | None = None,
    ) -> None:
        super().__init__(config, client=client)
        self.base_url = base_url
        self._api_key = self._resolve_api_key()
        timeout_value = config.timeout if config.timeout is not None else 30.0
        self._timeout = self._validate_timeout(timeout_value)
        self.retry_attempts = max(0, int(config.retry_attempts))
        self._validate_base_url()

    def _resolve_api_key(self) -> str:
        try:
            return key_for_provider("Deepseek")
        except RuntimeError as exc:
            raise DeepSeekAdapterError(str(exc), FailureClass.VALIDATION_ERROR) from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _validate_timeout(self, timeout: float) -> float:
        if timeout <= 0:
            raise DeepSeekAdapterError(
                "DeepSeek adapter timeout must be positive",
                FailureClass.VALIDATION_ERROR,
            )
        return min(timeout, 30.0)

    def _validate_base_url(self) -> None:
        parsed = urllib_parse.urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DeepSeekAdapterError(
                "DeepSeek base_url must be HTTPS with a host",
                FailureClass.VALIDATION_ERROR,
            )

    def _build_payload(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        payload.update({k: v for k, v in kwargs.items() if k != "metadata"})
        return payload

    def _post_once(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._client or requests
        response = client.post(
            self.base_url,
            json=payload,
            headers=self._headers(),
            timeout=self._timeout,
        )
        status_code = getattr(response, "status_code", 200)
        if status_code != 200:
            raise DeepSeekAdapterError(
                f"DeepSeek API error: status {status_code}",
                FailureClass.EXECUTION_ERROR,
            )
        return cast(dict[str, Any], response.json())

    def _call_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        attempts = self.retry_attempts + 1
        for attempt in range(attempts):
            try:
                return self._post_once(payload)
            except DeepSeekAdapterError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt == self.retry_attempts:
                    raise self._wrap_failure(exc) from exc
        if last_exc is None:
            raise self._wrap_failure(
                RuntimeError("DeepSeek request failed without raising an exception")
            )
        raise self._wrap_failure(last_exc) from last_exc

    def _wrap_failure(self, exc: Exception) -> DeepSeekAdapterError:
        failure_class = (
            FailureClass.RESOURCE_EXHAUSTION
            if self._is_timeout_exception(exc)
            else FailureClass.EXECUTION_ERROR
        )
        return DeepSeekAdapterError(f"DeepSeek request failed: {exc!s}", failure_class)

    @staticmethod
    def _is_timeout_exception(exc: Exception) -> bool:
        if isinstance(exc, (socket.timeout, TimeoutError)):
            return True
        if isinstance(exc, urllib_error.URLError):
            reason = exc.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                return True
            if isinstance(reason, str) and "timed out" in reason.lower():
                return True
        return False

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        metadata = self._prepare_metadata(kwargs.get("metadata"))
        payload = self._build_payload(prompt, **kwargs)
        response = self._call_with_retries(payload)
        text = response["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            model=self.config.model_name,
            prompt_hash=prompt_hash(prompt),
            model_hash=prompt_hash(self.config.model_name),
            metadata={**metadata, "usage": response.get("usage", {})},
            confidence=float(kwargs.get("confidence", 0.8)),
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=False, retries=True)


class MockAdapter(BaseLLMAdapter):
    """Deterministic adapter for CI/testing fixtures."""

    def __init__(
        self,
        config: AdapterConfig,
        canned_response: str | None = None,
    ) -> None:
        super().__init__(config)
        self.canned_response = canned_response or "mock response"

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        metadata = self._prepare_metadata(kwargs.get("metadata"))
        text = self.canned_response.format(prompt=prompt)
        return LLMResponse(
            text=text,
            model=self.config.model_name,
            prompt_hash=prompt_hash(prompt),
            model_hash=prompt_hash(self.config.model_name),
            metadata=metadata,
            confidence=float(kwargs.get("confidence", 0.9)),
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=False, retries=False)


class LocalAdapter(BaseLLMAdapter):
    """Deterministic local LLM implementation without networking."""

    def __init__(
        self,
        config: AdapterConfig,
        response_generator: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(config)
        self._response_generator = response_generator or (
            lambda prompt: f"local::{prompt}"
        )

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        metadata = self._prepare_metadata(kwargs.get("metadata"))
        text = self._response_generator(prompt).strip()
        return LLMResponse(
            text=text,
            model=self.config.model_name,
            prompt_hash=prompt_hash(prompt),
            model_hash=prompt_hash(self.config.model_name),
            metadata=metadata,
            confidence=float(kwargs.get("confidence", 1.0)),
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=False, retries=False)
