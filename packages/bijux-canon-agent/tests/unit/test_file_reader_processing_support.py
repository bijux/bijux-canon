from __future__ import annotations

from pathlib import Path

from bijux_canon_agent.agents.file_reader.capabilities.processing_support import (
    enrich_read_result,
    validate_read_target,
)
import pytest


async def _audit_stub(path: str | Path) -> dict[str, object]:
    return {"file_name": Path(path).name, "file_size_bytes": 10}


@pytest.mark.asyncio
async def test_validate_read_target_rejects_missing_file(tmp_path: Path) -> None:
    result = await validate_read_target(
        tmp_path / "missing.txt",
        max_file_bytes=10,
        create_file_audit=_audit_stub,
    )

    assert result == {
        "error": f"File not found: {tmp_path / 'missing.txt'}",
        "action_plan": ["Verify the file path and ensure the file exists"],
    }


@pytest.mark.asyncio
async def test_validate_read_target_rejects_large_file(tmp_path: Path) -> None:
    path = tmp_path / "large.txt"
    path.write_text("01234567890", encoding="utf-8")

    result = await validate_read_target(
        path,
        max_file_bytes=5,
        create_file_audit=_audit_stub,
    )

    assert result is not None
    assert result["error"] == "File too large: 11 bytes (limit: 5)"
    assert result["file_info"] == {"file_name": "large.txt", "file_size_bytes": 10}


def test_enrich_read_result_adds_processing_metadata(tmp_path: Path) -> None:
    result = enrich_read_result(
        {"text": "# Title\nbody"},
        file_path=tmp_path / "note.md",
        extension=".md",
        file_type="md",
        processing_method="text_file",
        processing_time=0.3456,
        max_pdf_pages=100,
        max_file_bytes=1000,
        chunk_size=64,
        ocr_enabled=False,
        text_extensions={".md"},
        image_extensions={".png"},
        yaml_extensions={".yaml"},
        xml_extensions={".xml"},
        docx_extensions={".docx"},
    )

    assert result["processing_profile"] == {
        "duration_seconds": 0.346,
        "file_extension": ".md",
        "processing_method": "text_file",
    }
    assert result["structure_preview"]["format"] == "md"
    assert result["audit_trail"]["format"] == "md"
