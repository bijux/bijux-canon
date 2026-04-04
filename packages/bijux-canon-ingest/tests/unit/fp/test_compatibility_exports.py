# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.fp import applicative, validation
from bijux_canon_ingest.fp.core import chunk_state_from_dict
from bijux_canon_ingest.result import Err
from bijux_canon_ingest.result.types import Ok


def test_applicative_module_re_exports_validation_api() -> None:
    assert applicative.v_failure is validation.v_failure
    assert applicative.__all__ == validation.__all__


def test_ok_ap_preserves_err_variant() -> None:
    result = Ok(lambda value: value + 1).ap(Err("boom"))

    assert isinstance(result, Err)
    assert result.error == "boom"


def test_chunk_state_from_dict_rejects_non_numeric_embeddings() -> None:
    try:
        chunk_state_from_dict(
            {
                "version": 1,
                "kind": "success",
                "embedding": ["bad"],
                "metadata": {},
            }
        )
    except ValueError as exc:
        assert "embedding must be a JSON array of numbers" in str(exc)
    else:  # pragma: no cover - defensive test shape
        raise AssertionError("chunk_state_from_dict should reject non-numeric embeddings")
