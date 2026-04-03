"""Shared Pydantic base class with consistent configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic.config import ConfigDict as _RuntimeConfigDict
from pydantic.main import BaseModel as _RuntimeBaseModel

if TYPE_CHECKING:
    from bijux_agent.schema._pydantic_typing import BaseModel as PydanticBase
else:
    PydanticBase = _RuntimeBaseModel  # type: ignore[assignment]

ModelConfigFactory = _RuntimeConfigDict


class TypedBaseModel(PydanticBase):
    """Centralized typed base ensuring all schemas inherit the same contract.

    Using a single ConfigDict factory keeps arbitrary-types_allowed/extra
    settings consistent while making it obvious why every schema extends this
    class.
    """

    model_config = ModelConfigFactory(arbitrary_types_allowed=True)
