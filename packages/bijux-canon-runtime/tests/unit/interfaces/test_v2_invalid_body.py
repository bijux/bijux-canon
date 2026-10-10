from fastapi.testclient import TestClient
import pytest

from bijux_canon_runtime.api.v2.app import create_app
from bijux_canon_runtime.api.v2.schemas import ProblemDetail


@pytest.mark.parametrize("body", [b"\xff", b"{"])
def test_invalid_json_body_uses_the_declared_problem_contract(body: bytes) -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v2/research",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Bijux-API-Version": "v2",
                "X-Correlation-ID": "invalid-body",
            },
        )
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    problem = ProblemDetail.model_validate(response.json())
    assert problem.code.value == "invalid-request"
    assert problem.correlation_id == "invalid-body"
