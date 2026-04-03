"""Universal file reader module for Bijux Agent.

This module provides the UniversalFileReader class, a robust utility for
asynchronously extracting content from multiple file formats, including PDFs,
text files, JSON, CSV, YAML, XML, DOCX, and images with OCR support.
It includes detailed metadata extraction and structural previews,
designed to be used by FileReaderAgent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import hashlib
from pathlib import Path
import time
from typing import Any, ClassVar
import unicodedata

from .binary import (
    HAS_FITZ,
    HAS_PDFMINER,
    HAS_PIL,
    HAS_PYPDF2,
    HAS_PYTESSERACT,
    BinaryExtractor,
)
from .binary import (
    IMAGE_EXTENSIONS as BINARY_IMAGE_EXTENSIONS,
)
from .structured import (
    HAS_PANDAS,
    HAS_XML,
    HAS_YAML,
    StructuredExtractor,
)
from .structured import (
    XML_EXTENSIONS as STRUCTURED_XML_EXTENSIONS,
)
from .structured import (
    YAML_EXTENSIONS as STRUCTURED_YAML_EXTENSIONS,
)
from .text import (
    DOCX_EXTENSIONS as TEXT_DOCX_EXTENSIONS,
)
from .text import (
    HAS_DOCX,
    TextExtractor,
)
from .text import (
    TEXT_EXTENSIONS as TEXT_FILE_EXTENSIONS,
)


class FileExtractionError(Exception):
    """Custom exception for file extraction errors."""

    pass


class UniversalFileReader:
    """A robust, async-compatible utility class for reading multiple file formats.

    Provides detailed metadata and structural previews.
    Designed to be used by FileReaderAgent, which handles logging and telemetry.
    """

    DEFAULT_MAX_PDF_PAGES = 1000
    DEFAULT_MAX_FILE_BYTES = 100 * 1024 * 1024  # 100 MB
    DEFAULT_CHUNK_SIZE = 65536  # 64 KB

    # Supported file extensions
    TEXT_EXTENSIONS: ClassVar[set[str]] = set(TEXT_FILE_EXTENSIONS)
    IMAGE_EXTENSIONS: ClassVar[set[str]] = set(BINARY_IMAGE_EXTENSIONS)
    YAML_EXTENSIONS: ClassVar[set[str]] = set(STRUCTURED_YAML_EXTENSIONS)
    XML_EXTENSIONS: ClassVar[set[str]] = set(STRUCTURED_XML_EXTENSIONS)
    DOCX_EXTENSIONS: ClassVar[set[str]] = set(TEXT_DOCX_EXTENSIONS)

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the UniversalFileReader with configuration.

        Args:
            config: Configuration dictionary containing settings like max_pdf_pages,
                    max_file_bytes, etc.
        """
        self.config = config
        self.max_pdf_pages = self._get_config_int(
            "max_pdf_pages", self.DEFAULT_MAX_PDF_PAGES
        )
        self.max_file_bytes = self._get_config_int(
            "max_file_bytes", self.DEFAULT_MAX_FILE_BYTES
        )
        self.chunk_size = self._get_config_int("chunk_size", self.DEFAULT_CHUNK_SIZE)
        self.ocr_enabled = self._get_config_bool("ocr_enabled", False)
        self._custom_extractors: dict[
            str, Callable[[str], Awaitable[dict[str, Any]]]
        ] = {}
        self._text_extractor = TextExtractor(
            create_file_audit=self._create_file_audit,
            normalize_text=self._normalize_text,
        )
        self._structured_extractor = StructuredExtractor(
            create_file_audit=self._create_file_audit,
        )
        self._binary_extractor = BinaryExtractor(
            create_file_audit=self._create_file_audit,
            normalize_text=self._normalize_text,
            max_pdf_pages=self.max_pdf_pages,
            ocr_enabled=self.ocr_enabled,
        )

    def _get_config_int(self, key: str, default: int) -> int:
        """Safely get integer config value.

        Args:
            key: Configuration key.
            default: Default value if key is missing or invalid.

        Returns:
            Integer value.
        """
        try:
            return int(self.config.get(key, default))
        except (ValueError, TypeError):
            return default

    def _get_config_bool(self, key: str, default: bool) -> bool:
        """Safely get boolean config value.

        Args:
            key: Configuration key.
            default: Default value if key is missing or invalid.

        Returns:
            Boolean value.
        """
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value) if value is not None else default

    async def _compute_file_hash(self, path: str | Path) -> str:
        """Compute SHA256 hash of a file asynchronously.

        Args:
            path: Path to the file.

        Returns:
            Hexadecimal hash string.
        """
        hash_obj = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
                    # Yield control to the event loop for large files
                    await asyncio.sleep(0)
            return hash_obj.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text to normalize.

        Returns:
            Normalized text.
        """
        if not text:
            return ""

        # Normalize unicode characters
        normalized = unicodedata.normalize("NFKC", text)

        # Clean up whitespace
        return " ".join(normalized.split())

    async def _create_file_audit(self, file_path: str | Path) -> dict[str, Any]:
        """Create audit information for a file asynchronously.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary containing file metadata.
        """
        path_obj = Path(file_path)
        try:
            stat = path_obj.stat()
            file_hash = await self._compute_file_hash(path_obj)
            return {
                "file_name": path_obj.name,
                "file_size_bytes": stat.st_size,
                "file_hash": file_hash,
                "last_modified": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)
                ),
            }
        except Exception as e:
            return {
                "file_name": path_obj.name,
                "file_size_bytes": 0,
                "file_hash": "",
                "error": str(e),
            }

    async def _extract_pdf_content(self, file_path: str | Path) -> dict[str, Any]:
        """Extract content from PDF files using multiple strategies asynchronously."""
        return await self._binary_extractor.extract_pdf_content(file_path)

    async def _extract_text_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract content from text files asynchronously."""
        return await self._text_extractor.extract_text_file(file_path)

    async def _extract_json_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract and parse JSON files asynchronously."""
        return await self._structured_extractor.extract_json_file(file_path)

    async def _extract_csv_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract and analyze CSV files asynchronously."""
        return await self._structured_extractor.extract_csv_file(file_path)

    async def _extract_yaml_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract and parse YAML files asynchronously."""
        return await self._structured_extractor.extract_yaml_file(file_path)

    async def _extract_xml_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract and parse XML files asynchronously."""
        return await self._structured_extractor.extract_xml_file(file_path)

    async def _extract_docx_file(self, file_path: str | Path) -> dict[str, Any]:
        """Extract content from DOCX files asynchronously."""
        return await self._text_extractor.extract_docx_file(file_path)

    async def _extract_image_with_ocr(self, file_path: str | Path) -> dict[str, Any]:
        """Extract text from images using OCR asynchronously."""
        return await self._binary_extractor.extract_image_with_ocr(file_path)

    async def _handle_unknown_file(self, file_path: str | Path) -> dict[str, Any]:
        """Handle files with unknown or unsupported formats asynchronously.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with error message and file info.
        """
        file_info = await self._create_file_audit(file_path)

        # Try to detect if it's text-based
        try:
            with open(file_path, "rb") as f:
                sample = f.read(2048)

            # Simple heuristic: if most bytes are printable ASCII, treat as text
            if (
                sample
                and sum(b < 128 and (b >= 32 or b in [9, 10, 13]) for b in sample)
                / len(sample)
                > 0.8
            ):
                return await self._extract_text_file(file_path)
            else:
                return {
                    "error": "Binary or unknown file type - not processed",
                    "file_info": file_info,
                    "warnings": ["File appears to be binary and cannot be processed"],
                    "action_plan": [
                        "Convert file to a supported format or register a "
                        "custom extractor"
                    ],
                }
        except Exception as e:
            return {
                "error": f"Could not analyze unknown file type: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file integrity or register a custom extractor"],
            }

    def _create_structure_preview(
        self, extension: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a structural preview of the file content.

        Args:
            extension: File extension.
            result: Extraction result.

        Returns:
            Dictionary containing structural information.
        """
        ext = extension.lower()
        preview: dict[str, Any] = {"format": ext.lstrip(".")}

        if ext in self.TEXT_EXTENSIONS and "text" in result:
            lines = result["text"].splitlines()
            # Basic section detection (e.g., lines starting with # for markdown)
            sections = [
                {"title": line, "depth": line.count("#")}
                for line in lines
                if line.startswith("#")
            ]
            preview.update(
                {
                    "line_count": len(lines),
                    "character_count": len(result["text"]),
                    "sample_lines": lines[:5],
                    "sections": sections[:10],
                    "section_count": len(sections),
                    "tables": [],
                    "images": [],
                }
            )
        elif ext == ".json" and "parsed" in result:
            preview.update(
                {
                    "data_type": result.get("data_type", "unknown"),
                    "structure": self._analyze_json_structure(result["parsed"]),
                    "sections": [],
                    "tables": [],
                    "images": [],
                }
            )
        elif ext == ".csv" and "columns" in result:
            preview.update(
                {
                    "columns": result["columns"],
                    "row_count": result.get("n_rows", 0),
                    "column_count": result.get("n_columns", 0),
                    "sections": [],
                    "tables": [
                        {
                            "columns": result["columns"],
                            "sample_rows": result.get("sample_data", []),
                        }
                    ],
                    "images": [],
                }
            )
        elif ext in self.YAML_EXTENSIONS and "parsed" in result:
            preview.update(
                {
                    "data_type": result.get("data_type", "unknown"),
                    "structure": self._analyze_json_structure(result["parsed"]),
                    "sections": [],
                    "tables": [],
                    "images": [],
                }
            )
        elif ext in self.XML_EXTENSIONS and "parsed" in result:
            preview.update(
                {
                    "root_tag": result.get("root_tag"),
                    "structure": self._analyze_json_structure(result["parsed"]),
                    "sections": [],
                    "tables": [],
                    "images": [],
                }
            )
        elif ext in self.DOCX_EXTENSIONS and "text" in result:
            lines = result["text"].splitlines()
            preview.update(
                {
                    "line_count": len(lines),
                    "character_count": len(result["text"]),
                    "sample_lines": lines[:5],
                    "paragraph_count": result.get("paragraph_count", 0),
                    "sections": [],
                    "tables": [],
                    "images": [],
                }
            )
        elif ext == ".pdf":
            preview.update(
                {
                    "page_count": result.get("page_count"),
                    "ocr_used": result.get("ocr_used", False),
                    "has_text": bool(result.get("text", "").strip()),
                    "sections": [],
                    "tables": [],
                    "images": [],
                }
            )
        elif ext in self.IMAGE_EXTENSIONS:
            if "image_size" in result:
                preview.update(
                    {
                        "image_size": result["image_size"],
                        "image_mode": result.get("image_mode"),
                        "has_text": bool(result.get("text", "").strip()),
                        "sections": [],
                        "tables": [],
                        "images": [
                            {
                                "size": result["image_size"],
                                "mode": result.get("image_mode"),
                            }
                        ],
                    }
                )

        return preview

    @staticmethod
    def _analyze_json_structure(data: Any, max_depth: int = 3) -> dict[str, Any]:
        """Analyze the structure of JSON data.

        Args:
            data: JSON data to analyze.
            max_depth: Maximum depth to traverse.

        Returns:
            Dictionary describing the structure.
        """
        if max_depth <= 0:
            return {"type": type(data).__name__, "truncated": True}

        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys())[:10],  # Limit to first 10 keys
                "key_count": len(data),
                "sample_values": {
                    key: UniversalFileReader._analyze_json_structure(
                        value, max_depth - 1
                    )
                    for key, value in list(data.items())[:3]
                },
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "sample_items": [
                    UniversalFileReader._analyze_json_structure(item, max_depth - 1)
                    for item in data[:3]
                ],
            }
        else:
            return {"type": type(data).__name__, "value": str(data)[:100]}

    async def read_file(self, file_path: str | Path) -> dict[str, Any]:
        """Main method to process a file and extract its content asynchronously.

        Args:
            file_path: Path to the file to read.

        Returns:
            Dictionary containing extraction results, metadata, and audit information.
        """
        file_path = Path(file_path)

        # Validate file exists
        if not file_path.exists():
            return {
                "error": f"File not found: {file_path}",
                "action_plan": ["Verify the file path and ensure the file exists"],
            }

        if not file_path.is_file():
            return {
                "error": f"Path is not a file: {file_path}",
                "action_plan": ["Provide a path to a file, not a directory"],
            }

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_bytes:
                file_info = await self._create_file_audit(file_path)
                return {
                    "error": (
                        f"File too large: {file_size} bytes "
                        f"(limit: {self.max_file_bytes})"
                    ),
                    "file_info": file_info,
                    "action_plan": [
                        "Reduce file size or increase max_file_bytes limit"
                    ],
                }
        except Exception as e:
            return {
                "error": f"Could not access file: {e}",
                "action_plan": ["Verify file permissions and accessibility"],
            }

        # Start processing
        start_time = time.time()
        extension = file_path.suffix.lower()
        file_type = extension.lstrip(".")

        # Determine extraction method based on file extension
        try:
            # Check for custom extractor
            custom_extractor = self._custom_extractors.get(file_type)
            if custom_extractor:
                result = await custom_extractor(str(file_path))
            elif extension == ".pdf":
                result = await self._extract_pdf_content(file_path)
            elif extension in self.TEXT_EXTENSIONS:
                result = await self._extract_text_file(file_path)
            elif extension == ".json":
                result = await self._extract_json_file(file_path)
            elif extension == ".csv":
                result = await self._extract_csv_file(file_path)
            elif extension in self.YAML_EXTENSIONS:
                result = await self._extract_yaml_file(file_path)
            elif extension in self.XML_EXTENSIONS:
                result = await self._extract_xml_file(file_path)
            elif extension in self.DOCX_EXTENSIONS:
                result = await self._extract_docx_file(file_path)
            elif extension in self.IMAGE_EXTENSIONS:
                if self.ocr_enabled:
                    result = await self._extract_image_with_ocr(file_path)
                else:
                    result = await self._handle_unknown_file(file_path)
            else:
                result = await self._handle_unknown_file(file_path)
        except Exception as e:
            result = {
                "error": f"Unexpected error during processing: {e}",
                "file_info": await self._create_file_audit(file_path),
                "action_plan": [
                    "Verify file integrity and format, or register a custom extractor"
                ],
            }

        # Add metadata
        processing_time = time.time() - start_time

        result.update(
            {
                "processing_profile": {
                    "duration_seconds": round(processing_time, 3),
                    "file_extension": extension,
                    "processing_method": self._get_processing_method(
                        extension, custom_extractor
                    ),
                },
                "structure_preview": self._create_structure_preview(extension, result),
                "audit_trail": {
                    "file_path": str(file_path),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "format": file_type,
                    "agent_config": {
                        "max_pdf_pages": self.max_pdf_pages,
                        "max_file_bytes": self.max_file_bytes,
                        "chunk_size": self.chunk_size,
                        "ocr_enabled": self.ocr_enabled,
                    },
                },
            }
        )

        return result

    def _get_processing_method(
        self, extension: str, custom_extractor: Callable | None
    ) -> str:
        """Get the processing method used for a given file extension.

        Args:
            extension: File extension.
            custom_extractor: Custom extractor function, if any.

        Returns:
            Name of the processing method.
        """
        if custom_extractor:
            return f"custom_{custom_extractor.__name__}"

        method_map = {
            ".pdf": "pdf_extraction",
            ".txt": "text_file",
            ".md": "text_file",
            ".rst": "text_file",
            ".log": "text_file",
            ".json": "json_parser",
            ".csv": "csv_analyzer",
            ".yaml": "yaml_parser",
            ".yml": "yaml_parser",
            ".xml": "xml_parser",
            ".docx": "docx_parser",
        }

        if extension in self.IMAGE_EXTENSIONS:
            return "ocr_extraction" if self.ocr_enabled else "binary_handler"

        return method_map.get(extension, "unknown_file_handler")

    def register_custom_extractor(
        self, file_type: str, extractor: Callable[[str], Awaitable[dict[str, Any]]]
    ) -> None:
        """Register a custom file extractor for a specific file type.

        Args:
            file_type: File type/extension (e.g., 'pdf', '.pdf').
            extractor: Async function to extract content from the file.
        """
        file_type = file_type.lstrip(".").lower()
        self._custom_extractors[file_type] = extractor

    def get_supported_formats(self) -> dict[str, Any]:
        """Get information about supported file formats.

        Returns:
            Dictionary categorizing supported file formats and dependencies.
        """
        return {
            "text_formats": list(self.TEXT_EXTENSIONS),
            "structured_formats": [
                ".json",
                ".csv",
                *self.YAML_EXTENSIONS,
                *self.XML_EXTENSIONS,
            ],
            "document_formats": [".pdf", *self.DOCX_EXTENSIONS],
            "image_formats": list(self.IMAGE_EXTENSIONS) if self.ocr_enabled else [],
            "custom_formats": list(self._custom_extractors.keys()),
            "dependencies": {
                "pandas": HAS_PANDAS,
                "yaml": HAS_YAML,
                "pdfminer": HAS_PDFMINER,
                "PyPDF2": HAS_PYPDF2,
                "pytesseract": HAS_PYTESSERACT,
                "PIL": HAS_PIL,
                "fitz": HAS_FITZ,
                "xml.etree.ElementTree": HAS_XML,
                "python-docx": HAS_DOCX,
            },
        }
