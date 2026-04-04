"""Dispatch helpers for universal file reading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class PathExtractor(Protocol):
    """Async extractor that accepts a filesystem path."""

    async def __call__(self, file_path: str | Path) -> dict[str, Any]: ...


class CustomExtractor(Protocol):
    """Async extractor registered for a custom extension."""

    async def __call__(self, file_path: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ExtractionHandlers:
    """Concrete extraction handlers available to the dispatcher."""

    pdf: PathExtractor
    text: PathExtractor
    json: PathExtractor
    csv: PathExtractor
    yaml: PathExtractor
    xml: PathExtractor
    docx: PathExtractor
    image: PathExtractor
    unknown: PathExtractor


@dataclass(frozen=True)
class ExtractionPlan:
    """Resolved extraction route for a file path."""

    processing_method: str
    uses_custom_extractor: bool
    extract: PathExtractor


class FileExtractionDispatcher:
    """Resolve extraction routes for supported file formats."""

    def __init__(
        self,
        *,
        text_extensions: set[str],
        image_extensions: set[str],
        yaml_extensions: set[str],
        xml_extensions: set[str],
        docx_extensions: set[str],
        ocr_enabled: bool,
    ) -> None:
        self._text_extensions = text_extensions
        self._image_extensions = image_extensions
        self._yaml_extensions = yaml_extensions
        self._xml_extensions = xml_extensions
        self._docx_extensions = docx_extensions
        self._ocr_enabled = ocr_enabled

    def plan_for(
        self,
        file_path: Path,
        *,
        custom_extractors: dict[str, CustomExtractor],
        handlers: ExtractionHandlers,
    ) -> ExtractionPlan:
        """Return the extraction plan for a file."""
        extension = file_path.suffix.lower()
        file_type = extension.lstrip(".")
        custom_extractor = custom_extractors.get(file_type)
        if custom_extractor is not None:
            return ExtractionPlan(
                processing_method=f"custom_{custom_extractor.__name__}",
                uses_custom_extractor=True,
                extract=self._wrap_custom_extractor(custom_extractor),
            )

        if extension == ".pdf":
            return ExtractionPlan("pdf_extraction", False, handlers.pdf)
        if extension in self._text_extensions:
            return ExtractionPlan("text_file", False, handlers.text)
        if extension == ".json":
            return ExtractionPlan("json_parser", False, handlers.json)
        if extension == ".csv":
            return ExtractionPlan("csv_analyzer", False, handlers.csv)
        if extension in self._yaml_extensions:
            return ExtractionPlan("yaml_parser", False, handlers.yaml)
        if extension in self._xml_extensions:
            return ExtractionPlan("xml_parser", False, handlers.xml)
        if extension in self._docx_extensions:
            return ExtractionPlan("docx_parser", False, handlers.docx)
        if extension in self._image_extensions:
            if self._ocr_enabled:
                return ExtractionPlan("ocr_extraction", False, handlers.image)
            return ExtractionPlan("binary_handler", False, handlers.unknown)
        return ExtractionPlan("unknown_file_handler", False, handlers.unknown)

    @staticmethod
    def _wrap_custom_extractor(custom_extractor: CustomExtractor) -> PathExtractor:
        async def extract(file_path: str | Path) -> dict[str, Any]:
            return await custom_extractor(str(file_path))

        return extract
