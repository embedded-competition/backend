from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
        serialize_by_alias=True,
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    error: str
    requestId: str
