# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Transport parity for persisted output-only answer evaluation."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from typing import cast
from unittest.mock import Mock

from fastapi.testclient import TestClient

from bijux_canon_reason.evaluation import SystemAnswerDisposition, SystemOutput
from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.operations import (
    PersistedAnswerEvaluationAdapter,
    RuntimeApplicationServicesV2,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import run_v2_command
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobManager
from bijux_canon_runtime.runtime.inspection import (
    RuntimeRunInspection,
    RuntimeRunInspector,
)


def _output() -> SystemOutput:
    return SystemOutput(
        output_id="system-output-1",
        case_id="case-1",
        runtime_run_id="run-1",
        runtime_attempt_id="attempt-1",
        answer="A citation-grounded answer.",
        disposition=SystemAnswerDisposition.answered,
        trace_identity_sha256="a" * 64,
    )


def test_application_service_binds_evaluation_to_selected_inspection() -> None:
    inspection = cast(RuntimeRunInspection, object())
    inspector = Mock(spec=RuntimeRunInspector)
    inspector.inspect.return_value = inspection
    adapter = Mock(spec=PersistedAnswerEvaluationAdapter)
    adapter.adapt.return_value = _output()
    service = RuntimeApplicationServicesV2(
        jobs=cast(DurableJobManager, object()),
        inspector=inspector,
        answer_evaluator=adapter,
    )

    output = service.evaluate_persisted_answer(
        case_id="case-1",
        question="What was reported?",
        run_id="run-1",
        attempt_id="attempt-1",
    )

    assert output == _output()
    inspector.inspect.assert_called_once_with("run-1", attempt_id="attempt-1")
    adapter.adapt.assert_called_once_with(
        case_id="case-1",
        question="What was reported?",
        inspection=inspection,
    )


def test_cli_and_http_return_the_same_output_only_record() -> None:
    services = Mock(spec=RuntimeApplicationServicesV2)
    services.evaluate_persisted_answer.return_value = _output()
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "v2",
            "evaluate-answer",
            "run-1",
            "--attempt-id",
            "attempt-1",
            "--case-id",
            "case-1",
            "--question",
            "What was reported?",
        ]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert run_v2_command(args, services=services) == 0
    cli_payload = json.loads(stdout.getvalue())

    response = TestClient(create_app(services)).post(
        "/api/v2/answer-evaluations",
        headers={"Bijux-API-Version": "v2"},
        json={
            "attempt_id": "attempt-1",
            "case_id": "case-1",
            "question": "What was reported?",
            "run_id": "run-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == cli_payload == _output().model_dump(mode="json")
