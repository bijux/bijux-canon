"""Utility module for interacting with LLM backends asynchronously.

This module provides classes and utilities for interacting with various LLM backends,
supporting features like retry logic, batch processing, and telemetry integration.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import logging
import time
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientSession, ClientTimeout

from bijux_agent.utilities.logger_manager import (
    LoggerConfig,
    LoggerManager,
    MetricType,
)
from bijux_agent.utilities.prompt_hash import prompt_hash


@dataclass
class LLMResponse:
    """Represents a response from an LLM backend."""

    content: str
    metadata: dict[str, Any]
    error: str | None = None
    action_plan: list[str] | None = None


class LLMBackend:
    """Base class for LLM backends."""

    async def generate(
        self, prompt: str, max_tokens: int | None, session: ClientSession
    ) -> LLMResponse:
        """Generate a response from the LLM backend.

        Args:
            prompt: The input prompt for the LLM.
            max_tokens: Maximum number of tokens to generate.
            session: The aiohttp ClientSession for making requests.

        Returns:
            An LLMResponse object containing the generated content and metadata.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("Subclasses must implement the generate method")


class DeepSeekBackend(LLMBackend):
    """Backend for interacting with the DeepSeek API."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the DeepSeekBackend with configuration.

        Args:
            config: Configuration dictionary containing API settings.
        """
        self.api_key = config.get("api_key")
        self.model = config.get("model", "deepseek-chat")
        self.temperature = float(config.get("temperature", 0.7))
        self.endpoint = config.get(
            "endpoint", "https://api.deepseek.com/v1/chat/completions"
        )
        self.logger = logging.getLogger(__name__)  # Temporary logger for initialization

        if not self.api_key:
            self.logger.error("DeepSeek API key not provided")
            raise ValueError("DeepSeek API key not provided")

    async def generate(
        self, prompt: str, max_tokens: int | None, session: ClientSession
    ) -> LLMResponse:
        """Generate a response using the DeepSeek API.

        Args:
            prompt: The input prompt for the LLM.
            max_tokens: Maximum number of tokens to generate.
            session: The aiohttp ClientSession for making requests.

        Returns:
            An LLMResponse object containing the generated content and metadata.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with session.post(
                self.endpoint, json=payload, headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(
                        content="",
                        metadata={
                            "status": response.status,
                            "prompt_hash": prompt_hash(prompt),
                        },
                        error=f"DeepSeek API request failed: {error_text}",
                        action_plan=[
                            "Verify API key",
                            "Check endpoint URL",
                            "Retry after delay",
                        ],
                    )
                data = await response.json()
                content = data["choices"][0]["message"]["content"].strip()
                metadata = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "usage": data.get("usage", {}),
                }
                metadata["prompt_hash"] = prompt_hash(prompt)
                return LLMResponse(content=content, metadata=metadata)
        except ClientResponseError as e:
            return LLMResponse(
                content="",
                metadata={
                    "status": e.status,
                    "prompt_hash": prompt_hash(prompt),
                },
                error=f"HTTP error: {e!s}",
                action_plan=[
                    "Check network connectivity",
                    "Retry with exponential backoff",
                ],
            )
        except Exception as e:
            return LLMResponse(
                content="",
                metadata={"prompt_hash": prompt_hash(prompt)},
                error=f"Unexpected error: {e!s}",
                action_plan=["Review logs for details", "Retry the request"],
            )


class LLMUtils:
    """Enhanced utility class for interacting with various LLM backends asynchronously.

    Supports multiple providers, retry logic, batch processing, and comprehensive
    telemetry. Fully integrated with LoggerManager for structured, async, and
    telemetry-enabled logging.
    """

    def __init__(
        self,
        config: dict[str, Any],
        backend: str = "deepseek",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
        logger_name: str = "LLMUtils",
    ):
        """Initialize the LLMUtils with a specific backend and configuration.

        Args:
            config: Configuration dictionary containing LLM settings.
            backend: The LLM backend to use (e.g., "deepseek", "openai").
            max_retries: Maximum number of retry attempts for API calls.
            retry_delay: Base delay between retries (seconds).
            timeout: HTTP request timeout (seconds).
            logger_name: Name for the LoggerManager instance.
        """
        self.config = config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = ClientTimeout(total=timeout)
        self.backend_name = backend
        self._custom_backends: dict[str, LLMBackend] = {}

        # Initialize LoggerManager
        logger_config = LoggerConfig(
            log_dir=self.config.get("log_dir", "./logs"),
            log_level=self.config.get("log_level", "INFO"),
            log_file_name=self.config.get("log_file_name", "llm_utils.log"),
            max_file_size_mb=self.config.get("max_log_file_size_mb", 10),
            backup_count=self.config.get("log_backup_count", 3),
            structured_logging=self.config.get("structured_logging", True),
            async_logging=self.config.get("async_logging", True),
            telemetry_enabled=self.config.get("telemetry_enabled", True),
            histogram_buckets=self.config.get(
                "histogram_buckets", LoggerConfig.DEFAULT_HISTOGRAM_BUCKETS
            ),
        )
        self.logger_manager = LoggerManager(name=logger_name, config=logger_config)
        self.logger = self.logger_manager.get_logger()

        # Initialize backend
        self.backend = self._create_backend(backend)
        self.logger.info(
            "LLMUtils initialized",
            extra={
                "context": {
                    "backend": backend,
                    "max_retries": max_retries,
                    "retry_delay": retry_delay,
                    "timeout": timeout,
                }
            },
        )

    def _create_backend(self, backend: str) -> LLMBackend:
        """Create an LLM backend instance based on the specified provider."""
        if backend in self._custom_backends:
            return self._custom_backends[backend]

        if backend == "deepseek":
            backend_config = self.config.get("llms", {}).get("deepseek", {})
            return DeepSeekBackend(backend_config)
        else:
            raise ValueError(
                f"Unsupported LLM backend: {backend}. Register a custom backend "
                "or use a supported provider."
            )

    def register_custom_backend(self, backend_name: str, backend: LLMBackend) -> None:
        """Register a custom LLM backend.

        Args:
            backend_name: Name of the custom backend.
            backend: Instance of the custom LLM backend.
        """
        self._custom_backends[backend_name] = backend
        self.logger.info(
            f"Registered custom LLM backend: {backend_name}",
            extra={
                "context": {"stage": "backend_registration", "backend": backend_name}
            },
        )
        self.logger_manager.log_metric(
            "custom_backends_registered",
            1,
            MetricType.COUNTER,
            tags={"backend": backend_name},
        )

    async def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Generate a response using the configured LLM backend with retry logic.

        Args:
            prompt: The input prompt for the LLM.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The generated text response.

        Raises:
            Exception: If all retries fail or the response is invalid.
        """
        context_id = hashlib.sha256(prompt.encode()).hexdigest()
        with self.logger.context(agent="LLMUtils", context_id=context_id):
            self.logger.info(
                "Starting LLM generation",
                extra={
                    "context": {
                        "stage": "init",
                        "prompt_length": len(prompt),
                        "max_tokens": max_tokens,
                    }
                },
            )

        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    start_time = time.time()
                    response = await self.backend.generate(prompt, max_tokens, session)
                    duration = time.time() - start_time

                    self.logger_manager.log_metric(
                        "llm_request_duration",
                        duration,
                        MetricType.HISTOGRAM,
                        tags={"backend": self.backend_name, "attempt": str(attempt)},
                    )
                    self.logger_manager.log_metric(
                        "llm_requests",
                        1,
                        MetricType.COUNTER,
                        tags={"backend": self.backend_name, "status": "success"},
                    )

                    if response.error:
                        self.logger.warning(
                            f"LLM generation failed: {response.error}",
                            extra={
                                "context": {"attempt": attempt, "duration": duration}
                            },
                        )
                        self.logger_manager.log_metric(
                            "llm_request_errors",
                            1,
                            MetricType.COUNTER,
                            tags={
                                "backend": self.backend_name,
                                "attempt": str(attempt),
                            },
                        )
                        if attempt == self.max_retries:
                            raise Exception(f"All retries failed: {response.error}")
                        await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                        continue

                    self.logger.info(
                        "LLM generation completed",
                        extra={
                            "context": {
                                "stage": "completion",
                                "duration": duration,
                                "response_length": len(response.content),
                            }
                        },
                    )
                    return response.content

            except Exception as e:
                self.logger.error(
                    f"LLM generation failed on attempt {attempt}: {e!s}",
                    extra={"context": {"attempt": attempt}},
                )
                self.logger_manager.log_metric(
                    "llm_request_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"backend": self.backend_name, "attempt": str(attempt)},
                )
                if attempt == self.max_retries:
                    raise Exception(f"All retries failed: {e!s}") from e
                await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))

        raise Exception("Unexpected error: Retry loop exited without result")

    async def batch_generate(
        self, prompts: list[str], max_tokens: int | None = None
    ) -> list[str]:
        """Generate responses for a batch of prompts concurrently.

        Args:
            prompts: List of input prompts for the LLM.
            max_tokens: Maximum number of tokens to generate for each prompt.

        Returns:
            List of generated text responses.
        """
        context_id = hashlib.sha256("".join(prompts).encode()).hexdigest()
        with self.logger.context(agent="LLMUtils", context_id=context_id):
            self.logger.info(
                "Starting LLM batch generation",
                extra={
                    "context": {
                        "stage": "init",
                        "batch_size": len(prompts),
                        "max_tokens": max_tokens,
                    }
                },
            )

        tasks = [self.generate(prompt, max_tokens) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Batch generation failed for prompt {idx}: {result!s}"
                )
                responses.append("")
                self.logger_manager.log_metric(
                    "llm_batch_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"backend": self.backend_name, "prompt_idx": str(idx)},
                )
            else:
                responses.append(result)

        self.logger.info(
            "LLM batch generation completed",
            extra={
                "context": {
                    "stage": "completion",
                    "batch_size": len(prompts),
                    "successful": sum(1 for r in responses if r),
                }
            },
        )
        self.logger_manager.log_metric(
            "llm_batch_requests",
            len(prompts),
            MetricType.COUNTER,
            tags={"backend": self.backend_name},
        )
        return responses

    async def get_telemetry(self) -> dict[str, Any]:
        """Retrieve telemetry metrics for the LLMUtils instance.

        Returns:
            A dictionary of telemetry metrics.
        """
        return self.logger_manager.get_metrics()

    async def flush_logs(self) -> None:
        """Flush all log handlers."""
        self.logger_manager.flush()
        self.logger.debug("Logs flushed", extra={"context": {"stage": "log_flush"}})
        self.logger_manager.log_metric(
            "log_flush", 1, MetricType.COUNTER, tags={"stage": "log_flush"}
        )
