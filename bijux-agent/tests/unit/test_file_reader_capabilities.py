from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_agent.agents.file_reader.capabilities.binary import BinaryExtractor
from bijux_agent.agents.file_reader.capabilities.structured import (
    HAS_PANDAS,
    StructuredExtractor,
)
from bijux_agent.agents.file_reader.capabilities.text import TextExtractor


async def _audit_stub(path: str | Path) -> dict[str, str]:
    return {"file_name": Path(path).name}


def _normalize(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.asyncio
async def test_text_extractor_reads_text(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello  world", encoding="utf-8")
    extractor = TextExtractor(create_file_audit=_audit_stub, normalize_text=_normalize)
    result = await extractor.extract_text_file(path)
    assert result["text"] == "hello world"


@pytest.mark.asyncio
async def test_structured_extractor_parses_json(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"alpha": 1}), encoding="utf-8")
    extractor = StructuredExtractor(create_file_audit=_audit_stub)
    result = await extractor.extract_json_file(path)
    assert result["parsed"] == {"alpha": 1}


@pytest.mark.asyncio
async def test_structured_extractor_handles_csv_dependency(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    extractor = StructuredExtractor(create_file_audit=_audit_stub)
    result = await extractor.extract_csv_file(path)
    if HAS_PANDAS:
        assert "columns" in result
    else:
        assert "error" in result


@pytest.mark.asyncio
async def test_binary_extractor_handles_missing_ocr(tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    extractor = BinaryExtractor(
        create_file_audit=_audit_stub,
        normalize_text=_normalize,
        max_pdf_pages=1,
        ocr_enabled=True,
    )
    result = await extractor.extract_image_with_ocr(path)
    assert "file_info" in result
