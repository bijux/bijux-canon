"""Structured data extraction capability for the universal file reader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import importlib
import json
from pathlib import Path
import xml.etree.ElementTree as _ElementTree  # nosec B405
from typing import Any, Protocol, TypeVar, cast


class PandasModule(Protocol):
    errors: Any

    def read_csv(
        self,
        file_path: str | Path,
        *,
        sep: str,
        encoding: str,
        nrows: int | None = None,
    ) -> Any: ...


class YamlModule(Protocol):
    YAMLError: type[Exception]

    def safe_load(self, stream: Any) -> Any: ...


class XmlModule(Protocol):
    ParseError: type[Exception]

    def parse(self, file_path: str | Path) -> Any: ...


pd: PandasModule | None = None
yaml: YamlModule | None = None
ET: XmlModule | None = None

try:
    pd = cast(PandasModule, importlib.import_module("pandas"))
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    yaml = cast(YamlModule, importlib.import_module("yaml"))
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

ET = cast(XmlModule, _ElementTree)
HAS_XML = True


DependencyT = TypeVar("DependencyT")


def _require_dependency(module: DependencyT | None, name: str) -> DependencyT:
    if module is None:
        raise RuntimeError(f"{name} dependency is required but not installed")
    return module


def _read_csv_with_options(
    pandas_module: PandasModule,
    file_path: str | Path,
    *,
    sep: str,
    encoding: str,
    nrows: int | None = None,
) -> Any:
    return pandas_module.read_csv(
        file_path,
        sep=sep,
        encoding=encoding,
        nrows=nrows,
    )


YAML_EXTENSIONS: set[str] = {".yaml", ".yml"}
XML_EXTENSIONS: set[str] = {".xml"}


class StructuredExtractor:
    """Capability module for structured file extraction."""

    def __init__(
        self,
        *,
        create_file_audit: Callable[[str | Path], Any],
    ) -> None:
        self._create_file_audit = create_file_audit

    async def extract_json_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                parsed_data = json.load(f)
            return {
                "parsed": parsed_data,
                "data_type": type(parsed_data).__name__,
                "file_info": file_info,
            }
        except json.JSONDecodeError as e:
            return {
                "error": f"JSON parsing error: {e}",
                "file_info": file_info,
                "action_plan": ["Fix JSON syntax errors in the file"],
            }
        except Exception as e:
            return {
                "error": f"Failed to read JSON file: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file is a valid JSON file"],
            }

    async def extract_csv_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        if not HAS_PANDAS:
            return {
                "error": "pandas is required for CSV processing but not installed",
                "file_info": file_info,
                "action_plan": ["Install pandas to enable CSV processing"],
            }

        try:
            pandas_module = _require_dependency(pd, "pandas")
            for sep in [",", ";", "\t"]:
                for encoding in ["utf-8", "latin1", "cp1252"]:
                    try:
                        df = await asyncio.to_thread(
                            _read_csv_with_options,
                            pandas_module,
                            file_path,
                            sep=sep,
                            encoding=encoding,
                            nrows=1000,
                        )
                        if len(df.columns) > 1:
                            full_df = await asyncio.to_thread(
                                _read_csv_with_options,
                                pandas_module,
                                file_path,
                                sep=sep,
                                encoding=encoding,
                            )
                            return {
                                "columns": list(full_df.columns),
                                "n_rows": len(full_df),
                                "n_columns": len(full_df.columns),
                                "sample_data": full_df.head(5).to_dict(
                                    orient="records"
                                ),
                                "data_types": full_df.dtypes.astype(str).to_dict(),
                                "separator_used": sep,
                                "encoding_used": encoding,
                                "file_info": file_info,
                            }
                    except (
                        pandas_module.errors.ParserError,
                        UnicodeDecodeError,
                        OSError,
                    ):
                        continue

            return {
                "error": "Could not parse CSV with any supported format",
                "file_info": file_info,
                "action_plan": [
                    "Verify CSV format and separator, or convert to a supported format"
                ],
            }
        except Exception as e:
            return {
                "error": f"CSV processing failed: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file is a valid CSV file"],
            }

    async def extract_yaml_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        if not HAS_YAML:
            return {
                "error": "PyYAML is required for YAML processing but not installed",
                "file_info": file_info,
                "action_plan": ["Install PyYAML to enable YAML processing"],
            }

        try:
            with open(file_path, encoding="utf-8") as f:
                yaml_module = _require_dependency(yaml, "PyYAML")
                parsed_data = yaml_module.safe_load(f)
            return {
                "parsed": parsed_data,
                "data_type": type(parsed_data).__name__,
                "file_info": file_info,
            }
        except _require_dependency(yaml, "PyYAML").YAMLError as e:
            return {
                "error": f"YAML parsing error: {e}",
                "file_info": file_info,
                "action_plan": ["Fix YAML syntax errors in the file"],
            }
        except Exception as e:
            return {
                "error": f"Failed to read YAML file: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file is a valid YAML file"],
            }

    async def extract_xml_file(self, file_path: str | Path) -> dict[str, Any]:
        file_info = await self._create_file_audit(file_path)

        if not HAS_XML:
            return {
                "error": (
                    "xml.etree.ElementTree is required for XML processing "
                    "but not installed"
                ),
                "file_info": file_info,
                "action_plan": [
                    "Install xml.etree.ElementTree to enable XML processing"
                ],
            }

        try:
            xml_module = _require_dependency(ET, "xml.etree.ElementTree")
            tree = xml_module.parse(file_path)  # nosec B314
            root = tree.getroot()
            xml_dict = self._xml_to_dict(root)
            return {
                "parsed": xml_dict,
                "root_tag": root.tag,
                "file_info": file_info,
            }
        except _require_dependency(ET, "xml.etree.ElementTree").ParseError as e:
            return {
                "error": f"XML parsing error: {e}",
                "file_info": file_info,
                "action_plan": ["Fix XML syntax errors in the file"],
            }
        except Exception as e:
            return {
                "error": f"Failed to read XML file: {e}",
                "file_info": file_info,
                "action_plan": ["Verify file is a valid XML file"],
            }

    def _xml_to_dict(self, element: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if getattr(element, "attrib", None):
            result["attributes"] = dict(element.attrib)
        children = list(element)
        if children:
            child_dict: dict[str, Any] = {}
            for child in children:
                child_data = self._xml_to_dict(child)
                if child.tag in child_dict:
                    existing = child_dict[child.tag]
                    if isinstance(existing, list):
                        existing.append(child_data)
                    else:
                        child_dict[child.tag] = [existing, child_data]
                else:
                    child_dict[child.tag] = child_data
            result.update(child_dict)
        text = element.text.strip() if element.text else ""
        if text:
            result["text"] = text
        return {element.tag: result}
