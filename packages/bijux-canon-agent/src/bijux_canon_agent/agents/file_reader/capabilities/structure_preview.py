"""Structure preview helpers for file-reader results."""

from __future__ import annotations

from typing import Any


def create_structure_preview(
    extension: str,
    result: dict[str, Any],
    *,
    text_extensions: set[str],
    image_extensions: set[str],
    yaml_extensions: set[str],
    xml_extensions: set[str],
    docx_extensions: set[str],
) -> dict[str, Any]:
    """Create a structural preview of the extracted file content."""
    ext = extension.lower()
    preview: dict[str, Any] = {"format": ext.lstrip(".")}

    if ext in text_extensions and "text" in result:
        preview.update(_text_preview(result["text"]))
    elif ext == ".json" and "parsed" in result:
        preview.update(_structured_preview(result))
    elif ext == ".csv" and "columns" in result:
        preview.update(_csv_preview(result))
    elif ext in yaml_extensions and "parsed" in result:
        preview.update(_structured_preview(result))
    elif ext in xml_extensions and "parsed" in result:
        preview.update(
            {
                "root_tag": result.get("root_tag"),
                "structure": analyze_json_structure(result["parsed"]),
                "sections": [],
                "tables": [],
                "images": [],
            }
        )
    elif ext in docx_extensions and "text" in result:
        preview.update(_docx_preview(result))
    elif ext == ".pdf":
        preview.update(_pdf_preview(result))
    elif ext in image_extensions and "image_size" in result:
        preview.update(_image_preview(result))

    return preview


def analyze_json_structure(data: Any, max_depth: int = 3) -> dict[str, Any]:
    """Analyze nested structured data for preview display."""
    if max_depth <= 0:
        return {"type": type(data).__name__, "truncated": True}
    if isinstance(data, dict):
        return {
            "type": "object",
            "keys": list(data.keys())[:10],
            "key_count": len(data),
            "sample_values": {
                key: analyze_json_structure(value, max_depth - 1)
                for key, value in list(data.items())[:3]
            },
        }
    if isinstance(data, list):
        return {
            "type": "array",
            "length": len(data),
            "sample_items": [
                analyze_json_structure(item, max_depth - 1) for item in data[:3]
            ],
        }
    return {"type": type(data).__name__, "value": str(data)[:100]}


def _text_preview(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    sections = [
        {"title": line, "depth": line.count("#")}
        for line in lines
        if line.startswith("#")
    ]
    return {
        "line_count": len(lines),
        "character_count": len(text),
        "sample_lines": lines[:5],
        "sections": sections[:10],
        "section_count": len(sections),
        "tables": [],
        "images": [],
    }


def _structured_preview(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_type": result.get("data_type", "unknown"),
        "structure": analyze_json_structure(result["parsed"]),
        "sections": [],
        "tables": [],
        "images": [],
    }


def _csv_preview(result: dict[str, Any]) -> dict[str, Any]:
    return {
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


def _docx_preview(result: dict[str, Any]) -> dict[str, Any]:
    lines = result["text"].splitlines()
    return {
        "line_count": len(lines),
        "character_count": len(result["text"]),
        "sample_lines": lines[:5],
        "paragraph_count": result.get("paragraph_count", 0),
        "sections": [],
        "tables": [],
        "images": [],
    }


def _pdf_preview(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "page_count": result.get("page_count"),
        "ocr_used": result.get("ocr_used", False),
        "has_text": bool(result.get("text", "").strip()),
        "sections": [],
        "tables": [],
        "images": [],
    }


def _image_preview(result: dict[str, Any]) -> dict[str, Any]:
    return {
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
