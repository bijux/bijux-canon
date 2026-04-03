# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.retrieval import stable_token_bucket, tokenize


def test_tokenize_is_deterministic_and_ascii_normalized() -> None:
    assert tokenize("Alpha, beta! GAMMA?") == ["alpha", "beta", "gamma"]


def test_stable_token_bucket_is_repeatable() -> None:
    assert stable_token_bucket("alpha", buckets=128) == stable_token_bucket(
        "alpha",
        buckets=128,
    )
