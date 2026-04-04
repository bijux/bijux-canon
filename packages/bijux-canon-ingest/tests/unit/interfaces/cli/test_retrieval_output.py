# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.interfaces.cli.retrieval_output import (
    render_answer_output,
    write_output,
)
from bijux_canon_ingest.retrieval.ports import Answer, Citation


class _FakeYamlModule:
    def safe_dump(
        self,
        data: object,
        *,
        sort_keys: bool = False,
        allow_unicode: bool = True,
    ) -> str:
        assert sort_keys is False
        assert allow_unicode is True
        return f"yaml:{data!r}"


def test_render_answer_output_uses_yaml_module() -> None:
    answer = Answer(
        text="alpha",
        citations=[Citation(doc_id="d1", chunk_id="c1", start=0, end=5, text="alpha")],
    )

    output = render_answer_output(
        answer,
        output_format="yaml",
        yaml_module=_FakeYamlModule(),
    )

    assert output.startswith("yaml:")


def test_write_output_appends_terminal_newline(tmp_path: Path) -> None:
    out_path = tmp_path / "answer.json"

    write_output(payload='{"answer":"alpha"}', out_path=out_path)

    assert out_path.read_text(encoding="utf-8").endswith("\n")
