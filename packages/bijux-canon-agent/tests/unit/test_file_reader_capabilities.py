from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_agent.agents.file_reader.capabilities.binary import BinaryExtractor
from bijux_canon_agent.agents.file_reader.capabilities.dispatch import (
    ExtractionHandlers,
    FileExtractionDispatcher,
)
from bijux_canon_agent.agents.file_reader.capabilities.structure_preview import (
    analyze_json_structure,
    create_structure_preview,
)
from bijux_canon_agent.agents.file_reader.capabilities.structured import (
    HAS_PANDAS,
    StructuredExtractor,
)
from bijux_canon_agent.agents.file_reader.capabilities.text import TextExtractor
import pytest


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


async def _route_stub(path: str | Path) -> dict[str, str]:
    return {"path": str(path)}


@pytest.fixture
def extraction_handlers() -> ExtractionHandlers:
    return ExtractionHandlers(
        pdf=_route_stub,
        text=_route_stub,
        json=_route_stub,
        csv=_route_stub,
        yaml=_route_stub,
        xml=_route_stub,
        docx=_route_stub,
        image=_route_stub,
        unknown=_route_stub,
    )


def test_dispatcher_routes_text_formats(
    extraction_handlers: ExtractionHandlers,
) -> None:
    dispatcher = FileExtractionDispatcher(
        text_extensions={".txt", ".md"},
        image_extensions={".png"},
        yaml_extensions={".yaml", ".yml"},
        xml_extensions={".xml"},
        docx_extensions={".docx"},
        ocr_enabled=False,
    )

    plan = dispatcher.plan_for(
        Path("notes.md"),
        custom_extractors={},
        handlers=extraction_handlers,
    )

    assert plan.processing_method == "text_file"
    assert plan.extract is extraction_handlers.text


def test_dispatcher_routes_images_without_ocr_to_unknown_handler(
    extraction_handlers: ExtractionHandlers,
) -> None:
    dispatcher = FileExtractionDispatcher(
        text_extensions={".txt"},
        image_extensions={".png"},
        yaml_extensions={".yaml", ".yml"},
        xml_extensions={".xml"},
        docx_extensions={".docx"},
        ocr_enabled=False,
    )

    plan = dispatcher.plan_for(
        Path("image.png"),
        custom_extractors={},
        handlers=extraction_handlers,
    )

    assert plan.processing_method == "binary_handler"
    assert plan.extract is extraction_handlers.unknown


def test_dispatcher_routes_custom_extractors(
    extraction_handlers: ExtractionHandlers,
) -> None:
    dispatcher = FileExtractionDispatcher(
        text_extensions={".txt"},
        image_extensions={".png"},
        yaml_extensions={".yaml", ".yml"},
        xml_extensions={".xml"},
        docx_extensions={".docx"},
        ocr_enabled=True,
    )

    async def custom_reader(path: str) -> dict[str, str]:
        return {"custom_path": path}

    plan = dispatcher.plan_for(
        Path("asset.custom"),
        custom_extractors={"custom": custom_reader},
        handlers=extraction_handlers,
    )

    assert plan.processing_method == "custom_custom_reader"


def test_create_structure_preview_handles_markdown_text() -> None:
    preview = create_structure_preview(
        ".md",
        {"text": "# Title\nbody"},
        text_extensions={".md"},
        image_extensions={".png"},
        yaml_extensions={".yaml", ".yml"},
        xml_extensions={".xml"},
        docx_extensions={".docx"},
    )

    assert preview["format"] == "md"
    assert preview["section_count"] == 1


def test_analyze_json_structure_limits_depth() -> None:
    structure = analyze_json_structure({"alpha": {"beta": {"gamma": 1}}}, max_depth=1)

    assert structure["type"] == "object"
    assert structure["sample_values"]["alpha"]["truncated"] is True
