# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Format-specific parsers for sources that passed admission."""

from bijux_canon_ingest.infra.parsers.jats import parse_jats_content

__all__ = ["parse_jats_content"]
