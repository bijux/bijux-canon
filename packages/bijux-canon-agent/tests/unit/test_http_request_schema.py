from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest
import yaml

from bijux_canon_agent.api.v1.schemas import RunRequestV1

REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("agents", [None, [], ["file_reader", "stage_runner"]])
def test_agent_selection_matches_the_published_nullable_contract(
    agents: object,
) -> None:
    schema = yaml.safe_load(
        (REPO_ROOT / "apis/bijux-canon-agent/v1/schema.yaml").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(
        {**schema, "$ref": "#/components/schemas/RunRequestV1"}
    )
    payload = {"text": "source", "task_goal": "summarize", "config": {"agents": agents}}
    validator.validate(payload)
    assert RunRequestV1.model_validate(payload).config is not None


@pytest.mark.parametrize("agents", [True, "file_reader", ["unknown"]])
def test_agent_selection_rejects_noncontract_values(agents: object) -> None:
    payload = {"text": "source", "task_goal": "summarize", "config": {"agents": agents}}
    with pytest.raises(ValidationError):
        RunRequestV1.model_validate(payload)
