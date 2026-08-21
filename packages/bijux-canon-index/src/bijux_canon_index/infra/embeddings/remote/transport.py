# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded standard-library HTTP transport for remote embeddings."""

from __future__ import annotations

import http.client
import urllib.parse
from collections.abc import Mapping

from .contracts import RemoteHTTPResponse, RemoteTimeouts


class StandardLibraryEmbeddingTransport:
    """HTTP transport with explicit connect/read timeouts and response bounds."""

    def send(
        self,
        *,
        endpoint: str,
        headers: Mapping[str, str],
        body: bytes,
        timeouts: RemoteTimeouts,
        max_response_bytes: int,
    ) -> RemoteHTTPResponse:
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.hostname is None:
            raise ValueError("remote embedding endpoint has no hostname")
        connection_type = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(
            parsed.hostname,
            parsed.port,
            timeout=timeouts.connect_seconds,
        )
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        try:
            connection.request("POST", path, body=body, headers=dict(headers))
            if connection.sock is not None:
                connection.sock.settimeout(timeouts.read_seconds)
            response = connection.getresponse()
            content = response.read(max_response_bytes + 1)
            if len(content) > max_response_bytes:
                raise ValueError("remote embedding response exceeds configured limit")
            return RemoteHTTPResponse(
                response.status,
                {name.lower(): value for name, value in response.getheaders()},
                content,
            )
        finally:
            connection.close()


__all__ = ["StandardLibraryEmbeddingTransport"]
