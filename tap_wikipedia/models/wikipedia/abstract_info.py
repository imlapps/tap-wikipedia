from typing import Annotated
from pydantic import Field, BaseModel
from tap_wikipedia.models.types import Title, WebPageUrl, ImageUrl


class AbstractInfo(BaseModel):
    """Pydantic Model to hold the contents extracted from the Wikipedia abstracts dump."""

    title: Title
    url: WebPageUrl
    abstract: Annotated[str, Field(
        json_schema_extra={"strip_whitespace": "True"})]
    imageUrl: ImageUrl | None = None
