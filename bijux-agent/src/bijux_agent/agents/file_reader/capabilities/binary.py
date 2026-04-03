"""Binary extraction capability for the universal file reader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

pdfminer: ModuleType | None = None
PyPDF2: ModuleType | None = None
pytesseract: ModuleType | None = None
Image: ModuleType | None = None
fitz: ModuleType | None = None

try:
    import pdfminer.high_level
    import pdfminer.pdfparser

    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

try:
    import PyPDF2 as _PyPDF2

    PyPDF2 = _PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pytesseract as _pytesseract

    pytesseract = _pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    from PIL import Image as _Image

    Image = _Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fitz as _fitz  # PyMuPDF

    fitz = _fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def _require_dependency(module: ModuleType | None, name: str) -> ModuleType:
    if module is None:
        raise RuntimeError(f"{name} dependency is required but not installed")
    return module


IMAGE_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
}


class BinaryExtractor:
    """Capability module for binary (PDF/image) extraction."""

    def __init__(
        self,
        *,
        create_file_audit: Callable[[str | Path], Any],
        normalize_text: Callable[[str], str],
        max_pdf_pages: int,
        ocr_enabled: bool,
    ) -> None:
        self._create_file_audit = create_file_audit
        self._normalize_text = normalize_text
        self.max_pdf_pages = max_pdf_pages
        self.ocr_enabled = ocr_enabled

    async def extract_pdf_content(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)
        warnings: list[str] = []
        text = ""
        page_count: int | None = None
        ocr_used = False

        if HAS_PDFMINER and not text.strip():
            try:
                loop = asyncio.get_running_loop()
                _require_dependency(pdfminer, "pdfminer")
                text = await loop.run_in_executor(
                    None, lambda: pdfminer.high_level.extract_text(str(file_path))
                )
            except Exception as e:
                warnings.append(f"pdfminer extraction failed: {e}")

        if HAS_PYPDF2 and not text.strip():
            try:
                with open(file_path, "rb") as file:
                    _require_dependency(PyPDF2, "PyPDF2")
                    reader = PyPDF2.PdfReader(file)
                    page_count = len(reader.pages)
                    pages_to_process = min(self.max_pdf_pages, page_count)
                    text_chunks = [
                        reader.pages[i].extract_text() or ""
                        for i in range(pages_to_process)
                    ]
                    text = "\n".join(text_chunks)
            except Exception as e:
                warnings.append(f"PyPDF2 extraction failed: {e}")

        if self._should_use_ocr(text):
            ocr_result = await self._extract_pdf_with_ocr(file_path)
            if ocr_result.get("text"):
                text = ocr_result["text"]
                ocr_used = True
                warnings.extend(ocr_result.get("warnings", []))

        return {
            "text": self._normalize_text(text),
            "page_count": page_count,
            "ocr_used": ocr_used,
            "warnings": warnings,
            "file_info": file_info,
        }

    def _should_use_ocr(self, text: str) -> bool:
        if not self.ocr_enabled:
            return False
        return not text.strip()

    async def _extract_pdf_with_ocr(self, file_path: str | Path) -> dict[str, Any]:
        warnings: list[str] = []
        if not (HAS_FITZ and HAS_PYTESSERACT and HAS_PIL):
            return {
                "error": "OCR dependencies (fitz, pytesseract, PIL) not available",
                "warnings": warnings,
            }

        try:
            _require_dependency(fitz, "PyMuPDF")
            _require_dependency(pytesseract, "pytesseract")
            loop = asyncio.get_running_loop()
            doc = await loop.run_in_executor(None, lambda: fitz.open(str(file_path)))
            ocr_chunks = []
            pages_to_process = min(self.max_pdf_pages, len(doc))
            for page_num in range(pages_to_process):
                page = doc.load_page(page_num)
                pix = getattr(page, "get_pixmap", None)
                pix = pix() if callable(pix) else getattr(page, "getPixmap", None)
                pix = pix() if callable(pix) else None
                if self._is_valid_pixmap(pix):
                    img = self._pixmap_to_pil_image(pix)
                    if img is not None:
                        ocr_text = await loop.run_in_executor(
                            None, pytesseract.image_to_string(img, lang="eng")
                        )
                        if ocr_text.strip():
                            ocr_chunks.append(ocr_text)
                    else:
                        warnings.append(
                            f"Could not extract image from page {page_num + 1}"
                        )
                else:
                    warnings.append(f"Invalid pixmap on page {page_num + 1}")
            if ocr_chunks:
                return {"text": "\n".join(ocr_chunks), "warnings": warnings}
            return {"warnings": warnings}
        except Exception as e:
            return {"error": f"OCR extraction failed: {e}", "warnings": warnings}

    @staticmethod
    def _is_valid_pixmap(pix: Any) -> bool:
        return (
            pix is not None
            and hasattr(pix, "n")
            and hasattr(pix, "width")
            and hasattr(pix, "height")
            and hasattr(pix, "samples")
        )

    @staticmethod
    def _pixmap_to_pil_image(pix: Any) -> Any | None:
        mode_map = {1: "L", 3: "RGB", 4: "RGBA"}
        try:
            mode = mode_map.get(getattr(pix, "n", 3), "RGB")
            width = int(getattr(pix, "width", 0))
            height = int(getattr(pix, "height", 0))
            samples = getattr(pix, "samples", None)
            if (
                isinstance(width, int)
                and isinstance(height, int)
                and isinstance(samples, (bytes, bytearray))
            ):
                _require_dependency(Image, "Pillow")
                return Image.frombytes(mode, (width, height), samples)
            return None
        except (AttributeError, ValueError, TypeError):
            return None

    async def extract_image_with_ocr(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        if not (HAS_PYTESSERACT and HAS_PIL):
            return {
                "error": "OCR dependencies (pytesseract, PIL) not available",
                "file_info": file_info,
                "action_plan": ["Install pytesseract and PIL to enable OCR"],
            }

        try:
            _require_dependency(Image, "Pillow")
            _require_dependency(pytesseract, "pytesseract")
            loop = asyncio.get_running_loop()
            img = await loop.run_in_executor(None, lambda: Image.open(file_path))
            ocr_text = await loop.run_in_executor(
                None, pytesseract.image_to_string(img, lang="eng")
            )
            return {
                "text": self._normalize_text(ocr_text),
                "image_mode": img.mode,
                "image_size": img.size,
                "warnings": ["OCR used for text extraction from image"],
                "file_info": file_info,
            }
        except Exception as e:
            return {
                "error": f"OCR image processing failed: {e}",
                "file_info": file_info,
                "action_plan": ["Verify image format or improve image quality for OCR"],
            }
