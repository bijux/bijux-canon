from __future__ import annotations

import os

import pytest
import requests

from bijux_agent.config.env import KEY_REGISTRY, APIKeySpec, load_environment

RUN_LIVE_KEY_TESTS = os.getenv("RUN_LIVE_KEY_TESTS") == "1"
ENDPOINTS = {
    "OpenAI": "https://api.openai.com/v1/models",
    "Anthropic": "https://api.anthropic.com/v1/models",
    "HuggingFace": "https://api-inference.huggingface.co/models",
    "Deepseek": "https://api.deepseek.com/v1/models",
}


@pytest.mark.parametrize("spec", KEY_REGISTRY)
@pytest.mark.skipif(
    not RUN_LIVE_KEY_TESTS,
    reason="Live key validation disabled; set RUN_LIVE_KEY_TESTS=1 to enable",
)
@pytest.mark.integration
def test_live_api_key_responses(spec: APIKeySpec) -> None:
    load_environment()
    env_value = os.getenv(spec.env_var)
    if not env_value:
        pytest.skip(f"{spec.env_var} not configured for this environment")

    endpoint = ENDPOINTS.get(spec.provider)
    if not endpoint:
        pytest.skip(f"No endpoint defined for provider {spec.provider}")

    response = requests.get(
        endpoint,
        headers={"Authorization": f"Bearer {env_value}"},
        timeout=20,
    )
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("application/json")
