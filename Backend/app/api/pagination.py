"""Bounded list inputs and the shared page envelope used by every list operation."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class PageParams(BaseModel):
    """`limit`/`offset` query parameters. Services count the authorized set before slicing."""

    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT
    offset: Annotated[int, Field(ge=0)] = 0


class Page[ItemT](BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ItemT]
    total: Annotated[int, Field(ge=0)]
    limit: int
    offset: int
