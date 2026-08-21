# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Byte signatures and bounded structural checks for OCR candidate images."""

from __future__ import annotations

from bijux_canon_ingest.infra.admission.limits import AdmissionFailure


def identify_image_media_type(content: bytes) -> str | None:
    """Identify an admitted image container from its byte signature."""

    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if content.startswith(b"BM"):
        return "image/bmp"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def inspect_image(content: bytes, media_type: str) -> None:
    """Reject visibly malformed containers without claiming image decoding."""

    malformed = AdmissionFailure(
        "malformed_input", f"{media_type} input has an invalid container structure"
    )
    if media_type == "image/png":
        if (
            len(content) < 45
            or int.from_bytes(content[8:12], "big") != 13
            or content[12:16] != b"IHDR"
            or int.from_bytes(content[16:20], "big") == 0
            or int.from_bytes(content[20:24], "big") == 0
            or content[-12:-8] != b"\x00\x00\x00\x00"
            or content[-8:-4] != b"IEND"
        ):
            raise malformed
        return
    if media_type == "image/jpeg":
        _inspect_jpeg(content, malformed)
        return
    if media_type == "image/gif":
        if (
            len(content) < 14
            or int.from_bytes(content[6:8], "little") == 0
            or int.from_bytes(content[8:10], "little") == 0
            or not content.endswith(b"\x3b")
        ):
            raise malformed
        return
    if media_type == "image/tiff":
        little_endian = content.startswith(b"II*\x00")
        if len(content) < 8:
            raise malformed
        directory_offset = int.from_bytes(
            content[4:8], "little" if little_endian else "big"
        )
        if directory_offset < 8 or directory_offset + 2 > len(content):
            raise malformed
        return
    if media_type == "image/bmp":
        if len(content) < 26:
            raise malformed
        file_size = int.from_bytes(content[2:6], "little")
        pixel_offset = int.from_bytes(content[10:14], "little")
        width = int.from_bytes(content[18:22], "little", signed=True)
        height = int.from_bytes(content[22:26], "little", signed=True)
        if (
            file_size > len(content)
            or pixel_offset >= len(content)
            or not width
            or not height
        ):
            raise malformed
        return
    if media_type == "image/webp":
        declared_size = int.from_bytes(content[4:8], "little") + 8
        if (
            len(content) < 20
            or declared_size > len(content)
            or content[12:16] not in {b"VP8 ", b"VP8L", b"VP8X"}
        ):
            raise malformed
        return
    raise malformed


def _inspect_jpeg(content: bytes, malformed: AdmissionFailure) -> None:
    if len(content) < 12 or not content.endswith(b"\xff\xd9"):
        raise malformed
    position = 2
    frame_markers = frozenset(
        {
            *range(0xC0, 0xC4),
            *range(0xC5, 0xC8),
            *range(0xC9, 0xCC),
            *range(0xCD, 0xD0),
        }
    )
    while position + 3 < len(content):
        if content[position] != 0xFF:
            position += 1
            continue
        while position < len(content) and content[position] == 0xFF:
            position += 1
        if position >= len(content):
            break
        marker = content[position]
        position += 1
        if marker in {0x00, 0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}:
            continue
        if position + 2 > len(content):
            raise malformed
        segment_length = int.from_bytes(content[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(content):
            raise malformed
        if marker in frame_markers:
            if (
                segment_length < 7
                or int.from_bytes(content[position + 3 : position + 5], "big") == 0
                or int.from_bytes(content[position + 5 : position + 7], "big") == 0
            ):
                raise malformed
            return
        position += segment_length
    raise malformed


__all__ = ["identify_image_media_type", "inspect_image"]
