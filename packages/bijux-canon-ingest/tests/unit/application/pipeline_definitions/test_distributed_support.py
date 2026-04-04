# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_ingest.application.pipeline_definitions import (
    DistributedCompilerError,
    beam_support,
    compile_to_beam,
    compile_to_dask_bag,
    dask_support,
)


def test_dask_support_is_explicit_about_missing_compiler() -> None:
    support = dask_support()
    assert support.backend == "dask"
    assert not support.implemented
    assert support.reason


def test_beam_support_is_explicit_about_missing_compiler() -> None:
    support = beam_support()
    assert support.backend == "beam"
    assert not support.implemented
    assert support.reason


def test_compile_to_dask_bag_raises_typed_boundary_error() -> None:
    with pytest.raises(DistributedCompilerError):
        compile_to_dask_bag()


def test_compile_to_beam_raises_typed_boundary_error() -> None:
    with pytest.raises(DistributedCompilerError):
        compile_to_beam()
