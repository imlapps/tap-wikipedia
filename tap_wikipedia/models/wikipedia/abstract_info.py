from typing import Annotated
from pydantic import Field, BaseModel

# A tiny type for string fields in an AbstractInfo
AbstractInfoStringType = Annotated[str, Field(min_length=1, json_schema_extra={
    "strip_whitespace": "True"})]


class AbstractInfo(BaseModel):
    title: AbstractInfoStringType
    url: AbstractInfoStringType
    imageUrl: AbstractInfoStringType | None = None
    abstract: AbstractInfoStringType | None = None
