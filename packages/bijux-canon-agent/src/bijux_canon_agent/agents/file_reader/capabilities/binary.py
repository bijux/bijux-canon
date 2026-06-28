"""Binary extraction capability for the universal file reader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import importlib
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast


class PdfMinerHighLevelModule(Protocol):
    def extract_text(self, file_path: str) -> str: ...


class PypdfModule(Protocol):
    PdfReader: Any


class PytesseractModule(Protocol):
    def image_to_string(self, image: Any, *, lang: str) -> str: ...


class ImageModule(Protocol):
    def frombytes(
        self, mode: str, size: tuple[int, int], data: bytes | bytearray
    ) -> Any: ...

    def open(self, file_path: str | Path) -> Any: ...


class FitzModule(Protocol):
    def open(self, file_path: str) -> Any: ...


pdfminer_high_level: PdfMinerHighLevelModule | None = None
pypdf: PypdfModule | None = None
pytesseract: PytesseractModule | None = None
Image: ImageModule | None = None
fitz: FitzModule | None = None

try:
    pdfminer_high_level = cast(
        PdfMinerHighLevelModule,
        importlib.import_module("pdfminer.high_level"),
    )
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

try:
    pypdf = cast(PypdfModule, importlib.import_module("pypdf"))
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    pytesseract = cast(PytesseractModule, importlib.import_module("pytesseract"))
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    from PIL import Image as _Image

    Image = cast(ImageModule, _Image)
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    fitz = cast(FitzModule, importlib.import_module("fitz"))
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


DependencyT = TypeVar("DependencyT")


def _require_dependency(module: DependencyT | None, name: str) -> DependencyT:
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
                pdfminer_module = _require_dependency(
                    pdfminer_high_level, "pdfminer.six"
                )
                text = await asyncio.to_thread(
                    pdfminer_module.extract_text,
                    str(file_path),
                )
            except Exception as e:
                warnings.append(f"pdfminer extraction failed: {e}")

        if HAS_PYPDF and not text.strip():
            try:
                with open(file_path, "rb") as file:
                    pypdf_module = _require_dependency(pypdf, "pypdf")
                    reader = pypdf_module.PdfReader(file)
                    page_count = len(reader.pages)
                    pages_to_process = min(self.max_pdf_pages, page_count)
                    text_chunks = [
                        reader.pages[i].extract_text() or ""
                        for i in range(pages_to_process)
                    ]
                    text = "\n".join(text_chunks)
            except Exception as e:
                warnings.append(f"pypdf extraction failed: {e}")

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
            fitz_module = _require_dependency(fitz, "PyMuPDF")
            pytesseract_module = _require_dependency(pytesseract, "pytesseract")
            doc = await asyncio.to_thread(fitz_module.open, str(file_path))
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
                        ocr_text = await asyncio.to_thread(
                            pytesseract_module.image_to_string,
                            img,
                            lang="eng",
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
                image_module = _require_dependency(Image, "Pillow")
                return image_module.frombytes(mode, (width, height), samples)
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
            image_module = _require_dependency(Image, "Pillow")
            pytesseract_module = _require_dependency(pytesseract, "pytesseract")
            img = await asyncio.to_thread(image_module.open, file_path)
            ocr_text = await asyncio.to_thread(
                pytesseract_module.image_to_string,
                img,
                lang="eng",
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
