"""Text extraction capability for the universal file reader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

docx: ModuleType | None = None
try:
    import docx as _docx

    docx = _docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def _require_dependency(module: ModuleType | None, name: str) -> ModuleType:
    if module is None:
        raise RuntimeError(f"{name} dependency is required but not installed")
    return module


TEXT_EXTENSIONS: set[str] = {".txt", ".md", ".rst", ".log"}
DOCX_EXTENSIONS: set[str] = {".docx"}


class TextExtractor:
    """Capability module for text and document extraction."""

    def __init__(
        self,
        *,
        create_file_audit: Callable[[str | Path], Any],
        normalize_text: Callable[[str], str],
    ) -> None:
        self._create_file_audit = create_file_audit
        self._normalize_text = normalize_text

    async def extract_text_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    text = f.read()
                return {
                    "text": self._normalize_text(text),
                    "encoding_used": encoding,
                    "warnings": [],
                    "file_info": file_info,
                }
            except UnicodeDecodeError:
                continue
            except Exception as e:
                return {
                    "error": f"Failed to read text file: {e}",
                    "file_info": file_info,
                    "action_plan": [
                        "Verify file encoding or convert to a supported encoding"
                    ],
                }

        return {
            "error": "Could not decode file with any supported encoding",
            "file_info": file_info,
            "action_plan": [
                "Convert file to UTF-8 encoding or specify correct encoding"
            ],
        }

    async def extract_docx_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        if not HAS_DOCX:
            return {
                "error": "python-docx is required for DOCX processing but not installed",
                "file_info": file_info,
                "action_plan": ["Install python-docx to enable DOCX processing"],
            }

        try:
            loop = asyncio.get_running_loop()
            _require_dependency(docx, "python-docx")
            doc = await loop.run_in_executor(None, lambda: docx.Document(file_path))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n".join(paragraphs)
            return {
                "text": self._normalize_text(text),
                "paragraph_count": len(paragraphs),
                "file_info": file_info,
            }
        except Exception as e:
            return {
                "error": f"DOCX processing failed: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file is a valid DOCX file"],
            }
