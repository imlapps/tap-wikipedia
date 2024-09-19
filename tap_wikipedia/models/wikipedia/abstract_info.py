from typing import Annotated
from pydantic import Field, BaseModel
from tap_wikipedia.models.types import Title, WebPageUrl, ImageUrl


class AbstractInfo(BaseModel):
    title: Title
    url: WebPageUrl
    abstract: Annotated[str, Field(json_schema_extra={
        "strip_whitespace": "True"})]
    imageUrl: ImageUrl | None = None
